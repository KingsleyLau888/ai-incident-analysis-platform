# AI Incident Copilot Platform

## Agentic RAG for Incident Diagnosis

## 1. Project Vision

AI Incident Copilot Platform is a backend system for incident diagnosis.

The goal is to help engineers understand why an incident may be happening by combining rule-based signal detection, log evidence extraction, runbook retrieval, similar incident retrieval, LLM structured diagnosis, trace logging, and evaluation.

The platform is not intended to be a fully autonomous production agent. It is a copilot: it helps diagnose, explain, and recommend next steps, while humans remain responsible for operational decisions and remediation.

Example scenario:

`payment-service` starts failing payments. Logs show `DBConnectionTimeout when connecting to mysql-primary`. The platform should help identify likely database connection issues, show supporting evidence, retrieve relevant runbooks, compare similar past incidents, and produce structured suggestions.

## 2. Problem Statement

Incident response is often slowed down by scattered information:

- Logs are large and noisy.
- Runbooks are separate from incident data.
- Historical incidents are hard to search during pressure.
- Engineers need to quickly distinguish symptoms from likely root causes.
- AI-generated answers are hard to trust without evidence and traceability.

The current project is a simple FastAPI and rule-engine demo. It can classify log messages with keywords, but it cannot yet provide evidence-backed, context-aware diagnosis.

The target system should answer questions such as:

- What are the most likely root cause hypotheses?
- Which logs support those hypotheses?
- Which service or dependency appears affected?
- Which runbook steps are relevant?
- Have we seen a similar incident before?
- How confident is the diagnosis?
- How was the diagnosis produced?

## 3. Target Users

Primary users:

- On-call engineers
- SREs
- Backend engineers debugging production issues
- Incident commanders who need a quick diagnosis summary

Secondary users:

- Platform engineers building internal AIOps tooling
- Engineering managers reviewing incident patterns
- QA or reliability engineers creating incident eval cases

The system is designed for technical users who need concise, evidence-backed diagnosis rather than generic explanations.

## 4. Core User Workflow

The core workflow is incident-centered:

1. A service such as `payment-service` is registered in the platform.
2. Logs are ingested for that service.
3. An incident is created, for example: "Users cannot complete payments."
4. The user triggers analysis with `POST /incidents/{incident_id}/analyze`.
5. The backend collects relevant signals for the incident.
6. The system detects rule-based signals, such as `DBConnectionTimeout` and `mysql-primary`.
7. The system extracts evidence logs.
8. The system retrieves relevant runbooks and similar historical incidents.
9. The LLM produces structured diagnosis based on retrieved evidence.
10. The backend stores the analysis run, evidence, trace, and evaluation metadata.
11. The user receives root cause hypotheses, impact scope, suggested actions, confidence, and trace.

In the payment example, the expected output is not just `database_issue`. The output should explain that `payment-service` is likely failing because requests are timing out while connecting to `mysql-primary`, with evidence and recommended checks.

## 5. System Architecture

The system should be organized around a controlled analysis pipeline.

High-level architecture:

```text
FastAPI API
  -> Incident Service
  -> Analysis Service
  -> Analyze Pipeline
     -> Signal Collection
     -> Rule-Based Detection
     -> Evidence Extraction
     -> Runbook Retrieval
     -> Similar Incident Retrieval
     -> LLM Structured Diagnosis
     -> Validation
     -> Trace Logging
     -> Persistence
  -> Analysis Response
```

The current project already has useful foundations:

- `Service`
- `Incident`
- `LogEntry`
- `AnalysisRun`
- `IncidentEvidence`
- `AnalysisTrace`
- `rule_engine`

These should evolve gradually rather than be replaced all at once.

The intended architecture is agentic, but controlled. The system may choose different retrieval steps depending on the detected signals, but it should not perform automatic remediation or unrestricted tool usage.

## 6. AI Components

### Rule-Based Signal Detection

Rule-based signal detection provides a deterministic first pass over logs and other signals.

For example:

- `DBConnectionTimeout`
- `mysql-primary`
- `postgres`
- `connection pool`

These may indicate a database-related incident. This component is useful because it is fast, testable, and explainable.

