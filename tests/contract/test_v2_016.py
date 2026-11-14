"""Registered fantasy facts, explicit before-state rules and exact resource costs.

Story text/semantic annotations here are supplied fixtures. They do not prove
extraction, production Permit readiness, literary quality or human book approval.
"""

import json
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from anovel.canon.identity import canonical_bytes
from anovel.canon.models import RootSeed
from anovel.domain.delta import (
    FactBaseline,
    FactPath,
    MarkUnknown,
    NarrativeDelta,
    OperationMeta,
    Precondition,
    ProseEvidence,
    RetractFact,
    SetFact,
    preview_delta,
)
from anovel.domain.events import NarrativePosition, Occurrence
from anovel.domain.extensions import ExtensionBinding, ExtensionRegistry
from anovel.domain.identity import Entity, EntityId
from anovel.domain.knowledge import Proposition, WorldFact
from anovel.genre.extensions.progression import (
    AbilityDefinition,
    AbilityState,
    Cultivator,
    ProgressionResource,
    ProgressionState,
    RealmDefinition,
    advance_realm,
    create_progression_binding,
    learn_ability,
    transfer_resource,
    use_ability,
)
from anovel.genre.extensions.progression_contracts import (
    PROGRESSION_PACK_IDENTITY,
    PROGRESSION_SCHEMA_BYTES,
    PROGRESSION_SCHEMA_HASH,
)
from anovel.genre.extensions.registration import registered_extensions
from anovel.genre.policy import (
    ClaimContext,
    EvidenceSpan,
    GenrePolicy,
    Mechanism,
    PolicyStatus,
    SemanticClaim,
    SourceDocument,
)
from anovel.genre.registry import GenreRegistry, PackRef, ProjectGenreBinding

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "specs/genres"
PROJECT = "progression-contract"
BRANCH = "main"
PARENT = "sha256:" + "a" * 64
AUTH = "supplied-fantasy-fixture"
FANTASY = "fantasy.eastern.progression"
URBAN = "urban.business.realistic"


def eid(value, project=PROJECT):
    return EntityId(project, value)


def pack(project=PROJECT, anchor=FANTASY, version="1.1.0"):
    rows = json.loads((SOURCE / "registry.yaml").read_text())["packs"]
    row = next(r for r in rows if r["id"] == anchor and r["version"] == version)
    return GenreRegistry.from_directory(SOURCE).bind(
        project, PackRef(row["id"], row["version"], row["content_hash"])
    )


def sample(*, learned=False, quantity=20):
    return ProgressionState(
        (
            RealmDefinition(eid("realm-0"), 0, "灵石", "颗", 0),
            RealmDefinition(eid("realm-1"), 1, "灵石", "颗", 5),
            RealmDefinition(eid("realm-2"), 2, "灵石", "颗", 9),
        ),
        (
            Cultivator(eid("alice"), eid("realm-0")),
            Cultivator(eid("bob"), eid("realm-0")),
        ),
        (AbilityDefinition(eid("step"), eid("realm-0"), "灵石", "颗", 3, 2),),
        (
            AbilityState(eid("ability-alice"), eid("alice"), eid("step"), learned, 0),
            AbilityState(eid("ability-bob"), eid("bob"), eid("step"), False, 0),
        ),
        (
            ProgressionResource(
                eid("pool-alice"), eid("alice"), "灵石", "颗", quantity, 0
            ),
            ProgressionResource(eid("pool-bob"), eid("bob"), "灵石", "颗", 20, 0),
            ProgressionResource(eid("pool-guild"), eid("商会"), "灵石", "颗", 10, 0),
        ),
    )


def entity_ids(state):
    result = set()

    def collect(value):
        if isinstance(value, dict):
            if set(value) == {"project", "local_id"}:
                result.add(EntityId.from_dict(value))
            else:
                for item in value.values():
                    collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(state.to_dict())
    return tuple(sorted(result, key=str))


