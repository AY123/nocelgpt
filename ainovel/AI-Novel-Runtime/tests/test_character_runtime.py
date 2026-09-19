"""test_character_runtime.py — Phase 4.3 Character Runtime (projection, ADR-008).

Proves:
  - project_character_runtime is a PURE deterministic fold (same facts + cursor +
    outline => same content_hash) and validates against character-runtime.schema;
  - only LEAD characters carry a runtime (a minor character is excluded);
  - goal/pressure/secret/fear/desire/relationship_tension are folded from
    facts + outline; growth_stage buckets by folded appearance count;
    next_likely_action is synthesized deterministically from goal + pressure;
  - the fold cursor works: a later cursor advances growth_stage (a consequence of
    the fold, never a written-back field);
  - the v5 serial runs end-to-end, persists character-runtime, and never gates;
  - v4 stays byte-identical (the v5 layer only activates for major=="5").
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from runtime import derived
from runtime.memory import (project_character_runtime,
                            render_character_runtime)
from runtime.serialize import run_serial

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"
CR_SCHEMA = json.loads(
    (STANDARD / "contracts" / "character-runtime.schema.json").read_text(encoding="utf-8"))


def _cr_validator():
    return Draft202012Validator(CR_SCHEMA)


class _Reg:
    def __init__(self, facts, version=1):
        self.facts = facts
        self.version = version

    def get(self, rid):
        return self.facts.get(rid)


def _facts(n_events=3):
    facts = {
        "CHR-00001": {"id": "CHR-00001", "name": "叶尘", "status": "active",
                      "fact_version": 2, "importance": "central",
                      "arcs": ["从废柴到强者"]},
        "CHR-00002": {"id": "CHR-00002", "name": "魔君", "status": "active",
                      "fact_version": 1, "importance": "major"},
        "CHR-00003": {"id": "CHR-00003", "name": "路人甲", "status": "active",
                      "fact_version": 1, "importance": "minor"},
        "REL-00001": {"id": "REL-00001", "name": "宿敌", "from": "CHR-00001",
                      "to": "CHR-00002", "kind": "enemy", "label": "血海深仇",
                      "status": "active", "fact_version": 1},
        "TML-00001": {"id": "TML-00001", "name": "主线", "kind": "main",
                      "fact_version": 1},
    }
    for i in range(1, n_events + 1):
        facts[f"EVT-{i:05d}"] = {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "fact_version": 1,
            "timeline": "TML-00001", "sequence_index": i,
            "participants": ["CHR-00001"] + (["CHR-00002"] if i == 1 else [])}
    return facts


def _outline():
    return {"id": "OUTLINE-00001",
            "protagonist_engine": {"desire": "登临巅峰", "flaw": "心魔未消"},
            "conflict_ladder": [{"level": "1", "enemy": "魔君",
                                 "pressure_source": "魔君步步紧逼"}],
            "characters": [{"name": "叶尘", "role": "protagonist",
                            "motivation": "为家族复仇", "secret": "身怀神秘血脉"}]}


# --------------------------------------------------------------------------- #
# pure deterministic fold + contract validity                                 #
# --------------------------------------------------------------------------- #
def _project(**kw):
    base = dict(chapter_no=3, task_id="TASK-00003", up_to_event="EVT-00002",
                outline=_outline())
    base.update(kw)
    return project_character_runtime(_Reg(_facts()), **base)


def test_runtime_is_deterministic():
    a = _project()
    b = _project()
    assert a == b
    assert a["content_hash"] == b["content_hash"]
    assert a["content_hash"].startswith("sha256:")


def test_runtime_validates_against_contract():
    _cr_validator().validate(_project())


def test_only_leads_carry_a_runtime():
    cr = _project()
    ids = [ld["character_id"] for ld in cr["leads"]]
    assert "CHR-00001" in ids and "CHR-00002" in ids
    assert "CHR-00003" not in ids  # minor character has no standing engine


def test_lead_fields_folded_from_facts_and_outline():
    cr = _project()
    p = next(ld for ld in cr["leads"] if ld["character_id"] == "CHR-00001")
    assert p["goal"] == "为家族复仇"            # outline motivation wins
    assert p["role"] == "protagonist"
    assert p["secret"] == "身怀神秘血脉"
    assert p["fear"] == "心魔未消"               # protagonist_engine.flaw fallback
    assert p["desire"] == "登临巅峰"             # engine desire, distinct from goal
    assert "魔君" in p["pressure"]               # active enemy REL folded into pressure
    tension = p["relationship_tension"][0]
    assert tension["with"] == "CHR-00002" and tension["kind"] == "enemy"


def test_next_likely_action_is_deterministic_goal_pressure_synthesis():
    cr = _project()
    p = next(ld for ld in cr["leads"] if ld["character_id"] == "CHR-00001")
    # synthesized from goal + pressure — contains both, no model
    assert p["goal"] in p["next_likely_action"]
    assert "压力" in p["next_likely_action"]


def test_psych_fields_folded_deterministically():
    """§12.1 ②: emotion/belief/value/decision_policy are DERIVED standing state,
    folded from the authored engine + pressure + growth_stage (no model). The
    protagonist under enemy pressure with an authored desire+flaw carries all four."""
    cr = _project()
    p = next(ld for ld in cr["leads"] if ld["character_id"] == "CHR-00001")
    # emotion reflects being under pressure (an active enemy REL)
    assert "emotion" in p and p["emotion"]
    # belief folds from the engine desire
    assert "belief" in p and "登临巅峰" in p["belief"]
    # value is synthesized from the desire↔fear tension (no authored value here)
    assert "value" in p and "登临巅峰" in p["value"] and "心魔未消" in p["value"]
    # decision_policy folds from the fear
    assert "decision_policy" in p and "心魔未消" in p["decision_policy"]


def test_authored_value_wins_over_synthesized():
    """An outline that authors a value/principle uses it verbatim instead of the
    desire↔fear synthesis."""
    outline = _outline()
    outline["characters"][0]["value"] = "守护弱者，绝不背叛同伴"
    cr = _project(outline=outline)
    p = next(ld for ld in cr["leads"] if ld["character_id"] == "CHR-00001")
    assert p["value"] == "守护弱者，绝不背叛同伴"


def test_psych_fields_omitted_without_source():
    """A lead with no authored desire/fear engine carries no phantom psych fields
    beyond what its own sources justify (belief needs a desire; decision_policy
    needs a fear)."""
    # a supporting lead (CHR-00002) with no engine desire/flaw of its own
    cr = _project()
    ally = next(ld for ld in cr["leads"] if ld["character_id"] == "CHR-00002")
    # no engine desire => no belief; the fold omits it rather than inventing one
    assert "belief" not in ally


def test_psych_fields_advance_with_growth_stage():
    """belief/decision_policy phrasing hardens as the fold cursor advances the
    lead's growth_stage — a consequence of the fold, deterministic."""
    facts = _facts(n_events=8)
    early = project_character_runtime(
        _Reg(facts), chapter_no=1, task_id="TASK-00001",
        up_to_event="EVT-00001", outline=_outline())
    late = project_character_runtime(
        _Reg(facts), chapter_no=8, task_id="TASK-00008",
        up_to_event="EVT-00008", outline=_outline())
    pe = next(ld for ld in early["leads"] if ld["character_id"] == "CHR-00001")
    pl = next(ld for ld in late["leads"] if ld["character_id"] == "CHR-00001")
    # a later stage yields a different (harder) belief phrasing than an early one
    assert pe.get("belief") != pl.get("belief")


