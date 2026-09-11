"""F08：索引新鲜度自动检测（语料签名 + 模型/分块版本记录）。

用替身集合验证：同数量内容变化触发重建；内容未变复用索引；数量变化重建；
来源清空不再保留旧集合；模型切换触发重建；嵌入失败不破坏旧索引；
freshness_status 只读体检给出陈旧原因。
"""

import pytest

from app.services import vector_store
from app.services.runbook_chunker import RunbookChunk
from app.services.similar_incident_retriever import HistoricalIncident
from app.services.vector_store import VectorStore


class _FakeCollection:
    """替身 ChromaDB 集合：记录 add/delete/modify，暴露 count/get/metadata。"""

    def __init__(self):
        self.ids: list[str] = []
        self.metadata: dict = {}
        self.adds: list[dict] = []
        self.deletes: list[list[str]] = []

    def count(self) -> int:
        return len(self.ids)

    def get(self) -> dict:
        return {"ids": list(self.ids)}

    def delete(self, ids: list[str]) -> None:
        self.deletes.append(list(ids))
        self.ids = [i for i in self.ids if i not in ids]

    def add(self, ids, documents=None, metadatas=None, embeddings=None) -> None:
        self.ids = list(ids)
        self.adds.append({"ids": list(ids), "documents": documents})

    def modify(self, metadata: dict) -> None:
        self.metadata = dict(metadata)


class _EmbedA:
    model_name = "model-a"

    def encode(self, texts):
        return [[0.1, 0.2]] * len(texts)


class _EmbedB:
    model_name = "model-b"

    def encode(self, texts):
        return [[0.3, 0.4]] * len(texts)


class _BoomEmbed:
    model_name = "model-boom"

    def encode(self, texts):
        raise RuntimeError("embedding backend down")


def _chunk(chunk_id: str, content: str) -> RunbookChunk:
    return RunbookChunk(
        chunk_id=chunk_id, source="s", title="t",
        content=content, issue_type="database_issue",
        chunk_type="body", strategy="markdown",
    )


def _incident(historical_id: str, root_cause: str) -> HistoricalIncident:
    return HistoricalIncident(
        historical_id=historical_id, title="outage", service_name="svc",
        issue_type="database_issue", symptoms=["db down"],
        root_cause=root_cause, resolution="res", tags=["db"],
    )


def _store(embed_fn, runbook_collection, incident_collection) -> VectorStore:
    store = VectorStore(embed_fn=embed_fn)
    store._runbook_collection = runbook_collection  # 替身直挂，不起真实 chromadb
    store._incident_collection = incident_collection
    return store


def _build(store, chunks, incidents, monkeypatch, force: bool = False) -> None:
    monkeypatch.setattr(vector_store, "load_runbook_chunks", lambda: chunks)
    monkeypatch.setattr(
        "app.services.similar_incident_retriever.load_historical_incidents",
        lambda: incidents,
    )
    store.ensure_initialized(force=force)


def test_same_count_changed_content_triggers_rebuild(monkeypatch):
    runbooks = _FakeCollection()
    incidents = _FakeCollection()
    store = _store(_EmbedA().encode, runbooks, incidents)

    _build(store, [_chunk("c1", "old content")], [_incident("h1", "old cause")], monkeypatch)
    first_add = list(runbooks.adds)
    assert runbooks.ids == ["c1"]

    # 数量不变、内容变化 → 必须重建（旧代码按数量判断会静默复用）
    _build(store, [_chunk("c1", "new content")], [_incident("h1", "old cause")], monkeypatch)
    assert len(runbooks.adds) == len(first_add) + 1
    assert runbooks.adds[-1]["documents"][0].endswith("new content")


def test_unchanged_corpus_reuses_index(monkeypatch):
    runbooks = _FakeCollection()
    incidents = _FakeCollection()
    store = _store(_EmbedA().encode, runbooks, incidents)

    chunks = [_chunk("c1", "stable"), _chunk("c2", "stable2")]
    _build(store, chunks, [_incident("h1", "cause")], monkeypatch)
    adds_before = len(runbooks.adds)
    deletes_before = len(runbooks.deletes)

    _build(store, chunks, [_incident("h1", "cause")], monkeypatch)
    assert len(runbooks.adds) == adds_before  # 未重建
    assert len(runbooks.deletes) == deletes_before
    assert runbooks.metadata["corpus_signature"]  # 签名已记录


