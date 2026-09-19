"""card.py — the per-chapter Production Card (roadmap 4.6).

A deterministic read-side fold of every signal the pipeline already produced for
ONE chapter — its lifecycle status, quality-report v2 scores, commercial-loop
movement, pacing, and (the anchor) its publish-readiness recommendation — into
the single summary a human consults before publishing. No new judgment: every
field is lifted from an existing artifact. Never gates (ADR-003); authority stays
human (ADR-009); the card CITES publish-readiness, it does not recompute it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .. import derived
from ..execution.envelope import unwrap

CARD_VERSION = "1.0"


def _load_draft_envelope(project_path, chapter_id: str) -> Optional[dict]:
    """Load one draft's on-disk envelope by chapter id, or None if missing/broken.
    Mirrors the dashboard's reader; kept local so publishing has no dependency on
    the dashboard subdomain."""
    index = derived._load_index(project_path)
    entry = next((e for e in index.get("artifacts", [])
                  if e.get("category") == "drafts" and e.get("id") == chapter_id), None)
    if entry is None:
        return None
    path = Path(project_path) / entry.get("path", "")
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _pacing_for(project_path, chapter_id: str) -> Optional[dict]:
    """Recompute the chapter's intra-chapter pacing from its persisted scene plan,
    if one exists. None when absent — pacing is optional."""
    entry = next((e for e in derived._load_index(project_path).get("artifacts", [])
                  if e.get("category") == "scene-plan" and e.get("id") == chapter_id), None)
    if entry is None:
        return None
    path = Path(project_path) / entry.get("path", "")
    if not path.exists():
        return None
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    from ..scene import check_pacing, curve_summary
    report = check_pacing(plan).to_dict()
    warnings = sum(1 for f in report["findings"] if f["severity"] == "warning")
    out = {"warnings": warnings}
    summary = curve_summary(plan)
    if summary is not None:
        out["peak"] = summary["peak"]
    return out


def _status_for(project_path, chapter_id: str, published_log: Optional[dict]) -> str:
    """The chapter's highest lifecycle stage, reusing the inventory projection so
    the card and the funnel never disagree."""
    from ..inventory import project_inventory
    funnel = project_inventory(project_path, published_log=published_log)
    for ch in funnel.chapters:
        if ch["task_id"] == chapter_id:
            return ch["status"]
    return "drafted"


# quality dims lifted onto the card (the operable commercial signals + drop risk)
_CARD_QUALITY_DIMS = ("retention", "subscription", "payoff", "reader_drop_risk")
# reader_drop_risk at/above this is flagged (mirrors publish_readiness.DROP_RISK_HOLD_AT)
_DROP_RISK_FLAG_AT = 60


def _publish_readiness_block(obj: Optional[dict], chapter_id: str) -> dict:
    """CITE the publish-readiness verdict from the draft envelope; NEVER recompute
    it. This is the card's anchor and the card is a pure read-side fold: it
    introduces no new judgment (production-card.schema.json — "Lifted from the
    draft envelope's publish_readiness, not recomputed. Absent envelope degrades
    to recommendation='unknown'.").

    The M7 gate is the UPSTREAM source of truth, but it runs on the PRODUCTION
    path (execution.run / serialize.loop fold it into the envelope's
    publish_readiness), not here. Re-running assess_m7 in the card would (a) turn
    an un-assessed chapter's 'unknown' into a spurious 'recommend', and (b) make
    the read-side card non-deterministic w.r.t. the reference corpus — both break
    the frozen contract. So a chapter with no readiness on its envelope stays
    'unknown' (the _flags step raises 'publish-unknown' for triage)."""
    pub = obj.get("publish_readiness") if isinstance(obj, dict) else None
    if isinstance(pub, dict) and pub.get("recommendation"):
        return {
            "recommendation": pub["recommendation"],
            "redline_passed": (pub.get("basis", {}).get("redline", {}) or {}).get("passed"),
            "rationale": pub.get("rationale", ""),
        }
    return {
        "recommendation": "unknown",
        "redline_passed": None,
        "rationale": "该章草稿信封未携带发布就绪判定（未评估）。",
    }


def _quality_block(obj: Optional[dict]) -> Optional[dict]:
    qa = obj.get("qa_review") if isinstance(obj, dict) else None
    scores = qa.get("scores") if isinstance(qa, dict) else None
    if not isinstance(scores, dict) or not scores:
        return None
    block = {"reviewer": qa.get("reviewer", "")}
    for dim in _CARD_QUALITY_DIMS:
        if isinstance(scores.get(dim), (int, float)):
            block[dim] = int(scores[dim])
    return block


def _commercial_block(obj: Optional[dict]) -> Optional[dict]:
    sess = obj.get("commercial_session") if isinstance(obj, dict) else None
    if not isinstance(sess, dict):
        return None
    block = {"verdict": sess.get("verdict", "")}
    rounds = sess.get("rounds") or []
    pay_deltas = [r["mean_pay_probability_delta"] for r in rounds
                  if isinstance(r, dict) and "mean_pay_probability_delta" in r]
    pay_leak = sorted({n for r in rounds if isinstance(r, dict)
                       for n in (r.get("newly_pay_lost") or [])})
    if pay_deltas or pay_leak:
        block["pay_probability_delta"] = sum(pay_deltas)
        block["pay_leak_personas"] = pay_leak
    return block


def _flags(status: str, readiness: dict, quality: Optional[dict],
           commercial: Optional[dict], pacing: Optional[dict]) -> list:
    """Deterministic attention flags for triage. Never gate — a human reads them."""
    flags = []
    rec = readiness.get("recommendation")
    if rec == "block":
        flags.append("publish-blocked")
    elif rec == "hold":
        flags.append("publish-hold")
    elif rec == "unknown":
        # no publish-readiness on the envelope — distinct from the lifecycle
        # 'reviewed' status (which is about qa_review), so name it for the
        # publish axis to avoid contradicting the status field.
        flags.append("publish-unknown")
    if quality and isinstance(quality.get("reader_drop_risk"), int) \
            and quality["reader_drop_risk"] >= _DROP_RISK_FLAG_AT:
        flags.append("high-drop-risk")
    if commercial and commercial.get("pay_leak_personas"):
        flags.append("pay-leak")
    if pacing and pacing.get("warnings", 0) > 0:
        flags.append("pacing-warning")
    return flags


def build_production_card(project_path, chapter_id: str, *,
                          published_log: Optional[dict] = None,
                          card_id: Optional[str] = None) -> dict:
    """Fold every existing signal for ONE chapter into a Production Card dict that
    validates against production-card.schema.json. Pure + deterministic; never
    gates (ADR-003); authority stays human (ADR-009)."""
    obj = _load_draft_envelope(project_path, chapter_id)
    status = _status_for(project_path, chapter_id, published_log)
    readiness = _publish_readiness_block(obj, chapter_id)
    quality = _quality_block(obj)
    commercial = _commercial_block(obj)
    pacing = _pacing_for(project_path, chapter_id)
    flags = _flags(status, readiness, quality, commercial, pacing)

    rec = readiness["recommendation"]
    rationale = f"{chapter_id}: status={status}, publish={rec}"
    if flags:
        rationale += f", flags={','.join(flags)}"

    card = {
        "id": card_id or f"PCARD-{chapter_id}",
        "kind": "production_card",
        "version": CARD_VERSION,
        "authority": "human",   # structural invariant (ADR-009)
        "gating": False,        # structural invariant (ADR-003)
        "chapter_id": chapter_id,
        "status": status,
        "publish_readiness": readiness,
        "flags": flags,
        "rationale": rationale,
    }
    if obj is not None:
        ch = unwrap(obj).get("content_hash")
        if ch:
            card["draft_content_hash"] = ch
    if quality is not None:
        card["quality"] = quality
    if commercial is not None:
        card["commercial"] = commercial
    if pacing is not None:
        card["pacing"] = pacing
    return card


def write_production_card(project_path, card: dict) -> str:
    """Persist a card under registry/derived/production-card/. A derived artifact
    (ADR-006), NEVER a fact. Returns the project-relative path."""
    project = Path(project_path)
    out_dir = project / "registry" / "derived" / "production-card"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{card['id']}.json"
    path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return str(path.relative_to(project))
