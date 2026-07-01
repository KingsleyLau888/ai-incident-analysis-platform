# Eval Report

Retrieval mode: tfidf
Effective retrieval modes: tfidf
LLM Judge: disabled

Total cases: 27

## Metrics

- issue_type_accuracy: 92.59%
- severity_accuracy: 92.59%
- evidence_recall: 92.59%
- runbook_retrieval_recall: 77.16%
- runbook_top1_accuracy: 55.56%
- runbook_precision_at_3: 60.49%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_accuracy: 100.00%
- similar_incident_precision_at_3: 92.59%
- failed_case_count: 11
- average_latency_ms: 54.48

## Cases

### database-payment-mysql-timeout

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, firewall_policy_block.md, database_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, cache_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 147.32
- passed: True
- failure_categories: none

### timeout-checkout-upstream

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: timeout_issue.md, token_signing_key_rotation.md, timeout_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 79.46
- passed: True
- failure_categories: none

### auth-token-rejected

- expected_issue_type: auth_issue
- actual_issue_type: auth_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: auth_issue.md
- actual_runbook_sources: config_secret_mismatch.md, auth_issue.md, config_secret_mismatch.md
- expected_similar_issue_types: auth_issue
- actual_similar_issue_types: auth_issue, auth_issue, cache_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 33.33%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 40.82
- passed: True
- failure_categories: none

### cache-redis-connection

- expected_issue_type: cache_issue
- actual_issue_type: cache_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: cache_issue.md
- actual_runbook_sources: redis_primary_failover.md, cache_issue.md, cache_stampede.md
- expected_similar_issue_types: cache_issue
- actual_similar_issue_types: cache_issue, cache_issue, cache_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 33.33%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 34.10
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
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 33.52
- passed: True
- failure_categories: none

### server-error-api-500

- expected_issue_type: server_error
- actual_issue_type: server_error
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: server_error.md
- actual_runbook_sources: bad_release_rollback.md, server_error.md, bad_release_rollback.md
- expected_similar_issue_types: server_error
- actual_similar_issue_types: server_error, server_error, database_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 33.33%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 34.19
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
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 14.85
- passed: True
- failure_categories: none

### hard-mixed-database-timeout-primary-timeout

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: timeout_issue.md, token_signing_key_rotation.md, timeout_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 73.26
- passed: True
- failure_categories: none

### hard-server-error-symptom-database-root-cause

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, firewall_policy_block.md, database_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 76.47
- passed: True
- failure_categories: none

### hard-auth-with-timeout-interference

- expected_issue_type: auth_issue
- actual_issue_type: auth_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: auth_issue.md
- actual_runbook_sources: config_secret_mismatch.md, config_secret_mismatch.md, auth_issue.md
- expected_similar_issue_types: auth_issue
- actual_similar_issue_types: auth_issue, auth_issue, auth_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 33.33%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 39.56
- passed: True
- failure_categories: none

### hard-cache-warning-not-incident

- expected_issue_type: unknown
- actual_issue_type: cache_issue
- expected_severity: low
- actual_severity: medium
- expected_runbook_sources: (none)
- actual_runbook_sources: cache_issue.md, redis_primary_failover.md, cache_stampede.md
- expected_similar_issue_types: (none)
- actual_similar_issue_types: (none)
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 16.95
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
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 16.06
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
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 14.64
- passed: True
- failure_categories: none

### hard-similar-incident-top3-challenge

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: timeout_issue.md, token_signing_key_rotation.md, timeout_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 72.88
- passed: True
- failure_categories: none

### adversarial-contradictory-signals

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: timeout_issue.md
- actual_runbook_sources: token_signing_key_rotation.md, timeout_issue.md, timeout_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 50.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 73.72
- passed: False
- failure_categories: evidence_selection

### adversarial-noise-injection

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, firewall_policy_block.md, database_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 88.95
- passed: True
- failure_categories: none

### adversarial-misleading-first-signal

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: database_issue.md
- actual_runbook_sources: database_issue.md, firewall_policy_block.md, database_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, database_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 76.57
- passed: True
- failure_categories: none

### rag-natural-language-payment-provider

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: payment_provider_timeout.md, timeout_issue.md
- actual_runbook_sources: token_signing_key_rotation.md, timeout_issue.md, timeout_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 50.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 73.82
- passed: False
- failure_categories: runbook_retrieval

### rag-config-secret-database

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: config_secret_mismatch.md, postgres_primary_unavailable.md, database_issue.md
- actual_runbook_sources: firewall_policy_block.md, database_issue.md, database_issue.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, cache_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 33.33%
- runbook_top1_correct: False
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 78.79
- passed: False
- failure_categories: runbook_retrieval

### rag-network-policy-postgres

