from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path

from runtime.cli import main
from runtime.serialize.live_baseline_precheck import (
    PRECHECK_BASELINE_ID,
    build_precheck_environment,
    build_precheck_report,
)
from runtime.serialize.live_baseline_run import BASELINE_3CH_ID
from runtime.serialize.baseline_freeze import (
    build_baseline_freeze_record,
    list_baseline_freeze_refs,
    load_baseline_freeze_record,
    write_baseline_freeze_record,
)
from runtime.serialize.baseline_comparison import compare_baseline_freeze_records
from runtime.serialize.baseline_compare_report import compare_and_write_baseline_report


def test_precheck_environment_and_report_shape():
    env = build_precheck_environment(
        provider="deepseek",
        model="deepseek-v4-pro",
        prompt_version="6.0.0",
        runtime_version="test",
    )
    report = build_precheck_report(
        project_path="/tmp/project",
        status="passed",
        environment=env,
        chapters=[],
        failures=[],
        replay={"generation_records": 0, "replay_hits": 0, "live_calls": 2},
        cost={"budget_limit": 20.0, "actual_cost": 0.0, "currency": "CNY"},
        resume={"interrupted_after_chapter": None, "resumed": False, "duplicate_calls_detected": False},
        run_manifest_ref="registry/derived/run-manifests/RUN-00001.json",
    )

    assert env["provider"] == "deepseek"
    assert report["baseline_id"] == PRECHECK_BASELINE_ID
    assert report["status"] == "passed"
    assert report["chapter_summary"]["count"] == 0
    assert report["run_manifest_ref"]


def test_baseline_freeze_record_write(tmp_path):
    record = build_baseline_freeze_record(
        baseline_id="LIVE-5CH-001",
        chapter_ids=["CH-00001", "CH-00002"],
        run_manifest_ref="registry/derived/run-manifests/RUN-00001.json",
        live_baseline_report_ref="registry/derived/live-baseline-reports/LBR-00001.json",
        prompt_version="6.0.0",
        replay_ref="registry/derived/live-baseline-reports/LBR-00001.json",
        quality_ref="registry/derived/live-baseline-reports/LBR-00001.json",
        provenance_ref="registry/derived/run-manifests/RUN-00001.json",
        notes="passed; chapters=2",
    )
    rel = write_baseline_freeze_record(project_path=tmp_path, record=record)

    assert record["kind"] == "baseline_freeze"
    assert record["baseline_id"] == "LIVE-5CH-001"
    assert record["provenance"]["derived_from"] == [
        "registry/derived/run-manifests/RUN-00001.json",
        "registry/derived/live-baseline-reports/LBR-00001.json",
        "registry/derived/live-baseline-reports/LBR-00001.json",
        "registry/derived/live-baseline-reports/LBR-00001.json",
        "registry/derived/run-manifests/RUN-00001.json",
    ]
    assert rel == "registry/derived/baseline-freezes/LIVE-5CH-001.json"
    assert (tmp_path / rel).exists()
    loaded = (tmp_path / rel).read_text(encoding="utf-8")
    assert '"content_hash"' in loaded


def test_baseline_freeze_index_and_load(tmp_path):
    record = build_baseline_freeze_record(
        baseline_id="LIVE-5CH-001",
        chapter_ids=["CH-00001"],
        run_manifest_ref="registry/derived/run-manifests/RUN-00001.json",
        live_baseline_report_ref="registry/derived/live-baseline-reports/LBR-00001.json",
    )
    write_baseline_freeze_record(project_path=tmp_path, record=record)
    refs = list_baseline_freeze_refs(tmp_path)
    loaded = load_baseline_freeze_record(tmp_path, "LIVE-5CH-001")

    assert refs and refs[0]["id"] == "LIVE-5CH-001"
    assert loaded is not None
    assert loaded["baseline_id"] == "LIVE-5CH-001"


