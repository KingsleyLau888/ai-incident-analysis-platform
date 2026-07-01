---
source_type: official_docs_summary
source_url:
  - https://nginx.org/en/docs/http/ngx_http_proxy_module.html
  - https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/
  - https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
issue_type: server_error
products: [NGINX, Kubernetes]
---

# HTTP 5xx and Application Error Runbook

## When to Use

Use this runbook when users see HTTP 500, 502, 503, or 504 and no stronger root-cause signal has been confirmed yet. Treat generic 5xx as a symptom until correlated with application exceptions, dependency failures, deployment events, or runtime crashes.

## Official Context

NGINX proxy behavior can surface upstream failures as 502/504 depending on connection, response, and timeout behavior. Kubernetes pod lifecycle and Deployment rollout events help determine whether the application is crashing, not ready, or failing after a new version.

## Common Signals

- `500`, `internal server error`, unhandled exception, stack trace
- `502 bad gateway`, `503 service unavailable`, `504 gateway timeout`
- Readiness or liveness failures
- CrashLoopBackOff, repeated restarts, or failed rollout
- Error spike starts immediately after deployment or config change

## Likely Causes

- Application exception or bad release.
- Backend pod not ready, crashing, or unreachable from proxy.
- Upstream dependency unavailable or too slow.
- Misconfigured proxy route, service selector, or deployment.
- Resource pressure causing intermittent crashes.

## Diagnostic Commands

```text
kubectl get pods
kubectl describe pod <pod>
kubectl rollout history deployment/<name>
kubectl logs <pod> --previous
```

Correlate gateway logs with application logs for the same request window.

## Metrics to Check

- 5xx rate by route and upstream
- Pod restarts and readiness failures
- Deployment version and rollout timeline
- Application exception count
- Upstream latency and saturation

## Suggested Actions

- Search for stronger signals: database, timeout, auth, cache, memory.
- Roll back a release if 5xx correlates with rollout and old version is known healthy.
- Fix route/service selector/proxy config if traffic cannot reach ready pods.
- Add canary checks for exceptions, readiness, and dependency health.

## Anti-patterns

- Do not stop analysis at `server_error` when logs mention a specific dependency.
- Do not use HTTP 500 alone as root cause.
- Do not retry all 5xx blindly; retries can amplify downstream failures.
