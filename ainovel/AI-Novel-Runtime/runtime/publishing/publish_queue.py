"""publish_queue.py — spawn publish approval requests from the ready funnel.

The one place publish-approval requests are BORN. It folds the inventory funnel
(P19) + each chapter's CITED publish-readiness into the M6 approval ledger:

    a chapter that is publish-ready (readiness.recommendation == 'recommend')
    and not yet published (库存, ready stock) → one pending publish request.

DISCIPLINE:
  - This is an explicit ADAPTER, not a side-effect of building a card: the
    Production Card stays PURE/read-only; spawning is a deliberate write.
  - It only ENQUEUES a decision to be made; it never publishes. Publishing is the
    irreversible outward transition, so per ADR-009 a human still authors the
    published log — approving the request records the go/no-go, nothing more.
  - IDEMPOTENT: a chapter already carrying a publish request is skipped, so
    re-running never duplicates. Stable request id = APR-PUB-<chapter_id>.
  - Never gates (ADR-003): a chapter on hold/block simply does not spawn a
    request; that is advice, not a block on anything.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..approval import ApprovalQueue, load_approval_queue
from ..approval.publish import build_publish_request
from ..inventory import project_inventory
from .card import build_production_card, _load_draft_envelope

# Only a publish-ready chapter spawns a request. hold/block/unknown do not: the
# system already advises against publishing them, so a publish go/no-go would be
# premature noise.
_SPAWN_ON = "recommend"

# target_type used for publish requests, matching build_publish_request.
_PUBLISH_TARGET = "publish"


def _publish_request_id(chapter_id: str) -> str:
    """Stable per-chapter id so re-running is idempotent."""
    return f"APR-PUB-{chapter_id}"


def _has_publish_request(queue: ApprovalQueue, chapter_id: str) -> bool:
    """True if a publish request already exists for this chapter (any status).
    Keyed on target so a manually-created request (different id) still counts."""
    return any(
        r.target_type == _PUBLISH_TARGET and r.target_id == chapter_id
        for r in queue.requests
    )


def sync_publish_requests(
    project_path: str | Path,
    *,
    published_log: Optional[dict] = None,
    requested_by: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Enqueue a pending publish request for every publish-ready, not-yet-published
    chapter that does not already have one. Returns a summary of the sync.

    Pure toward chapters it skips; the only writes are new pending requests. Safe
    to run repeatedly — idempotent by chapter."""
    project_path = Path(project_path)
    queue = load_approval_queue(project_path)
    inventory = project_inventory(project_path, published_log=published_log)

    created: list[str] = []
    skipped_existing: list[str] = []
    skipped_not_ready: list[str] = []
    published: list[str] = []

    for ch in inventory.chapters:
        chapter_id = ch["task_id"]
        if ch["status"] == "published":
            published.append(chapter_id)
            continue

        card = build_production_card(project_path, chapter_id, published_log=published_log)
        readiness = card["publish_readiness"]
        recommendation = readiness.get("recommendation")
        if recommendation != _SPAWN_ON:
            skipped_not_ready.append(chapter_id)
            continue

        if _has_publish_request(queue, chapter_id):
            skipped_existing.append(chapter_id)
            continue

        # M7 rides the draft envelope as its own sibling (M8-01) — read it there
        # to carry the originality/red-line context onto the publish request. A
        # chapter with no M7 assessment degrades to an empty block (advisory).
        envelope = _load_draft_envelope(project_path, chapter_id)
        m7 = (envelope.get("m7") if isinstance(envelope, dict) else None) or {}
        reason = card.get("rationale") or f"{chapter_id}: publish-ready"
        request = build_publish_request(
            request_id=_publish_request_id(chapter_id),
            chapter_id=chapter_id,
            reason=reason,
            requested_by=requested_by or {"module": "publishing.publish_queue"},
            context={
                "chapter_id": chapter_id,
                "recommendation": recommendation,
                "draft_content_hash": card.get("draft_content_hash"),
                "m7_risk_level": m7.get("risk_level"),
                "m7_recommendation": m7.get("recommendation"),
                "m7_redline_passed": m7.get("redline_passed"),
            },
        )
        queue.enqueue(request)
        created.append(request.id)

    return {
        "created": created,
        "skipped_existing": skipped_existing,
        "skipped_not_ready": skipped_not_ready,
        "published": published,
        "total_pending": len(queue.list_pending()),
    }