def test_count_change_triggers_rebuild(monkeypatch):
    runbooks = _FakeCollection()
    incidents = _FakeCollection()
    store = _store(_EmbedA().encode, runbooks, incidents)

    _build(store, [_chunk("c1", "a"), _chunk("c2", "b")], [], monkeypatch)
    assert runbooks.ids == ["c1", "c2"]

    _build(store, [_chunk("c1", "a")], [], monkeypatch)
    assert runbooks.ids == ["c1"]


def test_empty_source_clears_index(monkeypatch):
    runbooks = _FakeCollection()
    incidents = _FakeCollection()
    store = _store(_EmbedA().encode, runbooks, incidents)

    _build(store, [_chunk("c1", "a")], [], monkeypatch)
    assert runbooks.ids == ["c1"]

    # 来源清空 → 索引同步清空（旧代码直接 return，保留旧集合）
    _build(store, [], [], monkeypatch)
    assert runbooks.ids == []
    assert incidents.ids == []


def test_model_change_invalidates_signature(monkeypatch):
    runbooks = _FakeCollection()
    incidents = _FakeCollection()
    chunks = [_chunk("c1", "same content")]

    store_a = _store(_EmbedA().encode, runbooks, incidents)
    _build(store_a, chunks, [], monkeypatch)
    signature_a = runbooks.metadata["corpus_signature"]

    # 换模型重建同一语料 → 签名不同 → 触发重建，不静默复用旧模型嵌入
    store_b = _store(_EmbedB().encode, runbooks, incidents)
    _build(store_b, chunks, [], monkeypatch)
    assert runbooks.metadata["corpus_signature"] != signature_a
    assert runbooks.metadata["embedding_model"] == "model-b"


def test_embedding_failure_preserves_old_index(monkeypatch):
    runbooks = _FakeCollection()
    incidents = _FakeCollection()
    store = _store(_EmbedA().encode, runbooks, incidents)
    _build(store, [_chunk("c1", "old")], [], monkeypatch)

    broken = _store(_BoomEmbed().encode, runbooks, incidents)
    with pytest.raises(RuntimeError, match="embedding backend down"):
        _build(broken, [_chunk("c1", "changed")], [], monkeypatch)
    # 嵌入失败发生在删除旧数据之前 → 旧索引原样可用
    assert runbooks.ids == ["c1"]


def test_freshness_status_reports_reasons(monkeypatch):
    runbooks = _FakeCollection()
    incidents = _FakeCollection()
    store = _store(_EmbedA().encode, runbooks, incidents)
    chunks = [_chunk("c1", "v1")]
    _build(store, chunks, [_incident("h1", "cause")], monkeypatch)

    status = store.freshness_status()
    assert status["runbook_chunks"]["status"] == "fresh"
    assert status["historical_incidents"]["status"] == "fresh"

    # 同数量改内容（只换语料、不重建）→ content_or_model_changed
    monkeypatch.setattr(
        vector_store, "load_runbook_chunks", lambda: [_chunk("c1", "v2")]
    )
    status = store.freshness_status()
    assert status["runbook_chunks"]["status"] == "stale"
    assert status["runbook_chunks"]["reason"] == "content_or_model_changed"

    # 数量变化 → count_changed
    monkeypatch.setattr(vector_store, "load_runbook_chunks", lambda: [])
    status = store.freshness_status()
    assert status["runbook_chunks"]["reason"] == "count_changed"

    # 未签名的空库（旧版本构建）→ not_signed
    unsigned = _FakeCollection()
    unsigned_incidents = _FakeCollection()
    unsigned.add(ids=["stale-id"], documents=["stale doc"], metadatas=[{}], embeddings=[[0.1]])
    old_store = _store(_EmbedA().encode, unsigned, unsigned_incidents)
    status = old_store.freshness_status()
    assert status["runbook_chunks"]["status"] == "stale"
    assert status["runbook_chunks"]["reason"] == "not_signed"
