# Payment Provider Timeout

## Symptoms

Checkout or payment services log `payment provider request timed out`, `upstream payment timeout`, `deadline exceeded`, or retry exhaustion.

## Checks

Inspect provider latency, retry count, timeout configuration, circuit breaker state, and recent provider incidents.

## Suggested Actions

Reduce retry amplification, enable circuit breaker fallback, increase timeout only if safe, and contact provider support when external latency persists.

