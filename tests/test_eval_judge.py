"""F07 回归测试：Judge 调用失败不得静默，报告需显式统计。

覆盖：真实分析结果上 MockJudge 正常出分（旧的 .model_dump() 序列化 bug 不复现）；
judge 抛异常时状态为 failed 且错误脱敏后进报告；关闭 judge 时无 judge 输出。
"""

import importlib.util
import json
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


def _single_case_path(tmp_path: Path) -> Path:
    """取真实评测集里第一个 database_issue 案例，写成单案例评测集（只读，不改原文件）。"""
    cases = json.loads(EVAL_CASES_PATH.read_text(encoding="utf-8"))
    case = next(c for c in cases if c["expected_issue_type"] == "database_issue")
    path = tmp_path / "single_case.json"
    path.write_text(json.dumps([case]), encoding="utf-8")
    return path


def _isolated_env(monkeypatch):
    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    monkeypatch.delenv("RUNBOOK_EMBEDDING_BACKEND", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)


def test_judge_succeeds_on_real_analysis(tmp_path, monkeypatch):
    _isolated_env(monkeypatch)
    run_eval = _load_run_eval_module()

    report = run_eval.run_eval(
        cases_path=_single_case_path(tmp_path),
        report_path=tmp_path / "eval_report.md",
        enable_judge=True,
    )

    # 旧 bug 的症状：judge 全静默失败、无任何 judge_verdict。这里必须全成功。
    assert all(case["judge_status"] == "succeeded" for case in report["cases"])
    assert all(case["judge_verdict"]["provider"] == "mock" for case in report["cases"])
    assert report["metrics"]["judge_succeeded"] == 1
    assert report["metrics"]["judge_failed"] == 0
    assert report["metrics"]["judge_provider_mock"] == 1

    text = (tmp_path / "eval_report.md").read_text(encoding="utf-8")
    assert "judge_status: succeeded" in text
    assert "## LLM Judge Summary" in text
    assert "succeeded: 1" in text
    assert "failed: 0" in text


def test_judge_failure_is_reported_not_swallowed(tmp_path, monkeypatch):
    _isolated_env(monkeypatch)
    run_eval = _load_run_eval_module()

    class FailingJudge:
        def evaluate(self, **kwargs):
            raise RuntimeError(
                "judge boom https://api.example.com/v1 sk-abcdefghijklmnopqrstuvwxyz123456"
            )

    monkeypatch.setattr(run_eval, "get_judge", lambda: FailingJudge())

    report = run_eval.run_eval(
        cases_path=_single_case_path(tmp_path),
        report_path=tmp_path / "eval_report.md",
        enable_judge=True,
    )

    assert all(case["judge_status"] == "failed" for case in report["cases"])
    assert report["metrics"]["judge_failed"] == 1
    assert report["metrics"]["judge_succeeded"] == 0

    text = (tmp_path / "eval_report.md").read_text(encoding="utf-8")
    assert "judge_status: failed" in text
    assert "judge_error: RuntimeError: judge boom" in text
    assert "## LLM Judge Summary" in text
    assert "judge averages: n/a (no successful evaluations)" in text
    # 脱敏：URL 与长 token 不得原文进报告
    assert "https://api.example.com" not in text
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in text
    assert "<url>" in text


def test_desensitize_error_scrubs_urls_and_long_tokens():
    run_eval = _load_run_eval_module()

    text = run_eval._desensitize_error(
        ValueError("bad url https://example.com/x?key=abcdefghijklmnopqrstuvwxyz99999")
    )

    assert text.startswith("ValueError: bad url")
    assert "https://example.com" not in text
    assert "abcdefghijklmnopqrstuvwxyz99999" not in text


def test_judge_disabled_keeps_report_clean(tmp_path, monkeypatch):
    _isolated_env(monkeypatch)
    run_eval = _load_run_eval_module()

    report = run_eval.run_eval(
        cases_path=_single_case_path(tmp_path),
        report_path=tmp_path / "eval_report.md",
    )

    assert not report["judge_enabled"]
    assert not any(key.startswith("judge_") for key in report["metrics"])
    text = (tmp_path / "eval_report.md").read_text(encoding="utf-8")
    assert "LLM Judge: disabled" in text
    assert "judge_status" not in text
    assert "## LLM Judge Summary" not in text
