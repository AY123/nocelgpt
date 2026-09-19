"""test_mandate.py — Narrative Mandate (Phase 9) tests.

Covers the anti-流水账 layer: the cross-chapter mandate projection (9.1/9.2), the
three staleness detectors (9.3), the v8 prompt wiring (9.4), and the byte-identity
guarantee that a v6/v7 run is unchanged (the mandate binds only when supplied).
"""
from __future__ import annotations

from pathlib import Path
import sys

from runtime.director import (
    project_narrative_mandate, validate_narrative_mandate, render_narrative_mandate,
    check_mandate_chapter, check_mandate_series, build_chapter_objective,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_serial as T  # reuse the scaffold + _run helpers


# --- an outline with authored per-chapter beats, for the fold tests ------------
def _outline(n=6):
    return {
        "id": "OUTLINE-00001",
        "protagonist_engine": {"flaw": "隐忍", "desire": "复仇"},
        "reward_loop": {"cadence_chapters": 3},
        "first_30_chapters": [
            {"chapter_no": 1, "goal": "身份落差 + 立刻的威胁",
             "conflict": "主角在绝境中被逼", "escalation": "冲突较上一章升级",
             "reward_if_any": "", "end_hook": "触发金手指，代价显现"},
            {"chapter_no": 2, "goal": "推进当前阶段目标",
             "conflict": "本章的具体冲突：主角目标与压迫源的直接碰撞",
             "escalation": "冲突较上一章升级", "reward_if_any": "",
             "end_hook": "抛出新悬念"},
            {"chapter_no": 3, "goal": "第一次小翻身/打脸",
             "conflict": "主角反击", "escalation": "冲突较上一章升级",
             "reward_if_any": "打脸翻身", "end_hook": "引来更强注意"},
        ] + [
            {"chapter_no": i, "goal": f"推进第{i}章",
             "conflict": "本章的具体冲突：主角目标与压迫源的直接碰撞",
             "escalation": "冲突较上一章升级", "reward_if_any": "",
             "end_hook": f"第{i}章钩子"}
            for i in range(4, n + 1)
        ],
    }


# --- 9.1: schema + build -------------------------------------------------------
def test_mandate_validates_against_schema():
    m = project_narrative_mandate(chapter_no=1, task_id="TASK-00001",
                                  outline=_outline())
    assert validate_narrative_mandate(m) == []
    assert m["kind"] == "narrative_mandate"
    assert m["chapter_no"] == 1


def test_mandate_carries_structural_consts():
    """ADR-003/ADR-009: the mandate never gates and human owns direction."""
    m = project_narrative_mandate(chapter_no=1, task_id="TASK-00001",
                                  outline=_outline())
    assert m["gating"] is False
    assert m["authority"] == "human"


# --- 9.2: cross-chapter fold ---------------------------------------------------
def test_escalation_folds_from_previous_to_level():
    """escalation.from_level = the previous mandate's to_level (ADR-008 fold)."""
    o = _outline()
    m1 = project_narrative_mandate(chapter_no=1, task_id="TASK-00001", outline=o)
    m2 = project_narrative_mandate(chapter_no=2, task_id="TASK-00002", outline=o,
                                   prev_mandate=m1)
    assert m2["escalation"]["from_level"] == m1["escalation"]["to_level"]


def test_inner_shift_folds_from_previous_to():
    """inner_shift.from = the previous mandate's inner_shift.to (ADR-008 fold)."""
    o = _outline()
    m1 = project_narrative_mandate(chapter_no=1, task_id="TASK-00001", outline=o)
    m2 = project_narrative_mandate(chapter_no=2, task_id="TASK-00002", outline=o,
                                   prev_mandate=m1)
    assert m2["inner_shift"]["from"] == m1["inner_shift"]["to"]


def test_opening_chapter_degrades_without_prev_mandate():
    """Chapter 1 has no prior mandate => base tension levels, seeded inner-from."""
    m = project_narrative_mandate(chapter_no=1, task_id="TASK-00001",
                                  outline=_outline(), prev_mandate=None)
    assert m["escalation"]["from_level"] == 2   # _BASE_FROM_LEVEL
    assert m["inner_shift"]["from"]             # seeded from the protagonist engine


def test_fold_is_deterministic():
    """Same beat + same prev mandate => same content_hash (ADR-008)."""
    o = _outline()
    a = project_narrative_mandate(chapter_no=2, task_id="TASK-00002", outline=o)
    b = project_narrative_mandate(chapter_no=2, task_id="TASK-00002", outline=o)
    assert a["content_hash"] == b["content_hash"]


def test_ceiling_pins_kind_to_flat():
    """When the ladder hits MAX (10) and can't rise, escalation.kind is flat
    regardless of the beat keyword — so the stall detector still fires."""
    o = _outline(n=14)
    prev = None
    seq = []
    for n in range(1, 14):
        m = project_narrative_mandate(chapter_no=n, task_id=f"TASK-{n:05d}",
                                      outline=o, prev_mandate=prev)
        seq.append(m); prev = m
    ceiling = [m for m in seq if m["escalation"]["to_level"] == 10
               and m["escalation"]["from_level"] == 10]
    assert ceiling, "expected some chapters pinned at the ceiling"
    assert all(m["escalation"]["kind"] == "flat" for m in ceiling)


# --- 9.3: the three staleness detectors ----------------------------------------
def test_lukewarm_chapter_warns_on_no_cost_of_delay():
    o = _outline()
    # ch2's beat is a generic transition (推进当前阶段目标) => cost_of_delay none
    m2 = project_narrative_mandate(chapter_no=2, task_id="TASK-00002", outline=o)
    r = check_mandate_chapter(m2).to_dict()
    assert r["gating"] is False
    assert r["findings"][0]["severity"] == "warning"
    assert "温水" in r["findings"][0]["message"]


def test_urgent_chapter_is_clean():
    o = _outline()
    m1 = project_narrative_mandate(chapter_no=1, task_id="TASK-00001", outline=o)
    r = check_mandate_chapter(m1).to_dict()
    assert r["findings"][0]["severity"] == "info"


def test_none_mandate_check_degrades_clean():
    r = check_mandate_chapter(None).to_dict()
    assert r["findings"][0]["severity"] == "info"
    assert r["gating"] is False


def test_series_detects_tension_stall_at_ceiling():
    o = _outline(n=14)
    prev = None; seq = []
    for n in range(1, 14):
        m = project_narrative_mandate(chapter_no=n, task_id=f"TASK-{n:05d}",
                                      outline=o, prev_mandate=prev)
        seq.append(m); prev = m
    r = check_mandate_series(seq).to_dict()
    assert r["gating"] is False
    assert any(f["severity"] == "warning" and "停滞" in f["message"]
               for f in r["findings"])


def test_series_too_few_mandates_degrades_clean():
    o = _outline()
    m1 = project_narrative_mandate(chapter_no=1, task_id="TASK-00001", outline=o)
    r = check_mandate_series([m1]).to_dict()
    assert r["findings"][0]["severity"] == "info"


# --- 9.4: v8 wiring + byte-identity --------------------------------------------
def test_objective_without_mandate_is_byte_identical():
    """The mandate= param is gated: an objective built WITHOUT a mandate is
    identical to before the parameter existed (every v6/v7 run)."""
    a = build_chapter_objective(chapter_id="TASK-00018", narrative_ir={"id": "NIR-1"})
    b = build_chapter_objective(chapter_id="TASK-00018", narrative_ir={"id": "NIR-1"},
                                mandate=None)
    assert a == b


def test_objective_with_mandate_adds_constraints():
    """A supplied mandate appends its escalation/inner-shift as hard constraints."""
    o = _outline()
    m1 = project_narrative_mandate(chapter_no=1, task_id="TASK-00001", outline=o)
    base = build_chapter_objective(chapter_id="TASK-00001")
    withm = build_chapter_objective(chapter_id="TASK-00001", mandate=m1)
    assert len(withm["constraints"]) > len(base["constraints"])


def test_v8_serial_produces_mandates_and_series(tmp_path):
    T._scaffold_project(tmp_path, n_events=3)
    r = T._run(tmp_path, prompt_version="8.0.0")
    assert r.produced == 3
    assert r.gating is False
    # every chapter carries a mandate check; the run carries a series check
    assert all(c.mandate is not None for c in r.chapters)
    assert r.mandate_series is not None


def test_v6_run_carries_no_mandate(tmp_path):
    """A v6 run never builds a mandate => ChapterRun.mandate is a clean skip and
    the run's mandate_series stays None (byte-identity of the non-mandate path)."""
    T._scaffold_project(tmp_path, n_events=3)
    r = T._run(tmp_path, prompt_version="6.0.0")
    assert r.mandate_series is None
    # the per-chapter mandate check degrades to a clean info (mandate was None)
    for c in r.chapters:
        assert c.mandate["findings"][0]["severity"] == "info"


def test_v8_serial_is_reproducible(tmp_path):
    T._scaffold_project(tmp_path, n_events=3)
    r1 = T._run(tmp_path, prompt_version="8.0.0")
    r2 = T._run(tmp_path, prompt_version="8.0.0")
    assert [c.draft_hash for c in r1.chapters] == [c.draft_hash for c in r2.chapters]


def test_render_is_bounded_and_nonempty():
    m = project_narrative_mandate(chapter_no=1, task_id="TASK-00001",
                                  outline=_outline())
    s = render_narrative_mandate(m)
    assert s and "冲突阶梯" in s
