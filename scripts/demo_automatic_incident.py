"""Demonstrate automatic log ingestion, incident creation, and analysis."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from integrations.python_logging_handler import IncidentPlatformHandler


PLATFORM_URL = os.getenv("INCIDENT_API_URL", "http://127.0.0.1:8000").rstrip("/")
SERVICE_NAME = f"payment-service-auto-demo-{int(time.time())}"


def main() -> None:
    logger = logging.getLogger("automatic-incident-demo")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    handler = IncidentPlatformHandler(
        platform_url=PLATFORM_URL,
        service_name=SERVICE_NAME,
        async_mode=False,  # F18：短生命周期脚本保持同步即时发送（Demo 轻量）
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    print(f"Service: {SERVICE_NAME}")
    print("Producing application logs...")
    logger.info("Payment request received")
    logger.error("DBConnectionTimeout while connecting to mysql-primary")
    logger.error("Payment request failed after database retry")
    logger.error("Payment API returned 500 because database connection failed")

    with httpx.Client(base_url=PLATFORM_URL, timeout=10.0, trust_env=False) as client:
        services = client.get("/services").json()
        service = next(item for item in services if item["name"] == SERVICE_NAME)
        incidents = client.get("/incidents", params={"service_id": service["id"]}).json()
        incident = incidents[-1]
        print(f"Incident created automatically: {incident['title']} (id={incident['id']})")

        last_step = None
        analysis = None
        for _ in range(120):
            jobs = client.get(
                "/analysis-jobs", params={"incident_id": incident["id"]}
            ).json()
            if jobs:
                job = jobs[0]
                current = (job["status"], job["current_step"], job["detail"])
                if current != last_step:
                    print(f"[{job['status']}] {job['current_step']}: {job['detail']}")
                    last_step = current
                if job["status"] == "failed":
                    raise RuntimeError(job.get("error") or "Analysis job failed.")
                if job["status"] == "succeeded":
                    analysis = client.get(f"/incidents/{incident['id']}/analysis").json()
                    trace = client.get(f"/incidents/{incident['id']}/trace").json()
                    analysis["trace"] = trace
                    break
            else:
                print("[pending] waiting_for_job: Waiting for automatic analysis job.")
            if analysis is not None:
                break
            time.sleep(1)

    if analysis is None:
        raise RuntimeError("Automatic analysis did not finish within 120 seconds.")

    print("\n=== Analysis Result ===")
    print(f"Issue Type: {analysis['issue_type']}")
    print(f"Severity: {analysis['severity']}")
    diagnosis = analysis.get("diagnosis_summary") or analysis.get("summary", "")
    print(f"Diagnosis: {diagnosis}")

    print("\nEvidence Logs:")
    for evidence in analysis["evidence_logs"]:
        print(f"- {evidence['log_entry']['message']}")

    print("\nRunbook Chunks:")
    for chunk in analysis["retrieved_runbook_chunks"]:
        print(f"- {chunk['source']} / {chunk['title']} (score={chunk['score']:.4f})")

    print("\nSimilar Incidents:")
    for item in analysis["similar_incidents"]:
        print(f"- {item['historical_id']}: {item['title']}")

    print("\nRoot Cause Hypotheses:")
    for hypothesis in analysis["root_cause_hypotheses"]:
        print(f"- {hypothesis['cause']} (confidence={hypothesis['confidence']:.2f})")

    print(f"\nImpact Scope: {analysis['impact_scope']}")
    print("\nSuggested Actions:")
    for action in analysis["structured_suggested_actions"]:
        print(f"- {action}")

    print("\nTrace:")
    for step in analysis["trace"]:
        print(f"{step['step_order']}. {step['step_name']}: {step['detail']}")


if __name__ == "__main__":
    main()
