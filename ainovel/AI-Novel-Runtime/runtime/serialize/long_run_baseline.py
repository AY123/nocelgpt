"""N100-054: 100-chapter baseline report builder.

Folds a complete 100-chapter run into a single product baseline that can be
re-computed from raw artifacts. Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class BaselineSegment:
    label: str
    chapter_start: int
    chapter_end: int
    chapter_count: int
    produced: int
    skipped: int
    avg_quality: float | None
    quality_warnings: list[str] = field(default_factory=list)
    cost_total: float | None = None
    cost_currency: str | None = None
    promise_overdue: list[str] = field(default_factory=list)
    promise_resolved: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HundredChapterBaseline:
    project_id: str
    kind: str = "hundred_chapter_baseline"
    version: str = "1.0"
    front_half: BaselineSegment | None = None
    back_half: BaselineSegment | None = None
    full_run: BaselineSegment | None = None
    go_iterate_stop: str = "iterate"
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "kind": self.kind,
            "version": self.version,
            "front_half": self.front_half.to_dict() if self.front_half else None,
            "back_half": self.back_half.to_dict() if self.back_half else None,
            "full_run": self.full_run.to_dict() if self.full_run else None,
            "go_iterate_stop": self.go_iterate_stop,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def _build_segment(
    chapters: Sequence[Mapping[str, Any]],
    label: str,
    start: int,
    end: int,
    promise_ledger: Mapping[str, Any] | None = None,
) -> BaselineSegment:
    window = [c for c in chapters if start <= int(c.get("chapter_index") or 0) <= end]
    produced = sum(1 for c in window if c.get("ok"))
    skipped = sum(1 for c in window if not c.get("ok"))

    quality_scores: list[float] = []
    quality_warnings: list[str] = []
    for c in window:
        q = c.get("quality") or {}
        scores = q.get("scores") or {}
        if isinstance(scores, dict) and scores:
            vals = [float(v) for v in scores.values() if isinstance(v, (int, float))]
            if vals:
                quality_scores.append(sum(vals) / len(vals))
        verdict = str(q.get("verdict") or "")
        if verdict and verdict not in ("pass", "ok", ""):
            quality_warnings.append(f"ch{c.get('chapter_index')}: {verdict}")

    avg_quality = round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else None

    cost_total = 0.0
    cost_currency = None
    any_cost = False
    for c in window:
        cost_info = (c.get("cost") or {}).get("cost")
        if isinstance(cost_info, dict):
            any_cost = True
            cost_currency = cost_info.get("currency", cost_currency)
            cost_total += float(cost_info.get("total_cost", 0) or 0)

    promise_overdue: list[str] = []
    promise_resolved: list[str] = []
    if promise_ledger:
        promise_overdue = list(promise_ledger.get("overdue") or [])
        promise_resolved = list(promise_ledger.get("resolved") or [])

    return BaselineSegment(
        label=label,
        chapter_start=start,
        chapter_end=end,
        chapter_count=len(window),
        produced=produced,
        skipped=skipped,
        avg_quality=avg_quality,
        quality_warnings=quality_warnings,
        cost_total=round(cost_total, 6) if any_cost else None,
        cost_currency=cost_currency if any_cost else None,
        promise_overdue=promise_overdue,
        promise_resolved=promise_resolved,
        metadata={"avg_quality_source": "scores dict values"},
    )


def build_hundred_chapter_baseline(
    *,
    project_id: str,
    chapters: Sequence[Mapping[str, Any]],
    promise_ledger: Mapping[str, Any] | None = None,
) -> HundredChapterBaseline:
    total = len(chapters)
    mid = total // 2

    front = _build_segment(chapters, "front_half", 1, mid, promise_ledger)
    back = _build_segment(chapters, "back_half", mid + 1, total, promise_ledger)
    full = _build_segment(chapters, "full_run", 1, total, promise_ledger)

    # Determine go/iterate/stop
    go_iterate_stop = "iterate"
    if total == 0:
        go_iterate_stop = "stop"
    elif back.avg_quality is not None and front.avg_quality is not None:
        if back.avg_quality >= front.avg_quality and back.skipped == 0:
            go_iterate_stop = "go"
        elif back.avg_quality < front.avg_quality - 1.0:
            go_iterate_stop = "stop"
    elif back.skipped > front.skipped:
        go_iterate_stop = "stop"

    return HundredChapterBaseline(
        project_id=project_id,
        front_half=front,
        back_half=back,
        full_run=full,
        go_iterate_stop=go_iterate_stop,
        metadata={
            "total_chapters": total,
            "mid_point": mid,
            "front_avg_quality": front.avg_quality,
            "back_avg_quality": back.avg_quality,
        },
    )
