---
source_type: official_docs_summary
source_url:
  - https://nginx.org/en/docs/http/ngx_http_proxy_module.html
issue_type: timeout_issue
products: [HTTP Clients, Upstream Payment APIs]
---

# Payment Provider Timeout

## When to Use

Use this runbook when checkout or payment authorization fails because an upstream payment provider exceeds timeout budgets.

## Official Context

HTTP proxies and clients distinguish connection timeout, read timeout, and upstream response timeout. Payment calls also require idempotency because retries can create duplicate side effects if not designed carefully.

## Common Signals

- `payment provider timeout`
- `upstream timed out`
- `Payment API returned 504`
- `retry exhausted`
- Order or inventory step succeeds but payment authorization fails

## Likely Causes

- Payment provider is slow, degraded, or regionally unavailable.
- Client/proxy timeout is too aggressive for provider latency.
- Retry storm increases provider load.
- Network path to provider is unstable.

## Diagnostic Commands

```text
curl -v --max-time 5 <provider-health-or-tokenized-test-endpoint>
kubectl logs <checkout-service> --since=15m
```

Correlate failed payment attempts by request id and idempotency key.

## Metrics to Check

- Payment provider latency and timeout rate
- Retry count per checkout request
- Authorization success rate by provider/method/region
- Checkout 5xx/504 rate

## Suggested Actions

- Cap retries and use exponential backoff with jitter.
- Ensure idempotency keys are used for payment operations.
- Degrade or disable affected payment route if provider is unstable.
- Add alerts on provider timeout and retry amplification.

## Anti-patterns

- Do not retry payment authorization indefinitely.
- Do not hide provider outage as generic checkout failure.
- Do not increase timeout without checking user experience and resource usage.
