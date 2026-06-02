from dataclasses import dataclass
from pathlib import Path


RUNBOOKS_DIR = Path(__file__).resolve().parents[2] / "runbooks"


@dataclass(frozen=True)
class RunbookChunk:
    chunk_id: str
    source: str
    title: str
    content: str


def load_runbook_chunks(runbooks_dir: Path = RUNBOOKS_DIR) -> list[RunbookChunk]:
    chunks: list[RunbookChunk] = []
    if not runbooks_dir.exists():
        return chunks

    for path in sorted(runbooks_dir.glob("*.md")):
        chunks.extend(_chunk_markdown(path))
    return chunks


def _chunk_markdown(path: Path) -> list[RunbookChunk]:
    text = path.read_text(encoding="utf-8")
    title = _document_title(text, path)
    sections = _split_by_heading(text)
    chunks: list[RunbookChunk] = []

    for section_index, (section_title, section_content) in enumerate(sections, start=1):
        for paragraph_index, content in enumerate(_split_paragraphs(section_content), start=1):
            chunk_title = section_title or title
            chunk_id = f"{path.stem}:{section_index}:{paragraph_index}"
            chunks.append(
                RunbookChunk(
                    chunk_id=chunk_id,
                    source=path.name,
                    title=chunk_title,
                    content=content,
                )
            )
    return chunks


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
