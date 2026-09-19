"""draft_qa.py — deterministic structural QA for a ChapterDraft (ANES v2, ADR-003).

These are DETERMINISTIC checks on the output artifact: objective, pass/fail,
reproducible. They may gate. Voice/pacing/theme judgments are EVALUATIVE and do
NOT live here (they attach on the trend axis later) — keeping the "only
deterministic checks gate a build" rule intact (ADR-003).

Structural checks:
  - body is non-empty
  - word_count meets a floor
  - provenance is present and pins at least one source
  - content_hash present and well-formed
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass
class DraftFinding:
    check: str
    message: str

    def __str__(self):
        return f"[error] draft-qa/{self.check}: {self.message}"


def check_draft(artifact: dict, min_words: int = 1) -> List[DraftFinding]:
    out: List[DraftFinding] = []
    body = artifact.get("body", "")
    if not body.strip():
        out.append(DraftFinding("non-empty", "draft body is empty"))
    wc = artifact.get("word_count", 0)
    if wc < min_words:
        out.append(DraftFinding("word-floor",
                                f"word_count {wc} below floor {min_words}"))
    prov = artifact.get("provenance", {})
    if not prov.get("derived_from"):
        out.append(DraftFinding("provenance",
                                "draft has no derived_from provenance"))
    h = artifact.get("content_hash", "")
    if not _HASH_RE.match(h):
        out.append(DraftFinding("hash", f"malformed content_hash {h!r}"))
    return out
