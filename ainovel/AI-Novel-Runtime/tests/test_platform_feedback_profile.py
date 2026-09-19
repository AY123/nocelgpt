from runtime.serialize.platform_feedback_profile import build_platform_feedback_profile


def test_platform_feedback_profile():
    profile = build_platform_feedback_profile(
        profile_id="PLATFORM-001",
        sources=["起点中文网"],
        rows=[
            {"platform": "起点", "window_start": "2026-01-01", "window_end": "2026-01-31", "sample_size": 5000, "exposure": 100000, "three_chapter_retention": 0.65, "ten_chapter_retention": 0.42, "first_subscribe": 1200, "follow_up": 800, "comments": 350, "abandon_points": [3, 7, 15]},
        ],
    )
    data = profile.to_dict()

    assert data["kind"] == "platform_feedback_profile"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert data["sources"] == ["起点中文网"]
    assert len(data["rows"]) == 1
    assert data["rows"][0]["three_chapter_retention"] == 0.65
    assert data["metadata"]["row_count"] == 1


def test_platform_feedback_profile_empty():
    profile = build_platform_feedback_profile(profile_id="PLATFORM-002")
    data = profile.to_dict()

    assert data["rows"] == []
    assert data["metadata"]["row_count"] == 0
