---
source_type: official_docs_summary
source_url:
  - https://dev.mysql.com/doc/en/too-many-connections.html
  - https://docs.sqlalchemy.org/en/21/core/pooling.html
  - https://docs.sqlalchemy.org/en/21/errors.html
issue_type: database_issue
products: [MySQL, SQLAlchemy]
---

# MySQL and SQLAlchemy Connection Pool Saturation

## When to Use

Use this runbook when an application reports `Too many connections`, `QueuePool limit reached`, `pool exhausted`, `connection checkout timeout`, or repeated `DBConnectionTimeout` during traffic spikes.

## Official Context

MySQL limits concurrent connections through server configuration. SQLAlchemy QueuePool also limits application-side checked-out connections. Either side can become the bottleneck. A database can be healthy while the app pool is exhausted, or the app pool can appear exhausted because database queries are slow and connections are held longer.

## Common Signals

- `QueuePool limit of size <n> overflow <m> reached`
- `Too many connections`
- Pool active count equals configured capacity
- Request latency rises before database errors
- Errors increase after concurrency, worker count, or deployment changes

## Likely Causes

- Application concurrency exceeds pool and database capacity.
- Sessions are leaked or not closed after request handling.
- Long transactions or slow queries hold connections.
- Retry storm multiplies connection attempts.
- Pool settings are copied from development and too small for production traffic.

## Diagnostic Commands

```text
SHOW STATUS LIKE 'Threads_connected';
SHOW VARIABLES LIKE 'max_connections';
```

For SQLAlchemy apps, inspect pool metrics or logs around checked-out, overflow, and checkout wait time.

## Metrics to Check

- MySQL active connections and max connections
- SQLAlchemy checked-out connections
- Pool overflow count and checkout timeout count
- Long-running transaction count
- Request concurrency and retry rate

## Suggested Actions

- Fix leaked sessions and long transactions first.
- Tune `pool_size`, `max_overflow`, and `pool_timeout` based on real concurrency.
- Reduce worker concurrency if database capacity is the limiting factor.
- Add dashboards for pool checkout wait and database connection saturation.

## Anti-patterns

- Do not set an extremely large pool; it can overload the database.
- Do not increase MySQL `max_connections` without memory and workload analysis.
- Do not ignore retry storms; retries can exhaust pools faster than normal traffic.
