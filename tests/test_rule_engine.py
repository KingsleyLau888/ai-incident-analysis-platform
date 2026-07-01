from app.models.log_entry import LogEntry
from app.rule_engine.detector import detect_issue


def _log(message: str, level: str = "ERROR") -> LogEntry:
    log = LogEntry(service_id=1, level=level, message=message)
    log.id = abs(hash(message)) % 100000
    return log


def test_signal_detector_ranks_database_above_surface_500_and_timeout():
    result = detect_issue(
        [
            _log("Checkout API returned 500 after database write failure"),
            _log("DBConnectionTimeout while connecting to shop-primary"),
            _log("Payment request timed out after retry"),
        ]
    )

    assert result.issue_type == "database_issue"
    assert "database_issue" in result.matched_issues
    assert "server_error" in result.matched_issues
    assert "timeout_issue" in result.matched_issues
    assert result.confidence > 0.5
    assert result.candidate_scores
    assert result.candidate_scores["database_issue"] > result.candidate_scores["server_error"]
    assert len(result.evidence_logs) >= 2


def test_signal_detector_keeps_unknown_for_benign_logs():
    result = detect_issue(
        [
            _log("Checkout started request_id=abc", "INFO"),
            _log("Order created and paid request_id=abc", "INFO"),
        ]
    )

    assert result.issue_type == "unknown"
    assert result.confidence == 0.0
    assert result.evidence_logs == []
