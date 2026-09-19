"""book.py — assemble + render a manuscript from ordered chapter drafts.

`assemble_book` folds the produced chapter drafts into a BookModel (title +
ordered chapters), filtered by scope. `render_markdown` / `render_txt` turn the
model into bytes. The two are deliberately separated: adding epub/docx later is
just another renderer over the same BookModel, no change to the fold.

scope:
  - "published" (default): only chapters a human authorized in the published log
    (ADR-009 — the authorization boundary is honored by default).
  - "produced": every draft in the index (the author's full working copy).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .. import derived
from ..execution.envelope import unwrap
from ..inventory import load_published_log, project_inventory

SCOPE_PUBLISHED = "published"
SCOPE_PRODUCED = "produced"


@dataclass(frozen=True)
class Chapter:
    task_id: str
    title: str
    body: str


@dataclass(frozen=True)
class BookModel:
    title: str
    scope: str
    chapters: List[Chapter] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return sum(len(c.body) for c in self.chapters)


def _read_body(project_path: Path, entry: dict) -> Optional[str]:
    """Read a draft's prose body from its on-disk envelope. Missing/unparseable
    files degrade to None (skipped), never an error."""
    path = project_path / entry.get("path", "")
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return unwrap(obj).get("body")


def _scoped_task_ids(project_path: Path, scope: str) -> List[str]:
    """The task_ids to export, in chapter order, honoring scope. Reuses the
    inventory projection so 'published' means exactly what the funnel means
    (authored log only, ADR-009) — no duplicated authorization logic."""
    log = load_published_log(project_path)
    inv = project_inventory(project_path, published_log=log)
    # inv.chapters is already ordered by task_id (fold/chapter order).
    if scope == SCOPE_PUBLISHED:
        return [c["task_id"] for c in inv.chapters if c["status"] == "published"]
    return [c["task_id"] for c in inv.chapters]


def assemble_book(project_path: str | Path, *, scope: str = SCOPE_PUBLISHED,
                  title: Optional[str] = None) -> BookModel:
    """Fold ordered chapter drafts into a BookModel. Pure read-side; reads the
    draft index + envelopes only. `scope` defaults to 'published' so the natural
    export honors the ADR-009 authorization boundary."""
    if scope not in (SCOPE_PUBLISHED, SCOPE_PRODUCED):
        raise ValueError(f"unknown scope {scope!r}")
    project_path = Path(project_path)
    entries = {e["id"]: e for e in derived._load_index(project_path).get("artifacts", [])
               if e.get("category") == "drafts"}
    chapters: List[Chapter] = []
    for i, task_id in enumerate(_scoped_task_ids(project_path, scope), start=1):
        entry = entries.get(task_id)
        if entry is None:
            continue
        body = _read_body(project_path, entry)
        if not body:
            continue
        chapters.append(Chapter(task_id=task_id, title=f"第{i}章", body=body))
    return BookModel(title=title or project_path.name, scope=scope, chapters=chapters)


def render_markdown(book: BookModel) -> str:
    """Render a BookModel to markdown. Deterministic: same model => same bytes."""
    parts = [f"# {book.title}\n"]
    for ch in book.chapters:
        parts.append(f"## {ch.title}\n\n{ch.body.strip()}\n")
    return "\n".join(parts)


def render_txt(book: BookModel) -> str:
    """Render a BookModel to plain text (chapter headers as bare lines)."""
    parts = [book.title, ""]
    for ch in book.chapters:
        parts.append(ch.title)
        parts.append("")
        parts.append(ch.body.strip())
        parts.append("")
    return "\n".join(parts)
