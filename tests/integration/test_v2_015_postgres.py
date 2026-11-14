"""Business conservation through actual isolated PostgreSQL Canon commits.

All story contents use the sole CanonCommitService. The existing test issuer
remains explicitly isolated: these tests do not authorize production Q0-Q3,
model generation, literary certification, or external backup recovery.
"""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from test_v2_010 import (
    ACTOR,
    AUTHORIZATION,
    BRANCH,
    ISSUER,
    PROJECT,
    admin_engine,
    counts,
    database,
    engine,
    unchanged,
)

from anovel.canon.chapter import CandidateEvidence, ChapterCandidate
from anovel.canon.commit_service import CanonCommitService, ProtectedPermitIssuer
from anovel.canon.identity import canonical_bytes
from anovel.canon.models import CanonConflict, CanonPermissionError, RootSeed
from anovel.domain.delta import (
    FactPath,
    MarkUnknown,
    NarrativeDelta,
    OperationMeta,
    Precondition,
    ProseEvidence,
    RetractFact,
    SetFact,
)
from anovel.domain.events import NarrativePosition
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
from anovel.genre.registry import GenreRegistry, PackRef

# Import shared DB fixtures without importing old test functions for collection.
__all__ = ["admin_engine", "database", "engine"]
SOURCE = Path(__file__).resolve().parents[2] / "specs/genres"
PROSE = "双方确认本次交易，价款与资源按约定流转，股权变化保留了原始依据。".encode(
    "utf-8"
)


def eid(value):
    return EntityId(PROJECT, value)


def business_pack(version="1.1.0"):
    rows = json.loads((SOURCE / "registry.yaml").read_text())["packs"]
    row = next(
        r
        for r in rows
        if r["id"] == "urban.business.realistic" and r["version"] == version
    )
    return GenreRegistry.from_directory(SOURCE).bind(
        PROJECT, PackRef(row["id"], row["version"], row["content_hash"])
    )


def root_seed():
    company, alice, bob = (eid(s) for s in ("company", "alice", "bob"))
    state = BusinessState(
        (Company(company),),
        (
            CashAccount(eid("account-a"), alice, "CNY", 10_000),
            CashAccount(eid("account-b"), bob, "CNY", 0),
        ),
        (
            ShareHolding(eid("share-a"), company, alice, 700_000),
            ShareHolding(eid("share-b"), company, bob, 300_000),
        ),
        (
            ResourceHolding(eid("stock-a"), alice, "widget", "piece", 8),
            ResourceHolding(eid("stock-b"), bob, "widget", "piece", 2),
        ),
    )
    ids = tuple(
        eid(s)
        for s in (
            "company",
            "alice",
            "bob",
            "account-a",
            "account-b",
            "share-a",
            "share-b",
            "stock-a",
            "stock-b",
        )
    )
    binding = create_business_binding(business_pack(), ids)
    ordinary = WorldFact(
        eid("job-fact"), Proposition(alice, "occupation", "采购"), "manual-root"
    )
    return RootSeed(
        tuple(Entity(i, i.local_id) for i in ids),
        (),
        state.to_facts("manual-business-root") + (ordinary,),
        extensions=(binding,),
    )


def ready_business(engine):
    service = CanonCommitService(engine, test_database=engine.url.database)
    service.provision(PROJECT, BRANCH, ACTOR)
    ticket = service.begin_root(PROJECT, BRANCH, ACTOR, "root-business")
    seed = root_seed()
    receipt = service.initialize_root(
        ticket, seed, "人工给定的商业故事初始事实。".encode()
    )
    service.configure_chapter_authority(PROJECT, BRANCH, ACTOR, ISSUER, "TEST-POLICY-1")
    issuer = ProtectedPermitIssuer(
        engine, test_database=engine.url.database, issuer_id=ISSUER
    )
    return service, issuer, receipt, seed


def evidence(name):
    return ProseEvidence(eid(name), NarrativePosition(1, 1), "fixture:prose/1")


