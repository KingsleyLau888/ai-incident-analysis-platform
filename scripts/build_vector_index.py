"""Build the local ChromaDB vector index for RAG retrieval.

This script precomputes embeddings for runbook chunks and historical incidents.
It does not call any LLM API.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.embedding_service import get_sentence_transformer_embedder
from app.services.vector_store import VectorStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild ChromaDB collections even if they already contain data.",
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=None,
        help="Optional ChromaDB persistence directory. Defaults to CHROMA_PERSIST_DIR or runtime/vector_store/chroma.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="F08：只检查索引新鲜度（对比语料签名），不重建；有陈旧时以退出码 1 结束。",
    )
    args = parser.parse_args()

    embedder = get_sentence_transformer_embedder()
    if embedder is None:
        raise SystemExit(
            "sentence-transformers model is unavailable. "
            "Install dependencies or make sure the model exists in the local HuggingFace cache."
        )

    store = (
        VectorStore(embed_fn=embedder.encode, persist_dir=args.persist_dir)
        if args.persist_dir is not None
        else VectorStore(embed_fn=embedder.encode)
    )

    if args.check:
        stale = False
        for name, part in store.freshness_status().items():
            reason = f" ({part['reason']})" if part.get("reason") else ""
            print(f"{name}: {part['status']}{reason}")
            stale = stale or part["status"] == "stale"
        raise SystemExit(1 if stale else 0)

    store.ensure_initialized(force=args.force)

    print(f"ChromaDB persist_dir: {store.persist_dir}")
    print(f"Runbook chunks indexed: {store.runbook_count()}")
    print(f"Historical incidents indexed: {store.incident_count()}")


if __name__ == "__main__":
    main()
