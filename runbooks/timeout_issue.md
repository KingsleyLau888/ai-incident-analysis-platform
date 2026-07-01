---
source_type: official_docs_summary
source_url:
  - https://nginx.org/en/docs/http/ngx_http_proxy_module.html
  - https://redis.io/docs/latest/develop/reference/clients/
  - https://docs.sqlalchemy.org/en/21/errors.html
issue_type: timeout_issue
products: [NGINX, Redis, SQLAlchemy, HTTP Clients]
---

# Timeout and Upstream Latency Runbook

## When to Use

Use this runbook when requests exceed deadlines, upstream calls time out, retries are exhausted, or users see HTTP 504 / gateway timeout behavior. Typical logs include `timed out`, `deadline exceeded`, `upstream timeout`, `retry exhausted`, `504`, `gateway timeout`, or high p95/p99 latency.

## Official Context

NGINX proxy timeout settings control how long the proxy waits for upstream connection, response headers, and response body activity. A 504 often means the proxy waited too long for the upstream.

Redis client guidance treats timeout configuration and reconnect behavior as part of client reliability. Timeouts can indicate server pressure, network instability, or client-side pool saturation.

SQLAlchemy timeout errors may be pool checkout timeouts rather than database query timeouts. That distinction matters because the fix could be connection management rather than longer SQL timeouts.

## Common Signals

- `upstream request timed out after 30s`
- `Payment provider timeout retry exhausted`
- `deadline exceeded`, `gateway timeout`, `504`
- Latency warning before hard failures
- Retry count increases together with error rate
- A single downstream dependency appears repeatedly in failed requests

## Likely Causes

- Downstream service, database, cache, or third-party API is slow or unreachable.
- Proxy/client timeout is shorter than the dependency's actual response time.
- Retry storm amplifies load and makes the dependency slower.
- Connection pool exhaustion causes calls to wait before the network request starts.
- DNS or network instability delays connection setup.

## Diagnostic Commands

```text
curl -v --max-time 5 <upstream-url>
kubectl logs <pod> --since=15m
kubectl describe service <service>
```

Check client timeout, proxy timeout, retry policy, upstream latency, and whether failures happen before or after connection establishment.

## Metrics to Check

- p50/p95/p99 latency by route and upstream dependency
- Timeout rate and retry rate
- Upstream saturation: CPU, queue depth, thread pool, connection pool
- Proxy 502/504 counts
- DNS lookup latency and network error rate

## Suggested Actions

- Confirm upstream health before increasing timeout values.
- Reduce retry amplification with bounded retries, backoff, jitter, and circuit breaking.
- Separate timeout budgets for connection, read, and total request duration.
- Degrade non-critical features if the upstream is unstable.
- Alert on timeout rate, retry rate, and tail latency together.

## Anti-patterns

- Do not only increase timeout values; that can hide failures and increase resource usage.
- Do not retry non-idempotent operations without idempotency keys.
- Do not treat all timeouts as network problems; pool exhaustion and slow dependencies can look identical in logs.
