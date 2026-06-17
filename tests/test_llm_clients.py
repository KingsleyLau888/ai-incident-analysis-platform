import json

import httpx

from app.llm import factory
from app.llm.factory import FallbackLLMClient, get_llm_client
from app.llm.mock_client import MockLLMClient
from app.llm.openai_compatible_client import OpenAICompatibleClient
from app.services import analysis_service


class _Log:
    def __init__(self, message: str) -> None:
        self.message = message


def _diagnosis_kwargs() -> dict:
    return {
        "incident_title": "Payment API returns 500 errors",
        "service_name": "payment-service",
        "issue_type": "database_issue",
        "severity": "high",
        "evidence_logs": [_Log("DBConnectionTimeout while connecting to mysql-primary")],
        "retrieved_runbook_chunks": [],
        "similar_incidents": [],
    }


def test_default_llm_provider_uses_mock(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    client = get_llm_client()
    result = client.diagnose(**_diagnosis_kwargs())

    assert isinstance(client, MockLLMClient)
    assert result.provider == "mock"


def test_openai_compatible_call_failure_falls_back_to_mock(monkeypatch):
    class FailingClient:
        def __init__(self, **kwargs) -> None:
            pass

        def diagnose(self, **kwargs):
            raise RuntimeError("provider unavailable")

    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://llm.test/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setattr(factory, "OpenAICompatibleClient", FailingClient)

    result = get_llm_client().diagnose(**_diagnosis_kwargs())

    assert result.provider == "mock_fallback"
    assert result.diagnosis.diagnosis_summary


def test_invalid_openai_schema_falls_back_to_mock():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "diagnosis_summary": "Missing required structured fields"
                                }
                            )
                        }
                    }
                ]
            },
        )

    http_client = httpx.Client(
        base_url="http://llm.test/v1",
        transport=httpx.MockTransport(handler),
    )
    primary = OpenAICompatibleClient(
        api_key="test-key",
        base_url="http://llm.test/v1",
        model="test-model",
        http_client=http_client,
    )

    result = FallbackLLMClient(primary=primary).diagnose(**_diagnosis_kwargs())

    assert result.provider == "mock_fallback"


def test_openai_compatible_valid_response_uses_real_provider():
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        content = {
            "diagnosis_summary": "Database connections are timing out.",
            "root_cause_hypotheses": [
                {
                    "cause": "mysql-primary connection saturation",
                    "confidence": 0.9,
                    "supporting_evidence": ["DBConnectionTimeout"],
                }
            ],
            "impact_scope": "payment-service",
            "structured_suggested_actions": ["Check mysql-primary connections."],
        }
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(content)}}]},
        )

    http_client = httpx.Client(
        base_url="http://llm.test/v1/",
        transport=httpx.MockTransport(handler),
    )
    client = OpenAICompatibleClient(
        api_key="test-key",
        base_url="http://llm.test/v1",
        model="test-model",
        http_client=http_client,
    )

    result = client.diagnose(**_diagnosis_kwargs())
    user_context = json.loads(captured_payload["messages"][1]["content"])

    assert result.provider == "openai_compatible"
    assert user_context["incident_title"]
    assert user_context["service_name"]
    assert user_context["issue_type"]
    assert user_context["severity"]
    assert user_context["evidence_logs"]
    assert "retrieved_runbook_chunks" in user_context
    assert "similar_incidents" in user_context


def test_openai_compatible_decide_action_parses_agent_tool_choice():
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        content = {
            "thought": "I need the recent service logs first.",
            "action": "search_logs",
            "action_input": {"service_name": "payment-service"},
        }
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(content)}}]},
        )

    http_client = httpx.Client(
        base_url="http://llm.test/v1/",
        transport=httpx.MockTransport(handler),
    )
    client = OpenAICompatibleClient(
        api_key="test-key",
        base_url="http://llm.test/v1",
        model="test-model",
        http_client=http_client,
    )

    decision = client.decide_action("system prompt", "user prompt")

    assert captured_payload["response_format"] == {"type": "json_object"}
    assert decision["action"] == "search_logs"
    assert decision["action_input"]["service_name"] == "payment-service"


def test_react_agent_mode_uses_agent_selected_tools(client, monkeypatch):
    class FakeAgentLLM:
        def __init__(self) -> None:
            self.calls = 0

        def decide_action(self, system_prompt: str, user_prompt: str) -> dict:
            self.calls += 1
            actions = [
                {
                    "thought": "Start by searching service logs.",
                    "action": "search_logs",
                    "action_input": {"service_name": "payment-service"},
                },
                {
                    "thought": "Classify the signals from the retrieved logs.",
                    "action": "detect_signals",
                    "action_input": {},
                },
                {
                    "thought": "The evidence is enough for a diagnosis.",
                    "action": "generate_diagnosis",
                    "action_input": {},
                },
            ]
            return actions[min(self.calls - 1, len(actions) - 1)]

    monkeypatch.setenv("REACT_AGENT_ENABLED", "1")
    monkeypatch.setattr(analysis_service, "_get_react_llm_client", lambda: FakeAgentLLM())

    service = client.post("/services", json={"name": "payment-service"}).json()
    client.post(
        "/logs",
        json={
            "service_id": service["id"],
            "level": "ERROR",
            "message": "DBConnectionTimeout while connecting to mysql-primary",
        },
    )
    incident = client.post(
        "/incidents",
        json={"service_id": service["id"], "title": "Payment API errors"},
    ).json()

    response = client.post(f"/incidents/{incident['id']}/analyze")

    assert response.status_code == 201
    analysis = response.json()
    assert analysis["retrieved_runbook_chunks"] == []
    assert analysis["similar_incidents"] == []
    assert analysis["analysis_plan"]["tool_steps"] == [
        "search_logs",
        "detect_signals",
        "generate_diagnosis",
    ]

    trace = client.get(f"/incidents/{incident['id']}/trace").json()
    assert trace[0]["step_name"] == "analysis_mode_routing"
    assert "selected_mode=agent" in trace[0]["detail"]
    assert trace[1]["step_name"] == "react_agent_context"
    assert "Agent mode: react_llm" in trace[1]["detail"]


