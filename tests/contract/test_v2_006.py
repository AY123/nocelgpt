"""V2-006 real in-memory character, knowledge and planned-action contracts."""

from __future__ import annotations

import copy
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import jsonschema
import pytest

from anovel.domain.character import (
    Character,
    CharacterIdentity,
    Lifecycle,
    Relationship,
)
from anovel.domain.identity import Entity, EntityId, EntityRegistry
from anovel.domain.knowledge import (
    Belief,
    Goal,
    GoalStatus,
    Intent,
    IntentStatus,
    KnowledgeLevel,
    KnowledgeState,
    Observation,
    Proposition,
    WorldFact,
)

ROOT = Path(__file__).resolve().parents[2]


def eid(name: str, project: str = "book_a") -> EntityId:
    return EntityId(project, name)


def schema(name: str) -> dict:
    return json.loads((ROOT / "specs/schemas" / name).read_text())


def strict_json(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def relationship_schema() -> dict:
    whole = schema("character.schema.json")
    return {"$ref": "#/$defs/relationship", "$defs": whole["$defs"]}


@pytest.fixture
def story():
    lin = Character(eid("lin"), "林岚", {"小林"})
    zhou = Character(eid("zhou"), "周宁")
    outsider = Character(eid("outsider"), "未到场者")
    state = KnowledgeState("book_a", (lin, zhou, outsider))
    east = Proposition(eid("key"), "located_at", "east_warehouse")
    west = Proposition(eid("key"), "located_at", "west_warehouse")
    fact = WorldFact(eid("key_location"), east, "chapter-1:warehouse-inventory")
    belief = Belief(
        eid("zhou_rumour"), zhou.id, west, "rumour:unverified", confidence=0.0
    )
    state.add_fact(fact)
    state.add_belief(belief)
    return state, lin, zhou, outsider, fact, belief


def test_character_schema_is_valid_and_identity_contract_matches_entity():
    doc = schema("character.schema.json")
    jsonschema.Draft202012Validator.check_schema(doc)
    entity_schema = schema("entity.schema.json")
    assert doc["$defs"]["id"] == entity_schema["properties"]["id"]
    for field in ("display_name", "aliases"):
        assert doc["properties"][field] == entity_schema["properties"][field]
    assert doc["additionalProperties"] is False


def test_character_all_nondefault_derived_fields_roundtrip():
    """AT-V2-006-01: identity/species and every declared derived field survive."""
    original = Character(
        eid("lin"),
        "林岚",
        {"小林", "库房学徒"},
        identity=CharacterIdentity(species="human", gender="woman", origin="south"),
        lifecycle=Lifecycle.INACTIVE,
        description="隐瞒自己的出身",
    )
    payload = strict_json(original.to_dict())
    jsonschema.validate(payload, schema("character.schema.json"))
    restored = Character.from_dict(payload)
    assert restored == original
    assert restored.to_dict() == original.to_dict()
    assert restored.identity.species == "human"
    assert restored.identity.gender == "woman"
    assert restored.identity.origin == "south"
    assert restored.lifecycle is Lifecycle.INACTIVE
    assert restored.description == "隐瞒自己的出身"


def test_registry_rename_preserves_character_subtype_and_nondefault_fields():
    char = Character(
        eid("lin"),
        "林岚",
        {"小林"},
        identity=CharacterIdentity("human", "woman", "south"),
        lifecycle=Lifecycle.DEAD,
        description="旧名仍保留在档案中",
    )
    registry = EntityRegistry()
    registry.register(char)
    registry.rename(char.id, "林晚", keep_old_as_alias=True)
    changed = registry.get(char.id)
    assert isinstance(changed, Character)
    assert changed.id == char.id
    assert changed.identity == char.identity
    assert changed.lifecycle is Lifecycle.DEAD
    assert changed.description == char.description
    assert {"林岚", "小林"} <= changed.aliases
    assert changed.display_name == "林晚"
    jsonschema.validate(changed.to_dict(), schema("character.schema.json"))
    assert Character.from_dict(changed.to_dict()) == changed


@pytest.mark.parametrize("status", list(Lifecycle))
def test_legal_nonactive_lifecycles_are_not_blanket_rejected(status):
    char = Character(eid("lin"), "林岚", lifecycle=status)
    jsonschema.validate(char.to_dict(), schema("character.schema.json"))
    assert Character.from_dict(char.to_dict()).lifecycle is status


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("entity_type", "LOCATION"),
        ("schema_version", "999"),
        ("lifecycle", "受伤"),
        ("lifecycle", "DESTROYED"),
        ("lifecycle", "DISBANDED"),
        ("lifecycle", None),
        ("description", 1),
        ("cultivation_level", 3),
        ("identity", {"sepcies": "human"}),
        ("identity", {"species": None}),
        ("identity", []),
        ("aliases", ["same", "same"]),
    ],
)
def test_single_invalid_character_field_rejected_by_code_and_schema(field, value):
    """AT-V2-006-02: one defect at a time, with a passing control."""
    good = Character(eid("lin"), "林岚").to_dict()
    assert Character.from_dict(good).id == eid("lin")
    jsonschema.validate(good, schema("character.schema.json"))
    bad = copy.deepcopy(good)
    bad[field] = value
    with pytest.raises(ValueError):
        Character.from_dict(bad)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema("character.schema.json"))


