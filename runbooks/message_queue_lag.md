# Message Queue Lag

## Symptoms

Workers fall behind, queue depth grows, background jobs are delayed, and user-visible state updates lag behind requests.

## Checks

Inspect consumer lag, worker error rate, dead-letter queue, broker health, and recent payload size changes.

## Suggested Actions

Scale consumers, pause problematic producers, drain dead-letter messages, and cap payload sizes.

