---
source_type: official_docs_summary
source_url:
  - https://redis.io/docs/latest/develop/reference/clients/
  - https://redis.io/docs/latest/develop/reference/eviction/
  - https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/
issue_type: cache_issue
products: [Redis]
---

# Redis and Cache Availability Runbook

## When to Use

Use this runbook when logs mention Redis connection failures, cache timeouts, cache fallback latency, eviction spikes, stale values, `maxmemory`, or cache stampede symptoms.

## Official Context

Redis clients must manage connections, timeouts, reconnects, and command behavior under network or server pressure. Redis eviction behavior depends on memory limits and eviction policy. Failover changes the primary role and clients must reconnect or refresh topology.

## Common Signals

- `RedisConnection refused while reading cache`
- `redis timeout`, `READONLY`, reconnect loop, or cache write failure
- `evicted keys`, `maxmemory`, `noeviction`
- Cache miss spike followed by database latency
- Application remains partially available but becomes slower due to fallback

## Likely Causes

- Redis primary unavailable, failing over, overloaded, or rejecting clients.
- Client connection pool is saturated or blocked clients accumulate.
- Memory limit and eviction policy remove hot keys or reject writes.
- Cache stampede rebuilds hot keys concurrently.
- Stale connection topology after failover.

## Diagnostic Commands

```text
redis-cli -h <host> -p <port> PING
redis-cli INFO clients
redis-cli INFO memory
redis-cli INFO stats
```

Check primary/replica role, connected clients, blocked clients, used memory, eviction counters, keyspace hits/misses, and application fallback latency.

## Metrics to Check

- Redis availability and role
- Connected clients and blocked clients
- Used memory, maxmemory, evicted keys
- Cache hit rate / miss rate
- Database load after cache miss spike
- Client timeout and reconnect errors

## Suggested Actions

- Restore Redis connectivity or fail over to a healthy primary.
- Tune client timeout and reconnect behavior after confirming Redis health.
- Review `maxmemory` and eviction policy for workload expectations.
- Add TTL jitter, request coalescing, or stale-while-revalidate for hot keys.
- Add alerts for hit rate drop, evictions, blocked clients, and reconnect storms.

## Anti-patterns

- Do not treat Redis as only a performance component if the application depends on it for correctness.
- Do not increase cache TTL globally without checking stale data impact.
- Do not let cache miss spikes fall through unbounded to the primary database.