def dependencies(binding, pack_bytes=None):
    return tuple(
        CandidateEvidence(
            kind,
            (binding.pack_bytes if pack_bytes is None else pack_bytes)
            if kind == "PACK"
            else ("fixture " + kind).encode(),
            "test/" + kind.lower(),
            "1.0",
            "v2015-integration-fixture",
            "1.0",
        )
        for kind in ("CONTRACT", "PACK", "MODEL", "CONTEXT")
    )


def transfer_candidate(service, parent, kind="cash", *, name="chapter-1", amount=None):
    baseline = service.load_baseline(PROJECT, BRANCH, parent)
    fn, source, target, default = {
        "cash": (transfer_cash, "account-a", "account-b", 250),
        "shares": (transfer_shares, "share-a", "share-b", 50_000),
        "resource": (transfer_resource, "stock-a", "stock-b", 3),
    }[kind]
    delta = fn(
        baseline,
        eid(source),
        eid(target),
        default if amount is None else amount,
        delta_id=eid(name + "-delta"),
        evidence=evidence(name),
        authorization_ref=AUTHORIZATION,
    )
    return ChapterCandidate(
        eid(name), BRANCH, parent, 1, PROSE, delta, dependencies(baseline.extensions[0])
    )


def raw_candidate(
    service, parent, field, value, *, operation=SetFact, name="raw-chapter"
):
    baseline = service.load_baseline(PROJECT, BRANCH, parent)
    target = next(
        f for f in baseline.facts if f.seed_fact.proposition.predicate == field
    )
    meta = OperationMeta(
        eid(name + "-op"),
        target.seed_fact.id,
        FactPath.VALUE,
        Precondition.from_snapshot(target),
        evidence(name),
        AUTHORIZATION,
    )
    change = operation(meta, value) if operation is SetFact else operation(meta)
    delta = NarrativeDelta(eid(name + "-delta"), BRANCH, parent, eid(name), (change,))
    return ChapterCandidate(
        eid(name), BRANCH, parent, 1, PROSE, delta, dependencies(baseline.extensions[0])
    )


def accept(service, issuer, parent, proposal, request="request-1"):
    ticket = service.begin_chapter(PROJECT, BRANCH, ACTOR, request, parent)
    permit = issuer.issue(ticket, proposal)
    return ticket, permit, service.commit(ticket, proposal, permit)


@pytest.mark.parametrize(
    "kind,collection,field,expected",
    [
        ("cash", "accounts", "balance_minor", (9750, 250)),
        ("shares", "holdings", "parts", (650_000, 350_000)),
        ("resource", "resources", "quantity", (5, 5)),
    ],
)
def test_registered_transfer_commits_reads_and_rebuilds_in_real_postgres(
    engine, kind, collection, field, expected
):
    service, issuer, root, seed = ready_business(engine)
    proposal = transfer_candidate(service, root.commit_id, kind)
    _ticket, _permit, receipt = accept(service, issuer, root.commit_id, proposal)
    accepted = service.load_commit(PROJECT, BRANCH, receipt.commit_id)
    current = service.load_baseline(PROJECT, BRANCH, receipt.commit_id)
    rebuilt = service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id)
    state = BusinessState.from_baseline(current)
    assert tuple(getattr(v, field) for v in getattr(state, collection)) == expected
    assert (
        current.extensions
        == accepted.state.extensions
        == rebuilt.baseline.extensions
        == seed.extensions
    )
    assert BusinessState.from_baseline(rebuilt.baseline) == state
    assert rebuilt.receipt == accepted.receipt == receipt
    assert len(rebuilt.checkpoints) == 2
    assert canonical_bytes(
        service.load_root(PROJECT, BRANCH, root.commit_id).seed.to_dict()
    ) == canonical_bytes(seed.to_dict())
    assert accepted.candidate.prose == PROSE


