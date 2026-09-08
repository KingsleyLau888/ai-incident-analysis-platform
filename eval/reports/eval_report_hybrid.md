# Eval Report

Retrieval mode: hybrid
Effective retrieval modes: hybrid
LLM Judge: disabled

Total cases: 27

## Metrics

- issue_type_accuracy: 92.59%
- severity_accuracy: 92.59%
- evidence_recall: 92.59%
- runbook_retrieval_recall: 83.33%
- runbook_top1_accuracy: 92.59%
- runbook_precision_at_3: 77.78%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_accuracy: 100.00%
- similar_incident_precision_at_3: 97.53%
- failed_case_count: 10
- average_latency_ms: 2217.56

## Cases

### database-payment-mysql-timeout

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, database_issue.md, database_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 3261.53
- passed: True
- failure_categories: none

### timeout-checkout-upstream

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: timeout_issue.md, timeout_issue.md, payment_provider_timeout.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 3014.37
- passed: True
- failure_categories: none

### auth-token-rejected

- expected_issue_type: auth_issue
- actual_issue_type: auth_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: auth_issue.md
- actual_runbook_sources: auth_issue.md, auth_issue.md, token_signing_key_rotation.md
- expected_similar_issue_types: auth_issue
- actual_similar_issue_types: auth_issue, auth_issue, auth_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2604.40
- passed: True
- failure_categories: none

### cache-redis-connection

- expected_issue_type: cache_issue
- actual_issue_type: cache_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: cache_issue.md
- actual_runbook_sources: cache_issue.md, cache_issue.md, cache_stampede.md
- expected_similar_issue_types: cache_issue
- actual_similar_issue_types: cache_issue, cache_issue, cache_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 1972.72
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
- actual_similar_issue_types: memory_issue, memory_issue, memory_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 1246.40
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
- actual_similar_issue_types: server_error, server_error, database_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 1757.26
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
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 22.79
- passed: True
- failure_categories: none

### hard-mixed-database-timeout-primary-timeout

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: timeout_issue.md, timeout_issue.md, timeout_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 3052.11
- passed: True
- failure_categories: none

### hard-server-error-symptom-database-root-cause

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, database_issue.md, postgres_primary_unavailable.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 3156.95
- passed: True
- failure_categories: none

### hard-auth-with-timeout-interference

- expected_issue_type: auth_issue
- actual_issue_type: auth_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: auth_issue.md
- actual_runbook_sources: auth_issue.md, token_signing_key_rotation.md, oauth_callback_failure.md
- expected_similar_issue_types: auth_issue
- actual_similar_issue_types: auth_issue, auth_issue, auth_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 33.33%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2641.51
- passed: True
- failure_categories: none

### hard-cache-warning-not-incident

- expected_issue_type: unknown
- actual_issue_type: cache_issue
- expected_severity: low
- actual_severity: medium
- expected_runbook_sources: (none)
- actual_runbook_sources: cache_issue.md, cache_issue.md, cache_issue.md
- expected_similar_issue_types: (none)
- actual_similar_issue_types: (none)
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 749.59
- passed: False
- failure_categories: rule_detection, runbook_retrieval

### hard-memory-warning-without-oom

- expected_issue_type: unknown
- actual_issue_type: memory_issue
- expected_severity: low
- actual_severity: high
- expected_runbook_sources: (none)
- actual_runbook_sources: memory_issue.md, memory_issue.md, memory_issue.md
- expected_similar_issue_types: (none)
- actual_similar_issue_types: (none)
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 252.30
- passed: False
- failure_categories: rule_detection, runbook_retrieval

### hard-unknown-error-like-wording

- expected_issue_type: unknown
- actual_issue_type: unknown
- expected_severity: low
- actual_severity: low
- expected_runbook_sources: (none)
- actual_runbook_sources: (none)
- expected_similar_issue_types: (none)
- actual_similar_issue_types: (none)
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 17.63
- passed: True
- failure_categories: none

### hard-similar-incident-top3-challenge

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: timeout_issue.md, timeout_issue.md, payment_provider_timeout.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2997.65
- passed: True
- failure_categories: none

### adversarial-contradictory-signals

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: timeout_issue.md, payment_provider_timeout.md, timeout_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 50.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2980.64
- passed: False
- failure_categories: evidence_selection

### adversarial-noise-injection

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, database_issue.md, database_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 3200.60
- passed: True
- failure_categories: none

### adversarial-misleading-first-signal

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, database_issue.md, postgres_primary_unavailable.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 3155.74
- passed: True
- failure_categories: none

