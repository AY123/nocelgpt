"""test_scene_plan.py — the Scene DSL layer between outline and chapter draft.

Proves: plan_scenes is a deterministic projection (same inputs => same artifact
+ content_hash), its output validates against scene-plan.schema.json, outline
intent (first_30_chapters) flows into the beat skeleton, a chapter with no
outline entry degrades to a single goal-bearing scene (advisory, ADR-003), and
the v3 serial runs end-to-end without gating while v2 stays byte-identical.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from runtime import registry_loader
from runtime.scene import plan_scenes, render_scene_plan
from runtime.serialize import run_serial

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"
SCENE_PLAN_SCHEMA = json.loads(
    (STANDARD / "contracts" / "scene-plan.schema.json").read_text(encoding="utf-8"))


def _validator():
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


# --------------------------------------------------------------------------- #
# plan_scenes is a deterministic projection                                    #
# --------------------------------------------------------------------------- #
def test_plan_is_deterministic():
    kw = dict(task_id="TASK-00001", chapter_no=1, goal="draft chapter 1",
              participants=["CHR-00001"], derived_from=["EVT-00001@v1"],
              source_version=1, outline=_outline([_outline_entry(1)]))
    a = plan_scenes(**kw)
    b = plan_scenes(**kw)
    assert a == b
    assert a["content_hash"] == b["content_hash"]
    assert a["content_hash"].startswith("sha256:")


def test_plan_validates_against_contract():
    plan = plan_scenes(
        task_id="TASK-00001", chapter_no=1, goal="draft chapter 1",
        participants=["CHR-00001"], derived_from=["EVT-00001@v1"],
        source_version=1, outline=_outline([_outline_entry(1)]))
    _validator().validate(plan)


def test_outline_intent_flows_into_beats():
    plan = plan_scenes(
        task_id="TASK-00001", chapter_no=1, goal="draft chapter 1",
        participants=["CHR-00001"], derived_from=["EVT-00001@v1"],
        source_version=1, outline=_outline([_outline_entry(1)]))
    beats = [s["beat"] for s in plan["scenes"]]
    # a full outline entry yields setup -> escalation -> turn -> reward -> exit_hook
    assert beats == ["setup", "escalation", "turn", "reward", "exit_hook"]
    assert plan["scenes"][0]["purpose"] == "主角初入宗门，立威"
    assert plan["scenes"][-1]["exit_hook"] == "长老出现，目光落在主角身上"
    assert plan["outline_ref"] == "OUTLINE-00001"


def test_degrades_without_outline_entry():
    # outline present but no entry for chapter 2 -> single goal-bearing scene
    plan = plan_scenes(
        task_id="TASK-00002", chapter_no=2, goal="draft chapter 2: 事件2",
        participants=["CHR-00001"], derived_from=["EVT-00002@v1"],
        source_version=1, outline=_outline([_outline_entry(1)]))
    _validator().validate(plan)
    assert len(plan["scenes"]) == 1
    assert plan["scenes"][0]["beat"] == "setup"
    assert plan["scenes"][0]["purpose"] == "draft chapter 2: 事件2"
    assert plan["outline_ref"] is None


def test_degrades_with_no_outline_at_all():
    plan = plan_scenes(
        task_id="TASK-00001", chapter_no=1, goal="draft chapter 1",
        participants=["CHR-00001"], derived_from=["EVT-00001@v1"],
        source_version=1, outline=None)
    _validator().validate(plan)
    assert len(plan["scenes"]) == 1
    assert plan["outline_ref"] is None


def test_render_is_compact_and_ordered():
    plan = plan_scenes(
        task_id="TASK-00001", chapter_no=1, goal="draft chapter 1",
        participants=["CHR-00001"], derived_from=["EVT-00001@v1"],
        source_version=1, outline=_outline([_outline_entry(1)]))
    text = render_scene_plan(plan)
    assert "本章分镜" in text
    # scenes appear in order 1..N
    positions = [text.index(f"{i}.") for i in range(1, len(plan["scenes"]) + 1)]
    assert positions == sorted(positions)


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


# --------------------------------------------------------------------------- #
# v3 serial runs end-to-end with a scene plan, and never gates (ADR-003)       #
# --------------------------------------------------------------------------- #
def test_v3_serial_produces_all_chapters_and_never_gates(tmp_path):
    _scaffold(tmp_path, n_events=3)
    outline = _outline([_outline_entry(1), _outline_entry(2), _outline_entry(3)])
    r = _run(tmp_path, prompt_version="3.0.0", outline=outline)
    assert r.produced == 3
    assert r.skipped == 0
    assert r.gating is False


def test_v3_serial_degrades_without_outline(tmp_path):
    # v3 with no outline at all: still produces (scene plan degrades to goal).
    _scaffold(tmp_path, n_events=3)
    r = _run(tmp_path, prompt_version="3.0.0", outline=None)
    assert r.produced == 3
    assert r.gating is False


def test_v2_ignores_outline_and_is_unaffected(tmp_path):
    # v2 must not read outline; producing with and without it is identical.
    _scaffold(tmp_path, n_events=3)
    outline = _outline([_outline_entry(1), _outline_entry(2), _outline_entry(3)])
    with_outline = _run(tmp_path, prompt_version="2.0.0", outline=outline)

    _scaffold(tmp_path, n_events=3)
    without = _run(tmp_path, prompt_version="2.0.0", outline=None)

    assert with_outline.produced == without.produced == 3
    hashes_a = [c.draft_hash for c in with_outline.chapters]
    hashes_b = [c.draft_hash for c in without.chapters]
    assert hashes_a == hashes_b

