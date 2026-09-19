"""projection.py — Serialization schedule as a projection (ANES v2, roadmap P17).

The schedule is NOT mutable operational state that a daily job edits. Like the
Story State (ADR-008), it is a PROJECTION folded from two inputs:

    schedule@today = fold(authored SerialPlan, count of produced drafts)

  - produced chapters = how many drafts the pipeline has actually produced
    (counted from the derived draft index — the SSOT of what exists).
  - due chapters      = how many the authored plan says SHOULD be published by
    `today` (daily_target over active days since start_date, skipping rest_days).
  - backlog (库存)    = produced - due. A backlog below the plan's backlog_target
    is a BREAK RISK (断更预警).
  - update calendar   = the next N publish dates (skipping rest_days).

DISCIPLINE:
  - PURE + DETERMINISTIC: given the same inputs (+ the same `today`), the same
    report. No I/O beyond reading the draft index; no randomness.
  - ADVISORY, never gates (ADR-003): `gating=false`. A thin backlog WARNS; it
    never blocks a build.
  - READS only; never writes facts (ADR-006).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

from .. import derived


@dataclass(frozen=True)
class ScheduleReport:
    reviewer: str
    produced: int
    due: int
    backlog: int
    backlog_target: int
    active_days_elapsed: int
    break_risk: str                       # "none" | "low" | "high"
    upcoming: List[str] = field(default_factory=list)   # next publish dates
    findings: List[dict] = field(default_factory=list)
    gating: bool = False                  # ADR-003 — advisory, never blocks

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "gating": self.gating,
            "produced": self.produced,
            "due": self.due,
            "backlog": self.backlog,
            "backlog_target": self.backlog_target,
            "active_days_elapsed": self.active_days_elapsed,
            "break_risk": self.break_risk,
            "upcoming": self.upcoming,
            "findings": self.findings,
        }


def _count_produced_drafts(project_path: str | Path) -> int:
    """Count produced chapter drafts from the derived draft index (the SSOT of
    what the pipeline has actually produced). Zero if no index yet."""
    index = derived._load_index(project_path)
    return sum(1 for e in index.get("artifacts", []) if e.get("category") == "drafts")


def _active_days(start: date, today: date, rest_days: set) -> int:
    """Count publish (non-rest) days in [start, today]. Zero before start_date."""
    if today < start:
        return 0
    n = 0
    d = start
    while d <= today:
        if d.isoweekday() not in rest_days:
            n += 1
        d += timedelta(days=1)
    return n


def _next_publish_dates(start: date, today: date, rest_days: set, count: int) -> List[str]:
    """The next `count` publish dates strictly after today (or from start if the
    serial hasn't begun), skipping rest days."""
    out: List[str] = []
    d = max(today + timedelta(days=1), start)
    # scan forward a bounded window so a 7-rest-day plan can't loop forever
    guard = 0
    while len(out) < count and guard < count * 7 + 14:
        if d.isoweekday() not in rest_days:
            out.append(d.isoformat())
        d += timedelta(days=1)
        guard += 1
    return out


def project_schedule(
    project_path: str | Path,
    plan: dict,
    *,
    today: Optional[date] = None,
    upcoming_days: int = 7,
    reviewer_id: str = "serial-schedule-v1",
) -> ScheduleReport:
    """Fold the authored SerialPlan + the produced-draft count into an advisory
    backlog / break-risk / update-calendar readout. Pure + deterministic given
    `today`. Never gates (ADR-003)."""
    today = today or date.today()
    start = date.fromisoformat(plan["start_date"])
    daily_target = int(plan["daily_target"])
    backlog_target = int(plan.get("backlog_target", 0))
    rest_days = set(plan.get("rest_days", []) or [])

    produced = _count_produced_drafts(project_path)
    active_days = _active_days(start, today, rest_days)
    due = active_days * daily_target
    backlog = produced - due

    # Break risk: negative backlog means already behind schedule (high); a
    # backlog below target means the cushion is thinning (low); otherwise none.
    if backlog < 0:
        break_risk = "high"
    elif backlog < backlog_target:
        break_risk = "low"
    else:
        break_risk = "none"

    findings = [{
        "check": "serial-schedule",
        "severity": "info",
        "message": (f"produced={produced} due={due} backlog={backlog} "
                    f"target={backlog_target} risk={break_risk} (advisory, never gates)"),
    }]
    if break_risk == "high":
        findings.append({
            "check": "break-risk", "severity": "warning",
            "message": (f"已落后进度：已产出 {produced} 章，按计划应发 {due} 章，"
                        f"缺口 {-backlog} 章。断更风险高（建议，非阻断）"),
        })
    elif break_risk == "low":
        findings.append({
            "check": "break-risk", "severity": "warning",
            "message": (f"库存 {backlog} 章低于目标 {backlog_target} 章，"
                        f"缓冲变薄。建议补库存（建议，非阻断）"),
        })

    upcoming = _next_publish_dates(start, today, rest_days, upcoming_days)

    return ScheduleReport(
        reviewer=reviewer_id,
        produced=produced,
        due=due,
        backlog=backlog,
        backlog_target=backlog_target,
        active_days_elapsed=active_days,
        break_risk=break_risk,
        upcoming=upcoming,
        findings=findings,
    )
