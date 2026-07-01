---
source_type: official_docs_summary
source_url:
  - https://kafka.apache.org/documentation/#consumerconfigs
issue_type: timeout_issue
products: [Apache Kafka]
---

# Message Queue Lag

## When to Use

Use this runbook when asynchronous workflows are delayed, consumers fall behind, or user-visible state is stale because messages are not processed fast enough.

## Official Context

Kafka consumer behavior depends on group membership, partition assignment, poll interval, session timeout, and processing throughput. Lag means producers are adding messages faster than consumers commit progress.

## Common Signals

- Consumer lag grows continuously.
- Logs mention slow consumer, poll timeout, delayed processing, or rebalance.
- Checkout/order/search state becomes stale.
- Queue age increases while service pods remain running.

## Likely Causes

- Consumer processing is slower than producer rate.
- Downstream dependency inside consumer is slow.
- Batch size or max poll interval is mismatched with processing time.
- Too few partitions or consumers for workload.

## Diagnostic Commands

```text
kafka-consumer-groups --bootstrap-server <broker> --describe --group <group>
kubectl logs <consumer-pod> --since=15m
```

Check lag by partition, not only total lag.

## Metrics to Check

- Consumer lag count and oldest message age
- Consumer processing rate
- Rebalance frequency
- Downstream latency inside consumer
- Error and retry count in consumer loop

## Suggested Actions

- Scale consumers if partitions and downstream dependencies allow it.
- Reduce per-message processing time or batch size.
- Move slow calls out of the poll loop when possible.
- Alert on lag age, not only message count.

## Anti-patterns

- Do not scale consumers above partition count and expect improvement.
- Do not ignore downstream failures inside consumers.
- Do not treat lag as harmless if it affects user-visible freshness.