def baseline(state=None, extra_facts=()):
    state = sample() if state is None else state
    binding = create_progression_binding(pack(), entity_ids(state))
    return FactBaseline.from_world_facts(
        PROJECT,
        BRANCH,
        PARENT,
        state.to_facts("manual-fantasy-root") + extra_facts,
        extensions=(binding,),
    )


def fact(state, subject, field):
    return next(
        f
        for f in state.facts
        if f.seed_fact.proposition.subject == eid(subject)
        and f.seed_fact.proposition.predicate.rsplit(".", 1)[-1] == field
    )


def evidence(name="candidate"):
    return ProseEvidence(eid(name), NarrativePosition(1, 1), "fixture:prose/1")


def delta_with(state, changes, operation=SetFact):
    records = []
    prose = evidence()
    for index, (subject, field, value) in enumerate(changes):
        target = fact(state, subject, field)
        meta = OperationMeta(
            eid("op-" + str(index)),
            target.seed_fact.id,
            FactPath.VALUE,
            Precondition.from_snapshot(target),
            prose,
            AUTH,
        )
        records.append(
            operation(meta, value) if operation is SetFact else operation(meta)
        )
    return NarrativeDelta(
        eid("delta"), BRANCH, state.parent_ref, prose.source_id, tuple(records)
    )


def preview(state, delta, registry=None):
    return preview_delta(
        state,
        delta,
        source_id=delta.source_id,
        authorization_refs=frozenset({AUTH}),
        extension_registry=registered_extensions() if registry is None else registry,
    ).candidate


def action(state, fn, target):
    return fn(
        state,
        eid(target),
        delta_id=eid("delta"),
        evidence=evidence(),
        authorization_ref=AUTH,
    )


def transfer(state, amount=3, source="pool-alice", target="pool-guild"):
    return transfer_resource(
        state,
        eid(source),
        eid(target),
        amount,
        delta_id=eid("delta"),
        evidence=evidence(),
        authorization_ref=AUTH,
    )


def test_registered_schema_type_fact_and_binding_roundtrip_are_consistent():
    state = sample()
    schema = json.loads(PROGRESSION_SCHEMA_BYTES)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(state.to_dict())
    assert ProgressionState.from_dict(state.to_dict()) == state
    bound = baseline()
    assert canonical_bytes(
        ProgressionState.from_baseline(bound).to_dict()
    ) == canonical_bytes(state.to_dict())
    assert (
        canonical_bytes(json.loads((SOURCE / FANTASY / "schema.json").read_bytes()))
        == PROGRESSION_SCHEMA_BYTES
    )
    assert sha256(PROGRESSION_SCHEMA_BYTES).hexdigest() == PROGRESSION_SCHEMA_HASH
    assert pack().ref == PackRef(*PROGRESSION_PACK_IDENTITY)
    ids = entity_ids(state)
    seed = RootSeed(
        tuple(Entity(i, i.local_id) for i in ids),
        (),
        state.to_facts("manual-root"),
        extensions=bound.extensions,
    )
    assert RootSeed.from_dict(seed.to_dict()) == seed
    assert FactBaseline.from_dict(bound.to_dict()) == bound
    assert (
        ExtensionBinding.from_dict(bound.extensions[0].to_dict()) == bound.extensions[0]
    )
    assert bound.extensions[0].pack_bytes == canonical_bytes(pack().to_dict())
    assert bound.extensions[0].schema_bytes == PROGRESSION_SCHEMA_BYTES


@pytest.mark.parametrize("value", [True, False, 1.0, -1, None, "5"])
def test_resource_and_rank_require_exact_nonnegative_integers(value):
    with pytest.raises(ValueError):
        ProgressionResource(eid("pool"), eid("alice"), "灵石", "颗", value, 0)
    with pytest.raises(ValueError):
        ProgressionResource(eid("pool"), eid("alice"), "灵石", "颗", 5, value)
    with pytest.raises(ValueError):
        RealmDefinition(eid("realm"), value, "灵石", "颗", 1)
    with pytest.raises(ValueError):
        AbilityState(eid("ability"), eid("alice"), eid("step"), True, value)