@pytest.mark.parametrize("field", ["schema_version", "entity_type", "lifecycle", "id"])
def test_character_required_discriminator_and_version_not_inferred(field):
    bad = Character(eid("lin"), "林岚").to_dict()
    del bad[field]
    with pytest.raises(ValueError):
        Character.from_dict(bad)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema("character.schema.json"))


def test_generic_entity_parser_does_not_silently_downcast_character():
    with pytest.raises(ValueError):
        Entity.from_dict(Character(eid("lin"), "林岚").to_dict())


def test_character_and_nested_identity_are_immutable_and_aliases_copied():
    aliases = {"小林"}
    char = Character(eid("lin"), "林岚", aliases)
    aliases.add("后改")
    assert "后改" not in char.aliases
    with pytest.raises(FrozenInstanceError):
        char.description = "改写"
    with pytest.raises(FrozenInstanceError):
        char.identity.species = "changed"


def test_relationship_has_identity_and_preserves_negative_trust():
    relationship = Relationship(
        eid("lin_zhou"), eid("lin"), eid("zhou"), {"colleague", "rival"}, trust=-0.75
    )
    payload = strict_json(relationship.to_dict())
    jsonschema.validate(payload, relationship_schema())
    restored = Relationship.from_dict(payload)
    assert restored == relationship
    assert restored.trust == -0.75
    assert restored.party_a == eid("lin")
    assert restored.party_b == eid("zhou")
    assert restored.relationship_types == frozenset({"colleague", "rival"})


@pytest.mark.parametrize("field", ["id", "party_a", "party_b"])
def test_relationship_rejects_each_cross_project_identity(field):
    payload = Relationship(eid("edge"), eid("lin"), eid("zhou"), {"friend"}).to_dict()
    payload[field] = eid(payload[field]["local_id"], "book_b").to_dict()
    with pytest.raises(ValueError):
        Relationship.from_dict(payload)


@pytest.mark.parametrize("trust", [True, -1.1, 1.1, float("nan"), float("inf"), "0.5"])
def test_relationship_constructor_rejects_invalid_numeric_trust(trust):
    with pytest.raises(ValueError):
        Relationship(eid("edge"), eid("lin"), eid("zhou"), {"friend"}, trust=trust)


def test_world_fact_and_false_belief_coexist_without_magical_knowledge(story):
    """AT-V2-006-03: author truth never becomes a character's automatic knowledge."""
    state, lin, zhou, outsider, fact, belief = story
    assert state.query(zhou.id, belief.proposition) is KnowledgeLevel.BELIEVED
    assert state.query(zhou.id, fact.proposition) is KnowledgeLevel.UNKNOWN
    assert state.query(lin.id, fact.proposition) is KnowledgeLevel.UNKNOWN
    assert state.query(outsider.id, fact.proposition) is KnowledgeLevel.UNKNOWN
    assert state.facts == (fact,)
    assert state.beliefs == (belief,)
    assert state.beliefs[0].confidence == 0.0
    with pytest.raises(ValueError):
        state.require_known(zhou.id, fact.id)


