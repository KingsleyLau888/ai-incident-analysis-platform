from dataclasses import dataclass

from app.models.log_entry import LogEntry


ISSUE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "timeout_issue": ("timeout", "timed out"),
    "database_issue": ("dbconnection", "mysql", "postgres", "database"),
    "memory_issue": ("outofmemory", "oom", "memory"),
    "auth_issue": ("401", "unauthorized", "token", "auth"),
    "server_error": ("500", "internal server error"),
    "cache_issue": ("redisconnection", "cache", "redis"),
}

ISSUE_SEVERITY: dict[str, str] = {
    "database_issue": "high",
    "memory_issue": "high",
    "server_error": "high",
    "timeout_issue": "medium",
    "auth_issue": "medium",
    "cache_issue": "medium",
    "unknown": "low",
}

SUGGESTED_ACTIONS: dict[str, str] = {
    "database_issue": "Check database availability, connection pool, and credentials.",
    "timeout_issue": "Check upstream latency and timeout settings.",
    "memory_issue": "Check memory usage and recent deployments.",
    "auth_issue": "Check token validation, auth service, and credentials.",
    "server_error": "Check application error stack and recent changes.",
    "cache_issue": "Check Redis/cache availability and connection settings.",
    "unknown": "Manually inspect logs.",
}

ISSUE_PRIORITY = {
    "database_issue": 0,
    "memory_issue": 1,
    "server_error": 2,
    "timeout_issue": 3,
    "auth_issue": 4,
    "cache_issue": 5,
    "unknown": 6,
}


@dataclass(frozen=True)
class RuleDetectionResult:
    issue_type: str
    severity: str
    matched_issues: list[str]
    evidence_logs: list[LogEntry]


def detect_issue(logs: list[LogEntry]) -> RuleDetectionResult:
    matches_by_issue: dict[str, list[LogEntry]] = {}

    for log in logs:
        message = log.message.lower()
        for issue_type, keywords in ISSUE_KEYWORDS.items():
            if any(keyword in message for keyword in keywords):
                matches_by_issue.setdefault(issue_type, []).append(log)

    if not matches_by_issue:
        return RuleDetectionResult(
            issue_type="unknown",
            severity=ISSUE_SEVERITY["unknown"],
            matched_issues=[],
            evidence_logs=[],
        )

    matched_issues = sorted(matches_by_issue, key=lambda issue: ISSUE_PRIORITY[issue])
    issue_type = matched_issues[0]
    evidence_logs = _unique_logs(matches_by_issue[issue_type])

    return RuleDetectionResult(
        issue_type=issue_type,
        severity=ISSUE_SEVERITY[issue_type],
        matched_issues=matched_issues,
        evidence_logs=evidence_logs,
    )


def suggested_actions_for(issue_type: str) -> str:
    return SUGGESTED_ACTIONS.get(issue_type, SUGGESTED_ACTIONS["unknown"])


def _unique_logs(logs: list[LogEntry]) -> list[LogEntry]:
    seen: set[int] = set()
    unique_logs: list[LogEntry] = []
    for log in logs:
        if log.id not in seen:
            seen.add(log.id)
            unique_logs.append(log)
    return unique_logs
