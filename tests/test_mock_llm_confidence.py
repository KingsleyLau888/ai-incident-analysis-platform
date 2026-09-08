from types import SimpleNamespace

from app.llm.mock_client import MockLLMClient
from app.services.runbook_retriever import RetrievedRunbookChunk
from app.services.similar_incident_retriever import SimilarIncident


def test_mock_llm_confidence_changes_with_context_strength():
    client = MockLLMClient()

    weak = client.diagnose(
        incident_title="Checkout warning",
        service_name="checkout-service",
        issue_type="timeout_issue",
        severity="medium",
        evidence_logs=[SimpleNamespace(message="Payment provider timeout during checkout")],
        retrieved_runbook_chunks=[],
        similar_incidents=[],
    )

    strong = client.diagnose(
        incident_title="Checkout payment timeout",
        service_name="checkout-service",
        issue_type="timeout_issue",
        severity="high",
        evidence_logs=[
            SimpleNamespace(message="Payment provider timeout during checkout"),
            SimpleNamespace(message="Payment provider timeout retry exhausted"),
            SimpleNamespace(message="Checkout API returned 504 after upstream timeout"),
        ],
        retrieved_runbook_chunks=[
            RetrievedRunbookChunk(
                chunk_id="timeout-1",
                source="payment_provider_timeout.md",
                title="Suggested Actions",
                content="- Check upstream health\n- Tune timeout budget",
                score=0.82,
            )
        ],
        similar_incidents=[
            SimilarIncident(
                historical_id="HIST-TIMEOUT-001",
                title="Payment provider timeout",
                issue_type="timeout_issue",
                similarity_score=0.91,
                root_cause="Payment provider exceeded client timeout budget.",
                resolution="Added backoff and circuit breaker.",
            )
        ],
    )

    weak_confidence = weak.diagnosis.root_cause_hypotheses[0].confidence
    strong_confidence = strong.diagnosis.root_cause_hypotheses[0].confidence

    assert strong_confidence > weak_confidence
    assert strong_confidence != 0.65
