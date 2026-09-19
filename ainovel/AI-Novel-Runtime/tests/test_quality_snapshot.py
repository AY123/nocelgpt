from __future__ import annotations

from runtime.cli import main
from runtime.serialize.quality_snapshot import (
    build_quality_snapshot,
    compare_quality_snapshots,
)


def test_quality_snapshot_detects_prose_warnings():
    snapshot = build_quality_snapshot(
        chapter_id="CH-00001",
        body=(
            "He had not eaten. He had not slept. He had not stopped moving. "
            "The rain fell like glass. The wind cut like a blade."
        ),
    )

    assert snapshot["kind"] == "quality_snapshot"
    assert snapshot["chapter_id"] == "CH-00001"
    assert snapshot["warning_count"] > 0
    assert snapshot["length"]["body_chars"] > 0
    assert snapshot["language"]["body_chars"] > 0
    assert snapshot["findings"]


def test_quality_snapshot_comparison_reports_delta():
    left = build_quality_snapshot(
        chapter_id="CH-00001",
        body="He had not eaten. He had not slept.",
    )
    right = build_quality_snapshot(
        chapter_id="CH-00002",
        body="马伦举起铁锤挡在门口。埃德里克低声报出名字。",
    )
    cmp = compare_quality_snapshots(left, right)

    assert cmp["kind"] == "quality_snapshot_comparison"
    assert cmp["verdict"] in {"improved", "regressed", "unchanged"}
    assert cmp["right"]["chapter_id"] == "CH-00002"


def test_quality_snapshot_cli_json(capsys):
    code = main([
        "quality-snapshot",
        "--chapter-id", "CH-00002",
        "--body", "马伦举起铁锤挡在门口。埃德里克低声报出名字。",
        "--json",
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert '"chapter_id": "CH-00002"' in out
    assert '"length"' in out
    assert '"language"' in out
