# Eval Report

Total cases: 14

## Metrics

- issue_type_accuracy: 71.43%
- severity_accuracy: 78.57%
- evidence_recall: 92.86%
- runbook_retrieval_recall: 85.71%
- runbook_top1_accuracy: 71.43%
- runbook_precision_at_3: 61.90%
- similar_incident_retrieval_recall: 85.71%
- similar_incident_top1_accuracy: 78.57%
- similar_incident_precision_at_3: 45.24%
- failed_case_count: 4
- average_latency_ms: 16.25

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
- runbook_top1_correct: True
- runbook_precision_at_3: 33.33%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 37.08
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
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 33.33%
- latency_ms: 13.96
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
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 33.33%
- latency_ms: 13.48
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
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 33.33%
- latency_ms: 12.65
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
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 33.33%
- latency_ms: 17.11
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
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 33.33%
- latency_ms: 15.42
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
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 12.04
- passed: True

### hard-mixed-database-timeout-primary-timeout

- expected_issue_type: timeout_issue
- actual_issue_type: database_issue
- expected_severity: medium
- actual_severity: high
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: timeout_issue.md, timeout_issue.md, database_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, server_error, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 33.33%
- latency_ms: 16.63
- passed: False

### hard-server-error-symptom-database-root-cause

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: server_error.md, server_error.md, database_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, server_error
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 33.33%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 18.31
- passed: True

### hard-auth-with-timeout-interference

- expected_issue_type: auth_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: auth_issue.md
- actual_runbook_sources: timeout_issue.md, auth_issue.md, timeout_issue.md
- expected_similar_issue_types: auth_issue
- actual_similar_issue_types: timeout_issue, auth_issue, server_error
- evidence_recall: 0.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 33.33%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: False
- similar_incident_precision_at_3: 33.33%
- latency_ms: 14.62
- passed: False

### hard-cache-warning-not-incident

- expected_issue_type: unknown
- actual_issue_type: cache_issue
- expected_severity: low
- actual_severity: medium
- expected_runbook_sources: (none)
- actual_runbook_sources: cache_issue.md, cache_issue.md, cache_issue.md
- expected_similar_issue_types: (none)
- actual_similar_issue_types: cache_issue, database_issue, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 0.00%
- similar_incident_top1_correct: False
- similar_incident_precision_at_3: 0.00%
- latency_ms: 14.17
- passed: False

### hard-memory-warning-without-oom

- expected_issue_type: unknown
- actual_issue_type: memory_issue
- expected_severity: low
- actual_severity: high
- expected_runbook_sources: (none)
- actual_runbook_sources: memory_issue.md, cache_issue.md, memory_issue.md
- expected_similar_issue_types: (none)
- actual_similar_issue_types: memory_issue, database_issue, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 0.00%
- similar_incident_top1_correct: False
- similar_incident_precision_at_3: 0.00%
- latency_ms: 17.04
- passed: False

### hard-unknown-error-like-wording

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
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 12.26
- passed: True

### hard-similar-incident-top3-challenge

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: timeout_issue.md, timeout_issue.md, timeout_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, database_issue, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 33.33%
- latency_ms: 12.75
- passed: True

## Failed Cases

- hard-mixed-database-timeout-primary-timeout
- hard-auth-with-timeout-interference
- hard-cache-warning-not-incident
- hard-memory-warning-without-oom

## Error Analysis

### hard-mixed-database-timeout-primary-timeout

- failure_category: rule_detection
- expected: issue_type=timeout_issue, severity=medium, runbooks=['timeout_issue.md'], similar_types=['timeout_issue']
- actual: issue_type=database_issue, severity=high, runbooks=['timeout_issue.md', 'timeout_issue.md', 'database_issue.md'], similar_types=['timeout_issue', 'server_error', 'database_issue']
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification.

### hard-auth-with-timeout-interference

- failure_category: rule_detection, evidence_selection
- expected: issue_type=auth_issue, severity=medium, runbooks=['auth_issue.md'], similar_types=['auth_issue']
- actual: issue_type=timeout_issue, severity=medium, runbooks=['timeout_issue.md', 'auth_issue.md', 'timeout_issue.md'], similar_types=['timeout_issue', 'auth_issue', 'server_error']
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification. Expected evidence keywords were not present in the selected evidence logs.

### hard-cache-warning-not-incident

- failure_category: rule_detection, runbook_retrieval, similar_incident_retrieval
- expected: issue_type=unknown, severity=low, runbooks=[], similar_types=[]
- actual: issue_type=cache_issue, severity=medium, runbooks=['cache_issue.md', 'cache_issue.md', 'cache_issue.md'], similar_types=['cache_issue', 'database_issue', 'database_issue']
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification. The expected runbook source was missing from the retrieved top results. The expected historical issue type was missing from the retrieved top results.

### hard-memory-warning-without-oom

- failure_category: rule_detection, runbook_retrieval, similar_incident_retrieval
- expected: issue_type=unknown, severity=low, runbooks=[], similar_types=[]
- actual: issue_type=memory_issue, severity=high, runbooks=['memory_issue.md', 'cache_issue.md', 'memory_issue.md'], similar_types=['memory_issue', 'database_issue', 'database_issue']
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification. The expected runbook source was missing from the retrieved top results. The expected historical issue type was missing from the retrieved top results.

