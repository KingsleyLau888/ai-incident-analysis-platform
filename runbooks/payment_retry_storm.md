# Payment Retry Storm

## Symptoms

Logs show many payment retries, retry exhausted messages, duplicate authorization attempts, or API saturation after upstream latency.

## Checks

Measure retry rate, queue depth, provider error rate, idempotency behavior, and whether clients are also retrying.

## Suggested Actions

Throttle retries, enforce idempotency keys, add exponential backoff, and temporarily shed noncritical traffic.

