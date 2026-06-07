import argparse
import json
import os
import sys
import time
from contextlib import contextmanager
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
    expected_similar_issue_types: list[str]


def load_eval_cases(path: Path = DEFAULT_CASES_PATH) -> list[EvalCase]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [EvalCase(**item) for item in data]


def run_eval(
    cases_path: Path = DEFAULT_CASES_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    retrieval_mode: str | None = None,
) -> dict:
    with _retrieval_mode(retrieval_mode):
        active_retrieval_mode = os.getenv("RETRIEVAL_MODE", "tfidf")
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
            "retrieval_mode": active_retrieval_mode,
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
        f"Retrieval mode: {report.get('retrieval_mode', 'tfidf')}",
        "",
        f"Total cases: {report['total_cases']}",
        "",
        "## Metrics",
        "",
    ]
    for name, value in report["metrics"].items():
        if name == "average_latency_ms":
            lines.append(f"- {name}: {value:.2f}")
        elif name == "failed_case_count":
            lines.append(f"- {name}: {value}")
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
                f"- expected_similar_issue_types: {', '.join(result['expected_similar_issue_types']) or '(none)'}",
                f"- actual_similar_issue_types: {', '.join(result['actual_similar_issue_types']) or '(none)'}",
                f"- evidence_recall: {result['evidence_recall']:.2%}",
                f"- runbook_retrieval_recall: {result['runbook_retrieval_recall']:.2%}",
                f"- runbook_top1_correct: {result['runbook_top1_correct']}",
                f"- runbook_precision_at_3: {result['runbook_precision_at_3']:.2%}",
                f"- similar_incident_retrieval_recall: {result['similar_incident_retrieval_recall']:.2%}",
                f"- similar_incident_top1_correct: {result['similar_incident_top1_correct']}",
                f"- similar_incident_precision_at_3: {result['similar_incident_precision_at_3']:.2%}",
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

    lines.extend(["", "## Error Analysis", ""])
    if report["failed_cases"]:
        for result in report["failed_cases"]:
            lines.extend(
                [
                    f"### {result['case_id']}",
                    "",
                    f"- failure_category: {', '.join(result['failure_categories'])}",
                    f"- expected: issue_type={result['expected_issue_type']}, severity={result['expected_severity']}, "
                    f"runbooks={result['expected_runbook_sources']}, similar_types={result['expected_similar_issue_types']}",
                    f"- actual: issue_type={result['actual_issue_type']}, severity={result['actual_severity']}, "
                    f"runbooks={result['actual_runbook_sources']}, similar_types={result['actual_similar_issue_types']}",
                    f"- possible_failure_reason: {result['possible_failure_reason']}",
                    "",
                ]
            )
    else:
        lines.append("- No failed cases.")

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


@contextmanager
def _retrieval_mode(mode: str | None):
    previous = os.environ.get("RETRIEVAL_MODE")
    if mode is not None:
        os.environ["RETRIEVAL_MODE"] = mode
    try:
        yield
    finally:
        if mode is None:
            return
        if previous is None:
            os.environ.pop("RETRIEVAL_MODE", None)
        else:
            os.environ["RETRIEVAL_MODE"] = previous


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
    actual_similar_issue_types = [incident["issue_type"] for incident in analysis.similar_incidents]
    evidence_recall = _keyword_recall(case.expected_evidence_keywords, actual_evidence_messages)
    runbook_recall = _source_recall(case.expected_runbook_sources, actual_runbook_sources)
    similar_incident_recall = _source_recall(case.expected_similar_issue_types, actual_similar_issue_types)
    runbook_top1_correct = _top1_correct(case.expected_runbook_sources, actual_runbook_sources)
    runbook_precision_at_3 = _precision_at_k(case.expected_runbook_sources, actual_runbook_sources, 3)
    similar_incident_top1_correct = _top1_correct(
        case.expected_similar_issue_types, actual_similar_issue_types
    )
    similar_incident_precision_at_3 = _precision_at_k(
        case.expected_similar_issue_types, actual_similar_issue_types, 3
    )
    issue_type_match = analysis.issue_type == case.expected_issue_type
    severity_match = analysis.severity == case.expected_severity
    passed = (
        issue_type_match
        and severity_match
        and evidence_recall == 1.0
        and runbook_recall == 1.0
        and similar_incident_recall == 1.0
    )
    failure_categories = _failure_categories(
        issue_type_match=issue_type_match,
        severity_match=severity_match,
        evidence_recall=evidence_recall,
        runbook_recall=runbook_recall,
        similar_incident_recall=similar_incident_recall,
    )

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
        "expected_similar_issue_types": case.expected_similar_issue_types,
        "actual_similar_issue_types": actual_similar_issue_types,
        "issue_type_match": issue_type_match,
        "severity_match": severity_match,
        "evidence_recall": evidence_recall,
        "runbook_retrieval_recall": runbook_recall,
        "runbook_top1_correct": runbook_top1_correct,
        "runbook_precision_at_3": runbook_precision_at_3,
        "similar_incident_retrieval_recall": similar_incident_recall,
        "similar_incident_top1_correct": similar_incident_top1_correct,
        "similar_incident_precision_at_3": similar_incident_precision_at_3,
        "latency_ms": latency_ms,
        "passed": passed,
        "failure_categories": failure_categories,
        "possible_failure_reason": _possible_failure_reason(failure_categories),
    }


