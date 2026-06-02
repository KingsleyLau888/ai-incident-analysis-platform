# Cache Issue Runbook

## Symptoms

Cache incidents often show Redis connection errors, cache misses, stale values, or high latency when reading from a cache dependency.

Common log signals include `RedisConnection`, `redis`, and `cache`.

## Initial Checks

Check Redis health, connection count, memory usage, eviction rate, and whether the affected service can reach the cache.

## Suggested Actions

Inspect Redis availability, cache cluster status, client connection pool, and recent cache configuration changes.
