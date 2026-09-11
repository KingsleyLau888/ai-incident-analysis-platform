"""F09：降级信息与 Trace 结构化元数据。

覆盖：降级结果携带 requested/effective provider、fallback_reason、duration、
model、token_usage；计时容器入口重置（提前返回不残留）；检索器实例级计时
互不串扰；Trace 记录实际执行的查询与改写 provider（不再用环境推测与占位
符）；诊断步骤 Trace 展示降级元数据。
"""

import json
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.llm.base import DiagnosisResult, StructuredDiagnosis
from app.llm.factory import FallbackLLMClient, get_llm_client
from app.llm.openai_compatible_client import OpenAICompatibleClient
from app.models.analysis import AnalysisTrace
from app.services import analysis_service
from app.services import embedding_service as es
from app.services.embedding_service import TfidfEmbedder, two_stage_retrieve
from app.services.query_rewriter import RewrittenQueries
from app.services.runbook_chunker import RunbookChunk
from app.services.runbook_retriever import RunbookRetriever, build_runbook_query
from app.services.similar_incident_retriever import (
    HistoricalIncident,
    SimilarIncidentRetriever,
    build_similar_incident_query,
)


def _diagnose_kwargs():
    return dict(
        incident_title="db down",
        service_name="svc",
        issue_type="database_issue",
        severity="high",
        # F10 起全空输入会弃答（insufficient_evidence），此处给一条证据
        # 保证本文件的用例走真实 API 调用路径，聚焦 F09 元数据本身。
        evidence_logs=[SimpleNamespace(message="DBConnectionTimeout")],
        retrieved_runbook_chunks=[],
        similar_incidents=[],
    )


def _empty_diagnosis() -> StructuredDiagnosis:
    return StructuredDiagnosis(
        diagnosis_summary="ok",
        root_cause_hypotheses=[],
        impact_scope="",
        structured_suggested_actions=[],
    )


# ── 降级元数据（factory） ─────────────────────────────────────────────────────


class _BoomPrimary:
    provider_name = "openai_compatible"
    model = "test-model"

    def diagnose(self, **kwargs):
        raise ConnectionError("dial refused")


class _OKPrimary:
    provider_name = "openai_compatible"
    model = "test-model"

    def diagnose(self, **kwargs):
        return DiagnosisResult(
            diagnosis=_empty_diagnosis(),
            provider="openai_compatible",
            requested_provider="openai_compatible",
        )


def test_fallback_client_records_fallback_metadata():
    result = FallbackLLMClient(primary=_BoomPrimary()).diagnose(**_diagnose_kwargs())
    assert result.provider == "mock_fallback"
    assert result.requested_provider == "openai_compatible"
    assert result.model == "test-model"
    assert "ConnectionError" in result.fallback_reason
    assert "dial refused" in result.fallback_reason
    assert result.duration_ms is not None and result.duration_ms >= 0


def test_fallback_client_passes_through_success():
    result = FallbackLLMClient(primary=_OKPrimary()).diagnose(**_diagnose_kwargs())
    assert result.provider == "openai_compatible"
    assert result.fallback_reason is None


def test_bad_config_fallback_records_reason(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "")  # 缺 key → 客户端构造失败
    client = get_llm_client()
    result = client.diagnose(**_diagnose_kwargs())
    assert result.provider == "mock_fallback"
    assert result.requested_provider == "openai_compatible"
    assert "ValueError" in result.fallback_reason


# ── OpenAI 客户端元数据 ───────────────────────────────────────────────────────


def test_openai_client_records_model_usage_duration():
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(
                    _empty_diagnosis().model_dump()
                )}}],
                "model": "served-model",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    client = OpenAICompatibleClient(
        api_key="k",
        base_url="http://x",
        model="asked-model",
        http_client=httpx.Client(
            base_url="http://x", transport=httpx.MockTransport(handle)
        ),
    )
    result = client.diagnose(**_diagnose_kwargs())
    assert result.provider == "openai_compatible"
    assert result.model == "served-model"
    assert result.token_usage == {"prompt_tokens": 10, "completion_tokens": 5}
    assert result.duration_ms is not None and result.duration_ms >= 0


# ── 计时隔离（embedding_service + 检索器） ────────────────────────────────────


