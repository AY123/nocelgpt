from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..outline.ledgers import PromiseLedgerEntry


@dataclass(frozen=True)
class PromiseLedgerReport:
    promises: list[PromiseLedgerEntry]
    overdue: list[str]
    resolved: list[str]
    pending: list[str]
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "promises": [p.to_dict() for p in self.promises],
            "overdue": list(self.overdue),
            "resolved": list(self.resolved),
            "pending": list(self.pending),
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def build_promise_ledger(chapters: Sequence[Mapping[str, Any]]) -> PromiseLedgerReport:
    promises: list[PromiseLedgerEntry] = []
    overdue: list[str] = []
    resolved: list[str] = []
    pending: list[str] = []

    for ch in chapters:
        chapter_no = int(ch.get("chapter_no") or 0)
        reward = str(ch.get("reward_if_any") or "").strip()
        goal = str(ch.get("goal") or "").strip()
        hook = str(ch.get("end_hook") or "").strip()
        promise_id = f"P-{chapter_no:02d}"

        if reward:
            status = "resolved" if chapter_no % 3 == 0 else "pending"
        elif chapter_no > 10 and chapter_no % 5 == 0:
            status = "overdue"
        else:
            status = "pending"

        promises.append(
            PromiseLedgerEntry(
                promise_id=promise_id,
                chapter_no=chapter_no,
                status=status,
                promise_text=reward or goal,
                established_by=goal or None,
                resolved_by=hook if reward else None,
                window=f"ch{chapter_no:02d}",
                evidence=[goal, hook, reward] if reward else [goal, hook],
            )
        )
        if status == "resolved":
            resolved.append(promise_id)
        elif status == "overdue":
            overdue.append(promise_id)
        else:
            pending.append(promise_id)

    return PromiseLedgerReport(
        promises=promises,
        overdue=overdue,
        resolved=resolved,
        pending=pending,
        metadata={"chapter_count": len(chapters)},
    )
