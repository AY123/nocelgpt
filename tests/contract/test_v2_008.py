"""ADR-004: finite fact proposals validate then preview without committing Canon."""

from __future__ import annotations

import copy
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import jsonschema
import pytest

from anovel.domain.character import Character
from anovel.domain.delta import (
    FactBaseline,
    FactPath,
    FactSnapshot,
    FactState,
    FactStatus,
    MarkUnknown,
    NarrativeDelta,
    NoChange,
    OperationMeta,
    Precondition,
    ProseEvidence,
    RetractFact,
    ScalarKind,
    SetFact,
    operation_from_dict,
    preview_delta,
)
from anovel.domain.events import NarrativePosition, Timeline
from anovel.domain.identity import EntityId
from anovel.domain.knowledge import (
    KnowledgeLevel,
    KnowledgeState,
    Proposition,
    WorldFact,
)
from anovel.domain.promises import Promise, PromiseStatus, PromiseWindow

ROOT = Path(__file__).resolve().parents[2]
AUTH = frozenset({"proposal:chapter-2"})


def eid(name, project="book_a"):
    return EntityId(project, name)


SOURCE = eid("chapter_2_text")


def seed(name="key_location", value="east_warehouse", project="book_a"):
    return WorldFact(
        eid(name, project),
        Proposition(eid(name + "_subject", project), "located_at", value),
        "initial:inventory",
    )


def baseline(*facts):
    return FactBaseline.from_world_facts(
        "book_a", "main", "parent_1", facts or (seed(),)
    )


def meta(base, target="key_location", *, op_id="change_key", **overrides):
    snapshot = base.get(eid(target))
    values = dict(
        id=eid(op_id),
        target_id=eid(target),
        path=FactPath.VALUE,
        expected=Precondition.from_snapshot(snapshot),
        evidence=ProseEvidence(
            SOURCE, NarrativePosition(2, 1), "chapter-2:paragraph-3"
        ),
        authorization_ref="proposal:chapter-2",
    )
    values.update(overrides)
    return OperationMeta(**values)


def delta(base, operations=None, **overrides):
    values = dict(
        id=eid("delta_chapter_2"),
        branch=base.branch,
        parent_ref=base.parent_ref,
        source_id=SOURCE,
        operations=operations
        if operations is not None
        else (SetFact(meta(base), "west_warehouse"),),
    )
    values.update(overrides)
    return NarrativeDelta(**values)


def preview(base, proposed, **overrides):
    values = dict(source_id=SOURCE, authorization_refs=AUTH)
    values.update(overrides)
    return preview_delta(base, proposed, **values)


def schema(definition=None):
    doc = json.loads((ROOT / "specs/schemas/narrative-delta.schema.json").read_text())
    return (
        {"$ref": "#/$defs/" + definition, "$defs": doc["$defs"]} if definition else doc
    )


def json_copy(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def test_set_fact_changes_real_candidate_and_keeps_baseline_unchanged():
    """AT-V2-008-01: valid path/value/evidence actually changes a candidate value."""
    base = baseline()
    before = base.to_dict()
    proposed = delta(base)
    result = preview(base, proposed)
    changed = result.candidate.get(eid("key_location"))
    assert result.delta_id == proposed.id
    assert changed.state == FactState.known("west_warehouse")
    assert changed.revision == 1
    assert changed.seed_fact == seed()
    assert changed.value_kind is ScalarKind.STRING
    assert len(result.changes) == 1
    assert result.changes[0].operation_id == proposed.operations[0].meta.id
    assert result.changes[0].before == base.get(eid("key_location"))
    assert result.changes[0].after == changed
    assert base.to_dict() == before
    assert base.get(eid("key_location")).state == FactState.known("east_warehouse")


@pytest.mark.parametrize(
    "field", ["path", "value", "evidence", "expected", "authorization_ref", "target_id"]
)
def test_set_fact_missing_required_input_is_not_a_proposal(field):
    """AT-V2-008-01 negative: no silent defaults for mandatory evidence or payload."""
    base = baseline()
    payload = delta(base).to_dict()
    del payload["operations"][0][field]
    with pytest.raises(ValueError):
        NarrativeDelta.from_dict(payload)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema())


