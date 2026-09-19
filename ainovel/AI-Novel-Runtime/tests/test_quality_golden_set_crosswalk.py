from __future__ import annotations

import json
from pathlib import Path


def test_crosswalk_covers_rubric_and_categories():
    root = Path(__file__).resolve().parents[1] / "quality-golden-set" / "metadata"
    crosswalk = json.loads((root / "crosswalk.json").read_text(encoding="utf-8"))
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))

    categories = set(index["sample_categories"])
    mapped_categories = {rule["sample_category"] for rule in crosswalk["rules"]}
    assert mapped_categories == categories
    assert crosswalk["coverage_requirements"]["every_rubric_dimension_must_appear_as_primary_or_secondary"] is True
    assert index["crosswalk_ref"] == "metadata/crosswalk.json"