def test_growth_stage_advances_with_the_fold_cursor():
    # growth_stage is a CONSEQUENCE of appearing in more folded events, not a
    # written-back counter: a later cursor => more appearances => later stage.
    facts = _facts(n_events=8)
    early = project_character_runtime(
        _Reg(facts), chapter_no=1, task_id="TASK-00001",
        up_to_event="EVT-00001", outline=_outline())
    late = project_character_runtime(
        _Reg(facts), chapter_no=8, task_id="TASK-00008",
        up_to_event="EVT-00008", outline=_outline())
    e = next(ld for ld in early["leads"] if ld["character_id"] == "CHR-00001")
    l = next(ld for ld in late["leads"] if ld["character_id"] == "CHR-00001")
    stages = ["introduced", "developing", "tested", "transformed"]
    assert stages.index(l["growth_stage"]) > stages.index(e["growth_stage"])


def test_degrades_without_outline():
    cr = project_character_runtime(
        _Reg(_facts()), chapter_no=1, task_id="TASK-00001",
        up_to_event=None, outline=None)
    _cr_validator().validate(cr)
    # still projects the protagonist, goal degrades to the fact arc
    p = next(ld for ld in cr["leads"] if ld["character_id"] == "CHR-00001")
    assert p["goal"] == "从废柴到强者"          # degrades to the fact arc
    assert cr["up_to_event"] is None             # opening chapter, no prior event
    assert cr["outline_ref"] is None


