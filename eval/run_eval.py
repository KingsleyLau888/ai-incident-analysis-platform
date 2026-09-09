import argparse
import json
import os
import re
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
from app.services.llm_judge import JudgeVerdict, get_judge


EVAL_DIR = PROJECT_ROOT / "eval"
REPORTS_DIR = EVAL_DIR / "reports"
DEFAULT_CASES_PATH = EVAL_DIR / "eval_cases.json"
DEFAULT_REPORT_PATH = REPORTS_DIR / "eval_report.md"
DEFAULT_BENCHMARK_REPORT_PATH = REPORTS_DIR / "retrieval_benchmark_report.md"


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
    enable_judge: bool = False,
) -> dict:
    with _retrieval_mode(retrieval_mode):
        active_retrieval_mode = os.getenv("RETRIEVAL_MODE", "tfidf")
        cases = load_eval_cases(cases_path)
        judge = get_judge() if enable_judge else None
        case_results = []

        with _evaluation_session() as db:
            for case in cases:
                started = time.perf_counter()
                analysis = _run_case(db, case)
                latency_ms = (time.perf_counter() - started) * 1000
                judge_outcome = {"status": "skipped", "verdict": None, "error": None}
                if judge is not None:
                    judge_outcome = _run_judge(case, analysis, judge)
                case_results.append(_score_case(case, analysis, latency_ms, judge_outcome))

        metrics = _aggregate_metrics(case_results)
        report = {
            "retrieval_mode": active_retrieval_mode,
            "effective_retrieval_modes": _effective_retrieval_modes(case_results),
            "judge_enabled": enable_judge,
            "total_cases": len(cases),
            "metrics": metrics,
            "cases": case_results,
            "failed_cases": [result for result in case_results if not result["passed"]],
        }
        write_report(report, report_path)
        return report


def _run_judge(case: EvalCase, analysis, judge) -> dict:
    """Run LLM-as-Judge evaluation on the analysis result.

    Returns {"status": "succeeded", "verdict": JudgeVerdict, "error": None} on
    success, or {"status": "failed", "verdict": None, "error": <desensitized>}
    on failure. Failures must never be silently swallowed (F07).
    """
    try:
        evidence_messages = [evidence.log_entry.message for evidence in analysis.evidence_logs]
        verdict = judge.evaluate(
            incident_title=case.incident_title,
            service_name=case.service_name,
            issue_type=analysis.issue_type,
            severity=analysis.severity,
            evidence_messages=evidence_messages,
            diagnosis_summary=analysis.diagnosis_summary,
            # root_cause_hypotheses 是 JSON 列的 list[dict]，直接传给 judge
            root_cause_hypotheses=list(analysis.root_cause_hypotheses),
            suggested_actions=analysis.structured_suggested_actions or [analysis.suggested_actions],
            impact_scope=analysis.impact_scope,
        )
        return {"status": "succeeded", "verdict": verdict, "error": None}
    except Exception as exc:
        return {"status": "failed", "verdict": None, "error": _desensitize_error(exc)}


def _desensitize_error(exc: Exception, max_length: int = 200) -> str:
    """Turn an exception into a report-safe string: no URLs, no long tokens."""
    text = f"{type(exc).__name__}: {exc}"
    text = re.sub(r"https?://\S+", "<url>", text)
    text = re.sub(r"[A-Za-z0-9_\-]{20,}", "<redacted>", text)
    return text[:max_length]


