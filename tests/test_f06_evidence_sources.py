"""F06：Agent 调查的证据来源分型与查询透传。

覆盖：检索方法公开接收 query（调查查询真正改变检索输入）、
关键词命中的日志按 id 进入最终证据（可回溯）、
派生观察（调查笔记）与原始日志分型、真实 LLM 路径收到分型后的笔记字段。
"""

import json

import httpx

from app.agent.react_agent import ReActAgent, build_retrieval_query
from app.llm.openai_compatible_client import OpenAICompatibleClient
from app.models.log_entry import LogEntry
from app.services.runbook_retriever import RunbookRetriever
from app.services.similar_incident_retriever import SimilarIncidentRetriever


def _make_logs() -> list[LogEntry]:
    return [
        LogEntry(id=1, service_id=1, level="ERROR", message="DBConnectionTimeout mysql-primary"),
        LogEntry(id=2, service_id=1, level="INFO", message="request completed"),
        LogEntry(id=3, service_id=1, level="ERROR", message="mysql-primary down"),
    ]


def _execute(agent: ReActAgent, action_name: str, action_input: dict, ctx: dict):
    return agent._execute_tool(
        action_name=action_name,
        action_input=action_input,
        ctx=ctx,
        incident_title="Payment API errors",
        service_name="payment-service",
        search_logs_fn=lambda c: c.get("logs", []),
        detect_signals_fn=lambda c: {"issue_type": "database_issue", "severity": "high",
                                     "matched_issues": [], "evidence_logs": []},
        retrieve_runbooks_fn=lambda query, top_k, issue_type=None: [],
        retrieve_similar_incidents_fn=lambda query, top_k, issue_type=None: [],
    )


def test_agent_runbook_query_reaches_retriever():
    captured = {}

    def retrieve_runbooks_fn(query, top_k, issue_type=None):
        captured.update(query=query, top_k=top_k, issue_type=issue_type)
        return []

    agent = ReActAgent(llm_client=None)
    ctx = {"issue_type": "database_issue"}
    observation, ok = agent._execute_tool(
        action_name="retrieve_runbooks",
        action_input={"query": "mysql connection pool exhaustion", "top_k": 3},
        ctx=ctx,
        incident_title="Payment API errors",
        service_name="payment-service",
        search_logs_fn=lambda c: [],
        detect_signals_fn=lambda c: {},
        retrieve_runbooks_fn=retrieve_runbooks_fn,
        retrieve_similar_incidents_fn=lambda query, top_k, issue_type=None: [],
    )
    assert ok is True
    assert captured["query"] == "mysql connection pool exhaustion"  # 调查查询透传
    assert captured["issue_type"] == "database_issue"


def test_agent_runbook_query_falls_back_to_context_query():
    captured = {}

    def retrieve_runbooks_fn(query, top_k, issue_type=None):
        captured["query"] = query
        return []

    agent = ReActAgent(llm_client=None)
    ctx = {"issue_type": "timeout_issue", "evidence_logs": [_make_logs()[0]]}
    agent._execute_tool(
        action_name="retrieve_runbooks",
        action_input={},
        ctx=ctx,
        incident_title="Payment API errors",
        service_name="payment-service",
        search_logs_fn=lambda c: [],
        detect_signals_fn=lambda c: {},
        retrieve_runbooks_fn=retrieve_runbooks_fn,
        retrieve_similar_incidents_fn=lambda query, top_k, issue_type=None: [],
    )
    assert captured["query"] == build_retrieval_query("Payment API errors", "payment-service", ctx)


def test_runbook_retriever_public_query_method_returns_chunks():
    retriever = RunbookRetriever()
    chunks = retriever.retrieve_with_query("database connection timeout", top_k=2, issue_type=None)
    assert 1 <= len(chunks) <= 2
    for chunk in chunks:
        assert chunk.chunk_id
        assert chunk.content
        assert isinstance(chunk.score, float)


def test_similar_incident_retriever_public_query_method():
    retriever = SimilarIncidentRetriever()
    incidents = retriever.retrieve_with_query("database connection timeout", top_k=2)
    assert 1 <= len(incidents) <= 2
    for incident in incidents:
        assert incident.historical_id
        assert isinstance(incident.similarity_score, float)


def test_keyword_matches_record_log_ids_and_enter_evidence():
    agent = ReActAgent(llm_client=None)
    ctx = {"logs": _make_logs()}
    observation, ok = _execute(agent, "query_logs_by_keyword", {"keyword": "mysql-primary"}, ctx)
    assert ok is True
    matched_ids = {log.id for log in ctx["keyword_matches"]}
    assert matched_ids == {1, 3}  # 命中的真实 log id，可回溯来源
    assert "ids: [1, 3]" in ctx["investigation_notes"][0]


def test_real_llm_payload_receives_typed_notes_separate_from_logs():
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        content = {
            "diagnosis_summary": "ok",
            "root_cause_hypotheses": [],
            "impact_scope": "",
            "structured_suggested_actions": [],
        }
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(content)}}]},
        )

    client = OpenAICompatibleClient(
        api_key="test-key",
        base_url="http://llm.test/v1",
        model="test-model",
        http_client=httpx.Client(
            base_url="http://llm.test/v1", transport=httpx.MockTransport(handler)
        ),
    )
    client.diagnose(
        incident_title="t",
        service_name="s",
        issue_type="database_issue",
        severity="high",
        evidence_logs=[_make_logs()[0]],
        retrieved_runbook_chunks=[],
        similar_incidents=[],
        investigation_notes=["Timeline built with 3 of 3 logs."],
    )
    user_content = json.loads(captured_payload["messages"][1]["content"])
    # 派生观察单独分型传入，不与原始日志混在 evidence_logs 里
    assert user_content["investigation_notes"] == ["Timeline built with 3 of 3 logs."]
    assert user_content["evidence_logs"] == ["DBConnectionTimeout mysql-primary"]
