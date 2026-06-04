# AI Incident Copilot Platform

Agentic RAG backend prototype for evidence-based incident diagnosis, runbook retrieval, structured diagnosis, trace, and evaluation.

## Demo

Install dependencies, then start the API:

```bash
uvicorn app.main:app --reload
```

In another terminal, run the end-to-end incident analysis demo:

```bash
python scripts/demo_incident_analysis.py
```

The script creates or reuses `payment-service`, inserts `DBConnectionTimeout` and `mysql-primary` logs, creates a `Payment API returns 500 errors` incident, runs analysis, and prints the diagnosis and trace.

Run the test suite:

```bash
pytest
```

Run the offline eval harness:

```bash
python eval/run_eval.py
```
