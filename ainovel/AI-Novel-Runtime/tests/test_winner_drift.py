from runtime.serialize.winner_drift import build_winner_drift_report


def test_winner_drift_report_matches_and_mismatches():
    same = build_winner_drift_report(
        scored_hash="abc",
        written_hash="abc",
        scored_id="cand-1",
        written_id="cand-1",
        evidence_ref="registry/derived/version-comparison/cmp.json",
    )
    diff = build_winner_drift_report(
        scored_hash="abc",
        written_hash="xyz",
        scored_id="cand-1",
        written_id="cand-1",
    )

    assert same["matches"] is True
    assert diff["matches"] is False
    assert same["kind"] == "winner_drift_report"
    assert "content_hash" in same
