"""Y365-02: million-word stability report scaffold.

Folds a long-run execution report + quality trend + cost trend into a stability
assessment for a ~1M word project. Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class StabilityWindow:
    window_id: str
    chapter_start: int
    chapter_end: int
    word_count: int
    quality_avg: float | None
    quality_decline: bool
    cost_per_chapter: float | None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MillionWordStabilityReport:
    kind: str
    version: str
    project_id: str
    total_chapters: int
    total_words: int
    is_million_word: bool
    windows: list[StabilityWindow]
    back_half_decline: bool
    stable: bool
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "project_id": self.project_id,
            "total_chapters": self.total_chapters,
            "total_words": self.total_words,
            "is_million_word": self.is_million_word,
            "windows": [w.to_dict() for w in self.windows],
            "back_half_decline": self.back_half_decline,
            "stable": self.stable,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def build_million_word_stability_report(
    *,
    project_id: str,
    chapters: Sequence[Mapping[str, Any]],
    window_size: int = 50,
    words_per_chapter: int = 3000,
) -> MillionWordStabilityReport:
    total = len(chapters)
    # A chapter may carry its REAL measured word_count (the dashboard folds it
    # from the draft body via text_metrics). Only fall back to the flat
    # words_per_chapter estimate for chapters that don't: a million-word
    # stability claim built purely on count x 3000 would be a fabricated number.
    def _words(c: Mapping[str, Any]) -> int:
        wc = c.get("word_count")
        return int(wc) if isinstance(wc, (int, float)) and wc > 0 else words_per_chapter

    total_words = sum(_words(c) for c in chapters)
    is_million = total_words >= 1_000_000

    windows: list[StabilityWindow] = []
    quality_avgs: list[float] = []

    for start in range(0, total, window_size):
        w_chapters = list(chapters[start:start + window_size])
        if not w_chapters:
            continue
        ch_start = int(w_chapters[0].get("chapter_index") or start + 1)
        ch_end = int(w_chapters[-1].get("chapter_index") or start + len(w_chapters))
        wc = sum(_words(c) for c in w_chapters)

        scores: list[float] = []
        for c in w_chapters:
            q = c.get("quality") or {}
            s = q.get("scores") or {}
            if isinstance(s, dict) and s:
                vals = [float(v) for v in s.values() if isinstance(v, (int, float))]
                if vals:
                    scores.append(sum(vals) / len(vals))
        avg = round(sum(scores) / len(scores), 2) if scores else None
        if avg is not None:
            quality_avgs.append(avg)
        decline = False
        if len(quality_avgs) >= 2 and avg is not None:
            decline = avg < quality_avgs[-2] - 0.5

        cost_vals: list[float] = []
        for c in w_chapters:
            cost = (c.get("cost") or {}).get("cost")
            if isinstance(cost, dict):
                cost_vals.append(float(cost.get("total_cost", 0) or 0))
        cpc = round(sum(cost_vals) / len(cost_vals), 4) if cost_vals else None

        windows.append(StabilityWindow(
            window_id=f"ch{ch_start:03d}-{ch_end:03d}",
            chapter_start=ch_start,
            chapter_end=ch_end,
            word_count=wc,
            quality_avg=avg,
            quality_decline=decline,
            cost_per_chapter=cpc,
        ))

    back_half_decline = False
    if len(quality_avgs) >= 2:
        mid = len(quality_avgs) // 2
        front = quality_avgs[:mid]
        back = quality_avgs[mid:]
        front_avg = sum(front) / len(front) if front else 0
        back_avg = sum(back) / len(back) if back else 0
        back_half_decline = back_avg < front_avg - 0.5

    stable = not back_half_decline

    return MillionWordStabilityReport(
        kind="million_word_stability_report",
        version="1.0",
        project_id=project_id,
        total_chapters=total,
        total_words=total_words,
        is_million_word=is_million,
        windows=windows,
        back_half_decline=back_half_decline,
        stable=stable,
        metadata={
            "window_size": window_size,
            "words_per_chapter": words_per_chapter,
            "quality_avg_count": len(quality_avgs),
        },
    )
