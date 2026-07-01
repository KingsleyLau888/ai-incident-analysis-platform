---
source_type: official_docs_summary
source_url:
  - https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-indices-refresh
issue_type: server_error
products: [Elasticsearch]
---

# Search Index Stale

## When to Use

Use this runbook when writes succeed but search results are stale, missing, or delayed.

## Official Context

Search systems often make data visible after refresh or indexing pipeline completion. Forcing refresh can make documents visible sooner, but frequent refreshes can be expensive. The safer path is to understand indexing lag and failed ingestion.

## Common Signals

- Newly written records do not appear in search.
- Logs mention indexing lag, failed bulk request, refresh delay, or stale index.
- Source database contains data that index does not.
- Search freshness degrades after ingestion pipeline change.

## Likely Causes

- Indexing worker lag or failure.
- Bulk indexing errors ignored or retried incorrectly.
- Refresh interval or index lifecycle settings changed.
- Mapping error rejects documents.

## Diagnostic Commands

```text
curl -X GET <elasticsearch>/_cluster/health
curl -X GET <index>/_refresh
```

Compare source record count with indexed document count for affected entities.

## Metrics to Check

- Indexing lag age
- Failed bulk requests
- Refresh latency
- Rejected documents by mapping error
- Search result freshness

## Suggested Actions

- Restore indexing pipeline before forcing repeated refresh.
- Replay failed indexing events.
- Fix mapping/config errors and reindex affected documents.
- Alert on indexing lag and failed bulk batches.

## Anti-patterns

- Do not force refresh continuously as a permanent fix.
- Do not assume database write success means search visibility.
- Do not hide indexing failures behind empty search results.
