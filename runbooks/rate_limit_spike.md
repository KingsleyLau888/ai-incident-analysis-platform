---
source_type: official_docs_summary
source_url:
  - https://nginx.org/en/docs/http/ngx_http_limit_req_module.html
issue_type: server_error
products: [NGINX]
---

# Rate Limit Spike

## When to Use

Use this runbook when requests are rejected or delayed because traffic exceeds configured rate limits.

## Official Context

NGINX request limiting can delay or reject requests based on configured rate and burst. Rate limits are useful protection, but spikes may indicate retry loops, abusive clients, or legitimate traffic growth.

## Common Signals

- `429`, rate limited, excessive request rate
- One client, tenant, route, or API token dominates traffic
- Backend is healthy but requests are rejected at gateway
- Error starts after retry behavior or traffic source changes

## Likely Causes

- Legitimate traffic exceeds old limit.
- Client retry loop creates self-amplifying traffic.
- Bot or abusive client causes burst.
- Rate limit key is too broad and groups unrelated users.

## Diagnostic Commands

```text
kubectl logs <gateway> --since=15m
```

Group rejected requests by route, tenant, IP, user, and token.

## Metrics to Check

- Rate-limited request count by key
- Request rate versus configured limit
- Retry rate from clients
- Backend saturation to confirm whether limiting protected the service

## Suggested Actions

- Tune rate and burst only after identifying traffic source.
- Reduce retry loops that trigger limits.
- Add per-tenant or per-route limits if one key is too broad.
- Alert on sudden changes in rate-limited requests.

## Anti-patterns

- Do not simply disable rate limiting during unknown traffic spikes.
- Do not classify 429 as backend outage.
- Do not ignore retry behavior from your own clients.