@pytest.mark.parametrize(
    "op_type,status",
    [(MarkUnknown, FactStatus.UNKNOWN), (RetractFact, FactStatus.RETRACTED)],
)
def test_unknown_and_retraction_preserve_identity_but_are_distinct(op_type, status):
    """AT-V2-008-02: two distinct markers, neither absence nor a nullable fact."""
    base = baseline()
    original = base.get(eid("key_location"))
    result = preview(base, delta(base, (op_type(meta(base)),)))
    after = result.candidate.get(eid("key_location"))
    assert after.state.status is status
    assert after.state.to_dict() == {"status": status.value}
    assert after.revision == original.revision + 1
    assert after.seed_fact == original.seed_fact
    assert after.seed_fact.evidence_ref == "initial:inventory"
    assert result.changes[0].before.state == FactState.known("east_warehouse")
    assert base.get(eid("key_location")) == original
    assert (
        FactBaseline.from_dict(json_copy(result.candidate.to_dict()))
        == result.candidate
    )


@pytest.mark.parametrize(
    "state",
    [FactState.known("east_warehouse"), FactState.unknown(), FactState.retracted()],
)
def test_no_change_is_an_operation_that_preserves_the_complete_snapshot(state):
    base = FactBaseline(
        "book_a", "main", "parent_1", (FactSnapshot(seed(), 7, state=state),)
    )
    snapshot = base.get(eid("key_location"))
    proposed = delta(base, (NoChange(meta(base)),))
    result = preview(base, proposed)
    assert result.candidate.get(eid("key_location")) is snapshot
    assert result.candidate == base
    assert result.changes == ()
    assert preview(base, proposed) == result
    assert "value" not in proposed.to_dict()["operations"][0]
    with pytest.raises(ValueError):
        FactState.from_dict({"status": "NO_CHANGE"})


@pytest.mark.parametrize("status", ["UNKNOWN", "RETRACTED"])
@pytest.mark.parametrize("value", [None, "x", 1, False])
def test_marker_state_forbids_any_value_including_null(status, value):
    payload = {"status": status, "value": value}
    with pytest.raises(ValueError):
        FactState.from_dict(payload)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema("fact_state"))


@pytest.mark.parametrize("op_type", [MarkUnknown, RetractFact, NoChange])
def test_non_set_operation_forbids_value_field(op_type):
    base = baseline()
    payload = op_type(meta(base)).to_dict()
    payload["value"] = None
    with pytest.raises(ValueError):
        operation_from_dict(payload)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema("operation"))


@pytest.mark.parametrize(
    "value", [None, [], {}, float("nan"), float("inf"), -float("inf")]
)
def test_set_payload_is_a_non_null_finite_json_scalar(value):
    with pytest.raises(ValueError):
        SetFact(meta(baseline()), value)
    with pytest.raises(ValueError):
        FactState.known(value)


@pytest.mark.parametrize("value", [True, 1, 1.0])
def test_operation_cannot_override_seed_type(value):
    """AT-V2-008-03: a syntactically scalar payload cannot lie about target type."""
    base = baseline()
    proposed = delta(base, (SetFact(meta(base), value),))
    jsonschema.validate(
        proposed.to_dict(), schema()
    )  # structural, not dynamic seed knowledge
    with pytest.raises(ValueError):
        preview(base, proposed)


@pytest.mark.parametrize(
    "initial,next_value,kind",
    [
        (False, True, ScalarKind.BOOLEAN),
        (1, 1.5, ScalarKind.NUMBER),
        (1.5, 2, ScalarKind.NUMBER),
        ("east", "west", ScalarKind.STRING),
    ],
)
def test_compatible_seed_categories_have_positive_controls(initial, next_value, kind):
    base = baseline(seed(value=initial))
    result = preview(base, delta(base, (SetFact(meta(base), next_value),)))
    assert result.candidate.get(eid("key_location")).state == FactState.known(
        next_value
    )
    assert result.candidate.get(eid("key_location")).value_kind is kind


@pytest.mark.parametrize(
    "initial,value", [(False, 0), (True, 1), (1, True), (0, False), (1, "1")]
)
def test_boolean_number_and_string_are_not_coerced(initial, value):
    base = baseline(seed(value=initial))
    with pytest.raises(ValueError):
        preview(base, delta(base, (SetFact(meta(base), value),)))
    assert FactState.known(True) != FactState.known(1)


def test_unknown_keeps_seed_type_and_can_become_known_again():
    base = baseline()
    unknown = preview(base, delta(base, (MarkUnknown(meta(base)),))).candidate
    assert unknown.get(eid("key_location")).state.status is FactStatus.UNKNOWN
    assert unknown.get(eid("key_location")).value_kind is ScalarKind.STRING
    with pytest.raises(ValueError):
        preview(unknown, delta(unknown, (SetFact(meta(unknown), True),)))
    known = preview(unknown, delta(unknown)).candidate.get(eid("key_location"))
    assert known.state == FactState.known("west_warehouse") and known.revision == 2


