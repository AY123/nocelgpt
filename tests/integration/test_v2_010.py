"""Real isolated PostgreSQL chapter acceptance through the sole Canon service.

The issuer uses explicit disposable TEST composition; no semantic production
quality checks, network identity provider or production Permit are simulated.
Direct SQL below is limited to schema-upgrade setup and negative tamper/failure
probes. Every accepted story is written through CanonCommitService.
"""

import json
import os
import uuid
from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
from importlib.resources import files

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from test_postgres_environment import postgres

from anovel.canon.chapter import CandidateEvidence, ChapterCandidate
from anovel.canon.commit_service import CanonCommitService, ProtectedPermitIssuer
from anovel.canon.identity import canonical_bytes, utc_timestamp
from anovel.canon.migrations import migrate
from anovel.canon.models import (
    CanonConflict,
    CanonError,
    CanonIntegrityError,
    CanonPermissionError,
    RootSeed,
)
from anovel.canon.repository import Repository
from anovel.domain.delta import (
    FactPath,
    FactState,
    MarkUnknown,
    NarrativeDelta,
    NoChange,
    OperationMeta,
    Precondition,
    ProseEvidence,
    RetractFact,
    SetFact,
)
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import Entity, EntityId
from anovel.domain.knowledge import Proposition, WorldFact

PROJECT = "book"
BRANCH = "main"
ACTOR = "owner"
ISSUER = "test-issuer"
AUTHORIZATION = "TEST-AUTHORIZATION-1"
PROSE = "\ufeff甲确认余额变了。\r\n末尾空格  \n".encode()
AUTHORITATIVE = (
    "artifacts",
    "commits",
    "commit_artifacts",
    "events",
    "receipts",
    "entities",
    "relationships",
    "facts",
)


@pytest.fixture(scope="module")
def admin_engine():
    supplied = os.environ.get("ANOVELOS_TEST_DSN")
    if supplied:
        url = make_url(supplied)
        assert url.drivername == "postgresql+psycopg"
        assert url.database == "bootstrap_test", "Disposable test service required"
        engine = create_engine(url, isolation_level="AUTOCOMMIT")
        try:
            yield engine
        finally:
            engine.dispose()
    else:
        with postgres() as (environment, _project):
            engine = create_engine(
                environment["ANOVELOS_TEST_DSN"], isolation_level="AUTOCOMMIT"
            )
            try:
                yield engine
            finally:
                engine.dispose()


@pytest.fixture
def database(admin_engine):
    name = "anovel_test_v2010_" + uuid.uuid4().hex
    quoted = admin_engine.dialect.identifier_preparer.quote(name)
    with admin_engine.connect() as connection:
        connection.exec_driver_sql(f"CREATE DATABASE {quoted}")
    engine = create_engine(admin_engine.url.set(database=name))
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT current_database()")).scalar_one()
                == name
            )
            assert (
                connection.execute(text("SHOW server_version_num")).scalar_one()
                == "170011"
            )
        yield engine
    finally:
        engine.dispose()
        with admin_engine.connect() as connection:
            connection.exec_driver_sql(f"DROP DATABASE {quoted} WITH (FORCE)")
            assert (
                connection.execute(
                    text("SELECT count(*) FROM pg_database WHERE datname=:name"),
                    {"name": name},
                ).scalar_one()
                == 0
            )


@pytest.fixture
def engine(database):
    migrate(database)
    return database


def seed(project=PROJECT):
    entity = Entity(EntityId(project, "alice"), "甲")
    fact = WorldFact(
        EntityId(project, "balance"),
        Proposition(entity.id, "balance", 10),
        "manual-root",
    )
    return RootSeed((entity,), (), (fact,))


def initialize(engine, project=PROJECT, branch=BRANCH):
    service = CanonCommitService(engine, test_database=engine.url.database)
    service.provision(project, branch, ACTOR)
    root_ticket = service.begin_root(project, branch, ACTOR, "root")
    receipt = service.initialize_root(root_ticket, seed(project), b"initial root")
    return service, root_ticket, receipt


