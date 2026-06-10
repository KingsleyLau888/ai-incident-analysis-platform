"""ChromaDB-backed vector store for runbook chunks and historical incidents.

Provides persistent embedding storage with metadata filtering and
incremental upsert — no re-embedding when adding new documents.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.services.runbook_chunker import RunbookChunk, load_runbook_chunks

# HistoricalIncident and load_historical_incidents are imported lazily
# inside _index_incidents to avoid a circular import with similar_incident_retriever.


# ---------------------------------------------------------------------------
# Protocol for the embedding function
# ---------------------------------------------------------------------------


class EmbeddingFunction(Protocol):
    """Callable that maps a list of texts to a list of embedding vectors."""

    def __call__(self, texts: list[str]) -> list[list[float]]: ...


# ---------------------------------------------------------------------------
# Default persistence directory
# ---------------------------------------------------------------------------

DEFAULT_PERSIST_DIR = Path(__file__).resolve().parents[2] / ".chroma_db"


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
    persist_dir: Path = DEFAULT_PERSIST_DIR
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
        if not force and collection.count() > 0:
            return

        chunks = load_runbook_chunks()
        if not chunks:
            return

        ids = [c.chunk_id for c in chunks]
        documents = [_chunk_document(c) for c in chunks]
        metadatas = [
            {
                "source": c.source,
                "title": c.title,
                "chunk_id": c.chunk_id,
            }
            for c in chunks
        ]

        # Delete existing entries before re-adding (incremental is possible,
        # but for simplicity we rebuild on force).
        if force and collection.count() > 0:
            all_ids = collection.get()["ids"]
            if all_ids:
                collection.delete(ids=all_ids)

        embeddings = self.embed_fn(documents)
        collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)

    def _index_incidents(self, force: bool = False) -> None:
        from app.services.similar_incident_retriever import load_historical_incidents

        collection = self._get_incident_collection()
        if not force and collection.count() > 0:
            return

        incidents = load_historical_incidents()
        if not incidents:
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

        if force and collection.count() > 0:
            all_ids = collection.get()["ids"]
            if all_ids:
                collection.delete(ids=all_ids)

        embeddings = self.embed_fn(documents)
        collection.add(
            ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
        )

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
