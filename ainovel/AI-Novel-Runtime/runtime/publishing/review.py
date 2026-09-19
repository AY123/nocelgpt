"""review.py — periodic Volume / Direction reviews (roadmap 4.6).

A deterministic read-side fold over a WINDOW of chapters: it reuses the per-chapter
Production Cards, averages their quality signals, tallies publish recommendations,
sums commercial pay movement, and synthesizes a window health verdict.

  - scope='volume'    -> ~10-chapter 卷末复盘 (quality/retention health of a block).
  - scope='direction' -> ~30-chapter 大方向复盘. Additionally proposes a revision to
    the authored Market Position (4.5) where production reality diverged from the
    pre-book thesis — the feedback loop that closes Phase 4.

No new judgment model; same inputs => same review. Never gates (ADR-003). The
market_position_revision is a PROPOSAL only — authority stays human (ADR-009), it
is never auto-written to sources/market-position.yaml.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .card import build_production_card, _CARD_QUALITY_DIMS, _DROP_RISK_FLAG_AT

REVIEW_VERSION = "1.0"

VOLUME_SIZE = 10
DIRECTION_SIZE = 30

# window health thresholds (mirror the dashboard book_health synthesis)
_RETENTION_WATCH_AT = 60      # mean retention below this -> at least 'watch'
_DROP_RISK_WATCH_AT = 60      # mean reader_drop_risk at/above this -> 'watch'


def _chapter_window(project_path, scope: str, start_index: int,
                    size: Optional[int]) -> List[str]:
    """The ordered chapter ids in the review window. start_index is 0-based into
    the produced-draft order; size defaults to the scope's nominal size."""
    from .. import derived
    ids = sorted(e["id"] for e in derived._load_index(project_path).get("artifacts", [])
                 if e.get("category") == "drafts")
    n = size if size is not None else (DIRECTION_SIZE if scope == "direction" else VOLUME_SIZE)
    return ids[start_index:start_index + n]


def _summarize(cards: List[dict]) -> dict:
    """Fold the window's cards into averaged quality signals, drop risk, publish
    recommendation counts, commercial movement, pacing warnings, health, and
    deterministic observations."""
    dim_sum: dict = {}
    dim_count: dict = {}
    rec_counts: dict = {}
    pay_movement = 0
    pacing_warn_chapters = 0

    for c in cards:
        q = c.get("quality") or {}
        for dim in _CARD_QUALITY_DIMS:
            if isinstance(q.get(dim), (int, float)):
                dim_sum[dim] = dim_sum.get(dim, 0) + q[dim]
                dim_count[dim] = dim_count.get(dim, 0) + 1
        rec = c.get("publish_readiness", {}).get("recommendation", "unknown")
        rec_counts[rec] = rec_counts.get(rec, 0) + 1
        pay_movement += (c.get("commercial") or {}).get("pay_probability_delta", 0)
        if (c.get("pacing") or {}).get("warnings", 0) > 0:
            pacing_warn_chapters += 1

    averages = {dim: round(dim_sum[dim] / dim_count[dim], 1) for dim in dim_sum}
    mean_drop = averages.get("reader_drop_risk")

    # deterministic health synthesis — SAME precedence as the dashboard
    # book_health (asserted in sync by a test): at_risk > watch > healthy.
    observations: List[str] = []
    health = "healthy"

    def _raise(level: str):
        nonlocal health
        order = {"healthy": 0, "watch": 1, "at_risk": 2}
        if order[level] > order[health]:
            health = level

    if rec_counts.get("block"):
        _raise("at_risk")
        observations.append(f"{rec_counts['block']} chapter(s) publish-blocked (red-line)")
    mean_ret = averages.get("retention")
    if mean_ret is not None and mean_ret < _RETENTION_WATCH_AT:
        _raise("at_risk")
        observations.append(f"mean retention {mean_ret} below {_RETENTION_WATCH_AT}")
    if mean_drop is not None and mean_drop >= _DROP_RISK_WATCH_AT:
        _raise("at_risk")
        observations.append(f"mean reader_drop_risk {mean_drop} at/above {_DROP_RISK_WATCH_AT}")
    if rec_counts.get("hold"):
        _raise("watch")
        observations.append(f"{rec_counts['hold']} chapter(s) on publish-hold")
    if pay_movement < 0:
        _raise("watch")
        observations.append(f"net commercial pay movement negative ({pay_movement})")
    if pacing_warn_chapters:
        _raise("watch")
        observations.append(f"{pacing_warn_chapters} chapter(s) with pacing warnings")
    if not observations:
        observations.append("no attention signals in this window")

    summary = {
        "health": health,
        "quality_averages": averages,
        "mean_reader_drop_risk": mean_drop,
        "publish_recommendation_counts": rec_counts,
        "commercial_pay_movement": pay_movement,
        "pacing_warning_chapters": pacing_warn_chapters,
        "observations": observations,
    }
    return summary