def ready(engine):
    service, root_ticket, root = initialize(engine)
    service.configure_chapter_authority(PROJECT, BRANCH, ACTOR, ISSUER, "TEST-POLICY-1")
    issuer = ProtectedPermitIssuer(
        engine, test_database=engine.url.database, issuer_id=ISSUER
    )
    return service, issuer, root_ticket, root


def candidate(
    service, parent, *, name="chapter-1", value=20, operation="set", version=1
):
    source = EntityId(PROJECT, name)
    baseline = service.load_baseline(PROJECT, BRANCH, parent)
    snapshot = baseline.get(EntityId(PROJECT, "balance"))
    assert snapshot is not None
    meta = OperationMeta(
        EntityId(PROJECT, "op-" + name),
        snapshot.seed_fact.id,
        FactPath.VALUE,
        Precondition.from_snapshot(snapshot),
        ProseEvidence(source, NarrativePosition(1, 1), "prose:1"),
        AUTHORIZATION,
    )
    change = {
        "set": lambda: SetFact(meta, value),
        "unknown": lambda: MarkUnknown(meta),
        "retract": lambda: RetractFact(meta),
        "no_change": lambda: NoChange(meta),
    }[operation]()
    delta = NarrativeDelta(
        EntityId(PROJECT, "delta-" + name), BRANCH, parent, source, (change,)
    )
    dependencies = tuple(
        CandidateEvidence(
            kind,
            ("fixture " + kind).encode(),
            "test/" + kind.lower(),
            "1.0",
            "integration-fixture",
            "1.0",
        )
        for kind in ("CONTRACT", "PACK", "MODEL", "CONTEXT")
    )
    return ChapterCandidate(source, BRANCH, parent, version, PROSE, delta, dependencies)


def prepared(engine):
    service, issuer, root_ticket, root = ready(engine)
    ticket = service.begin_chapter(PROJECT, BRANCH, ACTOR, "request-1", root.commit_id)
    proposal = candidate(service, root.commit_id)
    permit = issuer.issue(ticket, proposal)
    return service, issuer, ticket, proposal, permit, root_ticket, root


def counts(engine):
    with engine.connect() as connection:
        return {
            table: connection.execute(
                text(f"SELECT count(*) FROM anovel_canon.{table}")
            ).scalar_one()
            for table in AUTHORITATIVE
        }


def unchanged(engine, before, head):
    assert counts(engine) == before
    assert Repository(engine).head(PROJECT, BRANCH) == head


def install_version_one(engine):
    """Reproduce the shipped old installer, without bypassing story writes."""
    raw = files("anovel.canon").joinpath("sql/0001_root.sql").read_bytes()
    digest = sha256(raw).hexdigest()
    with engine.begin() as connection:
        connection.exec_driver_sql(raw.decode())
        connection.execute(
            text(
                "INSERT INTO anovel_canon.schema_migrations(version,checksum) VALUES (1,:checksum)"
            ),
            {"checksum": digest},
        )
    return digest


def test_upgrade_existing_version_one_root_preserves_every_accepted_byte(database):
    old_checksum = install_version_one(database)
    service, _ticket, root = initialize(database)
    before_root = service.load_root(PROJECT, BRANCH, root.commit_id)
    with database.connect() as connection:
        before = {
            table: [
                tuple(row)
                for row in connection.execute(
                    text(f"SELECT * FROM anovel_canon.{table}")
                )
            ]
            for table in AUTHORITATIVE
        }
    migrate(database)
    assert migrate(database)
    assert service.load_root(PROJECT, BRANCH, root.commit_id) == before_root
    with database.connect() as connection:
        for table, rows in before.items():
            assert [
                tuple(row)
                for row in connection.execute(
                    text(f"SELECT * FROM anovel_canon.{table}")
                )
            ] == rows
        versions = connection.execute(
            text(
                "SELECT version,checksum FROM anovel_canon.schema_migrations ORDER BY version"
            )
        ).all()
        assert versions[0] == (1, old_checksum)
        assert [row[0] for row in versions] == [1, 2]
    service.configure_chapter_authority(PROJECT, BRANCH, ACTOR, ISSUER, "TEST-POLICY-1")
    ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "after-upgrade", root.commit_id
    )
    proposal = candidate(service, root.commit_id)
    issuer = ProtectedPermitIssuer(
        database, test_database=database.url.database, issuer_id=ISSUER
    )
    receipt = service.commit(ticket, proposal, issuer.issue(ticket, proposal))
    assert service.load_commit(PROJECT, BRANCH, receipt.commit_id).candidate == proposal


