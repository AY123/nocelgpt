"""
ANovelOS V2 Character Knowledge and Proposition.

This module implements the character knowledge domain model defining what characters
know, believe, and intend within the narrative.

Public API:
    Types:
        PropositionId, Proposition, CharacterKnowledge
        KnowledgeLevel, AcquisitionSource

    Operations:
        create_proposition, freeze_context

Invariants:
    - Proposition.context is immutable (recursively frozen)
    - PropositionId collision with different BASE payload is rejected
    - aligns_with_fact is CACHE (compare=False, not persisted)
    - Acquisition provenance is mandatory

Contract: V2-061 Implementation Contract + ADR-002
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, NewType, Optional, Union

from .identity import EntityId, ProjectId

# --- Type Aliases ---

PropositionId = NewType("PropositionId", str)
"""Unique identifier for propositions (UUID v4 format)."""


# --- Enums ---


class KnowledgeLevel(Enum):
    """Character's epistemic state regarding a proposition.

    Contract: Frozen V2-061 Contract §Knowledge Semantics

    KNOWN: High-confidence, verified knowledge. Must NOT contradict objective fact.
    BELIEVED: Accepted as true, not independently verified. May be correct or incorrect.
    SUSPECTED: Weak belief, uncertain.

    UNKNOWN representation: Absence of CharacterKnowledge record (no explicit enum).
    """

    KNOWN = "KNOWN"
    BELIEVED = "BELIEVED"
    SUSPECTED = "SUSPECTED"


class AcquisitionSource(Enum):
    """How character acquired knowledge.

    Contract: Frozen V2-061 Contract §Provenance

    Each source has REQUIRED provenance fields:
    - DIRECT_OBSERVATION: source_ref REQUIRED
    - COMMUNICATION: source_character REQUIRED
    - DOCUMENT: source_ref REQUIRED
    - INFERENCE: basis_ref REQUIRED (non-empty list)
    - RUMOR: source_character OR source_ref REQUIRED (at least one)
    """

    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    COMMUNICATION = "COMMUNICATION"
    DOCUMENT = "DOCUMENT"
    INFERENCE = "INFERENCE"
    RUMOR = "RUMOR"


# --- Context Freezing ---


def freeze_context(ctx: Union[Mapping[str, Any], dict[str, Any], None]) -> Optional[Mapping[str, Any]]:
    """
    Recursively freeze context mapping to immutable representation.

    Converts nested dicts and lists to immutable equivalents:
    - dict → types.MappingProxyType (recursively)
    - list → tuple (recursively)
    - Other types preserved as-is

    Args:
        ctx: Context mapping or None

    Returns:
        Recursively frozen immutable context, or None

    Example:
        >>> ctx = {"key": "value", "nested": {"a": 1, "b": [2, 3]}}
        >>> frozen = freeze_context(ctx)
        >>> frozen["nested"]["b"]
        (2, 3)
        >>> frozen["key"] = "new"  # TypeError

    Contract: ADR-002 Proposition.context immutability
    """
    if ctx is None:
        return None

    from types import MappingProxyType

    def _freeze_value(value: Any) -> Any:
        """Recursively freeze a single value."""
        if isinstance(value, dict):
            # Recursively freeze dict values
            frozen_dict = {k: _freeze_value(v) for k, v in value.items()}
            return MappingProxyType(frozen_dict)
        elif isinstance(value, list):
            # Recursively freeze list elements to tuple
            return tuple(_freeze_value(item) for item in value)
        elif isinstance(value, Mapping) and not isinstance(value, MappingProxyType):
            # Already a Mapping but not frozen - freeze it
            frozen_dict = {k: _freeze_value(v) for k, v in value.items()}
            return MappingProxyType(frozen_dict)
        else:
            # Primitive or already immutable
            return value

    # Freeze top-level mapping
    from types import MappingProxyType
    frozen_dict = {k: _freeze_value(v) for k, v in ctx.items()}
    return MappingProxyType(frozen_dict)


# --- Domain Models ---


@dataclass(frozen=True)
class Proposition:
    """
    Immutable proposition representing a statement about the narrative world.

    BASE fields (all persisted):
        proposition_id: Unique identifier
        project_id: Project scope
        subject: Entity this proposition is about
        predicate: What is claimed (e.g., "is_alive", "owns")
        object: Optional target entity or value
        context: Optional structured metadata (recursively immutable)

    Invariants:
        - context must be recursively frozen (not mutable dict)
        - Same PropositionId + different BASE payload → REJECT

    Contract: ADR-002 Proposition BASE fields
    """

    proposition_id: PropositionId
    project_id: ProjectId
    subject: EntityId
    predicate: str
    object: Optional[Union[str, EntityId]]
    context: Optional[Mapping[str, Any]]


def create_proposition(
    project_id: ProjectId,
    subject: EntityId,
    predicate: str,
    object: Optional[Union[str, EntityId]] = None,
    context: Union[Mapping[str, Any], dict[str, Any], None] = None,
) -> Proposition:
    """
    Create a new proposition with frozen context.

    Generates a fresh UUID v4 proposition ID and creates an immutable Proposition
    with recursively frozen context. This is a pure function with no side effects.

    Args:
        project_id: Project scope
        subject: Entity the proposition is about
        predicate: What is claimed (non-empty)
        object: Optional target entity or value
        context: Optional structured metadata (will be recursively frozen)

    Returns:
        Proposition with fresh proposition_id and frozen context

    Raises:
        ValueError: If project_id is empty
        ValueError: If predicate is empty or whitespace-only

    Example:
        >>> prop = create_proposition(
        ...     ProjectId("proj_01"),
        ...     EntityId("entity-123"),
        ...     "is_alive",
        ...     context={"certainty": "high"}
        ... )
        >>> prop.predicate
        'is_alive'

    Contract: V2-061 + ADR-002
    """
    import uuid

    # Validate project_id
    if not project_id or not project_id.strip():
        raise ValueError("project_id cannot be empty or whitespace-only")

    # Validate predicate
    if not predicate or not predicate.strip():
        raise ValueError("predicate cannot be empty or whitespace-only")

    # Generate fresh proposition ID
    proposition_id = PropositionId(str(uuid.uuid4()))

    # Freeze context recursively
    frozen_context = freeze_context(context)

    return Proposition(
        proposition_id=proposition_id,
        project_id=project_id,
        subject=subject,
        predicate=predicate.strip(),
        object=object,
        context=frozen_context,
    )


@dataclass(frozen=True)
class CharacterKnowledge:
    """
    Character's knowledge of a proposition at a point in narrative time.

    BASE fields (persisted):
        knower: Character who holds this knowledge
        proposition: What is known/believed
        knowledge_level: Character's epistemic state (KNOWN/BELIEVED/SUSPECTED)
        acquisition_source: How knowledge was acquired (REQUIRED)
        source_character: Entity from whom knowledge was acquired (for COMMUNICATION/RUMOR)
        source_ref: Reference to source event/scene (for DIRECT_OBSERVATION/DOCUMENT/RUMOR)
        basis_ref: Reference to inference basis (for INFERENCE, non-empty list required)
        acquired_at: System timestamp of knowledge acquisition
        story_time_ref: Narrative time reference
        confidence: Character's confidence level (0.0-1.0)

    CACHE fields (not persisted, compare=False):
        aligns_with_fact: Whether knowledge aligns with Canon truth

    Invariants:
        - KNOWN + aligns_with_fact=False = INVALID (high-confidence misbelief not allowed)
        - BELIEVED/SUSPECTED + aligns_with_fact=False = VALID (misbelief allowed)
        - acquisition_source provenance requirements MUST be satisfied
        - aligns_with_fact does not participate in equality

    Contract: ADR-002 CharacterKnowledge BASE + CACHE
    """

    # BASE fields
    knower: EntityId
    proposition: Proposition
    knowledge_level: KnowledgeLevel
    acquisition_source: AcquisitionSource
    source_character: Optional[EntityId] = None
    source_ref: Optional[str] = None
    basis_ref: Optional[list[PropositionId]] = None
    acquired_at: Optional[datetime] = None
    story_time_ref: Optional[str] = None
    confidence: Optional[float] = None

    # CACHE field (not persisted, not in equality)
    aligns_with_fact: Optional[bool] = field(default=None, compare=False)

    def __post_init__(self) -> None:
        """Validate invariants after construction.

        Contract: Frozen V2-061 §Provenance Hard Rules
        """
        # Validate KNOWN + aligns_with_fact=False invariant
        if self.knowledge_level == KnowledgeLevel.KNOWN and self.aligns_with_fact is False:
            raise ValueError(
                "knowledge_level=KNOWN with aligns_with_fact=False is INVALID. "
                "High-confidence misbelief must use BELIEVED with high confidence, not KNOWN."
            )

        # Validate acquisition source provenance requirements
        if self.acquisition_source == AcquisitionSource.DIRECT_OBSERVATION:
            if not self.source_ref:
                raise ValueError(
                    "acquisition_source=DIRECT_OBSERVATION requires source_ref (event/observation context)"
                )

        elif self.acquisition_source == AcquisitionSource.COMMUNICATION:
            if not self.source_character:
                raise ValueError(
                    "acquisition_source=COMMUNICATION requires source_character (who told character)"
                )

        elif self.acquisition_source == AcquisitionSource.DOCUMENT:
            if not self.source_ref:
                raise ValueError(
                    "acquisition_source=DOCUMENT requires source_ref (document identifier)"
                )

        elif self.acquisition_source == AcquisitionSource.INFERENCE:
            if not self.basis_ref or len(self.basis_ref) == 0:
                raise ValueError(
                    "acquisition_source=INFERENCE requires basis_ref (non-empty list of what was reasoned from)"
                )

        elif self.acquisition_source == AcquisitionSource.RUMOR:
            if not self.source_character and not self.source_ref:
                raise ValueError(
                    "acquisition_source=RUMOR requires source_character OR source_ref (at least one)"
                )

        # Hard invariant: acquisition_source alone is NOT sufficient provenance
        # At least one actual source reference must exist
        if not any([self.source_character, self.source_ref, self.basis_ref]):
            raise ValueError(
                "CharacterKnowledge requires actual provenance path: "
                "at least one of source_character, source_ref, or basis_ref must be provided. "
                "acquisition_source alone is not sufficient."
            )

        # Validate confidence range if provided
        if self.confidence is not None:
            if not (0.0 <= self.confidence <= 1.0):
                raise ValueError(
                    f"confidence must be in range [0.0, 1.0], got {self.confidence}"
                )
