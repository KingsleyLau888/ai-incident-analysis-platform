import importlib.util
import sys
from pathlib import Path

from app.services import embedding_service


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_EVAL_PATH = PROJECT_ROOT / "eval" / "run_eval.py"
RAG_ABLATION_PATH = PROJECT_ROOT / "scripts" / "rag_ablation_benchmark.py"
EVAL_CASES_PATH = PROJECT_ROOT / "eval" / "eval_cases.json"


def _load_run_eval_module():
    spec = importlib.util.spec_from_file_location("run_eval", RUN_EVAL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_rag_ablation_module():
    spec = importlib.util.spec_from_file_location("rag_ablation_benchmark", RAG_ABLATION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["rag_ablation_benchmark"] = module
    spec.loader.exec_module(module)
    return module


def test_eval_cases_can_be_read():
    run_eval = _load_run_eval_module()

    cases = run_eval.load_eval_cases(EVAL_CASES_PATH)

    assert len(cases) >= 6
    assert all(case.case_id for case in cases)
    assert all(case.expected_issue_type for case in cases)


def test_run_eval_generates_metrics_and_report(tmp_path, monkeypatch):
    monkeypatch.delenv("RUNBOOK_EMBEDDING_BACKEND", raising=False)
    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    run_eval = _load_run_eval_module()
    report_path = tmp_path / "eval_report.md"

    report = run_eval.run_eval(
        cases_path=EVAL_CASES_PATH,
        report_path=report_path,
    )

    assert report["total_cases"] >= 6
    assert report["retrieval_mode"] == "tfidf"
    assert set(report["metrics"]) == {
        "issue_type_accuracy",
        "severity_accuracy",
        "evidence_recall",
        "runbook_retrieval_recall",
        "runbook_top1_accuracy",
        "runbook_precision_at_3",
        "similar_incident_retrieval_recall",
        "similar_incident_top1_accuracy",
        "similar_incident_precision_at_3",
        "failed_case_count",
        "average_latency_ms",
        # F12：弃答/引用降级/token 成本/后端分布（评测口径扩展）
        "insufficient_evidence_count",
        "citation_downgraded_case_count",
        "citation_warning_total",
        "total_tokens",
        # R05 收尾：token 覆盖数（区分部分统计与未统计）
        "token_usage_covered_case_count",
        "provider_distribution",
    }
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "Retrieval mode: tfidf" in report_text
    assert "## Metrics" in report_text
    assert "similar_incident_retrieval_recall" in report_text
    assert "## Error Analysis" in report_text
    assert report["metrics"]["failed_case_count"] > 0


def test_run_eval_accepts_retrieval_mode_parameter(tmp_path, monkeypatch):
    class BrokenSentenceTransformerEmbedder:
        def __init__(self) -> None:
            raise RuntimeError("model unavailable")

    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    monkeypatch.setattr(embedding_service, "SentenceTransformerEmbedder", BrokenSentenceTransformerEmbedder)
    run_eval = _load_run_eval_module()

    report = run_eval.run_eval(
        cases_path=EVAL_CASES_PATH,
        report_path=tmp_path / "eval_report.md",
        retrieval_mode="hybrid",
    )

    assert report["retrieval_mode"] == "hybrid"
    assert "average_latency_ms" in report["metrics"]
    assert "RETRIEVAL_MODE" not in __import__("os").environ


def test_empty_expected_runbooks_fails_when_actual_sources_exist():
    run_eval = _load_run_eval_module()

    recall = run_eval._source_recall([], ["database_issue.md"])

    assert recall == 0.0


def test_write_benchmark_report_generates_markdown(tmp_path):
    run_eval = _load_run_eval_module()
    path = tmp_path / "retrieval_benchmark_report.md"
    reports = {
        "tfidf": {
            "metrics": {
                "issue_type_accuracy": 0.8,
                "runbook_top1_accuracy": 0.5,
                "runbook_precision_at_3": 0.4,
                "similar_incident_top1_accuracy": 0.45,
                "similar_incident_precision_at_3": 0.5,
                "average_latency_ms": 10.0,
                "failed_case_count": 3,
            },
            "failed_cases": [{"case_id": "case-a"}],
        },
        "hybrid": {
            "metrics": {
                "issue_type_accuracy": 0.8,
                "runbook_top1_accuracy": 0.7,
                "runbook_precision_at_3": 0.6,
                "similar_incident_top1_accuracy": 0.55,
                "similar_incident_precision_at_3": 0.6,
                "average_latency_ms": 30.0,
                "failed_case_count": 2,
            },
            "failed_cases": [],
        },
    }

    run_eval.write_benchmark_report(reports, path)

    text = path.read_text(encoding="utf-8")
    assert "# Retrieval Benchmark Report" in text
    assert "| mode |" in text
    assert "Best runbook top-1 accuracy: hybrid" in text


def test_write_rag_ablation_report_generates_markdown(tmp_path):
    rag_ablation = _load_rag_ablation_module()
    path = tmp_path / "rag_ablation_report.md"
    reports = {
        "tfidf_single_query": {
            "effective_retrieval_mode": "tfidf",
            "multi_query": False,
            "metadata_filter": False,
            "runbook_top1_accuracy": 0.5,
            "runbook_precision_at_3": 0.4,
            "average_latency_ms": 10.0,
        },
        "chromadb_multi_query_metadata": {
            "effective_retrieval_mode": "chromadb",
            "multi_query": True,
            "metadata_filter": True,
            "runbook_top1_accuracy": 0.7,
            "runbook_precision_at_3": 0.6,
            "average_latency_ms": 20.0,
        },
    }

    rag_ablation.write_report(reports, path)

    text = path.read_text(encoding="utf-8")
    assert "# RAG Ablation Report" in text
    assert "chromadb_multi_query_metadata" in text
    assert "top1 delta +20.00%" in text
