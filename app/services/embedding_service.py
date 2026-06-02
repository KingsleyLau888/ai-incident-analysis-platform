import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Protocol


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_.'-]+")


class TextEmbedder(Protocol):
    name: str

    def rank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        ...


@dataclass
class SentenceTransformerEmbedder:
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    name: str = "sentence-transformers"

    def __post_init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("sentence-transformers is not installed") from exc

        self._model = SentenceTransformer(self.model_name, local_files_only=True)

    def rank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        if not documents:
            return []

        embeddings = self._model.encode([query, *documents], normalize_embeddings=True)
        query_embedding = embeddings[0]
        document_embeddings = embeddings[1:]
        scored = [
            (index, float(query_embedding @ document_embedding))
            for index, document_embedding in enumerate(document_embeddings)
        ]
        return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]


@dataclass
class TfidfEmbedder:
    name: str = "tf-idf-fallback"

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


def get_embedder() -> TextEmbedder:
    if os.getenv("RUNBOOK_EMBEDDING_BACKEND") != "sentence-transformers":
        return TfidfEmbedder()

    try:
        return SentenceTransformerEmbedder()
    except Exception:
        return TfidfEmbedder()


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