def write_report(report: dict, path: Path = DEFAULT_REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Eval Report",
        "",
        f"Retrieval mode: {report.get('retrieval_mode', 'tfidf')}",
        f"Effective retrieval modes: {', '.join(report.get('effective_retrieval_modes', [])) or 'unknown'}",
        f"LLM Judge: {'enabled' if report.get('judge_enabled') else 'disabled'}",
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
                f"- runbook_effective_retrieval_mode: {result['runbook_effective_retrieval_mode']}",
                f"- similar_effective_retrieval_mode: {result['similar_effective_retrieval_mode']}",
                f"- evidence_recall: {result['evidence_recall']:.2%}",
                f"- runbook_retrieval_recall: {result['runbook_retrieval_recall']:.2%}",
                f"- runbook_top1_correct: {result['runbook_top1_correct']}",
                f"- runbook_precision_at_3: {result['runbook_precision_at_3']:.2%}",
                f"- similar_incident_retrieval_recall: {result['similar_incident_retrieval_recall']:.2%}",
                f"- similar_incident_top1_correct: {result['similar_incident_top1_correct']}",
                f"- similar_incident_precision_at_3: {result['similar_incident_precision_at_3']:.2%}",
                f"- latency_ms: {result['latency_ms']:.2f}",
            ]
        )
        # LLM Judge results — explicit status so failures are never silent
        if report.get("judge_enabled"):
            lines.append(f"- judge_status: {result.get('judge_status', 'unknown')}")
            if result.get("judge_error"):
                lines.append(f"- judge_error: {result['judge_error']}")
            if result.get("judge_verdict"):
                v = result["judge_verdict"]
                lines.extend([
                    f"- judge_provider: {v.get('provider', 'n/a')}",
                    f"- diagnosis_coherence: {v.get('diagnosis_coherence', 0):.2f}",
                    f"- evidence_grounding: {v.get('evidence_grounding', 0):.2f}",
                    f"- hallucination_flag: {v.get('hallucination_flag', False)}",
                    f"- actionability: {v.get('actionability', 0):.2f}",
                    f"- judge_critique: {v.get('critique', '')}",
                ])
        lines.extend([
            f"- passed: {result['passed']}",
            f"- failure_categories: {', '.join(result['failure_categories']) or 'none'}",
            "",
        ])

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

    # Add LLM Judge summary section — always present when enabled, even if
    # every evaluation failed, so "enabled but never reviewed" stays visible.
    if report.get("judge_enabled"):
        metrics = report.get("metrics", {})
        lines.extend([
            "",
            "## LLM Judge Summary",
            "",
            f"- requested: {metrics.get('judge_requested', 0)}",
            f"- attempted: {metrics.get('judge_attempted', 0)}",
            f"- succeeded: {metrics.get('judge_succeeded', 0)}",
            f"- failed: {metrics.get('judge_failed', 0)}",
            f"- skipped: {metrics.get('judge_skipped', 0)}",
            f"- provider: mock {metrics.get('judge_provider_mock', 0)} / llm {metrics.get('judge_provider_llm', 0)}",
            "",
        ])
        if metrics.get("judge_succeeded"):
            lines.extend([
                f"- avg diagnosis_coherence: {metrics.get('judge_diagnosis_coherence', 0):.2%}",
                f"- avg evidence_grounding: {metrics.get('judge_evidence_grounding', 0):.2%}",
                f"- hallucination_rate: {metrics.get('judge_hallucination_rate', 0):.2%}",
                f"- avg actionability: {metrics.get('judge_actionability', 0):.2%}",
                "",
            ])
        else:
            lines.extend([
                "- judge averages: n/a (no successful evaluations)",
                "",
            ])

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
    # Use case_id suffix to avoid UNIQUE constraint conflicts when
    # multiple eval cases share the same conceptual service name
    safe_case_id = "".join(
        char if char.isalnum() else "-"
        for char in case.case_id
    )
    unique_name = f"{case.service_name}-{safe_case_id}"[:120]
    service = service_service.create_service(db, ServiceCreate(name=unique_name))
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


