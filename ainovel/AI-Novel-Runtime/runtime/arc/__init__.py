"""Long-Arc subdomain (ANES v2, roadmap M3 — 百万字长弧规划).

The Long-Arc Plan projects the outline's authored volume / power-tier / conflict
skeleton FORWARD into per-chapter long-arc coordinates, so chapter generation
(especially past the ~30 authored chapters) knows its position in the whole arc:
which volume, how far to the volume climax, which power tier to approach, whether
a paywall / milestone is near.

DISCIPLINE:
  - PURE + DETERMINISTIC PROJECTION (ADR-008 sibling): same outline => same plan.
    No LLM in the base fold; the PlotArchitect may enrich it later, never replace.
  - ADVISORY, never gates (ADR-003): it shapes generation emphasis, never blocks.
  - READS the outline only; writes no facts (ADR-006).
"""
from .projection import (
    LongArcPlan,
    project_long_arc,
    LONG_ARC_REVIEWER_ID,
    DEFAULT_CHAPTER_LIMIT,
)
from .render import render_long_arc

__all__ = [
    "LongArcPlan",
    "project_long_arc",
    "render_long_arc",
    "LONG_ARC_REVIEWER_ID",
    "DEFAULT_CHAPTER_LIMIT",
]