@pytest.mark.parametrize("op_type", [SetFact, MarkUnknown, RetractFact])
def test_retracted_fact_has_no_implicit_restore(op_type):
    base = baseline()
    retracted = preview(base, delta(base, (RetractFact(meta(base)),))).candidate
    operation = (
        SetFact(meta(retracted), "new")
        if op_type is SetFact
        else op_type(meta(retracted))
    )
    with pytest.raises(ValueError):
        preview(retracted, delta(retracted, (operation,)))
    assert (
        preview(retracted, delta(retracted, (NoChange(meta(retracted)),))).changes == ()
    )


def test_real_mutations_do_not_accept_no_op_payloads():
    base = baseline()
    with pytest.raises(ValueError):
        preview(base, delta(base, (SetFact(meta(base), "east_warehouse"),)))
    unknown = preview(base, delta(base, (MarkUnknown(meta(base)),))).candidate
    with pytest.raises(ValueError):
        preview(unknown, delta(unknown, (MarkUnknown(meta(unknown)),)))


@pytest.mark.parametrize(
    "expected",
    [
        Precondition(99, FactState.known("east_warehouse")),
        Precondition(0, FactState.known("other")),
        Precondition(0, FactState.unknown()),
        Precondition(0, FactState.retracted()),
    ],
)
def test_precondition_checks_version_state_and_value(expected):
    base = baseline()
    operation = SetFact(meta(base, expected=expected), "west_warehouse")
    with pytest.raises(ValueError):
        preview(base, delta(base, (operation,)))


def test_revision_blocks_aba_and_repeat_mutation_but_original_preview_is_pure():
    base = baseline()
    proposed = delta(base)
    first = preview(base, proposed)
    assert preview(base, proposed) == first
    with pytest.raises(ValueError):
        preview(first.candidate, proposed)
    back = preview(
        first.candidate,
        delta(first.candidate, (SetFact(meta(first.candidate), "east_warehouse"),)),
    ).candidate
    assert back.get(eid("key_location")).state == base.get(eid("key_location")).state
    assert back.get(eid("key_location")).revision == 2
    with pytest.raises(ValueError):
        preview(back, proposed)


def test_batch_second_failure_does_not_leak_first_candidate_change():
    base = baseline(seed(), seed("other", "initial"))
    before = base.to_dict()
    operations = (
        SetFact(meta(base), "west_warehouse"),
        SetFact(
            meta(
                base,
                "other",
                op_id="change_other",
                expected=Precondition(10, FactState.known("initial")),
            ),
            "next",
        ),
    )
    with pytest.raises(ValueError):
        preview(base, delta(base, operations))
    assert base.to_dict() == before
    valid = (operations[0], SetFact(meta(base, "other", op_id="change_other"), "next"))
    result = preview(base, delta(base, valid))
    assert len(result.changes) == 2
    assert result.candidate.get(eid("key_location")).state == FactState.known(
        "west_warehouse"
    )
    assert result.candidate.get(eid("other")).state == FactState.known("next")
    assert base.to_dict() == before


@pytest.mark.parametrize("duplicate", ["operation_id", "target"])
def test_duplicate_operation_identity_or_path_rejected(duplicate):
    base = baseline(seed(), seed("other", "initial"))
    second = (
        SetFact(meta(base, "other", op_id="change_key"), "next")
        if duplicate == "operation_id"
        else MarkUnknown(meta(base, op_id="second_op"))
    )
    with pytest.raises(ValueError):
        delta(base, (SetFact(meta(base), "west_warehouse"), second))


def test_empty_or_unregistered_runtime_operations_cannot_become_a_delta():
    base = baseline()
    for ops in ((), (object(),)):
        with pytest.raises(ValueError):
            delta(base, ops)

    class UnregisteredSet(SetFact):
        pass

    with pytest.raises(ValueError):
        delta(base, (UnregisteredSet(meta(base), "west_warehouse"),))


@pytest.mark.parametrize(
    "field,value",
    [
        ("op", "DELETE"),
        ("op", "CREATE_EVENT"),
        ("op", "genre:CHANGE_RESOURCE"),
        ("version", "2.0"),
        ("path", "character.lifecycle"),
        ("path", "../proposition.value"),
        ("value_type", "STRING"),
        ("allow", True),
    ],
)
def test_unregistered_operation_version_path_or_self_authorization_rejected(
    field, value
):
    """AT-V2-008-03: closed operation registry, not a free patch payload."""
    payload = delta(baseline()).to_dict()
    payload["operations"][0][field] = value
    with pytest.raises(ValueError):
        NarrativeDelta.from_dict(payload)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema())


