"""measure.py — measure a reference chapter with the SAME instruments as generated.

This is the heart of the quality anchor: the reference novels are run through the
EXACT deterministic detector `*_summary` functions the runtime already runs on
generated chapter bodies (density / ai_taste / hook / length). Because the
instruments are identical, a reference chapter and a generated chapter produce
directly comparable feature vectors — no fabricated correspondence.

DISCIPLINE:
  - Imports NO model (guard-enforced): the deterministic arm is pure, same body
    => same features. The optional judge arm (double-measure) is injected by the
    caller as a reviewer, so this module never imports the LM stack.
  - COMPARISON-ONLY / advisory: features are raw numbers for later gap analysis,
    never a gate.
"""
from __future__ import annotations

from typing import Optional

from ..execution.density import density_summary
from ..execution.humanization import ai_taste_summary
from ..execution.hook_check import hook_summary
from ..execution.length_check import length_summary

# The deterministic feature keys, namespaced by detector so a generated chapter's
# measurement (same functions) lines up 1:1 with the reference. Booleans (hook
# flags) are carried as 0/1 so they aggregate into a rate across chapters. Only
# the CONTINUOUS, comparable features are listed for banding; identity/size
# features (total_chars, sentence_count, target_chars) are measured but excluded
# from the gap band because they are not quality signals on their own.
DETERMINISTIC_FEATURES = (
    "density.dialogue_ratio",
    "density.simile_per_1000",
    "density.opening_simile_per_1000",
    "ai_taste.anaphora_run",
    "ai_taste.dash_aside_per_1000",
    "ai_taste.sentence_length_cv",
    "hook.has_question",
    "hook.has_suspension",
    "hook.has_turn",
    "hook.has_closure",
)


def _flatten(prefix: str, summary: Optional[dict]) -> dict:
    """Namespace a detector summary's keys as prefix.key, coercing booleans to
    0/1 so downstream aggregation treats a hook flag as a per-chapter rate."""
    if not summary:
        return {}
    out = {}
    for k, v in summary.items():
        if isinstance(v, bool):
            v = 1 if v else 0
        out[f"{prefix}.{k}"] = v
    return out


def measure_reference_chapter(body: str, *, target_wordcount: Optional[int] = None,
                              reviewer=None) -> dict:
    """Measure one reference chapter body into a flat feature vector.

    The deterministic arm always runs (density / ai_taste / hook / length). The
    judge arm runs ONLY when a `reviewer` (a DraftReviewer, e.g. the LMQualityJudge)
    is supplied — the double-measure that lets us later check whether the judge
    scores a market-validated chapter meaningfully higher than a mediocre generated
    one. Returns {} for an empty body.

    Deterministic given (body, target); the judge arm's determinism follows the
    reviewer (temp-0 => stable)."""
    text = (body or "").strip()
    if not text:
        return {}
    features: dict = {}
    features.update(_flatten("density", density_summary(text)))
    features.update(_flatten("ai_taste", ai_taste_summary(text)))
    features.update(_flatten("hook", hook_summary(text)))
    features.update(_flatten("length", length_summary(text, target=target_wordcount)))

    if reviewer is not None:
        # The judge arm rides beside the deterministic features under a `judge.`
        # namespace. The reviewer takes an artifact ({"body": ...}); its report's
        # scores (if any) are flattened. A deterministic reviewer with no scores
        # simply contributes nothing — the arm degrades cleanly.
        report = reviewer.review({"body": text}, {})
        rd = report.to_dict() if hasattr(report, "to_dict") else (report or {})
        scores = rd.get("scores") if isinstance(rd, dict) else None
        if isinstance(scores, dict):
            for k, v in scores.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    features[f"judge.{k}"] = v
    return features