It should not be the final diagnosis. It should produce candidate signals that guide later retrieval and diagnosis.

### Log Evidence Extraction

Log evidence extraction selects the most relevant logs for an incident.

Instead of using every log from `payment-service`, the system should prefer logs that are:

- Near the incident time window
- Repeated or correlated with failure spikes
- Matched by rule-based detectors
- Mentioning affected dependencies such as `mysql-primary`
- Useful as evidence for a root cause hypothesis

Example evidence:

```text
ERROR DBConnectionTimeout when connecting to mysql-primary
```

### Runbook Retrieval

Runbook retrieval finds operational guidance relevant to the current incident.

For the payment example, the system might retrieve:

```text
MySQL Connection Timeout Runbook
Payment Service Database Connectivity Runbook
```

The runbook should help generate practical next steps, such as checking database health, connection pool usage, recent configuration changes, and failover status.

### Similar Incident Retrieval

Similar incident retrieval searches past incidents for related symptoms, services, dependencies, and resolutions.

For example:

```text
Previous incident:
payment-service failed due to mysql-primary connection pool exhaustion.
Symptoms included DBConnectionTimeout and payment request failures.
Resolution was to roll back a database pool configuration change.
```

This helps the system avoid generic answers and reuse organizational memory.

### LLM Structured Diagnosis

The LLM should synthesize evidence, runbooks, and similar incidents into structured output.

It should not invent facts. Each major conclusion should be grounded in retrieved evidence.

Target output:

- Root cause hypotheses
- Impact scope
- Supporting evidence
- Suggested actions
- Confidence
- Missing information
- Alternative hypotheses

Example hypothesis:

```text
payment-service is likely experiencing database connection timeouts while connecting to mysql-primary.
The strongest hypothesis is connection pool exhaustion or mysql-primary connection saturation.
```

### Trace Logging

Trace logging records how the diagnosis was produced.

Trace should capture:

- Pipeline step name
- Step input summary
- Step output summary
- Evidence IDs used
- Retrieval results
- LLM request metadata
- Validation status
- Duration
- Errors, if any

Trace makes the copilot easier to debug and easier to trust.

### Evaluation

Evaluation measures whether the diagnosis is useful and grounded.

The project should include fixed incident cases, expected outcomes, and scoring logic. Evaluation is especially important once LLM diagnosis is introduced.

Example eval case:

```text
Input:
payment-service incident with DBConnectionTimeout logs referencing mysql-primary.

Expected:
database connectivity hypothesis, mysql-primary dependency, evidence citation, and database runbook action.
```

## 7. Backend Components

### FastAPI APIs

FastAPI remains the API layer.

Core API areas:

- Services
- Logs or signals
- Incidents
- Analysis
- Trace
- Runbooks
- Evaluation reports

The existing `POST /incidents/{incident_id}/analyze` endpoint should remain the main analysis trigger.

### Database Models

Database models should represent the incident diagnosis domain:

- Services
- Incidents
- Logs and future signals
- Runbooks
- Analysis runs
- Evidence items
- Trace steps
- Evaluation reports
- Feedback

The model should support current demo behavior while allowing future expansion.

### Analysis Job

An analysis job represents the execution of an incident diagnosis pipeline.

In the MVP, this can run synchronously inside the request. Later, it can become an async background job.

The job should know:

- Incident ID
- Analysis status
- Start and end time
- Pipeline version
- Error state

### Analysis Run

An analysis run is the persisted result of one diagnosis attempt.

It should store:

- Incident ID
- Primary issue type
- Root cause hypotheses
- Impact scope
- Suggested actions
- Confidence
- Created timestamp
- Pipeline version

Multiple analysis runs may exist for the same incident.

### Trace

Trace stores step-level execution detail.

It should explain how the system moved from:

```text
payment-service payment failure
```

to:

```text
likely DBConnectionTimeout against mysql-primary
```

### Eval Report

An eval report records the quality of an analysis run against expected behavior.

It may include:

- Root cause match score
- Evidence grounding score
- Suggested action quality
- Schema validity
- Hallucination checks
- Regression status

## 8. Analyze Pipeline

Recommended pipeline:

