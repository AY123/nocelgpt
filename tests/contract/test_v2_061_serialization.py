"""
V2-061 Serialization Tests: BASE/DERIVED/CACHE semantics.

Tests Character serialization/deserialization against ADR-002:
- BASE fields persisted exactly
- DERIVED fields excluded from serialization, recomputed after deserialization
- CACHE fields excluded from serialization
- Schema validation compliance
- Round-trip preservation

Contract Authority: ADR-002 + Frozen V2-061 §Serialization
"""

import uuid
from datetime import datetime
from types import MappingProxyType

import pytest

from src.anovel.domain import (
    AcquisitionSource,
    ActionStatus,
    Character,
    CharacterKnowledge,
    CharacterLifecycle,
    Goal,
    GoalId,
    GoalStatus,
    Intent,
    IntentId,
    KnowledgeLevel,
    PlannedAction,
    PlannedActionId,
    Proposition,
    PropositionId,
    create_character,
    create_proposition,
)
from src.anovel.domain.identity import EntityId, ProjectId
from src.anovel.domain.serialization import (
    deserialize_character,
    serialize_character,
    validate_against_schema,
)


class TestBASESerialization:
    """BASE fields must be serialized exactly."""

    def test_minimal_character_serialization(self):
        """Minimal Character with empty collections serializes to BASE fields only."""
        char = create_character(ProjectId("proj_01"), "张三", authority="test")

        data = serialize_character(char)

        # BASE fields present
        assert data["entity_id"] == char.entity_id
        assert data["project_id"] == "proj_01"
        assert data["lifecycle"] == "ACTIVE"
        assert data["knowledge"] == {}
        assert data["goals"] == []
        assert data["intents"] == []
        assert data["planned_actions"] == []
        assert "created_at" in data
        assert "updated_at" in data
        assert data["authority"] == "test"
        assert data["provenance"] == {}

        # DERIVED fields excluded
        assert "active_goals" not in data
        assert "knowledge_count" not in data

    def test_character_with_knowledge_serialization(self):
        """Character with knowledge serializes CharacterKnowledge BASE fields."""
        char = create_character(ProjectId("proj_01"), "张三")
        prop = create_proposition(ProjectId("proj_01"), EntityId("entity-123"), "is_alive")

        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.KNOWN,
            acquisition_source=AcquisitionSource.DIRECT_OBSERVATION,
            source_ref="event-123",
            aligns_with_fact=True,  # CACHE field
        )

        from dataclasses import replace
        char = replace(char, knowledge={prop.proposition_id: ck})

        data = serialize_character(char)

        ck_data = data["knowledge"][prop.proposition_id]
        assert ck_data["knower"] == char.entity_id
        assert ck_data["knowledge_level"] == "KNOWN"
        assert ck_data["acquisition_source"] == "DIRECT_OBSERVATION"
        assert ck_data["source_ref"] == "event-123"

        # CACHE field excluded
        assert "aligns_with_fact" not in ck_data

    def test_character_with_goals_serialization(self):
        """Character with goals serializes Goal BASE fields."""
        char = create_character(ProjectId("proj_01"), "张三")

        goal = Goal(
            goal_id=GoalId(str(uuid.uuid4())),
            character=char.entity_id,
            description="Find artifact",
            target_state=MappingProxyType({"has_artifact": "true"}),
            status=GoalStatus.ACTIVE,
            priority=10,
            formed_at=datetime.utcnow(),
        )

        from dataclasses import replace
        char = replace(char, goals=[goal])

        data = serialize_character(char)

        assert len(data["goals"]) == 1
        goal_data = data["goals"][0]
        assert goal_data["goal_id"] == goal.goal_id
        assert goal_data["character"] == char.entity_id
        assert goal_data["description"] == "Find artifact"
        assert goal_data["target_state"] == {"has_artifact": "true"}
        assert goal_data["status"] == "ACTIVE"
        assert goal_data["priority"] == 10
        assert "formed_at" in goal_data

    def test_character_with_structured_provenance(self):
        """Character with structured provenance dict serializes correctly."""
        char = create_character(ProjectId("proj_01"), "张三")

        from dataclasses import replace
        char = replace(char, provenance={"source": "manual_creation", "version": "1.0"})

        data = serialize_character(char)

        assert data["provenance"] == {"source": "manual_creation", "version": "1.0"}
        assert isinstance(data["provenance"], dict)


