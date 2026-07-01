---
source_type: official_docs_summary
source_url:
  - https://kubernetes.io/docs/concepts/services-networking/network-policies/
issue_type: database_issue
products: [Kubernetes NetworkPolicy]
---

# Network Policy Blocking Database Access

## When to Use

Use this runbook when an application and database are individually healthy but traffic between them fails after firewall, security group, service mesh, or Kubernetes NetworkPolicy changes.

## Official Context

Kubernetes NetworkPolicy controls ingress and egress traffic based on pod selectors, namespaces, and ports. A policy can accidentally isolate a service from its database even if DNS and both pods are healthy.

## Common Signals

- Connection timeout rather than authentication failure
- Database host resolves but connection never completes
- Errors begin after network policy, firewall, or namespace label changes
- Only one namespace, service account, or pod label group is affected

## Likely Causes

- Egress from application namespace to database port is blocked.
- Ingress to database pods does not allow the application selector.
- Namespace labels changed and policy no longer matches.
- Service mesh or firewall rule blocks the path outside Kubernetes.

## Diagnostic Commands

```text
kubectl get networkpolicy -A
kubectl describe networkpolicy <policy> -n <namespace>
kubectl get pod --show-labels -n <namespace>
nc -vz <db-host> <db-port>
```

Test from inside the affected pod, not only from your laptop.

## Metrics to Check

- Connection timeout rate by source service
- NetworkPolicy changes and deployment timestamps
- DNS success rate versus TCP connection success rate
- Database accepted connection count drop

## Suggested Actions

- Roll back the policy change if it correlates with the outage.
- Add explicit least-privilege allow rules for application-to-database traffic.
- Add synthetic connectivity checks for critical service dependencies.

## Anti-patterns

- Do not only test connectivity from outside the cluster.
- Do not open all ingress/egress permanently just to recover.
- Do not classify the issue as database down if the database is healthy but isolated.