def _position_revision(position: Optional[dict], summary: dict) -> dict:
    """DIRECTION scope: propose concrete Market Position (4.5) edits where the
    30-chapter production reality diverged from the authored thesis. Deterministic
    and evidence-grounded; a PROPOSAL only (never auto-written, ADR-009). Absent
    position -> proposed=False (nothing to revise against)."""
    if position is None:
        return {"proposed": False}

    edits: List[dict] = []
    avgs = summary.get("quality_averages", {})
    mean_ret = avgs.get("retention")
    mean_drop = summary.get("mean_reader_drop_risk")
    promise = position.get("commercial_promise", {}) or {}
    segment = position.get("reader_segment", {}) or {}

    # thesis claimed 100-chapter sustainability, but retention is sagging across
    # 30 chapters -> the long-arc engine isn't holding.
    if mean_ret is not None and mean_ret < _RETENTION_WATCH_AT and promise.get("sustainability_100"):
        edits.append({
            "field": "commercial_promise.sustainability_100",
            "issue": f"authored sustainability thesis '{promise['sustainability_100']}' "
                     f"is not holding: mean retention {mean_ret} over the window",
            "suggestion": "revise the long-arc engine (add a fresh升级线/悬念线) or "
                          "reset expectations for the mid-book stretch",
            "evidence": f"mean retention {mean_ret} < {_RETENTION_WATCH_AT} across "
                        f"{summary['publish_recommendation_counts']}",
        })
    # drop risk elevated -> the segment's drop_triggers were under-designed.
    if mean_drop is not None and mean_drop >= _DROP_RISK_WATCH_AT:
        edits.append({
            "field": "reader_segment.drop_triggers",
            "issue": f"reader drop-risk is elevated (mean {mean_drop}) — real churn "
                     f"drivers exceed the authored drop_triggers",
            "suggestion": "add the observed churn drivers to reader_segment.drop_triggers "
                          "and design against them",
            "evidence": f"mean reader_drop_risk {mean_drop} >= {_DROP_RISK_WATCH_AT}",
        })
    # sustained publish-holds -> pay trigger not landing.
    holds = summary.get("publish_recommendation_counts", {}).get("hold", 0)
    if holds and promise.get("pay_trigger"):
        edits.append({
            "field": "commercial_promise.pay_trigger",
            "issue": f"{holds} chapter(s) on publish-hold — the authored pay trigger "
                     f"'{promise['pay_trigger']}' may not be converting",
            "suggestion": "sharpen or reposition the pay trigger earlier in the arc",
            "evidence": f"{holds} publish-hold chapter(s) in the window",
        })

    block = {"proposed": bool(edits)}
    if position.get("id"):
        block["market_position_id"] = position["id"]
    if edits:
        block["edits"] = edits
    return block


def build_review(project_path, *, scope: str = "volume", start_index: int = 0,
                 size: Optional[int] = None, published_log: Optional[dict] = None,
                 review_id: Optional[str] = None, standard_root=None) -> dict:
    """Fold a window of chapters into a Volume/Direction review dict that validates
    against review-report.schema.json. Pure + deterministic; never gates (ADR-003);
    authority stays human — the market_position_revision is a proposal (ADR-009)."""
    if scope not in ("volume", "direction"):
        raise ValueError(f"scope must be 'volume' or 'direction', got {scope!r}")

    window_ids = _chapter_window(project_path, scope, start_index, size)
    cards = [build_production_card(project_path, cid, published_log=published_log)
             for cid in window_ids]
    summary = _summarize(cards)
    target_size = size if size is not None else (
        DIRECTION_SIZE if scope == "direction" else VOLUME_SIZE)

    review = {
        "id": review_id or f"REVIEW-{scope}-{start_index + 1:05d}",
        "kind": "review_report",
        "version": REVIEW_VERSION,
        "authority": "human",   # structural invariant (ADR-009)
        "gating": False,        # structural invariant (ADR-003)
        "scope": scope,
        "window": {
            "chapters_in_window": len(window_ids),
            "target_size": target_size,
        },
        "summary": summary,
    }
    if window_ids:
        review["window"]["start_chapter"] = window_ids[0]
        review["window"]["end_chapter"] = window_ids[-1]

    sources = {"chapter_ids": window_ids}
    position = None
    brain = None
    if scope == "direction":
        from ..positioning import load_position
        from ..brain import load_brain
        position = load_position(project_path)
        brain = load_brain(project_path)
        revision = _position_revision(position, summary)
        review["market_position_revision"] = revision
        if position and position.get("id"):
            sources["market_position_id"] = position["id"]
        if brain and brain.get("id"):
            sources["novel_brain_id"] = brain["id"]
    review["sources"] = sources

    under = len(window_ids) < target_size
    review["rationale"] = (
        f"{scope} review over {len(window_ids)} chapter(s)"
        f"{' (under target)' if under else ''}: health={summary['health']}")
    return review


def write_review(project_path, review: dict) -> str:
    """Persist a review under registry/derived/review-report/. A derived artifact
    (ADR-006), NEVER a fact. Returns the project-relative path."""
    project = Path(project_path)
    out_dir = project / "registry" / "derived" / "review-report"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{review['id']}.json"
    path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return str(path.relative_to(project))
