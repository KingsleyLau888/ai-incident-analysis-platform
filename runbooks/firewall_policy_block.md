# Firewall Or Network Policy Block

## Symptoms

Applications cannot connect to a previously reachable database or upstream service after a network or security policy change.

## Checks

Compare current firewall rules, security groups, Kubernetes NetworkPolicies, and route tables with the previous working version.

## Suggested Actions

Roll back the blocking rule, add explicit allow rules for the affected service, and validate connectivity from application pods.

