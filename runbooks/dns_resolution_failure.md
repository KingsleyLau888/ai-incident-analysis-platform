# DNS Resolution Failure

## Symptoms

Services log `could not resolve host`, DNS timeout, name lookup failure, or intermittent connection failures to dependencies.

## Checks

Inspect resolver health, service discovery records, DNS TTLs, CoreDNS logs, and recent network changes.

## Suggested Actions

Restore DNS records, restart unhealthy resolvers, roll back service discovery changes, and add dependency DNS canaries.

