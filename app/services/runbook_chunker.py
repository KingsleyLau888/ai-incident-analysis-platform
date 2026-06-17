"""Runbook document loading and chunking.

Supports three chunking strategies:
- markdown: split by heading + paragraph (default, preserves document structure)
- fixed: split by approximate token count with overlap
- semantic: split at embedding-similarity drop points
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path


RUNBOOKS_DIR = Path(__file__).resolve().parents[2] / "runbooks"

# Approximate token count (4 chars ≈ 1 token for English text)
CHARS_PER_TOKEN = 4
DEFAULT_CHUNK_TOKENS = 256
DEFAULT_OVERLAP_TOKENS = 50


@dataclass(frozen=True)
class RunbookChunk:
    chunk_id: str
    source: str
    title: str
    content: str
    strategy: str = "markdown"  # "markdown" | "fixed" | "semantic"
    issue_type: str = "unknown"
    chunk_type: str = "general"


# ---------------------------------------------------------------------------
# Strategy selection
# ---------------------------------------------------------------------------

CHUNKING_STRATEGY = os.getenv("CHUNKING_STRATEGY", "markdown")


def load_runbook_chunks(
    runbooks_dir: Path = RUNBOOKS_DIR,
    strategy: str | None = None,
) -> list[RunbookChunk]:
    """Load and chunk all runbook markdown files using *strategy*."""
    strategy = strategy or CHUNKING_STRATEGY
    chunks: list[RunbookChunk] = []
    if not runbooks_dir.exists():
        return chunks

    for path in sorted(runbooks_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = _document_title(text, path)

        if strategy == "fixed":
            chunks.extend(_chunk_fixed(path, text, title))
        elif strategy == "semantic":
            chunks.extend(_chunk_semantic(path, text, title))
        else:
            chunks.extend(_chunk_markdown(path, text, title))

    return chunks


# ---------------------------------------------------------------------------
# Markdown structural chunking (default)
# ---------------------------------------------------------------------------


def _chunk_markdown(path: Path, text: str, title: str) -> list[RunbookChunk]:
    """Split by markdown heading + paragraph."""
    sections = _split_by_heading(text)
    chunks: list[RunbookChunk] = []

    for section_index, (section_title, section_content) in enumerate(sections, start=1):
        for paragraph_index, content in enumerate(_split_paragraphs(section_content), start=1):
            chunk_title = section_title or title
            chunk_id = f"{path.stem}:md:{section_index}:{paragraph_index}"
            chunks.append(
                RunbookChunk(
                    chunk_id=chunk_id,
                    source=path.name,
                    title=chunk_title,
                    content=content,
                    strategy="markdown",
                    issue_type=infer_issue_type(path.name, chunk_title, content),
                    chunk_type=infer_chunk_type(chunk_title),
                )
            )
    return chunks


# ---------------------------------------------------------------------------
# Fixed-size chunking
# ---------------------------------------------------------------------------


def _chunk_fixed(
    path: Path, text: str, title: str, chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[RunbookChunk]:
    """Split text into fixed-size chunks with overlap."""
    chunk_size = chunk_tokens * CHARS_PER_TOKEN
    overlap_size = overlap_tokens * CHARS_PER_TOKEN
    step = chunk_size - overlap_size

    # Flatten: remove extra whitespace
    flat = " ".join(text.split())
    chunks: list[RunbookChunk] = []
    start = 0
    index = 1

    while start < len(flat):
        end = min(start + chunk_size, len(flat))
        content = flat[start:end].strip()
        if content:
            chunks.append(
                RunbookChunk(
                    chunk_id=f"{path.stem}:fixed:{index}",
                    source=path.name,
                    title=title,
                    content=content,
                    strategy="fixed",
                    issue_type=infer_issue_type(path.name, title, content),
                    chunk_type="general",
                )
            )
            index += 1
        start += step
        if end >= len(flat):
            break

    return chunks


# ---------------------------------------------------------------------------
# Semantic chunking (embedding-similarity-based split)
# ---------------------------------------------------------------------------


def _chunk_semantic(path: Path, text: str, title: str) -> list[RunbookChunk]:
    """Split text where sentence embedding similarity drops.

    Falls back to paragraph chunking if sentence-transformers is unavailable.
    """
    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return _chunk_markdown(path, text, title)

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        embeddings = model.encode(sentences, normalize_embeddings=True)
    except Exception:
        # Fallback: use paragraph chunking
        return _chunk_markdown(path, text, title)

    # Compute cosine similarities between adjacent sentences
    similarities = []
    for i in range(len(embeddings) - 1):
        sim = float(embeddings[i] @ embeddings[i + 1])
        similarities.append(sim)

    # Find split points where similarity drops below threshold
    # (using median - 1 std dev as threshold)
    if not similarities:
        return _chunk_markdown(path, text, title)

    mean_sim = sum(similarities) / len(similarities)
    threshold = mean_sim * 0.7  # 30% below mean = split point

    chunks: list[RunbookChunk] = []
    chunk_sentences: list[str] = [sentences[0]]
    index = 1

    for i, sim in enumerate(similarities):
        if sim < threshold and chunk_sentences:
            content = " ".join(chunk_sentences).strip()
            if content:
                chunks.append(
                    RunbookChunk(
                        chunk_id=f"{path.stem}:sem:{index}",
                        source=path.name,
                        title=title,
                        content=content,
                        strategy="semantic",
                        issue_type=infer_issue_type(path.name, title, content),
                        chunk_type="general",
                    )
                )
                index += 1
            chunk_sentences = [sentences[i + 1]]
        else:
            chunk_sentences.append(sentences[i + 1])

    # Don't forget the last chunk
    if chunk_sentences:
        content = " ".join(chunk_sentences).strip()
        if content:
            chunks.append(
                RunbookChunk(
                chunk_id=f"{path.stem}:sem:{index}",
                source=path.name,
                title=title,
                content=content,
                strategy="semantic",
                issue_type=infer_issue_type(path.name, title, content),
                chunk_type="general",
            )
        )

    return chunks


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _document_title(text: str, path: Path) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.removeprefix("# ").strip()
    return path.stem.replace("_", " ").title()


def _split_by_heading(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            if current_lines:
                sections.append((current_title, current_lines))
                current_lines = []
            current_title = stripped.lstrip("#").strip()
            continue
        current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    return [(title, "\n".join(lines).strip()) for title, lines in sections if "\n".join(lines).strip()]


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    return paragraphs or ([text.strip()] if text.strip() else [])


def _split_sentences(text: str) -> list[str]:
    """Naive sentence splitter (no NLTK dependency)."""
    import re

    # Split on sentence-ending punctuation followed by space and capital letter
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    return [s.strip() for s in sentences if s.strip()]


def infer_issue_type(source: str, title: str = "", content: str = "") -> str:
    text = f"{source} {title} {content}".lower()
    if any(term in text for term in ["database", "mysql", "postgres", "connection_pool", "dbconnection"]):
        return "database_issue"
    if any(term in text for term in ["timeout", "deadline", "dns", "queue", "kafka", "provider"]):
        return "timeout_issue"
    if any(term in text for term in ["auth", "oauth", "token", "credential", "secret", "permission"]):
        return "auth_issue"
    if any(term in text for term in ["cache", "redis", "stampede"]):
        return "cache_issue"
    if any(term in text for term in ["memory", "oom", "heap"]):
        return "memory_issue"
    if any(term in text for term in ["server_error", "500", "rollback", "serialization", "release"]):
        return "server_error"
    return "unknown"


def infer_chunk_type(title: str) -> str:
    normalized = title.lower()
    if "symptom" in normalized:
        return "symptoms"
    if "check" in normalized or "diagnostic" in normalized:
        return "checks"
    if "action" in normalized or "resolution" in normalized or "rollback" in normalized:
        return "actions"
    if "cause" in normalized:
        return "causes"
    return "general"
