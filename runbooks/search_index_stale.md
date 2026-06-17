# Search Index Stale

## Symptoms

Search results are outdated or missing new products while write APIs remain healthy. Logs mention indexing lag or failed bulk index requests.

## Checks

Inspect indexing queue, search cluster health, bulk indexing failures, and last successful index timestamp.

## Suggested Actions

Restart index workers, replay failed index jobs, throttle bulk writes, and verify search freshness canaries.

