from runtime.outline.ledgers import build_ci_m4_ledger


OUTLINE = {
    "first_30_chapters": [
        {"chapter_no": 1, "goal": "开局", "end_hook": "悬念1", "reward_if_any": "奖励1", "escalation": "抬高"},
        {"chapter_no": 2, "goal": "推进", "end_hook": "悬念2", "reward_if_any": "", "escalation": "抬高"},
        {"chapter_no": 3, "goal": "翻身", "end_hook": "悬念3", "reward_if_any": "奖励3", "escalation": "反转"},
        {"chapter_no": 5, "goal": "加压", "end_hook": "悬念5", "reward_if_any": "", "escalation": "抬高"},
        {"chapter_no": 10, "goal": "收束", "end_hook": "悬念10", "reward_if_any": "", "escalation": "抬高"},
    ],
    "characters": [
        {"role": "protagonist", "name": "林照夜", "arc": "从求生者到秩序重建者", "motivation": "重建秩序"},
        {"role": "rival", "name": "沈无咎", "arc": "从对抗到理解", "motivation": "维护旧秩序"},
        {"role": "mentor", "name": "白砚", "arc": "守秘者面对旧错", "motivation": "赎清一段旧错"},
    ],
    "protagonist_engine": {"desire": "成为掌局者", "flaw": "不敢信任他人"},
}


def test_ci_m4_ledger_contains_all_four_ledgers():
    ledger = build_ci_m4_ledger(OUTLINE)
    data = ledger.to_dict()

    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert len(data["chapter_functions"]) == 5
    assert len(data["promises"]) == 5
    assert len(data["character_arcs"]) == 3
    assert len(data["narrative_economy"]) == 5


def test_ci_m4_ledger_metadata_has_counts():
    ledger = build_ci_m4_ledger(OUTLINE)
    data = ledger.to_dict()

    assert data["metadata"]["chapter_count"] == 5
    assert data["metadata"]["protagonist"] == "林照夜"
    assert data["metadata"]["character_count"] == 3
    assert data["metadata"]["promise_count"] == 5
    assert "resolved_count" in data["metadata"]
    assert "overdue_count" in data["metadata"]
    assert "pending_count" in data["metadata"]


def test_character_arc_covers_all_characters():
    ledger = build_ci_m4_ledger(OUTLINE)
    names = [arc.character for arc in ledger.character_arcs]

    assert "林照夜" in names
    assert "沈无咎" in names
    assert "白砚" in names
    assert len(names) == 3


def test_character_arc_protagonist_has_flaw_to_desire():
    ledger = build_ci_m4_ledger(OUTLINE)
    protagonist_arc = next(arc for arc in ledger.character_arcs if arc.character == "林照夜")

    assert protagonist_arc.arc_axis == "flaw_to_desire"
    assert "不敢信任他人" in protagonist_arc.starting_state
    assert "成为掌局者" in protagonist_arc.ending_state


def test_character_arc_rival_has_opposition_axis():
    ledger = build_ci_m4_ledger(OUTLINE)
    rival_arc = next(arc for arc in ledger.character_arcs if arc.character == "沈无咎")

    assert rival_arc.arc_axis == "opposition_to_reckoning"


def test_character_arc_mentor_has_secrecy_axis():
    ledger = build_ci_m4_ledger(OUTLINE)
    mentor_arc = next(arc for arc in ledger.character_arcs if arc.character == "白砚")

    assert mentor_arc.arc_axis == "secrecy_to_confession"


def test_promise_ledger_has_resolved_and_overdue():
    ledger = build_ci_m4_ledger(OUTLINE)
    statuses = [p.status for p in ledger.promises]

    assert "resolved" in statuses
    assert "overdue" in statuses or "pending" in statuses


def test_narrative_economy_tracks_debt():
    ledger = build_ci_m4_ledger(OUTLINE)
    economy = ledger.narrative_economy

    assert len(economy) == 5
    assert all(isinstance(e.debt, int) for e in economy)
    assert all(e.debt >= 0 for e in economy)


def test_chapter_function_signature_has_setup_and_payoff():
    ledger = build_ci_m4_ledger(OUTLINE)
    first = ledger.chapter_functions[0]

    assert first.function_type == "setup"
    assert first.setup == "开局"
    assert first.payoff == "悬念1"


def test_ci_m4_ledger_with_empty_outline():
    ledger = build_ci_m4_ledger({})
    data = ledger.to_dict()

    assert data["chapter_functions"] == []
    assert data["promises"] == []
    assert len(data["character_arcs"]) == 1
    assert data["character_arcs"][0]["character"] == "主角"
    assert data["narrative_economy"] == []
