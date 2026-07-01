from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.log_entry import LogEntry


@dataclass(frozen=True)
class SignalPattern:
    label: str
    pattern: str
    weight: float = 1.0
    evidence: bool = True


@dataclass(frozen=True)
class IssueSignalRule:
    issue_type: str
    severity: str
    base_weight: float
    patterns: tuple[SignalPattern, ...]


ISSUE_RULES: dict[str, IssueSignalRule] = {
    "database_issue": IssueSignalRule(
        issue_type="database_issue",
        severity="high",
        base_weight=1.25,
        patterns=(
            SignalPattern("db_connection_timeout", r"\bdbconnection(timeout| failed)?\b", 2.6),
            SignalPattern("database_unavailable", r"\bdatabase (is )?unavailable\b", 2.4),
            SignalPattern("database_write_failure", r"\bdatabase write failure\b", 2.1),
            SignalPattern("connection_refused", r"\b(connection refused|could not connect)\b", 1.9),
            SignalPattern("connection_pool", r"\b(connection pool|pool exhausted|too many connections)\b", 2.0),
            SignalPattern("database_primary", r"\b(mysql|postgres|postgresql|shop-primary|mysql-primary)\b", 1.4),
            SignalPattern("sql_error", r"\b(sqlstate|deadlock|slow quer(y|ies))\b", 1.3),
            SignalPattern("database_keyword", r"\bdatabase\b", 0.8),
        ),
    ),
    "memory_issue": IssueSignalRule(
        issue_type="memory_issue",
        severity="high",
        base_weight=1.15,
        patterns=(
            SignalPattern("oom", r"\b(outofmemory|oom|oomkilled)\b", 2.7),
            SignalPattern("memory_exceeded", r"\b(memory exceeded|heap exhausted|heap out of memory)\b", 2.2),
            SignalPattern("memory_keyword", r"\bmemory\b", 0.8),
        ),
    ),
    "auth_issue": IssueSignalRule(
        issue_type="auth_issue",
        severity="medium",
        base_weight=1.05,
        patterns=(
            SignalPattern("unauthorized", r"\b(unauthorized|401)\b", 2.2),
            SignalPattern("authentication_failed", r"\bauthentication failed\b", 2.1),
            SignalPattern("token_rejected", r"\b(token rejected|invalid token|expired token)\b", 1.9),
            SignalPattern("credentials", r"\b(credentials|permission denied|forbidden|403)\b", 1.3),
            SignalPattern("auth_keyword", r"\bauth\b", 0.8),
        ),
    ),
    "timeout_issue": IssueSignalRule(
        issue_type="timeout_issue",
        severity="medium",
        base_weight=0.95,
        patterns=(
            SignalPattern("timed_out", r"\b(timed out|timeout|deadline exceeded)\b", 1.8),
            SignalPattern("retry_exhausted", r"\bretry exhausted\b", 1.2),
            SignalPattern("gateway_timeout", r"\b(504|gateway timeout)\b", 1.4),
            SignalPattern("latency", r"\b(slow|latency|took \d+ms)\b", 0.9),
        ),
    ),
    "cache_issue": IssueSignalRule(
        issue_type="cache_issue",
        severity="medium",
        base_weight=0.9,
        patterns=(
            SignalPattern("redis_connection", r"\bredisconnection\b", 2.1),
            SignalPattern("redis_unavailable", r"\b(redis unavailable|redis timeout)\b", 1.8),
            SignalPattern("cache_eviction", r"\b(cache eviction|maxmemory|evicted keys)\b", 1.5),
            SignalPattern("cache_keyword", r"\b(cache|redis)\b", 0.8),
        ),
    ),
    "server_error": IssueSignalRule(
        issue_type="server_error",
        severity="high",
        base_weight=0.75,
        patterns=(
            SignalPattern("http_500", r"\b(500|http 500|returned 500)\b", 1.4),
            SignalPattern("internal_server_error", r"\binternal server error\b", 1.4),
            SignalPattern("unhandled_exception", r"\b(unhandled exception|stack trace)\b", 1.2),
        ),
    ),
}

ISSUE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "timeout_issue": ("timeout", "timed out", "deadline exceeded", "504"),
    "database_issue": (
        "dbconnection",
        "mysql",
        "postgres",
        "database",
        "connection pool",
        "sqlstate",
        "shop-primary",
    ),
    "memory_issue": ("outofmemory", "oom", "oomkilled", "memory"),
    "auth_issue": ("401", "unauthorized", "token", "auth", "credentials"),
    "server_error": ("500", "internal server error", "unhandled exception"),
    "cache_issue": ("redisconnection", "cache", "redis", "maxmemory"),
}

ISSUE_SEVERITY: dict[str, str] = {
    issue_type: rule.severity for issue_type, rule in ISSUE_RULES.items()
}
ISSUE_SEVERITY["unknown"] = "low"

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
    "auth_issue": 2,
    "timeout_issue": 3,
    "cache_issue": 4,
    "server_error": 5,
    "unknown": 6,
}


@dataclass(frozen=True)
class RuleDetectionResult:
    issue_type: str
    severity: str
    matched_issues: list[str]
    evidence_logs: list[LogEntry]
    confidence: float = 0.0
    candidate_scores: dict[str, float] | None = None
    matched_signals: list[str] | None = None


