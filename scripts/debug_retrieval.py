"""Print retrieval results across modes for one incident-style query."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.runbook_retriever import RunbookRetriever
from app.services.similar_incident_retriever import SimilarIncidentRetriever


class _Log:
    def __init__(self, message: str) -> None:
        self.message = message


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--query",
        default="Payment API returns 500 errors DBConnectionTimeout mysql-primary",
    )
    parser.add_argument("--service-name", default="payment-service")
    parser.add_argument("--issue-type", default="database_issue")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    evidence_logs = [_Log(args.query)]
    for mode in ["tfidf", "sentence-transformers", "hybrid", "chromadb"]:
        os.environ["RETRIEVAL_MODE"] = mode
        runbook_retriever = RunbookRetriever()
        similar_retriever = SimilarIncidentRetriever(
            embedder=runbook_retriever.embedder,
            dense_embedder=runbook_retriever.dense_embedder,
            retrieval_mode=runbook_retriever.retrieval_mode,
        )

        runbooks = runbook_retriever.retrieve(
            incident_title=args.query,
            service_name=args.service_name,
            evidence_logs=evidence_logs,
            issue_type=args.issue_type,
            top_k=args.top_k,
        )
        incidents = similar_retriever.retrieve(
            incident_title=args.query,
            service_name=args.service_name,
            issue_type=args.issue_type,
            evidence_logs=evidence_logs,
            top_k=args.top_k,
        )

        print(f"\n## {mode}")
        print(f"runbook_effective={runbook_retriever.effective_retrieval_mode}")
        for chunk in runbooks:
            print(f"- runbook {chunk.source} / {chunk.title} score={chunk.score:.4f}")
        print(f"similar_effective={similar_retriever.effective_retrieval_mode}")
        for incident in incidents:
            print(
                f"- incident {incident.historical_id} "
                f"{incident.issue_type} score={incident.similarity_score:.4f}"
            )


if __name__ == "__main__":
    main()
