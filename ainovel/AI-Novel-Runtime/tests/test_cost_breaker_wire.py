"""test_cost_breaker_wire.py — the D180-05 breaker is LIVE in the serial path.

`runtime/serialize/cost_breaker.py` documents itself as "a hard stop on billing",
had passing unit tests, and had NO caller: the serial loop compared
`spent >= limit` inline in two places instead. That is the built-but-never-wired
pattern this repo keeps re-landing, so these tests bind the module to the live
path rather than only testing it in isolation:

  1. a real `run_serial` with a budget routes its decision through `check_budget`
  2. both layers (run-level project, per-chapter) go through the SAME breaker
  3. no budget flags => the breaker never trips => behavior is unchanged

Test 1 is the anti-regression: inlining the compare again turns it red.
"""
from __future__ import annotations

import sys
from pathlib import Path

from runtime.serialize import loop as loop_mod

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_serial import (  # reuse the scaffold + enhancer stubs
    _ImprovingSim, _Rewriter, _run, _scaffold_project,
)


def test_serial_budget_decision_routes_through_the_breaker(tmp_path, monkeypatch):
    """The live serial must ASK cost_breaker, not re-implement the compare."""
    calls = []
    real = loop_mod.check_budget

    def spy(**kwargs):
        calls.append(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(loop_mod, "check_budget", spy)

    _scaffold_project(tmp_path, n_events=2)
    result = _run(tmp_path, budget_limit=0.0)

    # the run still holds, exactly as the hand-rolled compare did
    assert [c.stage for c in result.chapters] == ["budget-held", "budget-held"]
    # ...and the hold was DECIDED by the breaker
    assert calls, "cost_breaker.check_budget was never called by the serial path"
    assert any(c.get("project_limit") == 0.0 for c in calls), calls


def test_per_chapter_layer_uses_the_same_breaker(tmp_path, monkeypatch):
    """The chapter layer is the breaker's `chapter_*` layer, not a second engine.

    The chapter layer is only consulted BEFORE the optional enhancer loops (they
    are what adds cost on top of generation), so the run must supply the
    simulator/rewriter pair for that decision point to be reached at all.
    """
    calls = []
    real = loop_mod.check_budget

    def spy(**kwargs):
        calls.append(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(loop_mod, "check_budget", spy)

    _scaffold_project(tmp_path, n_events=1)
    result = _run(tmp_path, simulator=_ImprovingSim(), rewrite_model=_Rewriter(),
                  commercial_rounds=1, per_chapter_budget=0.0)

    assert any(c.get("chapter_limit") == 0.0 for c in calls), calls
    # and the breaker's verdict is what skipped the enhancer
    assert all(c.budget_note and "commercial loop skipped" in c.budget_note
               for c in result.chapters)


def test_no_budget_flags_never_trips(tmp_path):
    """A run with no budget flags is unaffected by the wiring (limit None)."""
    _scaffold_project(tmp_path, n_events=2)
    result = _run(tmp_path)

    assert result.produced == 2
    assert all(c.stage != "budget-held" for c in result.chapters)
    assert all(c.budget_note is None for c in result.chapters)
