"""Fantasy progression through real PostgreSQL and the sole Canon service.

The fixture issuer is isolated TEST authority. No production Permit, live model,
whole-prose Q2, human literary judgement or external backup is claimed here.
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
from anovel.genre.registry import GenreRegistry, PackRef

__all__ = ["admin_engine", "database", "engine"]
SOURCE = Path(__file__).resolve().parents[2] / "specs/genres"
PROSE = "她先向商会购得灵石，再按既定前提付出代价，修行与能力变化有据可查。".encode()


def eid(value):
    return EntityId(PROJECT, value)


def progression_pack(anchor="fantasy.eastern.progression", version="1.1.0"):
    rows = json.loads((SOURCE / "registry.yaml").read_text())["packs"]
    row = next(r for r in rows if r["id"] == anchor and r["version"] == version)
    return GenreRegistry.from_directory(SOURCE).bind(
        PROJECT, PackRef(row["id"], row["version"], row["content_hash"])
    )


def root_seed(*, learned=False):
    state = ProgressionState(
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
            ProgressionResource(eid("pool-alice"), eid("alice"), "灵石", "颗", 20, 0),
            ProgressionResource(eid("pool-bob"), eid("bob"), "灵石", "颗", 20, 0),
            ProgressionResource(eid("pool-guild"), eid("商会"), "灵石", "颗", 10, 0),
        ),
    )
    names = (
        "realm-0",
        "realm-1",
        "realm-2",
        "alice",
        "bob",
        "step",
        "ability-alice",
        "ability-bob",
        "pool-alice",
        "pool-bob",
        "pool-guild",
        "商会",
    )
    ids = tuple(eid(n) for n in names)
    binding = create_progression_binding(progression_pack(), ids)
    ordinary = WorldFact(
        eid("ordinary"), Proposition(eid("alice"), "occupation", "商人"), "manual-root"
    )
    return RootSeed(
        tuple(Entity(i, i.local_id) for i in ids),
        (),
        state.to_facts("manual-fantasy-root") + (ordinary,),
        extensions=(binding,),
    )


def ready_progression(engine, *, learned=False):
    service = CanonCommitService(engine, test_database=engine.url.database)
    service.provision(PROJECT, BRANCH, ACTOR)
    ticket = service.begin_root(PROJECT, BRANCH, ACTOR, "root-progression")
    seed = root_seed(learned=learned)
    receipt = service.initialize_root(
        ticket, seed, "人工给定的玄幻初始事实，不是正式故事书。".encode()
    )
    service.configure_chapter_authority(PROJECT, BRANCH, ACTOR, ISSUER, "TEST-POLICY-1")
    issuer = ProtectedPermitIssuer(
        engine, test_database=engine.url.database, issuer_id=ISSUER
    )
    return service, issuer, receipt, seed


def evidence(name, chapter=1):
    return ProseEvidence(eid(name), NarrativePosition(chapter, 1), "fixture:prose/1")


def dependencies(binding):
    return tuple(
        CandidateEvidence(
            kind,
            binding.pack_bytes if kind == "PACK" else ("fixture " + kind).encode(),
            "test/" + kind.lower(),
            "1.0",
            "v2016-integration-fixture",
            "1.0",
        )
        for kind in ("CONTRACT", "PACK", "MODEL", "CONTEXT")
    )


def candidate(service, parent, kind="advance", *, name="chapter-1", chapter=1):
    before = service.load_baseline(PROJECT, BRANCH, parent)
    opts = {
        "delta_id": eid(name + "-delta"),
        "evidence": evidence(name, chapter),
        "authorization_ref": AUTHORIZATION,
    }
    if kind == "trade":
        delta = transfer_resource(
            before, eid("pool-alice"), eid("pool-guild"), 3, **opts
        )
    else:
        fn, target = {
            "advance": (advance_realm, "alice"),
            "learn": (learn_ability, "ability-alice"),
            "use": (use_ability, "ability-alice"),
        }[kind]
        delta = fn(before, eid(target), **opts)
    return ChapterCandidate(
        eid(name),
        BRANCH,
        parent,
        chapter,
        PROSE,
        delta,
        dependencies(before.extensions[0]),
    )


def raw_candidate(service, parent, changes, *, operation=SetFact, name="raw-chapter"):
    before = service.load_baseline(PROJECT, BRANCH, parent)
    ops = []
    for i, (subject, field, value) in enumerate(changes):
        target = next(
            f
            for f in before.facts
            if f.seed_fact.proposition.subject == eid(subject)
            and f.seed_fact.proposition.predicate.rsplit(".", 1)[-1] == field
        )
        meta = OperationMeta(
            eid(name + "-op-" + str(i)),
            target.seed_fact.id,
            FactPath.VALUE,
            Precondition.from_snapshot(target),
            evidence(name),
            AUTHORIZATION,
        )
        ops.append(operation(meta, value) if operation is SetFact else operation(meta))
    delta = NarrativeDelta(eid(name + "-delta"), BRANCH, parent, eid(name), tuple(ops))
    return ChapterCandidate(
        eid(name), BRANCH, parent, 1, PROSE, delta, dependencies(before.extensions[0])
    )


def accept(service, issuer, parent, proposal, request="request-1"):
    ticket = service.begin_chapter(PROJECT, BRANCH, ACTOR, request, parent)
    permit = issuer.issue(ticket, proposal)
    return ticket, permit, service.commit(ticket, proposal, permit)


def resource(state, local_id="pool-alice"):
    return next(v for v in state.resources if v.id == eid(local_id))


@pytest.mark.parametrize(
    "kind,learned,quantity,spent",
    [
        ("advance", False, 15, 5),
        ("learn", False, 17, 3),
        ("use", True, 18, 2),
        ("trade", False, 17, 0),
    ],
)
def test_frozen_fantasy_actions_commit_read_back_and_replay_in_real_postgres(
    engine, kind, learned, quantity, spent
):
    service, issuer, root, seed = ready_progression(engine, learned=learned)
    proposal = candidate(service, root.commit_id, kind)
    _ticket, _permit, receipt = accept(service, issuer, root.commit_id, proposal)
    accepted = service.load_commit(PROJECT, BRANCH, receipt.commit_id)
    current = service.load_baseline(PROJECT, BRANCH, receipt.commit_id)
    rebuilt = service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id)
    state = ProgressionState.from_baseline(current)
    assert (resource(state).quantity, resource(state).spent) == (quantity, spent)
    assert current == rebuilt.baseline
    # Stored state belongs to the submitted parent; read views are re-anchored
    # to the accepted commit for the following proposal. All fact data agrees.
    assert accepted.state.parent_ref == root.commit_id
    assert replace(accepted.state, parent_ref=receipt.commit_id) == current
    assert current.extensions == seed.extensions
    assert rebuilt.receipt == accepted.receipt == receipt
    assert len(rebuilt.checkpoints) == 2
    assert canonical_bytes(
        service.load_root(PROJECT, BRANCH, root.commit_id).seed.to_dict()
    ) == canonical_bytes(seed.to_dict())
    assert accepted.candidate.prose == PROSE


def test_progression_learning_and_repeated_use_persist_costs_at_distinct_parents(
    engine, monkeypatch
):
    service, issuer, root, seed = ready_progression(engine)
    proposal1 = candidate(service, root.commit_id, "advance")
    _ticket, _permit, first = accept(service, issuer, root.commit_id, proposal1)
    proposal2 = candidate(
        service, first.commit_id, "learn", name="chapter-2", chapter=2
    )
    _ticket, _permit, second = accept(
        service, issuer, first.commit_id, proposal2, "request-2"
    )
    proposal3 = candidate(service, second.commit_id, "use", name="chapter-3", chapter=3)
    _ticket, _permit, third = accept(
        service, issuer, second.commit_id, proposal3, "request-3"
    )
    before = counts(engine)
    frozen = create_engine(engine.url)
    try:
        with monkeypatch.context() as isolated:
            isolated.setattr(
                GenreRegistry,
                "from_directory",
                lambda *args: pytest.fail("Cold replay must use frozen sources"),
            )
            reader = CanonCommitService(frozen)
            earlier = reader.rebuild_snapshot(PROJECT, BRANCH, first.commit_id)
            final = reader.rebuild_snapshot(PROJECT, BRANCH, third.commit_id)
            first_state = ProgressionState.from_baseline(earlier.baseline)
            final_state = ProgressionState.from_baseline(final.baseline)
            assert (resource(first_state).quantity, resource(first_state).spent) == (
                15,
                5,
            )
            assert (resource(final_state).quantity, resource(final_state).spent) == (
                10,
                10,
            )
            assert (
                next(
                    v
                    for v in final_state.ability_states
                    if v.id == eid("ability-alice")
                ).uses
                == 1
            )
            assert final.baseline.extensions == seed.extensions
            assert len(earlier.checkpoints) == 2 and len(final.checkpoints) == 4
    finally:
        frozen.dispose()
    unchanged(engine, before, third.commit_id)


def test_fantasy_same_request_restores_original_receipt_after_authority_revocation(
    engine,
):
    service, issuer, root, _seed = ready_progression(engine)
    proposal = candidate(service, root.commit_id)
    ticket, permit, receipt = accept(service, issuer, root.commit_id, proposal)
    service.revoke_chapter_authority(PROJECT, BRANCH, ACTOR)
    before = counts(engine)
    assert service.commit(ticket, proposal, permit) == receipt
    unchanged(engine, before, receipt.commit_id)


def test_fantasy_same_key_different_action_is_not_duplicate_success(engine):
    service, issuer, root, _seed = ready_progression(engine)
    proposal = candidate(service, root.commit_id)
    ticket, permit, receipt = accept(service, issuer, root.commit_id, proposal)
    different = candidate(service, root.commit_id, "learn")
    before = counts(engine)
    with pytest.raises(CanonConflict):
        service.commit(ticket, different, permit)
    unchanged(engine, before, receipt.commit_id)


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
        [
            ("ability-alice", "learned", True),
            ("ability-alice", "uses", 1),
            ("pool-alice", "quantity", 15),
            ("pool-alice", "spent", 5),
        ],
        [("realm-1", "breakthrough_cost", 1)],
        [("pool-alice", "quantity", 21)],
    ],
)
def test_native_fantasy_delta_cannot_obtain_permit_or_partially_mutate_canon(
    engine, changes
):
    service, issuer, root, _seed = ready_progression(engine)
    proposal = raw_candidate(service, root.commit_id, changes)
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
def test_unknown_and_retraction_cannot_erase_fantasy_resource_cost_preconditions(
    engine, operation
):
    service, issuer, root, _seed = ready_progression(engine)
    proposal = raw_candidate(
        service, root.commit_id, [("pool-alice", "quantity", None)], operation=operation
    )
    ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "unknown-cost", root.commit_id
    )
    before = counts(engine)
    with pytest.raises(ValueError):
        issuer.issue(ticket, proposal)
    unchanged(engine, before, root.commit_id)


@pytest.mark.parametrize("wrong", ["legacy", "business", "identity-only"])
def test_fantasy_pack_dependency_is_full_exact_root_source_not_claimed_label(
    engine, wrong
):
    service, issuer, root, _seed = ready_progression(engine)
    proposal = candidate(service, root.commit_id)
    alternatives = {
        "legacy": canonical_bytes(progression_pack(version="1.0.0").to_dict()),
        "business": canonical_bytes(
            progression_pack(anchor="urban.business.realistic").to_dict()
        ),
        "identity-only": canonical_bytes(progression_pack().ref.to_dict()),
    }
    proposal = replace(
        proposal,
        dependencies=tuple(
            replace(d, content=alternatives[wrong]) if d.kind == "PACK" else d
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
        "negative-resource",
        "float-resource",
        "unknown-owner",
        "missing-binding",
        "modern-equity",
        "duplicate-fact",
    ],
)
def test_invalid_fantasy_root_never_writes_partial_story_history(engine, fault):
    service = CanonCommitService(engine, test_database=engine.url.database)
    service.provision(PROJECT, BRANCH, ACTOR)
    ticket = service.begin_root(PROJECT, BRANCH, ACTOR, "bad-root")
    seed = root_seed()
    facts = list(seed.facts)
    if fault in {"negative-resource", "float-resource", "unknown-owner"}:
        field, value = {
            "negative-resource": ("resource.quantity", -1),
            "float-resource": ("resource.quantity", 20.0),
            "unknown-owner": ("resource.owner", "not-root-entity"),
        }[fault]
        i = next(
            i
            for i, f in enumerate(facts)
            if f.proposition.predicate == "ext:fantasy.progression:" + field
        )
        facts[i] = replace(
            facts[i], proposition=replace(facts[i].proposition, value=value)
        )
    elif fault == "modern-equity":
        facts.append(
            WorldFact(
                eid("company-shares"),
                Proposition(
                    eid("alice"), "ext:fantasy.progression:company.shares", 100
                ),
                "manual-root",
            )
        )
    elif fault == "duplicate-fact":
        facts.append(replace(facts[0], id=eid("duplicate")))
    before = counts(engine)
    with pytest.raises(ValueError):
        invalid = replace(
            seed,
            facts=tuple(facts),
            extensions=() if fault == "missing-binding" else seed.extensions,
        )
        service.initialize_root(ticket, invalid, b"invalid root fixture")
    unchanged(engine, before, None)


def test_stale_progression_cost_preconditions_are_not_rebound_to_new_parent(engine):
    service, issuer, root, _seed = ready_progression(engine)
    proposal = candidate(service, root.commit_id)
    _ticket, _permit, receipt = accept(service, issuer, root.commit_id, proposal)
    stale = replace(
        proposal,
        parent_ref=receipt.commit_id,
        delta=replace(proposal.delta, parent_ref=receipt.commit_id),
    )
    ticket = service.begin_chapter(PROJECT, BRANCH, ACTOR, "stale", receipt.commit_id)
    before = counts(engine)
    with pytest.raises(ValueError):
        issuer.issue(ticket, stale)
    unchanged(engine, before, receipt.commit_id)


def test_production_and_cancelled_requests_cannot_consume_fixture_fantasy_permit(
    engine,
):
    service, issuer, root, _seed = ready_progression(engine)
    proposal = candidate(service, root.commit_id)
    ticket = service.begin_chapter(PROJECT, BRANCH, ACTOR, "cancelled", root.commit_id)
    permit = issuer.issue(ticket, proposal)
    before = counts(engine)
    with pytest.raises(CanonPermissionError):
        CanonCommitService(engine).commit(ticket, proposal, permit)
    assert service.cancel(ticket) is None
    with pytest.raises(CanonPermissionError):
        service.commit(ticket, proposal, permit)
    unchanged(engine, before, root.commit_id)


def test_guild_trade_and_ability_learning_share_one_atomic_validated_chapter(engine):
    service, issuer, root, _seed = ready_progression(engine)
    proposal = raw_candidate(
        service,
        root.commit_id,
        [
            ("ability-alice", "learned", True),
            ("pool-alice", "quantity", 12),
            ("pool-alice", "spent", 3),
            ("pool-guild", "quantity", 15),
        ],
    )
    _ticket, _permit, receipt = accept(service, issuer, root.commit_id, proposal)
    final = ProgressionState.from_baseline(
        service.load_baseline(PROJECT, BRANCH, receipt.commit_id)
    )
    assert (resource(final).quantity, resource(final).spent) == (12, 3)
    assert resource(final, "pool-guild").quantity == 15
    assert resource(final, "pool-guild").spent == 0
    assert counts(engine)["commits"] == 2


def test_ordinary_quiet_chapter_needs_no_upgrade_or_resource_spend(engine):
    service, issuer, root, _seed = ready_progression(engine)
    proposal = raw_candidate(service, root.commit_id, [("alice", "occupation", "掌柜")])
    _ticket, _permit, receipt = accept(service, issuer, root.commit_id, proposal)
    final = service.load_baseline(PROJECT, BRANCH, receipt.commit_id)
    assert final.get(eid("ordinary")).state.value == "掌柜"
    assert (
        resource(ProgressionState.from_baseline(final)).quantity,
        resource(ProgressionState.from_baseline(final)).spent,
    ) == (20, 0)
    assert (
        service.rebuild_snapshot(PROJECT, BRANCH, receipt.commit_id).baseline == final
    )
