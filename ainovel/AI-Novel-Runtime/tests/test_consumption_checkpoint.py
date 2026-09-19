from runtime.director.consumption_checkpoint import build_consumption_checkpoint, checkpoint_to_prompt_variables


def test_checkpoint_carries_all_state():
    checkpoint = build_consumption_checkpoint(
        chapter_id="CH-05",
        approved_candidates=[{"id": "CAND-A"}],
        mint_records=[{"id": "FACT-1", "name": "金钥匙", "field": "items", "value": "金钥匙"}],
        recompute={"id": "RC-1"},
        state_before={"state_hash": "sha256:before"},
        state_after={"state_hash": "sha256:after"},
        objective_id="OBJ-1",
        prompt_manifest_id="PM-1",
        draft_ref="DRAFT-1",
        promise_ledger={"overdue": [], "resolved": ["P-01"], "pending": ["P-02"], "metadata": {"chapter_count": 5}},
        semantic_ledger={
            "items": [{"entry_id": "FACT-1", "text": "金钥匙", "source_chapter": 4}],
            "promise": [{"promise_id": "P-01", "promise_text": "用钥匙开门", "status": "pending", "source_chapter": 4}],
        },
    )
    assert checkpoint["checkpoint_hash"].startswith("sha256:")
    assert checkpoint["gating"] is False
    assert checkpoint["comparison_only"] is True
    assert checkpoint["approved_facts"][0]["name"] == "金钥匙"
    assert checkpoint["promise_summary"]["resolved"] == ["P-01"]
    assert "金钥匙" in checkpoint["semantic_ledger_text"]


def test_checkpoint_to_prompt_variables():
    checkpoint = build_consumption_checkpoint(
        chapter_id="CH-06",
        mint_records=[{"id": "FACT-2", "name": "地图", "field": "items", "value": "藏宝图"}],
        state_after={"state_hash": "sha256:after2"},
        promise_ledger={"overdue": ["P-05"], "resolved": [], "pending": ["P-01"], "metadata": {}},
        semantic_ledger={"items": [{"entry_id": "FACT-2", "text": "藏宝图"}]},
    )
    variables = checkpoint_to_prompt_variables(checkpoint)
    assert variables["approved_state"] is not None
    assert len(variables["approved_state_constraints"]) >= 1
    assert "藏宝图" in variables["semantic_ledger"]


def test_checkpoint_without_mints():
    checkpoint = build_consumption_checkpoint(chapter_id="CH-01")
    assert checkpoint["checkpoint_hash"].startswith("sha256:")
    assert checkpoint["approved_facts"] == []
    assert checkpoint["approved_state_constraints"] == []
    assert checkpoint["promise_summary"] == {}
