# Database Connectivity Runbook

## Symptoms

Database incidents often show connection failures, connection timeouts, pool exhaustion, or repeated errors when a service talks to MySQL, PostgreSQL, or another primary database.

For payment-service, a common signal is `DBConnectionTimeout when connecting to mysql-primary`.

## Initial Checks

Check whether the database host is healthy and reachable from the affected service. Confirm that mysql-primary is accepting connections and that there are no failover or network events.

Check the service connection pool. Compare active connections, idle connections, wait time, and maximum configured pool size.

## Suggested Actions

Inspect mysql-primary health, connection count, slow queries, and recent failover status.

Inspect payment-service database pool metrics and recent configuration changes.

If the database is healthy but the service pool is saturated, prioritize connection pool configuration, request concurrency, and recent deployments.