@pytest.mark.parametrize("autocommit", [False, True])
def test_failed_second_migration_preserves_version_one_schema_and_root(
    database, autocommit
):
    old_checksum = install_version_one(database)
    service, _ticket, root = initialize(database)
    original = service.load_root(PROJECT, BRANCH, root.commit_id)
    with database.begin() as connection:
        connection.exec_driver_sql(
            "CREATE FUNCTION public.fail_chapter_migration() RETURNS event_trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_TAG='CREATE TABLE' THEN RAISE EXCEPTION 'injected second migration failure'; END IF; END $$"
        )
        connection.exec_driver_sql(
            "CREATE EVENT TRIGGER fail_chapter_migration ON ddl_command_start EXECUTE FUNCTION public.fail_chapter_migration()"
        )
    installer = (
        database.execution_options(isolation_level="AUTOCOMMIT")
        if autocommit
        else database
    )
    try:
        with pytest.raises(DBAPIError):
            migrate(installer)
        with database.connect() as connection:
            assert connection.execute(
                text("SELECT version,checksum FROM anovel_canon.schema_migrations")
            ).all() == [(1, old_checksum)]
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM information_schema.columns WHERE table_schema='anovel_canon' AND table_name='requests' AND column_name='purpose'"
                    )
                ).scalar_one()
                == 0
            )
        assert service.load_root(PROJECT, BRANCH, root.commit_id) == original
    finally:
        with database.begin() as connection:
            connection.exec_driver_sql("DROP EVENT TRIGGER fail_chapter_migration")
            connection.exec_driver_sql("DROP FUNCTION public.fail_chapter_migration()")
    assert migrate(installer)
    assert service.load_root(PROJECT, BRANCH, root.commit_id) == original


def test_root_initializer_has_no_implicit_chapter_authority(engine):
    service, _ticket, root = initialize(engine)
    before = counts(engine)
    with pytest.raises(CanonPermissionError):
        service.begin_chapter(PROJECT, BRANCH, ACTOR, "no-grant", root.commit_id)
    unchanged(engine, before, root.commit_id)


def test_production_composition_refuses_test_permit(engine):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    before = counts(engine)
    production = CanonCommitService(engine)
    with pytest.raises(CanonPermissionError):
        production.commit(ticket, proposal, permit)
    unchanged(engine, before, root.commit_id)
    receipt = service.commit(ticket, proposal, permit)
    assert service.load_commit(PROJECT, BRANCH, receipt.commit_id).candidate == proposal


@pytest.mark.parametrize(
    "identity", ["anovel_test_wrong_database", "bootstrap_test", "production"]
)
def test_test_composition_requires_matching_explicit_disposable_database(
    engine, identity
):
    with pytest.raises(CanonError):
        service = CanonCommitService(engine, test_database=identity)
        service.provision(PROJECT, BRANCH, ACTOR)
    with pytest.raises(CanonError):
        ProtectedPermitIssuer(engine, test_database=identity, issuer_id=ISSUER)
    assert all(amount == 0 for amount in counts(engine).values())


