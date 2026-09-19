from __future__ import annotations

import json
from pathlib import Path


def test_reference_analysis_schema_and_template():
    root = Path(__file__).resolve().parents[1] / "quality-golden-set" / "metadata"
    schema = json.loads((root / "reference-analysis-schema.json").read_text(encoding="utf-8"))
    template = json.loads((root / "reference-analysis-template.json").read_text(encoding="utf-8"))
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))

    assert schema["kind"] == "reference_analysis_schema"
    assert schema["output_policy"]["llm_output_is_advisory"] is True
    assert template["kind"] == "reference_analysis"
    assert template["analysis_id"] == "RA-00000"
    assert index["reference_analysis_schema_ref"] == "metadata/reference-analysis-schema.json"