class TestDERIVEDExclusion:
    """DERIVED fields must be excluded from serialization."""

    def test_active_goals_not_serialized(self):
        """active_goals DERIVED field not in serialized output."""
        char = create_character(ProjectId("proj_01"), "张三")

        goal1 = Goal(
            goal_id=GoalId(str(uuid.uuid4())),
            character=char.entity_id,
            description="Active goal",
            target_state=None,
            status=GoalStatus.ACTIVE,
            priority=10,
            formed_at=datetime.utcnow(),
        )
        goal2 = Goal(
            goal_id=GoalId(str(uuid.uuid4())),
            character=char.entity_id,
            description="Achieved goal",
            target_state=None,
            status=GoalStatus.ACHIEVED,
            priority=5,
            formed_at=datetime.utcnow(),
        )

        from dataclasses import replace
        char = replace(char, goals=[goal1, goal2])

        # Verify DERIVED property works
        assert len(char.active_goals) == 1
        assert char.active_goals[0].goal_id == goal1.goal_id

        data = serialize_character(char)

        # active_goals not in serialized output
        assert "active_goals" not in data
        # Only BASE goals field present
        assert len(data["goals"]) == 2

    def test_knowledge_count_not_serialized(self):
        """knowledge_count DERIVED field not in serialized output."""
        char = create_character(ProjectId("proj_01"), "张三")
        prop = create_proposition(ProjectId("proj_01"), EntityId("entity-123"), "is_alive")

        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.KNOWN,
            acquisition_source=AcquisitionSource.DIRECT_OBSERVATION,
            source_ref="event-123",
        )

        from dataclasses import replace
        char = replace(char, knowledge={prop.proposition_id: ck})

        # Verify DERIVED property works
        assert char.knowledge_count == 1

        data = serialize_character(char)

        # knowledge_count not in serialized output
        assert "knowledge_count" not in data
        # Only BASE knowledge field present
        assert len(data["knowledge"]) == 1


class TestCACHEExclusion:
    """CACHE fields must be excluded from serialization."""

    def test_aligns_with_fact_not_serialized(self):
        """aligns_with_fact CACHE field not in serialized output."""
        char = create_character(ProjectId("proj_01"), "张三")
        prop = create_proposition(ProjectId("proj_01"), EntityId("entity-123"), "is_alive")

        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVED,
            acquisition_source=AcquisitionSource.INFERENCE,
            basis_ref=(PropositionId(str(uuid.uuid4())),),
            aligns_with_fact=False,  # CACHE field
        )

        from dataclasses import replace
        char = replace(char, knowledge={prop.proposition_id: ck})

        data = serialize_character(char)

        ck_data = data["knowledge"][prop.proposition_id]
        # aligns_with_fact not in serialized output
        assert "aligns_with_fact" not in ck_data


