from __future__ import annotations

import json
from pathlib import Path


def test_master_manifest_references_have_expected_prefixes():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "quality-golden-set" / "metadata" / "master-manifest.json").read_text(encoding="utf-8"))

    refs = {item["name"]: item["ref"] for item in manifest["catalogs"]}
    assert refs["artifact_catalog"].startswith("metadata/")
    assert refs["quality_rubric"] == "../../quality-rubric.yaml"
    assert refs["live_baseline_report"] == "runtime/serialize/live_baseline_report.py"