def test_cold_reader_uses_retained_pack_schema_and_replays_target_not_future_state(
    engine,
):
    service, issuer, root, seed = ready_business(engine)
    proposal = transfer_candidate(service, root.commit_id)
    _ticket, _permit, first = accept(service, issuer, root.commit_id, proposal)
    second_proposal = transfer_candidate(
        service, first.commit_id, amount=125, name="chapter-2"
    )
    _ticket, _permit, second = accept(
        service, issuer, first.commit_id, second_proposal, "request-2"
    )
    before = counts(engine)
    fresh = create_engine(engine.url)
    try:
        reader = CanonCommitService(fresh)
        restored_root = reader.load_root(PROJECT, BRANCH, root.commit_id)
        earlier = reader.rebuild_snapshot(PROJECT, BRANCH, first.commit_id)
        later = reader.rebuild_snapshot(PROJECT, BRANCH, second.commit_id)
        assert restored_root.seed.extensions == seed.extensions
        assert restored_root.seed.extensions[0].pack_bytes == canonical_bytes(
            business_pack().to_dict()
        )
        assert (
            BusinessState.from_baseline(earlier.baseline).accounts[0].balance_minor
            == 9750
        )
        assert (
            BusinessState.from_baseline(later.baseline).accounts[0].balance_minor
            == 9625
        )
        assert len(earlier.checkpoints) == 2 and len(later.checkpoints) == 3
    finally:
        fresh.dispose()
    unchanged(engine, before, second.commit_id)


def test_same_request_recovers_original_receipt_after_head_and_authority_advance(
    engine,
):
    service, issuer, root, _seed = ready_business(engine)
    proposal = transfer_candidate(service, root.commit_id)
    ticket, permit, receipt = accept(service, issuer, root.commit_id, proposal)
    service.revoke_chapter_authority(PROJECT, BRANCH, ACTOR)
    before = counts(engine)
    assert service.commit(ticket, proposal, permit) == receipt
    unchanged(engine, before, receipt.commit_id)


def test_reused_request_cannot_submit_a_different_business_transfer(engine):
    service, issuer, root, _seed = ready_business(engine)
    proposal = transfer_candidate(service, root.commit_id, amount=250)
    ticket, permit, receipt = accept(service, issuer, root.commit_id, proposal)
    alternate = transfer_candidate(service, root.commit_id, amount=500)
    assert alternate.payload_hash != proposal.payload_hash
    before = counts(engine)
    with pytest.raises(CanonConflict):
        service.commit(ticket, alternate, permit)
    unchanged(engine, before, receipt.commit_id)


@pytest.mark.parametrize(
    "field,value",
    [
        ("ext:urban.business:account.balance_minor", 9_999),
        ("ext:urban.business:share.parts", 699_999),
        ("ext:urban.business:resource.quantity", 7),
        ("ext:urban.business:account.currency", "USD"),
        ("ext:urban.business:account.owner", "bob"),
    ],
)
def test_native_delta_cannot_bypass_business_rules_or_leave_partial_canon(
    engine, field, value
):
    service, issuer, root, _seed = ready_business(engine)
    proposal = raw_candidate(service, root.commit_id, field, value)
    ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "invalid-native", root.commit_id
    )
    before = counts(engine)
    review = service.review_submission(ticket, proposal)
    assert review["blockers"] and review["permit_issued"] is False
    with pytest.raises(ValueError):
        issuer.issue(ticket, proposal)
    unchanged(engine, before, root.commit_id)


@pytest.mark.parametrize("operation", [MarkUnknown, RetractFact])
def test_unknown_or_retracted_balance_cannot_obtain_permit(engine, operation):
    service, issuer, root, _seed = ready_business(engine)
    proposal = raw_candidate(
        service,
        root.commit_id,
        "ext:urban.business:account.balance_minor",
        None,
        operation=operation,
    )
    ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "invalid-quantity-state", root.commit_id
    )
    before = counts(engine)
    with pytest.raises(ValueError):
        issuer.issue(ticket, proposal)
    unchanged(engine, before, root.commit_id)


