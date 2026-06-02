# Memory Issue Runbook

## Symptoms

Memory incidents often show out-of-memory errors, OOM kills, high heap usage, garbage collection pressure, or containers restarting unexpectedly.

Common log signals include `OutOfMemory`, `OOM`, memory allocation failures, and process killed messages.

## Initial Checks

Check memory usage, container limits, restart count, and recent traffic or deployment changes.

## Suggested Actions

Inspect heap, resident memory, recent releases, traffic spikes, and memory limit configuration.
