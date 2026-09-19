from runtime.serialize.long_run_checkpoint import build_long_run_checkpoint_report


CHAPTERS = [
    {"chapter_index": 1, "ok": True, "quality": {"verdict": "pass"}, "cost": {"cost": {"currency": "USD", "total_cost": 0.01}}},
    {"chapter_index": 2, "ok": True, "quality": {"verdict": "pass"}, "cost": {"cost": {"currency": "USD", "total_cost": 0.02}}},
    {"chapter_index": 3, "ok": False, "quality": {"verdict": "fail"}, "cost": {}},
]


def test_checkpoint_report_aggregates_windows():
    report = build_long_run_checkpoint_report(chapters=CHAPTERS, window_size=10)
    data = report.to_dict()

    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert data["total_chapters"] == 3
    assert data["total_produced"] == 2
    assert data["total_skipped"] == 1
    assert data["total_cost"] == 0.03
    assert data["cost_currency"] == "USD"
    assert len(data["checkpoints"]) == 1
    assert "ch001-003" in data["checkpoints"][0]["window"]
    assert data["checkpoints"][0]["produced"] == 2
    assert data["checkpoints"][0]["skipped"] == 1
    assert "ch3: fail" in data["checkpoints"][0]["quality_warnings"]


def test_checkpoint_report_with_promise_ledger():
    report = build_long_run_checkpoint_report(
        chapters=CHAPTERS,
        promise_ledger={"overdue": ["P-05"], "resolved": ["P-01", "P-02"], "pending": ["P-03"]},
    )
    data = report.to_dict()

    assert data["checkpoints"][0]["promise_overdue"] == ["P-05"]
    assert "P-01" in data["checkpoints"][0]["promise_resolved"]