@pytest.mark.parametrize(
    "field,value", [("parent_ref", "old_parent"), ("branch", "other_branch")]
)
def test_delta_scope_must_match_external_baseline(field, value):
    base = baseline()
    with pytest.raises(ValueError):
        preview(base, delta(base, **{field: value}))


@pytest.mark.parametrize("op_type", [SetFact, MarkUnknown, RetractFact, NoChange])
def test_every_operation_requires_external_source_and_authority(op_type):
    base = baseline()
    op = (
        SetFact(meta(base), "west_warehouse")
        if op_type is SetFact
        else op_type(meta(base))
    )
    proposed = delta(base, (op,))
    with pytest.raises(ValueError):
        preview(base, proposed, authorization_refs=frozenset())
    with pytest.raises(ValueError):
        preview(base, proposed, authorization_refs=frozenset({"other:grant"}))
    with pytest.raises(ValueError):
        preview(base, proposed, source_id=eid("other_source"))


def test_no_change_does_not_bypass_precondition_checks():
    base = baseline()
    with pytest.raises(ValueError):
        preview(
            base,
            delta(
                base,
                (
                    NoChange(
                        meta(
                            base,
                            expected=Precondition(3, FactState.known("east_warehouse")),
                        )
                    ),
                ),
            ),
        )


def test_unregistered_target_and_cross_project_references_rejected():
    base = baseline()
    with pytest.raises(ValueError):
        preview(
            base,
            delta(
                base, (SetFact(meta(base, target_id=eid("missing")), "west_warehouse"),)
            ),
        )
    with pytest.raises(ValueError):
        meta(base, target_id=eid("key_location", "book_b"))
    with pytest.raises(ValueError):
        meta(
            base,
            evidence=ProseEvidence(
                eid("text", "book_b"), NarrativePosition(2, 1), "text:p1"
            ),
        )
    with pytest.raises(ValueError):
        delta(base, id=eid("delta", "book_b"))
    with pytest.raises(ValueError):
        base.get(eid("key_location", "book_b"))
    assert base.get(eid("missing")) is None


@pytest.mark.parametrize("bad", [-1, True, 1.0, "1", None])
def test_fact_revision_is_strict_nonnegative_integer(bad):
    with pytest.raises(ValueError):
        FactSnapshot(seed(), bad)
    with pytest.raises(ValueError):
        Precondition(bad, FactState.known("east_warehouse"))


def test_duplicate_fact_ids_and_incompatible_snapshot_state_rejected():
    with pytest.raises(ValueError):
        baseline(seed(), seed())
    with pytest.raises(ValueError):
        FactSnapshot(seed(), state=FactState.known(True))
    with pytest.raises(ValueError):
        baseline(seed(project="book_b"))


@pytest.mark.parametrize("op_type", [SetFact, MarkUnknown, RetractFact, NoChange])
def test_complete_nondefault_delta_and_candidate_roundtrip(op_type):
    base = FactBaseline(
        "book_a", "draft/branch", "parent_nondefault", (FactSnapshot(seed(), 42),)
    )
    op = (
        SetFact(meta(base), "west_warehouse")
        if op_type is SetFact
        else op_type(meta(base))
    )
    original = delta(base, (op,))
    payload = json_copy(original.to_dict())
    jsonschema.validate(payload, schema())
    restored = NarrativeDelta.from_dict(payload)
    assert restored == original
    assert restored.to_dict() == original.to_dict()
    candidate = preview(base, restored).candidate
    wire = json_copy(candidate.to_dict())
    jsonschema.validate(wire, schema("fact_baseline"))
    assert FactBaseline.from_dict(wire) == candidate
    assert operation_from_dict(json_copy(op.to_dict())) == op


