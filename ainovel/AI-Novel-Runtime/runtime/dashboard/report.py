"""report.py — Novel Dashboard (ANES v2, roadmap P18).

The dashboard is a pure READ-SIDE aggregation: it folds together the structured
products the pipeline already produces — the Story State projection (P14), the
Novel Brain (P15), the serialization schedule (P17), and the derived draft index
plus the QA / commercial signals riding each draft's envelope (P16) — into one
project-wide panorama.

It introduces NO new state and computes nothing authoritative: every number is
read from an existing artifact or recomputed by an existing projection. It is
ADVISORY and never gates (ADR-003); it reads only and never writes facts
(ADR-006). Every source degrades gracefully when absent, so even an empty
project yields a (mostly zero) dashboard rather than an error.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from .. import derived, registry_loader
from ..brain import load_brain, validate_brain
from ..memory.state import project_state
from ..execution.envelope import unwrap
from ..schedule import load_plan, validate_plan, project_schedule
from ..inventory import load_published_log, project_inventory
from ..scene import check_pacing, curve_summary, check_serial_pacing
from ..execution.quality_center import is_degraded_scores, _overall_quality
from ..signals import signal_for_chapter, reconcile_signal
from ..reference import (load_reference_profile, measure_reference_chapter,
                         compare_to_profile)
from ..text_metrics import count_words
from ..signals import load_reader_signals
from ..serialize.million_word_stability import build_million_word_stability_report
from ..serialize.platform_feedback_reconciliation import reconcile_platform_feedback
from ..serialize.commercial_calibration import build_commercial_calibration


@dataclass(frozen=True)
class DashboardReport:
    reviewer: str
    story: dict = field(default_factory=dict)
    brain: dict = field(default_factory=dict)
    schedule: Optional[dict] = None
    production: dict = field(default_factory=dict)
    latest_signals: dict = field(default_factory=dict)
    quality_trend: Optional[dict] = None
    retention_curve: Optional[dict] = None
    reference_anchor: Optional[dict] = None
    judge_bias_divergence: Optional[dict] = None
    pacing: Optional[dict] = None
    chapter_final_compare: Optional[dict] = None
    chapter_final_compare_editor: Optional[dict] = None
    chapter_final_compare_decision: Optional[dict] = None
    chapter_final_compare_ops: Optional[dict] = None
    book_health: dict = field(default_factory=dict)
    director: Optional[dict] = None
    mandate: Optional[dict] = None
    openings: Optional[dict] = None
    pipeline: Optional[dict] = None
    narrative_state: Optional[dict] = None
    m5_closeout: Optional[dict] = None
    quality_sentinel: Optional[dict] = None
    stability: Optional[dict] = None
    platform_feedback: Optional[dict] = None
    commercial_calibration: Optional[dict] = None
    gating: bool = False

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "gating": self.gating,
            "story": self.story,
            "brain": self.brain,
            "schedule": self.schedule,
            "production": self.production,
            "latest_signals": self.latest_signals,
            "quality_trend": self.quality_trend,
            "retention_curve": self.retention_curve,
            "reference_anchor": self.reference_anchor,
            "judge_bias_divergence": self.judge_bias_divergence,
            "pacing": self.pacing,
            "chapter_final_compare": self.chapter_final_compare,
            "chapter_final_compare_editor": self.chapter_final_compare_editor,
            "chapter_final_compare_decision": self.chapter_final_compare_decision,
            "chapter_final_compare_ops": self.chapter_final_compare_ops,
            "book_health": self.book_health,
            "director": self.director,
            "mandate": self.mandate,
            "openings": self.openings,
            "pipeline": self.pipeline,
            "narrative_state": self.narrative_state,
            "m5_closeout": self.m5_closeout,
            "quality_sentinel": self.quality_sentinel,
            "stability": self.stability,
            "platform_feedback": self.platform_feedback,
            "commercial_calibration": self.commercial_calibration,
        }


def _story_section(reg) -> dict:
    state = project_state(reg)
    resolved = len(state.resolved_setups)
    total_setups = resolved + len(state.open_setups)
    return {"events": len(state.event_order), "characters": len(state.characters), "items": len(state.items), "relationships": len(state.relationships), "active_relationships": sum(1 for v in state.relationships.values() if v.get("active")), "timelines": len(state.timelines), "setups_total": total_setups, "setups_resolved": resolved, "setups_open": len(state.open_setups), "state_hash": state.state_hash}


def _brain_section(project_path, standard_root) -> dict:
    brain = load_brain(project_path)
    if brain is None:
        return {"authored": False}
    errors = validate_brain(brain, standard_root=standard_root)
    genre = brain.get("genre", {}) if isinstance(brain, dict) else {}
    return {"authored": True, "valid": not errors, "id": brain.get("id"), "mission": brain.get("mission", ""), "genre": genre.get("primary"), "channel": genre.get("channel"), "promise": brain.get("promise", "")}


def _production_section(project_path, *, ready_target: int = 0) -> dict:
    index = derived._load_index(project_path)
    drafts = sorted(e["id"] for e in index.get("artifacts", []) if e.get("category") == "drafts")
    log = load_published_log(project_path)
    funnel = project_inventory(project_path, published_log=log, ready_target=ready_target).to_dict()
    return {"chapters_produced": len(drafts), "latest_chapter": drafts[-1] if drafts else None, "chapter_ids": drafts, "funnel": {"drafted": funnel["drafted"], "reviewed": funnel["reviewed"], "published": funnel["published"], "ready": funnel["ready"], "ready_target": funnel["ready_target"], "thin_stock": funnel["thin_stock"]}}


def _load_draft_envelope(project_path, chapter_id: str) -> Optional[dict]:
    index = derived._load_index(project_path)
    entry = next((e for e in index.get("artifacts", []) if e.get("category") == "drafts" and e.get("id") == chapter_id), None)
    if entry is None:
        return None
    path = Path(project_path) / entry.get("path", "")
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _load_chapter_final(project_path, chapter_id: str) -> Optional[dict]:
    index = derived._load_index(project_path)
    entry = next((e for e in index.get("artifacts", []) if e.get("category") == "chapter-final" and e.get("id") == f"final-{chapter_id}"), None)
    if entry is None:
        return None
    path = Path(project_path) / entry.get("path", "")
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _chapter_final_compare_section(project_path, production: dict) -> Optional[dict]:
    chapter_ids = production.get("chapter_ids") or []
    if not chapter_ids:
        return None
    rows = []
    for cid in chapter_ids:
        draft = _load_draft_envelope(project_path, cid)
        final = _load_chapter_final(project_path, cid)
        if draft is None and final is None:
            continue
        draft_payload = (draft or {}).get("draft") or {}
        draft_text = draft_payload.get("text") or draft_payload.get("body") or ""
        final_text = (final or {}).get("final_text") or ""
        compare = (final or {}).get("comparison_report") or {}
        summary = compare.get("summary") or {}
        editorial = summary.get("editorial") or {}
        pipeline = compare.get("pipeline_decision") or {}
        rows.append({"chapter": cid, "draft_hash": (draft or {}).get("content_hash") or (draft or {}).get("draft", {}).get("content_hash"), "final_hash": (final or {}).get("content_hash") or (final or {}).get("draft", {}).get("content_hash"), "draft_chars": len(draft_text), "final_chars": len(final_text), "delta_chars": len(final_text) - len(draft_text), "changed": draft_text != final_text, "winner": compare.get("winner"), "headline": summary.get("headline"), "recommendation": summary.get("recommendation"), "editorial_verdict": editorial.get("editorial_verdict"), "pipeline_action": pipeline.get("action"), "risk_count": len((compare.get("risk_summary") or {}).get("risks") or []), "selected_strategy": (compare.get("selection_metadata") or {}).get("selected_strategy")})
    if not rows:
        return None
    changed = [r for r in rows if r["changed"]]
    accepted = [r for r in rows if r.get("recommendation") == "accept"]
    revised = [r for r in rows if r.get("pipeline_action") == "revise"]
    avg_delta = round(sum(r["delta_chars"] for r in rows) / len(rows), 1)
    report = {"chapters_compared": len(rows), "chapters_changed": len(changed), "chapters_accepted": len(accepted), "chapters_revised": len(revised), "avg_delta_chars": avg_delta, "rows": rows, "gating": False}
    report["editor_panel"] = {"chapters_compared": len(rows), "headline_sample": rows[0].get("headline") if rows else None}
    report["decision_panel"] = {"recommended_action": "advance" if len(accepted) == len(rows) else ("revise" if revised else "review"), "accepted_count": len(accepted), "revised_count": len(revised)}
    avg_change_rate = round(
        sum((r["delta_chars"] / r["draft_chars"]) if r["draft_chars"] else 0.0 for r in rows) / len(rows),
        4,
    )
    report["ops_panel"] = {
        "chapters_changed": len(changed),
        "change_rate_avg": avg_change_rate,
        "avg_delta_chars": avg_delta,
        "risk_total": sum(r["risk_count"] for r in rows),
    }
    return report


def _latest_signals_section(project_path, production: dict) -> dict:
    latest = production.get("latest_chapter")
    if not latest:
        return {}
    obj = _load_draft_envelope(project_path, latest)
    if obj is None:
        return {}
    out = {"chapter": latest, "draft_hash": unwrap(obj).get("content_hash")}
    qa = obj.get("qa_review") if isinstance(obj, dict) else None
    if isinstance(qa, dict) and qa.get("scores"):
        out["qa"] = {"reviewer": qa.get("reviewer"), "scores": qa["scores"]}
    commercial = obj.get("commercial_session") if isinstance(obj, dict) else None
    if isinstance(commercial, dict):
        block = {"verdict": commercial.get("verdict"), "terminate_reason": commercial.get("terminate_reason")}
        rounds = commercial.get("rounds") or []
        pay_deltas = [r["mean_pay_probability_delta"] for r in rounds if isinstance(r, dict) and "mean_pay_probability_delta" in r]
        pay_leak = sorted({n for r in rounds if isinstance(r, dict) for n in (r.get("newly_pay_lost") or [])})
        if pay_deltas or pay_leak:
            block["pay_probability_delta"] = sum(pay_deltas)
            block["pay_leak_personas"] = pay_leak
        out["commercial"] = block
    pub = obj.get("publish_readiness") if isinstance(obj, dict) else None
    if isinstance(pub, dict) and pub.get("recommendation"):
        out["publish_readiness"] = {"recommendation": pub["recommendation"], "redline_passed": (pub.get("basis", {}).get("redline", {}) or {}).get("passed"), "rationale": pub.get("rationale", "")}
    return out


_RISK_DIMS = ("originality_risk", "reader_drop_risk", "safety_risk")


def _quality_trend_section(project_path, production: dict) -> Optional[dict]:
    chapter_ids = production.get("chapter_ids") or []
    if not chapter_ids:
        return None
    per_dim_sum: dict = {}
    per_dim_count: dict = {}
    per_chapter: list = []
    scored_chapters = 0
    for cid in chapter_ids:
        obj = _load_draft_envelope(project_path, cid)
        if obj is None:
            continue
        qa = obj.get("qa_review") if isinstance(obj, dict) else None
        scores = qa.get("scores") if isinstance(qa, dict) else None
        if not isinstance(scores, dict) or not scores:
            continue
        scored_chapters += 1
        per_chapter.append({"chapter": cid, "commercial": scores.get("commercial"), "retention": scores.get("retention"), "reader_drop_risk": scores.get("reader_drop_risk")})
        for dim, val in scores.items():
            if not isinstance(val, (int, float)):
                continue
            per_dim_sum[dim] = per_dim_sum.get(dim, 0) + val
            per_dim_count[dim] = per_dim_count.get(dim, 0) + 1
    if scored_chapters == 0:
        return None
    return {"chapters_scored": scored_chapters, "chapters_total": len(chapter_ids), "dimension_averages": {dim: round(per_dim_sum[dim] / per_dim_count[dim], 1) for dim in per_dim_sum}, "dimension_coverage": {dim: per_dim_count[dim] for dim in per_dim_count}, "risk_dimensions": list(_RISK_DIMS), "per_chapter": per_chapter, "gating": False}


_DROP_HOTSPOT_MARGIN = 10.0


def _retention_curve_section(project_path, production: dict) -> Optional[dict]:
    chapter_ids = production.get("chapter_ids") or []
    if not chapter_ids:
        return None
    points: list = []
    for cid in chapter_ids:
        obj = _load_draft_envelope(project_path, cid)
        if obj is None or not isinstance(obj, dict):
            continue
        qa = obj.get("qa_review") if isinstance(obj, dict) else None
        scores = qa.get("scores") if isinstance(qa, dict) else None
        if not isinstance(scores, dict) or not scores:
            continue
        if is_degraded_scores(qa):
            continue
        retention = scores.get("retention")
        drop_risk = scores.get("reader_drop_risk")
        if not isinstance(retention, (int, float)) and not isinstance(drop_risk, (int, float)):
            continue
        reasons: list = []
        sim = obj.get("reader_simulation") if isinstance(obj, dict) else None
        if isinstance(sim, dict):
            for p in sim.get("personas") or []:
                r = p.get("drop_reason")
                if not p.get("would_continue") and r:
                    reasons.append(str(r))
        points.append((cid, retention, drop_risk, reasons))
    if not points:
        return None
    ret_vals = [p[1] for p in points if isinstance(p[1], (int, float))]
    risk_vals = [p[2] for p in points if isinstance(p[2], (int, float))]
    ret_baseline = round(sum(ret_vals) / len(ret_vals), 1) if ret_vals else None
    risk_baseline = round(sum(risk_vals) / len(risk_vals), 1) if risk_vals else None
    per_chapter: list = []
    hotspots: list = []
    chapters_with_signal = 0
    for cid, retention, drop_risk, reasons in points:
        entry = {"chapter": cid}
        if isinstance(retention, (int, float)) and ret_baseline is not None:
            entry["retention_delta"] = round(retention - ret_baseline, 1)
        if isinstance(drop_risk, (int, float)) and risk_baseline is not None:
            entry["drop_risk_delta"] = round(drop_risk - risk_baseline, 1)
        signal = signal_for_chapter(project_path, cid)
        if signal is not None:
            pred_agg = ({"continue_rate": retention} if isinstance(retention, (int, float)) else None)
            recon = reconcile_signal(pred_agg, signal)
            if recon.get("comparisons"):
                chapters_with_signal += 1
                entry["real_signal"] = {"source": recon.get("source"), "collected_at": recon.get("collected_at"), "confidence": recon.get("confidence"), "comparisons": recon.get("comparisons"), "note": recon.get("note")}
        per_chapter.append(entry)
        if (isinstance(drop_risk, (int, float)) and risk_baseline is not None and (drop_risk - risk_baseline) > _DROP_HOTSPOT_MARGIN):
            hot = {"chapter": cid, "drop_risk_delta": round(drop_risk - risk_baseline, 1)}
            if reasons:
                hot["drop_reasons"] = reasons
            hotspots.append(hot)
    return {"chapters_scored": len(points), "chapters_total": len(chapter_ids), "retention_baseline": ret_baseline, "drop_risk_baseline": risk_baseline, "per_chapter": per_chapter, "drop_hotspots": hotspots, "chapters_with_real_signal": chapters_with_signal, "comparison_only": True, "calibrates": False, "gating": False}


def _reference_anchor_section(project_path, production: dict) -> Optional[dict]:
    """Fold each generated chapter's own measurement against the pinned Reference
    Quality Profile (M9) into a per-chapter GAP read: how far each chapter sits
    from what a market-validated chapter looks like. Generated bodies are re-
    measured here with the SAME instruments used on the reference, so the vectors
    line up 1:1. None when no profile is pinned or no chapters exist. Advisory,
    never gates (ADR-003)."""
    profile = load_reference_profile(project_path)
    if profile is None:
        return None
    chapter_ids = production.get("chapter_ids") or []
    if not chapter_ids:
        return None
    per_chapter: list = []
    feature_out: dict = {}     # feature -> count of chapters out-of-band
    total_compared = 0
    total_out = 0
    for cid in chapter_ids:
        obj = _load_draft_envelope(project_path, cid)
        if not isinstance(obj, dict):
            continue
        body = (obj.get("draft") or {}).get("text") or ""
        if not body.strip():
            continue
        measurement = measure_reference_chapter(body)
        gap = compare_to_profile(measurement, profile)
        if gap.get("features_compared", 0) == 0:
            continue
        total_compared += 1
        total_out += gap["out_of_band"]
        offenders = sorted(
            (f for f, g in gap["features"].items() if not g["in_band"]),
            key=lambda f: gap["features"][f].get("band_widths_out") or 0.0,
            reverse=True)
        for f in offenders:
            feature_out[f] = feature_out.get(f, 0) + 1
        per_chapter.append({
            "chapter": cid,
            "features_compared": gap["features_compared"],
            "in_band": gap["in_band"],
            "out_of_band": gap["out_of_band"],
            "top_offenders": offenders[:3],
        })
    if not per_chapter:
        return None
    # Features most often outside the market-validated band, worst first — the
    # anchor's headline: where generated prose most consistently misses.
    persistent = sorted(feature_out.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "profile_id": profile.get("id"),
        "reference_sources": len(profile.get("source_ids") or []),
        "reference_chapters": profile.get("chapters_measured"),
        "chapters_compared": total_compared,
        "avg_features_out_of_band": round(total_out / total_compared, 2),
        "persistent_out_of_band": [{"feature": f, "chapters": n} for f, n in persistent],
        "per_chapter": per_chapter,
        "comparison_only": True,
        "gating": False,
    }


def _judge_bias_divergence_section(project_path, production: dict) -> Optional[dict]:
    """Reverse-utilize the LLM judge's proven bias (M9 acceptance probe): the
    absolute judge scores AI-shaped prose ABOVE market winners, so a HIGH judge
    score is NOT a quality truth — it can mark prose the judge likes precisely
    because it reads tidy/AI, diverging from what the market rewards. This section
    folds that into a signal: chapters whose judge quality is at/above the book
    median (judge approves) AND whose ai_taste features sit OUT of the reference
    anchor's market-validated band (the market says atypical) are the danger zone
    where the judge's approval is least trustworthy — surfaced for a human to
    re-read. It CLAIMS nothing about direction; it flags the intersection the
    probe proved is unreliable. Requires both a pinned reference profile and real
    judge scores. Comparison-only, never gates (ADR-003)."""
    profile = load_reference_profile(project_path)
    if profile is None:
        return None
    chapter_ids = production.get("chapter_ids") or []
    if not chapter_ids:
        return None
    rows: list = []
    for cid in chapter_ids:
        obj = _load_draft_envelope(project_path, cid)
        if not isinstance(obj, dict):
            continue
        qa = obj.get("qa_review") if isinstance(obj, dict) else None
        scores = qa.get("scores") if isinstance(qa, dict) else None
        if not isinstance(scores, dict) or not scores or is_degraded_scores(qa):
            continue
        judge_q = _overall_quality(scores)
        body = (obj.get("draft") or {}).get("text") or (obj.get("draft") or {}).get("body") or ""
        if judge_q is None or not body.strip():
            continue
        gap = compare_to_profile(measure_reference_chapter(body), profile)
        offenders = sorted(
            f for f, g in gap.get("features", {}).items()
            if f.startswith("ai_taste.") and not g["in_band"])
        rows.append({"chapter": cid, "judge_quality": round(judge_q, 1),
                     "ai_taste_out_of_band": len(offenders),
                     "offending_features": offenders})
    if not rows:
        return None
    qs = sorted(r["judge_quality"] for r in rows)
    n = len(qs)
    median = qs[n // 2] if n % 2 else round((qs[n // 2 - 1] + qs[n // 2]) / 2, 1)
    # The danger zone: judge approves (>= book median) AND market anchor disagrees
    # on ai_taste (>=1 feature out-of-band). This is exactly where the probe showed
    # the judge's high score cannot be trusted as a quality verdict.
    suspects = [r for r in rows
                if r["judge_quality"] >= median and r["ai_taste_out_of_band"] > 0]
    suspects.sort(key=lambda r: (r["ai_taste_out_of_band"], r["judge_quality"]),
                  reverse=True)
    return {
        "chapters_analyzed": len(rows),
        "judge_quality_median": median,
        "ai_taste_features_tracked": sorted(
            f for f in profile.get("bands", {}) if f.startswith("ai_taste.")),
        "judge_approved_but_anchor_divergent": len(suspects),
        "suspects": suspects,
        "note": ("high judge score + ai_taste out of the market band = the judge's "
                 "approval is least trustworthy here (M9 probe: judge rewards "
                 "AI-shaped prose over market winners); re-read, do not trust the score"),
        "comparison_only": True,
        "gating": False,
    }


def _outline_cadence(project_path) -> Optional[int]:
    path = Path(project_path) / "registry" / "derived" / "outline" / "OUTLINE-00001.json"
    if not path.exists():
        return None
    try:
        outline = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    c = (outline.get("reward_loop") or {}).get("cadence_chapters")
    return c if isinstance(c, int) and c >= 1 else None


def _pacing_section(project_path) -> Optional[dict]:
    entries = sorted((e for e in derived._load_index(project_path).get("artifacts", []) if e.get("category") == "scene-plan"), key=lambda e: e.get("id", ""))
    if not entries:
        return None
    peaks: list = []
    chapters_with_warnings = 0
    total = 0
    for e in entries:
        path = Path(project_path) / e.get("path", "")
        if not path.exists():
            continue
        try:
            plan = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        total += 1
        report = check_pacing(plan).to_dict()
        if any(f["severity"] == "warning" for f in report["findings"]):
            chapters_with_warnings += 1
        summary = curve_summary(plan)
        if summary is not None:
            peaks.append(summary["peak"])
    section = {"chapters_analyzed": total, "chapters_with_pacing_warnings": chapters_with_warnings, "gating": False}
    if len(peaks) >= 2:
        serial = check_serial_pacing(peaks, cadence=_outline_cadence(project_path)).to_dict()
        section["serial"] = {"peaks": peaks, "warnings": [f["message"] for f in serial["findings"] if f["severity"] == "warning"], "findings": serial["findings"]}
    return section


def _openings_section(project_path) -> Optional[dict]:
    """Cross-chapter 开篇雷同 (§14 anti-AI) as a read-side fold: reads each draft
    body in chapter order and runs check_serial_openings. Advisory, never gates
    (ADR-003). None when fewer than 2 chapters exist to compare."""
    entries = sorted((e for e in derived._load_index(project_path).get("artifacts", [])
                      if e.get("category") == "drafts"), key=lambda e: e.get("id", ""))
    if not entries:
        return None
    bodies: list = []
    for e in entries:
        path = Path(project_path) / e.get("path", "")
        if not path.exists():
            continue
        try:
            env = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        # unwrap the envelope to the inner ChapterDraft (back-compat for a bare
        # pre-envelope draft), where the prose body lives.
        draft = unwrap(env) if isinstance(env, dict) else {}
        bodies.append(draft.get("body", "") if isinstance(draft, dict) else "")
    if len([b for b in bodies if b]) < 2:
        return None
    from ..scene import check_serial_openings
    report = check_serial_openings(bodies).to_dict()
    warnings = [f["message"] for f in report["findings"] if f["severity"] == "warning"]
    return {"chapters_analyzed": len([b for b in bodies if b]),
            "warnings": warnings, "findings": report["findings"], "gating": False}


def _director_section(project_path) -> Optional[dict]:
    index = derived._load_index(project_path)
    artifacts = index.get("artifacts", [])
    obj_entries = sorted((e for e in artifacts if e.get("category") == "chapter-objective"), key=lambda e: e.get("id", ""))
    retention_focus: dict = {}
    payoff_type: dict = {}
    diverged = 0
    for e in obj_entries:
        path = Path(project_path) / e.get("path", "")
        if not path.exists():
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        ci = obj.get("commercial_intent") or {}
        rf = ci.get("retention_focus")
        pt = ci.get("payoff_type")
        if rf:
            retention_focus[rf] = retention_focus.get(rf, 0) + 1
        if pt:
            payoff_type[pt] = payoff_type.get(pt, 0) + 1
        if rf not in (None, "next_chapter_pull") or pt not in (None, "partial_payoff"):
            diverged += 1
    sessions_total = 0
    sessions_with_objective = 0
    for e in (a for a in artifacts if a.get("category") == "drafts"):
        path = Path(project_path) / e.get("path", "")
        if not path.exists():
            continue
        try:
            env = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sess = env.get("director") if isinstance(env, dict) else None
        if not sess:
            continue
        sessions_total += 1
        if sess.get("objective_id"):
            sessions_with_objective += 1
    if not obj_entries and sessions_total == 0:
        return None
    return {"objectives": len(obj_entries), "sessions": sessions_total, "sessions_with_objective": sessions_with_objective, "retention_focus_distribution": retention_focus, "payoff_type_distribution": payoff_type, "feedback_diverged_chapters": diverged, "gating": False}


def _mandate_section(project_path) -> Optional[dict]:
    entries = sorted((e for e in derived._load_index(project_path).get("artifacts", []) if e.get("category") == "narrative-mandate"), key=lambda e: e.get("id", ""))
    if not entries:
        return None
    mandates: list = []
    for e in entries:
        path = Path(project_path) / e.get("path", "")
        if not path.exists():
            continue
        try:
            mandates.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    if not mandates:
        return None
    lukewarm = sum(1 for m in mandates if (m.get("why_now") or {}).get("cost_of_delay") == "none")
    irreversible = sum(1 for m in mandates if (m.get("net_advance") or {}).get("irreversible"))
    ladder = [(m.get("escalation") or {}).get("to_level") for m in mandates]
    section = {"chapters_analyzed": len(mandates), "lukewarm_chapters": lukewarm, "irreversible_advances": irreversible, "escalation_ladder": ladder, "gating": False}
    if len(mandates) >= 2:
        from ..director import check_mandate_series
        series = check_mandate_series(mandates).to_dict()
        section["series"] = {"warnings": [f["message"] for f in series["findings"] if f["severity"] == "warning"], "findings": series["findings"]}
    return section


_RETENTION_WATCH_AT = 60
_DROP_RISK_WATCH_AT = 60


def _book_health_section(schedule, production, quality_trend, pacing, latest_signals, pipeline=None) -> dict:
    reasons: list = []
    health = "healthy"
    def _raise(level: str):
        nonlocal health
        order = {"healthy": 0, "watch": 1, "at_risk": 2}
        if order[level] > order[health]:
            health = level
    if quality_trend:
        avgs = quality_trend.get("dimension_averages", {})
        ret = avgs.get("retention")
        drop = avgs.get("reader_drop_risk")
        if isinstance(ret, (int, float)) and ret < _RETENTION_WATCH_AT:
            _raise("at_risk")
            reasons.append(f"mean retention {ret} below {_RETENTION_WATCH_AT}")
        if isinstance(drop, (int, float)) and drop >= _DROP_RISK_WATCH_AT:
            _raise("at_risk")
            reasons.append(f"mean reader_drop_risk {drop} at/above {_DROP_RISK_WATCH_AT}")
    pr = (latest_signals or {}).get("publish_readiness", {})
    rec = pr.get("recommendation")
    if rec == "block":
        _raise("at_risk"); reasons.append("latest chapter publish-blocked (red-line)")
    elif rec == "hold":
        _raise("watch"); reasons.append("latest chapter on publish-hold")
    comm = (latest_signals or {}).get("commercial", {})
    if isinstance(comm.get("pay_probability_delta"), int) and comm["pay_probability_delta"] < 0:
        _raise("watch"); reasons.append(f"latest commercial pay movement negative ({comm['pay_probability_delta']})")
    if comm.get("pay_leak_personas"):
        _raise("watch"); reasons.append(f"pay leak: {', '.join(comm['pay_leak_personas'])}")
    if schedule:
        if schedule.get("break_risk") == "high":
            _raise("at_risk"); reasons.append("schedule at high break risk (断更预警)")
        elif schedule.get("break_risk") == "low":
            _raise("watch"); reasons.append("schedule break risk low")
    funnel = (production or {}).get("funnel", {})
    if funnel.get("thin_stock"):
        _raise("watch"); reasons.append(f"thin stock: ready={funnel.get('ready')} < target {funnel.get('ready_target')}")
    if pacing:
        if pacing.get("chapters_with_pacing_warnings", 0) > 0:
            _raise("watch"); reasons.append(f"{pacing['chapters_with_pacing_warnings']} chapter(s) with pacing warnings")
        if (pacing.get("serial") or {}).get("warnings"):
            _raise("watch"); reasons.append("serial climax-rhythm warning")
    # Publish-governance backlog (M8-01): a blocked chapter (hard red-line or a
    # rejected M7 review) is a hard at-risk signal — it cannot ship as-is. A
    # chapter awaiting a human M7/publish decision is a watch signal — the
    # pipeline is stalled on human authority (ADR-009), not on a defect.
    if pipeline:
        if pipeline.get("blocked", 0) > 0:
            _raise("at_risk"); reasons.append(f"{pipeline['blocked']} chapter(s) publish-blocked (red-line/originality)")
        if pipeline.get("awaiting_approval", 0) > 0:
            _raise("watch"); reasons.append(f"{pipeline['awaiting_approval']} chapter(s) awaiting human publish approval")
    if not reasons:
        reasons.append("no attention signals")
    return {"health": health, "reasons": reasons, "gating": False}


def _pipeline_section(project_path) -> Optional[dict]:
    """Fold the book-level pipeline stage projection (M8-01) into a dashboard
    section: how many chapters sit at each lifecycle stage
    (drafted→reviewed→assessed→approved→published), plus the governance backlog
    (blocked chapters + chapters awaiting human approval). Pure read-side
    projection; advisory, never gates (ADR-003). Absent drafts => None so an empty
    project's dashboard is unchanged."""
    from ..serialize import project_pipeline
    report = project_pipeline(project_path).to_dict()
    if report.get("total", 0) == 0:
        return None
    blocked_ids = [c["task_id"] for c in report.get("chapters", []) if c.get("blocked")]
    awaiting_ids = [c["task_id"] for c in report.get("chapters", [])
                    if c.get("approval_status") in ("pending", "deferred", "needs_more_info")]
    return {
        "total": report["total"],
        "by_stage": report["by_stage"],
        "blocked": report["blocked"],
        "awaiting_approval": report["awaiting_approval"],
        "blocked_chapters": blocked_ids,
        "awaiting_approval_chapters": awaiting_ids,
        "gating": False,
    }


