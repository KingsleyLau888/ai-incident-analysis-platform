---
source_type: official_docs_summary
source_url:
  - https://www.postgresql.org/docs/current/auth-pg-hba-conf.html
  - https://www.rfc-editor.org/rfc/rfc6749
  - https://www.rfc-editor.org/rfc/rfc7519
  - https://kubernetes.io/docs/concepts/configuration/secret/
issue_type: auth_issue
products: [OAuth2, JWT, PostgreSQL, Kubernetes Secrets]
---

# Authentication and Token Failure Runbook

## When to Use

Use this runbook when requests fail with `401`, `403`, `unauthorized`, `authentication failed`, `invalid token`, `expired token`, rejected credentials, or signing key mismatch. It applies to user login, checkout session creation, service-to-service calls, and database authentication.

## Official Context

OAuth2 defines authorization and token exchange flows where clients, redirect URIs, grants, and tokens must match provider configuration. JWT validation depends on issuer, audience, expiry, signature algorithm, and signing keys.

Kubernetes Secrets and ConfigMaps are common delivery mechanisms for credentials. A rotation can fail if some pods keep stale values while others use new values.

PostgreSQL authentication rules can reject an otherwise reachable client if host/user/database/method configuration does not allow the connection.

## Common Signals

- `401 unauthorized token rejected`
- `Authentication failed while creating checkout session`
- `invalid signature`, `unknown kid`, `expired token`
- `bad credentials`, `permission denied`, `403 forbidden`
- Error spike starts after secret rotation, key rotation, gateway policy, or auth middleware deployment

## Likely Causes

- Token expired, malformed, signed by an old key, or validated with wrong issuer/audience.
- Signing key rotation did not propagate to every service instance.
- Client secret or database password changed but stale pods were not restarted.
- Gateway/auth middleware policy rejects a route that previously passed.
- OAuth callback URI or client credentials do not match provider configuration.

## Diagnostic Commands

```text
kubectl get secret <name> -o yaml
kubectl describe pod <pod>
kubectl logs <auth-pod> --since=15m
```

Decode a sample token without trusting it and inspect issuer, audience, expiry, and key id. Compare current secret versions across running pods.

## Metrics to Check

- Auth failure rate by reason and route
- Token validation failures by issuer/audience/key id
- Secret/config version skew across instances
- Gateway 401/403 counts
- Login callback failure rate

## Suggested Actions

- Refresh JWKS/key caches or restart stale validators if rotation is the cause.
- Roll out the same secret/config version to every instance.
- Verify OAuth redirect URI, client id, client secret, issuer, audience, and expiry behavior.
- Roll back auth middleware or gateway policy if failures correlate with deployment.

## Anti-patterns

- Do not log full tokens or secrets during debugging.
- Do not disable signature or expiry validation to recover quickly.
- Do not assume every 401 is user error; fleet-wide spikes usually indicate system configuration.
