"""test_chapter_ir.py — Phase 4.2 Narrative IR (chapter-ir + scene-plan v2 + v4).

Proves:
  - build_chapter_ir is a deterministic projection (same inputs => same artifact
    + content_hash) and validates against chapter-ir.schema.json;
  - outline intent (first_30_chapters) flows into the IR's beats + payoff_target;
  - a chapter with no outline entry DEGRADES to a single setup beat, no payoff
    (advisory, ADR-003);
  - lower_to_scene_plan produces a scene-plan v2 artifact (one scene per beat, in
    order) that still validates, carries ir_ref, and surfaces the v2 narrative
    ops (information_gain/reader_question);
  - the IR's payoff_target GROUNDS the quality judge's promise_delivery prompt;
  - the v4 serial runs end-to-end, persists chapter-ir + scene-plan, and never
    gates; while v3 stays byte-identical (v4's IR layer does not perturb v3).
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from runtime import derived
from runtime.scene import (build_chapter_ir, lower_to_scene_plan,
                           render_chapter_ir)
from runtime.execution.quality_center import build_judge_prompt
from runtime.serialize import run_serial

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"
IR_SCHEMA = json.loads(
    (STANDARD / "contracts" / "chapter-ir.schema.json").read_text(encoding="utf-8"))
SCENE_PLAN_SCHEMA = json.loads(
    (STANDARD / "contracts" / "scene-plan.schema.json").read_text(encoding="utf-8"))


def _ir_validator():
    return Draft202012Validator(IR_SCHEMA)


def _sp_validator():
    return Draft202012Validator(SCENE_PLAN_SCHEMA)


def _outline_entry(chapter_no=1):
    return {
        "chapter_no": chapter_no,
        "goal": "主角初入宗门，立威",
        "conflict": "被外门弟子刁难",
        "escalation": "对方叫来师兄围堵",
        "reward_if_any": "当众击败对手，获得关注",
        "end_hook": "长老出现，目光落在主角身上",
    }


def _outline(entries):
    return {"id": "OUTLINE-00001", "kind": "novel_outline",
            "first_30_chapters": entries}


_BASE_KW = dict(task_id="TASK-00001", chapter_no=1, goal="draft chapter 1",
                participants=["CHR-00001"], derived_from=["EVT-00001@v1"],
                source_version=1)


# --------------------------------------------------------------------------- #
# build_chapter_ir is a deterministic projection                              #
# --------------------------------------------------------------------------- #
def test_ir_is_deterministic():
    kw = dict(_BASE_KW, outline=_outline([_outline_entry(1)]))
    a = build_chapter_ir(**kw)
    b = build_chapter_ir(**kw)
    assert a == b
    assert a["content_hash"] == b["content_hash"]
    assert a["content_hash"].startswith("sha256:")


def test_ir_validates_against_contract():
    ir = build_chapter_ir(**dict(_BASE_KW, outline=_outline([_outline_entry(1)])))
    _ir_validator().validate(ir)


def test_outline_intent_flows_into_ir_beats_and_payoff():
    ir = build_chapter_ir(**dict(_BASE_KW, outline=_outline([_outline_entry(1)])))
    roles = [b["role"] for b in ir["beats"]]
    assert roles == ["setup", "escalation", "turn", "reward", "exit_hook"]
    assert ir["intent"] == "主角初入宗门，立威"
    assert ir["dramatic_question"] == "被外门弟子刁难"
    # the promised reward becomes the grounded payoff_target
    assert ir["payoff_target"]["promise"] == "当众击败对手，获得关注"
    assert ir["payoff_target"]["kind"] == "reward"
    # the turn beat carries a turning_point op; the exit_hook beat carries a hook
    turn = next(b for b in ir["beats"] if b["role"] == "turn")
    assert turn.get("turning_point")
    hook = next(b for b in ir["beats"] if b["role"] == "exit_hook")
    assert hook.get("exit_hook") == "长老出现，目光落在主角身上"


# --------------------------------------------------------------------------- #
# N100-072: long-arc coordinate de-templates the valence curve (GAP-B)        #
# --------------------------------------------------------------------------- #
def _coord(chapter_no, position_in_volume, volume_span, chapters_to_volume_climax,
           *, is_volume_climax=False, is_paywall=False):
    return {
        "chapter_no": chapter_no,
        "position_in_volume": position_in_volume,
        "volume_span": volume_span,
        "chapters_to_volume_climax": chapters_to_volume_climax,
        "is_volume_climax": is_volume_climax,
        "is_paywall": is_paywall,
    }


def test_no_long_arc_coord_is_byte_identical():
    # Default None must not perturb the fold — the whole non-v10 path relies on it.
    kw = dict(_BASE_KW, outline=_outline([_outline_entry(1)]))
    without = build_chapter_ir(**kw)
    explicit_none = build_chapter_ir(**dict(kw, long_arc_coord=None))
    assert without == explicit_none
    assert without["content_hash"] == explicit_none["content_hash"]


def test_long_arc_coord_shifts_valence_and_still_validates():
    entry = _outline_entry(1)
    base = build_chapter_ir(**dict(_BASE_KW, outline=_outline([entry])))
    near_climax = build_chapter_ir(**dict(
        _BASE_KW, outline=_outline([entry]),
        long_arc_coord=_coord(10, 10, 11, 1, is_volume_climax=False)))
    base_peak = max(b["emotion_shift"]["to"] for b in base["beats"] if "emotion_shift" in b)
    near_peak = max(b["emotion_shift"]["to"] for b in near_climax["beats"] if "emotion_shift" in b)
    # a chapter near its volume climax reads hotter than the flat table baseline
    assert near_peak > base_peak
    # still a valid IR (valence stayed inside the schema band after the shift)
    _ir_validator().validate(near_climax)
    # and it lowers to a schema-valid scene plan
    _sp_validator().validate(lower_to_scene_plan(near_climax))


def test_long_arc_breaks_the_flat_peak_loop():
    # The core GAP-B claim: identical outline entries across chapters, but distinct
    # long-arc positions produce distinct chapter peaks — not one repeated value.
    entry = _outline_entry(1)
    coords = [
        _coord(1, 1, 11, 10),                       # volume opener, far from climax
        _coord(6, 6, 11, 5),                        # mid-volume, ramping
        _coord(11, 11, 11, 0, is_volume_climax=True),  # the climax chapter
        _coord(12, 1, 11, 10, is_paywall=True),     # next-volume paywall opener
    ]
    peaks = []
    for c in coords:
        ir = build_chapter_ir(**dict(_BASE_KW, outline=_outline([entry]), long_arc_coord=c))
        peaks.append(max(b["emotion_shift"]["to"] for b in ir["beats"] if "emotion_shift" in b))
    assert len(set(peaks)) >= 3          # broke the single-value loop
    assert peaks[2] == max(peaks)        # the climax chapter is the hottest
    # every beat teaches the reader something OR asks a question (anti-注水)
    for b in ir["beats"]:
        assert b.get("information_gain") or b.get("reader_question") or b.get("exit_hook")


def test_ir_degrades_without_outline_entry():
    # outline present but no entry for chapter 2 -> single setup beat, no payoff
    ir = build_chapter_ir(**dict(_BASE_KW, task_id="TASK-00002", chapter_no=2,
                                 goal="draft chapter 2: 事件2",
                                 outline=_outline([_outline_entry(1)])))
    _ir_validator().validate(ir)
    assert len(ir["beats"]) == 1
    assert ir["beats"][0]["role"] == "setup"
    assert ir["intent"] == "draft chapter 2: 事件2"
    assert "payoff_target" not in ir
    assert ir["outline_ref"] is None


def test_ir_degrades_with_no_outline_at_all():
    ir = build_chapter_ir(**dict(_BASE_KW, outline=None))
    _ir_validator().validate(ir)
    assert len(ir["beats"]) == 1
    assert "payoff_target" not in ir
    assert ir["outline_ref"] is None


# --------------------------------------------------------------------------- #
# lowering: Chapter IR -> scene-plan v2                                        #
# --------------------------------------------------------------------------- #
def test_lowering_produces_valid_scene_plan_v2():
    ir = build_chapter_ir(**dict(_BASE_KW, outline=_outline([_outline_entry(1)])))
    plan = lower_to_scene_plan(ir)
    _sp_validator().validate(plan)
    # one scene per IR beat, same order
    assert [s["beat"] for s in plan["scenes"]] == [b["role"] for b in ir["beats"]]
    assert plan["ir_ref"] == "ir-TASK-00001"


def test_lowering_is_deterministic():
    ir = build_chapter_ir(**dict(_BASE_KW, outline=_outline([_outline_entry(1)])))
    assert lower_to_scene_plan(ir) == lower_to_scene_plan(ir)


def test_lowering_surfaces_v2_narrative_ops():
    ir = build_chapter_ir(**dict(_BASE_KW, outline=_outline([_outline_entry(1)])))
    plan = lower_to_scene_plan(ir)
    setup = plan["scenes"][0]
    # v2 fields the drafter reads to avoid 注水 / to plant curiosity
    assert setup.get("information_gain")
    assert setup.get("reader_question")
    # emotion_shift.to lowered to scene emotion.valence
    assert isinstance(setup["emotion"]["valence"], int)
    # turning_point lowered to the turn scene's `turn`
    turn = next(s for s in plan["scenes"] if s["beat"] == "turn")
    assert turn.get("turn")


def test_render_ir_is_compact_and_ordered():
    ir = build_chapter_ir(**dict(_BASE_KW, outline=_outline([_outline_entry(1)])))
    text = render_chapter_ir(ir)
    assert "本章意图" in text
    assert "payoff" in text  # the grounded promise is shown to the drafter
    positions = [text.index(f"{i}.") for i in range(1, len(ir["beats"]) + 1)]
    assert positions == sorted(positions)


# --------------------------------------------------------------------------- #
# the IR grounds the quality judge's promise_delivery                         #
# --------------------------------------------------------------------------- #
def test_payoff_target_grounds_judge_prompt():
    ir = build_chapter_ir(**dict(_BASE_KW, outline=_outline([_outline_entry(1)])))
    pkg = {"task": {"goal": "g"}, "context": {}}
    art = {"body": "正文"}
    ungrounded = build_judge_prompt(art, pkg)
    grounded = build_judge_prompt(art, pkg, grounding=ir["payoff_target"])
    assert ungrounded != grounded
    assert "当众击败对手，获得关注" in grounded
    assert "promise_delivery" in grounded
    # no payoff (degraded chapter) => ungrounded, byte-identical prompt
    ir2 = build_chapter_ir(**dict(_BASE_KW, outline=None))
    assert build_judge_prompt(art, pkg, grounding=ir2.get("payoff_target")) == ungrounded


# --------------------------------------------------------------------------- #
# v4 serial: end-to-end, persists IR + scene plan, never gates                #
# --------------------------------------------------------------------------- #
def _w(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


def _scaffold(root: Path, n_events=3):
    facts = root / "registry" / "facts"
    meta = root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    _w(facts / "timelines" / "TML-00001.yaml", {
        "id": "TML-00001", "name": "主线", "status": "active",
        "fact_version": 1, "kind": "main"})
    _w(facts / "characters" / "CHR-00001.yaml", {
        "id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1})
    for i in range(1, n_events + 1):
        _w(facts / "events" / f"EVT-{i:05d}.yaml", {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active",
            "fact_version": 1, "timeline": "TML-00001", "sequence_index": i,
            "participants": ["CHR-00001"],
            "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []),
            "effects": ([f"EVT-{i+1:05d}"] if i < n_events else []),
            "summary": f"第{i}章的核心事件"})
    _w(root / "sources" / "novel-brain.yaml", {
        "id": "BRAIN-00001", "kind": "novel_brain", "version": "1.0",
        "mission": "让读者一口气追到天亮",
        "genre": {"primary": "玄幻", "channel": "男频"},
        "target_reader": {"who": "18-30岁男性"},
        "promise": "每三章一个高潮",
        "writing_style": {"voice": "冷峻克制的第三人称", "pov": "第三人称限知"},
        "forbidden_style": ["注水"]})


def _run(root, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "build-serial", **kw)


def test_v4_serial_produces_all_chapters_and_never_gates(tmp_path):
    _scaffold(tmp_path, n_events=3)
    outline = _outline([_outline_entry(1), _outline_entry(2), _outline_entry(3)])
    r = _run(tmp_path, prompt_version="4.0.0", outline=outline)
    assert r.produced == 3
    assert r.skipped == 0
    assert r.gating is False


def test_v4_persists_chapter_ir_and_scene_plan(tmp_path):
    _scaffold(tmp_path, n_events=2)
    outline = _outline([_outline_entry(1), _outline_entry(2)])
    _run(tmp_path, prompt_version="4.0.0", outline=outline)
    index = derived._load_index(tmp_path).get("artifacts", [])
    cats = {e["category"] for e in index}
    assert "chapter-ir" in cats
    assert "scene-plan" in cats
    # both IR and its lowered scene plan are on disk and validate
    ir_entry = next(e for e in index if e["category"] == "chapter-ir")
    ir = json.loads((tmp_path / ir_entry["path"]).read_text(encoding="utf-8"))
    _ir_validator().validate(ir)
    sp_entry = next(e for e in index if e["category"] == "scene-plan")
    sp = json.loads((tmp_path / sp_entry["path"]).read_text(encoding="utf-8"))
    _sp_validator().validate(sp)
    assert sp["ir_ref"].startswith("ir-")


def test_v4_degrades_without_outline(tmp_path):
    _scaffold(tmp_path, n_events=3)
    r = _run(tmp_path, prompt_version="4.0.0", outline=None)
    assert r.produced == 3
    assert r.gating is False


def test_v3_unaffected_by_ir_layer(tmp_path):
    # v3 must be byte-identical with or without the 4.2 IR layer existing: the v4
    # branch only activates for major=="4", so v3 drafts do not change.
    _scaffold(tmp_path, n_events=3)
    outline = _outline([_outline_entry(1), _outline_entry(2), _outline_entry(3)])
    a = _run(tmp_path, prompt_version="3.0.0", outline=outline)

    _scaffold(tmp_path, n_events=3)
    b = _run(tmp_path, prompt_version="3.0.0", outline=outline)
    assert [c.draft_hash for c in a.chapters] == [c.draft_hash for c in b.chapters]
