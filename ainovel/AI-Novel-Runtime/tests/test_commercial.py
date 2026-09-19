"""test_commercial.py — Commercial Optimization Loop (roadmap P16).

Pins the P16 invariants: a rewrite that relatively improves reader retention is
accepted; a rewrite that makes any persona newly drop is rejected and the
ORIGINAL draft is kept; a degraded simulation bails safely; the session is
always gating=False + comparison_only=True; the loop never returns a draft worse
(by reader reaction) than its input; and the session validates against the
commercial-session Standard schema.
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.execution.commercial import optimize_commercial
from runtime.execution.reader_sim import ReaderSimulation
from runtime.execution.model import ModelOutput

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = json.loads(
    (STANDARD / "contracts" / "commercial-session.schema.json").read_text(encoding="utf-8"))
_VALIDATOR = Draft202012Validator(SCHEMA)


def _schema_errors(session: dict) -> list[str]:
    return [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
            for e in _VALIDATOR.iter_errors(session)]


def _sim(mean, cont, personas, *, degraded=False, pay=None):
    agg = {"mean_satisfaction": mean, "continue_rate": cont,
           "drop_personas": [p["name"] for p in personas
                             if not p.get("would_continue", True)],
           "common_expectations": []}
    if pay is not None:
        agg["mean_pay_probability"] = pay
    return ReaderSimulation(
        reviewer="fake-sim", personas=personas,
        aggregate=agg,
        judge_provenance={"model_id": "fake", "degraded": degraded})


class _ScriptedSim:
    """Returns pre-scripted simulations in call order (baseline, then re-sims)."""
    reviewer_id = "fake-sim"

    def __init__(self, sims):
        self.sims = sims
        self.i = 0

    def review(self, artifact, package):
        s = self.sims[min(self.i, len(self.sims) - 1)]
        self.i += 1
        return s


class _Rewriter:
    """Always returns non-empty prose so rewrite_once yields a real artifact."""
    model_id = "rw"
    model_kind = "llm"

    def generate(self, prompt):
        return ModelOutput(text="改写后的正文内容" * 20, model_id="rw", model_kind="llm")


class _DeadRewriter:
    model_id = "rw-dead"
    model_kind = "llm"

    def generate(self, prompt):
        return ModelOutput(text="", model_id="rw-dead", model_kind="llm")


_ART = {"task_id": "TASK-00001", "provenance": {}, "body": "原始正文",
        "content_hash": "sha256:original"}
_PKG = {"task": {"task_id": "TASK-00001"}, "context": {}}

_CONTINUE = [{"name": "小白", "satisfaction": 50, "would_continue": True, "degraded": False}]


# --------------------------------------------------------------------------- #
# Structural invariants: never gates, always comparison-only                   #
# --------------------------------------------------------------------------- #
def test_session_is_never_gating_and_comparison_only():
    r = optimize_commercial(
        _ScriptedSim([_sim(50, 100, _CONTINUE), _sim(70, 100, _CONTINUE)]),
        _Rewriter(), _ART, _PKG, max_rounds=1)
    d = r.session.to_dict()
    assert d["gating"] is False
    assert d["comparison_only"] is True


def test_session_validates_against_schema():
    r = optimize_commercial(
        _ScriptedSim([_sim(50, 100, _CONTINUE), _sim(70, 100, _CONTINUE)]),
        _Rewriter(), _ART, _PKG, max_rounds=1)
    assert _schema_errors(r.session.to_dict()) == []


# --------------------------------------------------------------------------- #
# Accept a relative improvement                                                #
# --------------------------------------------------------------------------- #
def test_rewrite_that_improves_retention_is_accepted():
    before = _sim(50, 100, _CONTINUE)
    after = _sim(80, 100, [{"name": "小白", "satisfaction": 80,
                            "would_continue": True, "degraded": False}])
    r = optimize_commercial(_ScriptedSim([before, after]), _Rewriter(),
                            _ART, _PKG, max_rounds=1)
    assert r.session.verdict == "improved"
    assert r.session.rounds[0]["accepted"] is True
    # selected the rewrite, not the original
    assert r.session.selected_draft_hash != _ART["content_hash"]
    assert r.final_artifact["content_hash"] == r.session.selected_draft_hash


# --------------------------------------------------------------------------- #
# Reject a regression — keep the ORIGINAL draft                                #
# --------------------------------------------------------------------------- #
def test_rewrite_that_drops_a_persona_is_rejected():
    before = _sim(50, 100, _CONTINUE)
    after = _sim(30, 0, [{"name": "小白", "satisfaction": 30,
                          "would_continue": False, "degraded": False,
                          "drop_reason": "节奏崩了"}])
    r = optimize_commercial(_ScriptedSim([before, after]), _Rewriter(),
                            _ART, _PKG, max_rounds=1)
    assert r.session.rounds[0]["accepted"] is False
    assert r.session.rounds[0]["newly_dropped"] == ["小白"]
    assert r.session.verdict == "regressed"
    # the ORIGINAL draft is kept (never returns something readers liked less)
    assert r.session.selected_draft_hash == _ART["content_hash"]
    assert r.final_artifact["content_hash"] == _ART["content_hash"]


# --------------------------------------------------------------------------- #
# Degradation bails safely                                                     #
# --------------------------------------------------------------------------- #
def test_degraded_baseline_simulation_bails():
    r = optimize_commercial(
        _ScriptedSim([_sim(0, 0, [], degraded=True)]),
        _Rewriter(), _ART, _PKG, max_rounds=2)
    assert r.session.terminate_reason == "degraded"
    assert r.session.verdict == "degraded"
    assert r.session.selected_draft_hash == _ART["content_hash"]


def test_dead_rewriter_bails_and_keeps_original():
    r = optimize_commercial(
        _ScriptedSim([_sim(50, 100, _CONTINUE)]),
        _DeadRewriter(), _ART, _PKG, max_rounds=2)
    assert r.session.terminate_reason == "degraded"
    assert r.session.rounds[0]["degraded"] is True
    assert r.final_artifact["content_hash"] == _ART["content_hash"]
    assert _schema_errors(r.session.to_dict()) == []


# --------------------------------------------------------------------------- #
# Stops on no improvement (unchanged reader reaction)                          #
# --------------------------------------------------------------------------- #
def test_no_improvement_stops_and_keeps_original():
    # identical before/after -> compare verdict is not "improved" -> rejected
    same = _sim(50, 100, _CONTINUE)
    r = optimize_commercial(_ScriptedSim([same, same]), _Rewriter(),
                            _ART, _PKG, max_rounds=3)
    assert r.session.terminate_reason == "no_improvement"
    assert r.session.verdict == "unchanged"
    assert r.final_artifact["content_hash"] == _ART["content_hash"]
    # bounded: it did not run all 3 rounds after the first no-gain
    assert len(r.session.rounds) == 1


# --------------------------------------------------------------------------- #
# v2 (roadmap 4.4): a rewrite that keeps readers but bleeds pay intent is      #
# rejected like a newly_dropped persona — the ORIGINAL draft is kept.          #
# --------------------------------------------------------------------------- #
_PAY = [{"name": "追订党", "satisfaction": 70, "would_continue": True,
         "continue_probability": 80, "pay_probability": 65, "degraded": False}]


def test_pay_loss_rewrite_is_rejected_and_keeps_original():
    before = _sim(70, 100, _PAY, pay=65)
    # satisfaction/retention nudge up, but付费意愿 collapses below the bar.
    after_persona = [{"name": "追订党", "satisfaction": 72, "would_continue": True,
                      "continue_probability": 82, "pay_probability": 30,
                      "degraded": False}]
    after = _sim(72, 100, after_persona, pay=30)
    r = optimize_commercial(_ScriptedSim([before, after]), _Rewriter(),
                            _ART, _PKG, max_rounds=1)
    assert r.session.rounds[0]["newly_pay_lost"] == ["追订党"]
    assert r.session.rounds[0]["accepted"] is False
    assert r.session.verdict == "regressed"
    # kept the original draft despite the satisfaction bump
    assert r.session.selected_draft_hash == _ART["content_hash"]
    assert r.final_artifact["content_hash"] == _ART["content_hash"]
    assert r.session.rounds[0]["mean_pay_probability_delta"] == -35
    assert _schema_errors(r.session.to_dict()) == []


def test_pay_and_retention_both_up_is_accepted():
    before = _sim(60, 100, _PAY, pay=55)
    after_persona = [{"name": "追订党", "satisfaction": 80, "would_continue": True,
                      "continue_probability": 88, "pay_probability": 78,
                      "degraded": False}]
    after = _sim(80, 100, after_persona, pay=78)
    r = optimize_commercial(_ScriptedSim([before, after]), _Rewriter(),
                            _ART, _PKG, max_rounds=1)
    assert r.session.rounds[0]["accepted"] is True
    assert r.session.rounds[0]["newly_pay_lost"] == []
    assert r.session.rounds[0]["mean_pay_probability_delta"] == 23
    assert r.session.verdict == "improved"
    assert r.final_artifact["content_hash"] != _ART["content_hash"]
    assert _schema_errors(r.session.to_dict()) == []


# --------------------------------------------------------------------------- #
# v2 softened veto: a single tip-driven persona dipping below the pay bar is    #
# TOLERATED when NET panel付费意愿 still rose — losing a tip != losing a reader. #
# --------------------------------------------------------------------------- #
def _two(a_pay, b_pay, *, sat=70):
    """Two-persona panel: 打赏党 (tip-driven) + 追订党 (core), each with an
    explicit pay_probability, so a per-persona crossing can diverge from the
    net-pay direction."""
    return [
        {"name": "打赏党", "satisfaction": sat, "would_continue": True,
         "continue_probability": 85, "pay_probability": a_pay, "degraded": False},
        {"name": "追订党", "satisfaction": sat, "would_continue": True,
         "continue_probability": 85, "pay_probability": b_pay, "degraded": False},
    ]


def test_tip_dip_tolerated_when_net_pay_rises():
    # 打赏党 crosses 60 -> 40 (below bar -> newly_pay_lost), but 追订党 climbs
    # 50 -> 90, so mean_pay 55 -> 65 (+10). The softened rule ACCEPTS.
    before = _sim(60, 100, _two(60, 50), pay=55)
    after = _sim(75, 100, _two(40, 90), pay=65)
    r = optimize_commercial(_ScriptedSim([before, after]), _Rewriter(),
                            _ART, _PKG, max_rounds=1)
    rd = r.session.rounds[0]
    assert rd["newly_pay_lost"] == ["打赏党"]      # the tip dip is still recorded
    assert rd["mean_pay_probability_delta"] == 10  # but net pay rose
    assert rd["accepted"] is True                  # ...so it's tolerated
    assert r.session.verdict == "improved"
    assert r.final_artifact["content_hash"] != _ART["content_hash"]
    assert _schema_errors(r.session.to_dict()) == []


def test_tip_dip_still_vetoes_when_net_pay_flat_or_down():
    # 打赏党 crosses 60 -> 40; 追订党 only 50 -> 55, so mean_pay 55 -> 47 (down).
    # A pay loss with no net gain is a real regression — REJECTED, original kept.
    before = _sim(60, 100, _two(60, 50), pay=55)
    after = _sim(72, 100, _two(40, 55), pay=47)
    r = optimize_commercial(_ScriptedSim([before, after]), _Rewriter(),
                            _ART, _PKG, max_rounds=1)
    rd = r.session.rounds[0]
    assert rd["newly_pay_lost"] == ["打赏党"]
    assert rd["mean_pay_probability_delta"] == -8
    assert rd["accepted"] is False
    assert r.session.verdict == "regressed"
    assert r.final_artifact["content_hash"] == _ART["content_hash"]


def test_custom_pay_bar_changes_crossing_detection():
    # With the default bar (50), 追订党 60 -> 45 crosses -> newly_pay_lost.
    # With a lower bar (40) supplied to the simulator, 45 is still above the bar,
    # so NO crossing is detected. Proves pay_bar is threaded end to end.
    from runtime.execution.reader_sim import LLMReaderSimulator

    class _BarSim:
        reviewer_id = "bar-sim"

        def __init__(self, sims, pay_bar):
            self.sims, self.i, self.pay_bar = sims, 0, pay_bar

        def review(self, artifact, package):
            s = self.sims[min(self.i, len(self.sims) - 1)]
            self.i += 1
            return s

    persona_b = [{"name": "追订党", "satisfaction": 70, "would_continue": True,
                  "continue_probability": 80, "pay_probability": 60, "degraded": False}]
    persona_a = [{"name": "追订党", "satisfaction": 75, "would_continue": True,
                  "continue_probability": 82, "pay_probability": 45, "degraded": False}]
    before = _sim(70, 100, persona_b, pay=60)
    after = _sim(75, 100, persona_a, pay=45)

    # low bar (40): 45 stays above -> no crossing -> accepted despite pay dip
    r = optimize_commercial(_BarSim([before, after], pay_bar=40), _Rewriter(),
                            _ART, _PKG, max_rounds=1)
    assert r.session.rounds[0]["newly_pay_lost"] == []
    assert r.session.rounds[0]["accepted"] is True
