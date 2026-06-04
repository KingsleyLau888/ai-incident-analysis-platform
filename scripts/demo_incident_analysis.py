import os
from datetime import UTC, datetime

import httpx


BASE_URL = os.getenv("INCIDENT_API_URL", "http://127.0.0.1:8000")


def main() -> None:
    with httpx.Client(base_url=BASE_URL, timeout=30.0, trust_env=False) as client:
        service = _create_demo_service(client)
        _create_demo_logs(client, service["id"])
        incident = _create_incident(client, service["id"])
        analysis = _request(client, "POST", f"/incidents/{incident['id']}/analyze")
        trace = _request(client, "GET", f"/incidents/{incident['id']}/trace")

    _print_demo_report(service, incident, analysis, trace)


def _create_demo_service(client: httpx.Client) -> dict:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return _request(
        client,
        "POST",
        "/services",
        json={
            "name": f"payment-service-demo-{timestamp}",
            "description": "Handles payment API requests.",
            "owner": "payments-team",
        },
    )


def _create_demo_logs(client: httpx.Client, service_id: int) -> None:
    messages = [
        ("INFO", "Payment request received for checkout"),
        ("ERROR", "DBConnectionTimeout while connecting to mysql-primary"),
        ("ERROR", "Payment API returned 500 after mysql-primary connection retry failed"),
    ]
    for level, message in messages:
        _request(
            client,
            "POST",
            "/logs",
            json={
                "service_id": service_id,
                "level": level,
                "message": message,
            },
        )


def _create_incident(client: httpx.Client, service_id: int) -> dict:
    return _request(
        client,
        "POST",
        "/incidents",
        json={
            "service_id": service_id,
            "title": "Payment API returns 500 errors",
            "description": "Users cannot complete payments because Payment API requests return HTTP 500.",
        },
    )


def _request(client: httpx.Client, method: str, path: str, **kwargs):
    try:
        response = client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError as exc:
        raise SystemExit(
            f"Cannot connect to {BASE_URL}. Start the API with: uvicorn app.main:app --reload"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise SystemExit(f"{method} {path} failed: {exc.response.status_code} {exc.response.text}") from exc


def _print_demo_report(service: dict, incident: dict, analysis: dict, trace: list[dict]) -> None:
    print("# AI Incident Copilot Demo")
    print()
    print(f"Service: {service['name']} (id={service['id']})")
    print(f"Incident: {incident['title']} (id={incident['id']})")
    print(f"Issue Type: {analysis['issue_type']}")
    print(f"Severity: {analysis['severity']}")

    print("\n## Analysis Plan")
    print(analysis["analysis_plan"]["analysis_plan"])
    for step in analysis["analysis_plan"]["tool_steps"]:
        print(f"- {step}")

    _print_section(
        "Evidence Logs",
        [
            f"{evidence['log_entry']['level']}: {evidence['log_entry']['message']}"
            for evidence in analysis["evidence_logs"]
        ],
    )
    _print_section(
        "Retrieved Runbook Chunks",
        [
            f"{chunk['source']} / {chunk['title']} (score={chunk['score']:.4f})\n  {chunk['content']}"
            for chunk in analysis["retrieved_runbook_chunks"]
        ],
    )

    print("\n## Diagnosis Summary")
    print(analysis["diagnosis_summary"])
    _print_section("Root Cause Hypotheses", analysis["root_cause_hypotheses"])

    print("\n## Impact Scope")
    print(analysis["impact_scope"])

    actions = analysis["structured_suggested_actions"] or [analysis["suggested_actions"]]
    _print_section("Suggested Actions", actions)
    _print_section(
        "Trace",
        [f"{step['step_order']}. {step['step_name']}: {step['detail']}" for step in trace],
        bullet=False,
    )


def _print_section(title: str, items: list[str], bullet: bool = True) -> None:
    print(f"\n## {title}")
    if not items:
        print("(none)")
        return
    for item in items:
        prefix = "- " if bullet else ""
        print(f"{prefix}{item}")


if __name__ == "__main__":
    main()
