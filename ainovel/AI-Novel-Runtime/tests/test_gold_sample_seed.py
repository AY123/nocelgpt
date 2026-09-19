from runtime.serialize.gold_sample_seed import seed_gold_sample_plan


def test_gold_sample_seed_plan():
    plan = seed_gold_sample_plan([{"chapter_id": f"CH-{i:03d}"} for i in range(1, 61)], target_count=50)
    data = plan.to_dict()

    assert data["kind"] == "gold_sample_collection_plan"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert data["target_count"] == 50
    assert len(data["samples"]) == 50
    assert data["metadata"]["seeded_count"] == 50
    assert data["samples"][0]["sample_id"] == "GS-001"
    assert data["samples"][0]["labels"] == ["dual_review", "adjudication_needed"]
