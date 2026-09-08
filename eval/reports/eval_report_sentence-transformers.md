# Eval Report

Retrieval mode: sentence-transformers
Effective retrieval modes: sentence-transformers
LLM Judge: disabled

Total cases: 27

## Metrics

- issue_type_accuracy: 92.59%
- severity_accuracy: 92.59%
- evidence_recall: 92.59%
- runbook_retrieval_recall: 69.14%
- runbook_top1_accuracy: 81.48%
- runbook_precision_at_3: 72.84%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_accuracy: 96.30%
- similar_incident_precision_at_3: 91.36%
- failed_case_count: 14
- average_latency_ms: 2570.23

## Cases

### database-payment-mysql-timeout

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, database_issue.md, firewall_policy_block.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, timeout_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 13559.85
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
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2996.99
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
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2559.90
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
- actual_similar_issue_types: cache_issue, cache_issue, cache_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 1930.41
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
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 1261.61
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
- actual_similar_issue_types: server_error, server_error, server_error
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 1772.84
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
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 22.13
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
- actual_similar_issue_types: database_issue, database_issue, timeout_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: False
- similar_incident_precision_at_3: 33.33%
- latency_ms: 2893.02
- passed: True
- failure_categories: none

### hard-server-error-symptom-database-root-cause

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: postgres_primary_unavailable.md, postgres_primary_unavailable.md, postgres_primary_unavailable.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 3146.13
- passed: False
- failure_categories: runbook_retrieval

### hard-auth-with-timeout-interference

- expected_issue_type: auth_issue
- actual_issue_type: auth_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: auth_issue.md
- actual_runbook_sources: token_signing_key_rotation.md, auth_issue.md, oauth_callback_failure.md
- expected_similar_issue_types: auth_issue
- actual_similar_issue_types: auth_issue, auth_issue, auth_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 33.33%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2582.82
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
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 717.91
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
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 263.31
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
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 19.94
- passed: True
- failure_categories: none

### hard-similar-incident-top3-challenge

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: timeout_issue.md, payment_provider_timeout.md, payment_retry_storm.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 33.33%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2965.44
- passed: True
- failure_categories: none

### adversarial-contradictory-signals

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: timeout_issue.md, payment_provider_timeout.md, payment_provider_timeout.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 50.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 33.33%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2995.18
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
- actual_similar_issue_types: database_issue, database_issue, timeout_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 3162.04
- passed: True
- failure_categories: none

### adversarial-misleading-first-signal

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: postgres_primary_unavailable.md, postgres_primary_unavailable.md, auth_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, timeout_issue, database_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 3156.04
- passed: False
- failure_categories: runbook_retrieval

### rag-natural-language-payment-provider

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: payment_provider_timeout.md, timeout_issue.md
- actual_runbook_sources: payment_provider_timeout.md, payment_provider_timeout.md, payment_provider_timeout.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 50.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2994.47
- passed: False
- failure_categories: runbook_retrieval

### rag-config-secret-database

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: config_secret_mismatch.md, postgres_primary_unavailable.md, database_issue.md
- actual_runbook_sources: postgres_primary_unavailable.md, auth_issue.md, postgres_primary_unavailable.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 33.33%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 3142.49
- passed: False
- failure_categories: runbook_retrieval

### rag-network-policy-postgres

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: firewall_policy_block.md, postgres_primary_unavailable.md, database_issue.md
- actual_runbook_sources: postgres_primary_unavailable.md, postgres_primary_unavailable.md, postgres_primary_unavailable.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, timeout_issue, database_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 33.33%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 3160.10
- passed: False
- failure_categories: runbook_retrieval

### rag-oauth-callback-login

- expected_issue_type: auth_issue
- actual_issue_type: auth_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: oauth_callback_failure.md, auth_issue.md
- actual_runbook_sources: oauth_callback_failure.md, oauth_callback_failure.md, oauth_callback_failure.md
- expected_similar_issue_types: auth_issue
- actual_similar_issue_types: auth_issue, auth_issue, auth_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 50.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2547.96
- passed: False
- failure_categories: runbook_retrieval