def test_baseline_freeze_comparison(tmp_path):
    left = build_baseline_freeze_record(
        baseline_id="LIVE-5CH-001",
        chapter_ids=["CH-00001", "CH-00002"],
        run_manifest_ref="registry/derived/run-manifests/RUN-00001.json",
        live_baseline_report_ref="registry/derived/live-baseline-reports/LBR-00001.json",
    )
    right = build_baseline_freeze_record(
        baseline_id="LIVE-3CH-001",
        chapter_ids=["CH-00001", "CH-00002", "CH-00003"],
        run_manifest_ref="registry/derived/run-manifests/RUN-00002.json",
        live_baseline_report_ref="registry/derived/live-baseline-reports/LBR-00002.json",
    )
    compare = compare_baseline_freeze_records(left, right)

    assert compare["kind"] == "baseline_freeze_comparison"
    assert compare["delta_chapter_count"] == 1
    assert compare["same_content_hash"] is False
    assert compare["shared_chapter_ids"] == ["CH-00001", "CH-00002"]


def test_baseline_compare_report_written(tmp_path):
    left = build_baseline_freeze_record(
        baseline_id="LIVE-5CH-001",
        chapter_ids=["CH-00001", "CH-00002"],
        run_manifest_ref="registry/derived/run-manifests/RUN-00001.json",
        live_baseline_report_ref="registry/derived/live-baseline-reports/LBR-00001.json",
    )
    right = build_baseline_freeze_record(
        baseline_id="LIVE-3CH-001",
        chapter_ids=["CH-00001", "CH-00002", "CH-00003"],
        run_manifest_ref="registry/derived/run-manifests/RUN-00002.json",
        live_baseline_report_ref="registry/derived/live-baseline-reports/LBR-00002.json",
    )
    write_baseline_freeze_record(project_path=tmp_path, record=left)
    write_baseline_freeze_record(project_path=tmp_path, record=right)
    result = compare_and_write_baseline_report(
        project_path=tmp_path,
        left_id="LIVE-5CH-001",
        right_id="LIVE-3CH-001",
        report_id="BCR-001",
    )
    assert result is not None
    report, rel = result
    assert report["kind"] == "baseline_compare_report"
    assert rel == "registry/derived/baseline-compare-reports/BCR-001.json"
    assert (tmp_path / rel).exists()


def test_serial_precheck_writes_freeze_artifact(tmp_path):
    root = tmp_path / "project"
    (root / "registry" / "_meta").mkdir(parents=True)
    (root / "registry" / "_meta" / "registry-version").write_text("1\n", encoding="utf-8")
    (root / "registry" / "_meta" / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main([
            "serial", "precheck",
            "--project", str(root),
            "--standard-root", str(Path(__file__).resolve().parents[2] / "AI-Novel-Standard"),
            "--schema-dir", str(Path(__file__).resolve().parents[2] / "AI-Novel-Standard" / "phase-1" / "generated" / "json-schema"),
            "--model-provider", "deterministic",
            "--model-id", "mock",
            "--reviewer", "unanchored",
        ])
    freeze_path = root / "registry" / "derived" / "baseline-freezes" / f"{PRECHECK_BASELINE_ID}.json"
    assert freeze_path.exists()
    assert code in (0, 1)
    assert "baseline freeze" in buf.getvalue()


def test_serial_freeze_writes_three_chapter_baseline(tmp_path):
    root = tmp_path / "project"
    (root / "registry" / "_meta").mkdir(parents=True)
    (root / "registry" / "_meta" / "registry-version").write_text("1\n", encoding="utf-8")
    (root / "registry" / "_meta" / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main([
            "serial", "freeze",
            "--project", str(root),
            "--standard-root", str(Path(__file__).resolve().parents[2] / "AI-Novel-Standard"),
            "--schema-dir", str(Path(__file__).resolve().parents[2] / "AI-Novel-Standard" / "phase-1" / "generated" / "json-schema"),
            "--model-provider", "deterministic",
            "--model-id", "mock",
            "--reviewer", "unanchored",
        ])
    freeze_path = root / "registry" / "derived" / "baseline-freezes" / f"{BASELINE_3CH_ID}.json"
    assert freeze_path.exists()
    assert code in (0, 1)
    assert "baseline-freeze" in buf.getvalue()