def test_correct_observation_grants_only_actual_witnesses(story):
    state, lin, zhou, outsider, fact, belief = story
    source = Observation(
        eid("east_observed"), fact.id, frozenset({lin.id}), "chapter-2:lin-saw"
    )
    state.add_observation(source)
    assert state.query(lin.id, fact.proposition) is KnowledgeLevel.UNKNOWN
    state.learn(lin.id, fact.id, source.id)
    assert state.query(lin.id, fact.proposition) is KnowledgeLevel.KNOWN
    assert state.require_known(lin.id, fact.id) == fact
    assert state.query(zhou.id, fact.proposition) is KnowledgeLevel.UNKNOWN
    assert state.query(outsider.id, fact.proposition) is KnowledgeLevel.UNKNOWN
    assert state.beliefs == (belief,)
    assert state.facts == (fact,)
    before = state.to_dict()
    state.learn(lin.id, fact.id, source.id)
    assert state.to_dict() == before  # same explicit acquisition is idempotent


@pytest.mark.parametrize(
    "reason",
    [
        "unknown_source",
        "wrong_witness",
        "wrong_fact",
        "foreign_source",
        "world_fact_is_not_source",
        "empty_witnesses",
    ],
)
def test_unproven_acquisition_fails_without_partial_state_change(story, reason):
    state, lin, zhou, outsider, fact, belief = story
    other = WorldFact(
        eid("other_fact"), Proposition(eid("door"), "locked", True), "chapter-1:door"
    )
    state.add_fact(other)
    witnesses = (
        frozenset()
        if reason == "empty_witnesses"
        else frozenset({zhou.id})
        if reason == "wrong_witness"
        else frozenset({lin.id})
    )
    source = Observation(
        eid("observation"),
        other.id if reason == "wrong_fact" else fact.id,
        witnesses,
        "chapter-2:observation",
    )
    state.add_observation(source)
    source_id = (
        eid("absent")
        if reason == "unknown_source"
        else eid("observation", "book_b")
        if reason == "foreign_source"
        else fact.id
        if reason == "world_fact_is_not_source"
        else source.id
    )
    before = state.to_dict()
    with pytest.raises(ValueError):
        state.learn(lin.id, fact.id, source_id)
    assert state.to_dict() == before
    assert state.query(lin.id, fact.proposition) is KnowledgeLevel.UNKNOWN


def test_source_cannot_self_declare_trust_or_author_plan_as_observation(story):
    state, lin, zhou, outsider, fact, belief = story
    source = Observation(
        eid("source"), fact.id, frozenset({lin.id}), "scene:1"
    ).to_dict()
    for patch in (
        {"reliable": True},
        {"kind": "AUTHOR_PLAN"},
        {"kind": "READER_REVEAL"},
        {"kind": "RUMOUR"},
    ):
        bad = source | patch
        with pytest.raises(ValueError):
            Observation.from_dict(bad)
    with pytest.raises(ValueError):
        state.learn(lin.id, fact.id, eid("zhou_rumour"))


def test_known_boolean_contradiction_is_explicit_but_unseen_world_is_not(story):
    state, lin, zhou, outsider, _fact, _belief = story
    objective = Proposition(eid("ally"), "betrayed", False)
    mistaken = Proposition(eid("ally"), "betrayed", True)
    fact = WorldFact(eid("betrayal_fact"), objective, "chapter-3:actual-event")
    belief = Belief(eid("lin_suspicion"), lin.id, mistaken, "rumour")
    state.add_fact(fact)
    state.add_belief(belief)
    assert state.query(lin.id, mistaken) is KnowledgeLevel.BELIEVED
    assert state.query(lin.id, objective) is KnowledgeLevel.UNKNOWN
    obs = Observation(
        eid("betrayal_observed"), fact.id, frozenset({lin.id}), "chapter-3:witness"
    )
    state.add_observation(obs)
    state.learn(lin.id, fact.id, obs.id)
    assert state.query(lin.id, objective) is KnowledgeLevel.CONTRADICTORY
    assert state.query(lin.id, mistaken) is KnowledgeLevel.CONTRADICTORY
    assert state.query(zhou.id, objective) is KnowledgeLevel.UNKNOWN
    with pytest.raises(ValueError):
        state.require_known(lin.id, fact.id)


