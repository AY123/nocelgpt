from runtime.serialize.platform_feedback_reconciliation import reconcile_platform_feedback


def test_reconcile_with_real_data():
    report = reconcile_platform_feedback(
        project_id="PROJ-1",
        batches=[
            {"batch_id": "B1", "platform": "起点", "window_start": "2026-01-01", "window_end": "2026-01-31",
             "sample_size": 5000, "signals": {"three_chapter_retention": 0.65, "first_subscribe": 1200}, "confidence": 0.9},
        ],
        predicted_signals={"three_chapter_retention": 0.70, "first_subscribe": 1000},
    )
    data = report.to_dict()

    assert data["kind"] == "platform_feedback_reconciliation"
    assert data["has_real_data"] is True
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert len(data["reconciled"]) == 2
    r = data["reconciled"][0]
    assert r["direction"] in ("over-predicted", "under-predicted", "matched")
    assert r["delta"] is not None


def test_reconcile_without_real_data():
    report = reconcile_platform_feedback(
        project_id="PROJ-1",
        batches=[{"batch_id": "B1", "platform": "起点", "sample_size": 0, "signals": {}}],
        predicted_signals={"three_chapter_retention": 0.70},
    )
    data = report.to_dict()

    assert data["has_real_data"] is False
    assert data["reconciled"][0]["direction"] == "predicted-only"


def test_reconcile_empty():
    report = reconcile_platform_feedback(project_id="PROJ-1", batches=[])
    assert report.has_real_data is False
    assert report.reconciled == []
