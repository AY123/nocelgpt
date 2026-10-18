"""Event occurrence, dual ordering and reader Promise contracts (ADR-003)."""

from __future__ import annotations

import copy
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import jsonschema
import pytest

from anovel.domain.character import Character
from anovel.domain.events import (
    Event,
    NarrativePosition,
    Occurrence,
    StoryTime,
    TemporalRelation,
    TimeKind,
    Timeline,
)
from anovel.domain.identity import EntityId
from anovel.domain.knowledge import (
    Belief,
    Goal,
    Intent,
    KnowledgeLevel,
    KnowledgeState,
    Proposition,
    WorldFact,
)
from anovel.domain.promises import (
    Promise,
    PromiseStatus,
    PromiseWindow,
    WindowKind,
    WindowResult,
)

ROOT = Path(__file__).resolve().parents[2]


def eid(name, project="book_a"):
    return EntityId(project, name)


def pos(chapter=1, order=1):
    return NarrativePosition(chapter, order)


def event(name="opened", *, chapter=2, order=1, time=10, **overrides):
    values = dict(
        id=eid(name),
        event_type="REVELATION",
        narrative_position=pos(chapter, order),
        story_time=StoryTime.exact(time),
        occurrence=Occurrence.OCCURRED,
        evidence_ref=f"text:chapter-{chapter}:event-{order}",
        description="东库钥匙被发现",
        participants={eid("lin"), eid("zhou")},
        location=eid("east_warehouse"),
    )
    values.update(overrides)
    return Event(**values)


def promise(**overrides):
    values = dict(
        id=eid("key_promise"),
        description="读者将在第三章前知道钥匙真正所在",
        opened_at=pos(1, 1),
        window=PromiseWindow.between(pos(2, 1), pos(3, 2)),
        related_entities={eid("lin"), eid("key")},
        evidence_ref="text:chapter-1:promise",
    )
    values.update(overrides)
    return Promise(**values)


def schema(name):
    return json.loads((ROOT / "specs/schemas" / name).read_text())


def event_schema():
    doc = schema("events.schema.json")
    return {"$ref": "#/$defs/event", "$defs": doc["$defs"]}


def json_copy(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def test_dual_order_distinguishes_same_chapter_and_flashback():
    """AT-V2-007-01: reader order and happened-before are independently observable."""
    reveal = event("reveal", chapter=2, order=1, time=20)
    flashback = event("hidden", chapter=2, order=2, time=-5)
    rescue = event("rescue", chapter=3, order=1, time=30)
    timeline = Timeline("book_a", (rescue, flashback, reveal))
    assert timeline.narration_order() == (reveal, flashback, rescue)
    assert timeline.story_order() == (flashback, reveal, rescue)
    assert timeline.story_relation(reveal.id, flashback.id) is TemporalRelation.AFTER
    assert timeline.story_relation(flashback.id, reveal.id) is TemporalRelation.BEFORE
    assert reveal.event_type == flashback.event_type and reveal.id != flashback.id
    assert timeline.get(flashback.id).evidence_ref == "text:chapter-2:event-2"


@pytest.mark.parametrize("occurrence", list(Occurrence))
def test_event_occurrence_is_explicit_and_roundtrips(occurrence):
    """AT-V2-007-03: identity/provenance preserved without guessing occurrence."""
    original = event(occurrence=occurrence, story_time=StoryTime.unknown())
    payload = json_copy(original.to_dict())
    jsonschema.validate(payload, event_schema())
    assert Event.from_dict(payload) == original
    assert payload["occurrence"] == occurrence.value
    timeline = Timeline("book_a", (original,))
    if occurrence is Occurrence.OCCURRED:
        assert timeline.require_occurred(original.id) == original
        with pytest.raises(ValueError):
            timeline.story_order()
    else:
        with pytest.raises(ValueError):
            timeline.require_occurred(original.id)
        assert timeline.story_order() == ()


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "INTENT"),
        ("schema_version", "999"),
        ("occurrence", None),
        ("occurrence", "PLANNED"),
        ("occurrence", True),
        ("evidence_ref", ""),
        ("narrative_position", {"chapter": 1, "order": True}),
        ("participants", [eid("lin").to_dict(), eid("lin").to_dict()]),
        ("location", "east"),
        ("description", 1),
        ("unknown_field", "x"),
    ],
)
def test_event_malformed_json_rejected_by_code_and_schema(field, value):
    payload = event().to_dict()
    payload[field] = value
    with pytest.raises(ValueError):
        Event.from_dict(payload)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, event_schema())