def _m5_closeout_section() -> dict:
    completed = [
        "winner rule stabilization",
        "candidate strategy normalization",
        "final report shape stabilization",
        "editor / decision / ops dashboard split",
        "end-to-end regression verified",
    ]
    return {"phase": "M5", "status": "closed", "completed_items": len(completed), "completed": completed, "gating": False}


# The per-chapter detectors persisted on each chapter-run artifact whose WARNING
# rate the sentinel tracks over 10-chapter blocks. Each is a ReviewReport
# ({findings:[{severity,...}]}) — the sentinel counts warning chapters per block
# rather than parsing metric text, so it is robust to message wording.
_SENTINEL_DETECTORS = ("ai_taste", "pacing", "density", "end_hook", "meta_reference")


def _has_warning(report: Optional[dict]) -> bool:
    if not isinstance(report, dict):
        return False
    return any(f.get("severity") == "warning" for f in report.get("findings") or [])


def _quality_sentinel_section(project_path, *, block: int = 10) -> Optional[dict]:
    """Long-run quality-trend sentinel (N100-075): fold each chapter-run's prose
    detectors (ai_taste / pacing / density / end_hook) into 10-chapter blocks and
    flag a block whose warning rate WORSENED vs the previous block. Advisory —
    it only ALERTS, never gates (ADR-003), and every number is recomputed from the
    persisted chapter-run artifacts (no new state, ADR-008). None when fewer than
    one full block of chapters exists.

    Warning-RATE per detector (not parsed metric text) keeps this robust to
    message wording — the same signal N100-071/072 target (anaphora / pacing
    template) surfaces here as a rising ai_taste / pacing warning rate over the
    book, so a regression that creeps back is visible without re-reading prose."""
    entries = sorted((e for e in derived._load_index(project_path).get("artifacts", [])
                      if e.get("category") == "chapter-run"), key=lambda e: e.get("id", ""))
    if len(entries) < block:
        return None
    runs: list = []
    for e in entries:
        path = Path(project_path) / e.get("path", "")
        if not path.exists():
            continue
        try:
            runs.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    if len(runs) < block:
        return None

    blocks: list = []
    prev_rates: Optional[dict] = None
    for start in range(0, len(runs), block):
        chunk = runs[start:start + block]
        n = len(chunk)
        rates = {d: round(sum(1 for r in chunk if _has_warning(r.get(d))) / n, 3)
                 for d in _SENTINEL_DETECTORS}
        degraded = []
        if prev_rates is not None:
            for d in _SENTINEL_DETECTORS:
                if rates[d] > prev_rates[d]:
                    degraded.append(d)
        blocks.append({
            "chapters": f"{start + 1}-{start + n}",
            "chapter_count": n,
            "warning_rate": rates,
            "degraded_vs_prev": degraded,
        })
        prev_rates = rates

    alerts = [f"第 {b['chapters']} 章块 {d} 恶化（warning 率升至 {b['warning_rate'][d]:.0%}）"
              for b in blocks for d in b["degraded_vs_prev"]]
    return {"block_size": block, "blocks": blocks, "alerts": alerts,
            "chapters_analyzed": len(runs), "gating": False}


