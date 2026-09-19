"""detectors.py — Promise detectors (Stage B.2).

Unified detection layer that wraps existing promise/setup/thread detection logic
into a consistent interface outputting PromiseEntry objects.

This module is a thin wrapper layer - it doesn't rewrite existing logic, just
provides a unified interface for the Promise Ledger to consume.
"""
from __future__ import annotations

from typing import List, Optional

from .ledger import PromiseEntry


def detect_packaging_promises(packaging: Optional[dict],
                              existing_ids: List[str]) -> List[PromiseEntry]:
    """Detect packaging promises from book-packaging.yaml.

    Wraps runtime.packaging.loader.packaging_promises() to output PromiseEntry.
    """
    if not packaging:
        return []

    from ..packaging.loader import packaging_promises

    promises = packaging_promises(packaging)
    entries = []
    next_id = len(existing_ids) + 1

    for p in promises:
        entry = PromiseEntry(
            id=f"PROMISE-{next_id:05d}",
            type="packaging",
            statement=p["statement"],
            created_at_chapter=1,  # Packaging promises are always at book start
            evidence_terms=p["evidence_terms"],
            must_deliver_by=p["must_appear_by"],
            status="open",
            level="critical",  # Packaging promises affect click-through, hence critical
        )
        entries.append(entry)
        next_id += 1

    return entries


def detect_narrative_setups(reg, existing_ids: List[str]) -> List[PromiseEntry]:
    """Detect narrative setups from events with [伏笔] markers.

    Wraps runtime.memory.threads logic to output PromiseEntry.
    """
    from ..memory.threads import _is_setup, _referenced_as_cause

    facts = reg.facts
    paid_off = _referenced_as_cause(facts)

    # Build event-to-chapter mapping
    event_to_chapter = {}
    for rid, rec in facts.items():
        if rid.startswith("EVT-"):
            seq_idx = rec.get("sequence_index")
            if seq_idx is not None:
                event_to_chapter[rid] = seq_idx + 1  # 1-based chapter numbering

    entries = []
    next_id = len(existing_ids) + 1

    for rid, rec in sorted(facts.items()):
        if not rid.startswith("EVT-"):
            continue

        if not _is_setup(rec):
            continue

        picked_up = rid in paid_off or bool(rec.get("effects"))
        chapter = event_to_chapter.get(rid, 1)

        # Extract a clean statement from summary/notes
        statement = (rec.get("summary") or rec.get("notes") or "")
        # Remove the [伏笔] markers for cleaner display
        for marker in ["[伏笔]", "[foreshadow]", "[setup]", "【伏笔】", "伏笔:", "伏笔："]:
            statement = statement.replace(marker, "")
        statement = statement.strip()[:200]  # Limit length

        entry = PromiseEntry(
            id=f"PROMISE-{next_id:05d}",
            type="narrative",
            statement=statement,
            created_at_chapter=chapter,
            created_in_event=rid,
            evidence_terms=[],  # Narrative setups don't have explicit evidence terms
            must_deliver_by=None,  # No hard deadline for narrative setups
            status="delivered" if picked_up else "open",
            delivered_in_event=None,  # TODO: Could extract from cause chain
            level="important",
        )
        entries.append(entry)
        next_id += 1

    return entries


def detect_plot_threads(reg, existing_ids: List[str]) -> List[PromiseEntry]:
    """Detect open plot threads (events with causes but no effects yet).

    Wraps runtime.memory.threads logic to output PromiseEntry.
    """
    from ..memory.threads import _referenced_as_cause

    facts = reg.facts
    paid_off = _referenced_as_cause(facts)

    # Build event-to-chapter mapping
    event_to_chapter = {}
    for rid, rec in facts.items():
        if rid.startswith("EVT-"):
            seq_idx = rec.get("sequence_index")
            if seq_idx is not None:
                event_to_chapter[rid] = seq_idx + 1

    entries = []
    next_id = len(existing_ids) + 1

    for rid, rec in sorted(facts.items()):
        if not rid.startswith("EVT-"):
            continue

        # Open thread: has causes but hasn't been picked up yet
        picked_up = rid in paid_off or bool(rec.get("effects"))
        has_causes = bool(rec.get("causes"))

        if has_causes and not picked_up:
            chapter = event_to_chapter.get(rid, 1)
            statement = (rec.get("summary") or rec.get("notes") or "")[:200]

            entry = PromiseEntry(
                id=f"PROMISE-{next_id:05d}",
                type="thread",
                statement=statement,
                created_at_chapter=chapter,
                created_in_event=rid,
                evidence_terms=[],
                must_deliver_by=None,  # Threads don't have hard deadlines
                status="open",
                level="optional",  # Threads are lower priority than explicit setups
            )
            entries.append(entry)
            next_id += 1

    return entries


def detect_all_promises(reg, packaging: Optional[dict] = None) -> List[PromiseEntry]:
    """Detect all promises from all sources.

    This is the main entry point for promise detection. It calls all specific
    detectors and returns a unified list of PromiseEntry objects.
    """
    existing_ids: List[str] = []

    # Detect in priority order: packaging (critical) -> narrative -> threads
    packaging_entries = detect_packaging_promises(packaging, existing_ids)
    existing_ids.extend([e.id for e in packaging_entries])

    narrative_entries = detect_narrative_setups(reg, existing_ids)
    existing_ids.extend([e.id for e in narrative_entries])

    thread_entries = detect_plot_threads(reg, existing_ids)

    return packaging_entries + narrative_entries + thread_entries


def detect_promises_summary(reg, packaging: Optional[dict] = None) -> dict:
    """Detect all promises and return a summary dict.

    Useful for quick diagnostics without building the full ledger.
    """
    promises = detect_all_promises(reg, packaging)

    return {
        "total": len(promises),
        "by_type": {
            "packaging": sum(1 for p in promises if p.type == "packaging"),
            "narrative": sum(1 for p in promises if p.type == "narrative"),
            "thread": sum(1 for p in promises if p.type == "thread"),
        },
        "by_status": {
            "open": sum(1 for p in promises if p.status == "open"),
            "delivered": sum(1 for p in promises if p.status == "delivered"),
        },
        "by_level": {
            "critical": sum(1 for p in promises if p.level == "critical"),
            "important": sum(1 for p in promises if p.level == "important"),
            "optional": sum(1 for p in promises if p.level == "optional"),
        },
        "with_deadlines": sum(1 for p in promises if p.must_deliver_by is not None),
    }