@pytest.mark.parametrize(
    "field",
    [
        "id",
        "kind",
        "schema_version",
        "occurrence",
        "evidence_ref",
        "story_time",
        "narrative_position",
    ],
)
def test_event_required_identity_and_occurrence_are_not_defaulted(field):
    payload = event().to_dict()
    del payload[field]
    with pytest.raises(ValueError):
        Event.from_dict(payload)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, event_schema())


@pytest.mark.parametrize("bad", [0, -1, True, 1.0, "1", None])
def test_narrative_position_rejects_non_positive_or_coerced_integers(bad):
    with pytest.raises(ValueError):
        NarrativePosition(bad, 1)
    with pytest.raises(ValueError):
        NarrativePosition(1, bad)


@pytest.mark.parametrize("bad", [True, 1.0, "1", None])
def test_story_clock_rejects_coercion(bad):
    with pytest.raises(ValueError):
        StoryTime.exact(bad)
    with pytest.raises(ValueError):
        StoryTime.between(-1, bad)


def test_story_time_strict_variants_and_negative_clock():
    assert StoryTime.exact(-10).earliest == -10
    for value in (StoryTime.unknown(), StoryTime.exact(-3), StoryTime.between(-5, 4)):
        assert StoryTime.from_dict(json_copy(value.to_dict())) == value
    for args in (
        (TimeKind.UNKNOWN, 0, 1),
        (TimeKind.EXACT, 1, 2),
        (TimeKind.RANGE, 1, 1),
        (TimeKind.RANGE, 2, 1),
    ):
        with pytest.raises(ValueError):
            StoryTime(*args)
    with pytest.raises(ValueError):
        StoryTime.from_dict(
            {"kind": "UNKNOWN", "earliest": None, "latest": None, "duration": 3}
        )


@pytest.mark.parametrize(
    "left,right,relation",
    [
        (StoryTime.between(-5, -1), StoryTime.exact(0), TemporalRelation.BEFORE),
        (StoryTime.exact(4), StoryTime.between(1, 3), TemporalRelation.AFTER),
        (StoryTime.exact(3), StoryTime.exact(3), TemporalRelation.SAME_TIME),
        (StoryTime.between(1, 3), StoryTime.between(3, 5), TemporalRelation.UNKNOWN),
        (StoryTime.between(1, 5), StoryTime.exact(3), TemporalRelation.UNKNOWN),
        (StoryTime.unknown(), StoryTime.exact(3), TemporalRelation.UNKNOWN),
    ],
)
def test_story_relations_do_not_invent_order_or_duration(left, right, relation):
    a = event("a", order=1, story_time=left)
    b = event("b", order=2, story_time=right)
    timeline = Timeline("book_a", (a, b))
    assert timeline.story_relation(a.id, b.id) is relation
    if relation in (TemporalRelation.SAME_TIME, TemporalRelation.UNKNOWN):
        with pytest.raises(ValueError):
            timeline.story_order()


@pytest.mark.parametrize("occurrence", [Occurrence.NOT_OCCURRED, Occurrence.UNKNOWN])
def test_exact_time_does_not_prove_occurrence_or_relation(occurrence):
    a = event("claim", order=1, time=-100, occurrence=occurrence)
    b = event("actual", order=2)
    timeline = Timeline("book_a", (a, b))
    assert timeline.story_relation(a.id, b.id) is TemporalRelation.UNKNOWN
    assert timeline.story_order() == (b,)


