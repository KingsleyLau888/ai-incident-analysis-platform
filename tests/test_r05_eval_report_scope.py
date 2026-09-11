"""R05（2026-09-11 复核）：评测口径自证与措辞。

- 报告必须写明数据集/语料指纹与模型配置（换数据/语料后旧报告不能冒充新评测）；
- provider 分布/弃答数/引用降级数/token 成本进入指标与逐案例实录；
- 裁判幻觉标记必须报"标记数/样本数"，不得写成"幻觉率 0%"这种绝对结论。
"""

from pathlib import Path

from eval.run_eval import _aggregate_metrics, _summary_metadata, write_report


class _FakeTrace:
    def __init__(self, step_name: str, detail: str):
        self.step_name = step_name
        self.detail = detail


class _FakeAnalysis:
    def __init__(self, traces: list[_FakeTrace]):
        self.traces = traces


def _fake_result(**overrides) -> dict:
    result = {
        "issue_type_match": True,
        "severity_match": True,
        "evidence_recall": 1.0,
        "runbook_retrieval_recall": 1.0,
        "runbook_top1_correct": True,
        "runbook_precision_at_3": 1.0,
        "similar_incident_retrieval_recall": 1.0,
        "similar_incident_top1_correct": True,
        "similar_incident_precision_at_3": 1.0,
        "latency_ms": 100.0,
        "passed": True,
        "failure_categories": [],
        "provider": "mock",
        "citation_warnings": 0,
        "token_usage_total": None,
    }
    result.update(overrides)
    return result


def _fake_case(**overrides) -> dict:
    case = {
        "case_id": "case-x",
        "expected_issue_type": "database_issue",
        "actual_issue_type": "database_issue",
        "expected_severity": "high",
        "actual_severity": "high",
        "expected_runbook_sources": ["database_issue.md"],
        "actual_runbook_sources": ["database_issue.md"],
        "expected_similar_issue_types": ["database_issue"],
        "actual_similar_issue_types": ["database_issue"],
        "runbook_effective_retrieval_mode": "tfidf",
        "similar_effective_retrieval_mode": "tfidf",
        "evidence_recall": 1.0,
        "runbook_retrieval_recall": 1.0,
        "runbook_top1_correct": True,
        "runbook_precision_at_3": 1.0,
        "similar_incident_retrieval_recall": 1.0,
        "similar_incident_top1_correct": True,
        "similar_incident_precision_at_3": 1.0,
        "latency_ms": 100.0,
        "passed": True,
        "failure_categories": [],
        "provider": "mock",
        "citation_warnings": 0,
        "token_usage_total": 12,
    }
    case.update(overrides)
    return case


# ── Trace 元数据解析 ─────────────────────────────────────────────────────

def test_summary_metadata_parses_provider_usage_and_citations():
    analysis = _FakeAnalysis(
        [
            _FakeTrace("log_filtering", "irrelevant"),
            _FakeTrace(
                "summary_generation",
                "provider=openai_compatible; model=deepseek-chat; "
                "usage={'prompt_tokens': 500, 'completion_tokens': 100, "
                "'total_tokens': 600}; citation_warnings=2: fake citation [E99]",
            ),
        ]
    )
    metadata = _summary_metadata(analysis)
    assert metadata["provider"] == "openai_compatible"
    assert metadata["total_tokens"] == 600
    assert metadata["citation_warnings"] == 2


def test_summary_metadata_defaults_when_trace_missing():
    analysis = _FakeAnalysis([_FakeTrace("log_filtering", "nothing")])
    metadata = _summary_metadata(analysis)
    assert metadata == {
        "provider": "unknown",
        "requested_provider": None,
        "total_tokens": None,
        "citation_warnings": 0,
    }


# ── 指标聚合：弃答/引用降级/token/后端分布 ───────────────────────────────

