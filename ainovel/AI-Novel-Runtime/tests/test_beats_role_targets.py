from runtime.chapter.types import Beat, BeatPlan


def test_beat_plan_serializes_length_and_turning_points():
    plan = BeatPlan(
        chapter_id="CH-1",
        beats=[Beat(beat_id="B-1", purpose="hook", summary="开篇钩子")],
        length_target=1200,
        hook_plan="chapter ends with a reveal",
        turning_points=["reveal"],
    )
    payload = plan.to_dict()
    assert payload["length_target"] == 1200
    assert payload["hook_plan"] == "chapter ends with a reveal"
    assert payload["turning_points"] == ["reveal"]
