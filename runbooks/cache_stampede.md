# Cache Stampede

## Symptoms

A popular key expires and many requests rebuild the same cache entry. Logs mention cache misses, high database read rate, or synchronized refresh.

## Checks

Inspect miss rate, hot keys, TTL distribution, lock behavior, and downstream database load.

## Suggested Actions

Add request coalescing, jitter TTLs, prewarm hot keys, and rate limit expensive cache rebuilds.