def _narrative_state_section(project_path, reg) -> Optional[dict]:
    """The unified narrative-state readout (M3-B5): conflict phase + pressure,
    protagonist arc, setup/payoff debt, active reader questions, emotion curve
    fatigue. Folds StoryState + the persisted mandate/ir/run artifacts. Advisory,
    never gates (ADR-003). Returns None only when there is nothing to show (no
    facts and no persisted narrative artifacts)."""
    from ..narrative import project_narrative_state
    ns = project_narrative_state(reg, project_path)
    # Nothing produced yet AND no facts folded => no signal to surface.
    if (ns.chapters_folded == 0 and not ns.setup_payoff.get("open_setups")
            and not ns.reader_questions.get("active")
            and ns.main_conflict.get("phase") == "unknown"):
        return None
    mc = ns.main_conflict
    sp = ns.setup_payoff
    ec = ns.emotional_curve
    warnings: list = []
    if sp.get("payoff_pressure") == "high":
        warnings.append(f"payoff debt high: {sp.get('open_count')} open setups unresolved")
    if ec.get("fatigue_risk") == "high":
        warnings.append(f"emotion-curve fatigue risk ({ec.get('current_temperature')} temperature run)")
    return {
        "chapters_folded": ns.chapters_folded,
        "main_conflict": {"phase": mc.get("phase"), "pressure_level": mc.get("pressure_level"),
                          "latest_escalation_kind": mc.get("latest_escalation_kind")},
        "protagonist_arc": ns.protagonist_arc,
        "setup_payoff": {"open_count": sp.get("open_count"), "resolved_count": sp.get("resolved_count"),
                         "payoff_pressure": sp.get("payoff_pressure")},
        "reader_questions": {"active_count": ns.reader_questions.get("active_count")},
        "emotional_curve": {"current_temperature": ec.get("current_temperature"),
                            "recent_peak_chapter": ec.get("recent_peak_chapter"),
                            "fatigue_risk": ec.get("fatigue_risk")},
        "warnings": warnings,
        "gating": False,
    }


