---
source_type: official_docs_summary
source_url:
  - https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
  - https://kubernetes.io/docs/tasks/configure-pod-container/assign-memory-resource/
issue_type: memory_issue
products: [Kubernetes]
---

# Memory Pressure and OOMKilled Runbook

## When to Use

Use this runbook when workers restart, pods crash, containers are killed, or logs mention `OutOfMemory`, `OOMKilled`, heap exhaustion, memory limit exceeded, or process killed by the kernel.

## Official Context

Kubernetes uses resource requests and limits to schedule and constrain containers. If a container exceeds its memory limit, it can be terminated and reported as `OOMKilled`. Memory pressure can also affect node stability and pod eviction behavior.

## Common Signals

- Pod status or last termination reason shows `OOMKilled`.
- Application logs show heap allocation failure or out-of-memory errors.
- Restart count rises after traffic growth, batch jobs, or deployment.
- Memory working set approaches configured limit.
- Latency rises before restarts because garbage collection or swapping pressure increases.

## Likely Causes

- Container memory limit is lower than actual workload peak.
- Memory leak, unbounded cache, large batch, or queue accumulation.
- New release increases heap/object allocation.
- Concurrency or batch size grows without memory budget changes.
- Node-level memory pressure causes eviction or unstable scheduling.

## Diagnostic Commands

```text
kubectl describe pod <pod>
kubectl get pod <pod> -o jsonpath='{.status.containerStatuses[*].lastState}'
kubectl top pod <pod>
kubectl logs <pod> --previous
```

Check whether memory growth is steady, spike-based, or tied to a particular job.

## Metrics to Check

- Container memory working set and RSS
- Memory request and limit
- Restart count and last termination reason
- GC duration, heap usage, queue length, batch size
- Node memory pressure events

## Suggested Actions

- Roll back a memory-regressing release if timing is clear.
- Reduce batch size, queue prefetch, cache size, or request concurrency.
- Fix leaks or unbounded in-memory structures.
- Adjust requests and limits using observed peak usage, not guesswork.
- Add alerts for OOMKilled, restart count, and sustained memory growth.

## Anti-patterns

- Do not only raise memory limits without checking leaks.
- Do not ignore warning-level memory pressure; OOM often follows a trend.
- Do not compare average memory only; inspect peaks and growth rate.
