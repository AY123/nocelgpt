"""test_llm_scene_planner.py — LLM scene-plan enrichment (roadmap P21).

Proves the LLM planner ENRICHES the deterministic skeleton without changing its
structure: it fills pov/emotion/beats_within, but a returned scene count/beat/
participant change is rejected; a bad POV is dropped; a model failure degrades
the whole plan to the skeleton (advisory, ADR-003); and the enriched artifact
still validates against scene-plan.schema.json.
"""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.scene import plan_scenes, render_scene_plan
from runtime.scene.llm_planner import LLMScenePlanner

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = json.loads(
    (STANDARD / "contracts" / "scene-plan.schema.json").read_text(encoding="utf-8"))


class _Out:
    def __init__(self, text): self.text = text; self.model_id = "fake-planner"


class _Model:
    """Fake planner model: returns a fixed enrichment for scene 1, echoing back
    whatever `scenes` payload it was constructed with."""
    model_id = "fake-planner"

    def __init__(self, payload): self._payload = payload

    def generate(self, prompt): return _Out(json.dumps(self._payload))


def _base_plan():
    return plan_scenes(
        task_id="TASK-00001", chapter_no=1, goal="draft chapter 1",
        participants=["CHR-00001"], derived_from=["EVT-00001@v1"],
        source_version=1,
        outline={"id": "OUTLINE-00001", "first_30_chapters": [
            {"chapter_no": 1, "goal": "立威", "conflict": "被刁难",
             "escalation": "围堵", "reward_if_any": "击败", "end_hook": "长老现身"}]})


# --------------------------------------------------------------------------- #
# Enrichment fills detail inside the skeleton                                  #
# --------------------------------------------------------------------------- #
def test_enrich_fills_pov_emotion_beats():
    base = _base_plan()
    model = _Model({"scenes": [
        {"index": 1, "pov": "CHR-00001", "emotion": {"valence": 30, "tone": "紧张"},
         "beats_within": [{"kind": "action", "text": "迈入训练场"},
                          {"kind": "dialogue", "text": "\"你也配？\""}]}]})
    enriched = LLMScenePlanner(model).enrich(base)
    Draft202012Validator(SCHEMA).validate(enriched)
    s1 = enriched["scenes"][0]
    assert s1["pov"] == "CHR-00001"
    assert s1["emotion"] == {"valence": 30, "tone": "紧张"}
    assert len(s1["beats_within"]) == 2
    assert enriched["enrichment"]["degraded"] is False
    assert enriched["enrichment"]["gating"] is False
    assert enriched["enrichment"]["scenes_enriched"] == 1


def test_structure_is_never_changed():
    base = _base_plan()
    n = len(base["scenes"])
    # model tries to add a scene, change a beat, and inject a foreign POV
    model = _Model({"scenes": [
        {"index": 1, "beat": "reward", "pov": "CHR-99999",
         "participants": ["CHR-99999"], "emotion": {"valence": 50}},
        {"index": n + 1, "beat": "setup", "purpose": "smuggled extra scene"}]})
    enriched = LLMScenePlanner(model).enrich(base)
    # scene count unchanged; beats unchanged; foreign POV rejected
    assert len(enriched["scenes"]) == n
    assert [s["beat"] for s in enriched["scenes"]] == [s["beat"] for s in base["scenes"]]
    assert "pov" not in enriched["scenes"][0]          # CHR-99999 not on stage -> dropped
    assert enriched["scenes"][0]["participants"] == base["scenes"][0]["participants"]
    # but the valid emotion still landed
    assert enriched["scenes"][0]["emotion"]["valence"] == 50


def test_bad_pov_dropped_valid_kept():
    base = _base_plan()
    model = _Model({"scenes": [
        {"index": 1, "pov": "CHR-00001",
         "beats_within": [{"kind": "bogus", "text": "x"},
                          {"kind": "interior", "text": "他攥紧了拳"}]}]})
    enriched = LLMScenePlanner(model).enrich(base)
    assert enriched["scenes"][0]["pov"] == "CHR-00001"      # valid POV kept
    beats = enriched["scenes"][0]["beats_within"]
    assert beats == [{"kind": "interior", "text": "他攥紧了拳"}]  # bogus kind dropped


# --------------------------------------------------------------------------- #
# Failure degrades to the skeleton (advisory, ADR-003)                         #
# --------------------------------------------------------------------------- #
def test_model_failure_degrades_to_skeleton():
    base = _base_plan()

    class _Boom:
        model_id = "boom"
        def generate(self, prompt): raise RuntimeError("provider down")

    enriched = LLMScenePlanner(_Boom()).enrich(base)
    Draft202012Validator(SCHEMA).validate(enriched)
    assert enriched["enrichment"]["degraded"] is True
    assert enriched["scenes"] == base["scenes"]        # skeleton scenes unchanged


def test_empty_output_degrades():
    base = _base_plan()
    enriched = LLMScenePlanner(_Model({"scenes": []})).enrich(base)
    assert enriched["enrichment"]["degraded"] is True
    assert enriched["scenes"] == base["scenes"]


def test_enriched_render_shows_emotion_curve():
    base = _base_plan()
    model = _Model({"scenes": [
        {"index": 1, "emotion": {"valence": 20, "tone": "压抑"}},
        {"index": len(base["scenes"]), "emotion": {"valence": 90, "tone": "爽快"}}]})
    enriched = LLMScenePlanner(model).enrich(base)
    text = render_scene_plan(enriched)
    assert "情绪曲线" in text
    assert "20（压抑）" in text and "90（爽快）" in text


def test_skeleton_unchanged_without_model():
    # render of a bare skeleton has no emotion curve line (byte-identical to pre-enrichment)
    base = _base_plan()
    assert "情绪曲线" not in render_scene_plan(base)
    assert "enrichment" not in base


# --------------------------------------------------------------------------- #
# psych-beats arm (§12.1 ② follow-up): the psych block + instruction only      #
# appear when psych is passed, and the arm is recorded in provenance.          #
# --------------------------------------------------------------------------- #
class _PromptCapturingModel:
    model_id = "capture"

    def __init__(self): self.prompt = None

    def generate(self, prompt):
        self.prompt = prompt
        return _Out(json.dumps({"scenes": [{"index": 1, "pov": "CHR-00001"}]}))


def test_generic_arm_has_no_psych_and_records_false():
    base = _base_plan()
    model = _PromptCapturingModel()
    enriched = LLMScenePlanner(model).enrich(base)  # no psych
    assert "内在状态" not in model.prompt and "落地" not in model.prompt
    assert enriched["enrichment"]["psych_beats"] is False
    Draft202012Validator(SCHEMA).validate(enriched)


def test_psych_arm_injects_block_and_instruction_and_records_true():
    base = _base_plan()
    model = _PromptCapturingModel()
    psych = "  ◆ 周洛铭\n      决策倾向：因恐惧而趋于谨慎、回避风险"
    enriched = LLMScenePlanner(model).enrich(base, psych=psych)
    # the block AND the "land it as concrete action" instruction reach the model
    assert "内在状态" in model.prompt
    assert "决策倾向：因恐惧而趋于谨慎" in model.prompt
    assert "转化为该 POV 角色在 beats_within 里的具体" in model.prompt
    assert enriched["enrichment"]["psych_beats"] is True
    Draft202012Validator(SCHEMA).validate(enriched)


def test_blank_psych_is_treated_as_generic():
    # whitespace-only psych must not flip the arm — guards the byte-identical path
    base = _base_plan()
    model = _PromptCapturingModel()
    enriched = LLMScenePlanner(model).enrich(base, psych="   \n  ")
    assert "内在状态" not in model.prompt
    assert enriched["enrichment"]["psych_beats"] is False