def _stability_section(project_path, production: dict) -> Optional[dict]:
    """Y365-02: long-run stability readout. Folds the produced chapters' REAL
    measured word counts + judge scores + folded LLM cost into 50-chapter windows
    and reports whether the back half degrades vs the front half.

    Word counts are measured from the persisted draft body via text_metrics (the
    unified CJK counter), never estimated — a "million word" claim built on
    chapter_count x 3000 would be a fabricated number. Degraded all-zero judge
    reports are excluded from the quality trend, exactly as the retention curve
    and quality sentinel do. Advisory, never gates (ADR-003)."""
    chapter_ids = production.get("chapter_ids") or []
    if not chapter_ids:
        return None
    chapters: list = []
    for idx, cid in enumerate(chapter_ids, start=1):
        obj = _load_draft_envelope(project_path, cid)
        if obj is None or not isinstance(obj, dict):
            continue
        body = (unwrap(obj) or {}).get("body") or ""
        entry: dict = {"chapter_index": idx, "ok": True,
                       "word_count": count_words(body) if body else 0}
        qa = obj.get("qa_review") if isinstance(obj, dict) else None
        scores = qa.get("scores") if isinstance(qa, dict) else None
        if isinstance(scores, dict) and scores and not is_degraded_scores(qa):
            entry["quality"] = {"scores": scores}
        llm = obj.get("produced_by", {}).get("llm") if isinstance(obj.get("produced_by"), dict) else None
        if isinstance(llm, dict) and llm.get("cost"):
            entry["cost"] = {"cost": llm["cost"]}
        chapters.append(entry)
    if not chapters:
        return None
    report = build_million_word_stability_report(
        project_id=str(Path(project_path).name), chapters=chapters, window_size=50)
    data = report.to_dict()
    measured = sum(1 for c in chapters if c.get("word_count"))
    data["word_counts_measured"] = measured
    data["word_counts_estimated"] = len(chapters) - measured
    return data


