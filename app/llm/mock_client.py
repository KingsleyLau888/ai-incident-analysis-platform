from app.llm.base import DiagnosisResult, RootCauseHypothesis, StructuredDiagnosis
from app.models.log_entry import LogEntry
from app.services.runbook_retriever import RetrievedRunbookChunk
from app.services.similar_incident_retriever import SimilarIncident


class MockLLMClient:
    def diagnose(
        self,
        incident_title: str,
        service_name: str,
        issue_type: str,
        severity: str,
        evidence_logs: list[LogEntry],
        retrieved_runbook_chunks: list[RetrievedRunbookChunk],
        similar_incidents: list[SimilarIncident],
    ) -> DiagnosisResult:
        evidence_hint = _first_evidence_message(evidence_logs)
        runbook_actions = _actions_from_runbooks(retrieved_runbook_chunks)
        historical_actions = _actions_from_similar_incidents(similar_incidents)
        issue_label = issue_type.replace("_", " ")
        context_sources = ["rule-matched logs"]
        if retrieved_runbook_chunks:
            context_sources.append("runbook guidance")
        if similar_incidents:
            context_sources.append("similar incidents")

        hypotheses = [
            RootCauseHypothesis(
                cause=f"{service_name} may be affected by {issue_label}.",
                confidence=_primary_confidence(
                    issue_type=issue_type,
                    severity=severity,
                    evidence_logs=evidence_logs,
                    retrieved_runbook_chunks=retrieved_runbook_chunks,
                    similar_incidents=similar_incidents,
                ),
                supporting_evidence=[evidence_hint],
            )
        ]
        if similar_incidents:
            closest = similar_incidents[0]
            hypotheses.append(
                RootCauseHypothesis(
                    cause=closest.root_cause,
                    confidence=_similar_incident_confidence(
                        closest.similarity_score,
                        evidence_logs=evidence_logs,
                        retrieved_runbook_chunks=retrieved_runbook_chunks,
                    ),
                    supporting_evidence=[f"Similar incident: {closest.title}"],
                )
            )

        diagnosis = StructuredDiagnosis(
            diagnosis_summary=(
                f"{service_name} is showing signs of {issue_label} for incident "
                f"'{incident_title}' with severity {severity}, based on {', '.join(context_sources)}."
            ),
            root_cause_hypotheses=hypotheses,
            impact_scope=f"Likely impact is scoped to {service_name} and its directly related dependencies.",
            structured_suggested_actions=(runbook_actions + historical_actions)[:3]
            or [
                f"Review the evidence logs for {service_name}.",
                f"Follow the runbook guidance associated with {issue_type}.",
            ],
        )
        return DiagnosisResult(diagnosis=diagnosis, provider="mock")


def _first_evidence_message(evidence_logs: list[LogEntry]) -> str:
    if not evidence_logs:
        return "No rule-matched evidence logs were selected."
    return evidence_logs[0].message


def _actions_from_runbooks(chunks: list[RetrievedRunbookChunk]) -> list[str]:
    actions: list[str] = []
    for chunk in chunks:
        if chunk.title.lower() == "suggested actions":
            actions.extend(_content_lines(chunk.content))
        if len(actions) >= 3:
            break
    return actions[:3]


def _content_lines(content: str) -> list[str]:
    return [line.strip(" -") for line in content.splitlines() if line.strip(" -")]


def _actions_from_similar_incidents(similar_incidents: list[SimilarIncident]) -> list[str]:
    if not similar_incidents:
        return []
    return [f"Consider the prior resolution: {similar_incidents[0].resolution}"]


def _primary_confidence(
    *,
    issue_type: str,
    severity: str,
    evidence_logs: list[LogEntry],
    retrieved_runbook_chunks: list[RetrievedRunbookChunk],
    similar_incidents: list[SimilarIncident],
) -> float:
    if issue_type == "unknown":
        return 0.2

    score = 0.45
    score += min(len(evidence_logs), 4) * 0.05
    score += _max_runbook_score(retrieved_runbook_chunks) * 0.15
    score += _max_similar_incident_score(similar_incidents) * 0.15
    if severity == "high":
        score += 0.05
    return _bounded_confidence(score)


def _similar_incident_confidence(
    similarity_score: float,
    *,
    evidence_logs: list[LogEntry],
    retrieved_runbook_chunks: list[RetrievedRunbookChunk],
) -> float:
    score = 0.4
    score += similarity_score * 0.35
    score += min(len(evidence_logs), 4) * 0.03
    score += _max_runbook_score(retrieved_runbook_chunks) * 0.08
    return _bounded_confidence(score)


def _max_runbook_score(chunks: list[RetrievedRunbookChunk]) -> float:
    return max((chunk.score for chunk in chunks), default=0.0)


def _max_similar_incident_score(similar_incidents: list[SimilarIncident]) -> float:
    return max((incident.similarity_score for incident in similar_incidents), default=0.0)


def _bounded_confidence(score: float) -> float:
    return round(max(0.05, min(score, 0.95)), 2)
