"""test_scene_persistence.py — scene plans are persisted as Derived artifacts.

The scene-plan contract declares its home as registry/derived/scene-plan/, but
until now the plan was a transient prompt input. This proves a v3 serial run
writes one scene-plan artifact per chapter there, indexed with a scene- prefixed
id (no collision with the chapter's draft entry), each schema-valid — so
read-side consumers (the dashboard pacing view) can fold them.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from runtime import derived
from runtime.serialize import run_serial

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"
SCENE_SCHEMA = json.loads(
    (STANDARD / "contracts" / "scene-plan.schema.json").read_text(encoding="utf-8"))


def _w(p: Path, o: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(o, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _scaffold(root: Path, n_events=3):
    facts = root / "registry" / "facts"
    meta = root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    _w(facts / "timelines" / "TML-00001.yaml", {
        "id": "TML-00001", "name": "主线", "status": "active", "fact_version": 1, "kind": "main"})
    _w(facts / "characters" / "CHR-00001.yaml", {
        "id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1})
    for i in range(1, n_events + 1):
        _w(facts / "events" / f"EVT-{i:05d}.yaml", {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active", "fact_version": 1,
            "timeline": "TML-00001", "sequence_index": i, "participants": ["CHR-00001"],
            "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []), "summary": f"第{i}章"})
    _w(root / "sources" / "novel-brain.yaml", {
        "id": "BRAIN-00001", "kind": "novel_brain", "version": "1.0", "mission": "追到天亮",
        "genre": {"primary": "玄幻", "channel": "男频"}, "target_reader": {"who": "男性"},
        "promise": "三章一高潮", "writing_style": {"voice": "冷峻", "pov": "第三人称"},
        "forbidden_style": ["注水"]})


def _outline(n):
    return {"id": "OUTLINE-00001", "reward_loop": {"cadence_chapters": 2},
            "first_30_chapters": [
                {"chapter_no": i, "goal": f"目标{i}", "conflict": "冲突",
                 "escalation": "升级", "reward_if_any": "回报", "end_hook": "钩子"}
                for i in range(1, n + 1)]}


class _Out:
    def __init__(self, t): self.text = t; self.model_id = "fake"


class _Model:
    model_id = "fake"
    def generate(self, prompt):
        return _Out(json.dumps({"scenes": [{"index": i, "emotion": {"valence": 40 + i * 10}}
                                           for i in range(1, 6)]}))


def _run(root, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "b", **kw)


def _scene_entries(root):
    return [e for e in derived._load_index(root).get("artifacts", [])
            if e.get("category") == "scene-plan"]


def test_v3_persists_one_scene_plan_per_chapter(tmp_path):
    _scaffold(tmp_path, n_events=3)
    _run(tmp_path, prompt_version="3.0.0", outline=_outline(3), scene_planner_model=_Model())
    entries = _scene_entries(tmp_path)
    assert len(entries) == 3
    # scene- prefixed ids, distinct from the draft entries (which use TASK-*)
    assert sorted(e["id"] for e in entries) == \
        ["scene-TASK-00001", "scene-TASK-00002", "scene-TASK-00003"]
    draft_ids = {e["id"] for e in derived._load_index(tmp_path)["artifacts"]
                 if e["category"] == "drafts"}
    assert draft_ids == {"TASK-00001", "TASK-00002", "TASK-00003"}
    # no id collision between the two categories
    assert draft_ids.isdisjoint({e["id"] for e in entries})


def test_persisted_scene_plans_are_schema_valid(tmp_path):
    _scaffold(tmp_path, n_events=2)
    _run(tmp_path, prompt_version="3.0.0", outline=_outline(2), scene_planner_model=_Model())
    for e in _scene_entries(tmp_path):
        obj = json.loads((tmp_path / e["path"]).read_text(encoding="utf-8"))
        Draft202012Validator(SCENE_SCHEMA).validate(obj)


def test_bare_skeleton_still_persists(tmp_path):
    # v3 without a scene planner model -> bare skeletons, but still persisted.
    _scaffold(tmp_path, n_events=2)
    _run(tmp_path, prompt_version="3.0.0", outline=_outline(2))
    assert len(_scene_entries(tmp_path)) == 2


def test_v1_persists_no_scene_plan(tmp_path):
    # v1 has no scene layer -> nothing under scene-plan.
    _scaffold(tmp_path, n_events=2)
    _run(tmp_path, prompt_version="1.0.0")
    assert _scene_entries(tmp_path) == []