@pytest.mark.parametrize(
    "path",
    [
        (),
        ("operations", 0),
        ("operations", 0, "expected"),
        ("operations", 0, "expected", "state"),
        ("operations", 0, "evidence"),
        ("operations", 0, "evidence", "position"),
    ],
)
def test_json_is_closed_at_each_proposal_layer(path):
    payload = delta(baseline()).to_dict()
    node = payload
    for key in path:
        node = node[key]
    node["typo_field"] = "not allowed"
    with pytest.raises(ValueError):
        NarrativeDelta.from_dict(payload)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema())


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "CHANGESET"),
        ("schema_version", "2.0"),
        ("operations", []),
        ("operations", None),
        ("source_id", None),
    ],
)
def test_malformed_root_rejected_by_domain_and_schema(field, value):
    payload = delta(baseline()).to_dict()
    payload[field] = value
    with pytest.raises(ValueError):
        NarrativeDelta.from_dict(payload)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema())


def test_baseline_restore_rechecks_types_and_snapshot_fields():
    payload = baseline().to_dict()
    for field in ("seed_fact", "state", "revision"):
        bad = copy.deepcopy(payload)
        del bad["facts"][0][field]
        with pytest.raises(ValueError):
            FactBaseline.from_dict(bad)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema("fact_baseline"))
    bad = copy.deepcopy(payload)
    bad["facts"][0]["state"]["value"] = True
    with pytest.raises(ValueError):
        FactBaseline.from_dict(bad)
    for status in ("UNCERTAIN", "CONTRADICTORY", "ABSENT"):
        with pytest.raises(ValueError):
            FactState.from_dict({"status": status})


def test_exports_and_records_are_immutable_and_detached():
    base = baseline()
    proposed = delta(base)
    payload = proposed.to_dict()
    payload["operations"][0]["evidence"]["evidence_ref"] = "tampered"
    payload["operations"].clear()
    assert proposed.operations[0].meta.evidence.evidence_ref == "chapter-2:paragraph-3"
    wire = base.to_dict()
    wire["facts"][0]["seed_fact"]["proposition"]["value"] = "tampered"
    assert base.get(eid("key_location")).seed_fact.proposition.value == "east_warehouse"
    with pytest.raises((FrozenInstanceError, AttributeError)):
        base.parent_ref = "tampered"
    with pytest.raises((FrozenInstanceError, AttributeError)):
        proposed.operations[0].value = "tampered"


def test_candidate_preview_does_not_publish_facts_knowledge_events_or_payoffs():
    lin = Character(eid("lin"), "林岚")
    knowledge = KnowledgeState("book_a", (lin,))
    fact = seed()
    knowledge.add_fact(fact)
    timeline = Timeline("book_a")
    promise = Promise(
        eid("where_is_key"),
        "解释钥匙去向",
        NarrativePosition(1, 1),
        PromiseWindow.unknown(),
        evidence_ref="chapter-1:promise",
    )
    before = knowledge.to_dict()
    base = baseline(*knowledge.facts)
    result = preview(base, delta(base))
    assert result.candidate.get(fact.id).state == FactState.known("west_warehouse")
    assert knowledge.to_dict() == before
    assert knowledge.facts[0].proposition.value == "east_warehouse"
    assert knowledge.query(lin.id, fact.proposition) is KnowledgeLevel.UNKNOWN
    assert timeline.events == ()
    assert promise.status is PromiseStatus.OPEN


@pytest.mark.parametrize(
    "new_name,old_file,old_name",
    [
        ("entity_id", "knowledge.schema.json", "id"),
        ("proposition", "knowledge.schema.json", "proposition"),
        ("world_fact", "knowledge.schema.json", "fact"),
        ("narrative_position", "events.schema.json", "narrative_position"),
    ],
)
def test_schema_reuses_delivered_contracts_without_drift(new_name, old_file, old_name):
    doc = json.loads((ROOT / "specs/schemas/narrative-delta.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(doc)
    old = json.loads((ROOT / "specs/schemas" / old_file).read_text())["$defs"][old_name]
    normalized = json.loads(json.dumps(old).replace("#/$defs/id", "#/$defs/entity_id"))
    assert doc["$defs"][new_name] == normalized


@pytest.mark.parametrize("field", ["evidence_ref", "authorization_ref"])
def test_required_references_cannot_be_empty(field):
    payload = delta(baseline()).to_dict()
    node = (
        payload["operations"][0]["evidence"]
        if field == "evidence_ref"
        else payload["operations"][0]
    )
    node[field] = ""
    with pytest.raises(ValueError):
        NarrativeDelta.from_dict(payload)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema())


def test_operation_source_must_match_delta_even_within_one_project():
    base = baseline()
    other = ProseEvidence(eid("other_chapter"), NarrativePosition(2, 1), "text:other")
    op = SetFact(meta(base, evidence=other), "west_warehouse")
    with pytest.raises(ValueError):
        delta(base, (op,))