### rag-redis-secret-cache

- expected_issue_type: cache_issue
- actual_issue_type: cache_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: config_secret_mismatch.md, redis_primary_failover.md, cache_issue.md
- actual_runbook_sources: cache_issue.md, cache_issue.md, cache_issue.md
- expected_similar_issue_types: cache_issue
- actual_similar_issue_types: cache_issue, cache_issue, cache_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 33.33%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 1962.03
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
- actual_similar_issue_types: cache_issue, server_error, cache_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 50.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 1961.44
- passed: False
- failure_categories: runbook_retrieval

### rag-bad-release-serialization

- expected_issue_type: server_error
- actual_issue_type: server_error
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: bad_release_rollback.md, server_error.md
- actual_runbook_sources: server_error.md, server_error.md, server_error.md
- expected_similar_issue_types: server_error
- actual_similar_issue_types: server_error, server_error, server_error
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 50.00%
- runbook_retrieval_recall: 50.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 1715.58
- passed: False
- failure_categories: evidence_selection, runbook_retrieval

### rag-queue-lag-not-db

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: message_queue_lag.md, timeout_issue.md
- actual_runbook_sources: message_queue_lag.md, timeout_issue.md, message_queue_lag.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 50.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2940.39
- passed: False
- failure_categories: evidence_selection

### rag-dns-provider-timeout

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: dns_resolution_failure.md, third_party_api_degradation.md, payment_provider_timeout.md
- actual_runbook_sources: payment_provider_timeout.md, payment_provider_timeout.md, dns_resolution_failure.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 50.00%
- runbook_retrieval_recall: 66.67%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 2940.94
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
- runbook_effective_retrieval_mode: sentence-transformers
- similar_effective_retrieval_mode: sentence-transformers
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 25.29
- passed: True
- failure_categories: none

## Failed Cases

- hard-server-error-symptom-database-root-cause
- hard-cache-warning-not-incident
- hard-memory-warning-without-oom
- adversarial-contradictory-signals
- adversarial-misleading-first-signal
- rag-natural-language-payment-provider
- rag-config-secret-database
- rag-network-policy-postgres
- rag-oauth-callback-login
- rag-redis-secret-cache
- rag-cache-stampede-database-noise
- rag-bad-release-serialization
- rag-queue-lag-not-db
- rag-dns-provider-timeout

## Error Analysis

### hard-server-error-symptom-database-root-cause

