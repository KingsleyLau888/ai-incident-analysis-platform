# Redis Primary Failover

## Symptoms

Services log `RedisConnection refused`, `READONLY`, cache write failures, or cart/session reads failing during failover.

## Checks

Inspect Redis primary role, failover status, client endpoint, connection count, and cache fallback behavior.

## Suggested Actions

Complete failover, refresh client endpoints, clear bad connection pools, and verify cache fallback does not overload the database.