class TestRoundTripPreservation:
    """Round-trip serialization/deserialization must preserve BASE state."""

    def test_minimal_character_round_trip(self):
        """Minimal Character round-trip preserves BASE state."""
        char = create_character(ProjectId("proj_01"), "张三", authority="test")

        data = serialize_character(char)
        char2 = deserialize_character(data)

        assert char2.entity_id == char.entity_id
        assert char2.project_id == char.project_id
        assert char2.lifecycle == char.lifecycle
        assert char2.knowledge == char.knowledge
        assert char2.goals == char.goals
        assert char2.intents == char.intents
        assert char2.planned_actions == char.planned_actions
        assert char2.authority == char.authority
        assert char2.provenance == char.provenance

    def test_character_with_non_default_data_round_trip(self):
        """Character with non-default data preserves exact BASE state."""
        char = create_character(ProjectId("proj_01"), "张三")

        # Add knowledge
        prop = create_proposition(
            ProjectId("proj_01"),
            EntityId("entity-123"),
            "knows",
            object="secret",
        )
        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVED,
            acquisition_source=AcquisitionSource.COMMUNICATION,
            source_character=EntityId("entity-456"),
            confidence=0.7,
        )

        # Add goal
        goal = Goal(
            goal_id=GoalId(str(uuid.uuid4())),
            character=char.entity_id,
            description="Find truth",
            target_state=MappingProxyType({"truth_found": "true"}),
            status=GoalStatus.BLOCKED,
            priority=20,
            formed_at=datetime.utcnow(),
        )

        # Add intent
        intent = Intent(
            intent_id=IntentId(str(uuid.uuid4())),
            character=char.entity_id,
            goal_ref=goal.goal_id,
            description="Investigate clues",
            formed_at=datetime.utcnow(),
        )

        # Add planned action
        action = PlannedAction(
            action_id=PlannedActionId(str(uuid.uuid4())),
            character=char.entity_id,
            action_description="Visit library",
            intent_ref=intent.intent_id,
            planned_for="tomorrow",
            status=ActionStatus.PLANNED,
            occurred_event_ref=None,
            created_at=datetime.utcnow(),
        )

        from dataclasses import replace
        char = replace(
            char,
            lifecycle=CharacterLifecycle.INACTIVE,
            knowledge={prop.proposition_id: ck},
            goals=[goal],
            intents=[intent],
            planned_actions=[action],
            provenance={"source": "test", "version": "2.0"},
        )

        data = serialize_character(char)
        char2 = deserialize_character(data)

        # BASE state preserved
        assert char2.lifecycle == CharacterLifecycle.INACTIVE
        assert len(char2.knowledge) == 1
        assert char2.knowledge[prop.proposition_id].confidence == 0.7
        assert len(char2.goals) == 1
        assert char2.goals[0].status == GoalStatus.BLOCKED
        assert char2.goals[0].priority == 20
        assert len(char2.intents) == 1
        assert char2.intents[0].goal_ref == goal.goal_id
        assert len(char2.planned_actions) == 1
        assert char2.planned_actions[0].intent_ref == intent.intent_id
        assert char2.provenance == {"source": "test", "version": "2.0"}

    def test_derived_fields_recomputed_after_deserialization(self):
        """DERIVED fields recomputed from BASE after deserialization."""
        char = create_character(ProjectId("proj_01"), "张三")

        goal1 = Goal(
            goal_id=GoalId(str(uuid.uuid4())),
            character=char.entity_id,
            description="Active goal",
            target_state=None,
            status=GoalStatus.ACTIVE,
            priority=10,
            formed_at=datetime.utcnow(),
        )
        goal2 = Goal(
            goal_id=GoalId(str(uuid.uuid4())),
            character=char.entity_id,
            description="Achieved goal",
            target_state=None,
            status=GoalStatus.ACHIEVED,
            priority=5,
            formed_at=datetime.utcnow(),
        )

        prop = create_proposition(ProjectId("proj_01"), EntityId("entity-123"), "is_alive")
        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.KNOWN,
            acquisition_source=AcquisitionSource.DIRECT_OBSERVATION,
            source_ref="event-123",
        )

        from dataclasses import replace
        char = replace(char, goals=[goal1, goal2], knowledge={prop.proposition_id: ck})

        data = serialize_character(char)
        char2 = deserialize_character(data)

        # DERIVED fields recomputed
        assert char2.active_goals == [goal1]
        assert char2.knowledge_count == 1

    def test_cache_fields_reset_after_deserialization(self):
        """CACHE fields reset to None after deserialization."""
        char = create_character(ProjectId("proj_01"), "张三")
        prop = create_proposition(ProjectId("proj_01"), EntityId("entity-123"), "is_alive")

        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.BELIEVED,
            acquisition_source=AcquisitionSource.INFERENCE,
            basis_ref=(PropositionId(str(uuid.uuid4())),),
            aligns_with_fact=False,  # CACHE field
        )

        from dataclasses import replace
        char = replace(char, knowledge={prop.proposition_id: ck})

        data = serialize_character(char)
        char2 = deserialize_character(data)

        # CACHE field reset to None
        ck2 = char2.knowledge[prop.proposition_id]
        assert ck2.aligns_with_fact is None