def _score_case(
    case: EvalCase,
    analysis,
    latency_ms: float,
    judge_outcome: dict | None = None,
) -> dict:
    actual_evidence_messages = [evidence.log_entry.message for evidence in analysis.evidence_logs]
    actual_runbook_sources = [chunk["source"] for chunk in analysis.retrieved_runbook_chunks]
    actual_similar_issue_types = [incident["issue_type"] for incident in analysis.similar_incidents]
    runbook_effective_mode = _trace_effective_mode(analysis, "vector_runbook_retrieval")
    similar_effective_mode = _trace_effective_mode(analysis, "similar_incident_retrieval")
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

    result: dict = {
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
        "runbook_effective_retrieval_mode": runbook_effective_mode,
        "similar_effective_retrieval_mode": similar_effective_mode,
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

    judge_outcome = judge_outcome or {"status": "skipped", "verdict": None, "error": None}
    result["judge_status"] = judge_outcome["status"]
    if judge_outcome.get("error"):
        result["judge_error"] = judge_outcome["error"]
    if judge_outcome.get("verdict") is not None:
        judge_verdict = judge_outcome["verdict"]
        result["judge_verdict"] = {
            "provider": judge_verdict.provider,
            "diagnosis_coherence": judge_verdict.diagnosis_coherence,
            "evidence_grounding": judge_verdict.evidence_grounding,
            "hallucination_flag": judge_verdict.hallucination_flag,
            "actionability": judge_verdict.actionability,
            "critique": judge_verdict.critique,
        }

    return result


def _trace_effective_mode(analysis, step_name: str) -> str:
    traces = getattr(analysis, "traces", []) or []
    for trace in traces:
        if trace.step_name != step_name:
            continue
        detail = trace.detail or ""
        match = re.search(r"effective_retrieval_mode=([^;\s.]+)", detail)
        if match:
            return match.group(1)
        match = re.search(r"retrieval_mode=([^;\s.]+)", detail)
        if match:
            return match.group(1)
    return "unknown"


def _effective_retrieval_modes(results: list[dict]) -> list[str]:
    modes = {
        result.get("runbook_effective_retrieval_mode", "unknown")
        for result in results
    } | {
        result.get("similar_effective_retrieval_mode", "unknown")
        for result in results
    }
    return sorted(mode for mode in modes if mode)


def _aggregate_metrics(results: list[dict]) -> dict:
    total = len(results) or 1
    metrics = {
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

    # LLM Judge aggregate metrics — only present when the judge was actually
    # attempted for at least one case (disabled runs keep the baseline key set).
    attempted = [r for r in results if r.get("judge_status") in ("succeeded", "failed")]
    if attempted:
        metrics["judge_requested"] = len(results)
        metrics["judge_attempted"] = len(attempted)
        metrics["judge_succeeded"] = sum(1 for r in attempted if r["judge_status"] == "succeeded")
        metrics["judge_failed"] = sum(1 for r in attempted if r["judge_status"] == "failed")
        metrics["judge_skipped"] = len(results) - len(attempted)
        metrics["judge_provider_mock"] = sum(
            1 for r in attempted if r.get("judge_verdict", {}).get("provider") == "mock"
        )
        metrics["judge_provider_llm"] = sum(
            1 for r in attempted if r.get("judge_verdict", {}).get("provider") == "llm"
        )

    judge_results = [r for r in results if r.get("judge_verdict")]
    if judge_results:
        metrics["judge_diagnosis_coherence"] = (
            sum(r["judge_verdict"]["diagnosis_coherence"] for r in judge_results) / len(judge_results)
        )
        metrics["judge_evidence_grounding"] = (
            sum(r["judge_verdict"]["evidence_grounding"] for r in judge_results) / len(judge_results)
        )
        metrics["judge_hallucination_rate"] = (
            sum(1 for r in judge_results if r["judge_verdict"]["hallucination_flag"]) / len(judge_results)
        )
        metrics["judge_actionability"] = (
            sum(r["judge_verdict"]["actionability"] for r in judge_results) / len(judge_results)
        )

    return metrics


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
        choices=["tfidf", "sentence-transformers", "hybrid", "chromadb"],
        default=None,
    )
    parser.add_argument("--compare-retrieval-modes", action="store_true")
    parser.add_argument("--judge", action="store_true", help="Enable LLM-as-Judge evaluation")
    args = parser.parse_args()

    if args.compare_retrieval_modes:
        modes = ["tfidf", "sentence-transformers", "hybrid"]
        try:
            import chromadb  # noqa: F401
            modes.append("chromadb")
        except ImportError:
            pass
        reports = {
            mode: run_eval(
                report_path=REPORTS_DIR / f"eval_report_{mode}.md",
                retrieval_mode=mode,
                enable_judge=args.judge,
            )
            for mode in modes
        }
        write_benchmark_report(reports, DEFAULT_BENCHMARK_REPORT_PATH)
        _print_comparison(reports)
        print(f"\nWrote benchmark report to {DEFAULT_BENCHMARK_REPORT_PATH}")
        return

    report = run_eval(
        retrieval_mode=args.retrieval_mode,
        enable_judge=args.judge,
    )
    print(f"Evaluated {report['total_cases']} cases")
    print(f"retrieval_mode: {report['retrieval_mode']}")
    if report.get("judge_enabled"):
        metrics = report["metrics"]
        print(
            "judge: enabled "
            f"(succeeded {metrics.get('judge_succeeded', 0)}, failed {metrics.get('judge_failed', 0)})"
        )
    else:
        print("judge: disabled")
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


def write_benchmark_report(
    reports: dict[str, dict],
    path: Path = DEFAULT_BENCHMARK_REPORT_PATH,
) -> None:
    metric_names = [
        "issue_type_accuracy",
        "runbook_top1_accuracy",
        "runbook_precision_at_3",
        "similar_incident_top1_accuracy",
        "similar_incident_precision_at_3",
        "average_latency_ms",
        "failed_case_count",
    ]
    lines = [
        "# Retrieval Benchmark Report",
        "",
        "This report compares retrieval strategies on the same incident eval cases.",
        "It is intended to show quality/latency tradeoffs rather than claim production-grade benchmark coverage.",
        "",
        "## Compared Modes",
        "",
    ]
    for mode in reports:
        lines.append(f"- {mode}")

    lines.extend(["", "## Metrics Table", ""])
    header = "| mode | effective_retrieval_modes | " + " | ".join(metric_names) + " |"
    separator = "|---" * (len(metric_names) + 2) + "|"
    lines.extend([header, separator])
    for mode, report in reports.items():
        values = []
        effective_modes = ", ".join(report.get("effective_retrieval_modes", [])) or "unknown"
        for metric in metric_names:
            value = report["metrics"][metric]
            if metric in {"average_latency_ms", "failed_case_count"}:
                values.append(f"{value:.2f}" if metric == "average_latency_ms" else str(value))
            else:
                values.append(f"{value:.2%}")
        lines.append(f"| {mode} | {effective_modes} | " + " | ".join(values) + " |")

    lines.extend(["", "## Interpretation", ""])
    best_runbook = _best_mode(reports, "runbook_top1_accuracy", higher_is_better=True)
    best_similar = _best_mode(reports, "similar_incident_top1_accuracy", higher_is_better=True)
    fastest = _best_mode(reports, "average_latency_ms", higher_is_better=False)
    lines.extend(
        [
            f"- Best runbook top-1 accuracy: {best_runbook}",
            f"- Best similar incident top-1 accuracy: {best_similar}",
            f"- Lowest average latency: {fastest}",
            "",
            "TF-IDF tends to be fast and strong on exact error names.",
            "Dense retrieval can help when the incident title is natural language or does not share exact keywords with the runbook.",
            "Hybrid retrieval combines sparse and dense ranking with RRF, which is often the most robust option when both exact error terms and semantic hints matter.",
        ]
    )

    lines.extend(["", "## Failed Case Overlap", ""])
    for mode, report in reports.items():
        failed_ids = [case["case_id"] for case in report["failed_cases"]]
        lines.append(f"- {mode}: {', '.join(failed_ids) if failed_ids else 'none'}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _best_mode(
    reports: dict[str, dict],
    metric: str,
    *,
    higher_is_better: bool,
) -> str:
    best = sorted(
        reports.items(),
        key=lambda item: item[1]["metrics"][metric],
        reverse=higher_is_better,
    )[0]
    value = best[1]["metrics"][metric]
    if metric == "average_latency_ms":
        return f"{best[0]} ({value:.2f} ms)"
    return f"{best[0]} ({value:.2%})"


if __name__ == "__main__":
    main()