@pytest.mark.parametrize("value", [False, True, 1.0, 0, -1, None])
def test_declared_learning_and_use_costs_are_positive_strict_integers(value):
    with pytest.raises(ValueError):
        AbilityDefinition(eid("step"), eid("realm-0"), "灵石", "颗", value, 2)
    with pytest.raises(ValueError):
        AbilityDefinition(eid("step"), eid("realm-0"), "灵石", "颗", 3, value)


@pytest.mark.parametrize("value", [0, 1, None, "true", [], {}])
def test_learned_requires_boolean_instead_of_truthiness(value):
    with pytest.raises(ValueError):
        AbilityState(eid("ability"), eid("alice"), eid("step"), value, 0)


@pytest.mark.parametrize(
    "collection,field,value",
    [
        ("resources", "quantity", -1),
        ("resources", "spent", True),
        ("realms", "rank", True),
        ("ability_states", "learned", 1),
    ],
)
def test_schema_and_type_reject_invalid_structural_input(collection, field, value):
    document = sample().to_dict()
    document[collection][0][field] = value
    assert list(
        Draft202012Validator(json.loads(PROGRESSION_SCHEMA_BYTES)).iter_errors(document)
    )
    with pytest.raises(ValueError):
        ProgressionState.from_dict(document)


@pytest.mark.parametrize(
    "field", ["company", "shares", "shareholding", "modern_equity", "cash_account"]
)
def test_unregistered_modern_equity_fields_do_not_pollute_fantasy_state(field):
    document = sample().to_dict()
    document["cultivators"][0][field] = 100
    assert list(
        Draft202012Validator(json.loads(PROGRESSION_SCHEMA_BYTES)).iter_errors(document)
    )
    with pytest.raises(ValueError):
        ProgressionState.from_dict(document)


@pytest.mark.parametrize(
    "fault",
    [
        "rank-gap",
        "rank-repeat",
        "realm-unknown",
        "ability-unknown",
        "owner-unknown",
        "resource-pool-repeat",
        "ability-state-repeat",
        "unlearned-uses",
    ],
)
def test_registered_state_rejects_inconsistent_references_and_sequences(fault):
    s = sample()
    with pytest.raises(ValueError):
        if fault == "rank-gap":
            replace(
                s,
                realms=(
                    s.realms[0],
                    replace(s.realms[1], rank=2),
                    replace(s.realms[2], rank=3),
                ),
            )
        elif fault == "rank-repeat":
            replace(s, realms=(s.realms[0], replace(s.realms[1], rank=0), s.realms[2]))
        elif fault == "realm-unknown":
            replace(
                s,
                cultivators=(
                    replace(s.cultivators[0], realm=eid("no-realm")),
                    s.cultivators[1],
                ),
            )
        elif fault == "ability-unknown":
            replace(
                s,
                ability_states=(
                    replace(s.ability_states[0], ability=eid("no-ability")),
                    s.ability_states[1],
                ),
            )
        elif fault == "owner-unknown":
            replace(
                s,
                ability_states=(
                    replace(s.ability_states[0], owner=eid("not-cultivator")),
                    s.ability_states[1],
                ),
            )
        elif fault == "resource-pool-repeat":
            replace(
                s,
                resources=s.resources
                + (replace(s.resources[0], id=eid("second-pool")),),
            )
        elif fault == "ability-state-repeat":
            replace(
                s,
                ability_states=s.ability_states
                + (replace(s.ability_states[0], id=eid("second-ability-state")),),
            )
        else:
            replace(
                s,
                ability_states=(
                    replace(s.ability_states[0], uses=1),
                    s.ability_states[1],
                ),
            )


