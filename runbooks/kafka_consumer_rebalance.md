# Kafka Consumer Rebalance Loop

## Symptoms

Consumers repeatedly rebalance, processing stalls, offsets stop advancing, and logs mention group coordinator or session timeout.

## Checks

Inspect consumer group state, session timeout, max poll interval, partition assignment, and broker health.

## Suggested Actions

Tune poll interval, reduce processing batch size, stabilize consumer membership, and scale partitions carefully.

