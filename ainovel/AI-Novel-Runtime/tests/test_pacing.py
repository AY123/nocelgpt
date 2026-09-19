"""test_pacing.py — intra-chapter pacing check over the emotion curve (P22).

Proves the pacing check is a DETERMINISTIC analysis of the valence sequence that
is EVALUATIVE and never gates (ADR-003): a flat/monotone/weak curve is flagged,
a healthy rise-peak-hook curve is clean, a bare skeleton (no emotion) degrades to
a clean info report, and the same curve always yields the same findings.
"""
from __future__ import annotations

from runtime.scene import check_pacing


def _plan(valences):
    """A scene plan carrying the given valence sequence."""
    return {"scenes": [
        {"index": i + 1, "beat": "x", "purpose": "p", "emotion": {"valence": v}}
        for i, v in enumerate(valences)]}


def _checks(valences):
    return [f["check"] for f in check_pacing(_plan(valences)).to_dict()["findings"]]


def _warnings(valences):
    return [f["message"] for f in check_pacing(_plan(valences)).to_dict()["findings"]
            if f["severity"] == "warning"]


# --------------------------------------------------------------------------- #
# It never gates and is always the evaluative axis                            #
# --------------------------------------------------------------------------- #
def test_never_gates():
    r = check_pacing(_plan([30, 45, 40, 80, 60])).to_dict()
    assert r["gating"] is False
    assert r["axis"] == "evaluative"


# --------------------------------------------------------------------------- #
# Curve shapes                                                                 #
# --------------------------------------------------------------------------- #
def test_flat_curve_flagged():
    w = _warnings([50, 52, 49, 51, 50])
    assert any("过平" in m for m in w)


def test_healthy_curve_is_clean():
    r = check_pacing(_plan([30, 45, 40, 80, 60])).to_dict()
    assert all(f["severity"] != "warning" for f in r["findings"])
    assert any("健康" in f["message"] for f in r["findings"])


def test_monotone_curve_flagged():
    w = _warnings([20, 40, 60, 80, 95])
    assert any("单调" in m for m in w)


def test_weak_amplitude_flagged():
    # spread just above flat-stdev but total swing still small
    w = _warnings([50, 58, 62, 56, 48])
    assert w  # at least one warning (flat or weak amplitude)


def test_front_loaded_peak_noted():
    findings = check_pacing(_plan([90, 60, 40, 30, 20])).to_dict()["findings"]
    assert any("虎头蛇尾" in f["message"] for f in findings)


# --------------------------------------------------------------------------- #
# Degrade + determinism                                                        #
# --------------------------------------------------------------------------- #
def test_bare_skeleton_degrades_to_clean_info():
    plan = {"scenes": [{"index": 1, "beat": "setup", "purpose": "p"}]}
    r = check_pacing(plan).to_dict()
    assert all(f["severity"] == "info" for f in r["findings"])
    assert r["gating"] is False


def test_partially_enriched_still_forms_curve():
    # only some scenes carry emotion; the curve is built from those
    plan = {"scenes": [
        {"index": 1, "beat": "a", "purpose": "p", "emotion": {"valence": 20}},
        {"index": 2, "beat": "b", "purpose": "p"},               # no emotion
        {"index": 3, "beat": "c", "purpose": "p", "emotion": {"valence": 85}}]}
    r = check_pacing(plan).to_dict()
    # two points, big swing -> not flat, should not warn "过平"
    assert not any("过平" in f["message"] for f in r["findings"])


def test_deterministic():
    a = check_pacing(_plan([30, 45, 40, 80, 60])).to_dict()
    b = check_pacing(_plan([30, 45, 40, 80, 60])).to_dict()
    assert a == b
