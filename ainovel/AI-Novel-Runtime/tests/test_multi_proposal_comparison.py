from runtime.serialize.multi_proposal_comparison import compare_multi_proposals


def test_multi_proposal_comparison_picks_winner():
    report = compare_multi_proposals(
        project_id="PROJ-1",
        proposals=[
            {"proposal_id": "P1", "logline": "方案A", "market_fit": 7, "opening_hook_strength": 8, "long_arc_clarity": 6, "originality_risk": "low"},
            {"proposal_id": "P2", "logline": "方案B", "market_fit": 8, "opening_hook_strength": 9, "long_arc_clarity": 7, "originality_risk": "medium"},
            {"proposal_id": "P3", "logline": "方案C", "market_fit": 6, "opening_hook_strength": 7, "long_arc_clarity": 5, "originality_risk": "high"},
        ],
    )
    data = report.to_dict()

    assert data["kind"] == "multi_proposal_comparison"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert data["publish_authority"] == "human"
    assert data["winner_id"] == "P2"
    assert len(data["proposals"]) == 3


def test_multi_proposal_no_scores():
    report = compare_multi_proposals(
        project_id="PROJ-1",
        proposals=[{"proposal_id": "P1", "logline": "方案A"}],
    )
    assert report.winner_id is None
    assert report.proposals[0].total_score is None
