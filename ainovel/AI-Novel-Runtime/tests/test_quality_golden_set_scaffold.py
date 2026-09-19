from __future__ import annotations

import json
from pathlib import Path


def test_golden_set_scaffold_exists():
    root = Path(__file__).resolve().parents[1] / "quality-golden-set"

    assert (root / "README.txt").exists()
    schema = json.loads((root / "metadata" / "schema.json").read_text(encoding="utf-8"))
    index = json.loads((root / "metadata" / "index.json").read_text(encoding="utf-8"))

    assert schema["kind"] == "quality_golden_set_schema"
    assert schema["policy"]["double_blind_required"] is True
    assert index["sample_count_target"] == 100
