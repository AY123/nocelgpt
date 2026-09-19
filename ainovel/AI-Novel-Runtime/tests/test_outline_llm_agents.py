"""test_outline_llm_agents.py — the live-model creative seam for genesis (G.8).

Pins the enrich-never-replace / degrade-never-raise discipline of the outline
LLM agents:
  - a model that returns valid candidate JSON flows its ORIGINAL settings
    (characters + world) into the final outline and the mint import plan;
  - a model that fails (raises / empty / garbage) degrades to the deterministic
    template path — byte-identical to the no-model run;
  - the deterministic gate (check_outline) still governs completeness either way.
"""
from __future__ import annotations

import json

from runtime.outline.workflow import run_outline_bootstrap
from runtime.outline.agents import (propose_candidates, review_candidate,
                                    synthesize_final_outline)
from runtime.outline.llm_agents import LLMCandidateProposer
from runtime.outline.import_plan import build_import_plan


_MERGED = {"genre_signals": ["玄幻"], "reader_rewards": ["实力突破", "打脸翻身"],
           "structure_signals": ["linear"], "originality_guardrails": ["no-copy"]}


class _Out:
    def __init__(self, text):
        self.text = text
        self.model_id = "fake-model"


class FakeModel:
    """Returns a fixed text for every generate() call."""
    model_id = "fake-model"

    def __init__(self, text):
        self._text = text

    def generate(self, prompt):
        return _Out(self._text)


class BoomModel:
    model_id = "boom"

    def generate(self, prompt):
        raise RuntimeError("provider down")


# A well-formed proposer response carrying ORIGINAL characters + world — the
# names/world here must survive into the outline and the mint import plan.
_GOOD_CANDIDATE = {
    "candidates": [{
        "id": "CANDIDATE-A",
        "direction": "商业强钩子升级线",
        "title": "潮汐纪年录",
        "genre": ["玄幻"],
        "logline": "潮民少年觉醒读潮之能，在断岸城的追杀中重建被抹去的名字。",
        "design_focus": ["fast-opening-hook", "progression"],
        "protagonist_engine": {
            "desire": "找回被潮汐抹去的族名",
            "flaw": "不敢承认自己就是灾潮之源",
            "golden_finger": "能听见退潮时遗落之物的记忆",
            "cost": "每听一次，自身一段记忆随潮水退去",
        },
        "power_system": {
            "tiers": ["听潮", "引潮", "驭潮", "镇潮", "定潮"],
            "breakthrough_condition": "亲手安葬一段真相",
            "hard_limits": ["记忆有限", "同一段记忆不可复听"],
        },
        "characters": [
            {"role": "protagonist", "name": "封屿", "arc": "从潮民到定潮者",
             "motivation": "找回族名"},
            {"role": "rival", "name": "沙问澜", "arc": "护潮官的动摇",
             "motivation": "维系断岸城的秩序"},
            {"role": "mentor", "name": "老渡", "arc": "赎清一桩沉海旧案",
             "motivation": "偿还当年的沉默"},
        ],
        "world": {
            "summary": "潮汐会周期性抹去沿岸的名字与记录的原创世界。",
            "rules": ["每次大潮抹去一批姓名", "退潮遗物承载被抹者的记忆",
                      "力量成长必须以自身记忆为代价"],
        },
    }]
}


# ---------------------------------------------------------------------------- #
# Proposer unit: valid JSON parses; failures degrade to the template producer   #
# ---------------------------------------------------------------------------- #
def test_proposer_parses_valid_candidate():
    cands = LLMCandidateProposer(FakeModel(json.dumps(_GOOD_CANDIDATE))).propose(_MERGED)
    assert len(cands) == 1
    assert cands[0]["title"] == "潮汐纪年录"
    assert cands[0]["world"]["rules"]                         # authored world carried
    assert any(c["role"] == "protagonist" for c in cands[0]["characters"])


def test_proposer_degrades_on_model_error():
    assert LLMCandidateProposer(BoomModel()).propose(_MERGED) == propose_candidates(_MERGED)


def test_proposer_degrades_on_garbage():
    assert LLMCandidateProposer(FakeModel("not json at all")).propose(_MERGED) == propose_candidates(_MERGED)


