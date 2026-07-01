---
source_type: official_docs_summary
source_url:
  - https://nginx.org/en/docs/http/ngx_http_proxy_module.html
issue_type: timeout_issue
products: [HTTP Clients, Third-Party APIs]
---

# Third-Party API Degradation

## When to Use

Use this runbook when an external API becomes slow or unreliable and internal services start returning timeout, 502, 503, or 504 errors.

## Common Signals

- Logs name one external provider or partner API repeatedly.
- Internal service health is normal except for calls to that dependency.
- Retry rate and latency increase at the same time.
- Errors affect a specific region, method, or integration.

## Likely Causes

- Third-party provider outage or rate limiting.
- Network path degradation.
- Client timeout/retry policy amplifies partial failures.
- Provider response schema or authentication changed.

## Diagnostic Commands

```text
curl -v --max-time 5 <third-party-endpoint>
kubectl logs <service> --since=15m
```

Compare internal processing time with external call duration.

## Metrics to Check

- External dependency latency and error rate
- Retry rate and circuit breaker state
- Internal queue depth caused by waiting calls
- Provider-specific status codes

## Suggested Actions

- Reduce retry amplification and enable circuit breaking.
- Route to alternate provider/path if available.
- Communicate third-party impact in incident summary.
- Track dependency SLO separately from internal service SLO.

## Anti-patterns

- Do not blame internal service CPU if the time is spent waiting on provider IO.
- Do not retry all provider errors equally.
- Do not omit provider name from the incident summary.
