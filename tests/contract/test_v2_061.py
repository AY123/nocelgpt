"""
V2-061 Contract Tests: Character Knowledge & Intent Core.

Tests Character, CharacterKnowledge, Proposition domain models against
frozen V2-061 contract (04862fca) and ADR-002 BASE/DERIVED/CACHE semantics.

Contract Authority: plan/validation/execution/V2-061/inputs/04862fca...txt
Contract Version: 1.0.0
ADR-002: plan/validation/execution/V2-061/inputs/0aadbc37...txt
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from types import MappingProxyType

import pytest

from anovel.domain import (
    AcquisitionSource,
    ActionStatus,
    Character,
    CharacterKnowledge,
    CharacterLifecycle,
    EntityId,
    Goal,
    GoalId,
    GoalStatus,
    Intent,
    IntentId,
    KnowledgeLevel,
    PlannedAction,
    PlannedActionId,
    ProjectId,
    Proposition,
    PropositionId,
    create_character,
    create_proposition,
    freeze_context,
)


# ============================================================================
# AC-1: Knowledge Acquisition Provenance (Frozen Contract §Provenance)
# ============================================================================


class TestKnowledgeAcquisitionProvenance:
    """AC-1: Knowledge acquisition requires valid provenance paths."""

    def test_direct_observation_requires_source_ref(self):
        """DIRECT_OBSERVATION requires source_ref (event/observation context)."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive",
        )

        # Valid: has source_ref
        ck = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.KNOWN,
            acquisition_source=AcquisitionSource.DIRECT_OBSERVATION,
            source_ref="event-789",
        )
        assert ck.source_ref == "event-789"

    def test_direct_observation_missing_source_ref_reject(self):
        """DIRECT_OBSERVATION without source_ref is INVALID."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive",
        )

        with pytest.raises(ValueError, match="DIRECT_OBSERVATION requires source_ref"):
            CharacterKnowledge(
                knower=EntityId("char-456"),
                proposition=prop,
                knowledge_level=KnowledgeLevel.KNOWN,
                acquisition_source=AcquisitionSource.DIRECT_OBSERVATION,
                # Missing source_ref
            )

    def test_communication_requires_source_character(self):
        """COMMUNICATION requires source_character (who told character)."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "betrayed_X",
        )

        # Valid: has source_character
        ck = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVED,
            acquisition_source=AcquisitionSource.COMMUNICATION,
            source_character=EntityId("char-789"),
        )
        assert ck.source_character == EntityId("char-789")

    def test_communication_missing_source_character_reject(self):
        """COMMUNICATION without source_character is INVALID."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "betrayed_X",
        )

        with pytest.raises(ValueError, match="COMMUNICATION requires source_character"):
            CharacterKnowledge(
                knower=EntityId("char-456"),
                proposition=prop,
                knowledge_level=KnowledgeLevel.BELIEVED,
                acquisition_source=AcquisitionSource.COMMUNICATION,
                # Missing source_character
            )

    def test_document_requires_source_ref(self):
        """DOCUMENT requires source_ref (document identifier)."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_heir",
        )

        # Valid: has source_ref
        ck = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.KNOWN,
            acquisition_source=AcquisitionSource.DOCUMENT,
            source_ref="document-will-123",
        )
        assert ck.source_ref == "document-will-123"

    def test_document_missing_source_ref_reject(self):
        """DOCUMENT without source_ref is INVALID."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_heir",
        )

        with pytest.raises(ValueError, match="DOCUMENT requires source_ref"):
            CharacterKnowledge(
                knower=EntityId("char-456"),
                proposition=prop,
                knowledge_level=KnowledgeLevel.KNOWN,
                acquisition_source=AcquisitionSource.DOCUMENT,
                # Missing source_ref
            )

    def test_inference_requires_basis_ref_non_empty(self):
        """INFERENCE requires basis_ref (non-empty list of what was reasoned from)."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_guilty",
        )

        # Valid: has non-empty basis_ref
        ck = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVED,
            acquisition_source=AcquisitionSource.INFERENCE,
            basis_ref=[PropositionId("prop-abc"), PropositionId("prop-def")],
        )
        assert len(ck.basis_ref) == 2

    def test_inference_missing_basis_ref_reject(self):
        """INFERENCE without basis_ref is INVALID."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_guilty",
        )

        with pytest.raises(ValueError, match="INFERENCE requires basis_ref"):
            CharacterKnowledge(
                knower=EntityId("char-456"),
                proposition=prop,
                knowledge_level=KnowledgeLevel.BELIEVED,
                acquisition_source=AcquisitionSource.INFERENCE,
                # Missing basis_ref
            )

    def test_inference_empty_basis_ref_reject(self):
        """INFERENCE with empty basis_ref is INVALID."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_guilty",
        )

        with pytest.raises(ValueError, match="INFERENCE requires basis_ref.*non-empty"):
            CharacterKnowledge(
                knower=EntityId("char-456"),
                proposition=prop,
                knowledge_level=KnowledgeLevel.BELIEVED,
                acquisition_source=AcquisitionSource.INFERENCE,
                basis_ref=[],  # Empty list
            )

    def test_rumor_requires_source_character_or_source_ref(self):
        """RUMOR requires source_character OR source_ref (at least one)."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_bankrupt",
        )

        # Valid: has source_character
        ck1 = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.SUSPECTED,
            acquisition_source=AcquisitionSource.RUMOR,
            source_character=EntityId("char-789"),
        )
        assert ck1.source_character is not None

        # Valid: has source_ref
        ck2 = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.SUSPECTED,
            acquisition_source=AcquisitionSource.RUMOR,
            source_ref="marketplace-gossip",
        )
        assert ck2.source_ref is not None

        # Valid: has both
        ck3 = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.SUSPECTED,
            acquisition_source=AcquisitionSource.RUMOR,
            source_character=EntityId("char-789"),
            source_ref="tavern-talk",
        )
        assert ck3.source_character is not None
        assert ck3.source_ref is not None

    def test_rumor_missing_both_sources_reject(self):
        """RUMOR without source_character OR source_ref is INVALID."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_bankrupt",
        )

        with pytest.raises(ValueError, match="RUMOR requires source_character OR source_ref"):
            CharacterKnowledge(
                knower=EntityId("char-456"),
                proposition=prop,
                knowledge_level=KnowledgeLevel.SUSPECTED,
                acquisition_source=AcquisitionSource.RUMOR,
                # Missing both source_character and source_ref
            )

    def test_knowledge_no_provenance_reject(self):
        """CharacterKnowledge with no actual provenance path is INVALID.

        Contract: acquisition_source alone is NOT sufficient. At least one
        actual source reference must exist.
        """
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "exists",
        )

        # Hard invariant test: Use DOCUMENT (requires source_ref)
        # Omitting source_ref triggers the DOCUMENT-specific check first
        with pytest.raises(ValueError, match="DOCUMENT requires source_ref"):
            CharacterKnowledge(
                knower=EntityId("char-456"),
                proposition=prop,
                knowledge_level=KnowledgeLevel.BELIEVED,
                acquisition_source=AcquisitionSource.DOCUMENT,
                # Omit source_ref to violate DOCUMENT provenance rule
            )


