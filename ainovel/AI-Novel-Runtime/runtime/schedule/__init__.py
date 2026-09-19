"""Serialization schedule subdomain (ANES v2, roadmap P17).

The serialization schedule (backlog / break-risk / update-calendar) is a
PROJECTION, not mutable operational state: schedule@today = fold(authored
SerialPlan, count of produced drafts). Like the Story State (ADR-008) it is
recomputed, never edited in place. The SerialPlan is an AUTHORED input under
sources/ (like the Novel Brain), never a fact or a derived artifact. The
projection is ADVISORY and never gates (ADR-003); it reads only, never writes
facts (ADR-006).
"""

from .loader import plan_path, load_plan, validate_plan
from .projection import ScheduleReport, project_schedule

__all__ = ["plan_path", "load_plan", "validate_plan",
           "ScheduleReport", "project_schedule"]
