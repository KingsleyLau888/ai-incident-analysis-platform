from dataclasses import dataclass

from app.models.log_entry import LogEntry
from app.services.runbook_retriever import RetrievedRunbookChunk


@dataclass(frozen=True)
class StructuredDiagnosis:
    diagnosis_summary: str
    root_cause_hypotheses: list[str]
    impact_scope: str
    structured_suggested_actions: list[str]


class MockLLMClient:
    def diagnose(
        self,
        incident_title: str,
        service_name: str,
        issue_type: str,
        evidence_logs: list[LogEntry],
        retrieved_runbook_chunks: list[RetrievedRunbookChunk],
    ) -> StructuredDiagnosis:
        evidence_hint = _first_evidence_message(evidence_logs)
        runbook_actions = _actions_from_runbooks(retrieved_runbook_chunks)
        issue_label = issue_type.replace("_", " ")

        return StructuredDiagnosis(
            diagnosis_summary=(
                f"{service_name} is showing signs of {issue_label} for incident "
                f"'{incident_title}' based on rule-matched logs and retrieved runbook guidance."
            ),
            root_cause_hypotheses=[
                f"{service_name} may be affected by {issue_label}.",
                f"The strongest evidence is: {evidence_hint}",
            ],
            impact_scope=f"Likely impact is scoped to {service_name} and its directly related dependencies.",
            structured_suggested_actions=runbook_actions
            or [
                f"Review the evidence logs for {service_name}.",
                f"Follow the runbook guidance associated with {issue_type}.",
            ],
        )


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
    return [
        line.strip(" -")
        for line in content.splitlines()
        if line.strip(" -")
    ]