@pytest.mark.parametrize("pack_kind", ["legacy", "id-only", "unretained"])
def test_pack_dependency_must_equal_root_frozen_complete_binding(engine, pack_kind):
    service, issuer, root, _seed = ready_business(engine)
    proposal = transfer_candidate(service, root.commit_id)
    wrong = {
        "legacy": canonical_bytes(business_pack("1.0.0").to_dict()),
        "id-only": canonical_bytes(business_pack().ref.to_dict()),
        "unretained": b"a claimed but unretained Pack",
    }[pack_kind]
    proposal = replace(
        proposal,
        dependencies=tuple(
            replace(d, content=wrong) if d.kind == "PACK" else d
            for d in proposal.dependencies
        ),
    )
    ticket = service.begin_chapter(PROJECT, BRANCH, ACTOR, "wrong-pack", root.commit_id)
    before = counts(engine)
    with pytest.raises(ValueError):
        issuer.issue(ticket, proposal)
    unchanged(engine, before, root.commit_id)


@pytest.mark.parametrize(
    "fault",
    [
        "negative-cash",
        "float-cash",
        "equity-total",
        "unknown-owner",
        "fantasy-field",
        "duplicate-predicate",
        "missing-binding",
    ],
)
def test_invalid_business_root_never_writes_story_history(engine, fault):
    service = CanonCommitService(engine, test_database=engine.url.database)
    service.provision(PROJECT, BRANCH, ACTOR)
    ticket = service.begin_root(PROJECT, BRANCH, ACTOR, "invalid-root")
    seed = root_seed()
    facts = list(seed.facts)
    if fault in {"negative-cash", "float-cash", "equity-total", "unknown-owner"}:
        field, value = {
            "negative-cash": ("account.balance_minor", -1),
            "float-cash": ("account.balance_minor", 10_000.0),
            "equity-total": ("share.parts", 700_001),
            "unknown-owner": ("account.owner", "not-a-root-entity"),
        }[fault]
        index = next(
            i
            for i, f in enumerate(facts)
            if f.proposition.predicate == "ext:urban.business:" + field
        )
        facts[index] = replace(
            facts[index], proposition=replace(facts[index].proposition, value=value)
        )
    elif fault == "fantasy-field":
        facts.append(
            WorldFact(
                eid("fantasy-field"),
                Proposition(
                    eid("company"), "ext:urban.business:company.cultivation_level", 9
                ),
                "manual-root",
            )
        )
    elif fault == "duplicate-predicate":
        facts.append(replace(facts[0], id=eid("duplicate-field")))
    before = counts(engine)
    with pytest.raises(ValueError):
        invalid = replace(
            seed,
            facts=tuple(facts),
            extensions=() if fault == "missing-binding" else seed.extensions,
        )
        service.initialize_root(ticket, invalid, b"invalid business fixture")
    unchanged(engine, before, None)


def test_cancelled_or_production_request_cannot_accept_isolated_business_permit(engine):
    service, issuer, root, _seed = ready_business(engine)
    proposal = transfer_candidate(service, root.commit_id)
    ticket = service.begin_chapter(PROJECT, BRANCH, ACTOR, "cancel-me", root.commit_id)
    permit = issuer.issue(ticket, proposal)
    before = counts(engine)
    production = CanonCommitService(engine)
    with pytest.raises(CanonPermissionError):
        production.commit(ticket, proposal, permit)
    unchanged(engine, before, root.commit_id)
    assert service.cancel(ticket) is None
    with pytest.raises(CanonPermissionError):
        service.commit(ticket, proposal, permit)
    unchanged(engine, before, root.commit_id)


