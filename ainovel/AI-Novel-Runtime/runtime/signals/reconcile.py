"""reconcile.py — place a REAL reader signal beside a PREDICTED simulation.

The comparison-only, never-gating, NEVER-CALIBRATING fold at the heart of P5.6.
The roadmap is explicit: this phase wires the seam a future real-publish
calibration will consume, but it does NOT calibrate — nothing here adjusts the
simulator, the prompt, or generation. It only REPORTS the gap between what the
model predicted and what really happened, for a human to read.

DISCIPLINE (mirrors reader_sim.compare_simulations):
  - `comparison_only` const True: the numbers are meaningful only as a gap, never
    as an absolute score.
  - `gating` const False: a prediction-vs-reality readout never gates a build
    (ADR-003).
  - PURE + DETERMINISTIC: same (prediction, signal) => same readout. No model, no
    I/O, no randomness.
  - HONEST correspondence: only continue_rate ↔ retention_rate is a clean pair
    (both mean "% who kept reading"). Other real metrics are reported side-by-side
    WITHOUT a fabricated predicted counterpart — simulated personas are not real
    readers, and forcing a gap on 打赏/月票 would over-claim.
  - Low `confidence` is surfaced so a noisy real number is never over-read.
"""
from __future__ import annotations

from typing import List, Optional


def _direction(gap: float) -> str:
    """gap = predicted - real. Positive => the model was optimistic."""
    if gap > 5:
        return "prediction optimistic"
    if gap < -5:
        return "prediction pessimistic"
    return "prediction close"


def reconcile_signal(predicted_aggregate: Optional[dict], signal: dict) -> dict:
    """Fold a real reader signal beside a predicted reader-sim aggregate.

    `predicted_aggregate` is a reader-simulation `aggregate` block (or None when no
    prediction was recorded for the chapter). `signal` is a ReaderSignal record.
    Returns a comparison-only, never-gating diagnostic. Never calibrates anything.
    """
    metrics = signal.get("metrics") or {}
    confidence = signal.get("confidence") or {}
    level = confidence.get("level")
    comparisons: List[dict] = []

    # The one clean pair: predicted continue_rate ↔ real retention_rate.
    real_ret = metrics.get("retention_rate")
    pred_cont = (predicted_aggregate or {}).get("continue_rate")
    if real_ret is not None and pred_cont is not None:
        gap = pred_cont - real_ret
        comparisons.append({
            "metric": "retention",
            "predicted": pred_cont,          # simulator continue_rate
            "real": real_ret,                # platform retention_rate
            "gap": gap,                      # predicted - real
            "direction": _direction(gap),
        })

    # Everything else: report the real number with NO fabricated prediction.
    # (Personas are not real readers; a forced 打赏/月票 gap would over-claim.)
    for key in ("subscription_count", "first_day_subscriptions", "drop_rate",
                "reward_count", "monthly_votes", "collection_count"):
        if metrics.get(key) is not None:
            comparisons.append({
                "metric": key,
                "predicted": None,
                "real": metrics[key],
                "gap": None,
                "direction": "no comparable prediction",
            })

    notes: List[str] = []
    if predicted_aggregate is None:
        notes.append("no predicted simulation for this chapter — real-only readout")
    if level == "low":
        notes.append("LOW confidence signal — do not over-read the gap")
    if not comparisons:
        notes.append("signal carries no comparable metrics")

    return {
        "comparison_only": True,     # structural invariant — relative use only
        "gating": False,             # ADR-003 — never gates
        "calibrates": False,         # P5.6 — the seam is wired, not fired
        "chapter_id": signal.get("chapter_id"),
        "scope": signal.get("scope"),
        "source": signal.get("source"),
        "collected_at": signal.get("collected_at"),
        "confidence": level,
        "comparisons": comparisons,
        "note": "; ".join(notes) if notes else "prediction placed beside reality (advisory)",
    }