- expected_issue_type: database_issue
- actual_issue_type: database_issue
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: firewall_policy_block.md, postgres_primary_unavailable.md, database_issue.md
- actual_runbook_sources: database_issue.md, database_issue.md, firewall_policy_block.md
- expected_similar_issue_types: database_issue
- actual_similar_issue_types: database_issue, database_issue, cache_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 66.67%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 78.06
- passed: False
- failure_categories: runbook_retrieval

### rag-oauth-callback-login

- expected_issue_type: auth_issue
- actual_issue_type: auth_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: oauth_callback_failure.md, auth_issue.md
- actual_runbook_sources: config_secret_mismatch.md, config_secret_mismatch.md, auth_issue.md
- expected_similar_issue_types: auth_issue
- actual_similar_issue_types: auth_issue, auth_issue, auth_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 50.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 33.33%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 41.09
- passed: False
- failure_categories: runbook_retrieval

### rag-redis-secret-cache

- expected_issue_type: cache_issue
- actual_issue_type: cache_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: config_secret_mismatch.md, redis_primary_failover.md, cache_issue.md
- actual_runbook_sources: redis_primary_failover.md, cache_stampede.md, redis_primary_failover.md
- expected_similar_issue_types: cache_issue
- actual_similar_issue_types: cache_issue, cache_issue, cache_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 33.33%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 34.19
- passed: False
- failure_categories: runbook_retrieval

### rag-cache-stampede-database-noise

- expected_issue_type: cache_issue
- actual_issue_type: cache_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: cache_stampede.md, cache_issue.md
- actual_runbook_sources: cache_stampede.md, redis_primary_failover.md, cache_issue.md
- expected_similar_issue_types: cache_issue
- actual_similar_issue_types: cache_issue, cache_issue, cache_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 34.23
- passed: True
- failure_categories: none

### rag-bad-release-serialization

- expected_issue_type: server_error
- actual_issue_type: server_error
- expected_severity: high
- actual_severity: high
- expected_runbook_sources: bad_release_rollback.md, server_error.md
- actual_runbook_sources: bad_release_rollback.md, server_error.md, bad_release_rollback.md
- expected_similar_issue_types: server_error
- actual_similar_issue_types: server_error, server_error, database_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 50.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 66.67%
- latency_ms: 34.72
- passed: False
- failure_categories: evidence_selection

### rag-queue-lag-not-db

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: message_queue_lag.md, timeout_issue.md
- actual_runbook_sources: token_signing_key_rotation.md, timeout_issue.md, timeout_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 50.00%
- runbook_retrieval_recall: 50.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 66.67%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 74.05
- passed: False
- failure_categories: evidence_selection, runbook_retrieval

### rag-dns-provider-timeout

- expected_issue_type: timeout_issue
- actual_issue_type: timeout_issue
- expected_severity: medium
- actual_severity: medium
- expected_runbook_sources: dns_resolution_failure.md, third_party_api_degradation.md, payment_provider_timeout.md
- actual_runbook_sources: token_signing_key_rotation.md, timeout_issue.md, timeout_issue.md
- expected_similar_issue_types: timeout_issue
- actual_similar_issue_types: timeout_issue, timeout_issue, timeout_issue
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 50.00%
- runbook_retrieval_recall: 0.00%
- runbook_top1_correct: False
- runbook_precision_at_3: 0.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 73.08
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
- runbook_effective_retrieval_mode: tfidf
- similar_effective_retrieval_mode: tfidf
- evidence_recall: 100.00%
- runbook_retrieval_recall: 100.00%
- runbook_top1_correct: True
- runbook_precision_at_3: 100.00%
- similar_incident_retrieval_recall: 100.00%
- similar_incident_top1_correct: True
- similar_incident_precision_at_3: 100.00%
- latency_ms: 15.58
- passed: True
- failure_categories: none

## Failed Cases

- hard-cache-warning-not-incident
- hard-memory-warning-without-oom
- adversarial-contradictory-signals
- rag-natural-language-payment-provider
- rag-config-secret-database
- rag-network-policy-postgres
- rag-oauth-callback-login
- rag-redis-secret-cache
- rag-bad-release-serialization
- rag-queue-lag-not-db
- rag-dns-provider-timeout

## Error Analysis

### hard-cache-warning-not-incident

- failure_category: rule_detection, runbook_retrieval
- expected: issue_type=unknown, severity=low, runbooks=[], similar_types=[]
- actual: issue_type=cache_issue, severity=medium, runbooks=['cache_issue.md', 'redis_primary_failover.md', 'cache_stampede.md'], similar_types=[]
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification. The expected runbook source was missing from the retrieved top results.

### hard-memory-warning-without-oom

- failure_category: rule_detection, runbook_retrieval
- expected: issue_type=unknown, severity=low, runbooks=[], similar_types=[]
- actual: issue_type=memory_issue, severity=high, runbooks=['memory_issue.md', 'memory_issue.md', 'memory_issue.md'], similar_types=[]
- possible_failure_reason: Keyword priority or ambiguous mixed signals produced a different classification. The expected runbook source was missing from the retrieved top results.

