"""ChromaDB-backed vector store for runbook chunks and historical incidents.

Persistent embedding storage with metadata filtering. Index freshness
is signature-checked (F08): the corpus content, the embedding model, and
the chunking schema version are hashed into collection metadata — a stale
index (same count, changed content) is rebuilt instead of silently reused.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.services.runbook_chunker import RunbookChunk, load_runbook_chunks

# HistoricalIncident and load_historical_incidents are imported lazily
# inside _index_incidents to avoid a circular import with similar_incident_retriever.

# ---------------------------------------------------------------------------
# Corpus signature (F08)
# ---------------------------------------------------------------------------

# 分块/文档拼装语义版本：chunk 切分或文档构造逻辑变化时递增，
# 否则旧嵌入会与旧签名一同被误判为"新鲜"
CHUNK_SCHEMA_VERSION = 2
INCIDENT_SCHEMA_VERSION = 2

SIGNATURE_KEY = "corpus_signature"
MODEL_KEY = "embedding_model"
SCHEMA_VERSION_KEY = "schema_version"


def _embedding_model_name(embed_fn: EmbeddingFunction) -> str:
    """识别嵌入模型名（bound method 取所属实例的 model_name，其余取类型名）。"""
    owner = getattr(embed_fn, "__self__", embed_fn)
    return getattr(owner, "model_name", None) or type(owner).__name__


def _corpus_signature(
    entries: list[str], *, model: str, schema_version: int
) -> str:
    """SHA-256 over sorted per-item strings + model + schema version.

    数量不变但内容变化时签名必然变化；模型或分块版本切换同样变化。
    """
    payload = json.dumps(
        {
            "schema_version": schema_version,
            "model": model,
            "entries": sorted(entries),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _runbook_entry_strings(chunks: list[RunbookChunk]) -> list[str]:
    """每个 chunk 的稳定字符串：文档文本 + 参与过滤/展示的元数据。"""
    return [
        json.dumps(
            {
                "id": c.chunk_id,
                "doc": _chunk_document(c),
                "issue_type": c.issue_type,
                "chunk_type": c.chunk_type,
                "strategy": c.strategy,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for c in chunks
    ]


def _incident_entry_strings(incidents: list) -> list[str]:
    """每个历史事故的稳定字符串：文档文本 + 参与检索的元数据。"""
    return [
        json.dumps(
            {
                "id": getattr(inc, "historical_id", ""),
                "doc": _incident_document(inc),
                "issue_type": getattr(inc, "issue_type", ""),
                "tags": sorted(getattr(inc, "tags", [])),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for inc in incidents
    ]


def _stored_signature(collection) -> str | None:
    """读取集合元数据里的语料签名（旧版本构建的索引没有签名）。"""
    metadata = getattr(collection, "metadata", None) or {}
    return metadata.get(SIGNATURE_KEY)


def _stamp_signature(
    collection, signature: str, *, model: str, schema_version: int
) -> None:
    """把本次构建的签名写回集合元数据（保留描述等其他键）。"""
    metadata = getattr(collection, "metadata", None) or {}
    collection.modify(
        metadata={
            **metadata,
            SIGNATURE_KEY: signature,
            MODEL_KEY: model,
            SCHEMA_VERSION_KEY: str(schema_version),
        }
    )


# ---------------------------------------------------------------------------
# Protocol for the embedding function
# ---------------------------------------------------------------------------


class EmbeddingFunction(Protocol):
    """Callable that maps a list of texts to a list of embedding vectors."""

    def __call__(self, texts: list[str]) -> list[list[float]]: ...


# ---------------------------------------------------------------------------
# Default persistence directory
# ---------------------------------------------------------------------------

# Repo-relative default; env CHROMA_PERSIST_DIR still wins (see get_chroma_persist_dir).
DEFAULT_PERSIST_DIR = Path(__file__).resolve().parents[2] / "runtime" / "vector_store" / "chroma"


def get_chroma_persist_dir() -> Path:
    configured = os.getenv("CHROMA_PERSIST_DIR")
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_PERSIST_DIR


# ---------------------------------------------------------------------------
# ChromaDB-backed collections
# ---------------------------------------------------------------------------


@dataclass
class VectorStore:
    """Wraps two ChromaDB collections — runbook chunks and historical incidents.

    Typical usage::

        store = VectorStore(embed_fn=my_embedder)
        store.ensure_initialized()       # upsert runbook + incident data
        results = store.query_runbooks("database timeout", top_k=5)
    """

    embed_fn: EmbeddingFunction
    persist_dir: Path = field(default_factory=get_chroma_persist_dir)
    runbook_collection_name: str = "runbook_chunks"
    incident_collection_name: str = "historical_incidents"

    # -- internal state ------------------------------------------------------
    _client: object = field(init=False, repr=False, default=None)
    _runbook_collection: object = field(init=False, repr=False, default=None)
    _incident_collection: object = field(init=False, repr=False, default=None)

    # ------------------------------------------------------------------
    # Lazy initialisation
    # ------------------------------------------------------------------

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        import chromadb

        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))

    def _get_runbook_collection(self):
        self._ensure_client()
        if self._runbook_collection is None:
            self._runbook_collection = self._client.get_or_create_collection(
                name=self.runbook_collection_name,
                metadata={"description": "Runbook chunks for incident diagnosis"},
            )
        return self._runbook_collection

    def _get_incident_collection(self):
        self._ensure_client()
        if self._incident_collection is None:
            self._incident_collection = self._client.get_or_create_collection(
                name=self.incident_collection_name,
                metadata={"description": "Historical incidents for similarity search"},
            )
        return self._incident_collection

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def ensure_initialized(self, force: bool = False) -> None:
        """Populate both collections if they are empty (or *force* is set)."""
        self._index_runbooks(force=force)
        self._index_incidents(force=force)

    def _index_runbooks(self, force: bool = False) -> None:
        collection = self._get_runbook_collection()

        chunks = load_runbook_chunks()
        signature = _corpus_signature(
            _runbook_entry_strings(chunks),
            model=_embedding_model_name(self.embed_fn),
            schema_version=CHUNK_SCHEMA_VERSION,
        )
        existing_count = collection.count()
        stored_signature = _stored_signature(collection)
        # F08：数量、内容、模型、分块版本全部一致才复用；否则重建。
        # 空语料也走替换路径——来源清空不再悄悄保留旧集合。
        if not force and existing_count == len(chunks) and stored_signature == signature:
            return

        ids = [c.chunk_id for c in chunks]
        documents = [_chunk_document(c) for c in chunks]
        metadatas = [
            {
                "source": c.source,
                "title": c.title,
                "chunk_id": c.chunk_id,
                "issue_type": c.issue_type,
                "chunk_type": c.chunk_type,
                "strategy": c.strategy,
            }
            for c in chunks
        ]

        # F08：先嵌入（耗时且易失败的阶段）再动旧索引——嵌入失败时
        # 旧索引原样可用；替换（delete+add）只做本地磁盘写入。
        embeddings = self.embed_fn(documents)

        if existing_count > 0:
            all_ids = collection.get()["ids"]
            if all_ids:
                collection.delete(ids=all_ids)
        if ids:
            collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
        _stamp_signature(collection, signature, model=_embedding_model_name(self.embed_fn),
                         schema_version=CHUNK_SCHEMA_VERSION)

    def _index_incidents(self, force: bool = False) -> None:
        from app.services.similar_incident_retriever import load_historical_incidents

        collection = self._get_incident_collection()

        incidents = load_historical_incidents()
        signature = _corpus_signature(
            _incident_entry_strings(incidents),
            model=_embedding_model_name(self.embed_fn),
            schema_version=INCIDENT_SCHEMA_VERSION,
        )
        existing_count = collection.count()
        stored_signature = _stored_signature(collection)
        if not force and existing_count == len(incidents) and stored_signature == signature:
            return

        ids = [inc.historical_id for inc in incidents]
        documents = [_incident_document(inc) for inc in incidents]
        metadatas = [
            {
                "historical_id": getattr(inc, "historical_id", ""),
                "title": getattr(inc, "title", ""),
                "service_name": getattr(inc, "service_name", ""),
                "issue_type": getattr(inc, "issue_type", ""),
                "root_cause": getattr(inc, "root_cause", ""),
                "resolution": getattr(inc, "resolution", ""),
                "tags": json.dumps(getattr(inc, "tags", [])),
            }
            for inc in incidents
        ]

        # F08：先嵌入再动旧索引（同上，嵌入失败保留可用索引）
        embeddings = self.embed_fn(documents)

        if existing_count > 0:
            all_ids = collection.get()["ids"]
            if all_ids:
                collection.delete(ids=all_ids)
        if ids:
            collection.add(
                ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
            )
        _stamp_signature(collection, signature, model=_embedding_model_name(self.embed_fn),
                         schema_version=INCIDENT_SCHEMA_VERSION)

    # ------------------------------------------------------------------
    # Query interface
    # ------------------------------------------------------------------

    def query_runbooks(
        self,
        query_text: str,
        top_k: int = 3,
        where: dict | None = None,
    ) -> list[dict]:
        """Return top-k runbook chunks for *query_text*.

        Each result dict: ``{chunk_id, source, title, content, score, rank}``.
        """
        collection = self._get_runbook_collection()
        if collection.count() == 0:
            return []

        query_embedding = self.embed_fn([query_text])
        result = collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        return _format_chroma_results(
            result,
            content_key="documents",
            distance_key="distances",
            top_k=top_k,
        )

    def query_incidents(
        self,
        query_text: str,
        top_k: int = 3,
        where: dict | None = None,
    ) -> list[dict]:
        """Return top-k historical incidents for *query_text*.

        Each result dict: ``{historical_id, title, issue_type, score, root_cause, resolution}``.
        """
        collection = self._get_incident_collection()
        if collection.count() == 0:
            return []

        query_embedding = self.embed_fn([query_text])
        result = collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, collection.count()),
            where=where,
            include=["metadatas", "distances"],
        )

        return _format_chroma_results(
            result,
            content_key=None,
            distance_key="distances",
            top_k=top_k,
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def runbook_count(self) -> int:
        self._ensure_client()
        try:
            return self._get_runbook_collection().count()
        except Exception:
            return 0

    def incident_count(self) -> int:
        self._ensure_client()
        try:
            return self._get_incident_collection().count()
        except Exception:
            return 0

    def freshness_status(self) -> dict:
        """F08：对比当前语料签名与已存索引签名（只读，不重建）。

        供构建脚本 --check 与运营巡检使用；ensure_initialized 本身在
        陈旧时会自动重建，因此正常运行不会静默复用错误索引。
        """
        return {
            "runbook_chunks": self._freshness_for(
                get_collection=self._get_runbook_collection,
                current_entries=_runbook_entry_strings(load_runbook_chunks()),
                schema_version=CHUNK_SCHEMA_VERSION,
            ),
            "historical_incidents": self._freshness_for(
                get_collection=self._get_incident_collection,
                current_entries=_incident_entry_strings(
                    _load_historical_incidents_lazy()
                ),
                schema_version=INCIDENT_SCHEMA_VERSION,
            ),
        }

    def _freshness_for(
        self,
        *,
        get_collection,
        current_entries: list[str],
        schema_version: int,
    ) -> dict:
        try:
            collection = get_collection()
            stored_count = collection.count()
            stored_signature = _stored_signature(collection)
        except Exception as exc:
            return {
                "status": "unavailable",
                "reason": f"{type(exc).__name__}: {str(exc)[:120]}",
            }
        current_signature = _corpus_signature(
            current_entries,
            model=_embedding_model_name(self.embed_fn),
            schema_version=schema_version,
        )
        if stored_count == 0 and not current_entries:
            return {"status": "fresh", "reason": None,
                    "stored_count": 0, "current_count": 0}
        if stored_signature is None:
            return {"status": "stale", "reason": "not_signed",
                    "stored_count": stored_count, "current_count": len(current_entries)}
        if stored_count != len(current_entries):
            return {"status": "stale", "reason": "count_changed",
                    "stored_count": stored_count, "current_count": len(current_entries)}
        if stored_signature != current_signature:
            return {"status": "stale", "reason": "content_or_model_changed",
                    "stored_count": stored_count, "current_count": len(current_entries)}
        return {"status": "fresh", "reason": None,
                "stored_count": stored_count, "current_count": len(current_entries)}


def _load_historical_incidents_lazy() -> list:
    """延迟导入历史事故加载函数（避免与 retriever 模块循环导入）。"""
    from app.services.similar_incident_retriever import load_historical_incidents

    return load_historical_incidents()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chunk_document(chunk: RunbookChunk) -> str:
    return f"{chunk.source}\n{chunk.title}\n{chunk.content}"


def _incident_document(incident) -> str:
    # incident is HistoricalIncident (lazy import to avoid circular dependency)
    return "\n".join(
        [
            incident.historical_id,
            incident.title,
            incident.service_name,
            incident.issue_type,
            " ".join(incident.symptoms),
            incident.root_cause,
            incident.resolution,
            " ".join(incident.tags),
        ]
    )


def _cosine_from_distance(distance: float) -> float:
    """Convert ChromaDB distance to cosine similarity.

    ChromaDB uses squared L2 for hnsw:space by default with
    sentence-transformers (which produce normalised vectors).
    For normalised vectors: cosine_sim ≈ 1 - (l2² / 2).
    """
    return max(0.0, 1.0 - distance / 2)


def _format_chroma_results(
    result: dict,
    *,
    content_key: str | None,
    distance_key: str,
    top_k: int,
) -> list[dict]:
    """Turn raw ChromaDB query result into consistent dict lists."""
    output: list[dict] = []
    ids_batch = result.get("ids", [[]])[0]
    metas_batch = result.get("metadatas", [[]])[0] if result.get("metadatas") else [[]] * len(ids_batch)
    distances_batch = result.get(distance_key, [[]])[0]

    contents_batch: list[str] = []
    if content_key and result.get(content_key):
        contents_batch = result[content_key][0]

    for rank, item_id in enumerate(ids_batch, start=1):
        meta = metas_batch[rank - 1] if rank - 1 < len(metas_batch) else {}
        distance = distances_batch[rank - 1] if rank - 1 < len(distances_batch) else 1.0
        score = _cosine_from_distance(distance)
        entry: dict = {
            **meta,
            "score": round(score, 6),
            "rank": rank,
        }
        if content_key and rank - 1 < len(contents_batch):
            entry["content"] = contents_batch[rank - 1]
        output.append(entry)
    return output[:top_k]