def test_fantasy_fact_codec_is_deterministic_scalar_and_state_is_immutable():
    s = sample()
    facts = s.to_facts("supplied-root")
    assert facts == s.to_facts("supplied-root")
    assert len({f.id for f in facts}) == len(facts)
    assert len(
        {(f.proposition.subject, f.proposition.predicate) for f in facts}
    ) == len(facts)
    assert all(
        f.proposition.predicate.startswith("ext:fantasy.progression:") for f in facts
    )
    assert all(type(f.proposition.value) in (str, int, bool) for f in facts)
    with pytest.raises(FrozenInstanceError):
        s.resources[0].quantity = 0
    exported = s.to_dict()
    exported["resources"][0]["quantity"] = 0
    assert s.resources[0].quantity == 20
    with pytest.raises(ValueError):
        replace(s, resources=list(s.resources))


@pytest.mark.parametrize(
    "fn,target,learned,quantity,spent",
    [
        (advance_realm, "alice", False, 15, 5),
        (learn_ability, "ability-alice", False, 17, 3),
        (use_ability, "ability-alice", True, 18, 2),
    ],
)
def test_exact_registered_actions_pay_frozen_costs(
    fn, target, learned, quantity, spent
):
    before = baseline(sample(learned=learned))
    original = before.to_dict()
    delta = action(before, fn, target)
    assert all(type(op) is SetFact for op in delta.operations)
    after = preview(before, delta)
    assert fact(after, "pool-alice", "quantity").state.value == quantity
    assert fact(after, "pool-alice", "spent").state.value == spent
    if fn is advance_realm:
        assert fact(after, "alice", "realm").state.value == "realm-1"
    elif fn is learn_ability:
        assert fact(after, "ability-alice", "learned").state.value is True
    else:
        assert fact(after, "ability-alice", "uses").state.value == 1
    assert before.to_dict() == original and after.extensions == before.extensions
    assert ProgressionState.from_baseline(after)


def test_multiple_actions_sum_costs_instead_of_reusing_one_payment():
    before = baseline()
    after = preview(
        before,
        delta_with(
            before,
            [
                ("alice", "realm", "realm-1"),
                ("ability-alice", "learned", True),
                ("pool-alice", "quantity", 12),
                ("pool-alice", "spent", 8),
            ],
        ),
    )
    assert fact(after, "pool-alice", "quantity").state.value == 12
    assert fact(after, "pool-alice", "spent").state.value == 8


@pytest.mark.parametrize(
    "changes",
    [
        [("alice", "realm", "realm-1")],
        [
            ("alice", "realm", "realm-2"),
            ("pool-alice", "quantity", 11),
            ("pool-alice", "spent", 9),
        ],
        [
            ("alice", "realm", "realm-1"),
            ("pool-alice", "quantity", 16),
            ("pool-alice", "spent", 4),
        ],
        [
            ("alice", "realm", "realm-1"),
            ("pool-alice", "quantity", 14),
            ("pool-alice", "spent", 6),
        ],
        [
            ("alice", "realm", "realm-1"),
            ("pool-alice", "quantity", 15),
            ("pool-guild", "quantity", 15),
        ],
        [
            ("alice", "realm", "realm-1"),
            ("pool-bob", "quantity", 15),
            ("pool-bob", "spent", 5),
        ],
        [
            ("alice", "realm", "realm-1"),
            ("ability-alice", "learned", True),
            ("pool-alice", "quantity", 15),
            ("pool-alice", "spent", 5),
        ],
        [
            ("alice", "realm", "realm-1"),
            ("bob", "realm", "realm-1"),
            ("pool-alice", "quantity", 15),
            ("pool-alice", "spent", 5),
        ],
        [("pool-alice", "quantity", 15), ("pool-alice", "spent", 5)],
        [("pool-alice", "quantity", 21)],
        [("pool-alice", "quantity", 19)],
        [("pool-alice", "spent", 1)],
        [("pool-alice", "quantity", -1)],
    ],
)
def test_raw_set_fact_cannot_bypass_exact_cost_conservation_or_owner(changes):
    before = baseline()
    with pytest.raises(ValueError):
        preview(before, delta_with(before, changes))
    assert fact(before, "pool-alice", "quantity").state.value == 20