def test_timeline_duplicate_or_foreign_event_rejected_without_partial_change():
    original = event()
    timeline = Timeline("book_a", (original,))
    before = timeline.to_dict()
    for invalid in (
        original,
        event("collision"),
        event("other", id=eid("other", "book_b"), participants=set(), location=None),
    ):
        with pytest.raises(ValueError):
            timeline.add_event(invalid)
        assert timeline.to_dict() == before
    assert timeline.get(eid("missing")) is None
    for query in (eid("missing"), eid("opened", "book_b")):
        with pytest.raises(ValueError):
            timeline.require_occurred(query)
        with pytest.raises(ValueError):
            timeline.story_relation(original.id, query)
    with pytest.raises(ValueError):
        timeline.get(eid("opened", "book_b"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "book_a/a"),
        ("occurrence", "OCCURRED"),
        ("story_time", 2),
        ("narrative_position", (1, 1)),
        ("participants", [eid("lin")]),
        ("participants", {eid("lin", "book_b")}),
        ("location", eid("east", "book_b")),
    ],
)
def test_event_constructor_enforces_types_and_project_boundary(field, value):
    with pytest.raises(ValueError):
        event(**{field: value})


def test_timeline_restore_rechecks_duplicate_scope_and_nested_occurrence():
    original = Timeline("book_a", (event(), event("second", order=2, time=20)))
    payload = json_copy(original.to_dict())
    jsonschema.validate(payload, schema("events.schema.json"))
    assert Timeline.from_dict(payload).to_dict() == original.to_dict()
    bad = copy.deepcopy(payload)
    bad["events"].append(copy.deepcopy(bad["events"][0]))
    with pytest.raises(ValueError):
        Timeline.from_dict(bad)
    bad = copy.deepcopy(payload)
    bad["events"][1]["id"]["project"] = "book_b"
    with pytest.raises(ValueError):
        Timeline.from_dict(bad)
    bad = copy.deepcopy(payload)
    bad["events"][0]["occurrence"] = "INTENT"
    with pytest.raises(ValueError):
        Timeline.from_dict(bad)
    assert Timeline("book_a").story_order() == ()


@pytest.mark.parametrize(
    "chapter,order,result",
    [
        (1, 2, WindowResult.EARLY),
        (2, 1, WindowResult.IN_WINDOW),
        (3, 2, WindowResult.IN_WINDOW),
        (3, 3, WindowResult.LATE),
    ],
)
def test_promise_window_inclusive_and_lifecycle(chapter, order, result):
    """AT-V2-007-02: explicit reader window, late payoff remains valid."""
    original = promise()
    payoff = event(chapter=chapter, order=order, time=-100)
    timeline = Timeline("book_a", (payoff,))
    assert original.window.classify(payoff.narrative_position) is result
    changed = original.pay_off(timeline, payoff.id, "review:payoff")
    assert original.status is PromiseStatus.OPEN
    assert changed.status is PromiseStatus.PAID
    assert changed.resolution_event == payoff
    assert changed.resolution_evidence_ref == "review:payoff"
    assert changed.opened_at == original.opened_at
    assert changed.id == original.id
    assert original.window.classify(pos(99)) is WindowResult.LATE
    assert original.status is PromiseStatus.OPEN  # elapsed window never auto-breaks


def test_unknown_promise_window_is_explicit_and_valid():
    original = promise(window=PromiseWindow.unknown())
    assert original.window.kind is WindowKind.UNKNOWN
    assert original.window.classify(pos(99)) is WindowResult.UNKNOWN
    assert Promise.from_dict(json_copy(original.to_dict())) == original
    with pytest.raises(ValueError):
        PromiseWindow(WindowKind.UNKNOWN, pos(), pos())
    with pytest.raises(ValueError):
        PromiseWindow(WindowKind.KNOWN, None, None)
    with pytest.raises(ValueError):
        PromiseWindow.between(pos(3), pos(2))
    with pytest.raises(ValueError):
        promise(opened_at=pos(2, 2))


