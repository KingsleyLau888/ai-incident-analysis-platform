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
