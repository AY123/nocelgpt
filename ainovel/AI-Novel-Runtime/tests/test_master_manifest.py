from __future__ import annotations

import json
from pathlib import Path


def test_master_manifest_references_key_artifacts():
    root = Path(__file__).resolve().parents[1] / "quality-golden-set" / "metadata"
    manifest = json.loads((root / "master-manifest.json").read_text(encoding="utf-8"))

    assert manifest["kind"] == "anovel_master_manifest"
    refs = {item["name"] for item in manifest["catalogs"]}
    assert {"artifact_catalog", "quality_golden_set_index", "quality_rubric", "live_baseline_report"}.issubset(refs)
    assert manifest["governance"]["read_only"] is True