def test_stale_resource_preconditions_are_not_rebound_to_new_parent(engine):
    service, issuer, root, _seed = ready_business(engine)
    proposal = transfer_candidate(service, root.commit_id)
    _ticket, _permit, receipt = accept(service, issuer, root.commit_id, proposal)
    stale = replace(
        proposal,
        parent_ref=receipt.commit_id,
        delta=replace(proposal.delta, parent_ref=receipt.commit_id),
    )
    ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "stale-business", receipt.commit_id
    )
    before = counts(engine)
    with pytest.raises(ValueError):
        issuer.issue(ticket, stale)
    unchanged(engine, before, receipt.commit_id)


def test_ordinary_fact_can_change_without_reading_fantasy_or_corrupting_business_state(
    engine,
):
    service, issuer, root, _seed = ready_business(engine)
    proposal = raw_candidate(service, root.commit_id, "occupation", "经理")
    _ticket, _permit, receipt = accept(service, issuer, root.commit_id, proposal)
    result = service.load_baseline(PROJECT, BRANCH, receipt.commit_id)
    assert result.get(eid("job-fact")).state.value == "经理"
    assert BusinessState.from_baseline(result).accounts[0].balance_minor == 10_000
    assert (
        service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id).baseline == result
    )


def test_cash_and_resource_exchange_is_one_atomic_chapter_commit(engine):
    service, issuer, root, _seed = ready_business(engine)
    before = service.load_baseline(PROJECT, BRANCH, root.commit_id)
    prose = evidence("exchange")
    cash = transfer_cash(
        before,
        eid("account-a"),
        eid("account-b"),
        250,
        delta_id=eid("pay-delta"),
        evidence=prose,
        authorization_ref=AUTHORIZATION,
    )
    goods = transfer_resource(
        before,
        eid("stock-b"),
        eid("stock-a"),
        1,
        delta_id=eid("goods-delta"),
        evidence=prose,
        authorization_ref=AUTHORIZATION,
    )
    delta = NarrativeDelta(
        eid("exchange-delta"),
        BRANCH,
        root.commit_id,
        prose.source_id,
        cash.operations + goods.operations,
    )
    proposal = ChapterCandidate(
        prose.source_id,
        BRANCH,
        root.commit_id,
        1,
        PROSE,
        delta,
        dependencies(before.extensions[0]),
    )
    _ticket, _permit, receipt = accept(service, issuer, root.commit_id, proposal)
    state = BusinessState.from_baseline(
        service.load_baseline(PROJECT, BRANCH, receipt.commit_id)
    )
    assert tuple(a.balance_minor for a in state.accounts) == (9750, 250)
    assert tuple(r.quantity for r in state.resources) == (9, 1)
    assert counts(engine)["commits"] == 2


def test_invalid_resource_leg_prevents_partial_cash_acceptance(engine):
    service, issuer, root, _seed = ready_business(engine)
    before = service.load_baseline(PROJECT, BRANCH, root.commit_id)
    prose = evidence("incomplete-exchange")
    cash = transfer_cash(
        before,
        eid("account-a"),
        eid("account-b"),
        250,
        delta_id=eid("pay-delta"),
        evidence=prose,
        authorization_ref=AUTHORIZATION,
    )
    goods = transfer_resource(
        before,
        eid("stock-b"),
        eid("stock-a"),
        1,
        delta_id=eid("goods-delta"),
        evidence=prose,
        authorization_ref=AUTHORIZATION,
    )
    delta = NarrativeDelta(
        eid("exchange-delta"),
        BRANCH,
        root.commit_id,
        prose.source_id,
        cash.operations + goods.operations[:1],
    )
    proposal = ChapterCandidate(
        prose.source_id,
        BRANCH,
        root.commit_id,
        1,
        PROSE,
        delta,
        dependencies(before.extensions[0]),
    )
    ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "incomplete-exchange", root.commit_id
    )
    prior_counts = counts(engine)
    with pytest.raises(ValueError):
        issuer.issue(ticket, proposal)
    unchanged(engine, prior_counts, root.commit_id)
    assert service.load_baseline(PROJECT, BRANCH, root.commit_id) == before
