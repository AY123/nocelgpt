from runtime.serialize.golden_three_records import build_golden_three_review_record


def test_golden_three_review_record_structure():
    record = build_golden_three_review_record(
        chapters=[
            ("CH-00001", "第一章正文"),
            ("CH-00002", "第二章正文"),
            ("CH-00003", "第三章正文"),
        ],
        reviewers=["reviewer-a", "reviewer-b"],
        notes="golden three check",
    )

    assert record["kind"] == "golden_three_review_record"
    assert record["reviewer_count"] == 2
    assert record["pack"]["chapter_count"] == 3
    assert record["notes"] == "golden three check"
    assert "content_hash" in record
