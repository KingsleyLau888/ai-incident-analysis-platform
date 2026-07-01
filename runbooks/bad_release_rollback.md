---
source_type: official_docs_summary
source_url:
  - https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
issue_type: server_error
products: [Kubernetes Deployments]
---

# Bad Release Rollback

## When to Use

Use this runbook when 5xx errors, crashes, readiness failures, latency spikes, or dependency errors begin immediately after a deployment or rollout.

## Official Context

Kubernetes Deployments manage rollout and rollback of application versions. Rollout history, ReplicaSet state, readiness, and pod events help determine whether the new version is unhealthy and whether rollback is appropriate.

## Common Signals

- Error rate changes at the same time as a new deployment.
- Only new pods or one version fails.
- Readiness or liveness probes fail after rollout.
- CrashLoopBackOff, OOMKilled, or dependency errors appear only in new version.
- Rolling back reduces error rate.

## Likely Causes

- Application bug or incompatible config in new release.
- Database migration mismatch.
- Missing environment variable, secret, or feature flag.
- New version increases memory, CPU, or dependency load.
- Readiness probe does not represent real dependency health.

## Diagnostic Commands

```text
kubectl rollout history deployment/<name>
kubectl rollout status deployment/<name>
kubectl describe pod <pod>
kubectl logs <pod> --previous
```

Compare failing version, pod template, config, and image tag with the last healthy version.

## Metrics to Check

- Error rate by version
- Pod readiness and restart count
- Deployment event timeline
- Latency and dependency error rate by version
- Canary or rollout health checks

## Suggested Actions

- Roll back to the previous stable version when deployment correlation is strong.
- Pause rollout while investigating.
- Verify database migration compatibility and feature flag state.
- Add canary gates for error rate, readiness, latency, and dependency health.

## Anti-patterns

- Do not keep rolling forward while error rate is rising.
- Do not roll back blindly if the failure is caused by external dependency outage.
- Do not rely only on pod readiness if user-facing errors are already high.
