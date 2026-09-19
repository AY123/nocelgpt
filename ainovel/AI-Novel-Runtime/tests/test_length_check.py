"""test_length_check.py — single-chapter length-vs-target check (ANES v2, ADR-003).

Pins the §14 anti-抖动 guard: the checker measures a draft body's char count
against the outline's target_wordcount DETERMINISTICALLY, stays advisory (never
gates), degrades cleanly (empty body / no target), and is NOT the draft_qa word
floor (a length miss is advised, never skips the chapter).
"""
from __future__ import annotations

from runtime.execution.length_check import (check_length, length_summary,
                                            LENGTH_REVIEWER_ID,
                                            BAND_LOW, BAND_HIGH)
from runtime.execution.draft_review import AXIS_EVALUATIVE


def _warns(rep):
    return [f for f in rep.findings if f.severity == "warning"]


def test_on_target_is_clean_info():
    body = "字" * 3000
    rep = check_length({"body": body}, target=3000)
    assert not _warns(rep)
    assert rep.findings[0].severity == "info" and "达标" in rep.findings[0].message


def test_too_short_warns():
    body = "字" * 1000          # 33% of 3000, below the 60% band
    rep = check_length({"body": body}, target=3000)
    w = _warns(rep)
    assert len(w) == 1 and "偏短" in w[0].message


def test_too_long_warns():
    body = "字" * 6000          # 200% of 3000, above the 150% band
    rep = check_length({"body": body}, target=3000)
    w = _warns(rep)
    assert len(w) == 1 and "偏长" in w[0].message


def test_no_target_is_measured_not_judged():
    rep = check_length({"body": "字" * 1200}, target=None)
    assert not _warns(rep)
    assert "未声明目标篇幅" in rep.findings[0].message


def test_empty_body_degrades():
    rep = check_length({"body": "   "}, target=3000)
    assert not _warns(rep)
    assert "正文为空" in rep.findings[0].message


def test_summary_ratio_and_band():
    s = length_summary("字" * 1500, target=3000)
    assert s["total_chars"] == 1500 and s["ratio"] == 0.5
    assert s["band_low"] == BAND_LOW and s["band_high"] == BAND_HIGH
    # no target => ratio None (measured, not judged)
    assert length_summary("字" * 100, target=None)["ratio"] is None
    # empty => None
    assert length_summary("", target=3000) is None


def test_report_is_evaluative_and_never_gates():
    d = check_length({"body": "字" * 500}, target=3000).to_dict()
    assert d["axis"] == AXIS_EVALUATIVE
    assert d["gating"] is False
    assert d["reviewer"] == LENGTH_REVIEWER_ID


def test_band_edges_are_inclusive_ok():
    # exactly at the low edge (60%) and high edge (150%) are in-band (no warning)
    assert not _warns(check_length({"body": "字" * int(3000 * BAND_LOW)}, target=3000))
    assert not _warns(check_length({"body": "字" * int(3000 * BAND_HIGH)}, target=3000))


def test_role_none_matches_global_band():
    # role=None is byte-identical to the historical global-band behavior.
    body = "字" * int(3000 * 0.5)   # 50%, below the global 60% low band
    assert _warns(check_length({"body": body}, target=3000, role=None))
    s = length_summary(body, 3000, role=None)
    assert s["band_low"] == BAND_LOW and s["band_high"] == BAND_HIGH


def test_hook_role_tolerates_shorter_than_advance():
    # 50% of target warns under the advance/global band but is IN-BAND for a hook
    # chapter (its low band is 45%), so the same body flips from warn → clean.
    body = "字" * int(3000 * 0.5)
    assert _warns(check_length({"body": body}, target=3000, role="advance"))
    assert not _warns(check_length({"body": body}, target=3000, role="hook"))


def test_opening_role_tolerates_longer_lower_bound_stricter():
    # An opening chapter's low band is 80%: a 70%-of-target body is fine for
    # advance but reads as thin for an 开篇章 (world-building expected).
    body = "字" * int(3000 * 0.7)
    assert not _warns(check_length({"body": body}, target=3000, role="advance"))
    assert _warns(check_length({"body": body}, target=3000, role="opening"))


def test_role_summary_carries_role_and_its_band():
    s = length_summary("字" * 1000, 3000, role="hook")
    assert s["role"] == "hook"
    assert s["band_low"] == 0.45 and s["band_high"] == 1.3
