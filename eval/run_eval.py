import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import Base
from app.models import base
from app.schemas.incident import IncidentCreate
from app.schemas.log_entry import LogEntryCreate
from app.schemas.service import ServiceCreate
from app.services import analysis_service, incident_service, log_service, service_service


EVAL_DIR = PROJECT_ROOT / "eval"
DEFAULT_CASES_PATH = EVAL_DIR / "eval_cases.json"
DEFAULT_REPORT_PATH = EVAL_DIR / "eval_report.md"


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    service_name: str
    incident_title: str
    incident_description: str | None
    logs: list[str]
    expected_issue_type: str
    expected_severity: str
    expected_evidence_keywords: list[str]
    expected_runbook_sources: list[str]


def load_eval_cases(path: Path = DEFAULT_CASES_PATH) -> list[EvalCase]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [EvalCase(**item) for item in data]


def run_eval(
    cases_path: Path = DEFAULT_CASES_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> dict:
    cases = load_eval_cases(cases_path)
    case_results = []

    with _evaluation_session() as db:
        for case in cases:
            started = time.perf_counter()
            analysis = _run_case(db, case)
            latency_ms = (time.perf_counter() - started) * 1000
            case_results.append(_score_case(case, analysis, latency_ms))

    metrics = _aggregate_metrics(case_results)
    report = {
        "total_cases": len(cases),
        "metrics": metrics,
        "cases": case_results,
        "failed_cases": [result for result in case_results if not result["passed"]],
    }
    write_report(report, report_path)
    return report


def write_report(report: dict, path: Path = DEFAULT_REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Eval Report",
        "",
        f"Total cases: {report['total_cases']}",
        "",
        "## Metrics",
        "",
    ]
    for name, value in report["metrics"].items():
        if name == "average_latency_ms":
            lines.append(f"- {name}: {value:.2f}")
        else:
            lines.append(f"- {name}: {value:.2%}")

    lines.extend(["", "## Cases", ""])
    for result in report["cases"]:
        lines.extend(
            [
                f"### {result['case_id']}",
                "",
                f"- expected_issue_type: {result['expected_issue_type']}",
                f"- actual_issue_type: {result['actual_issue_type']}",
                f"- expected_severity: {result['expected_severity']}",
                f"- actual_severity: {result['actual_severity']}",
                f"- expected_runbook_sources: {', '.join(result['expected_runbook_sources']) or '(none)'}",
                f"- actual_runbook_sources: {', '.join(result['actual_runbook_sources']) or '(none)'}",
                f"- evidence_recall: {result['evidence_recall']:.2%}",
                f"- runbook_retrieval_recall: {result['runbook_retrieval_recall']:.2%}",
                f"- latency_ms: {result['latency_ms']:.2f}",
                f"- passed: {result['passed']}",
                "",
            ]
        )

    lines.extend(["## Failed Cases", ""])
    if report["failed_cases"]:
        for result in report["failed_cases"]:
            lines.append(f"- {result['case_id']}")
    else:
        lines.append("- None")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _evaluation_session():
    class EvaluationSession:
        def __enter__(self) -> Session:
            self._engine = create_engine(
                "sqlite://",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
            self._session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
            Base.metadata.create_all(bind=self._engine)
            self._session = self._session_factory()
            return self._session

        def __exit__(self, exc_type, exc, traceback) -> None:
            self._session.close()
            Base.metadata.drop_all(bind=self._engine)
            self._engine.dispose()

    return EvaluationSession()


def _run_case(db: Session, case: EvalCase):
    service = service_service.create_service(db, ServiceCreate(name=case.service_name))
    for message in case.logs:
        log_service.create_log_entry(
            db,
            LogEntryCreate(
                service_id=service.id,
                level="ERROR" if "error" in message.lower() else "INFO",
                message=message,
            ),
        )
    incident = incident_service.create_incident(
        db,
        IncidentCreate(
            service_id=service.id,
            title=case.incident_title,
            description=case.incident_description,
        ),
    )
    return analysis_service.analyze_incident(db, incident)


def _score_case(case: EvalCase, analysis, latency_ms: float) -> dict:
    actual_evidence_messages = [evidence.log_entry.message for evidence in analysis.evidence_logs]
    actual_runbook_sources = [chunk["source"] for chunk in analysis.retrieved_runbook_chunks]
    evidence_recall = _keyword_recall(case.expected_evidence_keywords, actual_evidence_messages)
    runbook_recall = _source_recall(case.expected_runbook_sources, actual_runbook_sources)
    issue_type_match = analysis.issue_type == case.expected_issue_type
    severity_match = analysis.severity == case.expected_severity
    passed = issue_type_match and severity_match and evidence_recall == 1.0 and runbook_recall == 1.0

    return {
        "case_id": case.case_id,
        "expected_issue_type": case.expected_issue_type,
        "actual_issue_type": analysis.issue_type,
        "expected_severity": case.expected_severity,
        "actual_severity": analysis.severity,
        "expected_evidence_keywords": case.expected_evidence_keywords,
        "actual_evidence_messages": actual_evidence_messages,
        "expected_runbook_sources": case.expected_runbook_sources,
        "actual_runbook_sources": actual_runbook_sources,
        "issue_type_match": issue_type_match,
        "severity_match": severity_match,
        "evidence_recall": evidence_recall,
        "runbook_retrieval_recall": runbook_recall,
        "latency_ms": latency_ms,
        "passed": passed,
    }


def _aggregate_metrics(results: list[dict]) -> dict:
    total = len(results) or 1
    return {
        "issue_type_accuracy": sum(1 for result in results if result["issue_type_match"]) / total,
        "severity_accuracy": sum(1 for result in results if result["severity_match"]) / total,
        "evidence_recall": sum(result["evidence_recall"] for result in results) / total,
        "runbook_retrieval_recall": sum(result["runbook_retrieval_recall"] for result in results) / total,
        "average_latency_ms": sum(result["latency_ms"] for result in results) / total,
    }


def _keyword_recall(expected_keywords: list[str], messages: list[str]) -> float:
    if not expected_keywords:
        return 1.0
    joined_messages = "\n".join(messages).lower()
    matches = sum(1 for keyword in expected_keywords if keyword.lower() in joined_messages)
    return matches / len(expected_keywords)


def _source_recall(expected_sources: list[str], actual_sources: list[str]) -> float:
    if not expected_sources:
        return 1.0 if not actual_sources else 0.0
    actual_source_set = set(actual_sources)
    matches = sum(1 for source in expected_sources if source in actual_source_set)
    return matches / len(expected_sources)


def main() -> None:
    report = run_eval()
    print(f"Evaluated {report['total_cases']} cases")
    for name, value in report["metrics"].items():
        if name == "average_latency_ms":
            print(f"{name}: {value:.2f}")
        else:
            print(f"{name}: {value:.2%}")
    print(f"Wrote report to {DEFAULT_REPORT_PATH}")


if __name__ == "__main__":
    main()
