from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path

from runtime.cli import main


def test_serial_precheck_and_freeze_paths_exist(tmp_path):
    root = tmp_path / "project"
    (root / "registry" / "_meta").mkdir(parents=True)
    (root / "registry" / "_meta" / "registry-version").write_text("1\n", encoding="utf-8")
    (root / "registry" / "_meta" / "standard.pin").write_text("2.0.0\n", encoding="utf-8")

    buf = io.StringIO()
    with redirect_stdout(buf):
        precheck_code = main([
            "serial", "precheck",
            "--project", str(root),
            "--standard-root", str(Path(__file__).resolve().parents[2] / "AI-Novel-Standard"),
            "--schema-dir", str(Path(__file__).resolve().parents[2] / "AI-Novel-Standard" / "phase-1" / "generated" / "json-schema"),
            "--model-provider", "deterministic",
            "--model-id", "mock",
            "--reviewer", "unanchored",
        ])
    assert precheck_code in (0, 1)
    assert (root / "registry" / "derived" / "baseline-freezes").exists()
    assert "baseline freeze" in buf.getvalue()

    buf = io.StringIO()
    with redirect_stdout(buf):
        freeze_code = main([
            "serial", "freeze",
            "--project", str(root),
            "--standard-root", str(Path(__file__).resolve().parents[2] / "AI-Novel-Standard"),
            "--schema-dir", str(Path(__file__).resolve().parents[2] / "AI-Novel-Standard" / "phase-1" / "generated" / "json-schema"),
            "--model-provider", "deterministic",
            "--model-id", "mock",
            "--reviewer", "unanchored",
        ])
    assert freeze_code in (0, 1)
    assert "baseline-freeze" in buf.getvalue()


def test_serial_baseline_compare_report(tmp_path):
    root = tmp_path / "project"
    (root / "registry" / "derived" / "baseline-freezes").mkdir(parents=True)
    left = root / "registry" / "derived" / "baseline-freezes" / "LEFT.json"
    right = root / "registry" / "derived" / "baseline-freezes" / "RIGHT.json"
    left.write_text('{"baseline_id":"LEFT","chapter_ids":["CH-00001"],"content_hash":"a"}', encoding="utf-8")
    right.write_text('{"baseline_id":"RIGHT","chapter_ids":["CH-00001","CH-00002"],"content_hash":"b"}', encoding="utf-8")

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main([
            "serial", "baseline-compare",
            "--project", str(root),
            "--left-id", "LEFT",
            "--right-id", "RIGHT",
        ])
    assert code in (0, 2)
    assert "baseline comparison" in buf.getvalue()