def test_boolean_value_is_not_a_numeric_fact(story):
    state, lin, zhou, outsider, _fact, _belief = story
    numeric = Proposition(eid("counter"), "value", 0)
    fact = WorldFact(eid("numeric"), numeric, "record:counter")
    state.add_fact(fact)
    obs = Observation(
        eid("numeric_observed"), fact.id, frozenset({lin.id}), "record:seen"
    )
    state.add_observation(obs)
    state.learn(lin.id, fact.id, obs.id)
    assert (
        state.query(lin.id, Proposition(eid("counter"), "value", 0.0))
        is KnowledgeLevel.KNOWN
    )
    assert (
        state.query(lin.id, Proposition(eid("counter"), "value", False))
        is KnowledgeLevel.UNKNOWN
    )


def test_goal_and_mistaken_plan_do_not_change_actual_world_or_knowledge(story):
    """AT-V2-006-04: a character may choose wrongly; a plan isn't an occurrence."""
    state, lin, zhou, outsider, fact, belief = story
    original_facts = state.facts
    original_knowledge = state.knowledge
    goal = Goal(
        eid("rescue"), zhou.id, "救出被困者", status=GoalStatus.ACTIVE, priority=-2
    )
    intent = Intent(
        eid("fetch_key"),
        zhou.id,
        goal.id,
        "去西库取钥匙",
        (belief.id,),
        expected_cost="暴露行踪",
    )
    state.add_goal(goal)
    state.add_intent(intent)
    assert state.goals == (goal,)
    assert state.intents == (intent,)
    assert intent.status is IntentStatus.PLANNED
    assert state.goals[0].status is GoalStatus.ACTIVE
    assert state.facts == original_facts
    assert state.knowledge == original_knowledge
    assert state.facts[0].proposition.value == "east_warehouse"
    assert state.query(zhou.id, fact.proposition) is KnowledgeLevel.UNKNOWN
    assert state.query(zhou.id, belief.proposition) is KnowledgeLevel.BELIEVED
    before = state.to_dict()
    with pytest.raises(ValueError):
        state.add_fact(intent)
    with pytest.raises(ValueError):
        WorldFact.from_dict(intent.to_dict())
    assert state.to_dict() == before


def test_intent_cannot_borrow_another_characters_belief(story):
    state, lin, zhou, outsider, fact, belief = story
    goal = Goal(eid("lin_goal"), lin.id, "找到钥匙")
    state.add_goal(goal)
    before = state.to_dict()
    with pytest.raises(ValueError):
        state.add_intent(
            Intent(eid("wrong_basis"), lin.id, goal.id, "去西库", (belief.id,))
        )
    assert state.to_dict() == before


def test_intent_cannot_use_a_world_fact_that_its_owner_has_not_learned(story):
    state, lin, zhou, outsider, fact, belief = story
    goal = Goal(eid("lin_goal"), lin.id, "找到钥匙")
    state.add_goal(goal)
    before = state.to_dict()
    with pytest.raises(ValueError):
        state.add_intent(
            Intent(eid("author_leak"), lin.id, goal.id, "去东库", (fact.id,))
        )
    assert state.to_dict() == before
    obs = Observation(
        eid("seen_for_plan"), fact.id, frozenset({lin.id}), "scene:lin-sees"
    )
    state.add_observation(obs)
    state.learn(lin.id, fact.id, obs.id)
    valid = Intent(
        eid("informed"), lin.id, goal.id, "去东库", (fact.id,), expected_cost="耗时"
    )
    state.add_intent(valid)
    assert state.intents == (valid,)