@pytest.mark.parametrize("operation", ["pay_off", "break_promise"])
@pytest.mark.parametrize("occurrence", [Occurrence.UNKNOWN, Occurrence.NOT_OCCURRED])
def test_unoccurred_claim_cannot_resolve_promise(operation, occurrence):
    claim = event(occurrence=occurrence)
    original = promise()
    with pytest.raises(ValueError):
        getattr(original, operation)(Timeline("book_a", (claim,)), claim.id, "review:x")
    assert original.status is PromiseStatus.OPEN


@pytest.mark.parametrize("operation", ["pay_off", "break_promise"])
def test_resolution_requires_registered_same_project_event_and_reader_position(
    operation,
):
    original = promise()
    actual = event()
    candidates = [
        (Timeline("book_a"), actual.id),
        (
            Timeline(
                "book_b",
                (
                    event(
                        id=eid("foreign", "book_b"), participants=set(), location=None
                    ),
                ),
            ),
            eid("foreign", "book_b"),
        ),
        (Timeline("book_a", (event(chapter=1, order=1),)), actual.id),
    ]
    for timeline, event_id in candidates:
        target = promise(opened_at=pos(1, 2))
        with pytest.raises(ValueError):
            getattr(target, operation)(timeline, event_id, "review:x")
    with pytest.raises(ValueError):
        getattr(original, operation)(Timeline("book_a", (actual,)), actual.id, "")


@pytest.mark.parametrize("terminal", ["pay_off", "break_promise", "abandon"])
def test_terminal_states_are_immutable_and_cannot_reopen(terminal):
    original = promise()
    actual = event()
    timeline = Timeline("book_a", (actual,))
    changed = (
        original.abandon("review:drop")
        if terminal == "abandon"
        else getattr(original, terminal)(timeline, actual.id, "review:result")
    )
    for method in ("pay_off", "break_promise"):
        with pytest.raises(ValueError):
            getattr(changed, method)(timeline, actual.id, "review:again")
    with pytest.raises(ValueError):
        changed.abandon("review:again")
    with pytest.raises((FrozenInstanceError, AttributeError)):
        changed.status = PromiseStatus.OPEN
    with pytest.raises(TypeError):
        promise(status=PromiseStatus.PAID)


@pytest.mark.parametrize("terminal", ["OPEN", "PAID", "BROKEN", "ABANDONED"])
def test_complete_promise_json_roundtrip_including_terminal_context(terminal):
    original = promise()
    actual = event()
    timeline = Timeline("book_a", (actual,))
    if terminal == "PAID":
        original = original.pay_off(timeline, actual.id, "review:paid")
    elif terminal == "BROKEN":
        original = original.break_promise(timeline, actual.id, "review:broken")
    elif terminal == "ABANDONED":
        original = original.abandon("review:abandoned")
    assert original.status.value == terminal
    payload = json_copy(original.to_dict())
    jsonschema.validate(payload, schema("promises.schema.json"))
    restored = Promise.from_dict(payload, timeline=timeline)
    assert restored == original
    assert restored.to_dict() == original.to_dict()
    if terminal in ("PAID", "BROKEN"):
        with pytest.raises(ValueError):
            Promise.from_dict(payload)
        impostor = replace(actual, description="same ID but different source claim")
        with pytest.raises(ValueError):
            Promise.from_dict(payload, timeline=Timeline("book_a", (impostor,)))
        bad = copy.deepcopy(payload)
        bad["resolution_event"]["occurrence"] = "UNKNOWN"
        with pytest.raises(ValueError):
            Promise.from_dict(bad, timeline=timeline)


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "GOAL"),
        ("schema_version", "2.0"),
        ("status", "PROMISED"),
        ("opened_at", None),
        ("description", ""),
        ("evidence_ref", ""),
        ("related_entities", [eid("lin").to_dict(), eid("lin").to_dict()]),
        ("resolution_evidence_ref", "forged"),
        ("unknown", "x"),
    ],
)
def test_malformed_promise_json_rejected_by_domain_and_schema(field, value):
    payload = promise().to_dict()
    payload[field] = value
    with pytest.raises(ValueError):
        Promise.from_dict(payload)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema("promises.schema.json"))


