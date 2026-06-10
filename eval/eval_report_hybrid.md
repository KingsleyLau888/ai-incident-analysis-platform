# Eval Report

Retrieval mode: hybrid
LLM Judge: disabled

Total cases: 17

## Metrics

- issue_type_accuracy: 70.59%
- severity_accuracy: 76.47%
- evidence_recall: 91.18%
- runbook_retrieval_recall: 70.59%
- runbook_top1_accuracy: 70.59%
- runbook_precision_at_3: 70.59%
- similar_incident_retrieval_recall: 88.24%
- similar_incident_top1_accuracy: 76.47%
- similar_incident_precision_at_3: 47.06%
- failed_case_count: 5
- average_latency_ms: 516.01

## Cases

### database-payment-mysql-timeout

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, database_issue.md, database_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, timeout_issue, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 582.00
- passed: True
- failure_categories: none

### timeout-checkout-upstream

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
- latency_ms: 598.99
- passed: True
- failure_categories: none

### auth-token-rejected

- expected_issue_type: auth_issue
- actual_issue_type: auth_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: auth_issue.md
- actual_runbook_sources: auth_issue.md, auth_issue.md, auth_issue.md
- expected_similar_issue_types: auth_issue
- actual_similar_issue_types: auth_issue, database_issue, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 33.33%
- latency_ms: 625.50
- passed: True
- failure_categories: none

### cache-redis-connection

- expected_issue_type: cache_issue
- actual_issue_type: cache_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: cache_issue.md
- actual_runbook_sources: cache_issue.md, cache_issue.md, cache_issue.md
- expected_similar_issue_types: cache_issue
- actual_similar_issue_types: cache_issue, auth_issue, timeout_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 33.33%
- latency_ms: 579.55
- passed: True
- failure_categories: none

### memory-worker-oom

- expected_issue_type: memory_issue
- actual_issue_type: memory_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: memory_issue.md
- actual_runbook_sources: memory_issue.md, memory_issue.md, memory_issue.md
- expected_similar_issue_types: memory_issue
- actual_similar_issue_types: memory_issue, cache_issue, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 33.33%
- latency_ms: 577.17
- passed: True
- failure_categories: none

### server-error-api-500

- expected_issue_type: server_error
- actual_issue_type: server_error
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: server_error.md
- actual_runbook_sources: server_error.md, server_error.md, server_error.md
- expected_similar_issue_types: server_error
- actual_similar_issue_types: server_error, database_issue, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 33.33%
- latency_ms: 586.90
- passed: True
- failure_categories: none

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
- latency_ms: 8.37
- passed: True
- failure_categories: none

### hard-mixed-database-timeout-primary-timeout

- expected_issue_type: timeout_issue
- actual_issue_type: database_issue
- expected_severity: medium
- actual_severity: high
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: database_issue.md, database_issue.md, database_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: database_issue, database_issue, timeout_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: False
- similar_incident_precision_at_3: 33.33%
- latency_ms: 593.60
- passed: False
- failure_categories: rule_detection, runbook_retrieval

### hard-server-error-symptom-database-root-cause

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, database_issue.md, database_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 570.58
- passed: True
- failure_categories: none

### hard-auth-with-timeout-interference

- expected_issue_type: auth_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: auth_issue.md
- actual_runbook_sources: timeout_issue.md, timeout_issue.md, timeout_issue.md
- expected_similar_issue_types: auth_issue
- actual_similar_issue_types: auth_issue, database_issue, database_issue
- evidence_recall: 0.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 33.33%
- latency_ms: 568.01
- passed: False
- failure_categories: rule_detection, evidence_selection, runbook_retrieval

### hard-cache-warning-not-incident

- expected_issue_type: unknown
- actual_issue_type: cache_issue
- expected_severity: low
- actual_severity: medium
- expected_runbook_sources: (none)
- actual_runbook_sources: cache_issue.md, cache_issue.md, cache_issue.md
- expected_similar_issue_types: (none)
- actual_similar_issue_types: cache_issue, timeout_issue, database_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 0.00%
- similar_incident_top1_correct: False
- similar_incident_precision_at_3: 0.00%
- latency_ms: 588.25
- passed: False
- failure_categories: rule_detection, runbook_retrieval, similar_incident_retrieval

### hard-memory-warning-without-oom

