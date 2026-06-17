# Config Or Secret Mismatch

## Symptoms

Services fail after configuration rollout. Logs mention invalid credentials, missing secret, config mismatch, or permission denied.

## Checks

Compare config versions, secret rotation timestamps, environment variables, and rollout status across instances.

## Suggested Actions

Restore the previous config, synchronize secrets, restart stale instances, and add config validation checks.

