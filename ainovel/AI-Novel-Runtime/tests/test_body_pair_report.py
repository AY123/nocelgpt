from runtime.serialize.body_pair_report import build_body_pair_validation_report


def test_body_pair_validation_report_structure():
    report = build_body_pair_validation_report(
        before=[("CH-00001", "第一章。"), ("CH-00002", "第二章。")],
        after=[("CH-00001", "第一章 improved。"), ("CH-00002", "第二章 improved。")],
    )

    assert report["kind"] == "body_pair_validation_report"
    assert report["before_snapshot_count"] == 2
    assert report["after_snapshot_count"] == 2
    assert "content_hash" in report
