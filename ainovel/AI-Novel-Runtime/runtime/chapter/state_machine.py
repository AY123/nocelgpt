"""
Chapter State Machine (P0-1)

Canonical state machine for chapter production decisions. This is the SINGLE
source of truth for chapter status. All other decision fields (pipeline_decision,
publish_readiness, etc.) must be derived from this or removed.

Design Principles:
- One chapter = one state at any time
- State transitions are validated
- Contradictory fields are rejected at construction time
- All decision logic flows through ProductionDecisionEngine
"""
from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone


class ChapterState(Enum):
    """Canonical chapter production states (P0-1)

    These states form a strict state machine with validated transitions.
    """
    DRAFTED = "drafted"           # Generation complete, not yet reviewed
    REVIEWED = "reviewed"         # Review complete, decision pending
    REVISION_REQUIRED = "revision_required"  # Must revise before advancing
    REVISED = "revised"           # Revision complete, awaiting re-review
    APPROVED = "approved"         # All checks passed, ready to advance
    HELD = "held"                 # Human hold, cannot advance without approval
    BLOCKED = "blocked"           # Hard failure (redline/contract), cannot advance
    FINALIZED = "finalized"       # Final state, chapter is sealed


class StateTransition:
    """Valid state transitions (P0-1)

    Enforces the state machine graph. Any transition not in ALLOWED is illegal.
    """
    ALLOWED: Dict[ChapterState, set[ChapterState]] = {
        ChapterState.DRAFTED: {
            ChapterState.REVIEWED,
            ChapterState.BLOCKED,
        },
        ChapterState.REVIEWED: {
            ChapterState.REVISION_REQUIRED,
            ChapterState.APPROVED,
            ChapterState.HELD,
            ChapterState.BLOCKED,
        },
        ChapterState.REVISION_REQUIRED: {
            ChapterState.REVISED,
            ChapterState.BLOCKED,
        },
        ChapterState.REVISED: {
            ChapterState.REVIEWED,
            ChapterState.BLOCKED,
        },
        ChapterState.APPROVED: {
            ChapterState.FINALIZED,
            ChapterState.HELD,  # Can hold even approved chapters
        },
        ChapterState.HELD: {
            ChapterState.APPROVED,
            ChapterState.BLOCKED,
        },
        ChapterState.BLOCKED: set(),  # Terminal failure state
        ChapterState.FINALIZED: set(),  # Terminal success state
    }

    @classmethod
    def is_valid(cls, from_state: ChapterState, to_state: ChapterState) -> bool:
        """Check if transition is valid"""
        return to_state in cls.ALLOWED.get(from_state, set())

    @classmethod
    def validate(cls, from_state: ChapterState, to_state: ChapterState) -> None:
        """Validate transition or raise"""
        if not cls.is_valid(from_state, to_state):
            raise ValueError(
                f"Illegal state transition: {from_state.value} → {to_state.value}"
            )


