from runtime.serialize.quality_snapshot import build_quality_snapshot
from runtime.serialize.validation_report import (
    build_short_run_validation_report,
    build_short_run_validation_report_from_bodies,
)


def test_short_run_validation_report_structure():
    snaps = [
        build_quality_snapshot(chapter_id="CH-00001", body="第一章。"),
        build_quality_snapshot(chapter_id="CH-00002", body="第二章 with English drift."),
        build_quality_snapshot(chapter_id="CH-00003", body="第三章。"),
    ]
    report = build_short_run_validation_report(snaps)

    assert report["kind"] == "short_run_validation_report"
    assert report["snapshot_count"] == 3
    assert report["chapter_ids"] == ["CH-00001", "CH-00002", "CH-00003"]
    assert len(report["comparisons"]) == 2
    assert "content_hash" in report


def test_short_run_validation_report_from_bodies():
    report = build_short_run_validation_report_from_bodies([
        ("CH-00001", "第一章。"),
        ("CH-00002", "第二章 with English drift."),
    ])
    assert report["snapshot_count"] == 2
    assert report["chapter_ids"] == ["CH-00001", "CH-00002"]
