---
source_type: official_docs_summary
source_url:
  - https://www.postgresql.org/docs/current/server-start.html
  - https://www.postgresql.org/docs/current/runtime-config-connection.html
  - https://www.postgresql.org/docs/current/auth-pg-hba-conf.html
issue_type: database_issue
products: [PostgreSQL]
---

# PostgreSQL Primary Unavailable

## When to Use

Use this runbook when writes fail because the PostgreSQL primary is unavailable, unreachable, not accepting connections, or clients still target an old primary after failover.

## Official Context

PostgreSQL must be running, listening on the expected address and port, and configured to accept the client. Even when the process is healthy, connection configuration, access rules, or failover routing can reject or blackhole application traffic.

## Common Signals

- `connection refused`, `could not connect to server`
- `postgres-primary unavailable`
- Writes fail but some reads still work
- Errors start after failover, DNS, NetworkPolicy, firewall, or maintenance
- Application logs reference stale primary host

## Likely Causes

- PostgreSQL primary is down, restarting, or overloaded.
- `listen_addresses` or port configuration does not match client target.
- Network path blocks client-to-primary traffic.
- Failover completed but service discovery or DNS did not update for clients.
- Authentication rules reject the application host or user.

## Diagnostic Commands

```text
pg_isready -h <host> -p <port>
psql -h <host> -p <port> -U <user> -d <db>
kubectl get endpoints <postgres-service>
```

Check PostgreSQL logs for startup, rejected connection, authentication, and failover messages.

## Metrics to Check

- Primary availability and replication/failover state
- Connection accepted/rejected counts
- DNS/service endpoint changes
- Write error rate
- Database CPU, IO, and lock pressure

## Suggested Actions

- Restore or promote a healthy primary.
- Update service discovery, DNS, or application connection string after failover.
- Roll back network/firewall changes that block the database.
- Add alerts for primary unavailability and stale endpoint usage.

## Anti-patterns

- Do not repeatedly restart application clients before verifying the database endpoint.
- Do not treat read availability as proof that the primary is writable.
- Do not ignore authentication errors; they can look like connectivity failures at the application layer.
