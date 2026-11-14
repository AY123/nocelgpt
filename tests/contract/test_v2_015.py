"""Real registered business types and guarded finite fact transitions.

The Chinese prose/interpretations below are supplied fixtures. These tests
verify typed Canon inputs and deterministic genre rules, not prose extraction,
production Permit issuance, literary quality or financial/legal correctness.
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
from anovel.genre.extensions.business import (
    BusinessState,
    CashAccount,
    Company,
    ResourceHolding,
    ShareHolding,
    create_business_binding,
    transfer_cash,
    transfer_resource,
    transfer_shares,
)
from anovel.genre.extensions.contracts import (
    BUSINESS_PACK_IDENTITY,
    BUSINESS_SCHEMA_BYTES,
    BUSINESS_SCHEMA_HASH,
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
PROJECT = "business-contract"
BRANCH = "main"
PARENT = "sha256:" + "a" * 64
AUTH = "contract-fixture-reference"
URBAN = "urban.business.realistic"
FANTASY = "fantasy.eastern.progression"


def eid(value, project=PROJECT):
    return EntityId(project, value)


def pack(project=PROJECT, anchor=URBAN, version="1.1.0"):
    rows = json.loads((SOURCE / "registry.yaml").read_text())["packs"]
    row = next(r for r in rows if r["id"] == anchor and r["version"] == version)
    return GenreRegistry.from_directory(SOURCE).bind(
        project, PackRef(row["id"], row["version"], row["content_hash"])
    )


def sample(project=PROJECT):
    person_a, person_b, company = (eid(n, project) for n in ("alice", "bob", "company"))
    return BusinessState(
        (Company(company),),
        (
            CashAccount(eid("account-a", project), person_a, "CNY", 10_000),
            CashAccount(eid("account-b", project), person_b, "CNY", 0),
        ),
        (
            ShareHolding(eid("share-a", project), company, person_a, 700_000),
            ShareHolding(eid("share-b", project), company, person_b, 300_000),
        ),
        (
            ResourceHolding(eid("stock-a", project), person_a, "widget", "piece", 8),
            ResourceHolding(eid("stock-b", project), person_b, "widget", "piece", 2),
        ),
    )


def entity_ids(state):
    ids = {
        v.id
        for g in (state.companies, state.accounts, state.holdings, state.resources)
        for v in g
    }
    ids.update(
        v.owner for g in (state.accounts, state.holdings, state.resources) for v in g
    )
    return tuple(sorted(ids, key=str))


def baseline(state=None, extra_facts=()):
    state = sample() if state is None else state
    binding = create_business_binding(pack(), entity_ids(state))
    return FactBaseline.from_world_facts(
        PROJECT,
        BRANCH,
        PARENT,
        state.to_facts("manual-business-root") + extra_facts,
        extensions=(binding,),
    )


def fact(state, subject, field):
    return next(
        f
        for f in state.facts
        if f.seed_fact.proposition.subject == eid(subject)
        and f.seed_fact.proposition.predicate == "ext:urban.business:" + field
    )


def evidence(name="candidate"):
    return ProseEvidence(eid(name), NarrativePosition(1, 1), "fixture:prose/1")


def delta_with(state, changes, operation=SetFact):
    records = []
    prose = evidence()
    for index, (target, value) in enumerate(changes):
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
        authorization_refs=frozenset([AUTH]),
        extension_registry=registered_extensions() if registry is None else registry,
    )


def transfer(state, fn, source, target, amount):
    return fn(
        state,
        eid(source),
        eid(target),
        amount,
        delta_id=eid("delta"),
        evidence=evidence(),
        authorization_ref=AUTH,
    )


def test_business_schema_and_types_accept_real_closed_sample_with_minor_units():
    state = sample()
    bound = baseline()
    schema = json.loads(BUSINESS_SCHEMA_BYTES)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(state.to_dict())
    assert BusinessState.from_dict(state.to_dict()) == state
    assert BusinessState.from_baseline(bound) == state
    assert sha256(BUSINESS_SCHEMA_BYTES).hexdigest() == BUSINESS_SCHEMA_HASH
    assert (
        canonical_bytes(json.loads((SOURCE / URBAN / "schema.json").read_bytes()))
        == BUSINESS_SCHEMA_BYTES
    )
    assert pack().ref == PackRef(*BUSINESS_PACK_IDENTITY)
    assert len(pack().pack.extensions) == 1
    assert state.accounts[0].balance_minor == 10_000
    assert sum(h.parts for h in state.holdings) == 1_000_000
    assert sum(r.quantity for r in state.resources) == 10


@pytest.mark.parametrize(
    "field,value",
    [
        ("balance_minor", -1),
        ("balance_minor", True),
        ("currency", "cny"),
        ("currency", "CNY\n"),
    ],
)
def test_schema_and_domain_reject_invalid_account_input(field, value):
    document = sample().to_dict()
    document["accounts"][0][field] = value
    assert list(
        Draft202012Validator(json.loads(BUSINESS_SCHEMA_BYTES)).iter_errors(document)
    )
    with pytest.raises(ValueError):
        BusinessState.from_dict(document)


@pytest.mark.parametrize("value", [True, False, 1.0, -1, None, "100"])
def test_cash_and_resource_quantities_require_exact_nonnegative_integers(value):
    with pytest.raises(ValueError):
        CashAccount(eid("account"), eid("owner"), "CNY", value)
    with pytest.raises(ValueError):
        ResourceHolding(eid("stock"), eid("owner"), "widget", "piece", value)


@pytest.mark.parametrize("value", [True, 1.0, -1, 1_000_001, None])
def test_share_parts_require_strict_bounded_integer_ratio(value):
    with pytest.raises(ValueError):
        ShareHolding(eid("share"), eid("company"), eid("owner"), value)


@pytest.mark.parametrize("value", [True, 1.0, 999_999, 1_000_001])
def test_company_has_the_declared_fixed_equity_denominator(value):
    with pytest.raises(ValueError):
        Company(eid("company"), value)


@pytest.mark.parametrize("field", ["cultivation_level", "rebirth", "system", "magic"])
def test_realistic_business_schema_rejects_fantasy_fields(field):
    document = sample().to_dict()
    document["companies"][0][field] = 1
    assert list(
        Draft202012Validator(json.loads(BUSINESS_SCHEMA_BYTES)).iter_errors(document)
    )
    with pytest.raises(ValueError):
        BusinessState.from_dict(document)


def test_business_fact_codec_uses_closed_individual_scalars_and_retains_identity():
    state = sample()
    encoded = state.to_facts("root-business-source")
    assert encoded == state.to_facts("root-business-source")
    assert len({f.id for f in encoded}) == len(encoded)
    assert len(
        {(f.proposition.subject, f.proposition.predicate) for f in encoded}
    ) == len(encoded)
    assert all(
        f.proposition.predicate.startswith("ext:urban.business:") for f in encoded
    )
    assert all(type(f.proposition.value) in (str, int) for f in encoded)
    assert not any(
        isinstance(f.proposition.value, str) and f.proposition.value.startswith("{")
        for f in encoded
    )
    registered_extensions().validate_root(
        PROJECT, baseline().extensions, encoded, entity_ids(state)
    )


def test_root_and_baseline_version_binding_roundtrip_retains_complete_sources():
    state = sample()
    frozen = baseline()
    binding = frozen.extensions[0]
    entities = tuple(Entity(i, i.local_id) for i in entity_ids(state))
    seed = RootSeed(entities, (), state.to_facts("root-source"), extensions=(binding,))
    assert seed.to_dict()["schema_version"] == "1.1"
    assert RootSeed.from_dict(seed.to_dict()) == seed
    assert frozen.to_dict()["schema_version"] == "1.1"
    assert FactBaseline.from_dict(frozen.to_dict()) == frozen
    assert ExtensionBinding.from_dict(binding.to_dict()) == binding
    assert binding.pack_bytes == canonical_bytes(pack().to_dict())
    assert binding.schema_bytes == BUSINESS_SCHEMA_BYTES
    assert set(binding.entity_ids) == {e.id for e in seed.entities}


def test_legacy_pack_and_empty_binding_formats_remain_original_one_point_zero():
    old = pack(version="1.0.0")
    assert old.pack.extensions == ()
    assert (
        old.ref.content_hash
        == "8cdcad278b40f570487ac31f2ef6340e68329943098863776f6048ebd1cda061"
    )
    entity = Entity(eid("person"), "普通人物")
    world_fact = WorldFact(
        eid("ordinary"), Proposition(entity.id, "occupation", "采购"), "root"
    )
    seed = RootSeed((entity,), (), (world_fact,))
    state = FactBaseline.from_world_facts(PROJECT, BRANCH, PARENT, seed.facts)
    assert (
        seed.to_dict()["schema_version"] == state.to_dict()["schema_version"] == "1.0"
    )
    assert "extensions" not in seed.to_dict() and "extensions" not in state.to_dict()
    with pytest.raises(ValueError):
        create_business_binding(old, (entity.id,))


def test_retained_project_binding_is_restored_without_current_catalog_access(
    monkeypatch,
):
    original = pack()
    record = original.to_dict()
    with monkeypatch.context() as isolated:
        isolated.setattr(
            Path,
            "read_bytes",
            lambda _path: pytest.fail("Offline binding must use retained bytes"),
        )
        restored = ProjectGenreBinding.from_dict(record)
    assert restored == original
    assert restored.pack.manifest_bytes == original.pack.manifest_bytes
    assert (
        create_business_binding(restored, entity_ids(sample()))
        == baseline().extensions[0]
    )


@pytest.mark.parametrize("anchor,version", [(URBAN, "1.0.0"), (FANTASY, "1.0.0")])
def test_unregistered_or_other_anchor_cannot_claim_business_support(anchor, version):
    with pytest.raises(ValueError):
        create_business_binding(
            pack(anchor=anchor, version=version), entity_ids(sample())
        )


@pytest.mark.parametrize(
    "mechanism", [Mechanism.CULTIVATION, Mechanism.REBIRTH, Mechanism.SYSTEM]
)
def test_new_business_pack_keeps_realistic_world_mechanism_prohibitions(mechanism):
    document = SourceDocument(eid("prose"), "她在现实世界确实获得了超现实能力。")
    claim = SemanticClaim(
        "world-claim",
        mechanism,
        ClaimContext.WORLD,
        Occurrence.OCCURRED,
        EvidenceSpan(
            document.id, document.content_hash, 0, len(document.text), document.text
        ),
        "fixture:explicit-world-interpretation",
    )
    result = GenrePolicy(pack()).check(document, (claim,))
    assert result.status is PolicyStatus.FAIL
    assert result.prose_coverage == "NOT_VERIFIED"


@pytest.mark.parametrize(
    "fn,source,target,amount,field,expected",
    [
        (
            transfer_cash,
            "account-a",
            "account-b",
            250,
            "account.balance_minor",
            (9750, 250),
        ),
        (
            transfer_shares,
            "share-a",
            "share-b",
            50_000,
            "share.parts",
            (650_000, 350_000),
        ),
        (transfer_resource, "stock-a", "stock-b", 3, "resource.quantity", (5, 5)),
    ],
)
def test_legal_typed_transfers_reduce_existing_facts_atomically(
    fn, source, target, amount, field, expected
):
    before = baseline()
    original = before.to_dict()
    delta = transfer(before, fn, source, target, amount)
    assert len(delta.operations) == 2 and all(
        type(op) is SetFact for op in delta.operations
    )
    after = preview(before, delta).candidate
    assert (
        fact(after, source, field).state.value,
        fact(after, target, field).state.value,
    ) == expected
    assert after.extensions == before.extensions
    assert before.to_dict() == original
    assert BusinessState.from_baseline(after)


@pytest.mark.parametrize(
    "fn,source,target,available",
    [
        (transfer_cash, "account-a", "account-b", 10_000),
        (transfer_shares, "share-a", "share-b", 700_000),
        (transfer_resource, "stock-a", "stock-b", 8),
    ],
)
@pytest.mark.parametrize("amount", [0, -1, True, 1.0, None])
def test_transfer_builder_rejects_nonpositive_or_coerced_amount(
    fn, source, target, available, amount
):
    with pytest.raises(ValueError):
        transfer(baseline(), fn, source, target, amount)


@pytest.mark.parametrize(
    "fn,source,target,amount",
    [
        (transfer_cash, "account-a", "account-b", 10_001),
        (transfer_shares, "share-a", "share-b", 700_001),
        (transfer_resource, "stock-a", "stock-b", 9),
    ],
)
def test_transfer_requires_sufficient_source_resources(fn, source, target, amount):
    with pytest.raises(ValueError):
        transfer(baseline(), fn, source, target, amount)


@pytest.mark.parametrize(
    "fn,source,target",
    [
        (transfer_cash, "account-a", "account-a"),
        (transfer_shares, "share-a", "share-a"),
        (transfer_resource, "stock-a", "stock-a"),
    ],
)
def test_transfer_cannot_target_itself(fn, source, target):
    with pytest.raises(ValueError):
        transfer(baseline(), fn, source, target, 1)


def test_cash_transfer_does_not_silently_exchange_currency():
    state = sample()
    state = replace(
        state, accounts=(state.accounts[0], replace(state.accounts[1], currency="USD"))
    )
    with pytest.raises(ValueError):
        transfer(baseline(state), transfer_cash, "account-a", "account-b", 1)


@pytest.mark.parametrize(
    "field,value", [("unit", "box"), ("resource", "different-widget")]
)
def test_resource_transfer_does_not_convert_units_or_resource_identity(field, value):
    state = sample()
    state = replace(
        state,
        resources=(state.resources[0], replace(state.resources[1], **{field: value})),
    )
    with pytest.raises(ValueError):
        transfer(baseline(state), transfer_resource, "stock-a", "stock-b", 1)


@pytest.mark.parametrize(
    "field,subject",
    [
        ("account.balance_minor", "account-a"),
        ("share.parts", "share-a"),
        ("resource.quantity", "stock-a"),
    ],
)
def test_native_set_fact_cannot_mint_or_destroy_resources_with_partial_transfer(
    field, subject
):
    before = baseline()
    target = fact(before, subject, field)
    with pytest.raises(ValueError):
        preview(before, delta_with(before, [(target, target.state.value - 1)]))
    assert BusinessState.from_baseline(before) == sample()


@pytest.mark.parametrize("operation", [MarkUnknown, RetractFact])
@pytest.mark.parametrize(
    "field,subject",
    [
        ("account.balance_minor", "account-a"),
        ("share.parts", "share-a"),
        ("resource.quantity", "stock-a"),
    ],
)
def test_native_unknown_or_retraction_cannot_remove_resource_preconditions(
    operation, field, subject
):
    before = baseline()
    with pytest.raises(ValueError):
        preview(
            before,
            delta_with(before, [(fact(before, subject, field), None)], operation),
        )


@pytest.mark.parametrize(
    "field,subject,value",
    [
        ("account.owner", "account-a", "bob"),
        ("account.currency", "account-a", "USD"),
        ("resource.unit", "stock-a", "box"),
        ("share.company", "share-a", "alice"),
    ],
)
def test_native_set_fact_cannot_rewrite_registered_metadata(field, subject, value):
    before = baseline()
    with pytest.raises(ValueError):
        preview(before, delta_with(before, [(fact(before, subject, field), value)]))


def test_empty_registry_and_missing_binding_fail_closed_for_reserved_facts():
    before = baseline()
    delta = transfer(before, transfer_cash, "account-a", "account-b", 1)
    with pytest.raises(ValueError):
        preview(before, delta, ExtensionRegistry())
    unbound = replace(before, extensions=())
    with pytest.raises(ValueError):
        preview(unbound, delta)
    with pytest.raises(ValueError):
        BusinessState.from_baseline(unbound)


def test_ordinary_only_baseline_cannot_be_misrepresented_as_registered_business_state():
    ordinary = WorldFact(
        eid("job-fact"), Proposition(eid("alice"), "occupation", "采购"), "manual-root"
    )
    state = FactBaseline.from_world_facts(PROJECT, BRANCH, PARENT, (ordinary,))
    with pytest.raises(ValueError):
        BusinessState.from_baseline(state)


@pytest.mark.parametrize(
    "change",
    [
        {"namespace": "unknown.extension"},
        {"version": "99.0.0"},
        {"schema_id": "unknown-schema"},
        {"pack_version": "99.0.0"},
        {"pack_hash": "0" * 64},
        {"schema_hash": "0" * 64},
        {"pack_bytes": b"{}"},
        {"schema_bytes": b"{}"},
    ],
)
def test_binding_version_schema_and_retained_content_are_not_self_approval(change):
    before = baseline()
    with pytest.raises(ValueError):
        bad = replace(before, extensions=(replace(before.extensions[0], **change),))
        registered_extensions().validate_baseline(bad)


def test_registered_state_rejects_duplicate_predicate_even_with_distinct_fact_id():
    before = baseline()
    duplicate = replace(
        before.facts[0],
        seed_fact=replace(before.facts[0].seed_fact, id=eid("duplicate-fact")),
    )
    with pytest.raises(ValueError):
        registered_extensions().validate_baseline(
            replace(before, facts=before.facts + (duplicate,))
        )


def test_registered_root_requires_actual_entities_for_all_business_references():
    before = baseline()
    root_facts = tuple(f.seed_fact for f in before.facts)
    owner = next(
        f
        for f in root_facts
        if f.proposition.predicate == "ext:urban.business:account.owner"
    )
    bad = replace(
        owner, proposition=replace(owner.proposition, value="unregistered-person")
    )
    with pytest.raises(ValueError):
        registered_extensions().validate_root(
            PROJECT,
            before.extensions,
            tuple(bad if f.id == owner.id else f for f in root_facts),
            entity_ids(sample()),
        )


def test_cross_project_records_and_transfers_are_refused():
    with pytest.raises(ValueError):
        CashAccount(eid("account"), eid("alice", "other-book"), "CNY", 1)
    before = baseline()
    with pytest.raises(ValueError):
        transfer_cash(
            before,
            eid("account-a"),
            eid("account-b", "other-book"),
            1,
            delta_id=eid("delta"),
            evidence=evidence(),
            authorization_ref=AUTH,
        )


def test_non_business_fact_still_uses_original_finite_delta_path():
    ordinary = WorldFact(
        eid("job-fact"), Proposition(eid("alice"), "occupation", "采购"), "manual-root"
    )
    before = baseline(extra_facts=(ordinary,))
    target = before.get(ordinary.id)
    assert target is not None
    after = preview(before, delta_with(before, [(target, "经理")])).candidate
    assert after.get(ordinary.id).state.value == "经理"
    assert BusinessState.from_baseline(after) == sample()


def test_business_values_and_exported_records_are_immutable():
    state = sample()
    original = state.to_dict()
    exported = state.to_dict()
    exported["accounts"][0]["balance_minor"] = 0
    exported["holdings"].clear()
    assert state.to_dict() == original
    with pytest.raises((FrozenInstanceError, AttributeError)):
        state.accounts[0].balance_minor = 0
