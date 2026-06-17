# PostgreSQL Primary Unavailable

## Symptoms

Services log `postgres connection failed`, `primary unavailable`, `connection refused`, or failed writes to order and billing tables.

## Checks

Verify primary database health, failover status, DNS resolution, security group rules, and client connectivity from the affected service.

## Suggested Actions

Restore primary connectivity, roll back network policy changes, fail over if needed, and validate writes from the application service.

