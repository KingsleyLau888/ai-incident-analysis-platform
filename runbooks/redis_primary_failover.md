---
source_type: official_docs_summary
source_url:
  - https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/
  - https://redis.io/docs/latest/develop/reference/clients/
issue_type: cache_issue
products: [Redis]
---

# Redis Primary Failover

## When to Use

Use this runbook when Redis primary failover causes cache read/write failures, reconnect loops, stale topology, or clients writing to a replica.

## Official Context

Redis high availability systems can promote a new primary after failure. Clients must reconnect, refresh topology, and handle transient errors during role changes. Some applications keep stale connections and continue sending writes to the old primary or replica.

## Common Signals

- `READONLY You can't write against a read only replica`
- `RedisConnection refused`, reconnect loop, or timeout
- Errors occur during or immediately after failover event
- Some instances recover while others keep failing
- Cache writes fail but application still serves partial traffic

## Likely Causes

- Client topology cache is stale after failover.
- DNS or service endpoint still points to an old Redis node.
- Client reconnect timeout is too short.
- Application does not handle transient Redis errors.

## Diagnostic Commands

```text
redis-cli INFO replication
redis-cli ROLE
redis-cli INFO clients
```

Compare Redis role and endpoint from the perspective of each application instance.

## Metrics to Check

- Redis role changes and failover events
- Client reconnect errors and timeout count
- Cache write failure rate
- Connected clients per node
- Application fallback latency

## Suggested Actions

- Refresh client topology or restart only stale clients.
- Ensure the application uses the intended HA endpoint.
- Tune reconnect/backoff behavior.
- Add alerts for role changes, reconnect storms, and `READONLY` errors.

## Anti-patterns

- Do not assume all clients recover equally after failover.
- Do not disable cache writes globally if only stale clients are affected.
- Do not hide failover errors without measuring fallback latency.
