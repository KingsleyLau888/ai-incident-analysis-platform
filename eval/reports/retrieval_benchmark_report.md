# Retrieval Benchmark Report

This report compares retrieval strategies on the same incident eval cases.
It is intended to show quality/latency tradeoffs rather than claim production-grade benchmark coverage.

## Compared Modes

- tfidf
- sentence-transformers
- hybrid
- chromadb

## Metrics Table

| mode | effective_retrieval_modes | issue_type_accuracy | runbook_top1_accuracy | runbook_precision_at_3 | similar_incident_top1_accuracy | similar_incident_precision_at_3 | average_latency_ms | failed_case_count |
|---|---|---|---|---|---|---|---|---|
| tfidf | tfidf | 70.37% | 59.26% | 48.15% | 77.78% | 65.43% | 52.64 | 13 |
| sentence-transformers | sentence-transformers | 70.37% | 77.78% | 71.60% | 81.48% | 70.37% | 2151.32 | 15 |
| hybrid | hybrid | 70.37% | 66.67% | 65.43% | 77.78% | 70.37% | 1803.04 | 13 |
| chromadb | chromadb | 70.37% | 77.78% | 71.60% | 81.48% | 70.37% | 158.73 | 15 |

## Interpretation

- Best runbook top-1 accuracy: sentence-transformers (77.78%)
- Best similar incident top-1 accuracy: sentence-transformers (81.48%)
- Lowest average latency: tfidf (52.64 ms)

TF-IDF tends to be fast and strong on exact error names.
Dense retrieval can help when the incident title is natural language or does not share exact keywords with the runbook.
Hybrid retrieval combines sparse and dense ranking with RRF, which is often the most robust option when both exact error terms and semantic hints matter.

## Failed Case Overlap

- tfidf: hard-mixed-database-timeout-primary-timeout, hard-auth-with-timeout-interference, hard-cache-warning-not-incident, hard-memory-warning-without-oom, adversarial-contradictory-signals, rag-config-secret-database, rag-network-policy-postgres, rag-oauth-callback-login, rag-redis-secret-cache, rag-cache-stampede-database-noise, rag-bad-release-serialization, rag-queue-lag-not-db, rag-dns-provider-timeout
- sentence-transformers: hard-mixed-database-timeout-primary-timeout, hard-auth-with-timeout-interference, hard-cache-warning-not-incident, hard-memory-warning-without-oom, adversarial-contradictory-signals, adversarial-misleading-first-signal, rag-natural-language-payment-provider, rag-config-secret-database, rag-network-policy-postgres, rag-oauth-callback-login, rag-redis-secret-cache, rag-cache-stampede-database-noise, rag-bad-release-serialization, rag-queue-lag-not-db, rag-dns-provider-timeout
- hybrid: hard-mixed-database-timeout-primary-timeout, hard-auth-with-timeout-interference, hard-cache-warning-not-incident, hard-memory-warning-without-oom, adversarial-contradictory-signals, rag-natural-language-payment-provider, rag-config-secret-database, rag-oauth-callback-login, rag-redis-secret-cache, rag-cache-stampede-database-noise, rag-bad-release-serialization, rag-queue-lag-not-db, rag-dns-provider-timeout
- chromadb: hard-mixed-database-timeout-primary-timeout, hard-auth-with-timeout-interference, hard-cache-warning-not-incident, hard-memory-warning-without-oom, adversarial-contradictory-signals, adversarial-misleading-first-signal, rag-natural-language-payment-provider, rag-config-secret-database, rag-network-policy-postgres, rag-oauth-callback-login, rag-redis-secret-cache, rag-cache-stampede-database-noise, rag-bad-release-serialization, rag-queue-lag-not-db, rag-dns-provider-timeout
