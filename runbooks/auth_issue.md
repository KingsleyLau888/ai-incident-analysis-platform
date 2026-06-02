# Authentication Issue Runbook

## Symptoms

Authentication incidents often show unauthorized responses, token validation failures, expired credentials, or rejected requests from an identity provider.

Common log signals include `401`, `unauthorized`, `token`, and `auth`.

## Initial Checks

Check token validation services, credential rotation, identity provider health, and recent configuration changes.

## Suggested Actions

Verify auth-service health, token signing keys, credential expiry, and deployment history.
