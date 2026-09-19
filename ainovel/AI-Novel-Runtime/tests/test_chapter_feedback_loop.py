from runtime.chapter.types import ChapterIntent, BeatPlan


def test_chapter_intent_can_adjust_length_from_review():
    intent = ChapterIntent(chapter_id="CH-1", chapter_no=1, goal="开篇", chapter_role="opening", target_length_cjk=1200)
    adjusted = intent.adjusted_for_review(
        overall_verdict="revise",
        issues=["too short"],
        scores={"pacing": 0.5},
    )
    assert adjusted.target_length_cjk == 1600
    assert adjusted.constraints[-1] == "review_feedback:too short"


def test_beat_plan_can_nudge_length_from_review():
    plan = BeatPlan(chapter_id="CH-1", length_target=1000, turning_points=["reveal"])
    adjusted = plan.adjusted_for_review(
        overall_verdict="revise",
        issues=["hook weak"],
        scores={"hook_strength": 0.55},
    )
    assert adjusted.length_target == 1250
    assert adjusted.turning_points == ["reveal"]
