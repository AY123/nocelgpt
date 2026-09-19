"""N100-062: platform reader-signal import profile.

Defines the shape of external platform data imported as diagnostic signals only.
No facts are rewritten from it; it is used for calibration / comparison.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class PlatformSignalRow:
    platform: str
    window_start: str
    window_end: str
    sample_size: int
    confidence: float | None = None
    exposure: int | None = None
    complete_read_rate: float | None = None
    three_chapter_retention: float | None = None
    ten_chapter_retention: float | None = None
    first_subscribe: int | None = None
    follow_up: int | None = None
    comments: int | None = None
    abandon_points: list[int] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlatformFeedbackProfile:
    profile_id: str
    kind: str = "platform_feedback_profile"
    version: str = "1.0"
    data_format: str = "csv/json"
    sources: list[str] = field(default_factory=list)
    rows: list[PlatformSignalRow] = field(default_factory=list)
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "kind": self.kind,
            "version": self.version,
            "data_format": self.data_format,
            "sources": list(self.sources),
            "rows": [r.to_dict() for r in self.rows],
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def build_platform_feedback_profile(
    *,
    profile_id: str,
    sources: list[str] | None = None,
    rows: list[Mapping[str, Any]] | None = None,
) -> PlatformFeedbackProfile:
    parsed_rows = [PlatformSignalRow(**{k: v for k, v in dict(row).items() if k in PlatformSignalRow.__annotations__}) for row in (rows or [])]
    return PlatformFeedbackProfile(
        profile_id=profile_id,
        sources=sources or [],
        rows=parsed_rows,
        metadata={"row_count": len(parsed_rows), "signals": [
            "exposure", "complete_read_rate", "three_chapter_retention", "ten_chapter_retention", "first_subscribe", "follow_up", "comments", "abandon_points"
        ]},
    )