```text
1. Load incident
2. Load service context
3. Collect relevant logs and signals
4. Run rule-based signal detection
5. Extract and rank evidence logs
6. Retrieve related runbooks
7. Retrieve similar historical incidents
8. Build diagnosis context
9. Run LLM structured diagnosis
10. Validate structured output
11. Persist analysis run
12. Persist evidence and trace
13. Return diagnosis response
```

Payment example:

```text
Incident:
Users cannot complete payments.

Service:
payment-service

Relevant log:
ERROR DBConnectionTimeout when connecting to mysql-primary

Rule signal:
database_issue

Runbook:
MySQL connection timeout runbook

Similar incident:
Previous payment-service outage caused by mysql-primary connection saturation

Diagnosis:
payment-service is likely failing because database connections to mysql-primary are timing out.
```

## 9. Data Models

Recommended conceptual data models:

### Service

Represents a business service.

Example:

```text
payment-service
```

### Incident

Represents a specific operational problem.

Important fields:

- Service ID
- Title
- Description
- Status
- Severity
- Start time
- End time
- Environment
- Impact summary

### Signal

Represents observable system data.

Signal types may include:

- Log
- Metric
- Alert
- Deployment event
- Trace span

The current `LogEntry` model can remain the first signal type.

### Runbook

Represents operational guidance.

Important fields:

- Title
- Service or domain
- Content
- Tags
- Version

### AnalysisRun

Represents one diagnosis attempt for an incident.

Important fields:

- Incident ID
- Status
- Primary issue type
- Root cause hypotheses
- Impact scope
- Suggested actions
- Confidence
- Pipeline version

### Evidence

Represents evidence used by the diagnosis.

Evidence can point to:

- Log entries
- Runbooks
- Similar incidents
- Metrics
- Alerts

### TraceStep

Represents one step in the pipeline.

Important fields:

- Analysis run ID
- Step name
- Step order
- Input summary
- Output summary
- Status
- Duration
- Metadata

### EvalReport

Represents quality assessment for an analysis.

Important fields:

- Analysis run ID
- Dataset case ID
- Scores
- Pass or fail status
- Notes

## 10. Evaluation Metrics

Recommended evaluation metrics:

- Root cause hypothesis quality
- Evidence grounding
- Correct issue type classification
- Suggested action usefulness
- Runbook retrieval relevance
- Similar incident retrieval relevance
- Impact scope correctness
- Structured output validity
- Trace completeness
- Hallucination rate
- Regression pass rate

For the payment example, a good analysis should:

- Identify database connectivity as the likely issue.
- Mention `mysql-primary` as the affected dependency.
- Cite the `DBConnectionTimeout` log.
- Recommend checking database health and connection pool usage.
- Avoid claiming automatic remediation.

## 11. MVP Scope

The first version should focus on diagnosis, suggestions, trace, and eval.

In scope:

- Keep FastAPI backend
- Keep incident-centered workflow
- Keep `POST /incidents/{incident_id}/analyze`
- Rule-based signal detection
- Log evidence extraction
- Basic runbook retrieval
- Basic similar incident retrieval
- LLM structured diagnosis
- Trace logging
- Evaluation reports

Outcomes expected from MVP:

- Root cause hypotheses
- Evidence logs
- Suggested actions
- Confidence
- Trace
- Eval report

The MVP should use a controlled pipeline rather than a fully autonomous agent.

## 12. Future Work

Future work may include:

- Metrics ingestion
- Alert ingestion
- Deployment event correlation
- Service dependency graph
- Vector search for runbooks and historical incidents
- Async analysis jobs
- Human feedback loop
- Better eval datasets
- Incident timeline generation
- Slack or PagerDuty integrations
- Multi-incident pattern analysis

These should be added incrementally after the MVP pipeline is stable.

## 13. What Is Intentionally Out of Scope

The first version intentionally does not include:

- Fully autonomous production remediation
- Automatic rollback
- Automatic database failover
- Unrestricted agent tool execution
- Direct production infrastructure changes
- Replacing human incident commanders
- Real-time monitoring platform replacement
- Full APM or observability platform features

The platform should remain a copilot. It can diagnose, explain, recommend, trace, and evaluate. It should not independently modify production systems.