### adversarial-contradictory-signals

- failure_category: evidence_selection
- expected: issue_type=timeout_issue, severity=medium, runbooks=['timeout_issue.md'], similar_types=['timeout_issue']
- actual: issue_type=timeout_issue, severity=medium, runbooks=['token_signing_key_rotation.md', 'timeout_issue.md', 'timeout_issue.md'], similar_types=['timeout_issue', 'timeout_issue', 'timeout_issue']
- possible_failure_reason: Expected evidence keywords were not present in the selected evidence logs.

### rag-natural-language-payment-provider

- failure_category: runbook_retrieval
- expected: issue_type=timeout_issue, severity=medium, runbooks=['payment_provider_timeout.md', 'timeout_issue.md'], similar_types=['timeout_issue']
- actual: issue_type=timeout_issue, severity=medium, runbooks=['token_signing_key_rotation.md', 'timeout_issue.md', 'timeout_issue.md'], similar_types=['timeout_issue', 'timeout_issue', 'timeout_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-config-secret-database

- failure_category: runbook_retrieval
- expected: issue_type=database_issue, severity=high, runbooks=['config_secret_mismatch.md', 'postgres_primary_unavailable.md', 'database_issue.md'], similar_types=['database_issue']
- actual: issue_type=database_issue, severity=high, runbooks=['firewall_policy_block.md', 'database_issue.md', 'database_issue.md'], similar_types=['database_issue', 'database_issue', 'cache_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-network-policy-postgres

- failure_category: runbook_retrieval
- expected: issue_type=database_issue, severity=high, runbooks=['firewall_policy_block.md', 'postgres_primary_unavailable.md', 'database_issue.md'], similar_types=['database_issue']
- actual: issue_type=database_issue, severity=high, runbooks=['database_issue.md', 'database_issue.md', 'firewall_policy_block.md'], similar_types=['database_issue', 'database_issue', 'cache_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-oauth-callback-login

- failure_category: runbook_retrieval
- expected: issue_type=auth_issue, severity=medium, runbooks=['oauth_callback_failure.md', 'auth_issue.md'], similar_types=['auth_issue']
- actual: issue_type=auth_issue, severity=medium, runbooks=['config_secret_mismatch.md', 'config_secret_mismatch.md', 'auth_issue.md'], similar_types=['auth_issue', 'auth_issue', 'auth_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-redis-secret-cache

- failure_category: runbook_retrieval
- expected: issue_type=cache_issue, severity=medium, runbooks=['config_secret_mismatch.md', 'redis_primary_failover.md', 'cache_issue.md'], similar_types=['cache_issue']
- actual: issue_type=cache_issue, severity=medium, runbooks=['redis_primary_failover.md', 'cache_stampede.md', 'redis_primary_failover.md'], similar_types=['cache_issue', 'cache_issue', 'cache_issue']
- possible_failure_reason: The expected runbook source was missing from the retrieved top results.

### rag-bad-release-serialization

- failure_category: evidence_selection
- expected: issue_type=server_error, severity=high, runbooks=['bad_release_rollback.md', 'server_error.md'], similar_types=['server_error']
- actual: issue_type=server_error, severity=high, runbooks=['bad_release_rollback.md', 'server_error.md', 'bad_release_rollback.md'], similar_types=['server_error', 'server_error', 'database_issue']
- possible_failure_reason: Expected evidence keywords were not present in the selected evidence logs.

### rag-queue-lag-not-db

- failure_category: evidence_selection, runbook_retrieval
- expected: issue_type=timeout_issue, severity=medium, runbooks=['message_queue_lag.md', 'timeout_issue.md'], similar_types=['timeout_issue']
- actual: issue_type=timeout_issue, severity=medium, runbooks=['token_signing_key_rotation.md', 'timeout_issue.md', 'timeout_issue.md'], similar_types=['timeout_issue', 'timeout_issue', 'timeout_issue']
- possible_failure_reason: Expected evidence keywords were not present in the selected evidence logs. The expected runbook source was missing from the retrieved top results.

### rag-dns-provider-timeout

- failure_category: evidence_selection, runbook_retrieval
- expected: issue_type=timeout_issue, severity=medium, runbooks=['dns_resolution_failure.md', 'third_party_api_degradation.md', 'payment_provider_timeout.md'], similar_types=['timeout_issue']
- actual: issue_type=timeout_issue, severity=medium, runbooks=['token_signing_key_rotation.md', 'timeout_issue.md', 'timeout_issue.md'], similar_types=['timeout_issue', 'timeout_issue', 'timeout_issue']
- possible_failure_reason: Expected evidence keywords were not present in the selected evidence logs. The expected runbook source was missing from the retrieved top results.

