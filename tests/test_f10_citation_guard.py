"""F10 引用护栏与弃答回归测试。

覆盖：
- valid_reference_ids / verify_and_downgrade：伪引用与无引用条目标注
  [UNVERIFIED] 并封顶置信度，真实引用原样保留，警告逐条记录；
- OpenAICompatibleClient：全空输入弃答（不发 API 调用）、提示词带稳定
  引用 ID、伪造引用降级进 citation_warnings、真实引用无警告；
- 裁判：build_judge_user_prompt 携带开卷资料；MockJudge 只存在于参考
  资料中的名称不判幻觉；run_eval 把检索资料传给 judge；
- 查询改写：默认模板改写（真模型在线也不启用 LLM 改写）。
"""

import importlib.util
import json
from pathlib import Path

import httpx

from app.llm.base import RootCauseHypothesis, StructuredDiagnosis
from app.llm.citation_guard import (
    UNVERIFIED_CONFIDENCE_CAP,
    valid_reference_ids,
    verify_and_downgrade,
)
from app.llm.openai_compatible_client import OpenAICompatibleClient
from app.services.llm_judge import MockJudge, build_judge_user_prompt
from app.services.query_rewriter import (
    effective_rewrite_provider,
    rewrite_query,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_EVAL_PATH = PROJECT_ROOT / "eval" / "run_eval.py"
EVAL_CASES_PATH = PROJECT_ROOT / "eval" / "eval_cases.json"


class _Log:
    def __init__(self, message: str) -> None:
        self.message = message


def _diagnosis(hypotheses: list[RootCauseHypothesis]) -> StructuredDiagnosis:
    return StructuredDiagnosis(
        diagnosis_summary="summary",
        root_cause_hypotheses=hypotheses,
        impact_scope="svc",
        structured_suggested_actions=["check"],
    )


def _hypothesis(evidence: list[str], confidence: float = 0.8) -> RootCauseHypothesis:
    return RootCauseHypothesis(
        cause="cause", confidence=confidence, supporting_evidence=evidence
    )


def _llm_client(handler) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        api_key="test-key",
        base_url="http://llm.test/v1",
        model="test-model",
        http_client=httpx.Client(
            base_url="http://llm.test/v1", transport=httpx.MockTransport(handler)
        ),
    )


# ── 引用 ID 集合 ─────────────────────────────────────────────────────

def test_valid_reference_ids_only_includes_existing_materials():
    ids = valid_reference_ids(
        evidence_count=2, notes_count=1, runbook_count=1, similar_count=3
    )
    assert ids == {"E1", "E2", "N1", "R1", "S1", "S2", "S3"}
    assert "E3" not in ids
    assert "R2" not in ids


# ── verify_and_downgrade ─────────────────────────────────────────────

def test_verify_keeps_valid_citations_untouched():
    diagnosis = _diagnosis([_hypothesis(["[E1] timeout log", "[R2] runbook step"])])
    cleaned, warnings = verify_and_downgrade(
        diagnosis, evidence_count=1, runbook_count=2
    )
    assert warnings == []
    hypothesis = cleaned.root_cause_hypotheses[0]
    assert hypothesis.supporting_evidence == ["[E1] timeout log", "[R2] runbook step"]
    assert hypothesis.confidence == 0.8


def test_verify_flags_unknown_citation_and_caps_confidence():
    diagnosis = _diagnosis([_hypothesis(["[E1] real", "[E9] invented log"])])
    cleaned, warnings = verify_and_downgrade(diagnosis, evidence_count=2)

    hypothesis = cleaned.root_cause_hypotheses[0]
    assert "[E1] real" in hypothesis.supporting_evidence  # 真实引用原样保留
    assert any("[UNVERIFIED]" in entry for entry in hypothesis.supporting_evidence)
    assert hypothesis.confidence <= UNVERIFIED_CONFIDENCE_CAP
    assert any("unknown id E9" in warning for warning in warnings)


def test_verify_flags_entry_without_any_citation():
    diagnosis = _diagnosis([_hypothesis(["free text without id"])])
    cleaned, warnings = verify_and_downgrade(diagnosis, evidence_count=3)

    hypothesis = cleaned.root_cause_hypotheses[0]
    assert hypothesis.supporting_evidence == ["[UNVERIFIED] free text without id"]
    assert hypothesis.confidence <= UNVERIFIED_CONFIDENCE_CAP
    assert any("no citation id" in warning for warning in warnings)


def test_verify_handles_empty_materials_and_hypotheses():
    diagnosis = _diagnosis([])
    cleaned, warnings = verify_and_downgrade(diagnosis, evidence_count=0)
    assert cleaned.root_cause_hypotheses == []
    assert warnings == []


# ── 客户端弃答 ───────────────────────────────────────────────────────

