from __future__ import annotations

import json
from pathlib import Path

from runtime.serialize import build_real_calibration_report
from runtime.serialize.reviewer_calibration import DIMENSIONS, _mean_scores
from runtime.serialize.reviewer_calibration_cli import build_real_reviewer_output


def test_real_calibration_report_builds_from_subset():
    root = Path(__file__).resolve().parents[1]
    metadata = root / "quality-golden-set" / "metadata"
    subset = json.loads((metadata / "w9-calibration-subset.json").read_text(encoding="utf-8"))

    rows = []
    for item in subset["subset"]:
        sample_dir = root / "quality-golden-set" / "samples" / item["sample_id"]
        human_scores = json.loads((sample_dir / "human_scores.json").read_text(encoding="utf-8"))
        reviewer_output = {
            "decision_mode": "calibration",
            "dimension_scores": {k: v for k, v in human_scores["editor_a"].items()},
            "severity_labels": ["boundary"],
            "continue_probability": 0.5,
            "pay_probability": 0.5,
            "risk_flags": [],
            "evidence_spans": [{"chapter": item["sample_id"], "text": "sample evidence"}],
            "recommendation": "review_only",
            "uncertainty": "high",
        }
        rows.append(
            {
                "sample_id": item["sample_id"],
                "sample_category": item["category"],
                "dimension_scores": reviewer_output["dimension_scores"],
                "comparison": {"human_mean": reviewer_output["dimension_scores"]},
            }
        )

    report = build_real_calibration_report(rows=rows, subset=subset["subset"])
    assert report["kind"] == "w9_reviewer_calibration_report"
    assert report["status"] == "complete"
    assert report["missing_subset_ids"] == []
    assert report["sample_count"] == len(subset["subset"])


def test_reviewer_side_is_independent_of_human_ground_truth():
    """CLOSE-06 regression: the calibration reviewer side must NOT be derived from
    the human scores, or the correlation becomes self-referential (r≈1.0 by
    construction). It must read the independent AI judge (ai_scores.consensus_scores).
    """
    root = Path(__file__).resolve().parents[1]
    samples = root / "quality-golden-set" / "samples"
    checked = 0
    differs_from_human = 0
    for sample_dir in sorted(samples.glob("QGS-*")):
        if not (sample_dir / "ai_scores.json").exists():
            continue  # skeleton seed
        human = json.loads((sample_dir / "human_scores.json").read_text(encoding="utf-8"))
        ai = json.loads((sample_dir / "ai_scores.json").read_text(encoding="utf-8"))
        reviewer = build_real_reviewer_output(sample_dir.name, sample_dir)
        rev_scores = reviewer["dimension_scores"]

        # reviewer side is sourced from the independent AI judge, not human scores
        assert reviewer.get("reviewer_source") == "ai_scores.consensus_scores"
        assert rev_scores == (ai.get("consensus_scores") or {})

        # a genuinely independent judge may coincidentally match a human on a
        # given sample, so independence is asserted by provenance above; here we
        # only tally divergence to prove it is not a wholesale copy book-wide.
        human_mean = _mean_scores(human.get("editor_a") or {}, human.get("editor_b") or {})
        rev_on_dims = {d: rev_scores.get(d) for d in DIMENSIONS}
        if rev_on_dims != {d: human_mean.get(d) for d in DIMENSIONS}:
            differs_from_human += 1
        checked += 1
    assert checked >= 40  # all real (non-skeleton) samples exercised
    # the old bug set reviewer = floor(human_mean) for every sample; a real
    # independent judge diverges from the human mean on the large majority.
    assert differs_from_human >= checked - 2