@pytest.mark.parametrize(
    "fn,target,cost,learned",
    [
        (advance_realm, "alice", 5, False),
        (learn_ability, "ability-alice", 3, False),
        (use_ability, "ability-alice", 2, True),
    ],
)
def test_every_action_requires_actor_own_before_resources(fn, target, cost, learned):
    before = baseline(sample(learned=learned, quantity=cost - 1))
    with pytest.raises(ValueError):
        action(before, fn, target)


def test_receiving_resources_in_same_delta_cannot_replace_before_cost_precondition():
    before = baseline(sample(quantity=0))
    with pytest.raises(ValueError):
        preview(
            before,
            delta_with(
                before,
                [
                    ("alice", "realm", "realm-1"),
                    ("pool-alice", "quantity", 5),
                    ("pool-alice", "spent", 5),
                    ("pool-guild", "quantity", 0),
                ],
            ),
        )


def test_learning_uses_before_realm_not_the_resulting_rank():
    s = sample()
    s = replace(s, abilities=(replace(s.abilities[0], minimum_realm=eid("realm-1")),))
    before = baseline(s)
    with pytest.raises(ValueError):
        action(before, learn_ability, "ability-alice")
    with pytest.raises(ValueError):
        preview(
            before,
            delta_with(
                before,
                [
                    ("alice", "realm", "realm-1"),
                    ("ability-alice", "learned", True),
                    ("pool-alice", "quantity", 12),
                    ("pool-alice", "spent", 8),
                ],
            ),
        )


def test_learning_and_use_in_same_delta_cannot_skip_before_learned_requirement():
    before = baseline()
    with pytest.raises(ValueError):
        action(before, use_ability, "ability-alice")
    with pytest.raises(ValueError):
        preview(
            before,
            delta_with(
                before,
                [
                    ("ability-alice", "learned", True),
                    ("ability-alice", "uses", 1),
                    ("pool-alice", "quantity", 15),
                    ("pool-alice", "spent", 5),
                ],
            ),
        )


def test_repeated_ability_uses_charge_each_use_and_never_refund():
    before = baseline(sample(learned=True))
    after = preview(
        before,
        delta_with(
            before,
            [
                ("ability-alice", "uses", 3),
                ("pool-alice", "quantity", 14),
                ("pool-alice", "spent", 6),
            ],
        ),
    )
    assert fact(after, "ability-alice", "uses").state.value == 3
    with pytest.raises(ValueError):
        preview(
            after,
            delta_with(
                after,
                [
                    ("ability-alice", "uses", 2),
                    ("pool-alice", "quantity", 16),
                    ("pool-alice", "spent", 4),
                ],
            ),
        )
    with pytest.raises(ValueError):
        preview(after, delta_with(after, [("ability-alice", "learned", False)]))


def test_realm_cannot_regress_or_reach_beyond_frozen_sequence():
    before = baseline()
    first = preview(before, action(before, advance_realm, "alice"))
    with pytest.raises(ValueError):
        preview(first, delta_with(first, [("alice", "realm", "realm-0")]))
    second = preview(first, action(first, advance_realm, "alice"))
    with pytest.raises(ValueError):
        action(second, advance_realm, "alice")


@pytest.mark.parametrize(
    "subject,field,value",
    [
        ("realm-1", "breakthrough_cost", 1),
        ("realm-1", "rank", 8),
        ("realm-1", "resource", "金币"),
        ("step", "minimum_realm", "realm-2"),
        ("step", "learning_cost", 1),
        ("step", "use_cost", 1),
        ("pool-alice", "owner", "bob"),
        ("pool-alice", "unit", "箱"),
        ("ability-alice", "ability", "missing-ability"),
    ],
)
def test_generic_delta_cannot_rewrite_frozen_rules_or_metadata(subject, field, value):
    before = baseline()
    with pytest.raises(ValueError):
        preview(before, delta_with(before, [(subject, field, value)]))