class TestSchemaValidation:
    """Serialized Character must validate against character.schema.json."""

    def test_minimal_character_validates(self):
        """Minimal Character validates against schema."""
        char = create_character(ProjectId("proj_01"), "张三")

        data = serialize_character(char)

        # Should not raise
        validate_against_schema(data)

    def test_character_with_all_fields_validates(self):
        """Character with all optional fields validates against schema."""
        char = create_character(ProjectId("proj_01"), "张三")

        prop = create_proposition(ProjectId("proj_01"), EntityId("entity-123"), "is_alive")
        ck = CharacterKnowledge(
            knower=char.entity_id,
            proposition=prop,
            knowledge_level=KnowledgeLevel.KNOWN,
            acquisition_source=AcquisitionSource.DIRECT_OBSERVATION,
            source_ref="event-123",
            basis_ref=(PropositionId(str(uuid.uuid4())),),
            acquired_at=datetime.utcnow(),
            story_time_ref="chapter-1",
            confidence=0.95,
        )

        goal = Goal(
            goal_id=GoalId(str(uuid.uuid4())),
            character=char.entity_id,
            description="Find artifact",
            target_state=MappingProxyType({"has_artifact": "true"}),
            status=GoalStatus.ACTIVE,
            priority=10,
            formed_at=datetime.utcnow(),
        )

        from dataclasses import replace
        char = replace(
            char,
            knowledge={prop.proposition_id: ck},
            goals=[goal],
            provenance={"source": "test"},
        )

        data = serialize_character(char)

        # Should not raise
        validate_against_schema(data)


class TestEntityTypeValidation:
    """Entity type validation through deserialization and registry."""

    def test_deserialized_character_with_wrong_entity_type_rejects(self):
        """Deserialized Character with entity_type != CHARACTER rejects via registry."""
        from src.anovel.domain.identity import EntityRegistry, create_identity
        from src.anovel.domain.character import validate_project_isolation

        # Create LOCATION identity (not CHARACTER)
        registry = EntityRegistry()
        location_identity = create_identity(
            ProjectId("proj_01"),
            "某地",
            entity_type="LOCATION"
        )
        registry.add_entity(location_identity)

        # Create Character with valid entity_id, serialize, deserialize
        char = create_character(ProjectId("proj_01"), "张三")
        data = serialize_character(char)

        # Swap entity_id to LOCATION before deserialization
        data["entity_id"] = location_identity.entity_id

        char2 = deserialize_character(data)

        # Validation through registry must reject
        with pytest.raises(ValueError, match="entity_type='CHARACTER'"):
            validate_project_isolation(char2, registry)

    def test_deserialized_character_with_character_type_passes(self):
        """Deserialized Character with entity_type=CHARACTER passes validation."""
        from src.anovel.domain.identity import EntityRegistry, create_identity
        from src.anovel.domain.character import validate_project_isolation

        registry = EntityRegistry()
        identity = create_identity(
            ProjectId("proj_01"),
            "张三",
            entity_type="CHARACTER"
        )
        registry.add_entity(identity)

        char = create_character(ProjectId("proj_01"), "张三")
        data = serialize_character(char)
        data["entity_id"] = identity.entity_id

        char2 = deserialize_character(data)

        # Should not raise
        validate_project_isolation(char2, registry)