def test_promise_restore_cannot_bypass_resolution_and_window_rules():
    actual = event()
    timeline = Timeline("book_a", (actual,))
    paid = promise().pay_off(timeline, actual.id, "review:x").to_dict()
    for field in ("resolution_event", "resolution_evidence_ref"):
        bad = copy.deepcopy(paid)
        bad[field] = None
        with pytest.raises(ValueError):
            Promise.from_dict(bad, timeline=timeline)
    bad = promise().to_dict()
    bad["window"]["start"] = pos(9).to_dict()
    with pytest.raises(ValueError):
        Promise.from_dict(bad)
    bad = promise().to_dict()
    bad["related_entities"][0]["project"] = "book_b"
    with pytest.raises(ValueError):
        Promise.from_dict(bad)


def test_schema_definitions_are_valid_closed_and_do_not_drift():
    events = schema("events.schema.json")
    promises = schema("promises.schema.json")
    for doc in (events, promises):
        jsonschema.Draft202012Validator.check_schema(doc)
        root = doc["$defs"][doc["$ref"].split("/")[-1]] if "$ref" in doc else doc
        assert root["additionalProperties"] is False
    for key, definition in events["$defs"].items():
        assert promises["$defs"][key] == definition
    assert (
        events["$defs"]["entity_id"] == schema("entity.schema.json")["properties"]["id"]
    )


def test_records_and_json_exports_do_not_expose_mutable_state():
    participants = {eid("lin")}
    actual = event(participants=participants)
    participants.add(eid("zhou"))
    assert actual.participants == frozenset({eid("lin")})
    with pytest.raises((FrozenInstanceError, AttributeError)):
        actual.occurrence = Occurrence.UNKNOWN
    timeline = Timeline("book_a", (actual,))
    payload = timeline.to_dict()
    payload["events"][0]["participants"].clear()
    assert timeline.get(actual.id).participants == frozenset({eid("lin")})
    original = promise()
    payload = original.to_dict()
    payload["related_entities"].clear()
    assert len(original.related_entities) == 2
    payload["window"]["end"]["chapter"] = 999
    assert original.window.end == pos(3, 2)


def test_event_and_promise_do_not_execute_intent_or_publish_character_knowledge():
    lin = Character(eid("lin"), "林岚")
    zhou = Character(eid("zhou"), "周宁")
    state = KnowledgeState("book_a", (lin, zhou))
    east = Proposition(eid("key"), "located_at", "east_warehouse")
    west = Proposition(eid("key"), "located_at", "west_warehouse")
    state.add_fact(WorldFact(eid("key_location"), east, "inventory:east"))
    belief = Belief(eid("rumour"), zhou.id, west, "rumour:west")
    state.add_belief(belief)
    goal = Goal(eid("rescue_goal"), zhou.id, "取钥匙救人")
    state.add_goal(goal)
    intent = Intent(eid("west_plan"), zhou.id, goal.id, "去西库", (belief.id,))
    state.add_intent(intent)
    before = state.to_dict()
    timeline = Timeline("book_a")
    with pytest.raises(ValueError):
        timeline.add_event(intent)
    with pytest.raises(ValueError):
        Event.from_dict(intent.to_dict())
    actual = event()
    timeline.add_event(actual)
    resolved = promise().pay_off(timeline, actual.id, "reader-review:key-revealed")
    assert resolved.status is PromiseStatus.PAID
    assert state.to_dict() == before
    assert state.query(zhou.id, east) is KnowledgeLevel.UNKNOWN
    assert state.query(zhou.id, west) is KnowledgeLevel.BELIEVED
    assert len(state.facts) == 1
