"""R05 收尾（2026-09-12 独立复核 P1/P2）：CLI 指标打印崩溃与自定义数据集指纹。

- CLI 入口（P1）：新增的 provider_distribution（字典）与整数计数不再被误按
  百分比格式化，main() 正常退出、退出码为 0；
- 自定义 cases_path（P2）：报告必须记录实际数据集的文件名与内容指纹，
  不能写成默认集 eval_cases.json；
- token 口径：total_tokens 是部分统计（仅最终诊断调用），覆盖数必须可查。
"""

import json
import sys

from eval import run_eval as run_eval_module
from eval.run_eval import DEFAULT_CASES_PATH, _sha256_file


def _fake_report() -> dict:
    return {
        "retrieval_mode": "tfidf",
        "judge_enabled": False,
        "total_cases": 3,
        "metrics": {
            "issue_type_accuracy": 1.0,
            "failed_case_count": 1,
            "average_latency_ms": 12.34,
            "insufficient_evidence_count": 1,
            "citation_downgraded_case_count": 1,
            "citation_warning_total": 3,
            "total_tokens": 150,
            "token_usage_covered_case_count": 2,
            "provider_distribution": {"mock": 2, "insufficient_evidence": 1},
        },
    }


# ── P1：CLI 入口不得崩溃，字典/整数按类型格式化 ─────────────────────────

def test_main_cli_prints_metrics_without_crash(monkeypatch, capsys):
    monkeypatch.setattr(run_eval_module, "run_eval", lambda **kwargs: _fake_report())
    monkeypatch.setattr(sys, "argv", ["run_eval.py"])

    run_eval_module.main()  # 旧代码在这里抛 TypeError，测试失败即崩溃复现

    out = capsys.readouterr().out
    assert "Evaluated 3 cases" in out
    assert "provider_distribution: insufficient_evidence=1, mock=2" in out
    assert "total_tokens: 150" in out
    assert "failed_case_count: 1" in out
    assert "insufficient_evidence_count: 1" in out
    assert "average_latency_ms: 12.34" in out
    # 整数计数不得带百分号
    assert "150.00%" not in out


def test_main_cli_judge_metrics_deferred_to_report(monkeypatch, capsys):
    report = _fake_report()
    report["judge_enabled"] = True
    report["metrics"]["judge_requested"] = 3
    report["metrics"]["judge_succeeded"] = 3
    report["metrics"]["judge_hallucination_rate"] = 0.0
    monkeypatch.setattr(run_eval_module, "run_eval", lambda **kwargs: report)
    monkeypatch.setattr(sys, "argv", ["run_eval.py"])

    run_eval_module.main()

    out = capsys.readouterr().out
    assert "judge: enabled" in out
    # 完整 judge 指标只在报告 LLM Judge Summary（R05 措辞），命令行只报概览
    assert "judge_hallucination_rate" not in out


# ── P2：自定义数据集必须记录自己的文件名与指纹 ───────────────────────────

def test_custom_cases_path_records_own_name_and_fingerprint(tmp_path):
    dataset = json.loads(DEFAULT_CASES_PATH.read_text(encoding="utf-8"))
    custom = dataset[:1]
    custom[0]["case_id"] = "custom-case-20260912"
    cases_path = tmp_path / "custom_cases_20260912.json"
    cases_path.write_text(json.dumps(custom, ensure_ascii=False), encoding="utf-8")
    report_path = tmp_path / "report.md"

    report = run_eval_module.run_eval(cases_path=cases_path, report_path=report_path)

    assert report["total_cases"] == 1
    environment = report["environment"]
    assert environment["dataset_name"] == cases_path.name
    assert environment["dataset_sha256"] == _sha256_file(cases_path)
    assert environment["dataset_sha256"] != _sha256_file(DEFAULT_CASES_PATH)

    text = report_path.read_text(encoding="utf-8")
    assert f"dataset: {cases_path.name} sha256={environment['dataset_sha256']}" in text
    assert "custom-case-20260912" in text


# ── token 口径：部分统计与覆盖数 ─────────────────────────────────────────

def test_aggregate_metrics_reports_token_coverage():
    # 按字段语义构造最小结果（_aggregate_metrics 只读所需键）
    full_results = [
        {
            "issue_type_match": True, "severity_match": True,
            "evidence_recall": 1.0, "runbook_retrieval_recall": 1.0,
            "runbook_top1_correct": True, "runbook_precision_at_3": 1.0,
            "similar_incident_retrieval_recall": 1.0,
            "similar_incident_top1_correct": True,
            "similar_incident_precision_at_3": 1.0,
            "latency_ms": 10.0, "passed": True,
            "provider": "mock", "citation_warnings": 0,
            "token_usage_total": token,
        }
        for token in (100, 50, None)
    ]
    metrics = run_eval_module._aggregate_metrics(full_results)

    assert metrics["total_tokens"] == 150
    assert metrics["token_usage_covered_case_count"] == 2
