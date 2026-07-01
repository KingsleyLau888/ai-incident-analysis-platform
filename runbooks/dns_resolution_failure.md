---
source_type: official_docs_summary
source_url:
  - https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/
issue_type: timeout_issue
products: [Kubernetes DNS]
---

# DNS Resolution Failure

## When to Use

Use this runbook when services fail before connecting to an upstream because hostname lookup fails or becomes slow.

## Common Signals

- `no such host`, `temporary failure in name resolution`, `DNS timeout`
- Multiple upstreams fail by hostname
- Direct IP connectivity works but service name fails
- Failures appear after DNS, namespace, service, or CoreDNS changes

## Likely Causes

- CoreDNS unavailable or overloaded.
- Wrong service name, namespace, or search path.
- DNS records missing for service endpoints.
- NetworkPolicy blocks DNS traffic.

## Diagnostic Commands

```text
kubectl exec <pod> -- nslookup <service>.<namespace>.svc.cluster.local
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns --since=15m
```

Run checks from the affected pod namespace.

## Metrics to Check

- DNS query error rate
- DNS lookup latency
- CoreDNS pod restarts and CPU
- Service endpoint count
- NetworkPolicy affecting DNS egress

## Suggested Actions

- Restore CoreDNS health or roll back DNS config changes.
- Fix service name, namespace, or endpoint configuration.
- Allow DNS egress from affected namespace.
- Add synthetic DNS checks for critical dependencies.

## Anti-patterns

- Do not only test DNS from your workstation.
- Do not hardcode IPs as a permanent fix.
- Do not confuse DNS resolution failure with database or API outage.