@dataclass
class ChapterDecision:
    """Unified chapter decision (P0-1)

    This is the ONLY authoritative decision structure. All other decision fields
    must be derived from this or removed.

    Invariants:
    - BLOCKED chapters cannot advance
    - FINALIZED chapters cannot have blocking issues
    - HELD chapters require human approval
    - advance_to_next is true only for APPROVED or FINALIZED
    """
    state: ChapterState
    advance_to_next: bool  # Can the serial advance the chapter cursor?
    blocking_issues: List[str]
    warnings: List[str]
    human_approval_required: bool
    decision_provenance: Dict[str, Any]  # What produced this decision

    def __post_init__(self):
        """Validate invariants at construction (P0-1)"""
        # Invariant 1: BLOCKED chapters cannot advance
        if self.state == ChapterState.BLOCKED and self.advance_to_next:
            raise ValueError("BLOCKED chapters cannot advance")

        # Invariant 2: FINALIZED chapters cannot have blocking issues
        if self.state == ChapterState.FINALIZED and self.blocking_issues:
            raise ValueError("FINALIZED chapters cannot have blocking issues")

        # Invariant 3: HELD chapters require human approval
        if self.state == ChapterState.HELD and not self.human_approval_required:
            raise ValueError("HELD chapters must require human approval")

        # Invariant 4: Only APPROVED/FINALIZED/REVIEWED can advance
        # (REVIEWED can advance if there are only advisory warnings)
        if self.advance_to_next and self.state not in {
            ChapterState.APPROVED, ChapterState.FINALIZED, ChapterState.REVIEWED
        }:
            raise ValueError(
                f"Only APPROVED/FINALIZED/REVIEWED chapters can advance, not {self.state.value}"
            )

    def can_advance(self) -> bool:
        """Can the serial advance to the next chapter?

        Returns:
            True only if state is APPROVED or FINALIZED and advance_to_next is True
        """
        return self.advance_to_next and self.state in {
            ChapterState.APPROVED, ChapterState.FINALIZED
        }

    def requires_human_review(self) -> bool:
        """Must a human approve before advancing?

        Returns:
            True if human_approval_required or state is HELD
        """
        return self.human_approval_required or self.state == ChapterState.HELD

    def is_terminal(self) -> bool:
        """Is this a terminal state?

        Terminal states cannot transition to any other state.

        Returns:
            True if state is BLOCKED or FINALIZED
        """
        return self.state in {ChapterState.BLOCKED, ChapterState.FINALIZED}

    def validate_transition_from(self, from_state: ChapterState) -> None:
        """Validate this decision is a legal transition from previous state

        Args:
            from_state: The previous chapter state

        Raises:
            ValueError: If transition is illegal
        """
        StateTransition.validate(from_state, self.state)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization"""
        return {
            "state": self.state.value,
            "advance_to_next": self.advance_to_next,
            "blocking_issues": self.blocking_issues,
            "warnings": self.warnings,
            "human_approval_required": self.human_approval_required,
            "decision_provenance": self.decision_provenance,
            "can_advance": self.can_advance(),
            "requires_human_review": self.requires_human_review(),
            "is_terminal": self.is_terminal(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChapterDecision:
        """Create from dict"""
        state_str = data.get("state")
        if isinstance(state_str, str):
            state = ChapterState(state_str)
        else:
            state = state_str

        return cls(
            state=state,
            advance_to_next=data["advance_to_next"],
            blocking_issues=data.get("blocking_issues", []),
            warnings=data.get("warnings", []),
            human_approval_required=data["human_approval_required"],
            decision_provenance=data.get("decision_provenance", {}),
        )

    def __str__(self) -> str:
        """Human-readable summary"""
        parts = [f"State={self.state.value}"]
        if self.can_advance():
            parts.append("CAN_ADVANCE")
        if self.requires_human_review():
            parts.append("NEEDS_APPROVAL")
        if self.blocking_issues:
            parts.append(f"BLOCKED({len(self.blocking_issues)})")
        if self.warnings:
            parts.append(f"WARN({len(self.warnings)})")
        return " ".join(parts)


def create_approved_decision(provenance: Optional[Dict[str, Any]] = None) -> ChapterDecision:
    """Create an APPROVED decision (P0-1 convenience factory)"""
    return ChapterDecision(
        state=ChapterState.APPROVED,
        advance_to_next=True,
        blocking_issues=[],
        warnings=[],
        human_approval_required=False,
        decision_provenance=provenance or {
            "engine": "factory",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


def create_blocked_decision(
    reason: str,
    provenance: Optional[Dict[str, Any]] = None
) -> ChapterDecision:
    """Create a BLOCKED decision (P0-1 convenience factory)"""
    return ChapterDecision(
        state=ChapterState.BLOCKED,
        advance_to_next=False,
        blocking_issues=[reason],
        warnings=[],
        human_approval_required=False,
        decision_provenance=provenance or {
            "engine": "factory",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


def create_held_decision(
    warnings: List[str],
    provenance: Optional[Dict[str, Any]] = None
) -> ChapterDecision:
    """Create a HELD decision (P0-1 convenience factory)"""
    return ChapterDecision(
        state=ChapterState.HELD,
        advance_to_next=False,
        blocking_issues=[],
        warnings=warnings,
        human_approval_required=True,
        decision_provenance=provenance or {
            "engine": "factory",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
