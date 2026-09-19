"""w9_ai_calibration.py — run the W9 calibration flow with AI consensus as reviewer.

Feeds the AI-simulated consensus scores (from w8_ai_scoring.py's ai_scores.json)
through the REAL calibration code (build_calibration_row / build_calibration_summary)
as the reviewer side, compared against each sample's REAL human_mean. This walks
the whole W9 pipeline end-to-end and emits per-dimension correlation / MAE / level.

DISCIPLINE (hard):
  - Reuses runtime.serialize.reviewer_calibration — no reinvented scoring/stats.
  - Reads real human_scores.json (ground truth) but NEVER writes it.
  - Writes ONLY to metadata/w9-ai-calibration-results.json — never overwrites the
    real w9-calibration-results.json / w9-calibration-summary.json.
  - This validates the flow; it is NOT a real calibration (reviewer = AI, and both
    "editors" were one temp=0 model, so agreement is inflated — see report).

Usage (from AI-Novel-Runtime/):
  PYTHONPATH=. python3 scripts/w9_ai_calibration.py
"""
from __future__ import annotations

import json
from pathlib import Path

from runtime.serialize.reviewer_calibration import (
    DIMENSIONS, build_calibration_row, build_calibration_summary,
    load_sample_human_scores,
)

RT = Path(__file__).resolve().parents[1]
GSET = RT / "quality-golden-set" / "samples"
OUT = RT / "quality-golden-set" / "metadata" / "w9-ai-calibration-results.json"


def main() -> None:
    rows = []
    used = []
    for sd in sorted(GSET.glob("QGS-*")):
        ai_path = sd / "ai_scores.json"
        human_path = sd / "human_scores.json"
        if not ai_path.is_file() or not human_path.is_file():
            continue
        ai = json.loads(ai_path.read_text(encoding="utf-8"))
        consensus = ai.get("consensus_scores") or {}
        # AI consensus stands in for the automated reviewer side
        reviewer_output = {
            "decision_mode": "calibration",
            "dimension_scores": {d: consensus.get(d) for d in DIMENSIONS},
            "uncertainty": "high",
            "recommendation": "review_only",
        }
        human_scores = load_sample_human_scores(sd)  # REAL ground truth, read-only
        row = build_calibration_row(
            sample_id=sd.name,
            sample_category="ai-flow-validation",
            reviewer_output=reviewer_output,
            human_scores=human_scores,
            body_path=sd / "body.txt",
            notes_ref=sd / "notes.md",
            human_score_ref=human_path,
        )
        rows.append(row)
        used.append(sd.name)

    summary = build_calibration_summary(rows)
    results = {
        "kind": "w9_ai_calibration_flow_validation",
        "version": "1.0",
        "disclaimer": ("AI consensus as reviewer vs REAL human_mean. Validates the "
                       "W9 pipeline end-to-end; NOT a real calibration."),
        "sample_count": len(rows),
        "samples": used,
        "summary": summary,
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"calibration rows: {len(rows)} samples")
    print(f"{'dimension':<24}{'corr':>8}{'MAE':>8}{'n':>5}  level")
    for dim in DIMENSIONS:
        s = summary["dimension_stats"][dim]
        corr = f"{s['correlation']:.2f}" if s["correlation"] is not None else "  n/a"
        mae = f"{s['mean_abs_error']:.2f}" if s["mean_abs_error"] is not None else "n/a"
        print(f"{dim:<24}{corr:>8}{mae:>8}{s['sample_count']:>5}  {s['level']}")
    print(f"\ntrusted (n>=5, corr>=0.6): {summary['trusted_dimensions']}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
