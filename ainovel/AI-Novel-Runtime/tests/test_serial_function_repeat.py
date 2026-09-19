"""test_serial_function_repeat.py — W11-03 cross-chapter function-repetition.

Covers the three scaffold patterns (continuous / cyclical / renamed_same_function)
plus the healthy-sequence and too-short degrade cases. Deterministic, advisory,
never gates (ADR-003) — the report always carries axis=evaluative, gating=False.
"""
from __future__ import annotations

from runtime.scene import check_serial_function_repeat
from runtime.scene.serial_function_repeat import (
    CONTINUOUS_RUN,
    CYCLE_REPEATS,
    FUNCTION_REPEAT_REVIEWER_ID,
)


def _ch(cid, pacing, cliff, payoff, esc, threads=None, focus=None):
    """Build one chapter input in the {objective, mandate, chapter_id} shape."""
    return {
        "chapter_id": cid,
        "objective": {
            "pacing_role": pacing,
            "cliffhanger_type": cliff,
            "commercial_intent": {"payoff_type": payoff},
            "plot_threads": threads or ["main"],
            "character_focus": focus or ["lead"],
        },
        "mandate": {"escalation": {"kind": esc}},
    }


def _severities(report):
    d = report.to_dict()
    return d, [f["severity"] for f in d["findings"]]


def _warnings_about(report, needle):
    return [f for f in report.to_dict()["findings"]
            if f["severity"] == "warning" and needle in f["message"]]


def test_report_is_advisory_never_gates():
    chapters = [_ch(f"C{i}", "rising_action", "reveal", "partial_payoff", "flat")
                for i in range(5)]
    d, _ = _severities(check_serial_function_repeat(chapters))
    assert d["reviewer"] == FUNCTION_REPEAT_REVIEWER_ID
    assert d["axis"] == "evaluative"
    assert d["gating"] is False


def test_continuous_repeat_warns():
    # CONTINUOUS_RUN identical signatures in a row.
    n = CONTINUOUS_RUN + 2
    chapters = [_ch(f"C{i}", "rising_action", "reveal", "partial_payoff", "flat",
                    threads=[f"t{i}"], focus=[f"p{i}"]) for i in range(n)]
    rep = check_serial_function_repeat(chapters)
    assert _warnings_about(rep, "连续")


def test_cyclical_repeat_warns():
    # A B A B A B ... period-2 rotation for >= CYCLE_REPEATS cycles. Give each
    # chapter distinct surface so the ONLY structural finding is the cycle.
    sigs = [("rising_action", "reveal", "partial_payoff", "flat"),
            ("falling_action", "cliff", "full_payoff", "power_reveal")]
    chapters = []
    for i in range(CYCLE_REPEATS * 2):
        p, c, pay, e = sigs[i % 2]
        chapters.append(_ch(f"C{i}", p, c, pay, e, threads=[f"t{i}"], focus=[f"p{i}"]))
    rep = check_serial_function_repeat(chapters)
    assert _warnings_about(rep, "周期")


def test_renamed_same_function_warns():
    # Same structural signature every chapter, but DIFFERENT surface dressing
    # (threads/focus) — new names, same job. Keep the run below CONTINUOUS_RUN
    # length is impossible here (all same), so we assert the renamed finding
    # exists alongside the continuous one.
    chapters = [
        _ch("A", "rising_action", "reveal", "partial_payoff", "flat",
            threads=["heist"], focus=["ling"]),
        _ch("B", "rising_action", "reveal", "partial_payoff", "flat",
            threads=["romance"], focus=["mei"]),
        _ch("C", "rising_action", "reveal", "partial_payoff", "flat",
            threads=["war"], focus=["gen"]),
    ]
    rep = check_serial_function_repeat(chapters)
    assert _warnings_about(rep, "换名同功能")


def test_healthy_variety_is_info_only():
    # Every chapter a genuinely different structural job -> no warnings.
    variety = [
        ("rising_action", "reveal", "partial_payoff", "power_reveal"),
        ("falling_action", "cliff", "full_payoff", "reversal"),
        ("climax", "twist", "delayed_payoff", "flat"),
        ("setup", "question", "no_payoff", "escalate"),
        ("resolution", "resolve", "full_payoff", "de_escalate"),
    ]
    chapters = [_ch(f"C{i}", *variety[i], threads=[f"t{i}"], focus=[f"p{i}"])
                for i in range(len(variety))]
    d, sev = _severities(check_serial_function_repeat(chapters))
    assert "warning" not in sev
    assert any("健康" in f["message"] for f in d["findings"])


def test_too_short_degrades_to_info():
    chapters = [_ch("only", "rising_action", "reveal", "partial_payoff", "flat")]
    d, sev = _severities(check_serial_function_repeat(chapters))
    assert sev == ["info"]
    assert "不足" in d["findings"][0]["message"]


def test_deterministic():
    chapters = [_ch(f"C{i}", "rising_action", "reveal", "partial_payoff", "flat")
                for i in range(6)]
    a = check_serial_function_repeat(chapters).to_dict()
    b = check_serial_function_repeat(chapters).to_dict()
    assert a == b


def test_missing_fields_do_not_crash():
    # Objectives/mandates may be absent (a run without those layers).
    chapters = [{"chapter_id": f"C{i}", "objective": None, "mandate": None}
                for i in range(4)]
    d, _ = _severities(check_serial_function_repeat(chapters))
    # all-None signatures are identical -> continuous warning, but must not crash
    assert d["gating"] is False


# --------------------------------------------------------------------------- #
# Liveness: the detector actually runs inside a real serial (built != live).   #
# Mirrors test_mandate.test_v8_serial_produces_mandates_and_series.            #
# --------------------------------------------------------------------------- #
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_serial as T  # reuse the scaffold + _run helpers


def test_v8_serial_folds_function_repeat(tmp_path):
    """A v8 run builds objectives+mandates, so the run carries a function_repeat
    fold — proof the detector is wired into the live production path, not dead."""
    T._scaffold_project(tmp_path, n_events=3)
    r = T._run(tmp_path, prompt_version="8.0.0")
    assert r.produced == 3
    assert r.function_repeat is not None
    # structural invariants (ADR-003): advisory, never gates
    assert r.function_repeat["gating"] is False
    assert r.function_repeat["axis"] == "evaluative"
    assert r.to_dict()["function_repeat"] is not None


def test_v8_serial_is_reproducible_with_function_repeat(tmp_path):
    T._scaffold_project(tmp_path, n_events=3)
    r1 = T._run(tmp_path, prompt_version="8.0.0")
    r2 = T._run(tmp_path, prompt_version="8.0.0")
    assert r1.function_repeat == r2.function_repeat
