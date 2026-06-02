# Timeout Runbook

## Symptoms

Timeout incidents usually involve requests taking too long, upstream dependencies not responding, or clients giving up before a response is returned.

Common log signals include `timeout`, `timed out`, upstream latency, retries, and request deadline exceeded messages.

## Initial Checks

Identify the upstream dependency mentioned in the logs. Check latency, error rate, retry volume, and whether the timeout started after a deployment or configuration change.

## Suggested Actions

Compare service latency before and after the incident start time. Review timeout settings, retry policies, and dependency health.