def populated_snapshot(story):
    state, lin, zhou, outsider, fact, belief = story
    source = Observation(eid("seen"), fact.id, frozenset({lin.id}), "scene:lin")
    state.add_observation(source)
    state.learn(lin.id, fact.id, source.id)
    suspected = Belief(
        eid("suspicion"),
        lin.id,
        Proposition(eid("door"), "locked", True),
        "guess:lin",
        confidence=0.25,
        level=KnowledgeLevel.SUSPECTED,
    )
    state.add_belief(suspected)
    goal = Goal(eid("goal"), zhou.id, "救人", status=GoalStatus.BLOCKED, priority=-1)
    state.add_goal(goal)
    state.add_intent(
        Intent(
            eid("intent"),
            zhou.id,
            goal.id,
            "去西库",
            (belief.id,),
            expected_cost="行踪暴露",
            status=IntentStatus.CANCELLED,
        )
    )
    return state


def test_whole_projection_preserves_nondefault_fields_and_replays_acquisitions(story):
    original = populated_snapshot(story)
    payload = strict_json(original.to_dict())
    doc = schema("knowledge.schema.json")
    jsonschema.Draft202012Validator.check_schema(doc)
    jsonschema.validate(payload, doc)
    restored = KnowledgeState.from_dict(payload)
    assert restored.to_dict() == original.to_dict()
    assert restored.beliefs == original.beliefs
    assert restored.goals == original.goals
    assert restored.intents == original.intents
    assert (
        restored.query(eid("lin"), original.facts[0].proposition)
        is KnowledgeLevel.KNOWN
    )
    assert (
        restored.query(eid("outsider"), original.facts[0].proposition)
        is KnowledgeLevel.UNKNOWN
    )


def test_snapshot_exports_are_detached_and_domain_values_immutable(story):
    state = populated_snapshot(story)
    before = state.to_dict()
    exported = state.to_dict()
    exported["facts"].clear()
    exported["characters"][0]["display_name"] = "污染名字"
    exported["knowledge"].clear()
    assert state.to_dict() == before
    with pytest.raises(FrozenInstanceError):
        state.facts[0].evidence_ref = "changed"


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_source",
        "wrong_holder",
        "duplicate_acquisition",
        "foreign_subject",
        "unknown_fact_kind",
        "extra_root",
        "unknown_version",
        "duplicate_fact",
        "global_id_collision",
    ],
)
def test_forged_projection_is_revalidated_not_trusted(story, mutation):
    state = populated_snapshot(story)
    bad = copy.deepcopy(state.to_dict())
    if mutation == "unknown_source":
        bad["knowledge"][0]["source_id"] = eid("absent").to_dict()
    elif mutation == "wrong_holder":
        bad["knowledge"][0]["holder"] = eid("outsider").to_dict()
    elif mutation == "duplicate_acquisition":
        bad["knowledge"].append(copy.deepcopy(bad["knowledge"][0]))
    elif mutation == "foreign_subject":
        bad["facts"][0]["proposition"]["subject"]["project"] = "book_b"
    elif mutation == "unknown_fact_kind":
        bad["facts"][0]["kind"] = "AUTHOR_PLAN"
    elif mutation == "extra_root":
        bad["force_known"] = True
    elif mutation == "unknown_version":
        bad["schema_version"] = "999"
    elif mutation == "duplicate_fact":
        bad["facts"].append(copy.deepcopy(bad["facts"][0]))
    elif mutation == "global_id_collision":
        bad["goals"][0]["id"] = copy.deepcopy(bad["beliefs"][0]["id"])
    with pytest.raises(ValueError):
        KnowledgeState.from_dict(bad)


@pytest.mark.parametrize(
    "confidence", [True, -0.1, 1.1, float("nan"), float("inf"), "0.7"]
)
def test_invalid_belief_confidence_rejected(confidence):
    with pytest.raises(ValueError):
        Belief(
            eid("belief"),
            eid("lin"),
            Proposition(eid("key"), "located_at", "east"),
            "rumour",
            confidence=confidence,
        )


@pytest.mark.parametrize("value", [None, [], {}, float("nan"), float("inf")])
def test_non_json_proposition_values_rejected(value):
    with pytest.raises(ValueError):
        Proposition(eid("key"), "located_at", value)


