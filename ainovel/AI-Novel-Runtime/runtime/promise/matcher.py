"""matcher.py — Promise Evidence Matcher (Stage B.3).

Matches promise evidence terms against chapter draft content to detect delivery.
Pure deterministic matching - no LLM calls, just string matching with coverage
calculation.

This is the core of promise delivery detection. It reads draft content, checks
each open promise's evidence terms, and updates promise status when coverage
threshold is met.
"""
from __future__ import annotations

from typing import Optional
from dataclasses import replace

from .ledger import PromiseEntry, PromiseLedger


def match_evidence(promise: PromiseEntry, draft_body: str) -> float:
    """Calculate evidence coverage for a promise against draft content.

    Pure string matching - checks if each evidence term appears in the body.
    Case-sensitive for now (can be enhanced later).

    Args:
        promise: Promise entry with evidence_terms
        draft_body: Chapter draft content to search

    Returns:
        coverage: 0.0-1.0, proportion of evidence terms found in draft
                  Returns 0.0 if promise has no evidence terms

    Example:
        promise.evidence_terms = ["吞噬", "晶核", "曜能", "转化"]
        draft contains "吞噬" and "曜能"
        -> returns 0.5 (2/4 terms matched)
    """
    if not promise.evidence_terms:
        return 0.0

    if not draft_body:
        return 0.0

    # Count how many evidence terms appear in the draft
    matched_count = sum(1 for term in promise.evidence_terms if term in draft_body)

    coverage = matched_count / len(promise.evidence_terms)
    return coverage


def check_delivery(
    ledger: PromiseLedger,
    draft_body: str,
    chapter: int,
    event_id: str,
    threshold: float = 0.5
) -> PromiseLedger:
    """Check if draft delivers any open promises and update ledger.

    Scans all open promises, calculates evidence coverage, and marks as
    delivered if coverage >= threshold. Returns a NEW ledger with updated
    promise statuses (immutable update pattern).

    Args:
        ledger: Current Promise Ledger
        draft_body: Chapter draft content
        chapter: Chapter number (for delivered_in_chapter)
        event_id: Event ID (for delivered_in_event)
        threshold: Evidence coverage threshold (default 0.5 = 50%)

    Returns:
        Updated PromiseLedger with new promise statuses

    Example:
        ledger has 3 open promises
        draft contains evidence for 2 of them (coverage >= 0.5)
        -> returns ledger with those 2 marked as delivered
    """
    updated_promises = []

    for promise in ledger.promises:
        if promise.status == "open":
            # Calculate evidence coverage
            coverage = match_evidence(promise, draft_body)

            if coverage >= threshold:
                # Mark as delivered
                updated_promise = replace(
                    promise,
                    status="delivered",
                    delivered_at_chapter=chapter,
                    delivered_in_event=event_id,
                )
                updated_promises.append(updated_promise)
            else:
                # Keep as open
                updated_promises.append(promise)
        else:
            # Already delivered or other status - keep as is
            updated_promises.append(promise)

    # Return new ledger with updated promises
    return replace(ledger, promises=updated_promises)


def get_delivered_promises(ledger: PromiseLedger, chapter: int) -> list[str]:
    """Get list of promise IDs delivered in a specific chapter.

    Args:
        ledger: Promise Ledger
        chapter: Chapter number

    Returns:
        List of promise IDs delivered in that chapter
    """
    return [
        p.id for p in ledger.promises
        if p.status == "delivered" and p.delivered_at_chapter == chapter
    ]


def get_pending_promises(ledger: PromiseLedger, chapter: int) -> list[str]:
    """Get list of promise IDs that should have been delivered by this chapter.

    These are open promises where must_deliver_by <= current chapter - they
    are overdue.

    Args:
        ledger: Promise Ledger
        chapter: Current chapter number

    Returns:
        List of promise IDs that are overdue
    """
    return [
        p.id for p in ledger.promises
        if p.status == "open"
        and p.must_deliver_by is not None
        and p.must_deliver_by <= chapter
    ]


def calculate_ledger_summary(ledger: PromiseLedger) -> dict:
    """Calculate summary statistics for the ledger.

    Returns:
        Dict with counts by status and type
    """
    by_status = {}
    by_type = {}

    for p in ledger.promises:
        # Count by status
        status = p.status
        by_status[status] = by_status.get(status, 0) + 1

        # Count by type
        ptype = p.type
        by_type[ptype] = by_type.get(ptype, 0) + 1

    return {
        "total": len(ledger.promises),
        "by_status": by_status,
        "by_type": by_type,
    }
