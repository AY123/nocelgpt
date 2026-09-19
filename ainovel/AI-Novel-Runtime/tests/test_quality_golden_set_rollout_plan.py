from __future__ import annotations

import json
from pathlib import Path


def test_rollout_plan_matches_target_and_index_refs():
    root = Path(__file__).resolve().parents[1] / "quality-golden-set" / "metadata"
    rollout = json.loads((root / "rollout-plan.json").read_text(encoding="utf-8"))
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))

    assert rollout["sample_count_target"] == 100
    assert len(rollout["phases"]) == 4
    assert index["rollout_plan_ref"] == "metadata/rollout-plan.json"
    assert sum(phase["count"] for phase in rollout["phases"]) == 100
