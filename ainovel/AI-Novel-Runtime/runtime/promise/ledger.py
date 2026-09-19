"""ledger.py — Promise Ledger core (Stage B.1).

The Promise Ledger is a unified view of all promises in the story:
- Packaging promises (from book-packaging.yaml)
- Narrative setups (from event [伏笔] markers)
- Plot threads (open causal chains)

DISCIPLINE:
  - DERIVED, never a fact (ADR-006): the ledger is a projection over packaging +
    events, written to registry/derived/promise-ledger/
  - PURE + DETERMINISTIC (ADR-008): same inputs => same ledger
  - ADVISORY, never gates (ADR-003): gating=false
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict

from ..execution.agent import _hash


@dataclass(frozen=True)
class PromiseEntry:
    """A single trackable promise in the story."""

    id: str  # PROMISE-00001
    type: str  # packaging | narrative | thread
    statement: str  # What was promised
    created_at_chapter: int  # Where it was created (1-based)
    created_in_event: Optional[str] = None  # EVT-00005 (for narrative/thread)
    evidence_terms: List[str] = field(default_factory=list)  # Terms that prove delivery
    must_deliver_by: Optional[int] = None  # Chapter deadline (None = no deadline)
    delivered_at_chapter: Optional[int] = None  # Where it was delivered
    delivered_in_event: Optional[str] = None  # EVT that resolved it
    status: str = "open"  # open | delivered | missed | cancelled
    level: str = "important"  # critical | important | optional

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "statement": self.statement,
            "created_at_chapter": self.created_at_chapter,
            "created_in_event": self.created_in_event,
            "evidence_terms": self.evidence_terms,
            "must_deliver_by": self.must_deliver_by,
            "delivered_at_chapter": self.delivered_at_chapter,
            "delivered_in_event": self.delivered_in_event,
            "status": self.status,
            "level": self.level,
        }


@dataclass(frozen=True)
class PromiseLedger:
    """A projection of all promises in the story."""

    reviewer: str
    promises: List[PromiseEntry] = field(default_factory=list)
    gating: bool = False  # ADR-003: advisory, never blocks

    @property
    def ledger_hash(self) -> str:
        """Deterministic hash of the ledger content."""
        core = {"promises": [p.to_dict() for p in self.promises]}
        return _hash(core)

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "gating": self.gating,
            "ledger_hash": self.ledger_hash,
            "promises": [p.to_dict() for p in self.promises],
            "summary": {
                "total": len(self.promises),
                "open": sum(1 for p in self.promises if p.status == "open"),
                "delivered": sum(1 for p in self.promises if p.status == "delivered"),
                "missed": sum(1 for p in self.promises if p.status == "missed"),
                "by_type": {
                    "packaging": sum(1 for p in self.promises if p.type == "packaging"),
                    "narrative": sum(1 for p in self.promises if p.type == "narrative"),
                    "thread": sum(1 for p in self.promises if p.type == "thread"),
                },
            },
        }

    def pending_for_chapter(self, chapter: int) -> List[PromiseEntry]:
        """Return promises that should be delivered in this specific chapter.

        A promise is "pending for chapter N" if:
        - It's still open
        - It has a deadline
        - This is the last chapter to deliver it (chapter == must_deliver_by)
        """
        return [
            p for p in self.promises
            if p.status == "open" and p.must_deliver_by is not None
            and p.must_deliver_by == chapter
        ]

    def open_promises(self) -> List[PromiseEntry]:
        """Return all open promises."""
        return [p for p in self.promises if p.status == "open"]

    def overdue_promises(self, current_chapter: int) -> List[PromiseEntry]:
        """Return promises that should have been delivered but weren't."""
        return [
            p for p in self.promises
            if p.status == "open" and p.must_deliver_by is not None
            and current_chapter > p.must_deliver_by
        ]


def _next_promise_id(existing_ids: List[str]) -> str:
    """Generate the next promise ID."""
    if not existing_ids:
        return "PROMISE-00001"

    # Extract numbers from existing IDs
    nums = []
    for pid in existing_ids:
        if pid.startswith("PROMISE-"):
            try:
                nums.append(int(pid.split("-")[1]))
            except (IndexError, ValueError):
                pass

    next_num = max(nums) + 1 if nums else 1
    return f"PROMISE-{next_num:05d}"


def project_promise_ledger(reg, packaging: Optional[dict] = None, *,
                           reviewer_id: str = "promise-ledger-v1") -> PromiseLedger:
    """Project the Promise Ledger from packaging + registry facts.

    Pure and deterministic: same inputs => same ledger.
    """
    from .detectors import detect_all_promises

    all_promises = detect_all_promises(reg, packaging)

    return PromiseLedger(
        reviewer=reviewer_id,
        promises=all_promises,
    )


def ledger_artifact(ledger: PromiseLedger, project_path: str) -> dict:
    """Create a derived artifact from the ledger for persistence."""
    return {
        "id": "promise-ledger-v1",
        "kind": "promise_ledger",
        "version": "1.0",
        "authority": "human",
        "gating": False,
        "project_path": str(project_path),
        **ledger.to_dict(),
    }
