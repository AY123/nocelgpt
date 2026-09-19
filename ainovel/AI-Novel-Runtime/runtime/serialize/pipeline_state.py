"""pipeline_state.py — the book-level production pipeline as a projection (M8-01).

Until now the pipeline's stage signals lived in separate silos: the inventory
funnel (P19) knew drafted/reviewed/published, the envelope carried
publish_readiness + M7, and the approval queue (M6) held the human decisions —
but nothing folded them into ONE view answering "which stage is each chapter at,
and what gate is it waiting on?".

`project_pipeline` is that fold. It is a PROJECTION, not mutable state (ADR-008):
same products => same report. It READS only — never writes facts (ADR-006), never
writes the published log (ADR-009). It is ADVISORY and never gates (ADR-003): it
reports where a chapter sits and what a human owes it, it does not block anything.

The lifecycle stages, lowest to highest — a chapter's stage is the HIGHEST it has
reached:

  drafted    -> a draft envelope exists (reuses the inventory funnel)
  reviewed   -> its envelope carries a qa_review with scores
  assessed   -> its envelope carries publish_readiness (M7 folded in)
  approved   -> a human APPROVED its M7/publish review request (ADR-009 gate met)
  published  -> a human authorized it in the published log (ADR-009 executed)

Orthogonal to the stage, per-chapter GATE FLAGS surface what a human must act on:
publish_recommendation (recommend/hold/block), m7_risk_level, approval_status,
and `blocked` (a block recommendation OR a rejected review). These never change
the stage — a blocked chapter is still `assessed`; the flag is what triage reads.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .. import derived
from ..execution.envelope import unwrap
from ..inventory import project_inventory, load_published_log

# Pipeline stages, lowest to highest. Extends the inventory funnel's
# drafted/reviewed/published with the two governance stages M7 introduced.
STAGE_DRAFTED = "drafted"
STAGE_REVIEWED = "reviewed"
STAGE_ASSESSED = "assessed"
STAGE_APPROVED = "approved"
STAGE_PUBLISHED = "published"

_STAGE_ORDER = [STAGE_DRAFTED, STAGE_REVIEWED, STAGE_ASSESSED,
                STAGE_APPROVED, STAGE_PUBLISHED]


@dataclass(frozen=True)
class PipelineReport:
    reviewer: str
    total: int
    by_stage: Dict[str, int]          # stage -> count of chapters at that stage
    blocked: int                      # chapters flagged blocked (block rec / rejected)
    awaiting_approval: int            # chapters with a pending M7/publish review
    chapters: List[dict] = field(default_factory=list)
    gating: bool = False              # ADR-003: this projection never gates

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "total": self.total,
            "by_stage": self.by_stage,
            "blocked": self.blocked,
            "awaiting_approval": self.awaiting_approval,
            "chapters": self.chapters,
            "gating": self.gating,
        }


def _draft_entries(project_path) -> List[dict]:
    """Draft index entries, sorted by id — the SSOT of what was produced (mirrors
    the inventory funnel so the two projections never disagree on membership)."""
    index = derived._load_index(project_path)
    return sorted((e for e in index.get("artifacts", [])
                   if e.get("category") == "drafts"),
                  key=lambda e: e.get("id", ""))


def _envelope_signals(project_path, entries: List[dict]) -> Dict[str, dict]:
    """Per-chapter publish_readiness + M7 lifted off each on-disk envelope, keyed
    by task_id. A bare pre-envelope draft, a missing/unparseable file, or a null
    block all degrade to an empty signal — never an error (advisory discipline)."""
    signals: Dict[str, dict] = {}
    for e in entries:
        path = Path(project_path) / e.get("path", "")
        if not path.exists():
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(obj, dict):
            continue
        task_id = unwrap(obj).get("task_id")
        pub = obj.get("publish_readiness") if isinstance(obj.get("publish_readiness"), dict) else None
        sig: dict = {}
        if pub:
            sig["publish_recommendation"] = pub.get("recommendation")
        # M7 rides the envelope as its OWN sibling (not nested in publish_readiness,
        # whose frozen schema forbids it — see envelope.wrap / run.py). Read it there.
        m7 = obj.get("m7") if isinstance(obj.get("m7"), dict) else None
        if m7:
            sig["m7_risk_level"] = m7.get("risk_level")
        if sig:
            signals[task_id] = sig
    return signals


def _approvals_by_chapter(queue) -> Dict[str, dict]:
    """Fold the M7/publish review requests down to one status per chapter. When a
    chapter has several requests (a re-run enqueues a stable id, so this is rare),
    the highest-precedence status wins: rejected > pending > approved. Read-only
    over the loaded queue; never mutates it."""
    if queue is None:
        return {}
    _rank = {"rejected": 3, "pending": 2, "deferred": 2, "needs_more_info": 2,
             "approved": 1, "executed": 1, "cancelled": 0}
    out: Dict[str, dict] = {}
    for req in queue.list_requests(target_type="publish", action="review_m7_risk"):
        cur = out.get(req.target_id)
        if cur is None or _rank.get(req.status, 0) > _rank.get(cur["approval_status"], 0):
            out[req.target_id] = {
                "approval_status": req.status,
                "approval_id": req.id,
                "approval_risk_level": req.risk_level,
            }
    return out


def _stage_for(*, inventory_status: str, has_readiness: bool,
               approval_status: Optional[str]) -> str:
    """The highest lifecycle stage a chapter has reached. `published` (a human
    authored the log) is terminal and overrides everything below — the inventory
    funnel already decided it. Otherwise: approved review > publish_readiness
    present > reviewed > drafted. A block/reject does NOT lower the stage (the
    chapter WAS assessed) — that surfaces as the `blocked` flag instead."""
    if inventory_status == STAGE_PUBLISHED:
        return STAGE_PUBLISHED
    if approval_status in ("approved", "executed"):
        return STAGE_APPROVED
    if has_readiness:
        return STAGE_ASSESSED
    if inventory_status == STAGE_REVIEWED:
        return STAGE_REVIEWED
    return STAGE_DRAFTED


def project_pipeline(project_path: str | Path, *,
                     published_log: Optional[dict] = None,
                     approval_queue=None,
                     reviewer: str = "pipeline-v1") -> PipelineReport:
    """Fold the produced-draft index + envelope publish_readiness/M7 + approval
    queue + authored published log into ONE per-chapter pipeline view. Pure and
    deterministic (same products => same report); advisory, never gates (ADR-003);
    reads only — writes no facts (ADR-006) and no published log (ADR-009).

    `published_log` and `approval_queue` are loaded here when not supplied, so a
    caller can pass pre-loaded objects (tests, dashboards) or let the projection
    do the IO. Both absent => nothing approved/published yet, and the pipeline
    degrades to the inventory funnel's drafted/reviewed/assessed view."""
    project_path = Path(project_path)
    if published_log is None:
        published_log = load_published_log(project_path)
    if approval_queue is None:
        from ..approval import load_approval_queue
        approval_queue = load_approval_queue(project_path)

    # Reuse the inventory funnel for the drafted/reviewed/published membership so
    # the pipeline and the funnel never disagree on which chapters exist or which
    # a human published (the single source of truth for those three stages).
    funnel = project_inventory(project_path, published_log=published_log)
    inv_status = {c["task_id"]: c["status"] for c in funnel.chapters}

    entries = _draft_entries(project_path)
    signals = _envelope_signals(project_path, entries)
    approvals = _approvals_by_chapter(approval_queue)

    by_stage = {s: 0 for s in _STAGE_ORDER}
    blocked = 0
    awaiting = 0
    chapters: List[dict] = []
    for e in entries:
        task_id = e.get("id")
        sig = signals.get(task_id, {})
        appr = approvals.get(task_id, {})
        has_readiness = "publish_recommendation" in sig
        approval_status = appr.get("approval_status")
        stage = _stage_for(inventory_status=inv_status.get(task_id, STAGE_DRAFTED),
                           has_readiness=has_readiness,
                           approval_status=approval_status)
        by_stage[stage] += 1

        rec = sig.get("publish_recommendation")
        is_blocked = rec == "block" or approval_status == "rejected"
        if is_blocked:
            blocked += 1
        if approval_status in ("pending", "deferred", "needs_more_info"):
            awaiting += 1

        chapters.append({
            "task_id": task_id,
            "stage": stage,
            "publish_recommendation": rec,
            "m7_risk_level": sig.get("m7_risk_level"),
            "approval_status": approval_status,
            "approval_id": appr.get("approval_id"),
            "blocked": is_blocked,
        })

    return PipelineReport(
        reviewer=reviewer,
        total=len(entries),
        by_stage=by_stage,
        blocked=blocked,
        awaiting_approval=awaiting,
        chapters=chapters,
    )
