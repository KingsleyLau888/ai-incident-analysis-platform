---
source_type: official_docs_summary
source_url:
  - https://dev.mysql.com/doc/refman/8.4/en/problems-connecting.html
  - https://dev.mysql.com/doc/en/too-many-connections.html
  - https://www.postgresql.org/docs/current/runtime-config-connection.html
  - https://docs.sqlalchemy.org/en/21/errors.html
issue_type: database_issue
products: [MySQL, PostgreSQL, SQLAlchemy]
---

# Database Connectivity Runbook

## When to Use

Use this runbook when an application cannot complete a request because it cannot connect to, write to, or obtain a connection for its primary database. Typical logs include `DBConnectionTimeout`, `database unavailable`, `connection refused`, `too many connections`, `QueuePool limit`, `OperationalError`, `mysql-primary`, `postgres-primary`, or `shop-primary`.

This runbook is especially relevant when HTTP 500 appears after a database write failure. In that case, treat the 500 as the user-visible symptom and the database signal as the stronger root-cause candidate.

## Official Context

MySQL troubleshooting guidance focuses first on whether the server is running, listening on the expected host and port, and accepting connections. MySQL also documents `Too many connections` as a saturation condition controlled by server connection limits.

PostgreSQL connection configuration depends on the server listening address, port, and connection-related settings. A reachable host can still reject connections if listening or access configuration is wrong.

SQLAlchemy connection pool errors usually mean the application could not check out a database connection before timeout. Common causes include exhausted pool capacity, leaked sessions, long transactions, or a slow database holding connections longer than expected.

## Common Signals

- `DBConnectionTimeout while connecting to mysql-primary`
- `connection refused`, `could not connect`, `database unavailable`
- `database write failure`, failed transaction, failed order creation
- `QueuePool limit reached`, `pool exhausted`, `connection checkout timeout`
- HTTP 500 follows database retry or write failure
- Database connection count near limit or rejected connection metrics increasing

## Likely Causes

- Database process is down, restarting, overloaded, or not listening on the expected address.
- DNS, firewall, security group, or Kubernetes NetworkPolicy blocks the application-to-database path.
- Database `max_connections` or application pool capacity is exhausted.
- Application sessions are leaked or long transactions hold connections.
- Failover changed the primary endpoint but clients still target the old host.
- A slow query or lock wait causes connection hold time to grow until the pool saturates.

## Diagnostic Commands

Use commands appropriate for the environment:

```text
nc -vz <db-host> <db-port>
psql -h <host> -p <port> -U <user> -d <db>
mysql -h <host> -P <port> -u <user> -p
kubectl get pods -n <namespace>
kubectl describe networkpolicy -n <namespace>
```

For database state, inspect active connections, rejected connections, slow queries, long transactions, and failover events.

## Metrics to Check

- Database active connections / max connections
- Application pool active, idle, overflow, and checkout wait time
- Database CPU, memory, disk IO, and lock waits
- Request concurrency and retry rate
- DNS and network connectivity error rate

## Suggested Actions

- Restore reachability first: host, port, DNS, firewall, security group, or network policy.
- If the database is saturated, reduce traffic pressure before increasing limits.
- Fix leaked sessions and long transactions before tuning pool size.
- Tune `pool_size`, `max_overflow`, and checkout timeout from measured concurrency.
- Add alerts for pool checkout timeout, database rejected connections, and primary unavailability.

## Anti-patterns

- Do not blindly increase database connection limits without checking leaks and long transactions.
- Do not classify the incident as generic `server_error` when database-specific logs are present.
- Do not rely only on HTTP 500 rate; correlate it with database connection and pool metrics.
