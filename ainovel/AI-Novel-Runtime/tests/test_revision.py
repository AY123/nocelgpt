import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.execution.quality_center import llm_quality_judge, SCORE_DIMENSIONS, LOWER_IS_BETTER
from runtime.execution.revision import (
    build_rewrite_prompt,
    revise_until,
    rewrite_once,
)


class ScriptedModel:
    """Returns a fixed sequence of texts on successive .generate() calls."""

    model_id = "scripted-v1"

    def __init__(self, texts):
        self._texts = list(texts)
        self._i = 0

    def generate(self, prompt: str):
        text = self._texts[min(self._i, len(self._texts) - 1)]
        self._i += 1

        class _Out:
            pass
        o = _Out()
        o.text = text
        o.model_id = "scripted-v1"
        o.model_kind = "llm"
        return o


class BrokenModel:
    model_id = "broken-v1"

    def generate(self, prompt: str):
        raise RuntimeError("boom")


def _scores(**overrides):
    base = {d: 60 for d in SCORE_DIMENSIONS}
    for d in LOWER_IS_BETTER:       # risk dims: lower is better, so a passing value is low
        base[d] = 20
    base.update(overrides)
    return base


def _report_json(scores, revision_plan=None):
    return json.dumps({
        "scores": scores,
        "dimensions": [{"name": d, "score": s} for d, s in scores.items()],
        "revision_plan": revision_plan or [],
        "predictions": {"subscription": 60, "retention": 60, "reader_satisfaction": 60},
    }, ensure_ascii=False)


ARTIFACT = {
    "task_id": "TASK-00001",
    "body": "原始正文：主角抵达小镇，遇见神秘旅人。",
    "content_hash": "sha256:" + "0" * 64,
    "provenance": {"package_hash": "sha256:" + "a" * 64,
                   "derived_from": ["CHR-00001@v1"], "source_version": 1},
}
PACKAGE = {
    "task": {"goal": "draft chapter 1", "capability": "ChapterDraft", "task_id": "TASK-00001"},
    "content_hash": "sha256:" + "a" * 64,
    "provenance": {"derived_from": ["CHR-00001@v1"], "source_version": 1},
    "context": {"characters": [{"id": "CHR-00001", "name": "Edric", "notes": "流亡骑士"}]},
}

LOW_PLAN = [{"dimension": "reward_density", "issue": "无爽点",
             "action": "加一次小胜", "priority": "high"}]


