import importlib.util
from pathlib import Path

from app.services import embedding_service


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_EVAL_PATH = PROJECT_ROOT / "eval" / "run_eval.py"
EVAL_CASES_PATH = PROJECT_ROOT / "eval" / "eval_cases.json"


def _load_run_eval_module():
    spec = importlib.util.spec_from_file_location("run_eval", RUN_EVAL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
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
