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
| tfidf | tfidf | 92.59% | 88.89% | 74.07% | 100.00% | 93.83% | 52.41 | 9 |
| sentence-transformers | sentence-transformers | 92.59% | 81.48% | 72.84% | 96.30% | 91.36% | 2570.23 | 14 |
| hybrid | hybrid | 92.59% | 92.59% | 77.78% | 100.00% | 97.53% | 2217.56 | 10 |
| chromadb | chromadb | 92.59% | 81.48% | 72.84% | 96.30% | 91.36% | 169.33 | 14 |

## Interpretation

- Best runbook top-1 accuracy: hybrid (92.59%)
- Best similar incident top-1 accuracy: tfidf (100.00%)
- Lowest average latency: tfidf (52.41 ms)

TF-IDF tends to be fast and strong on exact error names.
Dense retrieval can help when the incident title is natural language or does not share exact keywords with the runbook.
Hybrid retrieval combines sparse and dense ranking with RRF, which is often the most robust option when both exact error terms and semantic hints matter.

## Failed Case Overlap

- tfidf: hard-cache-warning-not-incident, hard-memory-warning-without-oom, adversarial-contradictory-signals, rag-config-secret-database, rag-network-policy-postgres, rag-redis-secret-cache, rag-bad-release-serialization, rag-queue-lag-not-db, rag-dns-provider-timeout
- sentence-transformers: hard-server-error-symptom-database-root-cause, hard-cache-warning-not-incident, hard-memory-warning-without-oom, adversarial-contradictory-signals, adversarial-misleading-first-signal, rag-natural-language-payment-provider, rag-config-secret-database, rag-network-policy-postgres, rag-oauth-callback-login, rag-redis-secret-cache, rag-cache-stampede-database-noise, rag-bad-release-serialization, rag-queue-lag-not-db, rag-dns-provider-timeout
- hybrid: hard-cache-warning-not-incident, hard-memory-warning-without-oom, adversarial-contradictory-signals, rag-config-secret-database, rag-network-policy-postgres, rag-redis-secret-cache, rag-cache-stampede-database-noise, rag-bad-release-serialization, rag-queue-lag-not-db, rag-dns-provider-timeout
- chromadb: hard-server-error-symptom-database-root-cause, hard-cache-warning-not-incident, hard-memory-warning-without-oom, adversarial-contradictory-signals, adversarial-misleading-first-signal, rag-natural-language-payment-provider, rag-config-secret-database, rag-network-policy-postgres, rag-oauth-callback-login, rag-redis-secret-cache, rag-cache-stampede-database-noise, rag-bad-release-serialization, rag-queue-lag-not-db, rag-dns-provider-timeout