@pytest.mark.parametrize("operation", [MarkUnknown, RetractFact])
@pytest.mark.parametrize(
    "subject,field",
    [
        ("alice", "realm"),
        ("pool-alice", "quantity"),
        ("pool-alice", "spent"),
        ("step", "learning_cost"),
        ("ability-alice", "learned"),
    ],
)
def test_unknown_or_retracted_fields_cannot_remove_progression_preconditions(
    operation, subject, field
):
    before = baseline()
    with pytest.raises(ValueError):
        preview(before, delta_with(before, [(subject, field, None)], operation))


def test_guild_trade_is_legal_and_does_not_claim_cultivation_cost():
    before = baseline()
    after = preview(before, transfer(before, 3))
    assert fact(after, "pool-alice", "quantity").state.value == 17
    assert fact(after, "pool-guild", "quantity").state.value == 13
    assert (
        fact(after, "pool-alice", "spent").state.value
        == fact(after, "pool-guild", "spent").state.value
        == 0
    )
    assert fact(after, "alice", "realm").state.value == "realm-0"


@pytest.mark.parametrize("amount", [0, -1, True, 1.0, None, 21])
def test_trade_rejects_nonpositive_coerced_or_insufficient_amount(amount):
    with pytest.raises(ValueError):
        transfer(baseline(), amount)


@pytest.mark.parametrize("field,value", [("resource", "灵药"), ("unit", "箱")])
def test_trade_does_not_convert_resource_or_unit(field, value):
    s = sample()
    s = replace(
        s, resources=(*s.resources[:2], replace(s.resources[2], **{field: value}))
    )
    with pytest.raises(ValueError):
        transfer(baseline(s))


def test_cross_project_state_and_action_are_refused():
    with pytest.raises(ValueError):
        Cultivator(eid("alice"), eid("realm-0", "other-book"))
    with pytest.raises(ValueError):
        advance_realm(
            baseline(),
            eid("alice", "other-book"),
            delta_id=eid("delta"),
            evidence=evidence(),
            authorization_ref=AUTH,
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"version": "9.0.0"},
        {"namespace": "unknown.extension"},
        {"schema_id": "other-schema"},
        {"schema_hash": "0" * 64},
        {"pack_hash": "0" * 64},
        {"pack_version": "9.0.0"},
        {"schema_bytes": b"{}"},
        {"pack_bytes": b"{}"},
    ],
)
def test_binding_version_hash_and_retained_sources_cannot_self_authorize(changes):
    before = baseline()
    with pytest.raises(ValueError):
        invalid = replace(
            before, extensions=(replace(before.extensions[0], **changes),)
        )
        registered_extensions().validate_baseline(invalid)


@pytest.mark.parametrize(
    "anchor,version", [(FANTASY, "1.0.0"), (URBAN, "1.0.0"), (URBAN, "1.1.0")]
)
def test_wrong_anchor_or_legacy_pack_cannot_claim_fantasy_extension(anchor, version):
    with pytest.raises(ValueError):
        create_progression_binding(
            pack(anchor=anchor, version=version), entity_ids(sample())
        )


def test_unbound_or_empty_registry_cannot_accept_reserved_fantasy_facts():
    before = baseline()
    proposal = action(before, advance_realm, "alice")
    with pytest.raises(ValueError):
        preview(before, proposal, ExtensionRegistry())
    with pytest.raises(ValueError):
        preview(replace(before, extensions=()), proposal)
    with pytest.raises(ValueError):
        ProgressionState.from_baseline(replace(before, extensions=()))


def test_duplicate_or_unregistered_fact_identity_is_refused():
    before = baseline()
    duplicate = replace(
        before.facts[0],
        seed_fact=replace(before.facts[0].seed_fact, id=eid("forged-fact")),
    )
    with pytest.raises(ValueError):
        registered_extensions().validate_baseline(
            replace(before, facts=before.facts + (duplicate,))
        )
    ordinary = FactBaseline.from_world_facts(
        PROJECT,
        BRANCH,
        PARENT,
        (
            WorldFact(
                eid("ordinary"), Proposition(eid("alice"), "occupation", "商人"), "root"
            ),
        ),
    )
    with pytest.raises(ValueError):
        ProgressionState.from_baseline(ordinary)