def test_client_abstains_when_all_inputs_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("API must not be called when abstaining")

    client = _llm_client(handler)
    result = client.diagnose(
        incident_title="t",
        service_name="s",
        issue_type="unknown",
        severity="low",
        evidence_logs=[],
        retrieved_runbook_chunks=[],
        similar_incidents=[],
    )

    assert result.provider == "insufficient_evidence"
    assert result.requested_provider == "openai_compatible"
    assert result.token_usage is None
    assert result.diagnosis.root_cause_hypotheses == []
    assert "Insufficient evidence" in result.diagnosis.diagnosis_summary


def test_client_does_not_abstain_when_notes_exist():
    # 弃答门槛是"全部为空"：调查笔记是派生观察，有笔记仍可诊断（引用护栏兜底）
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["called"] = True
        content = {
            "diagnosis_summary": "ok",
            "root_cause_hypotheses": [
                {
                    "cause": "c",
                    "confidence": 0.8,
                    "supporting_evidence": ["[N1] timeline built"],
                }
            ],
            "impact_scope": "svc",
            "structured_suggested_actions": ["check"],
        }
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(content)}}]}
        )

    client = _llm_client(handler)
    result = client.diagnose(
        incident_title="t",
        service_name="s",
        issue_type="unknown",
        severity="low",
        evidence_logs=[],
        retrieved_runbook_chunks=[],
        similar_incidents=[],
        investigation_notes=["Timeline built from logs."],
    )
    assert captured.get("called")
    assert result.provider == "openai_compatible"
    assert result.citation_warnings is None


def test_client_does_not_abstain_when_evidence_exists():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["called"] = True
        content = {
            "diagnosis_summary": "ok",
            "root_cause_hypotheses": [
                {
                    "cause": "c",
                    "confidence": 0.8,
                    "supporting_evidence": ["[E1] timeout"],
                }
            ],
            "impact_scope": "svc",
            "structured_suggested_actions": ["check"],
        }
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(content)}}]}
        )

    client = _llm_client(handler)
    result = client.diagnose(
        incident_title="t",
        service_name="s",
        issue_type="timeout_issue",
        severity="high",
        evidence_logs=[_Log("request timed out")],
        retrieved_runbook_chunks=[],
        similar_incidents=[],
    )
    assert captured.get("called")
    assert result.provider == "openai_compatible"


# ── 提示词引用 ID ────────────────────────────────────────────────────

def test_prompt_assigns_stable_ids_to_all_materials():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        content = {
            "diagnosis_summary": "ok",
            "root_cause_hypotheses": [],
            "impact_scope": "",
            "structured_suggested_actions": [],
        }
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(content)}}]}
        )

    client = _llm_client(handler)
    client.diagnose(
        incident_title="t",
        service_name="s",
        issue_type="database_issue",
        severity="high",
        evidence_logs=[_Log("timeout")],
        retrieved_runbook_chunks=[],
        similar_incidents=[],
        investigation_notes=["note one"],
    )
    user = json.loads(captured["messages"][1]["content"])
    assert user["evidence_logs"] == ["[E1] timeout"]
    assert user["investigation_notes"] == ["[N1] note one"]
    assert "MUST begin with reference IDs" in json.dumps(user["output_schema"])
    assert "missing_information" in user["output_schema"]


# ── 客户端引用校验落进结果元数据 ────────────────────────────────────

def test_fabricated_citation_downgraded_and_recorded_in_warnings():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        content = {
            "diagnosis_summary": "ok",
            "root_cause_hypotheses": [
                {
                    "cause": "c",
                    "confidence": 0.9,
                    "supporting_evidence": ["[E3] fabricated log line"],
                }
            ],
            "impact_scope": "svc",
            "structured_suggested_actions": ["check"],
        }
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(content)}}]}
        )

    client = _llm_client(handler)
    result = client.diagnose(
        incident_title="t",
        service_name="s",
        issue_type="database_issue",
        severity="high",
        evidence_logs=[_Log("timeout")],
        retrieved_runbook_chunks=[],
        similar_incidents=[],
    )

    hypothesis = result.diagnosis.root_cause_hypotheses[0]
    assert hypothesis.confidence <= UNVERIFIED_CONFIDENCE_CAP
    assert any("[UNVERIFIED]" in entry for entry in hypothesis.supporting_evidence)
    assert result.citation_warnings and any(
        "unknown id E3" in warning for warning in result.citation_warnings
    )


def test_valid_citations_produce_no_warnings():
    def handler(request: httpx.Request) -> httpx.Response:
        content = {
            "diagnosis_summary": "ok",
            "root_cause_hypotheses": [
                {
                    "cause": "c",
                    "confidence": 0.8,
                    "supporting_evidence": ["[E1] timeout"],
                }
            ],
            "impact_scope": "svc",
            "structured_suggested_actions": ["check"],
        }
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(content)}}]}
        )

    client = _llm_client(handler)
    result = client.diagnose(
        incident_title="t",
        service_name="s",
        issue_type="database_issue",
        severity="high",
        evidence_logs=[_Log("timeout")],
        retrieved_runbook_chunks=[],
        similar_incidents=[],
    )
    assert result.provider == "openai_compatible"
    assert result.citation_warnings is None


