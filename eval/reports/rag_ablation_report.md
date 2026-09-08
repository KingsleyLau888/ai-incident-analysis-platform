# RAG Ablation Report

This report isolates runbook retrieval quality and latency.
It is meant to show which RAG techniques actually improve the system.

| config | effective_mode | multi_query | metadata_filter | top1 | precision@3 | avg_latency_ms |
|---|---|---|---|---|---|---|
| tfidf_single_query | tfidf | False | False | 100.00% | 66.67% | 101.99 |
| dense_single_query | sentence-transformers | False | False | 81.82% | 68.18% | 2413.16 |
| chromadb_single_query | chromadb | False | False | 81.82% | 68.18% | 14.77 |
| chromadb_multi_query | chromadb | True | False | 68.18% | 71.21% | 42.38 |
| chromadb_multi_query_metadata | chromadb | True | True | 81.82% | 78.79% | 45.25 |

## Takeaways

- dense_single_query: top1 delta -18.18%, latency delta +2311.18 ms vs TF-IDF baseline.
- chromadb_single_query: top1 delta -18.18%, latency delta -87.22 ms vs TF-IDF baseline.
- chromadb_multi_query: top1 delta -31.82%, latency delta -59.61 ms vs TF-IDF baseline.
- chromadb_multi_query_metadata: top1 delta -18.18%, latency delta -56.74 ms vs TF-IDF baseline.
