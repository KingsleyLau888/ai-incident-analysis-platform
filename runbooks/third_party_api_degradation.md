# Third Party API Degradation

## Symptoms

Application errors correlate with a vendor or external API. Logs mention provider timeout, upstream 5xx, gateway timeout, or retry exhaustion.

## Checks

Inspect provider status page, vendor latency, error codes, retry volume, and circuit breaker metrics.

## Suggested Actions

Open vendor incident, enable fallback behavior, reduce retry pressure, and communicate degraded external dependency status.

