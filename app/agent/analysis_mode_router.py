from __future__ import annotations

from dataclasses import dataclass

from app.models.log_entry import LogEntry
from app.rule_engine.detector import ISSUE_KEYWORDS, RuleDetectionResult


@dataclass(frozen=True)
class AnalysisModeDecision:
    mode: str
    reason: str


class AnalysisModeRouter:
    """Choose between the stable pipeline and ReAct agent investigation."""

    def route(
        self,
        *,
        incident_title: str,
        logs: list[LogEntry],
        detection: RuleDetectionResult,
        requested_mode: str,
        agent_available: bool,
    ) -> AnalysisModeDecision:
        requested_mode = requested_mode.strip().lower()

        if requested_mode == "pipeline":
            return AnalysisModeDecision(
                mode="pipeline",
                reason="forced pipeline mode by ANALYSIS_MODE=pipeline",
            )

        if requested_mode == "agent":
            if agent_available:
                return AnalysisModeDecision(
                    mode="agent",
                    reason="forced agent mode by ANALYSIS_MODE=agent",
                )
            return AnalysisModeDecision(
                mode="pipeline",
                reason="agent requested but no real LLM agent client is available",
            )

        if not agent_available:
            return AnalysisModeDecision(
                mode="pipeline",
                reason="auto mode selected pipeline because no real LLM agent client is available",
            )

        complexity_reasons = _complexity_reasons(incident_title, logs, detection)
        if complexity_reasons:
            return AnalysisModeDecision(
                mode="agent",
                reason="auto mode selected agent because " + "; ".join(complexity_reasons),
            )

        return AnalysisModeDecision(
            mode="pipeline",
            reason="auto mode selected pipeline because the incident has a single clear signal",
        )


def _complexity_reasons(
    incident_title: str,
    logs: list[LogEntry],
    detection: RuleDetectionResult,
) -> list[str]:
    reasons: list[str] = []

    if len(detection.matched_issues) >= 2:
        reasons.append(f"multiple issue signals detected: {detection.matched_issues}")

    error_count = sum(1 for log in logs if log.level.upper() in {"ERROR", "CRITICAL"})
    if len(logs) >= 10 or error_count >= 5:
        reasons.append(f"large or noisy log window: logs={len(logs)}, errors={error_count}")

    title_issues = _issues_in_text(incident_title)
    if title_issues and detection.issue_type not in title_issues:
        reasons.append(
            f"incident title signals {title_issues} but logs indicate {detection.issue_type}"
        )

    if "server_error" in detection.matched_issues and detection.issue_type != "server_error":
        reasons.append("server_error appears to be a symptom rather than the primary signal")

    if detection.issue_type == "unknown" and error_count > 0:
        reasons.append("unknown issue type despite error logs")

    return reasons


def _issues_in_text(text: str) -> list[str]:
    lowered = text.lower()
    matched: list[str] = []
    for issue_type, keywords in ISSUE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            matched.append(issue_type)
    return matched
