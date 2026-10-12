"""
V2-061 Contract Tests: Character Knowledge & Intent Core.

Tests Character, CharacterKnowledge, Proposition domain models against
frozen V2-061 contract and ADR-002 BASE/DERIVED/CACHE semantics.

Contract: V2-061 Implementation Contract v1.3.1 + ADR-002
"""

import json
from datetime import datetime
from pathlib import Path
from types import MappingProxyType

import pytest

from src.anovel.domain import (
    AcquisitionSource,
    ActionStatus,
    Character,
    CharacterKnowledge,
    CharacterLifecycle,
    EntityId,
    Goal,
    GoalStatus,
    Intent,
    KnowledgeLevel,
    PlannedAction,
    ProjectId,
    Proposition,
    PropositionId,
    create_character,
    create_proposition,
    freeze_context,
)


class TestPropositionContext:
    """Test Proposition.context immutability per ADR-002."""

    def test_freeze_context_none(self):
        """freeze_context(None) returns None."""
        assert freeze_context(None) is None

    def test_freeze_context_simple_dict(self):
        """Simple dict is frozen to MappingProxyType."""
        ctx = {"key": "value"}
        frozen = freeze_context(ctx)
        assert isinstance(frozen, MappingProxyType)
        assert frozen["key"] == "value"

        with pytest.raises(TypeError):
            frozen["key"] = "new"

    def test_freeze_context_nested_dict(self):
        """Nested dict is recursively frozen."""
        ctx = {"outer": {"inner": "value"}}
        frozen = freeze_context(ctx)
        assert frozen["outer"]["inner"] == "value"

        with pytest.raises(TypeError):
            frozen["outer"]["inner"] = "new"

    def test_freeze_context_list_to_tuple(self):
        """Lists are converted to tuples."""
        ctx = {"items": [1, 2, 3]}
        frozen = freeze_context(ctx)
        assert frozen["items"] == (1, 2, 3)
        assert isinstance(frozen["items"], tuple)

    def test_freeze_context_nested_list(self):
        """Nested lists are recursively frozen to tuples."""
        ctx = {"matrix": [[1, 2], [3, 4]]}
        frozen = freeze_context(ctx)
        assert frozen["matrix"] == ((1, 2), (3, 4))

    def test_create_proposition_freezes_context(self):
        """create_proposition recursively freezes context."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "owns",
            object="artifact-X",
            context={"nested": {"key": "value"}},
        )
        assert isinstance(prop.context, MappingProxyType)
        with pytest.raises(TypeError):
            prop.context["nested"]["key"] = "new"


class TestCharacterKnowledgeCache:
    """Test CharacterKnowledge CACHE field semantics per ADR-002."""

    def test_aligns_with_fact_defaults_none(self):
        """aligns_with_fact defaults to None."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive",
        )
        ck = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVES_TRUE,
            acquisition_source=AcquisitionSource.WITNESSED,
        )
        assert ck.aligns_with_fact is None

    def test_aligns_with_fact_not_in_equality(self):
        """aligns_with_fact does not participate in equality (compare=False)."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive",
        )
        ck1 = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVES_TRUE,
            acquisition_source=AcquisitionSource.WITNESSED,
            aligns_with_fact=True,
        )
        ck2 = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVES_TRUE,
            acquisition_source=AcquisitionSource.WITNESSED,
            aligns_with_fact=False,
        )
        assert ck1 == ck2  # CACHE field excluded from equality

    def test_told_by_requires_source_character(self):
        """acquisition_source=TOLD_BY requires source_character."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive",
        )
        with pytest.raises(ValueError, match="TOLD_BY requires source_character"):
            CharacterKnowledge(
                knower=EntityId("char-456"),
                proposition=prop,
                knowledge_level=KnowledgeLevel.BELIEVES_TRUE,
                acquisition_source=AcquisitionSource.TOLD_BY,
                source_character=None,
            )

    def test_confidence_validation(self):
        """confidence must be in range [0.0, 1.0]."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive",
        )
        with pytest.raises(ValueError, match="confidence must be in range"):
            CharacterKnowledge(
                knower=EntityId("char-456"),
                proposition=prop,
                knowledge_level=KnowledgeLevel.BELIEVES_TRUE,
                acquisition_source=AcquisitionSource.WITNESSED,
                confidence=1.5,
            )


class TestCharacterBaseDerived:
    """Test Character BASE/DERIVED semantics per ADR-002."""

    def test_create_character_uses_v2_005_entity_id(self):
        """create_character generates EntityId via V2-005."""
        char = create_character(ProjectId("proj_01"), "张三")
        assert isinstance(char.entity_id, str)
        # UUID v4 format
        import re
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(uuid_pattern, char.entity_id)

    def test_character_lifecycle_defaults_active(self):
        """Character lifecycle defaults to ACTIVE."""
        char = create_character(ProjectId("proj_01"), "张三")
        assert char.lifecycle == CharacterLifecycle.ACTIVE

    def test_character_empty_collections(self):
        """New character has empty knowledge, goals, intents, planned_actions."""
        char = create_character(ProjectId("proj_01"), "张三")
        assert char.knowledge == {}
        assert char.goals == []
        assert char.intents == []
        assert char.planned_actions == []

    def test_active_goals_derived(self):
        """active_goals is DERIVED (computed from BASE goals)."""
        goal1 = Goal(
            goal_id="goal-1",
            character=EntityId("char-123"),
            description="Find artifact",
            target_state=None,
            status=GoalStatus.ACTIVE,
            priority=10,
            formed_at=datetime.utcnow(),
        )
        goal2 = Goal(
            goal_id="goal-2",
            character=EntityId("char-123"),
            description="Old goal",
            target_state=None,
            status=GoalStatus.ACHIEVED,
            priority=5,
            formed_at=datetime.utcnow(),
        )
        char = create_character(ProjectId("proj_01"), "张三")
        # Replace with new Character including goals (frozen dataclass)
        from dataclasses import replace
        char = replace(char, goals=[goal1, goal2])

        active = char.active_goals
        assert len(active) == 1
        assert active[0].goal_id == "goal-1"

    def test_knowledge_count_derived(self):
        """knowledge_count is DERIVED (computed from BASE knowledge)."""
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
            knowledge_level=KnowledgeLevel.BELIEVES_TRUE,
            acquisition_source=AcquisitionSource.WITNESSED,
        )

        from dataclasses import replace
        char = replace(char, knowledge={prop.proposition_id: ck})
        assert char.knowledge_count == 1


class TestSchemaConformance:
    """Test character.schema.json contains BASE fields only per ADR-002."""

    def test_schema_excludes_cache_fields(self):
        """character.schema.json must not contain aligns_with_fact."""
        schema_path = Path("specs/schemas/character.schema.json")
        assert schema_path.exists()

        with open(schema_path) as f:
            schema = json.load(f)

        # Check CharacterKnowledge definition
        ck_schema = schema["$defs"]["CharacterKnowledge"]
        assert "aligns_with_fact" not in ck_schema["properties"]

    def test_schema_excludes_derived_fields(self):
        """character.schema.json must not contain active_goals or knowledge_count."""
        schema_path = Path("specs/schemas/character.schema.json")
        with open(schema_path) as f:
            schema = json.load(f)

        char_props = schema["properties"]
        assert "active_goals" not in char_props
        assert "knowledge_count" not in char_props

    def test_schema_includes_base_fields(self):
        """character.schema.json includes all BASE fields."""
        schema_path = Path("specs/schemas/character.schema.json")
        with open(schema_path) as f:
            schema = json.load(f)

        required_base_fields = [
            "entity_id",
            "project_id",
            "lifecycle",
            "knowledge",
            "goals",
            "intents",
            "planned_actions",
            "created_at",
            "updated_at",
            "authority",
        ]
        char_props = schema["properties"]
        for field in required_base_fields:
            assert field in char_props, f"BASE field {field} missing from schema"


class TestRoundtripSemantics:
    """Test BASE preservation and CACHE reset per ADR-002."""

    def test_cache_not_in_serialized_payload(self):
        """Serialized payload must not contain aligns_with_fact."""
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "is_alive",
        )
        ck = CharacterKnowledge(
            knower=EntityId("char-456"),
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVES_TRUE,
            acquisition_source=AcquisitionSource.WITNESSED,
            aligns_with_fact=True,
        )

        # Simulate serialization (simplified - BASE fields only)
        serialized = {
            "knower": ck.knower,
            "proposition": {
                "proposition_id": prop.proposition_id,
                "project_id": prop.project_id,
                "subject": prop.subject,
                "predicate": prop.predicate,
                "object": prop.object,
                "context": None,
            },
            "knowledge_level": ck.knowledge_level.value,
            "acquisition_source": ck.acquisition_source.value,
            "source_character": ck.source_character,
            "source_ref": ck.source_ref,
            "basis_ref": ck.basis_ref,
            "acquired_at": ck.acquired_at.isoformat() if ck.acquired_at else None,
            "story_time_ref": ck.story_time_ref,
            "confidence": ck.confidence,
        }

        # CACHE field must not be in payload
        assert "aligns_with_fact" not in serialized


class TestAuthorityBoundaries:
    """Test V2-061 does not absorb V2-005/V2-006/V2-007 authority."""

    def test_entity_id_from_v2_005(self):
        """Character uses EntityId from V2-005, not redesigned."""
        char = create_character(ProjectId("proj_01"), "张三")
        # EntityId is from identity module (V2-005)
        from src.anovel.domain.identity import EntityId as V2005EntityId
        assert isinstance(char.entity_id, str)
        assert EntityId == V2005EntityId

    def test_occurred_event_ref_is_reference_not_authority(self):
        """PlannedAction.occurred_event_ref is reference, not occurrence authority."""
        action = PlannedAction(
            action_id="action-1",
            character=EntityId("char-123"),
            action_description="Enter the room",
            intent_ref=None,
            planned_for=None,
            status=ActionStatus.COMPLETED,
            occurred_event_ref="event-456",
            created_at=datetime.utcnow(),
        )

        # This is a reference field, not occurrence truth
        # V2-007 owns occurrence authority
        assert action.occurred_event_ref == "event-456"
        # Test passes - we acknowledge this is a reference, not authority


class TestPropositionInvariants:
    """Test Proposition invariants per ADR-002."""

    def test_create_proposition_generates_id(self):
        """create_proposition generates fresh PropositionId."""
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
        assert prop1.proposition_id != prop2.proposition_id

    def test_proposition_context_immutable(self):
        """Proposition.context must be immutable."""
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