# ── 裁判开卷资料 ─────────────────────────────────────────────────────

def test_judge_prompt_includes_reference_materials():
    prompt = build_judge_user_prompt(
        incident_title="t",
        service_name="s",
        issue_type="database_issue",
        severity="high",
        evidence_messages=["timeout"],
        diagnosis_summary="sum",
        root_cause_hypotheses=[],
        suggested_actions=[],
        impact_scope="",
        retrieved_runbook_chunks=[{"source": "postgres_primary_unavailable.md"}],
        similar_incidents=[{"historical_id": "HIST-TIMEOUT-001"}],
    )
    payload = json.loads(prompt)
    materials = payload["reference_materials"]
    assert materials["retrieved_runbook_chunks"][0]["source"] == "postgres_primary_unavailable.md"
    assert materials["similar_incidents"][0]["historical_id"] == "HIST-TIMEOUT-001"


def test_mock_judge_does_not_flag_names_only_in_reference_materials():
    verdict = MockJudge().evaluate(
        incident_title="t",
        service_name="s",
        issue_type="database_issue",
        severity="high",
        evidence_messages=["connection refused"],
        diagnosis_summary="Root cause matches DatabaseClusterOverload incident.",
        root_cause_hypotheses=[],
        suggested_actions=[],
        impact_scope="",
        retrieved_runbook_chunks=[],
        similar_incidents=[{"historical_id": "h1", "title": "DatabaseClusterOverload"}],
    )
    assert verdict.hallucination_flag is False


def test_mock_judge_still_flags_names_absent_everywhere():
    verdict = MockJudge().evaluate(
        incident_title="t",
        service_name="s",
        issue_type="database_issue",
        severity="high",
        evidence_messages=["connection refused"],
        diagnosis_summary="Root cause matches DatabaseClusterOverload incident.",
        root_cause_hypotheses=[],
        suggested_actions=[],
        impact_scope="",
    )
    assert verdict.hallucination_flag is True


def test_run_eval_passes_retrieval_context_to_judge(tmp_path, monkeypatch):
    def _load_run_eval_module():
        spec = importlib.util.spec_from_file_location("run_eval", RUN_EVAL_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    monkeypatch.delenv("RETRIEVAL_MODE", raising=False)
    monkeypatch.delenv("RUNBOOK_EMBEDDING_BACKEND", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    received = {}

    class CapturingJudge:
        def evaluate(self, **kwargs):
            received.update(kwargs)

    run_eval = _load_run_eval_module()
    monkeypatch.setattr(run_eval, "get_judge", lambda: CapturingJudge())

    cases = json.loads(EVAL_CASES_PATH.read_text(encoding="utf-8"))
    case = next(c for c in cases if c["expected_issue_type"] == "database_issue")
    path = tmp_path / "single_case.json"
    path.write_text(json.dumps([case]), encoding="utf-8")

    run_eval.run_eval(
        cases_path=path,
        report_path=tmp_path / "eval_report.md",
        enable_judge=True,
    )

    # 检索到的开卷资料必须传给了裁判（裁判失明修复）
    assert received["retrieved_runbook_chunks"], "judge got no runbook context"
    assert received["similar_incidents"], "judge got no similar-incident context"


# ── 查询改写默认模板 ─────────────────────────────────────────────────

def test_rewrite_provider_defaults_to_template_even_with_real_llm(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.delenv("QUERY_REWRITE_PROVIDER", raising=False)
    assert effective_rewrite_provider() == "template"


def test_rewrite_query_skips_llm_by_default(monkeypatch):
    calls = []

    def fake_llm_rewrite(**kwargs):
        calls.append(kwargs)
        return ["fake variant"]

    monkeypatch.setattr(
        "app.services.query_rewriter._llm_rewrite", fake_llm_rewrite
    )
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.delenv("QUERY_REWRITE_PROVIDER", raising=False)

    result = rewrite_query(
        incident_title="t", service_name="s", issue_type="database_issue", evidence_text="e"
    )
    assert calls == []  # 未显式开启时绝不调用 LLM 改写
    assert result.provider == "template"


def test_rewrite_query_uses_llm_when_explicitly_enabled(monkeypatch):
    calls = []

    def fake_llm_rewrite(**kwargs):
        calls.append(kwargs)
        return ["fake variant"]

    monkeypatch.setattr(
        "app.services.query_rewriter._llm_rewrite", fake_llm_rewrite
    )
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("QUERY_REWRITE_PROVIDER", "llm")

    result = rewrite_query(
        incident_title="t", service_name="s", issue_type="database_issue", evidence_text="e"
    )
    assert calls, "QUERY_REWRITE_PROVIDER=llm 时必须调用 LLM 改写"
    assert result.provider == "llm"
    assert result.variants == ["fake variant"]


def test_rewrite_provider_llm_requires_configured_llm(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("QUERY_REWRITE_PROVIDER", "llm")
    assert effective_rewrite_provider() == "template"
