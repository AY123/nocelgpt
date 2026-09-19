from __future__ import annotations

import json
from pathlib import Path


def test_reviewer_calibration_schema_and_template():
    root = Path(__file__).resolve().parents[1] / "quality-golden-set" / "metadata"
    schema = json.loads((root / "reviewer-calibration-schema.json").read_text(encoding="utf-8"))
    template = json.loads((root / "calibration-template.json").read_text(encoding="utf-8"))
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))

    assert schema["kind"] == "reviewer_calibration_schema"
    assert schema["guardrails"]["simulator_cannot_gate_publish"] is True
    assert template["decision_mode"] == "calibration"
    assert template["recommendation"] == "review_only"
    assert index["reviewer_calibration_schema_ref"] == "metadata/reviewer-calibration-schema.json"
