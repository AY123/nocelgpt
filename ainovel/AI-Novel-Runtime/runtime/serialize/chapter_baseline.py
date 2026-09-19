"""D30-04 / D30-05 baseline + human review scaffold.

Builds a 30-chapter baseline report from existing chapter artifacts and pairs it
with an empty human review record scaffold. Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .serialization_utils import content_hash


@dataclass(frozen=True)
class HumanReviewRecord:
    reviewer_id: str
    chapter_id: str
    verdict: str | None = None
    notes: str = ""
    edit_minutes: int | None = None
    labels: list[str] = field(default_factory=list)
    adjudication: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChapterBaselineSummary:
    chapter_id: str
    chapter_index: int
    title: str
    draft_hash: str | None = None
    state_hash: str | None = None
    final_hash: str | None = None
    quality_verdict: str | None = None
    commercial_verdict: str | None = None
    publish_recommendation: str | None = None
    prompt_provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThirtyChapterBaseline:
    kind: str
    version: str
    chapter_count: int
    summaries: list[ChapterBaselineSummary]
    reviewers: list[str]
    human_reviews: list[HumanReviewRecord]
    notes: str = ""
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "chapter_count": self.chapter_count,
            "summaries": [s.to_dict() for s in self.summaries],
            "reviewers": list(self.reviewers),
            "human_reviews": [r.to_dict() for r in self.human_reviews],
            "notes": self.notes,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def build_thirty_chapter_baseline(*, chapters: Sequence[Mapping[str, Any]], reviewers: Sequence[str] | None = None, notes: str = "") -> ThirtyChapterBaseline:
    summaries: list[ChapterBaselineSummary] = []
    human_reviews: list[HumanReviewRecord] = []
    for ch in chapters[:30]:
        idx = int(ch.get("chapter_index") or ch.get("index") or 0)
        cid = str(ch.get("chapter_id") or ch.get("task_id") or f"CH-{idx:03d}")
        summaries.append(
            ChapterBaselineSummary(
                chapter_id=cid,
                chapter_index=idx,
                title=str(ch.get("title") or ch.get("chapter_title") or cid),
                draft_hash=ch.get("draft_hash"),
                state_hash=ch.get("state_hash"),
                final_hash=ch.get("final_hash") or (ch.get("chapter_final") or {}).get("final_hash"),
                quality_verdict=(ch.get("quality") or {}).get("verdict") or ch.get("verdict"),
                commercial_verdict=ch.get("commercial_verdict"),
                publish_recommendation=(ch.get("publish_readiness") or {}).get("recommendation"),
                prompt_provenance=ch.get("prompt_provenance") or {},
            )
        )
        human_reviews.append(HumanReviewRecord(reviewer_id="", chapter_id=cid))

    reviewers = list(reviewers or [])
    baseline = ThirtyChapterBaseline(
        kind="thirty_chapter_baseline",
        version="1.0",
        chapter_count=len(summaries),
        summaries=summaries,
        reviewers=reviewers,
        human_reviews=human_reviews,
        notes=notes,
        metadata={"review_count": len(human_reviews)},
    )
    return baseline


def write_thirty_chapter_baseline(path: str | Path, baseline: ThirtyChapterBaseline) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = baseline.to_dict()
    payload["content_hash"] = content_hash(payload)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out
