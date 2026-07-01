---
source_type: official_docs_summary
source_url:
  - https://dev.mysql.com/doc/refman/8.4/en/slow-query-log.html
  - https://www.postgresql.org/docs/current/runtime-config-logging.html
issue_type: database_issue
products: [MySQL, PostgreSQL]
---

# Database Slow Query

## When to Use

Use this runbook when slow queries, lock waits, long transactions, or missing indexes increase request latency and eventually cause timeouts or pool saturation.

## Official Context

MySQL and PostgreSQL both provide logging and configuration for slow statements. Slow queries can indirectly create application errors by holding connections longer, increasing pool wait time, and causing upstream timeouts.

## Common Signals

- `slow query`, `long transaction`, `lock wait`, `deadlock`
- Pool usage rises while request latency increases.
- A recent release changed query shape or added a migration.
- Database CPU or IO grows before app errors.

## Likely Causes

- Missing or inefficient index.
- Query scans too many rows.
- Long transaction holds locks.
- Migration or batch job competes with online traffic.
- N+1 query pattern introduced by release.

## Diagnostic Commands

```text
EXPLAIN <query>;
SHOW PROCESSLIST;
```

For PostgreSQL, inspect active sessions and long-running queries using system views.

## Metrics to Check

- Query latency percentile
- Lock wait time
- Rows scanned / rows returned
- Active connection duration
- Pool checkout wait time

## Suggested Actions

- Roll back query-regressing release if timing is clear.
- Add or fix indexes after verifying query plan.
- Terminate clearly stuck blockers if they block critical traffic.
- Move heavy batch work away from peak traffic.

## Anti-patterns

- Do not only increase application timeout; slow queries can exhaust pools.
- Do not add indexes blindly without checking write impact.
- Do not ignore slow warnings before timeout incidents.
