---
source_type: official_docs_summary
source_url:
  - https://kubernetes.io/docs/concepts/configuration/secret/
  - https://kubernetes.io/docs/concepts/configuration/configmap/
issue_type: auth_issue
products: [Kubernetes Secrets, Kubernetes ConfigMaps]
---

# Config or Secret Mismatch

## When to Use

Use this runbook when a deployment, secret rotation, or configuration update causes only some instances to fail authentication, connect to the wrong host, or reject tokens.

## Official Context

Kubernetes Secrets and ConfigMaps are common ways to inject credentials and configuration into pods. Depending on how values are mounted or exposed as environment variables, running pods may not automatically use updated values. This can create fleet skew.

## Common Signals

- Some pods succeed while others return 401/403 or connection errors
- Logs mention invalid token, bad credentials, wrong host, or signature mismatch
- Failures begin after secret/config rotation
- Restarting stale pods fixes only part of the issue

## Likely Causes

- Old pods still use previous secret values.
- ConfigMap/Secret mounted as environment variable was not refreshed.
- Deployment rollout partially completed.
- Services disagree on signing key, issuer, database password, or API endpoint.

## Diagnostic Commands

```text
kubectl get secret <name> -o yaml
kubectl get configmap <name> -o yaml
kubectl describe pod <pod>
kubectl rollout status deployment/<name>
```

Compare config version, checksum annotation, and environment values across pods.

## Metrics to Check

- Error rate by pod/version
- Secret/config version distribution
- Rollout progress and failed pods
- Auth failures by key id or credential version

## Suggested Actions

- Complete rollout so every instance uses the same config version.
- Restart stale pods when values are not refreshed automatically.
- Use checksum annotations to trigger rollout on config changes.
- Add a startup check that reports loaded config version.

## Anti-patterns

- Do not patch one pod manually and leave fleet skew.
- Do not print raw secrets while debugging.
- Do not assume ConfigMap/Secret updates instantly affect environment variables.
