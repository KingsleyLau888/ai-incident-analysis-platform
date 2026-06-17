# Bad Release Rollback

## Symptoms

Errors begin immediately after a deploy. Logs mention serialization failures, config mismatch, missing environment variables, or new exceptions.

## Checks

Compare deploy time with error onset, inspect changed files, config diffs, feature flags, and canary health.

## Suggested Actions

Roll back the release, disable the risky feature flag, and add regression tests for the failed path.

