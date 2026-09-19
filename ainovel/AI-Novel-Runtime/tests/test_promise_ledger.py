from runtime.serialize.promise_ledger import build_promise_ledger


CHAPTERS = [
    {"chapter_no": 1, "goal": "开局", "end_hook": "悬念1", "reward_if_any": "奖励1"},
    {"chapter_no": 2, "goal": "推进", "end_hook": "悬念2", "reward_if_any": ""},
    {"chapter_no": 3, "goal": "翻身", "end_hook": "悬念3", "reward_if_any": "奖励3"},
    {"chapter_no": 5, "goal": "加压", "end_hook": "悬念5", "reward_if_any": ""},
    {"chapter_no": 10, "goal": "收束", "end_hook": "悬念10", "reward_if_any": ""},
]


def test_promise_ledger_tracks_statuses():
    report = build_promise_ledger(CHAPTERS)
    data = report.to_dict()

    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert len(data["promises"]) == 5
    assert "P-01" in data["resolved"] or "P-01" in data["pending"]
    assert data["metadata"]["chapter_count"] == 5
