"""Embedding & retrieval backends: TF-IDF, sentence-transformers, ChromaDB, and re-ranking."""

from __future__ import annotations

import math
import os
import re
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol, TypeVar

from app.services.rrf import reciprocal_rank_fusion

# ---------------------------------------------------------------------------
# Tokenisation (shared by TF-IDF)
# ---------------------------------------------------------------------------

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_.'-]+")


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


class TextEmbedder(Protocol):
    name: str

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for *texts*."""
        ...

    def rank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        """Rank *documents* against *query*, returning (index, score) pairs."""
        ...


# ===================================================================
# Sentence-Transformer (BiEncoder) embedder
# ===================================================================


@dataclass
class SentenceTransformerEmbedder:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    name: str = "sentence-transformers"

    def __post_init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("sentence-transformers is not installed") from exc
        self._model = SentenceTransformer(self.model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def rank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        if not documents:
            return []
        embeddings = self._model.encode([query, *documents], normalize_embeddings=True)
        query_vec = embeddings[0]
        doc_vecs = embeddings[1:]
        scored = [
            (idx, float(query_vec @ doc_vecs[idx]))
            for idx in range(len(doc_vecs))
        ]
        return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]


# ===================================================================
# CrossEncoder re-ranker (fine-grained relevance)
# ===================================================================


@dataclass
class CrossEncoderReranker:
    """Re-rank a candidate list with a CrossEncoder model.

    BiEncoder (fast, independent encoding) → top-K candidates
    CrossEncoder (slow, joint encoding) → final top-k.
    """

    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    name: str = "cross-encoder"

    def __post_init__(self) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError("sentence-transformers is not installed") from exc
        self._model = CrossEncoder(self.model_name)

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int,
    ) -> list[tuple[int, float]]:
        """Score (query, document) pairs and return top-k (index, score)."""
        if not documents:
            return []
        pairs = [(query, doc) for doc in documents]
        scores = self._model.predict(pairs, show_progress_bar=False)
        ranked = sorted(
            [(idx, float(score)) for idx, score in enumerate(scores)],
            key=lambda item: item[1],
            reverse=True,
        )
        return ranked[:top_k]


# ===================================================================
# TF-IDF embedder (sparse / baseline)
# ===================================================================


@dataclass
class TfidfEmbedder:
    name: str = "tfidf"

    def encode(self, texts: list[str]) -> list[list[float]]:
        """TF-IDF doesn't produce dense vectors; return empty."""
        return []

    def rank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        if not documents:
            return []

        tokenized_documents = [_tokenize(document) for document in documents]
        query_tokens = _tokenize(query)
        idf = _inverse_document_frequency(tokenized_documents)
        query_vector = _tfidf_vector(query_tokens, idf)

        scored = []
        for index, tokens in enumerate(tokenized_documents):
            score = _cosine_similarity(query_vector, _tfidf_vector(tokens, idf))
            scored.append((index, score))

        return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]


# ===================================================================
# ChromaDB-backed retriever (dense, persistent)
# ===================================================================


@dataclass
class ChromaDBRetriever:
    """Thin wrapper so ChromaDB quacks like a TextEmbedder for the retrievers."""

    name: str = "chromadb"

    _store: object = None  # VectorStore, set after init

    def encode(self, texts: list[str]) -> list[list[float]]:
        return []

    def rank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        """Not used directly — retrievers call the VectorStore instead."""
        return []


# ===================================================================
# Retrieval-mode plumbing
# ===================================================================

VALID_RETRIEVAL_MODES = {"tfidf", "sentence-transformers", "hybrid", "chromadb"}


def get_retrieval_mode() -> str:
    requested_mode = os.getenv("RETRIEVAL_MODE")
    if requested_mode in VALID_RETRIEVAL_MODES:
        return requested_mode

    legacy_backend = os.getenv("RUNBOOK_EMBEDDING_BACKEND")
    if legacy_backend == "sentence-transformers":
        return "sentence-transformers"
    return "tfidf"


def get_embedder(mode: str | None = None) -> TextEmbedder:
    requested_mode = mode or get_retrieval_mode()
    if requested_mode == "sentence-transformers":
        dense_embedder = get_sentence_transformer_embedder()
        return dense_embedder if dense_embedder is not None else TfidfEmbedder()
    if requested_mode == "chromadb":
        return ChromaDBRetriever()
    return TfidfEmbedder()


# ---------------------------------------------------------------------------
# Re-ranking toggle
# ---------------------------------------------------------------------------

CROSS_ENCODER_ENABLED = (
    os.getenv("CROSS_ENCODER_ENABLED", "0").strip().lower() in {"1", "true", "yes"}
)


@lru_cache(maxsize=1)
def get_cross_encoder() -> CrossEncoderReranker | None:
    if not CROSS_ENCODER_ENABLED:
        return None
    try:
        return CrossEncoderReranker()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Two-stage retrieval helper (used by retrievers)
# ---------------------------------------------------------------------------

T = TypeVar("T")


def two_stage_retrieve(
    *,
    query: str,
    documents: list[str],
    coarse_top_k: int = 10,
    fine_top_k: int = 3,
    coarse_ranker: TextEmbedder,
) -> list[tuple[int, float]]:
    """Coarse rank → optional CrossEncoder fine rank."""
    started = time.perf_counter()
    coarse = coarse_ranker.rank(query, documents, top_k=coarse_top_k)
    coarse_ms = (time.perf_counter() - started) * 1000

    reranker = get_cross_encoder()
    if reranker is None:
        return coarse[:fine_top_k]

    if len(coarse) <= fine_top_k:
        return coarse

    started = time.perf_counter()
    coarse_docs = [documents[idx] for idx, _ in coarse]
    fine = reranker.rerank(query, coarse_docs, top_k=fine_top_k)
    rerank_ms = (time.perf_counter() - started) * 1000

    # Map back to original indices
    result = [(coarse[idx][0], score) for idx, score in fine]

    # Store timing metadata for observability (picked up by retrievers)
    _last_retrieval_timing["coarse_ms"] = coarse_ms
    _last_retrieval_timing["rerank_ms"] = rerank_ms
    _last_retrieval_timing["coarse_candidates"] = len(coarse)
    _last_retrieval_timing["reranker"] = reranker.name if reranker else "none"

    return result


# Module-level timing store (reset per retrieval)
_last_retrieval_timing: dict = {}


def get_last_retrieval_timing() -> dict:
    return dict(_last_retrieval_timing)


# ---------------------------------------------------------------------------
# Sentence-transformer singleton
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_sentence_transformer_embedder() -> TextEmbedder | None:
    try:
        return SentenceTransformerEmbedder()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# TF-IDF internals
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def _inverse_document_frequency(tokenized_documents: list[list[str]]) -> dict[str, float]:
    document_count = len(tokenized_documents)
    terms = {token for document in tokenized_documents for token in set(document)}
    idf: dict[str, float] = {}
    for term in terms:
        containing_documents = sum(1 for document in tokenized_documents if term in document)
        idf[term] = math.log((1 + document_count) / (1 + containing_documents)) + 1
    return idf


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(tokens)
    total = sum(counts.values()) or 1
    return {term: (count / total) * idf.get(term, 0.0) for term, count in counts.items()}


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot_product = sum(value * right.get(term, 0.0) for term, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)
