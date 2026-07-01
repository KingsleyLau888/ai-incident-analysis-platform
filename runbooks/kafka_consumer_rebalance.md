---
source_type: official_docs_summary
source_url:
  - https://kafka.apache.org/documentation/#consumerconfigs
issue_type: timeout_issue
products: [Apache Kafka]
---

# Kafka Consumer Rebalance

## When to Use

Use this runbook when Kafka consumer groups rebalance repeatedly, processing pauses, or lag rises during consumer instability.

## Common Signals

- Logs mention `rebalance`, `partition revoked`, `partition assigned`, `missed heartbeat`, or `max.poll.interval.ms`.
- Throughput drops while consumers appear alive.
- Lag rises after deployment, autoscaling, or slow processing.

## Likely Causes

- Processing takes longer than max poll interval.
- Consumers restart frequently during deployment.
- Heartbeats are delayed by CPU pressure or blocking work.
- Autoscaling changes membership too often.

## Diagnostic Commands

```text
kafka-consumer-groups --bootstrap-server <broker> --describe --group <group>
kubectl rollout history deployment/<consumer>
```

Correlate rebalance events with deployments and processing latency.

## Metrics to Check

- Rebalance count
- Poll duration and processing duration
- Consumer lag age
- Consumer restarts
- CPU throttling or garbage collection pauses

## Suggested Actions

- Tune `max.poll.interval.ms` and batch size to match processing time.
- Avoid unstable autoscaling that constantly changes group membership.
- Move slow IO out of the critical poll path.
- Add alerting for rebalance loops and lag age.

## Anti-patterns

- Do not only increase poll interval if processing is genuinely stuck.
- Do not redeploy all consumers at once during an incident.
- Do not ignore CPU throttling; it can delay heartbeats.
