from runtime.outline.agents import review_candidate, synthesize_final_outline
from runtime.retrieval.originality import assess_candidate_originality, assess_evidence_originality


def _pack(clusters=1, share=0.9):
    return {
        "id": "NEP-RISK-TEST",
        "corpus_snapshot_id": "CORPUS-TEST-001",
        "patterns": [{"pattern_type": "opening-payoff"}],
        "originality": {"source_cluster_count": clusters, "max_single_source_share": share, "risk_level": "low"},
        "provenance": {"snapshot_hash": "sha256:" + "a" * 64, "query_hash": "sha256:" + "b" * 64},
    }


def _candidate(cid, focus):
    return {
        "id": cid, "title": cid, "genre": ["玄幻"], "logline": "原创候选",
        "design_focus": focus, "structure_basis": [],
        "protagonist_engine": {"desire": "成长", "golden_finger": "能力", "cost": "代价"},
        "power_system": {"tiers": ["一阶", "二阶"], "hard_limits": ["限制"]},
    }


def test_evidence_originality_is_replayable_and_snapshot_bound():
    a = assess_evidence_originality(_pack())
    b = assess_evidence_originality(_pack())
    assert a == b
    assert a["risk_level"] == "high"
    assert a["snapshot_hash"] == "sha256:" + "a" * 64
    assert a["query_hash"] == "sha256:" + "b" * 64
    assert not a["legal_conclusion"]


def test_low_diversity_pattern_overlap_marks_candidate_high_risk():
    result = assess_candidate_originality(_candidate("A", ["opening-payoff"]), _pack())
    assert result["risk_level"] == "high"
    assert "candidate_overfits_low_diversity_patterns" in result["reasons"]


def test_high_risk_candidate_cannot_auto_win_when_safe_candidate_exists():
    merged = {"genre_signals": ["玄幻"], "reader_rewards": [], "structure_signals": [], "originality_guardrails": [], "narrative_evidence": _pack()}
    risky = _candidate("RISKY", ["opening-payoff"])
    safe = _candidate("SAFE", ["worldbuilding"])
    reviews = [
        {**review_candidate(risky, merged), "score": 10},
        {**review_candidate(safe, merged), "score": 6, "risk_level": "low"},
    ]
    outline = synthesize_final_outline([risky, safe], reviews, merged, "PROJECT-TEST", [])
    assert outline["collaboration"]["selected_candidate"] == "SAFE"
    assert "RISKY" in outline["originality_report"]["high_risk_candidates_excluded"]
    assert outline["originality_report"]["comparison_only"] is True
    assert outline["originality_report"]["legal_conclusion"] is False