def _aggregate_metrics(results: list[dict]) -> dict:
    total = len(results) or 1
    return {
        "issue_type_accuracy": sum(1 for result in results if result["issue_type_match"]) / total,
        "severity_accuracy": sum(1 for result in results if result["severity_match"]) / total,
        "evidence_recall": sum(result["evidence_recall"] for result in results) / total,
        "runbook_retrieval_recall": sum(result["runbook_retrieval_recall"] for result in results) / total,
        "runbook_top1_accuracy": sum(1 for result in results if result["runbook_top1_correct"])
        / total,
        "runbook_precision_at_3": sum(result["runbook_precision_at_3"] for result in results)
        / total,
        "similar_incident_retrieval_recall": sum(
            result["similar_incident_retrieval_recall"] for result in results
        )
        / total,
        "similar_incident_top1_accuracy": sum(
            1 for result in results if result["similar_incident_top1_correct"]
        )
        / total,
        "similar_incident_precision_at_3": sum(
            result["similar_incident_precision_at_3"] for result in results
        )
        / total,
        "failed_case_count": sum(1 for result in results if not result["passed"]),
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


def _top1_correct(expected: list[str], actual: list[str]) -> bool:
    if not expected:
        return not actual
    return bool(actual) and actual[0] in set(expected)


def _precision_at_k(expected: list[str], actual: list[str], k: int) -> float:
    if not expected:
        return 1.0 if not actual else 0.0
    relevant = set(expected)
    return sum(1 for item in actual[:k] if item in relevant) / k


def _failure_categories(
    issue_type_match: bool,
    severity_match: bool,
    evidence_recall: float,
    runbook_recall: float,
    similar_incident_recall: float,
) -> list[str]:
    categories: list[str] = []
    if not issue_type_match or not severity_match:
        categories.append("rule_detection")
    if evidence_recall < 1.0:
        categories.append("evidence_selection")
    if runbook_recall < 1.0:
        categories.append("runbook_retrieval")
    if similar_incident_recall < 1.0:
        categories.append("similar_incident_retrieval")
    return categories


def _possible_failure_reason(categories: list[str]) -> str:
    reasons = {
        "rule_detection": "Keyword priority or ambiguous mixed signals produced a different classification.",
        "evidence_selection": "Expected evidence keywords were not present in the selected evidence logs.",
        "runbook_retrieval": "The expected runbook source was missing from the retrieved top results.",
        "similar_incident_retrieval": "The expected historical issue type was missing from the retrieved top results.",
    }
    return " ".join(reasons[category] for category in categories) or "No scored failure detected."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--retrieval-mode",
        choices=["tfidf", "sentence-transformers", "hybrid"],
        default=None,
    )
    parser.add_argument("--compare-retrieval-modes", action="store_true")
    args = parser.parse_args()

    if args.compare_retrieval_modes:
        reports = {
            mode: run_eval(report_path=EVAL_DIR / f"eval_report_{mode}.md", retrieval_mode=mode)
            for mode in ["tfidf", "sentence-transformers", "hybrid"]
        }
        _print_comparison(reports)
        return

    report = run_eval(retrieval_mode=args.retrieval_mode)
    print(f"Evaluated {report['total_cases']} cases")
    print(f"retrieval_mode: {report['retrieval_mode']}")
    for name, value in report["metrics"].items():
        if name == "average_latency_ms":
            print(f"{name}: {value:.2f}")
        elif name == "failed_case_count":
            print(f"{name}: {value}")
        else:
            print(f"{name}: {value:.2%}")
    print(f"Wrote report to {DEFAULT_REPORT_PATH}")


def _print_comparison(reports: dict[str, dict]) -> None:
    metric_names = [
        "runbook_top1_accuracy",
        "runbook_precision_at_3",
        "similar_incident_top1_accuracy",
        "similar_incident_precision_at_3",
        "average_latency_ms",
    ]
    print("Retrieval mode comparison")
    for mode, report in reports.items():
        print(f"\n{mode}")
        for name in metric_names:
            value = report["metrics"][name]
            if name == "average_latency_ms":
                print(f"{name}: {value:.2f}")
            else:
                print(f"{name}: {value:.2%}")


if __name__ == "__main__":
    main()
