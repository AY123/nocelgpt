from runtime.serialize.long_arc_plan import build_hundred_chapter_long_arc


def test_hundred_chapter_long_arc_has_10_bands():
    plan = build_hundred_chapter_long_arc(outline={"title": "灰烬纪元", "logline": "少年觉醒"})
    data = plan.to_dict()

    assert data["kind"] == "hundred_chapter_long_arc_plan"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert len(data["bands"]) == 10
    assert data["bands"][0]["start"] == 1
    assert data["bands"][0]["end"] == 10
    assert data["bands"][-1]["start"] == 91
    assert data["bands"][-1]["end"] == 100
    assert "少年觉醒" in data["bands"][0]["main_conflict"]
    assert data["metadata"]["band_count"] == 10
    assert data["metadata"]["chapter_count"] == 100


def test_long_arc_band_has_required_fields():
    plan = build_hundred_chapter_long_arc(outline={})
    band = plan.bands[5]
    assert band.volume_goal
    assert band.main_conflict
    assert band.growth_shift
    assert band.world_addition
    assert band.commercial_peak
    assert band.payoff_commitment