- expected_issue_type: unknown
- actual_issue_type: memory_issue
- expected_severity: low
- actual_severity: high
- expected_runbook_sources: (none)
- actual_runbook_sources: memory_issue.md, memory_issue.md, memory_issue.md
- expected_similar_issue_types: (none)
- actual_similar_issue_types: memory_issue, database_issue, cache_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 0.00%
- similar_incident_top1_correct: False
- similar_incident_precision_at_3: 0.00%
- latency_ms: 580.64
- passed: False
- failure_categories: rule_detection, runbook_retrieval, similar_incident_retrieval

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
- latency_ms: 8.60
- passed: True
- failure_categories: none

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
- latency_ms: 604.28
- passed: True
- failure_categories: none

### adversarial-contradictory-signals

- expected_issue_type: timeout_issue
- actual_issue_type: database_issue
- expected_severity: medium
- actual_severity: high
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: database_issue.md, database_issue.md, database_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: database_issue, database_issue, timeout_issue
- evidence_recall: 50.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: False
- similar_incident_precision_at_3: 33.33%
- latency_ms: 561.66
- passed: False
- failure_categories: rule_detection, evidence_selection, runbook_retrieval

### adversarial-noise-injection

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, database_issue.md, database_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, timeout_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 554.76
- passed: True
- failure_categories: none

### adversarial-misleading-first-signal

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, database_issue.md, database_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, timeout_issue
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 583.37
- passed: True
- failure_categories: none

## Failed Cases

- hard-mixed-database-timeout-primary-timeout
- hard-auth-with-timeout-interference
- hard-cache-warning-not-incident
- hard-memory-warning-without-oom
- adversarial-contradictory-signals

## Error Analysis

### hard-mixed-database-timeout-primary-timeout

- failure_category: rule_detection, runbook_retrieval
- expected: issue_type=timeout_issue, severity=medium, runbooks=['timeout_issue.md'], similar_types=['timeout_issue']
- actual: issue_type=database_issue, severity=high, runbooks=['database_issue.md', 'database_issue.md', 'database_issue.md'], similar_types=['database_issue', 'database_issue', 'timeout_issue']
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification. The expected runbook source was missing from the retrieved top results.

### hard-auth-with-timeout-interference

- failure_category: rule_detection, evidence_selection, runbook_retrieval
- expected: issue_type=auth_issue, severity=medium, runbooks=['auth_issue.md'], similar_types=['auth_issue']
- actual: issue_type=timeout_issue, severity=medium, runbooks=['timeout_issue.md', 'timeout_issue.md', 'timeout_issue.md'], similar_types=['auth_issue', 'database_issue', 'database_issue']
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification. Expected evidence keywords were not present in the selected evidence logs. The expected runbook source was missing from the retrieved top results.

### hard-cache-warning-not-incident

- failure_category: rule_detection, runbook_retrieval, similar_incident_retrieval
- expected: issue_type=unknown, severity=low, runbooks=[], similar_types=[]
- actual: issue_type=cache_issue, severity=medium, runbooks=['cache_issue.md', 'cache_issue.md', 'cache_issue.md'], similar_types=['cache_issue', 'timeout_issue', 'database_issue']
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification. The expected runbook source was missing from the retrieved top results. The expected historical issue type was missing from the retrieved top results.

### hard-memory-warning-without-oom

- failure_category: rule_detection, runbook_retrieval, similar_incident_retrieval
- expected: issue_type=unknown, severity=low, runbooks=[], similar_types=[]
- actual: issue_type=memory_issue, severity=high, runbooks=['memory_issue.md', 'memory_issue.md', 'memory_issue.md'], similar_types=['memory_issue', 'database_issue', 'cache_issue']
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification. The expected runbook source was missing from the retrieved top results. The expected historical issue type was missing from the retrieved top results.

### adversarial-contradictory-signals

- failure_category: rule_detection, evidence_selection, runbook_retrieval
- expected: issue_type=timeout_issue, severity=medium, runbooks=['timeout_issue.md'], similar_types=['timeout_issue']
- actual: issue_type=database_issue, severity=high, runbooks=['database_issue.md', 'database_issue.md', 'database_issue.md'], similar_types=['database_issue', 'database_issue', 'timeout_issue']
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification. Expected evidence keywords were not present in the selected evidence logs. The expected runbook source was missing from the retrieved top results.