def test_two_stage_timing_sink_reset_on_early_return(monkeypatch):
    monkeypatch.setattr(es, "get_cross_encoder", lambda: None)
    sink = {"coarse_ms": 999, "reranker": "cross-encoder", "rerank_ms": 42,
            "coarse_candidates": 7}  # 上一次检索的残留
    two_stage_retrieve(
        query="q", documents=["a", "b", "c"], coarse_top_k=10, fine_top_k=3,
        coarse_ranker=TfidfEmbedder(), timing=sink,
    )
    assert sink["reranker"] == "none"  # 提前返回也刷新，不残留旧重排信息
    assert "rerank_ms" not in sink
    assert sink["coarse_ms"] >= 0
    assert sink["coarse_candidates"] == 3


def test_two_stage_timing_sink_records_rerank(monkeypatch):
    class _FakeReranker:
        name = "cross-encoder"

        def rerank(self, query, documents, top_k):
            return [(index, 0.9) for index in range(top_k)]

    monkeypatch.setattr(es, "get_cross_encoder", lambda: _FakeReranker())
    sink: dict = {}
    two_stage_retrieve(
        query="q", documents=[f"d{i}" for i in range(8)], coarse_top_k=10,
        fine_top_k=2, coarse_ranker=TfidfEmbedder(), timing=sink,
    )
    assert sink["reranker"] == "cross-encoder"
    assert sink["rerank_ms"] >= 0


def test_retriever_timing_isolated_per_instance():
    chunks = [
        RunbookChunk(
            chunk_id=f"c{i}", source="s", title=f"t{i}",
            content=f"database connection failed {i}",
            issue_type="database_issue", chunk_type="body", strategy="markdown",
        )
        for i in range(3)
    ]
    first = RunbookRetriever(chunks=chunks, retrieval_mode="tfidf")
    first.retrieve(
        incident_title="db down", service_name="svc",
        evidence_logs=[SimpleNamespace(message="database refused")],
        issue_type="database_issue",
    )
    assert first._last_timing.get("coarse_ms") is not None
    assert "coarse=" in first.retrieval_detail

    second = RunbookRetriever(chunks=chunks, retrieval_mode="tfidf")
    assert second._last_timing == {}  # 新实例不残留上一次分析的计时
    assert "coarse=" not in second.retrieval_detail


# ── Trace 与执行一致 ──────────────────────────────────────────────────────────


def _trace_session() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _pipeline_trace_details(pipeline_meta, diagnosis_result):
    session = _trace_session()
    analysis_service._persist_pipeline_trace(
        session, 1,
        logs=[],
        detection=SimpleNamespace(
            issue_type="database_issue", confidence=0.8,
            matched_issues=["database_issue"], candidate_scores={},
            matched_signals=[], evidence_logs=[],
        ),
        diagnosis_plan=SimpleNamespace(
            tool_steps=["retrieve_runbooks", "retrieve_similar_incidents"]
        ),
        retrieved_runbook_chunks=[],
        similar_incidents=[],
        diagnosis_result=diagnosis_result,
        runbook_retriever=SimpleNamespace(
            retrieval_detail="retrieval_mode=tfidf; effective_retrieval_mode=tfidf coarse=3ms; candidates=10"
        ),
        similar_incident_retriever=SimpleNamespace(
            retrieval_detail="retrieval_mode=tfidf; effective_retrieval_mode=tfidf coarse=2ms; candidates=10"
        ),
        pipeline_meta=pipeline_meta,
        mode_decision=SimpleNamespace(mode="pipeline", reason="auto"),
    )
    session.commit()
    return {trace.step_name: trace.detail for trace in session.query(AnalysisTrace).all()}


def test_trace_records_actual_queries_and_rewrite_provider():
    pipeline_meta = {
        "rewritten": RewrittenQueries(
            original="orig", variants=["var one", "var two"], provider="template"
        ),
        "queries_used": {
            "runbook": ["actual runbook query text"],
            "similar_incidents": ["actual incident query text"],
        },
    }
    details = _pipeline_trace_details(
        pipeline_meta,
        DiagnosisResult(diagnosis=_empty_diagnosis(), provider="mock"),
    )
    assert "provider=template" in details["query_rewriting"]
    assert "var one" in details["query_rewriting"]
    assert "var two" in details["query_rewriting"]
    assert "(original)" not in details["query_rewriting"]  # 旧占位符不再出现
    assert "actual runbook query text" in details["vector_runbook_retrieval"]
    assert "actual incident query text" in details["similar_incident_retrieval"]