_REAL_TO_PREDICTED = {"retention_rate": "retention"}


def _platform_feedback_section(project_path, production: dict) -> Optional[dict]:
    """Y365-01: real platform feedback closed loop. Folds the imported
    ReaderSignal store (sources/reader-signals/) into batches and reconciles the
    real metrics against the judge's PREDICTED retention.

    Returns None when no signals are imported — a project has no real signals
    until it ships, and an empty reconciliation must not be dressed up as a
    closed loop. Reads only; never writes facts (ADR-006); never gates
    (ADR-003)."""
    signals = load_reader_signals(project_path)
    if not signals:
        return None
    batches: list = []
    for s in signals:
        conf = s.get("confidence") or {}
        batches.append({
            "batch_id": str(s.get("id") or s.get("chapter_id") or s.get("collected_at") or ""),
            "platform": str(s.get("source") or ""),
            "window_start": str(s.get("collected_at") or ""),
            "window_end": str(s.get("collected_at") or ""),
            "sample_size": int(conf.get("sample_size") or 0),
            "signals": {k: v for k, v in (s.get("metrics") or {}).items()
                        if isinstance(v, (int, float))},
            "confidence": conf.get("level"),
        })
    # The one honest predicted counterpart: the judge's retention score. Other
    # real metrics (打赏/月票/订阅) have no comparable prediction and are reported
    # real-only by the reconciler, matching signals/reconcile.py discipline.
    ret_vals: list = []
    for cid in production.get("chapter_ids") or []:
        obj = _load_draft_envelope(project_path, cid)
        qa = obj.get("qa_review") if isinstance(obj, dict) else None
        scores = qa.get("scores") if isinstance(qa, dict) else None
        if isinstance(scores, dict) and scores and not is_degraded_scores(qa):
            r = scores.get("retention")
            if isinstance(r, (int, float)):
                ret_vals.append(float(r))
    predicted = {"retention_rate": round(sum(ret_vals) / len(ret_vals), 2)} if ret_vals else {}
    report = reconcile_platform_feedback(
        project_id=str(Path(project_path).name), batches=batches,
        predicted_signals=predicted)
    data = report.to_dict()
    data["calibrates"] = False
    return data


