"""test_schedule.py — serialization schedule projection (roadmap P17).

The schedule (backlog / break-risk / update-calendar) is a PROJECTION folded
from the authored SerialPlan + the count of produced drafts — not mutable
operational state. These tests pin: the plan is an authored input (absent is not
an error), the schema rejects malformed plans, the projection is deterministic,
backlog = produced - due, break-risk tracks the backlog, the update calendar
skips rest days, and the report never gates (ADR-003).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from runtime.schedule import (load_plan, validate_plan, project_schedule,
                              plan_path)

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"


_VALID_PLAN = {
    "id": "PLAN-00001", "kind": "serial_plan", "version": "1.0",
    "start_date": "2026-06-25", "daily_target": 2,
    "backlog_target": 10, "rest_days": [7],
}


def _project_with_drafts(root: Path, n_drafts: int):
    """Write a minimal derived draft index with n produced drafts so the
    projection has something to count (it reads the index, not the facts)."""
    import yaml as _yaml
    idx_dir = root / "registry" / "derived"
    idx_dir.mkdir(parents=True, exist_ok=True)
    artifacts = [{"id": f"TASK-{i:05d}", "category": "drafts",
                  "path": f"registry/derived/drafts/TASK-{i:05d}.json",
                  "content_hash": f"sha256:{i:064d}"} for i in range(1, n_drafts + 1)]
    # a non-draft artifact must NOT be counted as a chapter
    artifacts.append({"id": "PM-1", "category": "prompt-manifests",
                      "path": "x", "content_hash": "sha256:0"})
    (idx_dir / "_index.yaml").write_text(
        _yaml.safe_dump({"artifacts": artifacts}, allow_unicode=True), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Schema: authored plan validated; malformed rejected                          #
# --------------------------------------------------------------------------- #
def test_valid_plan_passes_schema():
    assert validate_plan(_VALID_PLAN, standard_root=STANDARD) == []


def test_unknown_field_is_rejected():
    bad = dict(_VALID_PLAN, surprise="nope")
    errs = validate_plan(bad, standard_root=STANDARD)
    assert any("Additional properties" in e for e in errs)


def test_missing_required_is_rejected():
    bad = {k: v for k, v in _VALID_PLAN.items() if k != "daily_target"}
    assert any("daily_target" in e for e in validate_plan(bad, standard_root=STANDARD))


def test_rest_day_out_of_range_is_rejected():
    bad = dict(_VALID_PLAN, rest_days=[8])
    assert validate_plan(bad, standard_root=STANDARD)


# --------------------------------------------------------------------------- #
# Loader: absence is not an error                                              #
# --------------------------------------------------------------------------- #
def test_absent_plan_returns_none(tmp_path):
    assert load_plan(tmp_path) is None
    assert plan_path(tmp_path).name == "serial-plan.yaml"


def test_all_commented_plan_parses_as_absent(tmp_path):
    (tmp_path / "sources").mkdir()
    plan_path(tmp_path).write_text("# just comments\n# id: PLAN-00001\n", encoding="utf-8")
    assert load_plan(tmp_path) is None


# --------------------------------------------------------------------------- #
# Projection: deterministic, never gates                                       #
# --------------------------------------------------------------------------- #
def test_projection_is_deterministic_and_never_gates(tmp_path):
    _project_with_drafts(tmp_path, 5)
    a = project_schedule(tmp_path, _VALID_PLAN, today=date(2026, 7, 2))
    b = project_schedule(tmp_path, _VALID_PLAN, today=date(2026, 7, 2))
    assert a.to_dict() == b.to_dict()
    assert a.gating is False
    assert a.to_dict()["gating"] is False


def test_backlog_is_produced_minus_due(tmp_path):
    # start 2026-06-25 .. today 2026-07-02, rest day = Sunday (7). Days in range:
    # Jun25 Thu, 26 Fri, 27 Sat, 28 Sun(REST), 29 Mon, 30 Tue, Jul1 Wed, 2 Thu
    # => 7 active days * daily_target 2 = 14 due.
    _project_with_drafts(tmp_path, 6)
    r = project_schedule(tmp_path, _VALID_PLAN, today=date(2026, 7, 2))
    assert r.active_days_elapsed == 7
    assert r.due == 14
    assert r.produced == 6      # the prompt-manifest entry is NOT counted
    assert r.backlog == 6 - 14


def test_break_risk_tracks_backlog(tmp_path):
    # high: behind schedule (negative backlog)
    _project_with_drafts(tmp_path, 2)
    assert project_schedule(tmp_path, _VALID_PLAN, today=date(2026, 7, 2)).break_risk == "high"

    # low: ahead of due but below the backlog_target cushion
    _project_with_drafts(tmp_path, 18)   # due=14 -> backlog 4, target 10
    assert project_schedule(tmp_path, _VALID_PLAN, today=date(2026, 7, 2)).break_risk == "low"

    # none: backlog at/above target
    _project_with_drafts(tmp_path, 30)   # backlog 16 >= 10
    assert project_schedule(tmp_path, _VALID_PLAN, today=date(2026, 7, 2)).break_risk == "none"


def test_before_start_date_nothing_is_due(tmp_path):
    _project_with_drafts(tmp_path, 3)
    r = project_schedule(tmp_path, _VALID_PLAN, today=date(2026, 6, 1))
    assert r.active_days_elapsed == 0
    assert r.due == 0
    assert r.backlog == 3


# --------------------------------------------------------------------------- #
# Update calendar skips rest days                                              #
# --------------------------------------------------------------------------- #
def test_calendar_skips_rest_days(tmp_path):
    _project_with_drafts(tmp_path, 5)
    r = project_schedule(tmp_path, _VALID_PLAN, today=date(2026, 7, 3), upcoming_days=3)
    # rest day = Sunday(7). Next dates after Fri Jul 3: Sat 4, [Sun 5 skip], Mon 6, Tue 7
    assert r.upcoming == ["2026-07-04", "2026-07-06", "2026-07-07"]


def test_calendar_never_loops_forever_with_many_rest_days(tmp_path):
    _project_with_drafts(tmp_path, 1)
    plan = dict(_VALID_PLAN, rest_days=[1, 2, 3, 4, 5, 6, 7])  # every day is rest
    r = project_schedule(tmp_path, plan, today=date(2026, 7, 2), upcoming_days=5)
    assert r.upcoming == []   # bounded scan, no infinite loop