### rag-natural-language-payment-provider

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: payment_provider_timeout.md, timeout_issue.md
- actual_runbook_sources: timeout_issue.md, payment_provider_timeout.md, payment_provider_timeout.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2981.68
- passed: True
- failure_categories: none

### rag-config-secret-database

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: config_secret_mismatch.md, postgres_primary_unavailable.md, database_issue.md
- actual_runbook_sources: postgres_primary_unavailable.md, database_issue.md, postgres_primary_unavailable.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 66.67%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 3182.50
- passed: False
- failure_categories: runbook_retrieval

### rag-network-policy-postgres

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: firewall_policy_block.md, postgres_primary_unavailable.md, database_issue.md
- actual_runbook_sources: firewall_policy_block.md, firewall_policy_block.md, postgres_primary_unavailable.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 66.67%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 3127.38
- passed: False
- failure_categories: runbook_retrieval

### rag-oauth-callback-login

- expected_issue_type: auth_issue
- actual_issue_type: auth_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: oauth_callback_failure.md, auth_issue.md
- actual_runbook_sources: oauth_callback_failure.md, token_signing_key_rotation.md, auth_issue.md
- expected_similar_issue_types: auth_issue
- actual_similar_issue_types: auth_issue, auth_issue, auth_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2594.98
- passed: True
- failure_categories: none

### rag-redis-secret-cache

- expected_issue_type: cache_issue
- actual_issue_type: cache_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: config_secret_mismatch.md, redis_primary_failover.md, cache_issue.md
- actual_runbook_sources: cache_issue.md, cache_issue.md, cache_stampede.md
- expected_similar_issue_types: cache_issue
- actual_similar_issue_types: cache_issue, cache_issue, cache_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 33.33%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 1999.41
- passed: False
- failure_categories: runbook_retrieval

### rag-cache-stampede-database-noise

- expected_issue_type: cache_issue
- actual_issue_type: cache_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: cache_stampede.md, cache_issue.md
- actual_runbook_sources: cache_stampede.md, cache_stampede.md, cache_stampede.md
- expected_similar_issue_types: cache_issue
- actual_similar_issue_types: cache_issue, timeout_issue, cache_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 50.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 2027.55
- passed: False
- failure_categories: runbook_retrieval

### rag-bad-release-serialization

- expected_issue_type: server_error
- actual_issue_type: server_error
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: bad_release_rollback.md, server_error.md
- actual_runbook_sources: server_error.md, bad_release_rollback.md, bad_release_rollback.md
- expected_similar_issue_types: server_error
- actual_similar_issue_types: server_error, server_error, server_error
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 50.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 1790.82
- passed: False
- failure_categories: evidence_selection

### rag-queue-lag-not-db

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: message_queue_lag.md, timeout_issue.md
- actual_runbook_sources: message_queue_lag.md, timeout_issue.md, timeout_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 50.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 3007.33
- passed: False
- failure_categories: evidence_selection

### rag-dns-provider-timeout

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: dns_resolution_failure.md, third_party_api_degradation.md, payment_provider_timeout.md
- actual_runbook_sources: payment_provider_timeout.md, timeout_issue.md, payment_provider_timeout.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 50.00%
- runbook_retrieval_recall: 33.33%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 3051.94
- passed: False
- failure_categories: evidence_selection, runbook_retrieval

### rag-benign-rate-limit-warning

- expected_issue_type: unknown
- actual_issue_type: unknown
- expected_severity: low
- actual_severity: low
- expected_runbook_sources: (none)
- actual_runbook_sources: (none)
- expected_similar_issue_types: (none)
- actual_similar_issue_types: (none)
- runbook_effective_retrieval_mode: hybrid
- similar_effective_retrieval_mode: hybrid
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 26.21
- passed: True
- failure_categories: none

## Failed Cases

- hard-cache-warning-not-incident
- hard-memory-warning-without-oom
- adversarial-contradictory-signals
- rag-config-secret-database
- rag-network-policy-postgres
- rag-redis-secret-cache
- rag-cache-stampede-database-noise
- rag-bad-release-serialization
- rag-queue-lag-not-db
- rag-dns-provider-timeout

## Error Analysis

### hard-cache-warning-not-incident

- failure_category: rule_detection, runbook_retrieval
- expected: issue_type=unknown, severity=low, runbooks=[], similar_types=[]
- actual: issue_type=cache_issue, severity=medium, runbooks=['cache_issue.md', 'cache_issue.md', 'cache_issue.md'], similar_types=[]
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification. The expected runbook source was missing from the retrieved top results.