def test_actual_permit_commit_preserves_exact_evidence_and_head_event_receipt(engine):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    before = counts(engine)
    receipt = service.commit(ticket, proposal, permit)
    stored = service.load_commit(PROJECT, BRANCH, receipt.commit_id)
    assert stored.receipt == receipt
    assert stored.candidate == proposal
    assert stored.candidate.prose == PROSE
    assert stored.candidate.delta.to_dict() == proposal.delta.to_dict()
    assert stored.candidate.dependencies == proposal.dependencies
    assert isinstance(json.loads(stored.permit_bytes), dict)
    assert Repository(engine).head(PROJECT, BRANCH) == receipt.commit_id
    assert Repository(engine).receipt(PROJECT, BRANCH, ticket.request_id) == receipt
    assert counts(engine)["commits"] == before["commits"] + 1
    assert counts(engine)["events"] == before["events"] + 1
    assert counts(engine)["receipts"] == before["receipts"] + 1
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT parent_id,sequence FROM anovel_canon.commits WHERE commit_id=:commit"
            ),
            {"commit": receipt.commit_id},
        ).one() == (root.commit_id, 1)
        assert connection.execute(
            text(
                "SELECT event_type,reducer_version FROM anovel_canon.events WHERE commit_id=:commit"
            ),
            {"commit": receipt.commit_id},
        ).one() == ("CHAPTER_COMMITTED", "FACT_DELTA-1")
    fresh = create_engine(engine.url)
    try:
        recovered = CanonCommitService(fresh).load_commit(
            PROJECT, BRANCH, receipt.commit_id
        )
        assert recovered == stored
    finally:
        fresh.dispose()


@pytest.mark.parametrize("operation", ["set", "unknown", "retract", "no_change"])
def test_chapter_reducer_persists_finite_fact_operation_states(engine, operation):
    service, issuer, _root_ticket, root = ready(engine)
    ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "finite-operation", root.commit_id
    )
    proposal = candidate(service, root.commit_id, operation=operation)
    receipt = service.commit(ticket, proposal, issuer.issue(ticket, proposal))
    original = service.load_baseline(PROJECT, BRANCH, root.commit_id)
    updated = service.load_baseline(PROJECT, BRANCH, receipt.commit_id)
    assert updated.parent_ref == receipt.commit_id
    before, after = original.facts[0], updated.facts[0]
    expected = {
        "set": FactState.known(20),
        "unknown": FactState.unknown(),
        "retract": FactState.retracted(),
        "no_change": before.state,
    }[operation]
    assert after.state == expected
    assert after.revision == (0 if operation == "no_change" else 1)
    assert before.state == FactState.known(10)
    assert before.revision == 0
    assert before.seed_fact == after.seed_fact


def test_two_chapters_read_each_historical_baseline_and_reuse_equal_artifact_bytes(
    engine,
):
    service, issuer, ticket, first, permit, _root_ticket, root = prepared(engine)
    first_receipt = service.commit(ticket, first, permit)
    second = candidate(service, first_receipt.commit_id, name="chapter-2", value=30)
    second_ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "request-2", first_receipt.commit_id
    )
    second_receipt = service.commit(
        second_ticket, second, issuer.issue(second_ticket, second)
    )
    assert first.prose == second.prose
    for commit, value, revision in [
        (root.commit_id, 10, 0),
        (first_receipt.commit_id, 20, 1),
        (second_receipt.commit_id, 30, 2),
    ]:
        baseline = service.load_baseline(PROJECT, BRANCH, commit)
        assert baseline.parent_ref == commit
        assert baseline.facts[0].state == FactState.known(value)
        assert baseline.facts[0].revision == revision
    assert (
        service.load_commit(PROJECT, BRANCH, first_receipt.commit_id).candidate == first
    )
    assert (
        service.load_commit(PROJECT, BRANCH, second_receipt.commit_id).candidate
        == second
    )
    assert service.load_root(PROJECT, BRANCH, root.commit_id).prose == b"initial root"
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM anovel_canon.artifacts WHERE artifact_type='RAW_PROSE' AND content=:prose"
                ),
                {"prose": PROSE},
            ).scalar_one()
            == 1
        )


@pytest.mark.parametrize(
    "permit", [None, "", "sha256:" + "0" * 64, "self-declared-ALLOW"]
)
def test_missing_or_forged_permit_ref_never_writes_canon(engine, permit):
    service, _issuer, ticket, proposal, _permit, _root_ticket, root = prepared(engine)
    before = counts(engine)
    with pytest.raises(CanonError):
        service.commit(ticket, proposal, permit)
    unchanged(engine, before, root.commit_id)


