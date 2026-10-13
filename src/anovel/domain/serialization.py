"""
Character serialization and deserialization.

Implements BASE field serialization per ADR-002:
- Serializes all BASE fields to JSON-compatible dict
- Excludes DERIVED fields (active_goals, knowledge_count)
- Excludes CACHE fields (CharacterKnowledge.aligns_with_fact)
- Validates against character.schema.json
- Preserves exact BASE state in round-trip

Contract: ADR-002 + Frozen V2-061 §Serialization
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .character import (
    ActionStatus,
    Character,
    CharacterLifecycle,
    Goal,
    GoalId,
    GoalStatus,
    Intent,
    IntentId,
    PlannedAction,
    PlannedActionId,
)
from .identity import EntityId, ProjectId
from .knowledge import (
    AcquisitionSource,
    CharacterKnowledge,
    KnowledgeLevel,
    Proposition,
    PropositionId,
)


def serialize_character(character: Character) -> dict[str, Any]:
    """
    Serialize Character to JSON-compatible dict (BASE fields only).

    Excludes DERIVED fields:
    - active_goals (computed from goals)
    - knowledge_count (computed from knowledge)

    Excludes CACHE fields:
    - CharacterKnowledge.aligns_with_fact

    Args:
        character: Character to serialize

    Returns:
        JSON-compatible dict with BASE fields only

    Contract: ADR-002 BASE serialization
    """
    return {
        "entity_id": character.entity_id,
        "project_id": character.project_id,
        "lifecycle": character.lifecycle.value,
        "knowledge": {
            prop_id: _serialize_character_knowledge(ck)
            for prop_id, ck in character.knowledge.items()
        },
        "goals": [_serialize_goal(g) for g in character.goals],
        "intents": [_serialize_intent(i) for i in character.intents],
        "planned_actions": [
            _serialize_planned_action(pa) for pa in character.planned_actions
        ],
        "created_at": character.created_at.isoformat(),
        "updated_at": character.updated_at.isoformat(),
        "authority": character.authority,
        "provenance": character.provenance,
    }


def _serialize_character_knowledge(ck: CharacterKnowledge) -> dict[str, Any]:
    """Serialize CharacterKnowledge BASE fields (excludes aligns_with_fact CACHE)."""
    result: dict[str, Any] = {
        "knower": ck.knower,
        "proposition": _serialize_proposition(ck.proposition),
        "knowledge_level": ck.knowledge_level.value,
        "acquisition_source": ck.acquisition_source.value,
    }

    if ck.source_ref is not None:
        result["source_ref"] = ck.source_ref
    if ck.source_character is not None:
        result["source_character"] = ck.source_character
    if ck.basis_ref is not None:
        result["basis_ref"] = list(ck.basis_ref)
    if ck.acquired_at is not None:
        result["acquired_at"] = ck.acquired_at.isoformat()
    if ck.story_time_ref is not None:
        result["story_time_ref"] = ck.story_time_ref
    if ck.confidence is not None:
        result["confidence"] = ck.confidence

    # aligns_with_fact is CACHE - NOT serialized

    return result


def _serialize_proposition(prop: Proposition) -> dict[str, Any]:
    """Serialize Proposition BASE fields with recursive context thaw."""
    result: dict[str, Any] = {
        "proposition_id": prop.proposition_id,
        "project_id": prop.project_id,
        "subject": prop.subject,
        "predicate": prop.predicate,
    }

    if prop.object is not None:
        result["object"] = prop.object
    if prop.context is not None:
        result["context"] = _thaw_context(prop.context)

    return result


def _thaw_context(ctx: Any) -> Any:
    """
    Recursively thaw frozen context to JSON-compatible structures.

    Converts:
    - MappingProxyType → dict (recursively)
    - tuple → list (recursively)
    - Nested structures recursively converted

    Args:
        ctx: Frozen context value

    Returns:
        JSON-compatible structure

    Contract: Proposition.context JSON serialization compatibility
    """
    from types import MappingProxyType

    if isinstance(ctx, MappingProxyType):
        # Recursively thaw mapping
        return {k: _thaw_context(v) for k, v in ctx.items()}
    elif isinstance(ctx, dict):
        # Already dict, thaw values
        return {k: _thaw_context(v) for k, v in ctx.items()}
    elif isinstance(ctx, tuple):
        # Recursively thaw tuple to list
        return [_thaw_context(item) for item in ctx]
    elif isinstance(ctx, list):
        # Already list, thaw elements
        return [_thaw_context(item) for item in ctx]
    else:
        # Primitive or already JSON-compatible
        return ctx


def _serialize_goal(goal: Goal) -> dict[str, Any]:
    """Serialize Goal BASE fields."""
    result: dict[str, Any] = {
        "goal_id": goal.goal_id,
        "character": goal.character,
        "description": goal.description,
        "status": goal.status.value,
    }

    if goal.target_state is not None:
        result["target_state"] = dict(goal.target_state)
    if goal.priority is not None:
        result["priority"] = goal.priority
    if goal.formed_at is not None:
        result["formed_at"] = goal.formed_at.isoformat()
    if goal.resolved_at is not None:
        result["resolved_at"] = goal.resolved_at.isoformat()

    return result


def _serialize_intent(intent: Intent) -> dict[str, Any]:
    """Serialize Intent BASE fields."""
    result: dict[str, Any] = {
        "intent_id": intent.intent_id,
        "character": intent.character,
        "description": intent.description,
    }

    if intent.goal_ref is not None:
        result["goal_ref"] = intent.goal_ref
    if intent.formed_at is not None:
        result["formed_at"] = intent.formed_at.isoformat()
    if intent.abandoned_at is not None:
        result["abandoned_at"] = intent.abandoned_at.isoformat()

    return result


def _serialize_planned_action(pa: PlannedAction) -> dict[str, Any]:
    """Serialize PlannedAction BASE fields."""
    result: dict[str, Any] = {
        "action_id": pa.action_id,
        "character": pa.character,
        "action_description": pa.action_description,
        "status": pa.status.value,
        "created_at": pa.created_at.isoformat(),
    }

    if pa.intent_ref is not None:
        result["intent_ref"] = pa.intent_ref
    if pa.planned_for is not None:
        result["planned_for"] = pa.planned_for
    if pa.occurred_event_ref is not None:
        result["occurred_event_ref"] = pa.occurred_event_ref
    if pa.cancelled_at is not None:
        result["cancelled_at"] = pa.cancelled_at.isoformat()

    return result


def deserialize_character(data: dict[str, Any]) -> Character:
    """
    Deserialize Character from JSON-compatible dict.

    DERIVED fields (active_goals, knowledge_count) are recomputed from BASE.
    CACHE fields (aligns_with_fact) reset to None after deserialization.

    Args:
        data: JSON-compatible dict with BASE fields

    Returns:
        Character with DERIVED fields recomputed

    Raises:
        ValueError: If data invalid or missing required fields
        ValueError: If knowledge dict key != embedded proposition.proposition_id

    Contract: ADR-002 BASE deserialization + DERIVED recomputation + knowledge key invariant
    """
    # Deserialize knowledge with key validation
    knowledge = {}
    for prop_id, ck_data in data["knowledge"].items():
        ck = _deserialize_character_knowledge(ck_data)
        # Validate knowledge key invariant
        if prop_id != ck.proposition.proposition_id:
            raise ValueError(
                f"knowledge dict key '{prop_id}' must match embedded "
                f"proposition.proposition_id '{ck.proposition.proposition_id}'. "
                f"Knowledge key invariant violation."
            )
        knowledge[PropositionId(prop_id)] = ck

    char = Character(
        entity_id=EntityId(data["entity_id"]),
        project_id=ProjectId(data["project_id"]),
        lifecycle=CharacterLifecycle(data["lifecycle"]),
        knowledge=knowledge,
        goals=[_deserialize_goal(g) for g in data["goals"]],
        intents=[_deserialize_intent(i) for i in data["intents"]],
        planned_actions=[
            _deserialize_planned_action(pa) for pa in data["planned_actions"]
        ],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        authority=data["authority"],
        provenance=data.get("provenance", {}),
    )

    return char


def _deserialize_character_knowledge(data: dict[str, Any]) -> CharacterKnowledge:
    """Deserialize CharacterKnowledge BASE fields (aligns_with_fact reset to None)."""
    return CharacterKnowledge(
        knower=EntityId(data["knower"]),
        proposition=_deserialize_proposition(data["proposition"]),
        knowledge_level=KnowledgeLevel(data["knowledge_level"]),
        acquisition_source=AcquisitionSource(data["acquisition_source"]),
        source_ref=data.get("source_ref"),
        source_character=EntityId(data["source_character"])
        if "source_character" in data
        else None,
        basis_ref=list(PropositionId(p) for p in data["basis_ref"])
        if "basis_ref" in data
        else None,
        acquired_at=datetime.fromisoformat(data["acquired_at"])
        if "acquired_at" in data
        else None,
        story_time_ref=data.get("story_time_ref"),
        confidence=data.get("confidence"),
        aligns_with_fact=None,  # CACHE field reset to None
    )


def _deserialize_proposition(data: dict[str, Any]) -> Proposition:
    """Deserialize Proposition BASE fields."""
    from .knowledge import freeze_context

    context = data.get("context")
    return Proposition(
        proposition_id=PropositionId(data["proposition_id"]),
        project_id=ProjectId(data["project_id"]),
        subject=data["subject"],
        predicate=data["predicate"],
        object=data.get("object"),
        context=freeze_context(context) if context is not None else None,
    )


def _deserialize_goal(data: dict[str, Any]) -> Goal:
    """Deserialize Goal BASE fields."""
    from types import MappingProxyType

    target_state = data.get("target_state")
    return Goal(
        goal_id=GoalId(data["goal_id"]),
        character=EntityId(data["character"]),
        description=data["description"],
        target_state=MappingProxyType(target_state)
        if target_state is not None
        else None,
        status=GoalStatus(data["status"]),
        priority=data.get("priority"),
        formed_at=datetime.fromisoformat(data["formed_at"])
        if "formed_at" in data
        else None,
        resolved_at=datetime.fromisoformat(data["resolved_at"])
        if "resolved_at" in data
        else None,
    )


def _deserialize_intent(data: dict[str, Any]) -> Intent:
    """Deserialize Intent BASE fields."""
    return Intent(
        intent_id=IntentId(data["intent_id"]),
        character=EntityId(data["character"]),
        goal_ref=GoalId(data["goal_ref"]) if "goal_ref" in data else None,
        description=data["description"],
        formed_at=datetime.fromisoformat(data["formed_at"])
        if "formed_at" in data
        else None,
        abandoned_at=datetime.fromisoformat(data["abandoned_at"])
        if "abandoned_at" in data
        else None,
    )


def _deserialize_planned_action(data: dict[str, Any]) -> PlannedAction:
    """Deserialize PlannedAction BASE fields."""
    return PlannedAction(
        action_id=PlannedActionId(data["action_id"]),
        character=EntityId(data["character"]),
        action_description=data["action_description"],
        intent_ref=IntentId(data["intent_ref"]) if "intent_ref" in data else None,
        planned_for=data.get("planned_for"),
        status=ActionStatus(data["status"]),
        occurred_event_ref=data.get("occurred_event_ref"),
        created_at=datetime.fromisoformat(data["created_at"]),
        cancelled_at=datetime.fromisoformat(data["cancelled_at"])
        if "cancelled_at" in data
        else None,
    )


def validate_against_schema(data: dict[str, Any]) -> None:
    """
    Validate serialized Character against character.schema.json.

    Args:
        data: Serialized Character dict

    Raises:
        ValueError: If validation fails

    Contract: character.schema.json compliance
    """
    import jsonschema

    # Path from src/anovel/domain/ to specs/schemas/
    schema_path = (
        Path(__file__).parent.parent.parent.parent
        / "specs"
        / "schemas"
        / "character.schema.json"
    )
    with open(schema_path) as f:
        schema = json.load(f)

    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Schema validation failed: {e.message}") from e
