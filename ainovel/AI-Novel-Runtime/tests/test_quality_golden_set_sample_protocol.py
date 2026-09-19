from __future__ import annotations

import json
from pathlib import Path


def test_sample_protocol_and_representative_samples():
    root = Path(__file__).resolve().parents[1] / "quality-golden-set"
    protocol = json.loads((root / "metadata" / "sample-protocol.json").read_text(encoding="utf-8"))

    assert protocol["kind"] == "quality_golden_set_sample_protocol"
    assert "body.txt" in protocol["required_files"]

    for sample_id in ["QGS-00001", "QGS-00002", "QGS-00003"]:
        sample_dir = root / "samples" / sample_id
        assert (sample_dir / "body.txt").exists()
        assert (sample_dir / "meta.json").exists()
        assert (sample_dir / "human_scores.json").exists()
        assert (sample_dir / "labels.json").exists()
        assert (sample_dir / "notes.md").exists()