@pytest.mark.parametrize(
    "change", ["prose", "version", "delta", "dependency-content", "dependency-metadata"]
)
def test_permit_cannot_authorize_changed_candidate_payload(engine, change):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    if change == "prose":
        changed = replace(proposal, prose=PROSE + b"modified")
    elif change == "version":
        changed = replace(proposal, version=proposal.version + 1)
    elif change == "delta":
        operation = proposal.delta.operations[0]
        changed = replace(
            proposal,
            delta=replace(proposal.delta, operations=(replace(operation, value=21),)),
        )
    else:
        first = proposal.dependencies[0]
        replacement = (
            replace(first, content=b"changed dependency")
            if change == "dependency-content"
            else replace(first, producer_version="2.0")
        )
        changed = replace(
            proposal, dependencies=(replacement,) + proposal.dependencies[1:]
        )
    before = counts(engine)
    with pytest.raises(CanonError):
        service.commit(ticket, changed, permit)
    unchanged(engine, before, root.commit_id)


@pytest.mark.parametrize(
    "field,value",
    [
        ("actor", "untrusted-worker"),
        ("request_id", "another-request"),
        ("authorization_version", 999),
        ("execution_version", 999),
        ("project", "other-book"),
        ("branch", "other-branch"),
    ],
)
def test_forged_ticket_cannot_consume_valid_permit(engine, field, value):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    before = counts(engine)
    with pytest.raises(CanonError):
        service.commit(replace(ticket, **{field: value}), proposal, permit)
    unchanged(engine, before, root.commit_id)


def test_revoked_permit_is_rejected_without_any_story_write(engine):
    service, issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    issuer.revoke(PROJECT, BRANCH, permit)
    before = counts(engine)
    with pytest.raises(CanonPermissionError):
        service.commit(ticket, proposal, permit)
    unchanged(engine, before, root.commit_id)


def test_expired_permit_is_checked_using_actual_database_time(engine):
    service, issuer, _root_ticket, root = ready(engine)
    ticket = service.begin_chapter(PROJECT, BRANCH, ACTOR, "expiry", root.commit_id)
    proposal = candidate(service, root.commit_id)
    permit = issuer.issue(ticket, proposal, ttl_seconds=1)
    with engine.connect() as connection:
        connection.execute(text("SELECT pg_sleep(1.1)"))
    before = counts(engine)
    with pytest.raises(CanonPermissionError):
        service.commit(ticket, proposal, permit)
    unchanged(engine, before, root.commit_id)


def test_authority_revocation_fences_an_already_issued_permit(engine):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    assert (
        service.revoke_chapter_authority(PROJECT, BRANCH, ACTOR)
        > ticket.authorization_version
    )
    before = counts(engine)
    with pytest.raises(CanonPermissionError):
        service.commit(ticket, proposal, permit)
    unchanged(engine, before, root.commit_id)


def test_changed_policy_invalidates_old_permit(engine):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    service.configure_chapter_authority(PROJECT, BRANCH, ACTOR, ISSUER, "TEST-POLICY-2")
    before = counts(engine)
    with pytest.raises(CanonPermissionError):
        service.commit(ticket, proposal, permit)
    unchanged(engine, before, root.commit_id)


def test_cancel_before_commit_fences_valid_permit(engine):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    before = counts(engine)
    assert service.cancel(ticket) is None
    with pytest.raises(CanonPermissionError):
        service.commit(ticket, proposal, permit)
    unchanged(engine, before, root.commit_id)


def test_commit_before_cancel_returns_the_original_receipt_and_keeps_history(engine):
    service, issuer, ticket, proposal, permit, _root_ticket, _root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    before = counts(engine)
    assert service.cancel(ticket) == receipt
    issuer.revoke(PROJECT, BRANCH, permit)
    service.revoke_chapter_authority(PROJECT, BRANCH, ACTOR)
    assert service.commit(ticket, proposal, permit) == receipt
    assert service.load_commit(PROJECT, BRANCH, receipt.commit_id).candidate == proposal
    unchanged(engine, before, receipt.commit_id)


