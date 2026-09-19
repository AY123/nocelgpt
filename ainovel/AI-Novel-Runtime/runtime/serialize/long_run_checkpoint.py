"""N100-051~054: per-10-chapter checkpoint aggregator.

Folds consumption checkpoints, promise ledger, chapter evidence, and quality
sentinel into a single per-window report so a long run can be audited at every
10-chapter boundary. Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class WindowCheck:
    window: str
    chapter_start: int
    chapter_end: int
    chapter_count: int
    produced: int
    skipped: int
    quality_warnings: list[str] = field(default_factory=list)
    promise_overdue: list[str] = field(default_factory=list)
    promise_resolved: list[str] = field(default_factory=list)
    fact_conflicts_unresolved: int = 0
    cost_total: float | None = None
    cost_currency: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LongRunCheckpointReport:
    checkpoints: list[WindowCheck]
    total_chapters: int
    total_produced: int
    total_skipped: int
    total_cost: float | None
    cost_currency: str | None
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoints": [c.to_dict() for c in self.checkpoints],
            "total_chapters": self.total_chapters,
            "total_produced": self.total_produced,
            "total_skipped": self.total_skipped,
            "total_cost": self.total_cost,
            "cost_currency": self.cost_currency,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def build_long_run_checkpoint_report(
    *,
    chapters: Sequence[Mapping[str, Any]],
    promise_ledger: Mapping[str, Any] | None = None,
    window_size: int = 10,
) -> LongRunCheckpointReport:
    total = len(chapters)
    checkpoints: list[WindowCheck] = []
    total_produced = 0
    total_skipped = 0
    total_cost = 0.0
    cost_currency = None
    any_cost = False

    for start in range(0, total, window_size):
        window_chapters = list(chapters[start:start + window_size])
        if not window_chapters:
            continue
        chapter_start = int(window_chapters[0].get("chapter_index") or start + 1)
        chapter_end = int(window_chapters[-1].get("chapter_index") or start + len(window_chapters))
        produced = sum(1 for c in window_chapters if c.get("ok"))
        skipped = sum(1 for c in window_chapters if not c.get("ok"))
        total_produced += produced
        total_skipped += skipped

        quality_warnings: list[str] = []
        for c in window_chapters:
            verdict = str(c.get("quality", {}).get("verdict") or "")
            if verdict and verdict not in ("pass", "ok", ""):
                quality_warnings.append(f"ch{c.get('chapter_index')}: {verdict}")

        promise_overdue: list[str] = []
        promise_resolved: list[str] = []
        if promise_ledger:
            promise_overdue = list(promise_ledger.get("overdue") or [])
            promise_resolved = list(promise_ledger.get("resolved") or [])

        window_cost = 0.0
        for c in window_chapters:
            cost_info = c.get("cost", {}).get("cost")
            if isinstance(cost_info, dict):
                any_cost = True
                cost_currency = cost_info.get("currency", cost_currency)
                window_cost += float(cost_info.get("total_cost", 0) or 0)
        total_cost += window_cost

        checkpoints.append(WindowCheck(
            window=f"ch{chapter_start:03d}-{chapter_end:03d}",
            chapter_start=chapter_start,
            chapter_end=chapter_end,
            chapter_count=len(window_chapters),
            produced=produced,
            skipped=skipped,
            quality_warnings=quality_warnings,
            promise_overdue=promise_overdue,
            promise_resolved=promise_resolved,
            fact_conflicts_unresolved=0,
            cost_total=round(window_cost, 6) if window_cost > 0 else None,
            cost_currency=cost_currency if window_cost > 0 else None,
            metadata={"window_index": start // window_size},
        ))

    return LongRunCheckpointReport(
        checkpoints=checkpoints,
        total_chapters=total,
        total_produced=total_produced,
        total_skipped=total_skipped,
        total_cost=round(total_cost, 6) if any_cost else None,
        cost_currency=cost_currency,
        metadata={"window_size": window_size, "window_count": len(checkpoints)},
    )
