"""Novel Dashboard subdomain (ANES v2, roadmap P18).

A pure READ-SIDE aggregation of the products the pipeline already produces —
Story State projection (P14), Novel Brain (P15), serialization schedule (P17),
and the derived draft index plus QA/commercial signals on each draft's envelope
(P16) — into one project-wide panorama. Introduces no new state, computes
nothing authoritative, is advisory and never gates (ADR-003), and reads only,
never writing facts (ADR-006).
"""

from .report import DashboardReport, build_dashboard

__all__ = ["DashboardReport", "build_dashboard"]
