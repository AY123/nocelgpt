from __future__ import annotations

import json
from pathlib import Path


def test_artifact_catalog_sections_and_references():
    root = Path(__file__).resolve().parents[1] / "quality-golden-set" / "metadata"
    catalog = json.loads((root / "artifact-catalog.json").read_text(encoding="utf-8"))

    assert catalog["kind"] == "artifact_catalog"
    assert catalog["governance"]["catalog_is_read_only"] is True
    sections = {section["section"] for section in catalog["sections"]}
    assert {"quality", "reference_and_genesis", "release_and_scale"}.issubset(sections)
