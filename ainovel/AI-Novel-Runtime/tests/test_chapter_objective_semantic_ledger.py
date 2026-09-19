from runtime.director.plan import build_chapter_objective


SEMANTIC_LEDGER = {
    "knowledge": [{"entry_id": "K-01", "text": "世界存在旧约束", "source_chapter": 1}],
    "ability": [{"entry_id": "A-01", "text": "主角学会控火", "status": "active"}],
    "injury": [],
    "items": [],
    "relationship_expectation": [{"entry_id": "R-01", "text": "盟友期待信任", "parties": ["林照夜", "白砚"], "expectation": "坦诚"}],
    "promise": [{"entry_id": "P-01", "text": "揭开真相", "status": "pending", "due_by": "ch01"}],
}


def test_chapter_objective_embeds_semantic_ledger_as_constraint():
    obj = build_chapter_objective(
        chapter_id="TASK-00004",
        narrative_ir={"id": "IR-4", "primary_goal": "推进冲突"},
        semantic_ledger=SEMANTIC_LEDGER,
    )

    assert obj["semantic_ledger"] == SEMANTIC_LEDGER
    assert any("语义状态" in c for c in obj["constraints"])
    rendered_constraints = "\n".join(obj["constraints"])
    assert "【承诺】" in rendered_constraints
    assert "P-01" in rendered_constraints
