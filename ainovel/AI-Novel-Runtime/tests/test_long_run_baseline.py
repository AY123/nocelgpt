from runtime.serialize.long_run_baseline import build_hundred_chapter_baseline


CHAPTERS = []
for i in range(1, 101):
    CHAPTERS.append({
        "chapter_index": i,
        "ok": True,
        "quality": {"scores": {"quality": 8 if i <= 50 else 9}, "verdict": "pass"},
        "cost": {"cost": {"currency": "USD", "total_cost": 0.01}},
    })


def test_hundred_chapter_baseline_segments():
    baseline = build_hundred_chapter_baseline(project_id="PROJ-1", chapters=CHAPTERS, promise_ledger={"overdue": ["P-05"], "resolved": ["P-01"], "pending": []})
    data = baseline.to_dict()

    assert data["kind"] == "hundred_chapter_baseline"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert data["front_half"]["chapter_count"] == 50
    assert data["back_half"]["chapter_count"] == 50
    assert data["full_run"]["chapter_count"] == 100
    assert data["go_iterate_stop"] == "go"
    assert data["front_half"]["promise_overdue"] == ["P-05"]


def test_hundred_chapter_baseline_empty_run_stops():
    baseline = build_hundred_chapter_baseline(project_id="PROJ-1", chapters=[])
    assert baseline.go_iterate_stop == "stop"
