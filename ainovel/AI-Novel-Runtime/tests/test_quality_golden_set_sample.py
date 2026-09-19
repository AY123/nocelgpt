from __future__ import annotations

import json
from pathlib import Path


def test_golden_set_sample_skeleton():
    sample = Path(__file__).resolve().parents[1] / "quality-golden-set" / "samples" / "QGS-00001"

    assert sample.exists()
    meta = json.loads((sample / "meta.json").read_text(encoding="utf-8"))
    scores = json.loads((sample / "human_scores.json").read_text(encoding="utf-8"))
    labels = json.loads((sample / "labels.json").read_text(encoding="utf-8"))

    assert meta["sample_id"] == "QGS-00001"
    assert meta["revision_candidate"] is True
    assert scores["final_judgement"] == "use_for_calibration_only"
    assert labels["boundary_case"] is True
