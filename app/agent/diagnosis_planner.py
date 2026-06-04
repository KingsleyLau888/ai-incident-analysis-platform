from dataclasses import dataclass

from app.models.log_entry import LogEntry


@dataclass(frozen=True)
class DiagnosisPlan:
    analysis_plan: str
    tool_steps: list[str]


class DiagnosisPlanner:
    def plan(
        self,
        incident_title: str,
        service_name: str,
        issue_type: str,
        severity: str,
        evidence_logs: list[LogEntry],
    ) -> DiagnosisPlan:
        tool_steps = [
            "search_logs",
            "detect_signals",
            "select_evidence",
        ]

        if issue_type != "unknown":
            tool_steps.append("retrieve_runbooks")
        if issue_type != "unknown" and evidence_logs:
            tool_steps.append("retrieve_similar_incidents")

        tool_steps.append("generate_structured_diagnosis")
        evidence_count = len(evidence_logs)
        analysis_plan = (
            f"Analyze '{incident_title}' for {service_name} as a {severity} {issue_type} incident. "
            f"Use {evidence_count} selected evidence logs and execute: {', '.join(tool_steps)}."
        )
        return DiagnosisPlan(analysis_plan=analysis_plan, tool_steps=tool_steps)
