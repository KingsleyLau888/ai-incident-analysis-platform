---
source_type: official_docs_summary
source_url:
  - https://www.rfc-editor.org/rfc/rfc6749
issue_type: auth_issue
products: [OAuth2]
---

# OAuth Callback Failure

## When to Use

Use this runbook when login fails during OAuth redirect, authorization code exchange, callback validation, or token exchange.

## Official Context

OAuth2 authorization code flow depends on exact redirect URI matching, valid client credentials, correct grant type, and secure token exchange. Small configuration mismatches often create user-visible login failures even when the application itself is healthy.

## Common Signals

- `invalid_grant`, `invalid_client`, `invalid redirect_uri`
- Callback route receives code but token exchange fails
- Users can start login but cannot complete it
- Failures begin after identity provider or client configuration changes

## Likely Causes

- Redirect URI differs from provider configuration.
- Client id or client secret is stale.
- Authorization code expires before exchange.
- Callback URL changed during deployment.
- Clock skew affects token validation.

## Diagnostic Commands

```text
kubectl logs <auth-service> --since=15m
curl -I <callback-url>
```

Compare configured redirect URI exactly, including scheme, host, path, and trailing slash.

## Metrics to Check

- OAuth callback failure rate
- Token exchange error code distribution
- Login completion rate
- Identity provider latency and availability

## Suggested Actions

- Restore known-good OAuth client configuration.
- Redeploy consistent client secret and callback configuration.
- Add structured logging for OAuth error codes without logging secrets.

## Anti-patterns

- Do not log authorization codes, access tokens, or client secrets.
- Do not broaden redirect URI rules casually.
- Do not treat OAuth provider errors as generic frontend failures.
