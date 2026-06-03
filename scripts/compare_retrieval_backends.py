import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.embedding_service import get_embedder
from app.services.runbook_chunker import load_runbook_chunks
from app.services.runbook_retriever import RunbookRetriever


@dataclass(frozen=True)
class RetrievalCase:
    name: str
    incident_title: str
    service_name: str
    issue_type: str
    evidence_logs: list[str]
    expected_source: str


class EvidenceLog:
    def __init__(self, message: str) -> None:
        self.message = message


CASES = [
    RetrievalCase(
        name="mysql connection timeout",
        incident_title="Users cannot complete payments",
        service_name="payment-service",
        issue_type="database_issue",
        evidence_logs=["ERROR DBConnectionTimeout when connecting to mysql-primary"],
        expected_source="database_issue.md",
    ),
    RetrievalCase(
        name="semantic database wording",
        incident_title="Payment checkout cannot reach primary datastore",
        service_name="payment-service",
        issue_type="database_issue",
        evidence_logs=["Checkout failed because the primary data store was unreachable"],
        expected_source="database_issue.md",
    ),
    RetrievalCase(
        name="upstream deadline",
        incident_title="Checkout requests are timing out",
        service_name="checkout-service",
        issue_type="timeout_issue",
        evidence_logs=["Request deadline exceeded while calling upstream dependency"],
        expected_source="timeout_issue.md",
    ),
    RetrievalCase(
        name="unauthorized token",
        incident_title="Users cannot sign in",
        service_name="auth-service",
        issue_type="auth_issue",
        evidence_logs=["401 unauthorized token rejected by auth service"],
        expected_source="auth_issue.md",
    ),
    RetrievalCase(
        name="redis connection",
        incident_title="Cart reads are failing",
        service_name="cart-service",
        issue_type="cache_issue",
        evidence_logs=["RedisConnection refused while reading cache"],
        expected_source="cache_issue.md",
    ),
    RetrievalCase(
        name="heap pressure",
        incident_title="Worker containers are restarting",
        service_name="worker-service",
        issue_type="memory_issue",
        evidence_logs=["Process killed after OutOfMemory heap pressure"],
        expected_source="memory_issue.md",
    ),
    RetrievalCase(
        name="http 500",
        incident_title="API is returning internal errors",
        service_name="api-service",
        issue_type="server_error",
        evidence_logs=["HTTP 500 internal server error in request handler"],
        expected_source="server_error.md",
    ),
]


@contextmanager
def embedding_backend(name: str):
    previous = os.environ.get("RUNBOOK_EMBEDDING_BACKEND")
    if name == "tfidf":
        os.environ.pop("RUNBOOK_EMBEDDING_BACKEND", None)
    else:
        os.environ["RUNBOOK_EMBEDDING_BACKEND"] = name
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("RUNBOOK_EMBEDDING_BACKEND", None)
        else:
            os.environ["RUNBOOK_EMBEDDING_BACKEND"] = previous


def evaluate(requested_backend: str, top_k: int = 3) -> dict:
    with embedding_backend(requested_backend):
        embedder = get_embedder()
        retriever = RunbookRetriever(chunks=load_runbook_chunks(), embedder=embedder)
        latencies: list[float] = []
        reciprocal_ranks: list[float] = []
        top1_hits = 0
        recall_hits = 0
        rows = []

        for case in CASES:
            evidence_logs = [EvidenceLog(message) for message in case.evidence_logs]
            started = time.perf_counter()
            results = retriever.retrieve(
                incident_title=case.incident_title,
                service_name=case.service_name,
                evidence_logs=evidence_logs,
                issue_type=case.issue_type,
                top_k=top_k,
            )
            latencies.append((time.perf_counter() - started) * 1000)

            sources = [result.source for result in results]
            rank = _rank_of(case.expected_source, sources)
            if rank == 1:
                top1_hits += 1
            if rank is not None and rank <= top_k:
                recall_hits += 1
            reciprocal_ranks.append(1 / rank if rank else 0)

            rows.append(
                {
                    "case": case.name,
                    "expected": case.expected_source,
                    "top_sources": sources,
                    "rank": rank,
                }
            )

        case_count = len(CASES)
        return {
            "requested_backend": requested_backend,
            "actual_backend": retriever.backend_name,
            "top_k": top_k,
            "top1_accuracy": top1_hits / case_count,
            "recall_at_k": recall_hits / case_count,
            "mrr": sum(reciprocal_ranks) / case_count,
            "avg_latency_ms": sum(latencies) / case_count,
            "rows": rows,
        }


def _rank_of(expected_source: str, sources: list[str]) -> int | None:
    for index, source in enumerate(sources, start=1):
        if source == expected_source:
            return index
    return None


def print_report(report: dict) -> None:
    print(f"\nBackend requested: {report['requested_backend']}")
    print(f"Backend actual:    {report['actual_backend']}")
    print(f"Top-1 Accuracy:   {report['top1_accuracy']:.2%}")
    print(f"Recall@{report['top_k']}:       {report['recall_at_k']:.2%}")
    print(f"MRR:              {report['mrr']:.3f}")
    print(f"Avg latency:      {report['avg_latency_ms']:.2f} ms")
    print("\nCases:")
    for row in report["rows"]:
        rank = row["rank"] if row["rank"] is not None else "miss"
        top_sources = ", ".join(row["top_sources"])
        print(f"- {row['case']}: expected={row['expected']} rank={rank} top=[{top_sources}]")


def main() -> None:
    for backend in ["tfidf", "sentence-transformers"]:
        print_report(evaluate(backend))


if __name__ == "__main__":
    main()
