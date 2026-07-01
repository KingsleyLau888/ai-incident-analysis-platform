---
source_type: official_docs_summary
source_url:
  - https://redis.io/docs/latest/develop/reference/eviction/
issue_type: cache_issue
products: [Redis, Application Cache]
---

# Cache Stampede

## When to Use

Use this runbook when many requests rebuild the same missing or expired cache key, causing latency spikes, database pressure, and cascading failures.

## Official Context

Redis eviction and expiration behavior can remove keys under memory pressure or TTL expiry. Applications must protect hot-key rebuild paths because cache miss bursts can move load from Redis to the primary database.

## Common Signals

- Cache miss rate spikes for hot keys.
- Database query volume rises immediately after cache expiry.
- Logs mention cache rebuild, fallback latency, or repeated recomputation.
- User-facing latency increases without a database deployment.

## Likely Causes

- Hot key expired for all clients at the same time.
- Redis eviction removed frequently used keys.
- No request coalescing for expensive rebuild.
- Cache fallback path is slower than expected.

## Diagnostic Commands

```text
redis-cli INFO stats
redis-cli INFO memory
```

Look for hit-rate drop, evictions, and simultaneous database query spike.

## Metrics to Check

- Cache hit/miss rate by key prefix
- Evicted keys and memory usage
- Database QPS after cache miss
- Rebuild duration and concurrency

## Suggested Actions

- Add TTL jitter to avoid synchronized expiration.
- Use single-flight/request coalescing for hot-key rebuild.
- Serve stale data briefly while refreshing in background.
- Add alerts for hit-rate drop and hot-key rebuild concurrency.

## Anti-patterns

- Do not let every request rebuild the same cache key.
- Do not set identical TTLs for all hot keys.
- Do not push cache miss bursts directly to the primary database.