- failure_category: runbook_retrieval
- expected: issue_type=database_issue, severity=high, runbooks=['database_issue.md'], similar_types=['database_issue']
- actual: issue_type=database_issue, severity=high, runbooks=['postgres_primary_unavailable.md', 'postgres_primary_unavailable.md', 'postgres_primary_unavailable.md'], similar_types=['database_issue', 'database_issue', 'database_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

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
- actual: issue_type=timeout_issue, severity=medium, runbooks=['timeout_issue.md', 'payment_provider_timeout.md', 'payment_provider_timeout.md'], similar_types=['timeout_issue', 'timeout_issue', 'timeout_issue']
- possible_failure_reason: Expected evidence keywords were not present in the selected evidence logs.

### adversarial-misleading-first-signal

- failure_category: runbook_retrieval
- expected: issue_type=database_issue, severity=high, runbooks=['database_issue.md'], similar_types=['database_issue']
- actual: issue_type=database_issue, severity=high, runbooks=['postgres_primary_unavailable.md', 'postgres_primary_unavailable.md', 'auth_issue.md'], similar_types=['database_issue', 'timeout_issue', 'database_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-natural-language-payment-provider

- failure_category: runbook_retrieval
- expected: issue_type=timeout_issue, severity=medium, runbooks=['payment_provider_timeout.md', 'timeout_issue.md'], similar_types=['timeout_issue']
- actual: issue_type=timeout_issue, severity=medium, runbooks=['payment_provider_timeout.md', 'payment_provider_timeout.md', 'payment_provider_timeout.md'], similar_types=['timeout_issue', 'timeout_issue', 'timeout_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-config-secret-database

- failure_category: runbook_retrieval
- expected: issue_type=database_issue, severity=high, runbooks=['config_secret_mismatch.md', 'postgres_primary_unavailable.md', 'database_issue.md'], similar_types=['database_issue']
- actual: issue_type=database_issue, severity=high, runbooks=['postgres_primary_unavailable.md', 'auth_issue.md', 'postgres_primary_unavailable.md'], similar_types=['database_issue', 'database_issue', 'database_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-network-policy-postgres

- failure_category: runbook_retrieval
- expected: issue_type=database_issue, severity=high, runbooks=['firewall_policy_block.md', 'postgres_primary_unavailable.md', 'database_issue.md'], similar_types=['database_issue']
- actual: issue_type=database_issue, severity=high, runbooks=['postgres_primary_unavailable.md', 'postgres_primary_unavailable.md', 'postgres_primary_unavailable.md'], similar_types=['database_issue', 'timeout_issue', 'database_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-oauth-callback-login

- failure_category: runbook_retrieval
- expected: issue_type=auth_issue, severity=medium, runbooks=['oauth_callback_failure.md', 'auth_issue.md'], similar_types=['auth_issue']
- actual: issue_type=auth_issue, severity=medium, runbooks=['oauth_callback_failure.md', 'oauth_callback_failure.md', 'oauth_callback_failure.md'], similar_types=['auth_issue', 'auth_issue', 'auth_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-redis-secret-cache

- failure_category: runbook_retrieval
- expected: issue_type=cache_issue, severity=medium, runbooks=['config_secret_mismatch.md', 'redis_primary_failover.md', 'cache_issue.md'], similar_types=['cache_issue']
- actual: issue_type=cache_issue, severity=medium, runbooks=['cache_issue.md', 'cache_issue.md', 'cache_issue.md'], similar_types=['cache_issue', 'cache_issue', 'cache_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-cache-stampede-database-noise

- failure_category: runbook_retrieval
- expected: issue_type=cache_issue, severity=medium, runbooks=['cache_stampede.md', 'cache_issue.md'], similar_types=['cache_issue']
- actual: issue_type=cache_issue, severity=medium, runbooks=['cache_stampede.md', 'cache_stampede.md', 'cache_stampede.md'], similar_types=['cache_issue', 'server_error', 'cache_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-bad-release-serialization

- failure_category: evidence_selection, runbook_retrieval
- expected: issue_type=server_error, severity=high, runbooks=['bad_release_rollback.md', 'server_error.md'], similar_types=['server_error']
- actual: issue_type=server_error, severity=high, runbooks=['server_error.md', 'server_error.md', 'server_error.md'], similar_types=['server_error', 'server_error', 'server_error']
- possible_failure_reason: Expected evidence keywords were not present in the selected evidence logs. The expected runbook source was missing from the retrieved top results.

### rag-queue-lag-not-db

- failure_category: evidence_selection
- expected: issue_type=timeout_issue, severity=medium, runbooks=['message_queue_lag.md', 'timeout_issue.md'], similar_types=['timeout_issue']
- actual: issue_type=timeout_issue, severity=medium, runbooks=['message_queue_lag.md', 'timeout_issue.md', 'message_queue_lag.md'], similar_types=['timeout_issue', 'timeout_issue', 'timeout_issue']
- possible_failure_reason: Expected evidence keywords were not present in the selected evidence logs.

### rag-dns-provider-timeout

- failure_category: evidence_selection, runbook_retrieval
- expected: issue_type=timeout_issue, severity=medium, runbooks=['dns_resolution_failure.md', 'third_party_api_degradation.md', 'payment_provider_timeout.md'], similar_types=['timeout_issue']
- actual: issue_type=timeout_issue, severity=medium, runbooks=['payment_provider_timeout.md', 'payment_provider_timeout.md', 'dns_resolution_failure.md'], similar_types=['timeout_issue', 'timeout_issue', 'timeout_issue']
- possible_failure_reason: Expected evidence keywords were not present in the selected evidence logs. The expected runbook source was missing from the retrieved top results.

