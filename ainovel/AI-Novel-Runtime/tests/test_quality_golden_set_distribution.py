from __future__ import annotations

import json
from pathlib import Path


def test_golden_set_distribution_sums_to_target():
    root = Path(__file__).resolve().parents[1] / "quality-golden-set" / "metadata"
    distribution = json.loads((root / "distribution.json").read_text(encoding="utf-8"))
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))

    total = sum(item["count"] for item in distribution["category_distribution"])
    assert total == index["sample_count_target"] == 100
    assert distribution["labeling_rules"]["primary_category_required"] is True
    assert index["distribution_ref"] == "metadata/distribution.json"
