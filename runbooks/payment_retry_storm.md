---
source_type: official_docs_summary
source_url:
  - https://nginx.org/en/docs/http/ngx_http_proxy_module.html
issue_type: timeout_issue
products: [HTTP Clients, Payment APIs]
---

# Payment Retry Storm

## When to Use

Use this runbook when retries after payment failures increase load and make checkout or provider latency worse.

## Common Signals

- Same request id or user action causes many payment attempts.
- `retry exhausted`, `duplicate attempt`, or `upstream timeout` appears repeatedly.
- Request volume rises while user traffic is flat.
- Provider latency worsens after retries begin.

## Likely Causes

- Retry policy lacks cap, backoff, or jitter.
- Client and gateway both retry the same operation.
- Non-idempotent payment call is retried after uncertain outcome.
- Timeout is shorter than provider normal tail latency.

## Diagnostic Commands

```text
kubectl logs <checkout-service> --since=15m | findstr retry
```

Group attempts by request id and idempotency key.

## Metrics to Check

- Attempts per checkout request
- Retry rate and retry exhaustion count
- Provider latency under retry load
- Duplicate authorization prevention metrics

## Suggested Actions

- Add retry budget, backoff, jitter, and circuit breaking.
- Require idempotency keys for payment operations.
- Disable duplicate retry layers.
- Lower concurrency temporarily to protect provider and checkout path.

## Anti-patterns

- Do not retry payment writes without idempotency.
- Do not let frontend, backend, and gateway all retry the same operation independently.
- Do not treat retry storms as only provider degradation.
