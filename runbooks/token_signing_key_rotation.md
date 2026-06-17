# Token Signing Key Rotation

## Symptoms

Auth services log `401 unauthorized`, `token rejected`, `signature verification failed`, or valid users being rejected after a deploy or key rotation.

## Checks

Compare signing key versions across auth-service instances, API gateways, and token issuers. Check clock skew and stale pods.

## Suggested Actions

Synchronize signing keys, restart stale instances, validate token refresh flow, and add canary checks for key rotation.

