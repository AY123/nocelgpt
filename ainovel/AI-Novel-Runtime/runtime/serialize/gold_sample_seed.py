"""D90-01 gold sample seeding helpers.

Creates a framework for collecting 50+ chapter gold samples with dual review and
adjudication scaffolds. Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GoldSample:
    sample_id: str
    chapter_id: str
    source_type: str
    reviewer_a: str = ""
    reviewer_b: str = ""
    adjudicator: str = ""
    score_a: float | None = None
    score_b: float | None = None
    agreed: bool = False
    notes: str = ""
    labels: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GoldSampleCollectionPlan:
    kind: str
    version: str
    target_count: int
    samples: list[GoldSample]
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "target_count": self.target_count,
            "samples": [s.to_dict() for s in self.samples],
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def seed_gold_sample_plan(chapters: Sequence[Mapping[str, Any]], target_count: int = 50) -> GoldSampleCollectionPlan:
    samples: list[GoldSample] = []
    for i, ch in enumerate(chapters[:target_count], start=1):
        cid = str(ch.get("chapter_id") or ch.get("task_id") or f"CH-{i:03d}")
        samples.append(GoldSample(
            sample_id=f"GS-{i:03d}",
            chapter_id=cid,
            source_type="chapter_run",
            notes="seeded from existing chapter artifact",
            labels=["dual_review", "adjudication_needed"],
        ))
    return GoldSampleCollectionPlan(
        kind="gold_sample_collection_plan",
        version="1.0",
        target_count=target_count,
        samples=samples,
        metadata={"seeded_count": len(samples), "dual_review": True, "adjudication": True},
    )
