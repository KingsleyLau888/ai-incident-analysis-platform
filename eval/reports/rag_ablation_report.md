# RAG Ablation Report

This report isolates runbook retrieval quality and latency.
It is meant to show which RAG techniques actually improve the system.

| config | effective_mode | multi_query | metadata_filter | top1 | precision@3 | avg_latency_ms |
|---|---|---|---|---|---|---|
| tfidf_single_query | tfidf | False | False | 59.09% | 60.61% | 8.09 |
| dense_single_query | sentence-transformers | False | False | 81.82% | 69.70% | 377.47 |
| chromadb_single_query | chromadb | False | False | 81.82% | 69.70% | 16.31 |
| chromadb_multi_query | chromadb | True | False | 86.36% | 81.82% | 41.73 |
| chromadb_multi_query_metadata | chromadb | True | True | 95.45% | 86.36% | 43.74 |

## Takeaways

- dense_single_query: top1 delta +22.73%, latency delta +369.38 ms vs TF-IDF baseline.
- chromadb_single_query: top1 delta +22.73%, latency delta +8.22 ms vs TF-IDF baseline.
- chromadb_multi_query: top1 delta +27.27%, latency delta +33.64 ms vs TF-IDF baseline.
- chromadb_multi_query_metadata: top1 delta +36.36%, latency delta +35.65 ms vs TF-IDF baseline.
