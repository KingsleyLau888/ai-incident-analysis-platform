"""F05：Agent 取证前置条件（代码级门禁，不再只靠提示词）。

覆盖：零取证诊断被拒（insufficient_evidence）、未知动作报决策错误、
重复调用代码拒绝、参数强类型与限额、预算耗尽无证据时如实返回、
确定性工作流不受门禁影响。
"""

from app.agent.react_agent import ReActAgent
from app.models.log_entry import LogEntry


class _FakeAgentLLM:
    """按给定序列返回决策的假 LLM；序列耗尽后停在最后一项。"""

    def __init__(self, actions: list[dict]):
        self.actions = actions
        self.calls = 0

    def decide_action(self, system_prompt: str, user_prompt: str) -> dict:
        index = min(self.calls, len(self.actions) - 1)
        self.calls += 1
        return self.actions[index]


def _make_logs() -> list[LogEntry]:
    return [
        LogEntry(id=1, service_id=1, level="ERROR", message="DBConnectionTimeout mysql-primary"),
        LogEntry(id=2, service_id=1, level="ERROR", message="Payment request failed after retry"),
    ]


def _agent(llm=None, max_steps: int = 5) -> ReActAgent:
    return ReActAgent(llm_client=llm, max_steps=max_steps)


def _investigate(agent: ReActAgent, generate_diagnosis_fn=None):
    return agent.investigate(
        incident_title="Payment API errors",
        service_name="payment-service",
        search_logs_fn=lambda ctx: _make_logs(),
        detect_signals_fn=lambda ctx: {
            "issue_type": "database_issue",
            "severity": "high",
            "matched_issues": ["database_issue"],
            "evidence_logs": ctx.get("logs", _make_logs())[:1],
        },
        retrieve_runbooks_fn=lambda query, top_k, issue_type=None: [],
        retrieve_similar_incidents_fn=lambda query, top_k, issue_type=None: [],
        generate_diagnosis_fn=generate_diagnosis_fn or (lambda ctx: {"diagnosed": True}),
    )


def test_early_diagnosis_without_evidence_is_insufficient():
    llm = _FakeAgentLLM([{"thought": "skip", "action": "generate_diagnosis", "action_input": {}}])
    result = _investigate(_agent(llm=llm))
    assert result.insufficient_evidence is True
    assert result.final_diagnosis is None
    # 首步请求诊断 → 决策错误而不是出诊断；最后一步如实标注证据不足
    assert "Decision error" in result.steps[0].observation
    assert result.steps[-1].is_final is True
    assert "Insufficient evidence" in result.steps[-1].observation


def test_budget_exhausted_without_evidence_is_insufficient():
    # LLM 一直选无关工具，永远不满足取证前置 → 预算耗尽如实返回证据不足
    llm = _FakeAgentLLM(
        [{"thought": "t", "action": "compare_log_level_trend", "action_input": {}}]
    )
    result = _investigate(_agent(llm=llm, max_steps=3))
    assert result.insufficient_evidence is True
    assert result.final_diagnosis is None
    assert result.steps[-1].observation.startswith("Insufficient evidence")


def test_unknown_action_is_decision_error_and_investigation_continues():
    llm = _FakeAgentLLM(
        [
            {"thought": "try magic", "action": "do_magic", "action_input": {}},
            {"thought": "collect logs", "action": "search_logs", "action_input": {"service_name": "x"}},
            {"thought": "detect", "action": "detect_signals", "action_input": {}},
            {"thought": "done", "action": "generate_diagnosis", "action_input": {}},
        ]
    )
    result = _investigate(_agent(llm=llm))
    assert result.steps[0].observation.startswith("Decision error: unknown tool")
    # 未知动作不再静默转 generate_diagnosis：后续取证完成后正常出诊断
    assert result.insufficient_evidence is False
    assert result.final_diagnosis == {"diagnosed": True}


def test_duplicate_tool_call_is_rejected_by_code():
    llm = _FakeAgentLLM(
        [
            {"thought": "logs", "action": "search_logs", "action_input": {"service_name": "x"}},
            {"thought": "again", "action": "search_logs", "action_input": {"service_name": "x"}},
            {"thought": "detect", "action": "detect_signals", "action_input": {}},
            {"thought": "done", "action": "generate_diagnosis", "action_input": {}},
        ]
    )
    result = _investigate(_agent(llm=llm))
    assert "Rejected duplicate tool call" in result.steps[1].observation
    assert result.final_context["successful_tools"].count("search_logs") == 1
    assert result.insufficient_evidence is False


def test_invalid_tool_parameters_are_rejected_without_execution():
    llm = _FakeAgentLLM(
        [
            {"thought": "logs", "action": "search_logs", "action_input": {"service_name": "x"}},
            {"thought": "detect", "action": "detect_signals", "action_input": {}},
            {
                "thought": "runbooks",
                "action": "retrieve_runbooks",
                "action_input": {"query": "db timeout", "top_k": "abc"},
            },
            {
                "thought": "runbooks again",
                "action": "retrieve_runbooks",
                "action_input": {"query": "db timeout", "top_k": 999},
            },
            {"thought": "done", "action": "generate_diagnosis", "action_input": {}},
        ]
    )
    result = _investigate(_agent(llm=llm))
    assert "rejected invalid input" in result.steps[2].observation
    assert "rejected invalid input" in result.steps[3].observation
    assert "retrieve_runbooks" not in result.final_context["successful_tools"]
    assert result.insufficient_evidence is False
    assert result.final_diagnosis == {"diagnosed": True}


def test_deterministic_workflow_satisfies_evidence_gate():
    result = _investigate(_agent())
    assert result.provider == "react_deterministic"
    assert result.insufficient_evidence is False
    assert result.final_diagnosis == {"diagnosed": True}
    for required in ("search_logs", "detect_signals"):
        assert required in result.final_context["successful_tools"]
