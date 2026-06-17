# Database Slow Query

## Symptoms

Requests become slow while database connections remain available. Logs mention `slow query`, `lock wait timeout`, or `query exceeded deadline`.

## Checks

Inspect slow query logs, lock waits, index usage, query plan changes, and recent migrations.

## Suggested Actions

Kill blocking transactions, add or restore indexes, roll back expensive query changes, and add query latency alerts.