def _commercial_calibration_section(project_path, production: dict) -> Optional[dict]:
    """Y365-04: calibrate the SIMULATED commercial signal against real platform
    signals. The simulated reader is an unvalidated instrument (same class as the
    biased judge), so this only ever REPORTS a gap.

    Returns None with no real signals: without platform ground truth every
    metric would be labelled "predicted", which states nothing the retention
    curve doesn't already. Never gates (ADR-003), never calibrates the model."""
    signals = load_reader_signals(project_path)
    if not signals:
        return None
    chapter_ids = production.get("chapter_ids") or []
    simulated: dict = {}
    real: dict = {}
    for cid in chapter_ids:
        signal = signal_for_chapter(project_path, cid)
        if signal is None:
            continue
        obj = _load_draft_envelope(project_path, cid)
        qa = obj.get("qa_review") if isinstance(obj, dict) else None
        scores = qa.get("scores") if isinstance(qa, dict) else None
        if not isinstance(scores, dict) or not scores or is_degraded_scores(qa):
            continue
        metrics = signal.get("metrics") or {}
        for real_key, pred_key in _REAL_TO_PREDICTED.items():
            rv = metrics.get(real_key)
            pv = scores.get(pred_key)
            if isinstance(rv, (int, float)) and isinstance(pv, (int, float)):
                simulated.setdefault(pred_key, []).append(float(pv))
                real.setdefault(pred_key, []).append(float(rv))
    if not simulated:
        return None
    report = build_commercial_calibration(
        project_id=str(Path(project_path).name),
        simulated_signals=simulated, real_signals=real)
    data = report.to_dict()
    data["paired_chapters"] = max((len(v) for v in simulated.values()), default=0)
    return data