def test_react_agent_can_use_focused_investigation_tools(client, monkeypatch):
    class FakeAgentLLM:
        def __init__(self) -> None:
            self.calls = 0

        def decide_action(self, system_prompt: str, user_prompt: str) -> dict:
            self.calls += 1
            actions = [
                {
                    "thought": "Collect the service logs first.",
                    "action": "search_logs",
                    "action_input": {"service_name": "payment-service"},
                },
                {
                    "thought": "Classify the main failure signal.",
                    "action": "detect_signals",
                    "action_input": {},
                },
                {
                    "thought": "The title says 500, but I need to verify the database dependency.",
                    "action": "query_logs_by_keyword",
                    "action_input": {"keyword": "mysql-primary", "top_k": 5},
                },
                {
                    "thought": "Check whether dependency terms point to a downstream root cause.",
                    "action": "inspect_dependency_signals",
                    "action_input": {},
                },
                {
                    "thought": "Now generate the diagnosis from the investigated evidence.",
                    "action": "generate_diagnosis",
                    "action_input": {},
                },
            ]
            return actions[min(self.calls - 1, len(actions) - 1)]

    monkeypatch.setenv("REACT_AGENT_ENABLED", "1")
    monkeypatch.setattr(analysis_service, "_get_react_llm_client", lambda: FakeAgentLLM())

    service = client.post("/services", json={"name": "payment-service"}).json()
    for message in [
        "INFO payment request started",
        "ERROR Payment API returned 500",
        "ERROR DBConnectionTimeout while connecting to mysql-primary",
    ]:
        client.post(
            "/logs",
            json={
                "service_id": service["id"],
                "level": "ERROR" if message.startswith("ERROR") else "INFO",
                "message": message,
            },
        )
    incident = client.post(
        "/incidents",
        json={"service_id": service["id"], "title": "Payment API returns 500 errors"},
    ).json()

    response = client.post(f"/incidents/{incident['id']}/analyze")

    assert response.status_code == 201
    tool_steps = response.json()["analysis_plan"]["tool_steps"]
    assert "query_logs_by_keyword" in tool_steps
    assert "inspect_dependency_signals" in tool_steps

    trace = client.get(f"/incidents/{incident['id']}/trace").json()
    trace_text = "\n".join(step["detail"] for step in trace)
    assert "Keyword `mysql-primary` matched 1 logs" in trace_text
    assert "Dependency signals found" in trace_text


def test_auto_mode_routes_complex_incident_to_agent(client, monkeypatch):
    class FakeAgentLLM:
        def __init__(self) -> None:
            self.calls = 0

        def decide_action(self, system_prompt: str, user_prompt: str) -> dict:
            self.calls += 1
            actions = [
                {"thought": "Start with logs.", "action": "search_logs", "action_input": {}},
                {"thought": "Classify signals.", "action": "detect_signals", "action_input": {}},
                {
                    "thought": "The 500 may be a symptom, inspect dependencies.",
                    "action": "inspect_dependency_signals",
                    "action_input": {},
                },
                {"thought": "Finish.", "action": "generate_diagnosis", "action_input": {}},
            ]
            return actions[min(self.calls - 1, len(actions) - 1)]

    monkeypatch.delenv("REACT_AGENT_ENABLED", raising=False)
    monkeypatch.setenv("ANALYSIS_MODE", "auto")
    monkeypatch.setattr(analysis_service, "_get_react_llm_client", lambda: FakeAgentLLM())

    service = client.post("/services", json={"name": "payment-service"}).json()
    for message in [
        "ERROR Payment API returned 500",
        "ERROR DBConnectionTimeout while connecting to mysql-primary",
    ]:
        client.post(
            "/logs",
            json={"service_id": service["id"], "level": "ERROR", "message": message},
        )
    incident = client.post(
        "/incidents",
        json={"service_id": service["id"], "title": "Payment API returns 500 errors"},
    ).json()

    response = client.post(f"/incidents/{incident['id']}/analyze")

    assert response.status_code == 201
    trace = client.get(f"/incidents/{incident['id']}/trace").json()
    assert trace[0]["step_name"] == "analysis_mode_routing"
    assert "selected_mode=agent" in trace[0]["detail"]
    assert "server_error appears to be a symptom" in trace[0]["detail"]


def test_analyze_trace_records_mock_fallback(client, monkeypatch):
    class FailingClient:
        def diagnose(self, **kwargs):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        analysis_service,
        "get_llm_client",
        lambda: FallbackLLMClient(primary=FailingClient()),
    )
    service = client.post("/services", json={"name": "payment-service"}).json()
    client.post(
        "/logs",
        json={
            "service_id": service["id"],
            "level": "ERROR",
            "message": "DBConnectionTimeout while connecting to mysql-primary",
        },
    )
    incident = client.post(
        "/incidents",
        json={"service_id": service["id"], "title": "Payment API errors"},
    ).json()

    client.post(f"/incidents/{incident['id']}/analyze")
    trace = client.get(f"/incidents/{incident['id']}/trace").json()

    summary_step = next(step for step in trace if step["step_name"] == "summary_generation")
    assert "provider=mock_fallback" in summary_step["detail"]
