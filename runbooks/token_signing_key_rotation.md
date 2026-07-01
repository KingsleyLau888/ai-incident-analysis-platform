---
source_type: official_docs_summary
source_url:
  - https://www.rfc-editor.org/rfc/rfc7517
  - https://www.rfc-editor.org/rfc/rfc7519
issue_type: auth_issue
products: [JWKS, JWT]
---

# Token Signing Key Rotation

## When to Use

Use this runbook when JWT validation fails after signing key rotation, services return 401, or validators disagree about the active key set.

## Official Context

JWT validation depends on signature, issuer, audience, expiry, and key id. JWKS exposes public keys used by verifiers. During rotation, old and new keys often need overlap so in-flight tokens remain valid while validators refresh their cache.

## Common Signals

- `invalid signature`, `unknown kid`, `JWT validation failed`
- Auth failures after identity provider key rotation
- Some services reject tokens while others accept them
- Restarting a service refreshes keys and resolves the issue temporarily

## Likely Causes

- JWKS cache is stale.
- Old signing key removed before old tokens expired.
- Validator expects wrong issuer, audience, or algorithm.
- Services have inconsistent key refresh intervals.

## Diagnostic Commands

```text
curl <issuer>/.well-known/jwks.json
kubectl logs <auth-validator> --since=15m
```

Inspect token header `kid` and compare it with currently published JWKS.

## Metrics to Check

- Token validation failures by `kid`
- JWKS refresh success/failure count
- 401 rate by service instance
- Secret/config version skew

## Suggested Actions

- Refresh JWKS caches or restart stale validators.
- Restore old key until old tokens expire if it was removed too early.
- Standardize issuer, audience, and algorithm validation config.

## Anti-patterns

- Do not disable signature validation.
- Do not remove old keys before token TTL overlap ends.
- Do not log full JWTs while debugging.