def test_same_local_ids_in_different_books_never_cross_knowledge_boundary(story):
    state, lin, zhou, outsider, fact, belief = story
    before = state.to_dict()
    with pytest.raises(ValueError):
        state.query(eid("lin", "book_b"), fact.proposition)
    with pytest.raises(ValueError):
        state.add_goal(Goal(eid("goal"), eid("lin", "book_b"), "偷渡项目"))
    with pytest.raises(ValueError):
        state.add_belief(
            Belief(
                eid("foreign_belief"),
                lin.id,
                Proposition(eid("key", "book_b"), "located_at", "east"),
                "wrong-book",
            )
        )
    assert state.to_dict() == before


def test_snapshot_character_contract_cannot_drift_from_standalone_schema():
    character = schema("character.schema.json")
    snapshot = schema("knowledge.schema.json")
    expected = {
        key: value
        for key, value in character.items()
        if key not in {"$schema", "$id", "$defs"}
    }
    assert snapshot["$defs"]["character"] == expected
    for key, value in character["$defs"].items():
        assert snapshot["$defs"][key] == value


@pytest.mark.parametrize(
    ("model", "definition", "required_field"),
    [
        (WorldFact, "fact", "evidence_ref"),
        (Observation, "observation", "witnesses"),
        (Belief, "belief", "source_ref"),
        (Goal, "goal", "description"),
        (Intent, "intent", "based_on"),
    ],
)
@pytest.mark.parametrize("defect", ["wrong_kind", "missing_field", "extra_field"])
def test_each_knowledge_record_has_a_closed_typed_boundary(
    story, model, definition, required_field, defect
):
    state = populated_snapshot(story)
    records = {
        "fact": state.facts,
        "observation": state.observations,
        "belief": state.beliefs,
        "goal": state.goals,
        "intent": state.intents,
    }
    whole = schema("knowledge.schema.json")
    doc = {"$ref": "#/$defs/" + definition, "$defs": whole["$defs"]}
    good = records[definition][0].to_dict()
    assert model.from_dict(good).to_dict() == good
    jsonschema.validate(good, doc)
    bad = copy.deepcopy(good)
    if defect == "wrong_kind":
        bad["kind"] = "AUTHOR_PLAN"
    elif defect == "missing_field":
        del bad[required_field]
    else:
        bad["reliable"] = True
    with pytest.raises(ValueError):
        model.from_dict(bad)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, doc)


@pytest.mark.parametrize("status", list(GoalStatus))
def test_goal_states_roundtrip_without_becoming_world_events(status):
    goal = Goal(eid("goal"), eid("lin"), "救人", status=status, priority=-3)
    whole = schema("knowledge.schema.json")
    jsonschema.validate(
        goal.to_dict(), {"$ref": "#/$defs/goal", "$defs": whole["$defs"]}
    )
    assert Goal.from_dict(strict_json(goal.to_dict())) == goal
    with pytest.raises(ValueError):
        WorldFact.from_dict(goal.to_dict())


@pytest.mark.parametrize("priority", [True, 1.0, 1.5, "1"])
def test_goal_priority_uses_strict_integer_boundary(priority):
    # JSON Schema accepts mathematically integral 1.0; the Python parser is stricter.
    payload = Goal(eid("goal"), eid("lin"), "救人").to_dict()
    payload["priority"] = priority
    with pytest.raises(ValueError):
        Goal.from_dict(payload)
    with pytest.raises(ValueError):
        Goal(eid("goal"), eid("lin"), "救人", priority=priority)


def test_missing_snapshot_collection_is_not_silently_restored_as_empty(story):
    payload = populated_snapshot(story).to_dict()
    for field in payload:
        bad = copy.deepcopy(payload)
        del bad[field]
        with pytest.raises(ValueError):
            KnowledgeState.from_dict(bad)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema("knowledge.schema.json"))


def test_invalid_registered_references_leave_projection_unchanged(story):
    state, lin, zhou, outsider, fact, belief = story
    own_goal = Goal(eid("goal"), zhou.id, "救人")
    state.add_goal(own_goal)
    before = state.to_dict()
    with pytest.raises(ValueError):
        state.add_observation(
            Observation(
                eid("unknown_witness"),
                fact.id,
                frozenset({eid("absent")}),
                "scene:source",
            )
        )
    with pytest.raises(ValueError):
        state.add_intent(
            Intent(eid("borrowed_goal"), lin.id, own_goal.id, "取钥匙", ())
        )
    assert state.to_dict() == before