def revision_schema() -> dict:
    path = (Path(__file__).resolve().parents[2]
            / "AI-Novel-Standard" / "contracts" / "revision-session.schema.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_rewrite_once_produces_new_hash_and_wordcount():
    model = ScriptedModel(["修订后的正文，主角在中段打赢了一场小冲突，赢得读者认同。"])
    revised = rewrite_once(model, ARTIFACT, PACKAGE, LOW_PLAN)
    assert revised is not None
    assert revised["content_hash"] != ARTIFACT["content_hash"]   # rewrite changed the artifact
    assert revised["word_count"] > 0
    assert revised["capability"] == "ChapterDraft"
    # provenance is carried from the original draft
    assert revised["provenance"]["derived_from"] == ["CHR-00001@v1"]


def test_rewrite_once_degrades_to_none_on_error():
    assert rewrite_once(BrokenModel(), ARTIFACT, PACKAGE, LOW_PLAN) is None


def test_loop_detects_targeted_improvement():
    # Judge: round0 low reward_density (flagged), after-rewrite high.
    judge_model = ScriptedModel([
        _report_json(_scores(reward_density=55), LOW_PLAN),   # initial
        _report_json(_scores(reward_density=85), []),          # after round 1
    ])
    judge = llm_quality_judge(judge_model)
    rewrite_model = ScriptedModel(["修订稿：主角中段打赢一场，兑现了爽点。"])

    result = revise_until(judge, rewrite_model, ARTIFACT, PACKAGE, max_rounds=3)
    session = result.session

    assert len(session.rounds) == 1
    rnd = session.rounds[0]
    assert "reward_density" in rnd["targeted_dimensions"]
    assert rnd["scores_before"]["reward_density"] == 55
    assert rnd["scores_after"]["reward_density"] == 85
    assert "reward_density" in rnd["improved"]
    assert rnd["draft_hash_before"] != rnd["draft_hash_after"]
    assert session.verdict == "improved"
    assert result.final_report["scores"]["reward_density"] == 85


def test_loop_stops_when_all_dimensions_pass_initially():
    judge = llm_quality_judge(ScriptedModel([_report_json(_scores(**{d: 90 for d in SCORE_DIMENSIONS if d not in LOWER_IS_BETTER}))]))
    # risk dims already pass at 20 (<=20). All others 90 >= 80.
    result = revise_until(judge, ScriptedModel(["unused"]), ARTIFACT, PACKAGE)
    assert result.session.terminate_reason == "all_dimensions_pass"
    assert result.session.rounds == []


def test_loop_stops_on_no_improvement():
    # Rewrite does not move the flagged dim → controller stops rather than burn budget.
    judge_model = ScriptedModel([
        _report_json(_scores(reward_density=55), LOW_PLAN),   # initial
        _report_json(_scores(reward_density=55), LOW_PLAN),   # after round 1 (no gain)
    ])
    judge = llm_quality_judge(judge_model)
    result = revise_until(judge, ScriptedModel(["没有真正改动的稿子"]), ARTIFACT, PACKAGE, max_rounds=3)
    assert result.session.terminate_reason == "no_improvement"
    assert len(result.session.rounds) == 1


def test_loop_respects_max_rounds():
    # Every round improves a little but never reaches threshold → capped at max_rounds.
    judge_model = ScriptedModel([
        _report_json(_scores(reward_density=50), LOW_PLAN),
        _report_json(_scores(reward_density=60), LOW_PLAN),
        _report_json(_scores(reward_density=68), LOW_PLAN),
        _report_json(_scores(reward_density=74), LOW_PLAN),
    ])
    judge = llm_quality_judge(judge_model)
    rewrite_model = ScriptedModel(["稿1", "稿2", "稿3"])
    result = revise_until(judge, rewrite_model, ARTIFACT, PACKAGE, max_rounds=3)
    assert result.session.terminate_reason == "max_rounds"
    assert len(result.session.rounds) == 3
    assert result.session.verdict == "improved"


def test_gating_invariant_always_false():
    judge = llm_quality_judge(ScriptedModel([_report_json(_scores(reward_density=55), LOW_PLAN),
                                             _report_json(_scores(reward_density=85), [])]))
    result = revise_until(judge, ScriptedModel(["改稿"]), ARTIFACT, PACKAGE)
    assert result.session.gating is False


def test_degraded_judge_short_circuits():
    judge = llm_quality_judge(ScriptedModel(["模型今天不输出JSON"]))
    result = revise_until(judge, ScriptedModel(["x"]), ARTIFACT, PACKAGE)
    assert result.session.terminate_reason == "degraded"
    assert result.session.verdict == "degraded"


def test_session_validates_against_contract():
    judge_model = ScriptedModel([
        _report_json(_scores(reward_density=55), LOW_PLAN),
        _report_json(_scores(reward_density=85), []),
    ])
    judge = llm_quality_judge(judge_model)
    result = revise_until(judge, ScriptedModel(["改稿"]), ARTIFACT, PACKAGE)
    schema = revision_schema()
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(result.session.to_dict()))
    assert errors == [], [e.message for e in errors]


def test_rewrite_prompt_carries_plan_and_facts():
    prompt = build_rewrite_prompt(ARTIFACT, PACKAGE, LOW_PLAN)
    assert "Edric" in prompt              # bound fact reached the rewriter
    assert "加一次小胜" in prompt          # revision action reached the rewriter
    assert ARTIFACT["body"][:8] in prompt # original prose is present