def test_begin_committed_request_after_grant_revocation_restores_ticket_and_receipt(
    engine,
):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    before = counts(engine)
    assert (
        service.revoke_chapter_authority(PROJECT, BRANCH, ACTOR)
        > ticket.authorization_version
    )
    recovered = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, ticket.request_id, root.commit_id
    )
    assert recovered == ticket
    assert service.commit(recovered, proposal, permit) == receipt
    assert service.load_commit(PROJECT, BRANCH, receipt.commit_id).candidate == proposal
    unchanged(engine, before, receipt.commit_id)


def test_expired_committed_permit_remains_readable_as_historical_evidence(engine):
    service, issuer, _root_ticket, root = ready(engine)
    ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "historical-expiry", root.commit_id
    )
    proposal = candidate(service, root.commit_id)
    permit = issuer.issue(ticket, proposal, ttl_seconds=1)
    receipt = service.commit(ticket, proposal, permit)
    stored = service.load_commit(PROJECT, BRANCH, receipt.commit_id)
    before = counts(engine)
    with engine.connect() as connection:
        connection.execute(text("SELECT pg_sleep(1.1)"))
        assert (
            connection.execute(
                text(
                    "SELECT expires_at < clock_timestamp() FROM anovel_canon.commit_permits WHERE permit_ref=:permit"
                ),
                {"permit": permit},
            ).scalar_one()
            is True
        )
    assert service.load_commit(PROJECT, BRANCH, receipt.commit_id) == stored
    assert service.commit(ticket, proposal, permit) == receipt
    unchanged(engine, before, receipt.commit_id)


def test_root_and_chapter_request_purposes_are_not_interchangeable(engine):
    service, issuer, root_ticket, root = ready(engine)
    before = counts(engine)
    with pytest.raises(CanonError):
        service.begin_chapter(
            PROJECT, BRANCH, ACTOR, root_ticket.request_id, root.commit_id
        )
    ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "chapter-purpose", root.commit_id
    )
    with pytest.raises(CanonError):
        service.begin_root(PROJECT, BRANCH, ACTOR, ticket.request_id)
    proposal = candidate(service, root.commit_id)
    with pytest.raises(CanonError):
        issuer.issue(root_ticket, proposal)
    unchanged(engine, before, root.commit_id)


def test_stale_parent_cannot_become_new_head_even_with_earlier_valid_permit(engine):
    service, issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    other_ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "competing-request", root.commit_id
    )
    other = candidate(service, root.commit_id, name="competing", value=25)
    other_permit = issuer.issue(other_ticket, other)
    receipt = service.commit(ticket, proposal, permit)
    before = counts(engine)
    with pytest.raises(CanonConflict):
        service.commit(other_ticket, other, other_permit)
    unchanged(engine, before, receipt.commit_id)


@pytest.mark.parametrize("autocommit", [False, True])
def test_event_failure_rolls_back_chapter_artifacts_commit_receipt_and_head(
    engine, autocommit
):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    if autocommit:
        service = CanonCommitService(
            engine.execution_options(isolation_level="AUTOCOMMIT"),
            test_database=engine.url.database,
        )
    before = counts(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE FUNCTION anovel_canon.reject_chapter_test_event() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.event_type='CHAPTER_COMMITTED' THEN RAISE EXCEPTION 'injected chapter event failure' USING ERRCODE='23514'; END IF; RETURN NEW; END $$"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER injected_chapter_event_failure BEFORE INSERT ON anovel_canon.events FOR EACH ROW EXECUTE FUNCTION anovel_canon.reject_chapter_test_event()"
        )
    try:
        with pytest.raises((DBAPIError, CanonError)):
            service.commit(ticket, proposal, permit)
        unchanged(engine, before, root.commit_id)
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "DROP TRIGGER injected_chapter_event_failure ON anovel_canon.events"
            )
    receipt = service.commit(ticket, proposal, permit)
    assert service.load_commit(PROJECT, BRANCH, receipt.commit_id).candidate == proposal


