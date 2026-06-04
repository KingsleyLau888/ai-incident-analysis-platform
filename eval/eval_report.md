# Eval Report

Total cases: 7

## Metrics

- issue_type_accuracy: 100.00%
- severity_accuracy: 100.00%
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- similar_incident_retrieval_recall: 100.00%
- average_latency_ms: 13.15

## Cases

### database-payment-mysql-timeout

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, server_error.md, timeout_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- similar_incident_retrieval_recall: 100.00%
- latency_ms: 31.44
- passed: True

### timeout-checkout-upstream

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: timeout_issue.md, timeout_issue.md, server_error.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, server_error, auth_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- similar_incident_retrieval_recall: 100.00%
- latency_ms: 11.39
- passed: True

### auth-token-rejected

- expected_issue_type: auth_issue
- actual_issue_type: auth_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: auth_issue.md
- actual_runbook_sources: auth_issue.md, auth_issue.md, auth_issue.md
- expected_similar_issue_types: auth_issue
- actual_similar_issue_types: auth_issue, server_error, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- similar_incident_retrieval_recall: 100.00%
- latency_ms: 10.40
- passed: True

### cache-redis-connection

- expected_issue_type: cache_issue
- actual_issue_type: cache_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: cache_issue.md
- actual_runbook_sources: cache_issue.md, cache_issue.md, cache_issue.md
- expected_similar_issue_types: cache_issue
- actual_similar_issue_types: cache_issue, timeout_issue, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- similar_incident_retrieval_recall: 100.00%
- latency_ms: 10.44
- passed: True

### memory-worker-oom

- expected_issue_type: memory_issue
- actual_issue_type: memory_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: memory_issue.md
- actual_runbook_sources: memory_issue.md, memory_issue.md, server_error.md
- expected_similar_issue_types: memory_issue
- actual_similar_issue_types: memory_issue, server_error, cache_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- similar_incident_retrieval_recall: 100.00%
- latency_ms: 10.36
- passed: True

### server-error-api-500

- expected_issue_type: server_error
- actual_issue_type: server_error
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: server_error.md
- actual_runbook_sources: server_error.md, server_error.md, timeout_issue.md
- expected_similar_issue_types: server_error
- actual_similar_issue_types: server_error, database_issue, timeout_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- similar_incident_retrieval_recall: 100.00%
- latency_ms: 10.31
- passed: True

### unknown-benign-warning

- expected_issue_type: unknown
- actual_issue_type: unknown
- expected_severity: low
- actual_severity: low
- expected_runbook_sources: (none)
- actual_runbook_sources: (none)
- expected_similar_issue_types: (none)
- actual_similar_issue_types: (none)
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- similar_incident_retrieval_recall: 100.00%
- latency_ms: 7.72
- passed: True

## Failed Cases

- None