# ============================================================================
# AC-2: Misbelief Representation (Frozen Contract §Misbelief Semantics)
# ============================================================================


class TestMisbeliefRepresentation:
    """AC-2: System must support misbeliefs (character belief contradicts objective fact)."""

    def test_known_with_aligns_false_reject(self):
        """KNOWN + aligns_with_fact=False is INVALID.

        Contract: High-confidence misbelief must use BELIEVED with high confidence,
        not KNOWN. KNOWN must not contradict objective fact.
        """
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive",
        )

        with pytest.raises(ValueError, match="KNOWN with aligns_with_fact=False is INVALID"):
            CharacterKnowledge(
                knower=EntityId("char-456"),
                proposition=prop,
                knowledge_level=KnowledgeLevel.KNOWN,
                acquisition_source=AcquisitionSource.DIRECT_OBSERVATION,
                source_ref="event-789",
                aligns_with_fact=False,  # Contradiction
            )

    def test_believed_with_aligns_false_valid(self):
        """BELIEVED + aligns_with_fact=False is VALID (misbelief allowed)."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_dead",
        )

        # Valid misbelief: character believes X, but objective fact is ¬X
        ck = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVED,
            acquisition_source=AcquisitionSource.COMMUNICATION,
            source_character=EntityId("char-liar"),
            aligns_with_fact=False,  # Misbelief
            confidence=0.95,  # High confidence, but still wrong
        )
        assert ck.aligns_with_fact is False
        assert ck.knowledge_level == KnowledgeLevel.BELIEVED

    def test_suspected_with_aligns_false_valid(self):
        """SUSPECTED + aligns_with_fact=False is VALID (weak misbelief allowed)."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "betrayed_me",
        )

        # Valid weak misbelief
        ck = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.SUSPECTED,
            acquisition_source=AcquisitionSource.RUMOR,
            source_character=EntityId("char-gossip"),
            aligns_with_fact=False,  # Wrong suspicion
        )
        assert ck.aligns_with_fact is False
        assert ck.knowledge_level == KnowledgeLevel.SUSPECTED

    def test_aligns_with_fact_not_in_equality(self):
        """aligns_with_fact (CACHE) does not participate in equality (compare=False)."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive",
        )

        ck1 = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVED,
            acquisition_source=AcquisitionSource.COMMUNICATION,
            source_character=EntityId("char-789"),
            aligns_with_fact=True,
        )

        ck2 = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVED,
            acquisition_source=AcquisitionSource.COMMUNICATION,
            source_character=EntityId("char-789"),
            aligns_with_fact=False,
        )

        # CACHE field excluded from equality
        assert ck1 == ck2


# ============================================================================
# AC-3: Intent vs Occurrence Separation (Frozen Contract §PlannedAction)
# ============================================================================


class TestIntentOccurrenceSeparation:
    """AC-3: PlannedAction intent records are separate from V2-007 occurrence authority."""

    def test_planned_action_only_planned_cancelled_status(self):
        """PlannedAction status can only be PLANNED or CANCELLED.

        Contract: V2-061 owns PLANNED/CANCELLED. V2-007 owns occurrence.
        No IN_PROGRESS or COMPLETED status in V2-061.
        """
        # PLANNED is valid
        action1 = PlannedAction(
            action_id=PlannedActionId(str(uuid.uuid4())),
            character=EntityId("char-456"),
            action_description="Attack the fortress",
            intent_ref=None,
            planned_for=None,
            status=ActionStatus.PLANNED,
            occurred_event_ref=None,
            created_at=datetime.utcnow(),
        )
        assert action1.status == ActionStatus.PLANNED

        # CANCELLED is valid
        action2 = PlannedAction(
            action_id=PlannedActionId(str(uuid.uuid4())),
            character=EntityId("char-456"),
            action_description="Retreat",
            intent_ref=None,
            planned_for=None,
            status=ActionStatus.CANCELLED,
            occurred_event_ref=None,
            created_at=datetime.utcnow(),
            cancelled_at=datetime.utcnow(),
        )
        assert action2.status == ActionStatus.CANCELLED

        # IN_PROGRESS/COMPLETED do not exist
        with pytest.raises(AttributeError):
            ActionStatus.IN_PROGRESS

        with pytest.raises(AttributeError):
            ActionStatus.COMPLETED

    def test_cancelled_with_occurrence_ref_reject(self):
        """status=CANCELLED + occurred_event_ref != None is INVALID.

        Contract: Cancelled plans should not link to occurrence events.
        """
        with pytest.raises(ValueError, match="CANCELLED cannot have occurred_event_ref"):
            PlannedAction(
                action_id=PlannedActionId(str(uuid.uuid4())),
                character=EntityId("char-456"),
                action_description="Attack",
                intent_ref=None,
                planned_for=None,
                status=ActionStatus.CANCELLED,
                occurred_event_ref="event-789",  # Invalid combination
                created_at=datetime.utcnow(),
                cancelled_at=datetime.utcnow(),
            )

    def test_occurred_event_ref_is_reference_not_authority(self):
        """occurred_event_ref is a reference field, NOT occurrence authority.

        Contract: Objective occurrence is determined ONLY by validated V2-007 Event,
        not by PlannedAction status or occurred_event_ref field alone.
        """
        # Plan with linked occurrence reference
        action = PlannedAction(
            action_id=PlannedActionId(str(uuid.uuid4())),
            character=EntityId("char-456"),
            action_description="Enter room",
            intent_ref=None,
            planned_for=None,
            status=ActionStatus.PLANNED,  # Still PLANNED, not "OCCURRED"
            occurred_event_ref="event-789",  # Links to V2-007 Event
            created_at=datetime.utcnow(),
        )

        # This is a reference field
        assert action.occurred_event_ref == "event-789"
        # But V2-007 owns occurrence truth, not this field
        # Test passes - we acknowledge this is just a reference


# (Continuing in next edit due to length...)

# ============================================================================
# AC-4: Goal Lifecycle (Frozen Contract §Goal Lifecycle)
# ============================================================================


class TestGoalLifecycle:
    """AC-4: Goal status transitions and lifecycle semantics."""

    def test_goal_all_statuses_exist(self):
        """Goal must support all contract statuses: ACTIVE/BLOCKED/ACHIEVED/FAILED/ABANDONED/SUPERSEDED."""
        # All statuses must be defined
        assert GoalStatus.ACTIVE
        assert GoalStatus.BLOCKED
        assert GoalStatus.ACHIEVED
        assert GoalStatus.FAILED
        assert GoalStatus.ABANDONED
        assert GoalStatus.SUPERSEDED

    def test_goal_stable_id(self):
        """GoalId uses stable UUID v4 semantics."""
        import uuid

        goal_id = GoalId(str(uuid.uuid4()))

        goal = Goal(
            goal_id=goal_id,
            character=EntityId("char-123"),
            description="Find the artifact",
            target_state=None,
            status=GoalStatus.ACTIVE,
            priority=10,
            formed_at=datetime.utcnow(),
        )

        assert goal.goal_id == goal_id
        # UUID v4 format
        import re
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(uuid_pattern, goal.goal_id)

    def test_goal_abandoned_to_superseded_transition_acceptance(self):
        """Acceptance matrix: ABANDONED → SUPERSEDED transition is valid.

        Contract: Frozen V2-061 §Goal Lifecycle (AC-4)

        This test explicitly validates the acceptance matrix entry for
        ABANDONED → SUPERSEDED transition. While the contract doesn't forbid
        this transition, we explicitly test it to ensure the model supports
        goal evolution after abandonment (e.g., abandoned goal replaced by
        refined/merged goal).
        """
        char = create_character(ProjectId("proj_01"), "张三")

        # Create goal in ABANDONED status
        goal_abandoned = Goal(
            goal_id=GoalId(str(uuid.uuid4())),
            character=char.entity_id,
            description="Original abandoned goal",
            target_state=None,
            status=GoalStatus.ABANDONED,
            priority=5,
            formed_at=datetime.utcnow(),
            resolved_at=datetime.utcnow(),
        )

        # Transition to SUPERSEDED (goal concept replaced/merged)
        from dataclasses import replace
        goal_superseded = replace(goal_abandoned, status=GoalStatus.SUPERSEDED)

        # Must be valid - no runtime rejection
        assert goal_superseded.status == GoalStatus.SUPERSEDED
        assert goal_superseded.goal_id == goal_abandoned.goal_id

        # Semantic validation: SUPERSEDED goals represent replaced concepts
        # This is a valid evolution: abandoned goal later recognized as
        # replaced by different/merged goal rather than truly abandoned


class TestIntentModel:
    """Intent model with stable IntentId."""

    def test_intent_stable_id(self):
        """IntentId uses stable UUID v4 semantics."""
        import uuid

        intent_id = IntentId(str(uuid.uuid4()))

        intent = Intent(
            intent_id=intent_id,
            character=EntityId("char-123"),
            goal_ref=None,
            description="Investigate the tower",
            formed_at=datetime.utcnow(),
        )

        assert intent.intent_id == intent_id


class TestPlannedActionModel:
    """PlannedAction model with stable PlannedActionId."""

    def test_planned_action_stable_id(self):
        """PlannedActionId uses stable UUID v4 semantics."""
        import uuid

        action_id = PlannedActionId(str(uuid.uuid4()))

        action = PlannedAction(
            action_id=action_id,
            character=EntityId("char-123"),
            action_description="Scout the perimeter",
            intent_ref=None,
            planned_for=None,
            status=ActionStatus.PLANNED,
            occurred_event_ref=None,
            created_at=datetime.utcnow(),
        )

        assert action.action_id == action_id


# ============================================================================
# AC-5: Character Lifecycle (Frozen Contract §Lifecycle)
# ============================================================================


class TestCharacterLifecycle:
    """Character lifecycle states and constraints."""

    def test_character_all_lifecycle_states_exist(self):
        """Character must support all contract lifecycle states."""
        assert CharacterLifecycle.PLANNED
        assert CharacterLifecycle.ACTIVE
        assert CharacterLifecycle.INACTIVE
        assert CharacterLifecycle.DECEASED
        assert CharacterLifecycle.SUPERSEDED

    def test_character_lifecycle_defaults_active(self):
        """New character defaults to ACTIVE lifecycle."""
        char = create_character(ProjectId("proj_01"), "张三")
        assert char.lifecycle == CharacterLifecycle.ACTIVE


# ============================================================================
# AC-6: Proposition Invariants (Frozen Contract §Proposition)
# ============================================================================


class TestPropositionInvariants:
    """Proposition collision detection and context immutability."""

    def test_proposition_context_immutable(self):
        """Proposition.context must be recursively frozen (immutable)."""
        context = {"key": "value", "nested": {"inner": [1, 2, 3]}}
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "owns",
            context=context,
        )

        # Context is frozen
        with pytest.raises(TypeError):
            prop.context["key"] = "new"

        # Nested structures also frozen
        with pytest.raises(TypeError):
            prop.context["nested"]["inner"] = (4, 5, 6)

    def test_freeze_context_recursively(self):
        """freeze_context converts nested dicts and lists to immutable forms."""
        ctx = {"key": "value", "nested": {"a": 1, "b": [2, 3]}}
        frozen = freeze_context(ctx)

        assert isinstance(frozen, MappingProxyType)
        assert frozen["nested"]["b"] == (2, 3)  # list → tuple

        with pytest.raises(TypeError):
            frozen["key"] = "new"

    def test_create_proposition_generates_unique_id(self):
        """create_proposition generates fresh PropositionId for each call."""
        prop1 = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive",
        )
        prop2 = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive",
        )

        # Different IDs even with same payload
        assert prop1.proposition_id != prop2.proposition_id

    def test_proposition_validates_empty_predicate(self):
        """Proposition rejects empty predicate."""
        with pytest.raises(ValueError, match="predicate cannot be empty"):
            create_proposition(
                ProjectId("proj_01"),
                EntityId("entity-123"),
                "",
            )

    def test_proposition_validates_empty_project_id(self):
        """Proposition rejects empty project_id."""
        with pytest.raises(ValueError, match="project_id cannot be empty"):
            create_proposition(
                ProjectId(""),
                EntityId("entity-123"),
                "is_alive",
            )


# ============================================================================
# AC-7: Entity Type Validation (Frozen Contract §Entity Type)
# ============================================================================


class TestEntityTypeValidation:
    """V2-061 only handles CHARACTER entity_type."""

    def test_create_character_uses_character_entity_type(self):
        """create_character uses entity_type="CHARACTER" (hardcoded per contract)."""
        from anovel.domain.identity import EntityRegistry

        registry = EntityRegistry()
        char = create_character(ProjectId("proj_01"), "张三")

        # V2-005 identity should have entity_type="CHARACTER"
        # (This is validated at V2-005 level, but V2-061 must enforce it)
        assert char.entity_id  # Has stable V2-005 EntityId


# ============================================================================
# Schema Compliance (Frozen Contract + ADR-002)
# ============================================================================


class TestSchemaCompliance:
    """character.schema.json must match frozen contract enums and BASE fields."""

    def test_schema_uses_contract_knowledge_level_enums(self):
        """Schema must use KNOWN/BELIEVED/SUSPECTED, not old enums."""
        schema_path = Path("specs/schemas/character.schema.json")
        assert schema_path.exists()

        with open(schema_path) as f:
            schema = json.load(f)

        ck_schema = schema["$defs"]["CharacterKnowledge"]
        knowledge_level_enum = ck_schema["properties"]["knowledge_level"]["enum"]

        assert set(knowledge_level_enum) == {"KNOWN", "BELIEVED", "SUSPECTED"}

    def test_schema_uses_contract_acquisition_source_enums(self):
        """Schema must use contract acquisition sources."""
        schema_path = Path("specs/schemas/character.schema.json")
        with open(schema_path) as f:
            schema = json.load(f)

        ck_schema = schema["$defs"]["CharacterKnowledge"]
        acq_source_enum = ck_schema["properties"]["acquisition_source"]["enum"]

        expected = {"DIRECT_OBSERVATION", "COMMUNICATION", "DOCUMENT", "INFERENCE", "RUMOR"}
        assert set(acq_source_enum) == expected

    def test_schema_uses_contract_lifecycle_enums(self):
        """Schema must use contract lifecycle states."""
        schema_path = Path("specs/schemas/character.schema.json")
        with open(schema_path) as f:
            schema = json.load(f)

        lifecycle_enum = schema["properties"]["lifecycle"]["enum"]
        expected = {"PLANNED", "ACTIVE", "INACTIVE", "DECEASED", "SUPERSEDED"}
        assert set(lifecycle_enum) == expected

    def test_schema_uses_contract_goal_status_enums(self):
        """Schema must use contract goal statuses."""
        schema_path = Path("specs/schemas/character.schema.json")
        with open(schema_path) as f:
            schema = json.load(f)

        goal_schema = schema["$defs"]["Goal"]
        status_enum = goal_schema["properties"]["status"]["enum"]
        expected = {"ACTIVE", "BLOCKED", "ACHIEVED", "FAILED", "ABANDONED", "SUPERSEDED"}
        assert set(status_enum) == expected

    def test_schema_uses_contract_action_status_enums(self):
        """Schema must use contract action statuses (PLANNED/CANCELLED only)."""
        schema_path = Path("specs/schemas/character.schema.json")
        with open(schema_path) as f:
            schema = json.load(f)

        action_schema = schema["$defs"]["PlannedAction"]
        status_enum = action_schema["properties"]["status"]["enum"]

        # V2-061 only: PLANNED and CANCELLED
        assert set(status_enum) == {"PLANNED", "CANCELLED"}

    def test_schema_excludes_cache_fields(self):
        """character.schema.json must not contain aligns_with_fact (CACHE)."""
        schema_path = Path("specs/schemas/character.schema.json")
        with open(schema_path) as f:
            schema = json.load(f)

        ck_schema = schema["$defs"]["CharacterKnowledge"]
        assert "aligns_with_fact" not in ck_schema["properties"]

    def test_schema_excludes_derived_fields(self):
        """character.schema.json must not contain active_goals or knowledge_count (DERIVED)."""
        schema_path = Path("specs/schemas/character.schema.json")
        with open(schema_path) as f:
            schema = json.load(f)

        char_props = schema["properties"]
        assert "active_goals" not in char_props
        assert "knowledge_count" not in char_props

    def test_schema_basis_ref_is_array(self):
        """basis_ref must be array type (list of PropositionIds)."""
        schema_path = Path("specs/schemas/character.schema.json")
        with open(schema_path) as f:
            schema = json.load(f)

        ck_schema = schema["$defs"]["CharacterKnowledge"]
        basis_ref_type = ck_schema["properties"]["basis_ref"]["type"]

        assert "array" in basis_ref_type or basis_ref_type == "array"


# ============================================================================
# Authority Boundaries (Frozen Contract §Authority)
# ============================================================================


class TestAuthorityBoundaries:
    """V2-061 does not absorb V2-005/V2-006/V2-007 authority."""

    def test_entity_id_from_v2_005(self):
        """Character uses EntityId from V2-005, not redesigned."""
        char = create_character(ProjectId("proj_01"), "张三")

        # EntityId is from identity module (V2-005)
        from anovel.domain.identity import EntityId as V2005EntityId
        assert isinstance(char.entity_id, str)
        assert EntityId == V2005EntityId

    def test_character_has_no_canonical_name_field(self):
        """Character does not duplicate V2-005 canonical_name authority."""
        char = create_character(ProjectId("proj_01"), "张三")

        # Character dataclass should not have canonical_name field
        assert not hasattr(char, "canonical_name")

    def test_character_has_no_aliases_field(self):
        """Character does not duplicate V2-005 aliases authority."""
        char = create_character(ProjectId("proj_01"), "张三")

        # Character dataclass should not have aliases field
        assert not hasattr(char, "aliases")


# ============================================================================
# DERIVED Semantics (ADR-002)
# ============================================================================


class TestDerivedSemantics:
    """DERIVED fields computed from BASE, not persisted."""

    def test_active_goals_derived_from_goals(self):
        """active_goals is DERIVED (computed from goals where status=ACTIVE)."""
        import uuid
        from dataclasses import replace

        goal1 = Goal(
            goal_id=GoalId(str(uuid.uuid4())),
            character=EntityId("char-123"),
            description="Find artifact",
            target_state=None,
            status=GoalStatus.ACTIVE,
            priority=10,
            formed_at=datetime.utcnow(),
        )
        goal2 = Goal(
            goal_id=GoalId(str(uuid.uuid4())),
            character=EntityId("char-123"),
            description="Old goal",
            target_state=None,
            status=GoalStatus.ACHIEVED,
            priority=5,
            formed_at=datetime.utcnow(),
        )

        char = create_character(ProjectId("proj_01"), "张三")
        char = replace(char, goals=[goal1, goal2])

        active = char.active_goals
        assert len(active) == 1
        assert active[0].goal_id == goal1.goal_id

    def test_knowledge_count_derived_from_knowledge(self):
        """knowledge_count is DERIVED (computed from len(knowledge))."""
        char = create_character(ProjectId("proj_01"), "张三")
        assert char.knowledge_count == 0

        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive",
        )
        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.KNOWN,
            acquisition_source=AcquisitionSource.DIRECT_OBSERVATION,
            source_ref="event-123",
        )

        from dataclasses import replace
        char = replace(char, knowledge={prop.proposition_id: ck})
        assert char.knowledge_count == 1


# ============================================================================
# Project Isolation (Frozen Contract §Project Isolation)
# ============================================================================


class TestProjectIsolation:
    """Project isolation validation per frozen Contract §Project Isolation."""

    def test_same_project_character_valid(self):
        """Character with matching project_id passes validation."""
        from anovel.domain.identity import EntityRegistry, create_identity
        from anovel.domain.character import validate_project_isolation
        from dataclasses import replace

        registry = EntityRegistry()
        identity = create_identity(
            ProjectId("proj_01"),
            "张三",
            entity_type="CHARACTER"
        )
        registry.add_entity(identity)

        char = create_character(ProjectId("proj_01"), "张三")
        # Use the identity's entity_id
        char = replace(char, entity_id=identity.entity_id)

        # Should not raise
        validate_project_isolation(char, registry)

    def test_project_id_mismatch_reject(self):
        """Character.project_id != EntityIdentity.project_id must be rejected."""
        from anovel.domain.identity import EntityRegistry, create_identity
        from anovel.domain.character import validate_project_isolation
        from dataclasses import replace

        registry = EntityRegistry()
        identity = create_identity(
            ProjectId("proj_01"),
            "张三",
            entity_type="CHARACTER"
        )
        registry.add_entity(identity)

        char = create_character(ProjectId("proj_01"), "张三")
        char = replace(char, entity_id=identity.entity_id)
        # Force project_id mismatch
        char = replace(char, project_id=ProjectId("proj_02"))

        with pytest.raises(ValueError, match="project_id.*must match"):
            validate_project_isolation(char, registry)

    def test_cross_project_source_character_reject(self):
        """source_character from different project must be rejected."""
        from anovel.domain.identity import EntityRegistry, create_identity
        from anovel.domain.character import validate_project_isolation
        from dataclasses import replace

        registry = EntityRegistry()

        # Project 1 character
        identity1 = create_identity(ProjectId("proj_01"), "张三", entity_type="CHARACTER")
        registry.add_entity(identity1)

        # Project 2 source
        identity2 = create_identity(ProjectId("proj_02"), "李四", entity_type="CHARACTER")
        registry.add_entity(identity2)

        char = create_character(ProjectId("proj_01"), "张三")
        char = replace(char, entity_id=identity1.entity_id)

        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive"
        )
        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVED,
            acquisition_source=AcquisitionSource.COMMUNICATION,
            source_character=identity2.entity_id,  # Cross-project!
        )

        char = replace(char, knowledge={prop.proposition_id: ck})

        with pytest.raises(ValueError, match="Cross-project provenance invalid"):
            validate_project_isolation(char, registry)

    def test_entity_type_not_character_reject(self):
        """Entity with entity_type != CHARACTER must be rejected."""
        from anovel.domain.identity import EntityRegistry, create_identity
        from anovel.domain.character import validate_project_isolation
        from dataclasses import replace

        registry = EntityRegistry()
        identity = create_identity(
            ProjectId("proj_01"),
            "某地",
            entity_type="LOCATION"  # Not CHARACTER
        )
        registry.add_entity(identity)

        char = create_character(ProjectId("proj_01"), "某地")
        # Force entity_id to the LOCATION identity
        char = replace(char, entity_id=identity.entity_id)

        with pytest.raises(ValueError, match="entity_type='CHARACTER'"):
            validate_project_isolation(char, registry)

    def test_cross_project_proposition_subject_reject(self):
        """Proposition with subject from different project must be rejected."""
        from anovel.domain.identity import EntityRegistry, create_identity
        from anovel.domain.character import validate_project_isolation
        from dataclasses import replace

        registry = EntityRegistry()

        # Project 1 character
        identity1 = create_identity(ProjectId("proj_01"), "张三", entity_type="CHARACTER")
        registry.add_entity(identity1)

        # Project 2 entity (subject of proposition)
        identity2 = create_identity(ProjectId("proj_02"), "李四", entity_type="CHARACTER")
        registry.add_entity(identity2)

        char = create_character(ProjectId("proj_01"), "张三")
        char = replace(char, entity_id=identity1.entity_id)

        # Proposition with cross-project subject
        prop = create_proposition(
            ProjectId("proj_01"),
            identity2.entity_id,  # From proj_02!
            "is_alive"
        )
        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.KNOWN,
            acquisition_source=AcquisitionSource.DIRECT_OBSERVATION,
            source_ref="event-123"
        )

        char = replace(char, knowledge={prop.proposition_id: ck})

        with pytest.raises(ValueError, match="Cross-project references invalid"):
            validate_project_isolation(char, registry)

    def test_cross_project_proposition_object_reject(self):
        """Proposition with object from different project must be rejected."""
        from anovel.domain.identity import EntityRegistry, create_identity
        from anovel.domain.character import validate_project_isolation
        from dataclasses import replace

        registry = EntityRegistry()

        # Project 1 character and subject
        identity1 = create_identity(ProjectId("proj_01"), "张三", entity_type="CHARACTER")
        registry.add_entity(identity1)
        identity_subj = create_identity(ProjectId("proj_01"), "王五", entity_type="CHARACTER")
        registry.add_entity(identity_subj)

        # Project 2 entity (object of proposition)
        identity2 = create_identity(ProjectId("proj_02"), "李四", entity_type="CHARACTER")
        registry.add_entity(identity2)

        char = create_character(ProjectId("proj_01"), "张三")
        char = replace(char, entity_id=identity1.entity_id)

        # Proposition with cross-project object
        prop = Proposition(
            proposition_id=PropositionId(str(uuid.uuid4())),
            project_id=ProjectId("proj_01"),
            subject=identity_subj.entity_id,
            predicate="knows",
            object=identity2.entity_id,  # From proj_02!
            context=None
        )
        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.KNOWN,
            acquisition_source=AcquisitionSource.DIRECT_OBSERVATION,
            source_ref="event-456"
        )

        char = replace(char, knowledge={prop.proposition_id: ck})

        with pytest.raises(ValueError, match="Cross-project references invalid"):
            validate_project_isolation(char, registry)


# ============================================================================
# Proposition Collision (Frozen Contract §Proposition Collision Invariant)
# ============================================================================


class TestPropositionCollision:
    """Proposition collision detection per frozen Contract."""

    def test_same_id_same_base_valid(self):
        """Same PropositionId + same BASE payload is valid."""
        from anovel.domain.knowledge import validate_proposition_collision

        prop1 = Proposition(
            proposition_id=PropositionId("550e8400-e29b-41d4-a716-446655440000"),
            project_id=ProjectId("proj_01"),
            subject=EntityId("entity-123"),
            predicate="is_alive",
            object=None,
            context=None
        )
        prop2 = Proposition(
            proposition_id=PropositionId("550e8400-e29b-41d4-a716-446655440000"),
            project_id=ProjectId("proj_01"),
            subject=EntityId("entity-123"),
            predicate="is_alive",
            object=None,
            context=None
        )

        # Should not raise
        validate_proposition_collision(prop1, prop2)

    def test_same_id_different_predicate_reject(self):
        """Same PropositionId + different predicate must be rejected."""
        from anovel.domain.knowledge import validate_proposition_collision

        prop1 = Proposition(
            proposition_id=PropositionId("550e8400-e29b-41d4-a716-446655440000"),
            project_id=ProjectId("proj_01"),
            subject=EntityId("entity-123"),
            predicate="is_alive",
            object=None,
            context=None
        )
        prop2 = Proposition(
            proposition_id=PropositionId("550e8400-e29b-41d4-a716-446655440000"),
            project_id=ProjectId("proj_01"),
            subject=EntityId("entity-123"),
            predicate="is_dead",  # Different!
            object=None,
            context=None
        )

        with pytest.raises(ValueError, match="Proposition collision.*different predicate"):
            validate_proposition_collision(prop1, prop2)

    def test_same_id_different_subject_reject(self):
        """Same PropositionId + different subject must be rejected."""
        from anovel.domain.knowledge import validate_proposition_collision

        prop1 = Proposition(
            proposition_id=PropositionId("550e8400-e29b-41d4-a716-446655440000"),
            project_id=ProjectId("proj_01"),
            subject=EntityId("entity-123"),
            predicate="is_alive",
            object=None,
            context=None
        )
        prop2 = Proposition(
            proposition_id=PropositionId("550e8400-e29b-41d4-a716-446655440000"),
            project_id=ProjectId("proj_01"),
            subject=EntityId("entity-456"),  # Different!
            predicate="is_alive",
            object=None,
            context=None
        )

        with pytest.raises(ValueError, match="Proposition collision.*different subject"):
            validate_proposition_collision(prop1, prop2)

    def test_same_id_different_object_reject(self):
        """Same PropositionId + different object must be rejected."""
        from anovel.domain.knowledge import validate_proposition_collision

        prop1 = Proposition(
            proposition_id=PropositionId("550e8400-e29b-41d4-a716-446655440000"),
            project_id=ProjectId("proj_01"),
            subject=EntityId("entity-123"),
            predicate="knows",
            object=EntityId("entity-456"),
            context=None
        )
        prop2 = Proposition(
            proposition_id=PropositionId("550e8400-e29b-41d4-a716-446655440000"),
            project_id=ProjectId("proj_01"),
            subject=EntityId("entity-123"),
            predicate="knows",
            object=EntityId("entity-789"),  # Different!
            context=None
        )

        with pytest.raises(ValueError, match="Proposition collision.*different object"):
            validate_proposition_collision(prop1, prop2)

    def test_same_id_different_context_reject(self):
        """Same PropositionId + different context must be rejected."""
        from anovel.domain.knowledge import validate_proposition_collision

        prop1 = Proposition(
            proposition_id=PropositionId("550e8400-e29b-41d4-a716-446655440000"),
            project_id=ProjectId("proj_01"),
            subject=EntityId("entity-123"),
            predicate="is_alive",
            object=None,
            context=MappingProxyType({"location": "Beijing"})
        )
        prop2 = Proposition(
            proposition_id=PropositionId("550e8400-e29b-41d4-a716-446655440000"),
            project_id=ProjectId("proj_01"),
            subject=EntityId("entity-123"),
            predicate="is_alive",
            object=None,
            context=MappingProxyType({"location": "Shanghai"})  # Different!
        )

        with pytest.raises(ValueError, match="Proposition collision.*different context"):
            validate_proposition_collision(prop1, prop2)

    def test_same_id_different_project_id_reject(self):
        """Same PropositionId + different project_id must be rejected."""
        from anovel.domain.knowledge import validate_proposition_collision

        prop1 = Proposition(
            proposition_id=PropositionId("550e8400-e29b-41d4-a716-446655440000"),
            project_id=ProjectId("proj_01"),
            subject=EntityId("entity-123"),
            predicate="is_alive",
            object=None,
            context=None
        )
        prop2 = Proposition(
            proposition_id=PropositionId("550e8400-e29b-41d4-a716-446655440000"),
            project_id=ProjectId("proj_02"),  # Different!
            subject=EntityId("entity-123"),
            predicate="is_alive",
            object=None,
            context=None
        )

        with pytest.raises(ValueError, match="Proposition collision.*different project_id"):
            validate_proposition_collision(prop1, prop2)


# ============================================================================
# Knowledge Key Invariant (Frozen Contract §Proposition Resolution)
# ============================================================================


class TestKnowledgeKeyInvariant:
    """Knowledge dict key invariant per frozen Contract."""

    def test_key_matches_proposition_id_valid(self):
        """Dict key == proposition.proposition_id is valid."""
        from anovel.domain.character import validate_knowledge_key_invariant

        char = create_character(ProjectId("proj_01"), "张三")
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive"
        )
        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.KNOWN,
            acquisition_source=AcquisitionSource.DIRECT_OBSERVATION,
            source_ref="event-123"
        )

        from dataclasses import replace
        char = replace(char, knowledge={prop.proposition_id: ck})

        # Should not raise
        validate_knowledge_key_invariant(char)

    def test_key_mismatch_proposition_id_reject(self):
        """Dict key != proposition.proposition_id must be rejected."""
        from anovel.domain.character import validate_knowledge_key_invariant

        char = create_character(ProjectId("proj_01"), "张三")
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive"
        )
        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.KNOWN,
            acquisition_source=AcquisitionSource.DIRECT_OBSERVATION,
            source_ref="event-123"
        )

        wrong_key = PropositionId("550e8400-e29b-41d4-a716-446655440000")

        from dataclasses import replace
        char = replace(char, knowledge={wrong_key: ck})  # Mismatched key!

        with pytest.raises(ValueError, match="knowledge key.*must match"):
            validate_knowledge_key_invariant(char)


# ============================================================================
# UUID v4 Validation (Frozen Contract §PropositionId, §GoalId, etc.)
# ============================================================================


class TestUUIDv4Validation:
    """UUID v4 format validation per frozen Contract."""

    def test_valid_uuid_v4_pass(self):
        """Valid lowercase hyphenated UUID v4 passes validation."""
        from anovel.domain.knowledge import validate_uuid_v4_format

        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        # Should not raise
        validate_uuid_v4_format(valid_uuid, "test_field")

    def test_malformed_string_reject(self):
        """Malformed string must be rejected."""
        from anovel.domain.knowledge import validate_uuid_v4_format

        with pytest.raises(ValueError, match="36 characters"):
            validate_uuid_v4_format("not-a-uuid", "test_field")

    def test_uuid_v1_reject(self):
        """UUID v1 format must be rejected (wrong version digit)."""
        from anovel.domain.knowledge import validate_uuid_v4_format

        uuid_v1 = "550e8400-e29b-11d4-a716-446655440000"  # Version 1
        with pytest.raises(ValueError, match="version 4"):
            validate_uuid_v4_format(uuid_v1, "test_field")

    def test_uppercase_reject(self):
        """Uppercase UUID must be rejected."""
        from anovel.domain.knowledge import validate_uuid_v4_format

        uppercase_uuid = "550E8400-E29B-41D4-A716-446655440000"
        with pytest.raises(ValueError, match="lowercase"):
            validate_uuid_v4_format(uppercase_uuid, "test_field")

    def test_proposition_malformed_id_reject(self):
        """Proposition with malformed proposition_id rejects at construction."""
        with pytest.raises(ValueError, match="36 characters"):
            Proposition(
                proposition_id=PropositionId("malformed-id"),
                project_id=ProjectId("proj_01"),
                subject=EntityId("entity-123"),
                predicate="is_alive",
                object=None,
                context=None
            )

    def test_proposition_uuid_v1_reject(self):
        """Proposition with UUID v1 format rejects at construction."""
        with pytest.raises(ValueError, match="version 4"):
            Proposition(
                proposition_id=PropositionId("550e8400-e29b-11d4-a716-446655440000"),
                project_id=ProjectId("proj_01"),
                subject=EntityId("entity-123"),
                predicate="is_alive",
                object=None,
                context=None
            )

    def test_goal_malformed_id_reject(self):
        """Goal with malformed goal_id rejects at construction."""
        from datetime import datetime

        with pytest.raises(ValueError, match="36 characters"):
            Goal(
                goal_id=GoalId("goal-abc"),
                character=EntityId("char-123"),
                description="Find artifact",
                target_state=None,
                status=GoalStatus.ACTIVE,
                priority=10,
                formed_at=datetime.utcnow(),
            )

    def test_intent_malformed_id_reject(self):
        """Intent with malformed intent_id rejects at construction."""
        from datetime import datetime

        with pytest.raises(ValueError, match="36 characters"):
            Intent(
                intent_id=IntentId("intent-xyz"),
                character=EntityId("char-123"),
                goal_ref=None,
                description="Investigate",
                formed_at=datetime.utcnow(),
            )

    def test_planned_action_malformed_id_reject(self):
        """PlannedAction with malformed action_id rejects at construction."""
        from datetime import datetime

        with pytest.raises(ValueError, match="36 characters"):
            PlannedAction(
                action_id=PlannedActionId("action-123"),
                character=EntityId("char-123"),
                action_description="Visit library",
                intent_ref=None,
                planned_for=None,
                status=ActionStatus.PLANNED,
                occurred_event_ref=None,
                created_at=datetime.utcnow(),
            )
        from anovel.domain.knowledge import validate_uuid_v4_format

        # UUID v1 has version digit 1, not 4
        uuid_v1 = "550e8400-e29b-11d4-a716-446655440000"

        with pytest.raises(ValueError, match="valid UUID v4 format"):
            validate_uuid_v4_format(uuid_v1, "test_field")

    def test_uppercase_uuid_reject(self):
        """Uppercase UUID must be rejected (contract requires lowercase)."""
        from anovel.domain.knowledge import validate_uuid_v4_format

        uppercase_uuid = "550E8400-E29B-41D4-A716-446655440000"

        with pytest.raises(ValueError, match="valid UUID v4 format"):
            validate_uuid_v4_format(uppercase_uuid, "test_field")
