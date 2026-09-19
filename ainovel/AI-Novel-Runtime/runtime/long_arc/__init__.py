"""long_arc — long-arc planning projections (Phase 9 / M3).

This subdomain folds authored high-level planning inputs (Brain, market-position,
outline / events) into a derived long-arc plan with chapter-band goals and
commercial cadence. Advisory only, never gates; it does not write facts.
"""

from .plan import build_long_arc_plan, validate_long_arc_plan, write_long_arc_plan

__all__ = ["build_long_arc_plan", "validate_long_arc_plan", "write_long_arc_plan"]
