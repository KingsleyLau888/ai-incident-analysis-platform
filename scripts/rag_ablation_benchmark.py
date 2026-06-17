"""Run RAG retrieval ablation experiments.

This script answers: which retrieval technique actually improves runbook
retrieval quality or latency?
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from eval.run_eval import DEFAULT_CASES_PATH, load_eval_cases
from app.services.query_rewriter import rewrite_query
from app.services.rrf import reciprocal_rank_fusion
from app.services.runbook_retriever import RunbookRetriever, build_runbook_query


REPORT_PATH = PROJECT_ROOT / "eval" / "rag_ablation_report.md"


class _Log:
    def __init__(self, message: str) -> None:
        self.message = message


@dataclass(frozen=True)
class AblationConfig:
    name: str
    retrieval_mode: str
    multi_query: bool = False
    metadata_filter: bool = False


CONFIGS = [
    AblationConfig("tfidf_single_query", "tfidf"),
    AblationConfig("dense_single_query", "sentence-transformers"),
    AblationConfig("chromadb_single_query", "chromadb"),
    AblationConfig("chromadb_multi_query", "chromadb", multi_query=True),
    AblationConfig(
        "chromadb_multi_query_metadata",
        "chromadb",
        multi_query=True,
        metadata_filter=True,
    ),
]


def main() -> None:
    cases = [
        case for case in load_eval_cases(DEFAULT_CASES_PATH)
        if case.expected_issue_type != "unknown"
    ]
    reports = {
        config.name: _run_config(config, cases)
        for config in CONFIGS
    }
    write_report(reports, REPORT_PATH)
    _print_summary(reports)
    print(f"\nWrote report to {REPORT_PATH}")


def _run_config(config: AblationConfig, cases) -> dict:
    with _retrieval_env(config):
        retriever = RunbookRetriever()
        results = []
        for case in cases:
            started = time.perf_counter()
            actual_sources = _retrieve_sources(retriever, case, config)
            latency_ms = (time.perf_counter() - started) * 1000
            results.append(
                {
                    "case_id": case.case_id,
                    "expected_sources": case.expected_runbook_sources,
                    "actual_sources": actual_sources,
                    "top1_correct": _top1_correct(case.expected_runbook_sources, actual_sources),
                    "precision_at_3": _precision_at_k(case.expected_runbook_sources, actual_sources, 3),
                    "latency_ms": latency_ms,
                }
            )

    total = len(results) or 1
    return {
        "retrieval_mode": config.retrieval_mode,
        "effective_retrieval_mode": retriever.effective_retrieval_mode,
        "multi_query": config.multi_query,
        "metadata_filter": config.metadata_filter,
        "runbook_top1_accuracy": sum(1 for result in results if result["top1_correct"]) / total,
        "runbook_precision_at_3": sum(result["precision_at_3"] for result in results) / total,
        "average_latency_ms": sum(result["latency_ms"] for result in results) / total,
        "cases": results,
    }


def _retrieve_sources(retriever: RunbookRetriever, case, config: AblationConfig) -> list[str]:
    logs = [_Log(message) for message in case.logs]
    base_query = build_runbook_query(
        incident_title=case.incident_title,
        service_name=case.service_name,
        evidence_logs=logs,
        issue_type=case.expected_issue_type,
    )
    documents = [
        f"{chunk.source}\n{chunk.title}\n{chunk.content}"
        for chunk in retriever.chunks
    ]

    if config.multi_query:
        rewritten = rewrite_query(
            incident_title=case.incident_title,
            service_name=case.service_name,
            issue_type=case.expected_issue_type,
            evidence_text=" ".join(case.logs),
        )
        ranked_lists = [
            retriever._rank(
                variant,
                documents,
                top_k=5,
                issue_type=case.expected_issue_type,
            )
            for variant in rewritten.variants
        ]
        fused = reciprocal_rank_fusion(ranked_lists, key=lambda item: item[0])
        ranked = [(result.item[0], result.score) for result in fused[:3]]
    else:
        ranked = retriever._rank(
            base_query,
            documents,
            top_k=3,
            issue_type=case.expected_issue_type,
        )

    return [retriever.chunks[index].source for index, _ in ranked[:3]]


@contextmanager
def _retrieval_env(config: AblationConfig):
    previous = {
        "RETRIEVAL_MODE": os.environ.get("RETRIEVAL_MODE"),
        "RUNBOOK_METADATA_FILTER": os.environ.get("RUNBOOK_METADATA_FILTER"),
    }
    os.environ["RETRIEVAL_MODE"] = config.retrieval_mode
    os.environ["RUNBOOK_METADATA_FILTER"] = "1" if config.metadata_filter else "0"
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def write_report(reports: dict[str, dict], path: Path = REPORT_PATH) -> None:
    lines = [
        "# RAG Ablation Report",
        "",
        "This report isolates runbook retrieval quality and latency.",
        "It is meant to show which RAG techniques actually improve the system.",
        "",
        "| config | effective_mode | multi_query | metadata_filter | top1 | precision@3 | avg_latency_ms |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, report in reports.items():
        lines.append(
            f"| {name} | {report['effective_retrieval_mode']} | "
            f"{report['multi_query']} | {report['metadata_filter']} | "
            f"{report['runbook_top1_accuracy']:.2%} | "
            f"{report['runbook_precision_at_3']:.2%} | "
            f"{report['average_latency_ms']:.2f} |"
        )

    lines.extend(["", "## Takeaways", ""])
    baseline = reports["tfidf_single_query"]
    for name, report in reports.items():
        if name == "tfidf_single_query":
            continue
        top1_delta = report["runbook_top1_accuracy"] - baseline["runbook_top1_accuracy"]
        latency_delta = report["average_latency_ms"] - baseline["average_latency_ms"]
        lines.append(
            f"- {name}: top1 delta {top1_delta:+.2%}, "
            f"latency delta {latency_delta:+.2f} ms vs TF-IDF baseline."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_summary(reports: dict[str, dict]) -> None:
    print("RAG ablation benchmark")
    for name, report in reports.items():
        print(
            f"{name}: top1={report['runbook_top1_accuracy']:.2%}, "
            f"p@3={report['runbook_precision_at_3']:.2%}, "
            f"latency={report['average_latency_ms']:.2f}ms, "
            f"effective={report['effective_retrieval_mode']}"
        )


def _top1_correct(expected: list[str], actual: list[str]) -> bool:
    if not expected:
        return not actual
    return bool(actual) and actual[0] in set(expected)


def _precision_at_k(expected: list[str], actual: list[str], k: int) -> float:
    if not expected:
        return 1.0 if not actual else 0.0
    relevant = set(expected)
    return sum(1 for item in actual[:k] if item in relevant) / k


if __name__ == "__main__":
    main()