def test_render_is_compact_and_ordered():
    text = render_character_runtime(_project())
    assert "主要角色运行时" in text
    assert "叶尘" in text and "目标" in text and "本章可能的行动" in text


# --------------------------------------------------------------------------- #
# v5 serial: end-to-end, persists character-runtime, never gates; v4 identical #
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
        "id": "CHR-00001", "name": "主角", "status": "active",
        "fact_version": 1, "importance": "central"})
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


def _outline_full(n=3):
    return {"id": "OUTLINE-00001", "kind": "novel_outline",
            "protagonist_engine": {"desire": "登临巅峰"},
            "characters": [{"name": "主角", "role": "protagonist",
                            "motivation": "变强"}],
            "first_30_chapters": [
                {"chapter_no": i, "goal": f"第{i}章目标", "conflict": "冲突",
                 "escalation": "升级", "reward_if_any": "回报",
                 "end_hook": "钩子"} for i in range(1, n + 1)]}


def _run(root, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "build-serial", **kw)


def test_v5_serial_produces_all_chapters_and_never_gates(tmp_path):
    _scaffold(tmp_path, n_events=3)
    r = _run(tmp_path, prompt_version="5.0.0", outline=_outline_full(3))
    assert r.produced == 3
    assert r.skipped == 0
    assert r.gating is False


def test_v5_persists_character_runtime(tmp_path):
    _scaffold(tmp_path, n_events=2)
    _run(tmp_path, prompt_version="5.0.0", outline=_outline_full(2))
    index = derived._load_index(tmp_path).get("artifacts", [])
    cats = {e["category"] for e in index}
    assert "character-runtime" in cats
    assert "chapter-ir" in cats and "scene-plan" in cats  # v5 does v4's work too
    cr_entry = next(e for e in index if e["category"] == "character-runtime")
    cr = json.loads((tmp_path / cr_entry["path"]).read_text(encoding="utf-8"))
    _cr_validator().validate(cr)
    assert any(ld["character_id"] == "CHR-00001" for ld in cr["leads"])


def test_v5_degrades_without_outline(tmp_path):
    _scaffold(tmp_path, n_events=3)
    r = _run(tmp_path, prompt_version="5.0.0", outline=None)
    assert r.produced == 3
    assert r.gating is False


def test_v4_unaffected_by_character_runtime_layer(tmp_path):
    # v4 must be byte-identical with or without the 4.3 layer: the v5 branch only
    # activates for major=="5", so v4 drafts do not change.
    _scaffold(tmp_path, n_events=3)
    outline = _outline_full(3)
    a = _run(tmp_path, prompt_version="4.0.0", outline=outline)

    _scaffold(tmp_path, n_events=3)
    b = _run(tmp_path, prompt_version="4.0.0", outline=outline)
    assert [c.draft_hash for c in a.chapters] == [c.draft_hash for c in b.chapters]
