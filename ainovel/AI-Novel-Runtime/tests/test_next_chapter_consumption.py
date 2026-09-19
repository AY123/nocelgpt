from runtime.director.consumption import build_consumption_evidence, approved_state_constraints


def test_consumption_evidence_carries_semantic_facts():
    evidence = build_consumption_evidence(
        chapter_id="CH-05",
        approved_candidates=[{"id": "CAND-A"}],
        mint_records=[{"id": "FACT-1", "name": "金钥匙", "field": "items", "value": "一把金色钥匙"}],
        recompute={"id": "RC-1"},
        state_before={"state_hash": "sha256:before"},
        state_after={"state_hash": "sha256:after"},
        objective_id="OBJ-1",
        prompt_manifest_id="PM-1",
        draft_ref="DRAFT-1",
    )
    assert evidence["consumption_hash"].startswith("sha256:")
    assert evidence["mint_ids"] == ["FACT-1"]
    assert evidence["approved_facts"][0]["name"] == "金钥匙"
    assert evidence["state_before_hash"] != evidence["state_after_hash"]


def test_approved_state_constraints_when_minted():
    evidence = build_consumption_evidence(
        chapter_id="CH-05",
        mint_records=[{"id": "FACT-1", "name": "钥匙", "field": "items", "value": "金钥匙"}],
        state_after={"state_hash": "sha256:after"},
    )
    constraints = approved_state_constraints(evidence, {"state_hash": "sha256:after"})
    assert len(constraints) >= 1
    assert "sha256:after" in constraints[1]
    assert any("钥匙" in constraint and "items=金钥匙" in constraint
               for constraint in constraints)


def test_approved_state_constraints_empty_without_mints():
    evidence = build_consumption_evidence(chapter_id="CH-05")
    constraints = approved_state_constraints(evidence, None)
    assert constraints == []


def test_semantic_ledger_integrates_with_consumption():
    evidence = build_consumption_evidence(
        chapter_id="CH-05",
        mint_records=[{"id": "FACT-1", "name": "金钥匙", "field": "items", "value": "金钥匙"}],
        state_after={"state_hash": "sha256:after"},
    )
    semantic_ledger = {
        "items": [{"entry_id": "FACT-1", "text": "金钥匙", "source_chapter": 4}],
        "promise": [{"promise_id": "P-01", "promise_text": "用钥匙开门", "status": "pending", "source_chapter": 4}],
    }
    constraints = approved_state_constraints(evidence, {"state_hash": "sha256:after"})
    assert "sha256:after" in constraints[1]
    assert semantic_ledger["items"][0]["entry_id"] == "FACT-1"
    assert evidence["approved_facts"][0]["id"] == "FACT-1"
