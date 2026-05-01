"""Load and chunk the local support corpus from data/ directory."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Chunk:
    chunk_id: str
    company: str          # hackerrank | claude | visa
    title: str
    source_url: str
    breadcrumbs: list[str]
    text: str             # ~500 char window
    doc_path: str


COMPANY_DIR_MAP = {
    "hackerrank": "hackerrank",
    "claude": "claude",
    "visa": "visa",
}

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_CHUNK_SIZE = 600
_OVERLAP = 80


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Strip YAML frontmatter and return (metadata dict, body)."""
    import yaml  # local import to keep top-level clean
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except Exception:
        meta = {}
    body = text[m.end():]
    return meta, body


def _chunk_text(text: str, size: int = _CHUNK_SIZE, overlap: int = _OVERLAP) -> list[str]:
    """Split body into overlapping windows."""
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


class CorpusLoader:
    """Loads all corpus markdown files and returns Chunk objects per company."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def load(self) -> dict[str, list[Chunk]]:
        """Returns {company_key: [Chunk, ...]} for all three domains."""
        corpus: dict[str, list[Chunk]] = {k: [] for k in COMPANY_DIR_MAP}
        for company_key, subdir in COMPANY_DIR_MAP.items():
            company_path = self.data_dir / subdir
            if not company_path.exists():
                continue
            for md_file in company_path.rglob("*.md"):
                self._ingest_file(md_file, company_key, corpus)
        return corpus

    def _ingest_file(self, path: Path, company_key: str, corpus: dict) -> None:
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return

        meta, body = _parse_frontmatter(raw)
        title = meta.get("title", path.stem)
        source_url = meta.get("source_url", "")
        breadcrumbs_raw = meta.get("breadcrumbs", [])
        if isinstance(breadcrumbs_raw, list):
            breadcrumbs = [str(b) for b in breadcrumbs_raw]
        else:
            breadcrumbs = [str(breadcrumbs_raw)]

        windows = _chunk_text(body)
        for i, window in enumerate(windows):
            chunk_id = f"{company_key}::{path.stem}::{i}"
            corpus[company_key].append(
                Chunk(
                    chunk_id=chunk_id,
                    company=company_key,
                    title=title,
                    source_url=source_url,
                    breadcrumbs=breadcrumbs,
                    text=window,
                    doc_path=str(path),
                )
            )
