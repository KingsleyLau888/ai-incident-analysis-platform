# Server Error Runbook

## Symptoms

Server error incidents often show HTTP 500 responses, unhandled exceptions, internal server errors, or repeated application stack failures.

Common log signals include `500`, `internal server error`, exception messages, and failed request handlers.

## Initial Checks

Identify the failing endpoint, recent deployments, exception frequency, and whether errors are isolated to one service or spread across dependencies.

## Suggested Actions

Inspect application error logs, stack traces, recent changes, dependency health, and rollback options.
