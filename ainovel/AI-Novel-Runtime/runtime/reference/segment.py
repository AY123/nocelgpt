"""segment.py — split a reference novel into chapters for per-chapter measurement.

The detectors measure a per-chapter body, so a reference novel must be split the
same way. Chinese web novels almost always mark chapters with a 第N章 heading (or
序章/楔子/尾声 for front/back matter). We split on those headings; a text with no
recognizable headings degrades to fixed-size chunks (chunk_text) so the profile
can still be built. Deterministic: same text => same segmentation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from ..outline.chunker import chunk_text

# A chapter heading line: 第<num>章/节/回 (num may be Chinese or Arabic), or a
# named front/back-matter section. Anchored to line start so a mid-line "第三章"
# reference inside prose does not falsely split. Matches the heading + optional
# trailing title on the same line.
_HEADING_RE = re.compile(
    r"^[ \t　]*"
    r"(?:第\s*[0-9一二三四五六七八九十百千零两]+\s*[章节回卷]"
    r"|序章|序言|楔子|引子|尾声|后记|终章|番外)"
    r"[^\n]*$",
    re.MULTILINE,
)

# A too-short "chapter" is almost certainly a heading-only fragment or a stray
# match, not a real chapter; fold it away rather than pollute the profile.
_MIN_CHAPTER_CHARS = 200


@dataclass(frozen=True)
class ReferenceChapter:
    """One segmented reference chapter: its 1-based index within a source novel,
    the heading line (if any), and the body the detectors will measure."""
    source_id: str
    index: int
    heading: str
    body: str

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "index": self.index,
            "heading": self.heading,
            "body": self.body,
        }


def _split_on_headings(text: str) -> List[tuple]:
    """Return [(heading, body), ...] by cutting at each heading line. Text before
    the first heading (front matter / metadata) is dropped. Deterministic."""
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return []
    out: List[tuple] = []
    for i, m in enumerate(matches):
        heading = m.group(0).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if len(body) >= _MIN_CHAPTER_CHARS:
            out.append((heading, body))
    return out


def segment_reference_novel(source_id: str, text: str, *,
                            max_chunk_chars: int = 6000) -> List[ReferenceChapter]:
    """Split one reference novel's full text into ReferenceChapters.

    Prefers real chapter headings (第N章 / 序章 / 楔子 …). When a text carries no
    recognizable headings (e.g. a scraped blob), it degrades to fixed-size chunks
    so a profile can still be built — advisory data, never a hard requirement.
    Deterministic: same (source_id, text) => same chapters."""
    text = text or ""
    chapters: List[ReferenceChapter] = []
    parts = _split_on_headings(text)
    if parts:
        for idx, (heading, body) in enumerate(parts, start=1):
            chapters.append(ReferenceChapter(
                source_id=source_id, index=idx, heading=heading, body=body))
        return chapters
    # Degrade: no headings => fixed-size chunks, no heading label.
    for idx, chunk in enumerate(chunk_text(text, max_chars=max_chunk_chars), start=1):
        if len(chunk.strip()) >= _MIN_CHAPTER_CHARS:
            chapters.append(ReferenceChapter(
                source_id=source_id, index=idx, heading="", body=chunk.strip()))
    return chapters