@pytest.mark.parametrize("action", ["UPDATE", "DELETE"])
def test_accepted_chapter_prose_cannot_be_replaced_or_removed(engine, action):
    service, _issuer, ticket, proposal, permit, _root_ticket, _root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    before = service.load_commit(PROJECT, BRANCH, receipt.commit_id)
    sql = (
        "UPDATE anovel_canon.artifacts SET content=:replacement WHERE artifact_type='RAW_PROSE'"
        if action == "UPDATE"
        else "DELETE FROM anovel_canon.artifacts WHERE artifact_type='RAW_PROSE'"
    )
    with pytest.raises(DBAPIError) as exc, engine.begin() as connection:
        connection.execute(text(sql), {"replacement": b"rewritten accepted prose"})
    assert getattr(exc.value.orig, "sqlstate", None) == "23514"
    assert service.load_commit(PROJECT, BRANCH, receipt.commit_id) == before


@pytest.mark.parametrize("scope", [("other-book", BRANCH), (PROJECT, "other-branch")])
def test_chapter_and_state_reads_cannot_cross_scope(engine, scope):
    service, _issuer, ticket, proposal, permit, _root_ticket, _root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    with pytest.raises(CanonError):
        service.load_commit(*scope, receipt.commit_id)
    with pytest.raises(CanonError):
        service.load_baseline(*scope, receipt.commit_id)


def test_review_submission_shows_actual_candidate_and_does_not_accept_or_write(engine):
    service, _issuer, ticket, proposal, _permit, _root_ticket, root = prepared(engine)
    before = counts(engine)
    review = service.review_submission(ticket, proposal)
    assert review["prose"] == PROSE.decode("utf-8")
    assert review["delta"] == proposal.delta.to_dict()
    assert review["parent"] == root.commit_id
    assert review["version"] == proposal.version
    assert isinstance(review["blockers"], (list, tuple))
    unchanged(engine, before, root.commit_id)


def test_seed_state_cannot_be_forged_by_mutating_caller_preview(engine):
    service, issuer, _root_ticket, root = ready(engine)
    ticket = service.begin_chapter(
        PROJECT, BRANCH, ACTOR, "wrong-precondition", root.commit_id
    )
    proposal = candidate(service, root.commit_id)
    operation = proposal.delta.operations[0]
    invalid = replace(
        operation,
        meta=replace(operation.meta, expected=Precondition(999, FactState.known(999))),
    )
    proposal = replace(proposal, delta=replace(proposal.delta, operations=(invalid,)))
    before = counts(engine)
    with pytest.raises(ValueError):
        issuer.issue(ticket, proposal)
    unchanged(engine, before, root.commit_id)


def alter_unaccepted_permit(engine, permit_ref, mutation, *, expires_at=None):
    """Explicit administrator tampering probes validation, never an issuer path."""
    with engine.begin() as connection:
        row = connection.execute(
            text(
                "SELECT content FROM anovel_canon.commit_permits WHERE permit_ref=:permit"
            ),
            {"permit": permit_ref},
        ).one()
        body = json.loads(bytes(row[0]))
        changed = mutation(body)
        raw = changed if type(changed) is bytes else canonical_bytes(changed)
        digest = sha256(raw).hexdigest()
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.commit_permits DISABLE TRIGGER immutable_permit"
        )
        connection.execute(
            text(
                "UPDATE anovel_canon.commit_permits SET content=:content,content_hash=:digest WHERE permit_ref=:old"
            ),
            {
                "old": permit_ref,
                "content": raw,
                "digest": digest,
            },
        )
        if expires_at is not None:
            connection.execute(
                text(
                    "UPDATE anovel_canon.commit_permits SET expires_at=:expires WHERE permit_ref=:permit"
                ),
                {"expires": expires_at, "permit": permit_ref},
            )
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.commit_permits ENABLE TRIGGER immutable_permit"
        )
    return permit_ref