def test_proposer_degrades_on_invalid_candidate():
    # missing golden_finger => not a valid candidate => wholesale fallback
    bad = {"candidates": [{"id": "X", "direction": "d", "title": "t", "genre": ["玄幻"],
                           "logline": "l", "protagonist_engine": {}, "power_system": {}}]}
    assert LLMCandidateProposer(FakeModel(json.dumps(bad))).propose(_MERGED) == propose_candidates(_MERGED)


# ---------------------------------------------------------------------------- #
# Synthesis: authored characters/world win; deterministic candidate keeps default#
# ---------------------------------------------------------------------------- #
def test_authored_settings_flow_into_outline_and_plan():
    cand = _GOOD_CANDIDATE["candidates"][0]
    review = review_candidate(cand, _MERGED)
    outline = synthesize_final_outline([cand], [review], _MERGED, "proj", [])
    names = {c["name"] for c in outline["characters"]}
    assert "封屿" in names and "沙问澜" in names
    assert outline["world"]["summary"].startswith("潮汐")
    # and the mint import plan folds those exact names / rules into candidates
    plan = build_import_plan(outline)
    chr_names = {it["record"]["name"] for it in plan["items"] if it["target_type"] == "Character"}
    assert "封屿" in chr_names
    rule_stmts = [it["record"]["statement"] for it in plan["items"] if it["target_type"] == "WorldRule"]
    assert any("大潮" in s for s in rule_stmts)


def test_deterministic_candidate_keeps_default_cast():
    cands = propose_candidates(_MERGED)
    reviews = [review_candidate(c, _MERGED) for c in cands]
    outline = synthesize_final_outline(cands, reviews, _MERGED, "proj", [])
    names = {c["name"] for c in outline["characters"]}
    assert "林照夜" in names            # hardcoded default retained when candidate has no cast


# ---------------------------------------------------------------------------- #
# Workflow parity: a degrading model must not perturb the deterministic path     #
# ---------------------------------------------------------------------------- #
import tempfile
from pathlib import Path


def _project_with_reference() -> Path:
    proj = Path(tempfile.mkdtemp(prefix="outline-llm-"))
    (proj / "sources" / "reference-novels").mkdir(parents=True)
    meta = proj / "registry" / "_meta"
    meta.mkdir(parents=True)
    meta.joinpath("project-id").write_text("novel\n", encoding="utf-8")
    meta.joinpath("registry-version").write_text("1\n", encoding="utf-8")
    meta.joinpath("standard.pin").write_text("2.0.0\n", encoding="utf-8")
    (proj / "sources" / "reference-novels" / "ref.txt").write_text(
        "少年在废城遭遇灵气危机，觉醒传承后逃离宗门追杀。"
        "他发现秘密线索，突破境界并赢得第一次胜利。" * 3, encoding="utf-8")
    return proj


def _outline_json(run_dir_result, proj) -> dict:
    return json.loads((proj / run_dir_result.outline_json).read_text(encoding="utf-8"))


def test_degrading_model_is_byte_identical_to_no_model():
    import shutil
    proj_a, proj_b = _project_with_reference(), _project_with_reference()
    try:
        r_none = run_outline_bootstrap(proj_a, run_id="fixed")
        r_boom = run_outline_bootstrap(proj_b, run_id="fixed", model=BoomModel())
        assert r_none.ok and r_boom.ok
        # The final outline is identical modulo provenance (which carries the
        # project's own reference sources); compare the authored content.
        o_none, o_boom = _outline_json(r_none, proj_a), _outline_json(r_boom, proj_b)
        for key in ("title", "characters", "world", "protagonist_engine",
                    "power_system", "first_30_chapters", "conflict_ladder"):
            assert o_none[key] == o_boom[key]
    finally:
        shutil.rmtree(proj_a, ignore_errors=True)
        shutil.rmtree(proj_b, ignore_errors=True)


def test_live_model_authors_settings_through_workflow():
    import shutil
    proj = _project_with_reference()
    try:
        r = run_outline_bootstrap(proj, model=FakeModel(json.dumps(_GOOD_CANDIDATE)))
        assert r.ok
        outline = _outline_json(r, proj)
        assert outline["title"] == "潮汐纪年录"
        assert "封屿" in {c["name"] for c in outline["characters"]}
    finally:
        shutil.rmtree(proj, ignore_errors=True)
