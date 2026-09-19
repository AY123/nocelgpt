from __future__ import annotations

import json
from pathlib import Path


def test_seed_manifest_and_sample_roots():
    root = Path(__file__).resolve().parents[1] / "quality-golden-set"
    seed_manifest = json.loads((root / "metadata" / "seed-manifest.json").read_text(encoding="utf-8"))

    assert seed_manifest["seed_count"] == 10
    assert len(seed_manifest["seeds"]) == 10
    assert seed_manifest["seeds"][0]["sample_id"] == "QGS-00001"

    for i in range(1, 11):
        sample_dir = root / "samples" / f"QGS-{i:05d}"
        assert sample_dir.exists()
        assert (sample_dir / "README.txt").exists()
