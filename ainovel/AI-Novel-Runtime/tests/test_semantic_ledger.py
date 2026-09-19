from runtime.outline.ledgers import build_semantic_ledger


OUTLINE = {
    "first_30_chapters": [
        {"chapter_no": 1, "goal": "开局", "end_hook": "悬念1", "reward_if_any": "奖励1"},
        {"chapter_no": 2, "goal": "推进", "end_hook": "悬念2", "reward_if_any": ""},
        {"chapter_no": 3, "goal": "翻身", "end_hook": "悬念3", "reward_if_any": "奖励3"},
    ],
    "characters": [
        {"role": "protagonist", "name": "林照夜", "arc": "从求生者到秩序重建者", "motivation": "重建秩序"},
        {"role": "rival", "name": "沈无咎", "arc": "从对抗到理解", "motivation": "维护旧秩序"},
        {"role": "mentor", "name": "白砚", "arc": "守秘者面对旧错", "motivation": "赎清旧错"},
    ],
    "protagonist_engine": {"desire": "成为掌局者", "flaw": "不敢信任他人"},
}


def test_semantic_ledger_has_six_categories():
    ledger = build_semantic_ledger(OUTLINE)
    data = ledger.to_dict()

    for key in ("knowledge", "ability", "injury", "items", "relationship_expectation", "promise"):
        assert key in data


def test_semantic_ledger_extracts_knowledge_from_chapters():
    ledger = build_semantic_ledger(OUTLINE)
    assert len(ledger.knowledge) == 3
    assert all(e.source_chapter is not None for e in ledger.knowledge)


def test_semantic_ledger_extracts_promise_with_status():
    ledger = build_semantic_ledger(OUTLINE)
    statuses = [e.status for e in ledger.promise]
    assert "pending" in statuses
    assert "resolved" in statuses


def test_semantic_ledger_extracts_relationship_expectation():
    ledger = build_semantic_ledger(OUTLINE)
    assert len(ledger.relationship_expectation) == 2
    for e in ledger.relationship_expectation:
        assert len(e.parties) == 2


def test_semantic_ledger_metadata():
    ledger = build_semantic_ledger(OUTLINE)
    data = ledger.to_dict()
    assert data["metadata"]["chapter_count"] == 3
    assert data["metadata"]["protagonist"] == "林照夜"


def test_semantic_ledger_conflict_detection_enabled():
    ledger = build_semantic_ledger(OUTLINE)
    assert ledger.conflict_detection["enabled"] is True
    assert "promise" in ledger.conflict_detection["conflict_types"]


def test_semantic_ledger_empty_outline():
    ledger = build_semantic_ledger({})
    data = ledger.to_dict()
    assert data["knowledge"] == []
    assert data["promise"] == []
    assert data["metadata"]["chapter_count"] == 0
    assert data["metadata"]["protagonist"] == "主角"
