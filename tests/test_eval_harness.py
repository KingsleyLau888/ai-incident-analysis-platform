import importlib.util
from pathlib import Path


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
    run_eval = _load_run_eval_module()
    report_path = tmp_path / "eval_report.md"

    report = run_eval.run_eval(
        cases_path=EVAL_CASES_PATH,
        report_path=report_path,
    )

    assert report["total_cases"] >= 6
    assert set(report["metrics"]) == {
        "issue_type_accuracy",
        "severity_accuracy",
        "evidence_recall",
        "runbook_retrieval_recall",
        "average_latency_ms",
    }
    assert report_path.exists()
    assert "## Metrics" in report_path.read_text(encoding="utf-8")


def test_empty_expected_runbooks_fails_when_actual_sources_exist():
    run_eval = _load_run_eval_module()

    recall = run_eval._source_recall([], ["database_issue.md"])

    assert recall == 0.0
