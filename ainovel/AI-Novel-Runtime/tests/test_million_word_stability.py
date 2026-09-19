from runtime.serialize.million_word_stability import build_million_word_stability_report


CHAPTERS = []
for i in range(1, 301):
    CHAPTERS.append({
        "chapter_index": i,
        "ok": True,
        "quality": {"scores": {"quality": 8 if i <= 150 else 7.5}, "verdict": "pass"},
        "cost": {"cost": {"currency": "USD", "total_cost": 0.01}},
    })


def test_million_word_stability_report():
    report = build_million_word_stability_report(
        project_id="PROJ-1",
        chapters=CHAPTERS,
        window_size=50,
        words_per_chapter=3500,
    )
    data = report.to_dict()

    assert data["kind"] == "million_word_stability_report"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert data["total_chapters"] == 300
    assert data["total_words"] == 1_050_000
    assert data["is_million_word"] is True
    assert len(data["windows"]) == 6


def test_million_word_not_reached():
    report = build_million_word_stability_report(
        project_id="PROJ-2",
        chapters=CHAPTERS[:30],
        words_per_chapter=3000,
    )
    assert report.is_million_word is False
    assert report.total_words == 90_000


def test_back_half_decline_detection():
    declining = []
    for i in range(1, 101):
        score = 9.0 if i <= 50 else 6.0
        declining.append({"chapter_index": i, "ok": True, "quality": {"scores": {"q": score}}})
    report = build_million_word_stability_report(project_id="PROJ-3", chapters=declining, window_size=20)
    assert report.back_half_decline is True
    assert report.stable is False