def test_aggregate_metrics_counts_insufficient_citations_and_tokens():
    results = [
        _fake_result(provider="insufficient_evidence", passed=True),
        _fake_result(provider="mock", citation_warnings=3, token_usage_total=100),
        _fake_result(provider="mock", citation_warnings=1, token_usage_total=50),
    ]
    metrics = _aggregate_metrics(results)
    assert metrics["insufficient_evidence_count"] == 1
    assert metrics["citation_downgraded_case_count"] == 2
    assert metrics["citation_warning_total"] == 4
    assert metrics["total_tokens"] == 150
    # R05 收尾：覆盖数区分"确实为零"与"未统计"（部分统计口径）
    assert metrics["token_usage_covered_case_count"] == 2
    assert metrics["provider_distribution"] == {"insufficient_evidence": 1, "mock": 2}


# ── 报告正文：环境自证 + 新指标 + 逐案例实录 ─────────────────────────────

def test_write_report_includes_environment_and_new_metrics(tmp_path):
    report = {
        "retrieval_mode": "tfidf",
        "effective_retrieval_modes": ["tfidf"],
        "judge_enabled": False,
        "total_cases": 2,
        "metrics": {
            "issue_type_accuracy": 1.0,
            "failed_case_count": 0,
            "average_latency_ms": 100.0,
            "insufficient_evidence_count": 1,
            "citation_downgraded_case_count": 1,
            "citation_warning_total": 3,
            "total_tokens": 123,
            "token_usage_covered_case_count": 2,
            "provider_distribution": {"mock": 2},
        },
        "cases": [
            _fake_case(),
            _fake_case(
                case_id="case-warned",
                provider="mock",
                citation_warnings=3,
                token_usage_total=111,
            ),
        ],
        "failed_cases": [],
        "environment": {
            "dataset_sha256": "aaaabbbbccccdddd",
            "runbook_corpus_sha256": "eeeeffff11112222",
            "historical_incidents_sha256": "99990000aaaabbbb",
            "llm_provider_env": "mock",
            "llm_model_env": None,
            "cross_encoder_enabled_env": "0",
        },
    }
    path = tmp_path / "r05-report.md"
    write_report(report, path)
    text = path.read_text(encoding="utf-8")

    assert "Evaluation Environment" in text
    assert "dataset: eval_cases.json sha256=aaaabbbbccccdddd" in text
    assert "runbook corpus: runbooks/ sha256=eeeeffff11112222" in text
    assert "LLM provider (env): mock / model: unset" in text
    assert "insufficient_evidence_count: 1" in text
    assert "citation_downgraded_case_count: 1" in text
    assert "total_tokens: 123" in text
    # R05 收尾：token 只统计最终诊断调用，报告必须写明"部分统计"口径
    assert "仅统计最终诊断调用回传的 usage" in text
    assert "覆盖 2/2 个案例" in text
    assert "provider_distribution: mock=2" in text
    # 逐案例实录：引用降级与 token 成本
    assert "citation_warnings: 3" in text
    assert "token_usage_total: 111" in text


# ── 裁判措辞：不得写成"幻觉率 0%"这种绝对结论 ───────────────────────────

def test_judge_summary_wording_never_claims_zero_hallucination(tmp_path):
    report = {
        "retrieval_mode": "tfidf",
        "effective_retrieval_modes": ["tfidf"],
        "judge_enabled": True,
        "total_cases": 27,
        "metrics": {
            "issue_type_accuracy": 1.0,
            "failed_case_count": 0,
            "average_latency_ms": 100.0,
            "judge_requested": 27,
            "judge_attempted": 27,
            "judge_succeeded": 27,
            "judge_failed": 0,
            "judge_skipped": 0,
            "judge_provider_mock": 0,
            "judge_provider_llm": 27,
            "judge_diagnosis_coherence": 0.9,
            "judge_evidence_grounding": 0.88,
            "judge_hallucination_rate": 0.0,
            "judge_flagged_hallucination_count": 0,
            "judge_actionability": 0.76,
        },
        "cases": [_fake_case() for _ in range(27)],
        "failed_cases": [],
        "environment": {},
    }
    path = tmp_path / "r05-judge.md"
    write_report(report, path)
    text = path.read_text(encoding="utf-8")

    assert "judge_flagged_hallucination_count: 0 / 27" in text
    assert "未检出不等于幻觉率为 0" in text
    assert "hallucination_rate: 0.00%" not in text
