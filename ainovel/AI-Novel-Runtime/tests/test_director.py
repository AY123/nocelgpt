from __future__ import annotations

import json

from runtime.director import (
    build_chapter_objective, build_director_brief, build_director_critique,
    build_rewrite_decision, build_version_comparison, build_version_selection,
    validate_chapter_objective, validate_director_brief, validate_rewrite_decision,
    validate_director_critique, validate_version_comparison, validate_version_selection,
)


def test_chapter_objective_validates():
    obj = build_chapter_objective(chapter_id="TASK-00018", narrative_ir={"id": "NIR-00012"})
    assert validate_chapter_objective(obj) == []
    assert obj["kind"] == "chapter_objective"
    assert obj["chapter_id"] == "TASK-00018"


def test_director_brief_validates():
    obj = build_chapter_objective(chapter_id="TASK-00018", narrative_ir={"id": "NIR-00012"})
    brief = build_director_brief(chapter_id="TASK-00018", objective=obj)
    assert validate_director_brief(brief) == []
    assert brief["kind"] == "director_brief"
    assert brief["objective_ref"] == obj["id"]


def test_critique_compare_select_and_rewrite_roundtrip():
    obj = build_chapter_objective(chapter_id="TASK-00018")
    brief = build_director_brief(chapter_id="TASK-00018", objective=obj)
    critique = build_director_critique(chapter_id="TASK-00018")
    rewrite = build_rewrite_decision(chapter_id="TASK-00018", critique=critique, objective=obj)
    assert validate_rewrite_decision(rewrite) == []
    cmp = build_version_comparison(chapter_id="TASK-00018", versions=[{"version_id": "a"}, {"version_id": "b"}])
    sel = build_version_selection(chapter_id="TASK-00018", comparison=cmp)
    assert cmp["winner"] == "a"
    assert sel["selected_version"] == "a"
    assert brief["objective_ref"] == obj["id"]


def test_critique_comparison_selection_validate_against_schema():
    crit = build_director_critique(chapter_id="TASK-00018")
    assert validate_director_critique(crit) == []
    cmp = build_version_comparison(chapter_id="TASK-00018", versions=[{"version_id": "a"}, {"version_id": "b"}])
    assert validate_version_comparison(cmp) == []
    sel = build_version_selection(chapter_id="TASK-00018", comparison=cmp)
    assert validate_version_selection(sel) == []


def test_every_director_artifact_carries_structural_consts():
    obj = build_chapter_objective(chapter_id="TASK-00018")
    brief = build_director_brief(chapter_id="TASK-00018", objective=obj)
    crit = build_director_critique(chapter_id="TASK-00018")
    rwd = build_rewrite_decision(chapter_id="TASK-00018", critique=crit, objective=obj)
    cmp = build_version_comparison(chapter_id="TASK-00018", versions=[{"version_id": "a"}])
    sel = build_version_selection(chapter_id="TASK-00018", comparison=cmp)
    for art in (obj, brief, crit, rwd, cmp, sel):
        assert art["gating"] is False, art["kind"]
        assert art["authority"] == "human", art["kind"]


def test_comparison_uses_supplied_scores_not_a_fabricated_scale():
    cmp = build_version_comparison(chapter_id="TASK-00018", versions=[
        {"version_id": "a", "director_score": 10, "before_text": "甲", "after_text": "甲乙", "before_review": {"overall_verdict": "pass", "scores": {"qa": 0.6}}, "after_review": {"overall_verdict": "pass", "scores": {"qa": 0.9}}},
        {"version_id": "b", "director_score": 42, "before_text": "甲乙", "after_text": "甲乙丙丁", "before_review": {"overall_verdict": "revise", "scores": {"qa": 0.4}}, "after_review": {"overall_verdict": "pass", "scores": {"qa": 0.8}}},
    ])
    assert cmp["winner"] == "b"
    assert "summary" in cmp and "risk_summary" in cmp and "pipeline_decision" in cmp
    assert cmp["summary"]["headline"].startswith("改动率")
    assert cmp["summary"]["recommendation"] in {"accept", "revise", "rollback"}
    assert cmp["summary"]["editorial"]["editorial_verdict"] in {"accept", "revise"}
    assert cmp["pipeline_decision"]["action"] in {"advance", "revise", "review"}
    assert cmp["versions"][0]["diff_summary"]["change_rate_percent"] > 0
    assert cmp["versions"][0]["qa_change"]["score_delta"]["qa"] == 0.3


def test_winner_tie_break_prefers_earlier_input_order():
    cmp = build_version_comparison(chapter_id="TASK-00018", versions=[
        {"version_id": "first", "director_score": 10},
        {"version_id": "second", "director_score": 10},
        {"version_id": "third", "director_score": 8},
    ])
    assert cmp["winner"] == "first"
    assert cmp["selection_policy"]["tie_break"] == "earlier_input_order"
    assert cmp["selection_metadata"]["tie_break_applied"] is True
    assert cmp["selection_metadata"]["winner_index"] == 0
    assert [r["version_id"] for r in cmp["selection_metadata"]["ranking"]] == ["first", "second", "third"]


def test_comparison_handles_unscored_versions_with_stable_order():
    cmp = build_version_comparison(chapter_id="TASK-00018", versions=[
        {"version_id": "x"}, {"version_id": "y"}, {"version_id": "z"},
    ])
    assert cmp["winner"] == "x"
    assert [v["score"] for v in cmp["versions"]] == [0, -1, -2]
    assert cmp["selection_metadata"]["tie_break_applied"] is False


def test_director_rides_envelope_not_the_sealed_draft():
    from runtime.execution.envelope import wrap, unwrap
    draft = {"kind": "chapter_draft", "content_hash": "sha256:" + "0" * 64}
    director = {"chapter_id": "TASK-1", "selected_version": "sha256:abc"}
    env = wrap(dict(draft), manifest=None, director=director)
    assert env["director"] == director
    assert "director" not in unwrap(env)
    env2 = wrap(dict(draft), manifest=None)
    assert "director" not in env2