def detect_issue(logs: list[LogEntry]) -> RuleDetectionResult:
    scores: dict[str, float] = {}
    evidence_by_issue: dict[str, list[LogEntry]] = {}
    signals_by_issue: dict[str, set[str]] = {}

    for log in logs:
        message = log.message.lower()
        level_weight = _level_weight(log.level)
        for issue_type, rule in ISSUE_RULES.items():
            matched_labels = _matched_pattern_labels(rule, message)
            if not matched_labels:
                continue
            signal_score = sum(
                pattern.weight
                for pattern in rule.patterns
                if pattern.label in matched_labels
            )
            scores[issue_type] = scores.get(issue_type, 0.0) + (
                rule.base_weight * signal_score * level_weight
            )
            signals_by_issue.setdefault(issue_type, set()).update(matched_labels)
            if _is_evidence_log(log, matched_labels, rule):
                evidence_by_issue.setdefault(issue_type, []).append(log)

    scores = _apply_root_cause_ranking(scores)
    if not scores:
        return RuleDetectionResult(
            issue_type="unknown",
            severity=ISSUE_SEVERITY["unknown"],
            matched_issues=[],
            evidence_logs=[],
            confidence=0.0,
            candidate_scores={},
            matched_signals=[],
        )

    matched_issues = sorted(
        scores,
        key=lambda issue: (-scores[issue], ISSUE_PRIORITY[issue]),
    )
    issue_type = matched_issues[0]
    evidence_logs = _select_evidence_logs(
        logs=logs,
        primary_issue=issue_type,
        evidence_by_issue=evidence_by_issue,
        matched_issues=matched_issues,
    )
    confidence = _confidence(issue_type, scores)

    return RuleDetectionResult(
        issue_type=issue_type,
        severity=ISSUE_SEVERITY[issue_type],
        matched_issues=matched_issues,
        evidence_logs=evidence_logs,
        confidence=confidence,
        candidate_scores={issue: round(score, 3) for issue, score in scores.items()},
        matched_signals=sorted(signals_by_issue.get(issue_type, set())),
    )


def suggested_actions_for(issue_type: str) -> str:
    return SUGGESTED_ACTIONS.get(issue_type, SUGGESTED_ACTIONS["unknown"])


def _matched_pattern_labels(rule: IssueSignalRule, message: str) -> set[str]:
    labels: set[str] = set()
    for pattern in rule.patterns:
        if re.search(pattern.pattern, message):
            labels.add(pattern.label)
    return labels


def _level_weight(level: str) -> float:
    normalized = (level or "").upper()
    if normalized in {"CRITICAL", "FATAL"}:
        return 1.25
    if normalized == "ERROR":
        return 1.0
    if normalized in {"WARN", "WARNING"}:
        return 0.45
    return 0.25


def _is_evidence_log(
    log: LogEntry,
    matched_labels: set[str],
    rule: IssueSignalRule,
) -> bool:
    if (log.level or "").upper() not in {"ERROR", "CRITICAL", "FATAL", "WARN", "WARNING"}:
        return False
    return any(
        pattern.evidence and pattern.label in matched_labels and pattern.weight >= 0.8
        for pattern in rule.patterns
    )


def _apply_root_cause_ranking(scores: dict[str, float]) -> dict[str, float]:
    adjusted = dict(scores)
    root_cause_issues = {
        issue
        for issue in adjusted
        if issue not in {"server_error", "timeout_issue"}
    }
    if root_cause_issues and "server_error" in adjusted:
        adjusted["server_error"] *= 0.55
    if {"database_issue", "timeout_issue"} <= set(adjusted):
        adjusted["timeout_issue"] *= 0.75
    if {"auth_issue", "timeout_issue"} <= set(adjusted):
        adjusted["timeout_issue"] *= 0.85
    return adjusted


def _select_evidence_logs(
    logs: list[LogEntry],
    primary_issue: str,
    evidence_by_issue: dict[str, list[LogEntry]],
    matched_issues: list[str],
) -> list[LogEntry]:
    selected: list[LogEntry] = []
    selected.extend(evidence_by_issue.get(primary_issue, []))
    for issue in matched_issues:
        if issue == primary_issue:
            continue
        selected.extend(evidence_by_issue.get(issue, [])[:2])
    if selected:
        return _unique_logs(selected)[:8]
    return _unique_logs(
        log for log in logs if (log.level or "").upper() in {"ERROR", "CRITICAL", "FATAL"}
    )[:5]


def _confidence(issue_type: str, scores: dict[str, float]) -> float:
    if not scores or issue_type not in scores:
        return 0.0
    total = sum(scores.values())
    share = scores[issue_type] / total if total else 0.0
    absolute = min(scores[issue_type] / 7.0, 1.0)
    return round(min(0.95, 0.35 + share * 0.4 + absolute * 0.25), 2)


def _unique_logs(logs) -> list[LogEntry]:
    seen: set[int] = set()
    unique_logs: list[LogEntry] = []
    for log in logs:
        key = log.id or id(log)
        if key not in seen:
            seen.add(key)
            unique_logs.append(log)
    return unique_logs