def test_trace_summary_shows_fallback_metadata():
    pipeline_meta = {
        "rewritten": RewrittenQueries(original="o", variants=["v"], provider="template"),
        "queries_used": {"runbook": [], "similar_incidents": []},
    }
    details = _pipeline_trace_details(
        pipeline_meta,
        DiagnosisResult(
            diagnosis=_empty_diagnosis(),
            provider="mock_fallback",
            requested_provider="openai_compatible",
            model="m",
            fallback_reason="ConnectError: down",
            duration_ms=12,
            token_usage={"total_tokens": 7},
        ),
    )
    summary = details["summary_generation"]
    assert "provider=mock_fallback" in summary
    assert "requested=openai_compatible" in summary
    assert "model=m" in summary
    assert "fallback_reason=ConnectError: down" in summary
    assert "duration=12ms" in summary
    assert "usage={'total_tokens': 7}" in summary


# ── _run_pipeline 的查询实录 ──────────────────────────────────────────────────


def _pipeline_inputs(chunks, incidents, evidence_messages):
    detection = SimpleNamespace(
        issue_type="database_issue", severity="high",
        evidence_logs=[SimpleNamespace(message=m) for m in evidence_messages],
    )
    return (
        SimpleNamespace(title="db down"),
        "svc",
        detection,
        SimpleNamespace(tool_steps=["retrieve_runbooks", "retrieve_similar_incidents"]),
    )


def _three_chunks():
    return [
        RunbookChunk(
            chunk_id=f"c{i}", source="s", title=f"t{i}",
            content=f"database connection failed {i}",
            issue_type="database_issue", chunk_type="body", strategy="markdown",
        )
        for i in range(3)
    ]


def _one_incident():
    return [
        HistoricalIncident(
            historical_id="h1", title="db outage", service_name="svc",
            issue_type="database_issue", symptoms=["db down"],
            root_cause="r", resolution="res", tags=["db"],
        )
    ]


def test_run_pipeline_multiquery_records_variants_as_queries():
    incident, service_name, detection, plan = _pipeline_inputs(
        _three_chunks(), _one_incident(), ["database connection refused"]
    )
    _, _, _, _, meta = analysis_service._run_pipeline(
        incident=incident, service_name=service_name, detection=detection,
        logs=[], runbook_retriever=RunbookRetriever(chunks=_three_chunks(), retrieval_mode="tfidf"),
        similar_incident_retriever=SimilarIncidentRetriever(incidents=_one_incident(), retrieval_mode="tfidf"),
        diagnosis_plan=plan, features={},
    )
    assert meta["rewritten"].provider == "template"
    assert len(meta["rewritten"].variants) > 1  # 多查询路径
    assert meta["queries_used"]["runbook"] == meta["rewritten"].variants
    assert meta["queries_used"]["similar_incidents"] == meta["rewritten"].variants


def test_run_pipeline_singlequery_records_exact_retriever_query(monkeypatch):
    incident, service_name, detection, plan = _pipeline_inputs(
        _three_chunks(), _one_incident(), ["database connection refused"]
    )
    single = RewrittenQueries(original="o", variants=["one-query"], provider="llm")
    monkeypatch.setattr(analysis_service, "rewrite_query",
                        lambda **kwargs: single)
    _, _, _, _, meta = analysis_service._run_pipeline(
        incident=incident, service_name=service_name, detection=detection,
        logs=[], runbook_retriever=RunbookRetriever(chunks=_three_chunks(), retrieval_mode="tfidf"),
        similar_incident_retriever=SimilarIncidentRetriever(incidents=_one_incident(), retrieval_mode="tfidf"),
        diagnosis_plan=plan, features={},
    )
    expected_runbook = build_runbook_query(
        incident_title="db down", service_name="svc",
        evidence_logs=detection.evidence_logs, issue_type="database_issue",
    )
    expected_incident = build_similar_incident_query(
        incident_title="db down", service_name="svc",
        issue_type="database_issue", evidence_logs=detection.evidence_logs,
    )
    assert meta["queries_used"]["runbook"] == [expected_runbook]
    assert meta["queries_used"]["similar_incidents"] == [expected_incident]