### hard-memory-warning-without-oom

- failure_category: rule_detection, runbook_retrieval
- expected: issue_type=unknown, severity=low, runbooks=[], similar_types=[]
- actual: issue_type=memory_issue, severity=high, runbooks=['memory_issue.md', 'memory_issue.md', 'memory_issue.md'], similar_types=[]
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification. The expected runbook source was missing from the retrieved top results.

### adversarial-contradictory-signals

- failure_category: evidence_selection
- expected: issue_type=timeout_issue, severity=medium, runbooks=['timeout_issue.md'], similar_types=['timeout_issue']
- actual: issue_type=timeout_issue, severity=medium, runbooks=['timeout_issue.md', 'payment_provider_timeout.md', 'timeout_issue.md'], similar_types=['timeout_issue', 'timeout_issue', 'timeout_issue']
- possible_failure_reason: Expected evidence keywords were not present in the selected evidence logs.

### rag-config-secret-database

- failure_category: runbook_retrieval
- expected: issue_type=database_issue, severity=high, runbooks=['config_secret_mismatch.md', 'postgres_primary_unavailable.md', 'database_issue.md'], similar_types=['database_issue']
- actual: issue_type=database_issue, severity=high, runbooks=['postgres_primary_unavailable.md', 'database_issue.md', 'postgres_primary_unavailable.md'], similar_types=['database_issue', 'database_issue', 'database_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-network-policy-postgres

- failure_category: runbook_retrieval
- expected: issue_type=database_issue, severity=high, runbooks=['firewall_policy_block.md', 'postgres_primary_unavailable.md', 'database_issue.md'], similar_types=['database_issue']
- actual: issue_type=database_issue, severity=high, runbooks=['firewall_policy_block.md', 'firewall_policy_block.md', 'postgres_primary_unavailable.md'], similar_types=['database_issue', 'database_issue', 'database_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-redis-secret-cache

- failure_category: runbook_retrieval
- expected: issue_type=cache_issue, severity=medium, runbooks=['config_secret_mismatch.md', 'redis_primary_failover.md', 'cache_issue.md'], similar_types=['cache_issue']
- actual: issue_type=cache_issue, severity=medium, runbooks=['cache_issue.md', 'cache_issue.md', 'cache_stampede.md'], similar_types=['cache_issue', 'cache_issue', 'cache_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-cache-stampede-database-noise

- failure_category: runbook_retrieval
- expected: issue_type=cache_issue, severity=medium, runbooks=['cache_stampede.md', 'cache_issue.md'], similar_types=['cache_issue']
- actual: issue_type=cache_issue, severity=medium, runbooks=['cache_stampede.md', 'cache_stampede.md', 'cache_stampede.md'], similar_types=['cache_issue', 'timeout_issue', 'cache_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-bad-release-serialization

- failure_category: evidence_selection
- expected: issue_type=server_error, severity=high, runbooks=['bad_release_rollback.md', 'server_error.md'], similar_types=['server_error']
- actual: issue_type=server_error, severity=high, runbooks=['server_error.md', 'bad_release_rollback.md', 'bad_release_rollback.md'], similar_types=['server_error', 'server_error', 'server_error']
- possible_failure_reason: Expected evidence keywords were not present in the selected evidence logs.

### rag-queue-lag-not-db

- failure_category: evidence_selection
- expected: issue_type=timeout_issue, severity=medium, runbooks=['message_queue_lag.md', 'timeout_issue.md'], similar_types=['timeout_issue']
- actual: issue_type=timeout_issue, severity=medium, runbooks=['message_queue_lag.md', 'timeout_issue.md', 'timeout_issue.md'], similar_types=['timeout_issue', 'timeout_issue', 'timeout_issue']
- possible_failure_reason: Expected evidence keywords were not present in the selected evidence logs.

### rag-dns-provider-timeout

- failure_category: evidence_selection, runbook_retrieval
- expected: issue_type=timeout_issue, severity=medium, runbooks=['dns_resolution_failure.md', 'third_party_api_degradation.md', 'payment_provider_timeout.md'], similar_types=['timeout_issue']
- actual: issue_type=timeout_issue, severity=medium, runbooks=['payment_provider_timeout.md', 'timeout_issue.md', 'payment_provider_timeout.md'], similar_types=['timeout_issue', 'timeout_issue', 'timeout_issue']
- possible_failure_reason: Expected evidence keywords were not present in the selected evidence logs. The expected runbook source was missing from the retrieved top results.