def build_dashboard(project_path: str | Path, *, standard_root: Optional[str | Path] = None, today: Optional[date] = None, upcoming_days: int = 5, reviewer_id: str = "dashboard-v1") -> DashboardReport:
    reg = registry_loader.load(project_path)
    schedule = None
    ready_target = 0
    plan = load_plan(project_path)
    if plan is not None and not validate_plan(plan, standard_root=standard_root):
        schedule = project_schedule(project_path, plan, today=today, upcoming_days=upcoming_days).to_dict()
        ready_target = int(plan.get("backlog_target", 0))
    story = _story_section(reg)
    brain = _brain_section(project_path, standard_root)
    production = _production_section(project_path, ready_target=ready_target)
    latest_signals = _latest_signals_section(project_path, production)
    quality_trend = _quality_trend_section(project_path, production)
    retention_curve = _retention_curve_section(project_path, production)
    reference_anchor = _reference_anchor_section(project_path, production)
    judge_bias_divergence = _judge_bias_divergence_section(project_path, production)
    pacing = _pacing_section(project_path)
    chapter_final_compare = _chapter_final_compare_section(project_path, production)
    pipeline = _pipeline_section(project_path)
    book_health = _book_health_section(schedule, production, quality_trend, pacing, latest_signals, pipeline)
    director = _director_section(project_path)
    mandate = _mandate_section(project_path)
    openings = _openings_section(project_path)
    narrative_state = _narrative_state_section(project_path, reg)
    m5_closeout = _m5_closeout_section()
    quality_sentinel = _quality_sentinel_section(project_path)
    stability = _stability_section(project_path, production)
    platform_feedback = _platform_feedback_section(project_path, production)
    commercial_calibration = _commercial_calibration_section(project_path, production)
    return DashboardReport(reviewer=reviewer_id, story=story, brain=brain, schedule=schedule, production=production, latest_signals=latest_signals, quality_trend=quality_trend, retention_curve=retention_curve, reference_anchor=reference_anchor, judge_bias_divergence=judge_bias_divergence, pacing=pacing, chapter_final_compare=chapter_final_compare, chapter_final_compare_editor=(chapter_final_compare or {}).get("editor_panel") if chapter_final_compare else None, chapter_final_compare_decision=(chapter_final_compare or {}).get("decision_panel") if chapter_final_compare else None, chapter_final_compare_ops=(chapter_final_compare or {}).get("ops_panel") if chapter_final_compare else None, book_health=book_health, director=director, mandate=mandate, openings=openings, pipeline=pipeline, narrative_state=narrative_state, m5_closeout=m5_closeout, quality_sentinel=quality_sentinel, stability=stability, platform_feedback=platform_feedback, commercial_calibration=commercial_calibration)
