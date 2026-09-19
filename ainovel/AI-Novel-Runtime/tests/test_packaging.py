"""test_packaging.py — 包装层 (规范 §3): authored packaging + 承诺一致性 check.

The gap this closes: the funnel is 点击 × 前三章留存 × 免费追读 × 付费转化 × 长期稳定.
Packaging (书名/一句话卖点/简介/标签) decides 点击 — whether a reader opens the book at
all — and its promises decide whether the opening chapters read as honored or as
bait. Neither had any tooling: outline.schema.json carries title/logline/core_hook
but no blurb/tags, and nothing checked packaging against the produced text.

Pins:
  - packaging is a NEW authored artifact under sources/ (both plausible homes,
    outline and market-position, are frozen additionalProperties:false — §2 says a
    frozen product gets no new fields);
  - the schema carries the ADR-003 gating=false / ADR-009 authority=human consts;
  - the delivery check is deterministic, reads AUTHORED evidence_terms, and never
    gates;
  - it degrades cleanly on absent/corrupt packaging, absent promises, and an
    unfinished window;
  - it is LIVE in run_serial (proven by a real run, not a source grep).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from runtime.execution.draft_review import AXIS_EVALUATIVE
from runtime.packaging import (check_promise_delivery, load_packaging,
                              packaging_path, packaging_promises,
                              validate_packaging, PACKAGING_REVIEWER_ID)

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
_SCHEMA = json.loads(
    (STANDARD / "contracts" / "book-packaging.schema.json").read_text(encoding="utf-8"))


def _packaging(**over) -> dict:
    base = {
        "id": "PKG-00001", "kind": "book_packaging", "version": "1.0",
        "gating": False, "authority": "human",
        "title": "梦墟行者",
        "one_line_pitch": "都市悬疑 + 梦境解析 + 心理医生 + 连环命案 + 克制推理感",
        "blurb": "失忆的心理医生能进入病人梦境，靠梦晶强化自身，代价是封印一种情感。",
        "tags": ["都市", "悬疑", "梦境"],
        "promises": [
            {"promise_id": "P1", "promise_type": "金手指",
             "statement": "进入梦境取梦晶强化自身",
             "evidence_terms": ["梦墟", "梦晶"]},
            {"promise_id": "P2", "promise_type": "复仇",
             "statement": "查明连环命案真凶", "must_appear_by": 2,
             "evidence_terms": ["命案"]},
        ],
    }
    base.update(over)
    return base


def _severities(report) -> list[str]:
    return [f.severity for f in report.findings]


def _messages(report) -> str:
    return " ".join(f.message for f in report.findings)


# --------------------------------------------------------------------------- #
# Schema                                                                       #
# --------------------------------------------------------------------------- #
def test_schema_is_valid_and_closed():
    Draft202012Validator.check_schema(_SCHEMA)
    assert _SCHEMA["additionalProperties"] is False


def test_schema_pins_the_adr_invariants():
    """gating=false (ADR-003) and authority=human (ADR-009) are structural, so they
    are consts in the contract, not conventions in prose."""
    props = _SCHEMA["properties"]
    assert props["gating"]["const"] is False
    assert props["authority"]["const"] == "human"
    assert "gating" in _SCHEMA["required"] and "authority" in _SCHEMA["required"]


def test_authored_packaging_validates():
    assert validate_packaging(_packaging()) == []


def test_gating_true_is_rejected_by_the_contract():
    assert validate_packaging(_packaging(gating=True))


def test_unknown_top_level_field_is_rejected():
    assert validate_packaging(_packaging(shipping_date="2026-08"))


def test_frozen_contracts_were_not_touched():
    """§2: outline and market-position are additionalProperties:false, which is
    exactly why packaging became its own artifact instead of new fields there."""
    for name in ("outline", "market-position"):
        s = json.loads((STANDARD / "contracts" / f"{name}.schema.json")
                       .read_text(encoding="utf-8"))
        assert s.get("additionalProperties") is False
        assert "blurb" not in s.get("properties", {})


# --------------------------------------------------------------------------- #
# Loader                                                                      #
# --------------------------------------------------------------------------- #
def test_load_packaging_absent_returns_none(tmp_path):
    assert load_packaging(tmp_path) is None


def test_load_packaging_reads_authored_file(tmp_path):
    p = packaging_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(_packaging(), allow_unicode=True), encoding="utf-8")
    assert (load_packaging(tmp_path) or {}).get("title") == "梦墟行者"


def test_corrupt_packaging_degrades_instead_of_crashing_a_run(tmp_path):
    """A malformed packaging file must not take down a production run — the same
    degrade discipline load_project_outline uses."""
    p = packaging_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("title: [unclosed", encoding="utf-8")
    assert load_packaging(tmp_path) is None


def test_promises_are_normalized_with_the_golden_three_default():
    got = packaging_promises(_packaging())
    assert [p["promise_id"] for p in got] == ["P1", "P2"]
    assert got[0]["must_appear_by"] == 3      # schema default = 黄金三章 window
    assert got[1]["must_appear_by"] == 2      # authored value wins


@pytest.mark.parametrize("bad_by", [0, -1, "3", 3.5, True, None])
def test_invalid_must_appear_by_falls_back_to_three(bad_by):
    pkg = _packaging(promises=[{"promise_id": "X", "statement": "s",
                                "must_appear_by": bad_by,
                                "evidence_terms": ["t"]}])
    assert packaging_promises(pkg)[0]["must_appear_by"] == 3


def test_incomplete_promise_entries_are_dropped_not_raised():
    pkg = _packaging(promises=[
        {"promise_id": "", "statement": "无 id"},
        {"promise_id": "OK", "statement": ""},
        "not a dict",
        {"promise_id": "GOOD", "statement": "完整"},
    ])
    assert [p["promise_id"] for p in packaging_promises(pkg)] == ["GOOD"]


def test_packaging_promises_handles_none():
    assert packaging_promises(None) == []
    assert packaging_promises({}) == []


# --------------------------------------------------------------------------- #
# Delivery check                                                              #
# --------------------------------------------------------------------------- #
def test_report_is_evaluative_and_never_gates():
    r = check_promise_delivery(_packaging(), {1: "梦墟梦晶命案" * 20})
    assert r.axis == AXIS_EVALUATIVE
    assert r.gating is False
    assert r.reviewer == PACKAGING_REVIEWER_ID
    assert r.to_dict()["gating"] is False


def test_deterministic():
    bodies = {1: "梦墟" * 30, 2: "别的" * 30, 3: "还是别的" * 30}
    a = check_promise_delivery(_packaging(), bodies).to_dict()
    b = check_promise_delivery(_packaging(), bodies).to_dict()
    assert a == b


def test_promise_missed_in_its_window_warns():
    """The §3.3 defect: the window closed and the promise was never evidenced."""
    bodies = {1: "他走在街上。" * 30, 2: "什么也没发生。" * 30}
    r = check_promise_delivery(_packaging(), bodies)
    assert "warning" in _severities(r)
    assert "P2" in _messages(r)          # due by ch2, window complete, no 命案


def test_delivered_promise_is_not_warned():
    bodies = {1: "他踏入梦墟，取出梦晶。" * 20,
              2: "命案的线索浮现。" * 20,
              3: "继续。" * 20}
    r = check_promise_delivery(_packaging(), bodies)
    assert "warning" not in _severities(r)
    assert "2/2" in _messages(r)


def test_unfinished_window_is_not_called_a_failure():
    """A promise due by ch3 cannot be 'missed' when only ch1 exists — that would
    warn on every book mid-production."""
    r = check_promise_delivery(
        _packaging(promises=[{"promise_id": "P9", "statement": "后面兑现",
                              "must_appear_by": 3, "evidence_terms": ["某物"]}]),
        {1: "开篇。" * 30})
    assert "warning" not in _severities(r)
    assert "尚未产出完" in _messages(r)


def test_promise_without_evidence_terms_is_info_not_warning():
    """An unlisted term is a gap in the packaging file, not proof the book failed.
    The check never guesses at semantics."""
    r = check_promise_delivery(
        _packaging(promises=[{"promise_id": "P3", "promise_type": "智斗",
                              "statement": "靠推理取胜"}]),
        {1: "任意正文。" * 30, 2: "x" * 200, 3: "y" * 200})
    assert "warning" not in _severities(r)
    assert "evidence_terms" in _messages(r)


def test_absent_packaging_degrades_to_info():
    r = check_promise_delivery(None, {1: "正文" * 30})
    assert _severities(r) == ["info"]
    assert "未撰写" in _messages(r)


def test_packaging_without_promises_degrades_to_info():
    r = check_promise_delivery(_packaging(promises=[]), {1: "正文" * 30})
    assert _severities(r) == ["info"]
    assert r.gating is False


@pytest.mark.parametrize("bodies", [None, {}, {"x": "not an int key"}])
def test_no_produced_bodies_degrades_to_info(bodies):
    r = check_promise_delivery(_packaging(), bodies)
    assert _severities(r) == ["info"]


def test_window_uses_real_chapter_numbers_not_list_position():
    """--start-chapter skips chapters, so a flat list index would mislabel bodies.
    A resumed run producing only ch5+ must not judge a ch2 promise as missed."""
    r = check_promise_delivery(_packaging(), {5: "梦墟梦晶" * 20, 6: "命案" * 20})
    # ch1/ch2 were never produced => P1/P2 windows incomplete => no warning.
    assert "warning" not in _severities(r)


# --------------------------------------------------------------------------- #
# BUILT != LIVE                                                               #
# --------------------------------------------------------------------------- #
def test_delivery_check_is_live_in_run_serial(tmp_path):
    """Proven by driving the real run_serial. This repo has shipped 7+ detectors
    that existed but were never called from a production path."""
    from tests.test_serial import _scaffold_project, _run, _write_outline
    from runtime.outline.writer import load_project_outline

    _scaffold_project(tmp_path, n_events=3)
    _write_outline(tmp_path, [{"chapter_no": i, "goal": f"第{i}章目标"}
                              for i in (1, 2, 3)])
    # Author a packaging whose promise the deterministic stub cannot possibly honor,
    # so a real warning must come back through the run.
    p = packaging_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(_packaging(promises=[
        {"promise_id": "PX", "statement": "必须出现的承诺", "must_appear_by": 2,
         "evidence_terms": ["绝不会出现的证据词ZZZ"]}]), allow_unicode=True),
        encoding="utf-8")

    result = _run(tmp_path, outline=load_project_outline(tmp_path))
    assert result.packaging_delivery is not None, (
        "packaging_delivery must be populated by run_serial")
    assert result.packaging_delivery["gating"] is False
    msgs = " ".join(f["message"] for f in result.packaging_delivery["findings"])
    assert "PX" in msgs
    assert "packaging_delivery" in result.to_dict()


def test_run_without_packaging_still_reports_cleanly(tmp_path):
    """Every existing project has no packaging file — they must be unaffected."""
    from tests.test_serial import _scaffold_project, _run

    _scaffold_project(tmp_path, n_events=2)
    result = _run(tmp_path)
    assert result.packaging_delivery is not None
    assert all(f["severity"] == "info"
               for f in result.packaging_delivery["findings"])