def test_offline_binding_uses_retained_sources_not_current_catalog(monkeypatch):
    original = pack()
    record = original.to_dict()
    with monkeypatch.context() as isolated:
        isolated.setattr(
            Path,
            "read_bytes",
            lambda _path: pytest.fail(
                "Retained binding must not reopen current catalog"
            ),
        )
        restored = ProjectGenreBinding.from_dict(record)
    assert restored == original
    assert (
        create_progression_binding(restored, entity_ids(sample()))
        == baseline().extensions[0]
    )


def test_old_pack_versions_keep_original_sources_and_plain_fact_format():
    for anchor, expected in [
        (FANTASY, "820499c61491affb367b13a3b7e200911e9c0e586df1b55e15eb82c24cf56968"),
        (URBAN, "8cdcad278b40f570487ac31f2ef6340e68329943098863776f6048ebd1cda061"),
    ]:
        bound = pack(anchor=anchor, version="1.0.0")
        assert bound.ref.content_hash == expected and bound.pack.extensions == ()
    assert (
        pack(anchor=URBAN).ref.content_hash
        == "aadc2b0cd538d897299be7da775ecc81e51290ad7d5f89a325bcb55b0c8395c7"
    )
    ordinary = WorldFact(
        eid("fact"), Proposition(eid("alice"), "occupation", "商人"), "root"
    )
    plain = FactBaseline.from_world_facts(PROJECT, BRANCH, PARENT, (ordinary,))
    assert (
        plain.to_dict()["schema_version"] == "1.0"
        and "extensions" not in plain.to_dict()
    )


@pytest.mark.parametrize(
    "mechanism,context,expected",
    [
        (Mechanism.LOCAL_TRADE, ClaimContext.WORLD, PolicyStatus.PASS),
        (Mechanism.CULTIVATION, ClaimContext.WORLD, PolicyStatus.PASS),
        (Mechanism.MODERN_CORPORATE_SCHEMA, ClaimContext.WORLD, PolicyStatus.FAIL),
        (
            Mechanism.COST_FREE_CULTIVATION_ADVANCE,
            ClaimContext.WORLD,
            PolicyStatus.FAIL,
        ),
        (Mechanism.MODERN_CORPORATE_SCHEMA, ClaimContext.DREAM, PolicyStatus.PASS),
        (Mechanism.MODERN_CORPORATE_SCHEMA, ClaimContext.QUOTATION, PolicyStatus.PASS),
        (Mechanism.UNKNOWN, ClaimContext.WORLD, PolicyStatus.UNKNOWN),
    ],
)
def test_new_fantasy_policy_uses_explicit_world_evidence_not_business_keywords(
    mechanism, context, expected
):
    document = SourceDocument(
        eid("source"), "她向商会交易灵石，依冻结世界规则付出修炼代价。"
    )
    claim = SemanticClaim(
        "supplied-claim",
        mechanism,
        context,
        Occurrence.OCCURRED,
        EvidenceSpan(
            document.id, document.content_hash, 0, len(document.text), document.text
        ),
        "fixture:explicit-interpretation",
    )
    result = GenrePolicy(pack()).check(document, (claim,))
    assert result.status is expected
    assert result.prose_coverage == "NOT_VERIFIED"


def test_ordinary_fact_can_change_without_forcing_any_upgrade_or_battle():
    ordinary = WorldFact(
        eid("ordinary"), Proposition(eid("alice"), "occupation", "商人"), "root"
    )
    before = baseline(extra_facts=(ordinary,))
    after = preview(before, delta_with(before, [("alice", "occupation", "掌柜")]))
    assert after.get(ordinary.id).state.value == "掌柜"
    assert (
        ProgressionState.from_baseline(after).to_dict()
        == ProgressionState.from_baseline(before).to_dict()
    )
