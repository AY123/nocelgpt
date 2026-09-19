"""compare.py — Director version comparison.

Compares multiple draft versions and emits a structured comparison report. This
module is advisory and read-side: it never writes facts, never publishes, and
never calibrates real reader signals.

THIN ADAPTER (Phase 7): the director does NOT invent a scorer here. Each version
carries a `director_score` supplied by an existing advisory signal — the
Commercial Loop's reader simulation (`commercial.compare_simulations`) or a
quality review. Comparison only ranks the scores it is given; when a version
arrives unscored we fall back to input order (a stable, explicit tie-break),
and we record the decision metadata so the selection remains auditable rather
than magically inferred. This keeps the director an ARBITER over existing
signals, not a third rewrite/scoring engine.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Optional

from jsonschema import Draft202012Validator

# NOTE: filter_w9_decision_scores is imported lazily at its two call sites below.
# A top-level `from ..serialize.w9_policy import ...` pulls in serialize/__init__
# -> loop -> chapter -> director.compare, a circular import that breaks collection
# of every test transitively importing the chapter/serialize stack (regression
# introduced by b49fc62). w9_policy itself is standalone; the cycle is only the
# package __init__ path, so a lazy import inside the functions avoids it.

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "AI-Novel-Standard" / "contracts" / "version-comparison.schema.json"
_WORD_RE = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+")


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _tokens(text: str) -> list[str]:
    return _WORD_RE.findall(text or "")


def _length_stats(text: str) -> dict[str, int]:
    chars = len(text or "")
    words = len(_tokens(text))
    lines = len((text or "").splitlines()) if text else 0
    return {"chars": chars, "words": words, "lines": lines}


def _diff_summary(before: str, after: str) -> dict[str, Any]:
    before_tokens = _tokens(before)
    after_tokens = _tokens(after)
    before_count = Counter(before_tokens)
    after_count = Counter(after_tokens)
    added = sum(max(after_count[t] - before_count[t], 0) for t in after_count)
    removed = sum(max(before_count[t] - after_count[t], 0) for t in before_count)
    baseline = max(len(before_tokens), 1)
    change_rate = round(((added + removed) / baseline) * 100, 2)
    return {
        "added_tokens": added,
        "removed_tokens": removed,
        "change_rate_percent": change_rate,
        "added_terms": [t for t in after_count if after_count[t] > before_count[t]][:12],
        "removed_terms": [t for t in before_count if before_count[t] > after_count[t]][:12],
        "before_length": _length_stats(before),
        "after_length": _length_stats(after),
    }


def _qa_delta(before: dict, after: dict) -> dict[str, Any]:
    before_scores = before.get("scores") or {}
    after_scores = after.get("scores") or {}
    keys = sorted(set(before_scores) | set(after_scores))
    score_delta = {k: round(float(after_scores.get(k, 0)) - float(before_scores.get(k, 0)), 4) for k in keys}
    return {
        "before_verdict": before.get("overall_verdict"),
        "after_verdict": after.get("overall_verdict"),
        "score_delta": score_delta,
        "issues_added": [x for x in (after.get("issues") or []) if x not in (before.get("issues") or [])],
        "issues_removed": [x for x in (before.get("issues") or []) if x not in (after.get("issues") or [])],
        "strengths_added": [x for x in (after.get("strengths") or []) if x not in (before.get("strengths") or [])],
        "strengths_removed": [x for x in (before.get("strengths") or []) if x not in (after.get("strengths") or [])],
    }


def _text_summary(before: str, after: str) -> dict[str, Any]:
    before_len = _length_stats(before)
    after_len = _length_stats(after)
    return {
        "before": before_len,
        "after": after_len,
        "delta_chars": after_len["chars"] - before_len["chars"],
        "delta_words": after_len["words"] - before_len["words"],
        "delta_lines": after_len["lines"] - before_len["lines"],
    }


def _commercial_delta(before: str, after: str, brief: Optional[dict], objective: Optional[dict]) -> dict[str, Any]:
    before_len = _length_stats(before)
    after_len = _length_stats(after)
    hook_target = (objective or {}).get("hook_target") or (brief or {}).get("hook_target")
    commercial_target = (objective or {}).get("commercial_target") or (brief or {}).get("commercial_target")
    delta_words = after_len["words"] - before_len["words"]
    delta_chars = after_len["chars"] - before_len["chars"]
    return {
        "hook_alignment": "stronger" if hook_target and delta_chars >= 0 else "stable",
        "commercial_target": commercial_target,
        "hook_target": hook_target,
        "pacing_shift_words": delta_words,
        "length_delta_words": delta_words,
        "retention_signal": "improved" if delta_words >= 0 else "neutral",
    }


def _risk_and_recovery(before_review: dict, after_review: dict, commercial_change: dict[str, Any]) -> dict[str, Any]:
    before_verdict = before_review.get("overall_verdict")
    after_verdict = after_review.get("overall_verdict")
    risks = []
    if commercial_change.get("hook_alignment") != "stronger":
        risks.append("hook_strength_not_improved")
    if after_verdict and before_verdict and after_verdict != before_verdict:
        risks.append("qa_verdict_shift")
    if (commercial_change.get("pacing_shift_words") or 0) < 0:
        risks.append("pacing_contracted")
    return {
        "risks": risks,
        "recovery_actions": [
            "restore stronger chapter hook",
            "rebalance pacing and scene load",
            "tighten issue-focused QA pass",
        ] if risks else [],
        "verdict_shift": [before_verdict, after_verdict],
        "recommendation": "accept" if not risks else ("revise" if len(risks) < 2 else "rollback"),
    }


def _compose_headline(diff: dict[str, Any], qa: dict[str, Any], commercial: dict[str, Any]) -> str:
    change = diff.get("change_rate_percent", 0)
    verdict = qa.get("after_verdict") or qa.get("before_verdict") or "unknown"
    hook = commercial.get("hook_alignment", "stable")
    return f"改动率{change:.2f}%｜QA={verdict}｜商业钩子{hook}"


def _editorial_evaluation(diff: dict[str, Any], qa: dict[str, Any], commercial: dict[str, Any]) -> dict[str, Any]:
    change = diff.get("change_rate_percent", 0)
    qa_delta = qa.get("score_delta") or {}
    qa_gain = sum(v for v in qa_delta.values() if v > 0)
    qa_loss = sum(abs(v) for v in qa_delta.values() if v < 0)
    readability = "improved" if change <= 35 or diff.get("added_tokens", 0) <= diff.get("removed_tokens", 0) + 25 else "needs_attention"
    retention = commercial.get("retention_signal", "neutral")
    market_fit = "strong" if commercial.get("hook_alignment") == "stronger" and retention == "improved" else "moderate"
    editorial_verdict = "accept" if readability == "improved" and qa_loss <= qa_gain else "revise"
    return {
        "readability": readability,
        "retention": retention,
        "market_fit": market_fit,
        "editorial_verdict": editorial_verdict,
        "notes": [
            "整体节奏更顺" if readability == "improved" else "正文变动偏大，需要编辑复核",
            "追读动机有增强" if retention == "improved" else "追读动机变化不明显",
            "题材卖点更清晰" if market_fit == "strong" else "题材卖点对齐度一般",
        ],
    }


def _pipeline_decision(summary: dict[str, Any], editorial: dict[str, Any], risk: dict[str, Any]) -> dict[str, Any]:
    recommendation = summary.get("recommendation")
    verdict = editorial.get("editorial_verdict")
    risks = risk.get("risks") or []
    should_advance = recommendation == "accept" and verdict == "accept" and not risks
    trigger_rewrite = recommendation != "accept" or verdict != "accept" or len(risks) >= 2
    return {
        "advance_to_next_chapter": should_advance,
        "trigger_revision_round": trigger_rewrite,
        "hold_for_human_review": bool(risks),
        "action": "advance" if should_advance else ("revise" if trigger_rewrite else "review"),
        "reasons": {
            "summary_recommendation": recommendation,
            "editorial_verdict": verdict,
            "risk_count": len(risks),
        },
    }


def _selection_metadata(scored: list[dict[str, Any]], winner_index: int, tie_break_applied: bool) -> dict[str, Any]:
    return {
        "winner_index": winner_index,
        "tie_break_applied": tie_break_applied,
        "ranking": [
            {
                "version_id": row["version_id"],
                "score": row["score"],
                "input_index": row["input_index"],
            }
            for row in scored
        ],
    }


def _apply_selection_policy(version: dict[str, Any], decision_scores: dict[str, Any]) -> dict[str, Any]:
    from ..serialize.w9_policy import filter_w9_decision_scores
    cleaned_scores = filter_w9_decision_scores(version.get("policy_root") or version.get("project_path") or "", decision_scores)
    return {**version, "decision_scores": cleaned_scores}


def build_version_comparison(*, chapter_id: str, versions: Iterable[dict],
                             objective: Optional[dict] = None,
                             brief: Optional[dict] = None,
                             long_arc_plan: Optional[dict] = None) -> dict[str, Any]:
    versions = list(versions)
    scored = []
    for idx, v in enumerate(versions, start=1):
        score = v.get("director_score")
        if score is None:
            score = -(idx - 1)
        before_text = v.get("before_text") or ""
        after_text = v.get("after_text") or v.get("text") or ""
        before_review = v.get("before_review") or {}
        after_review = v.get("after_review") or v.get("review") or {}
        commercial_change = _commercial_delta(before_text, after_text, brief, objective)
        from ..serialize.w9_policy import filter_w9_decision_scores
        decision_scores = filter_w9_decision_scores(
            v.get("project_path") or "",
            v.get("dimension_scores") or {},
        )
        scored.append({
            "version_id": v.get("version_id") or v.get("id") or f"v{idx}",
            "input_index": idx - 1,
            "score": score,
            "reason": v.get("reason") or "",
            "decision_score_mean": mean(list(decision_scores.values())) if decision_scores else None,
            "decision_scores": decision_scores,
            "diff_summary": _diff_summary(before_text, after_text),
            "text_summary": _text_summary(before_text, after_text),
            "qa_change": _qa_delta(before_review, after_review),
            "commercial_change": commercial_change,
            "risk_and_recovery": _risk_and_recovery(before_review, after_review, commercial_change),
        })
    best = max(scored, key=lambda x: (x["score"], -x["input_index"])) if scored else None
    best_diff = best["diff_summary"] if best else {"change_rate_percent": 0, "added_tokens": 0, "removed_tokens": 0}
    best_qa = best["qa_change"] if best else {"score_delta": {}}
    best_commercial = best["commercial_change"] if best else {}
    best_risk = best["risk_and_recovery"] if best else {"recommendation": "revise", "risks": [], "recovery_actions": [], "verdict_shift": [None, None]}
    tie_break_applied = False
    if scored:
        top_score = best["score"]
        tie_break_applied = sum(1 for row in scored if row["score"] == top_score) > 1
    summary = {
        "headline": _compose_headline(best_diff, best_qa, best_commercial),
        "major_change_rate_percent": best_diff.get("change_rate_percent", 0),
        "qa_score_deltas": best_qa.get("score_delta", {}),
        "commercial_focus": (objective or {}).get("commercial_target") or (brief or {}).get("commercial_target"),
        "long_arc_band": None,
        "recommendation": best_risk["recommendation"],
        "editorial": _editorial_evaluation(best_diff, best_qa, best_commercial),
    }
    if long_arc_plan:
        for band in long_arc_plan.get("chapter_bands") or []:
            if not isinstance(band, dict):
                continue
            try:
                chapter_no = int("".join(ch for ch in str(chapter_id) if ch.isdigit()) or 0)
            except Exception:
                chapter_no = 0
            if chapter_no and int(band.get("start") or chapter_no) <= chapter_no <= int(band.get("end") or chapter_no):
                summary["long_arc_band"] = {
                    "id": band.get("id"),
                    "goal": band.get("goal"),
                    "commercial_goal": band.get("commercial_goal"),
                }
                break
    risk_summary = {
        "risks": best_risk["risks"],
        "recovery_actions": best_risk["recovery_actions"],
        "verdict_shift": best_risk["verdict_shift"],
    }
    pipeline_decision = _pipeline_decision(summary, summary["editorial"], risk_summary)
    return {
        "id": f"CMP-{chapter_id[-5:] if chapter_id else '00001'}",
        "kind": "version_comparison",
        "authority": "human",
        "gating": False,
        "schema_version": "1.0",
        "chapter_id": chapter_id,
        "objective_ref": (objective or {}).get("id") or (objective or {}).get("objective_id"),
        "brief_ref": (brief or {}).get("id") or (brief or {}).get("brief_id"),
        "versions": scored,
        "winner": best["version_id"] if best else None,
        "selection_policy": {
            "primary_metric": "reader_pull",
            "secondary_metric": "quality_consistency",
            "tie_break": "earlier_input_order",
        },
        "selection_metadata": _selection_metadata(scored, best["input_index"] if best else -1, tie_break_applied),
        "summary": summary,
        "risk_summary": risk_summary,
        "pipeline_decision": pipeline_decision,
        "notes": "Comparison ranks scores supplied by commercial/quality signals; advisory, never gating.",
    }


def validate_version_comparison(obj: dict) -> list[str]:
    validator = Draft202012Validator(_load_schema())
    errs = []
    for e in sorted(validator.iter_errors(obj), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs
