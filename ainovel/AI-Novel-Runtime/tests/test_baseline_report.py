from runtime.serialize.baseline_report import build_baseline_report


def test_baseline_report_structure():
    report = build_baseline_report(
        chapters=[
            ("CH-00001", "第一章正文"),
            ("CH-00002", "第二章正文"),
            ("CH-00003", "第三章正文"),
        ],
        reviewers=["reviewer-a", "reviewer-b"],
        winner_scored_hash="abc",
        winner_written_hash="abc",
        winner_scored_id="cand-1",
        winner_written_id="cand-1",
        notes="baseline report",
    )

    assert report["kind"] == "baseline_report"
    assert report["chapter_count"] == 3
    assert report["winner_drift"]["matches"] is True
    assert report["pack"]["chapter_count"] == 3
    assert "content_hash" in report