@pytest.mark.parametrize(
    "field,replacement",
    [("authorization_version", False), ("candidate_version", True)],
)
def test_rehashed_permit_rejects_boolean_binding_even_when_numerically_equal(
    engine, field, replacement
):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)

    def mutate(body):
        assert type(body["binding"][field]) is int
        assert body["binding"][field] == replacement
        body["binding"][field] = replacement
        return body

    corrupted = alter_unaccepted_permit(engine, permit, mutate)
    before = counts(engine)
    with pytest.raises(CanonError):
        service.commit(ticket, proposal, corrupted)
    unchanged(engine, before, root.commit_id)


def test_rehashed_permit_issued_in_future_is_rejected_even_with_consistent_expiry(
    engine,
):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)
    with engine.connect() as connection:
        issued = connection.execute(
            text("SELECT clock_timestamp()")
        ).scalar_one() + timedelta(minutes=5)
    expires = issued + timedelta(minutes=5)

    def mutate(body):
        body["issued_at"] = utc_timestamp(issued)
        body["expires_at"] = utc_timestamp(expires)
        for check in body["checks"]:
            check["performed_at"] = utc_timestamp(issued)
        return body

    corrupted = alter_unaccepted_permit(engine, permit, mutate, expires_at=expires)
    before = counts(engine)
    with pytest.raises(CanonPermissionError):
        service.commit(ticket, proposal, corrupted)
    unchanged(engine, before, root.commit_id)


@pytest.mark.parametrize(
    "mutation",
    ["missing-checks", "malformed-json", "unknown-version", "missing-policy"],
)
def test_rehashed_permit_with_missing_or_malformed_requirements_is_rejected(
    engine, mutation
):
    service, _issuer, ticket, proposal, permit, _root_ticket, root = prepared(engine)

    def mutate(body):
        if mutation == "malformed-json":
            return b"{malformed permit"
        if mutation == "missing-checks":
            assert "checks" in body
            body["checks"] = []
        elif mutation == "unknown-version":
            assert "schema_version" in body
            body["schema_version"] = "999.0"
        else:
            assert "policy" in body
            body.pop("policy")
        return body

    corrupted = alter_unaccepted_permit(engine, permit, mutate)
    before = counts(engine)
    with pytest.raises(CanonError):
        service.commit(ticket, proposal, corrupted)
    unchanged(engine, before, root.commit_id)


def test_accepted_state_damage_is_detected_on_historical_read(engine):
    service, _issuer, ticket, proposal, permit, _root_ticket, _root = prepared(engine)
    receipt = service.commit(ticket, proposal, permit)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.artifacts DISABLE TRIGGER immutable_artifacts"
        )
        connection.execute(
            text(
                "UPDATE anovel_canon.artifacts SET content=:bad WHERE artifact_type='STATE_SNAPSHOT'"
            ),
            {"bad": b"corrupted fact state"},
        )
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.artifacts ENABLE TRIGGER immutable_artifacts"
        )
    with pytest.raises(CanonIntegrityError):
        service.load_commit(PROJECT, BRANCH, receipt.commit_id)
    with pytest.raises(CanonIntegrityError):
        service.load_baseline(PROJECT, BRANCH, receipt.commit_id)


@pytest.mark.parametrize("action", ["UPDATE", "DELETE"])
def test_issued_permit_evidence_cannot_be_replaced_or_deleted(engine, action):
    _service, issuer, _ticket, _proposal, permit, _root_ticket, _root = prepared(engine)
    sql = (
        "UPDATE anovel_canon.commit_permits SET content=:bad WHERE permit_ref=:permit"
        if action == "UPDATE"
        else "DELETE FROM anovel_canon.commit_permits WHERE permit_ref=:permit"
    )
    with pytest.raises(DBAPIError) as exc, engine.begin() as connection:
        connection.execute(text(sql), {"permit": permit, "bad": b"replaced permit"})
    assert getattr(exc.value.orig, "sqlstate", None) == "23514"
    issuer.revoke(PROJECT, BRANCH, permit)
    with pytest.raises(DBAPIError) as exc, engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE anovel_canon.commit_permits SET revoked=false WHERE permit_ref=:permit"
            ),
            {"permit": permit},
        )
    assert getattr(exc.value.orig, "sqlstate", None) == "23514"
