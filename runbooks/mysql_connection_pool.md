# MySQL Connection Pool Saturation

## Symptoms

Applications log `DBConnectionTimeout`, `mysql-primary connection limit reached`, or `too many connections`. User-facing APIs may show payment failures, checkout 500 errors, or delayed order creation.

## Checks

Inspect active connection count, connection pool utilization, slow transactions, and recent traffic spikes. Compare application pool size with database max connections.

## Suggested Actions

Reduce connection hold time, tune pool size, terminate stale sessions, and add alerts for pool saturation before user-facing failures occur.

