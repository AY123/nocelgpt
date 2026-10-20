"""Real PostgreSQL persistence acceptance, isolated from the bootstrap database.

Only explicit negative constraint/tamper tests issue Canon SQL. Every valid root
is initialized through the same public service used by application callers.
"""

import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from importlib.resources import files

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from test_postgres_environment import postgres

from anovel.canon.commit_service import CanonCommitService
from anovel.canon.migrations import migrate
from anovel.canon.models import (
    CanonConflict,
    CanonError,
    CanonIntegrityError,
    CanonPermissionError,
    CommitReceipt,
    RootSeed,
)
from anovel.canon.repository import Repository
from anovel.domain.character import Relationship
from anovel.domain.identity import Entity, EntityId
from anovel.domain.knowledge import Proposition, WorldFact

SCHEMA = "anovel_canon"
PROSE = "\ufeff初始人物和事实。\r\n末尾保留空格  \n".encode()
AUTHORITATIVE_TABLES = (
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
    """The parent service is never migrated or used as a Canon test database."""
    supplied = os.environ.get("ANOVELOS_TEST_DSN")
    if supplied:
        url = make_url(supplied)
        assert url.drivername == "postgresql+psycopg"
        assert url.database == "bootstrap_test", (
            "An explicit disposable test service is required"
        )
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
    name = "anovel_v2009_" + uuid.uuid4().hex
    quoted = admin_engine.dialect.identifier_preparer.quote(name)
    with admin_engine.connect() as connection:
        connection.exec_driver_sql(f"CREATE DATABASE {quoted}")
    engine = create_engine(admin_engine.url.set(database=name))
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(text("SHOW server_version_num")).scalar_one()
                == "170011"
            )
            assert (
                connection.execute(text("SELECT current_database()")).scalar_one()
                == name
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


def seed(project="book", prefix=""):
    a = Entity(EntityId(project, prefix + "alice"), "甲")
    b = Entity(EntityId(project, prefix + "bob"), "乙")
    relation = Relationship(
        EntityId(project, prefix + "relation"), a.id, b.id, {"friend"}, trust=0.25
    )
    fact = WorldFact(
        EntityId(project, prefix + "fact"),
        Proposition(a.id, "balance", 0.1),
        "root-input:1",
    )
    return RootSeed((a, b), (relation,), (fact,))


def provision(engine, project="book", branch="main", request="request"):
    service = CanonCommitService(engine)
    service.provision(project, branch, "owner")
    return service, service.begin_root(project, branch, "owner", request)


def initialize(engine, project="book", branch="main", request="request", prefix=""):
    service, ticket = provision(engine, project, branch, request)
    receipt = service.initialize_root(ticket, seed(project, prefix), PROSE)
    return service, ticket, receipt


def counts(engine):
    with engine.connect() as connection:
        return {
            table: connection.execute(
                text(f"SELECT count(*) FROM {SCHEMA}.{table}")
            ).scalar_one()
            for table in AUTHORITATIVE_TABLES
        }


def assert_sqlstate(exc, state):
    assert getattr(exc.value.orig, "sqlstate", None) == state


def test_empty_database_migration_is_repeatable_and_creates_no_canon(database):
    with database.connect() as connection:
        assert (
            connection.execute(
                text("SELECT to_regnamespace('anovel_canon')")
            ).scalar_one()
            is None
        )
    checksum = migrate(database)
    assert len(checksum) == 64
    assert migrate(database) == checksum
    assert all(value == 0 for value in counts(database).values())
    with database.connect() as connection:
        expected = [
            (
                version,
                sha256(files("anovel.canon").joinpath(name).read_bytes()).hexdigest(),
            )
            for version, name in ((1, "sql/0001_root.sql"), (2, "sql/0002_chapter.sql"))
        ]
        assert expected[-1][1] == checksum
        assert (
            connection.execute(
                text(
                    "SELECT version,checksum FROM anovel_canon.schema_migrations ORDER BY version"
                )
            ).all()
            == expected
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM anovel_canon.branches")
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE anovel_canon.schema_migrations SET checksum=repeat('0',64)",
        "INSERT INTO anovel_canon.schema_migrations(version,checksum) VALUES (999,repeat('0',64))",
    ],
)
def test_migration_checksum_or_unknown_version_is_rejected(engine, mutation):
    with engine.begin() as connection:
        connection.execute(text(mutation))
    with pytest.raises(CanonIntegrityError):
        migrate(engine)


def test_concurrent_installers_return_the_same_complete_schema(database):
    start = threading.Barrier(2)

    def install():
        start.wait(timeout=10)
        return migrate(database)

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: install(), range(2)))
    assert results[0] == results[1]
    assert all(value == 0 for value in counts(database).values())
    assert migrate(database) == results[0]


def test_provisioning_never_initializes_story_and_wrong_actor_is_rejected(engine):
    service, _ticket = provision(engine)
    assert Repository(engine).head("book", "main") is None
    assert all(value == 0 for value in counts(engine).values())
    with pytest.raises(CanonPermissionError):
        service.begin_root("book", "main", "untrusted-writer", "another-request")
    assert all(value == 0 for value in counts(engine).values())


def test_root_round_trip_preserves_domain_raw_bytes_and_authority(engine):
    _service, ticket, receipt = initialize(engine)
    repository = Repository(engine)
    assert repository.head("book", "main") == receipt.commit_id
    assert repository.receipt("book", "main", ticket.request_id) == receipt
    stored = repository.load_root("book", "main", receipt.commit_id)
    assert stored.receipt == receipt
    assert stored.seed.to_dict() == seed().to_dict()
    assert stored.prose == PROSE
    assert isinstance(json.loads(stored.authority_bytes), dict)
    assert counts(engine) == {
        "artifacts": 3,
        "commits": 1,
        "commit_artifacts": 3,
        "events": 1,
        "receipts": 1,
        "entities": 2,
        "relationships": 1,
        "facts": 1,
    }
    with engine.connect() as connection:
        root = connection.execute(
            text("SELECT parent_id,sequence FROM anovel_canon.commits")
        ).one()
        assert root == (None, 0)
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM anovel_canon.artifacts WHERE octet_length(content)>0"
                )
            ).scalar_one()
            == 3
        )


def test_reopening_connection_recovers_committed_root_without_memory(engine):
    _service, _ticket, receipt = initialize(engine)
    independent = create_engine(engine.url)
    try:
        stored = Repository(independent).load_root("book", "main", receipt.commit_id)
        assert stored.prose == PROSE
        assert stored.seed.to_dict() == seed().to_dict()
        assert stored.receipt == receipt
    finally:
        independent.dispose()


def test_same_entity_names_and_ids_are_independent_between_scopes(engine):
    receipts = [
        initialize(engine, project, branch)[2]
        for project, branch in (
            ("book", "main"),
            ("book", "other"),
            ("another-book", "main"),
        )
    ]
    assert len({receipt.commit_id for receipt in receipts}) == 3
    for receipt in receipts:
        stored = Repository(engine).load_root(
            receipt.project, receipt.branch, receipt.commit_id
        )
        assert stored.seed.project == receipt.project
        assert stored.receipt == receipt


@pytest.mark.parametrize(
    "foreign_scope",
    [("another-book", "main"), ("book", "other")],
    ids=["project", "branch"],
)
@pytest.mark.parametrize("target", ["party_a", "party_b", "fact_subject"])
def test_relationship_and_fact_foreign_keys_reject_foreign_scope(
    engine, foreign_scope, target
):
    _service, _ticket, own = initialize(engine)
    initialize(engine, *foreign_scope, prefix="foreign-")
    if target == "fact_subject":
        sql = "INSERT INTO anovel_canon.facts(project_id,branch_id,fact_id,subject_id,commit_id) VALUES ('book','main','invalid-fact','foreign-alice',:commit)"
    else:
        a, b = (
            ("foreign-alice", "bob")
            if target == "party_a"
            else ("alice", "foreign-bob")
        )
        sql = "INSERT INTO anovel_canon.relationships(project_id,branch_id,relationship_id,party_a,party_b,commit_id) VALUES ('book','main','invalid-relationship',:a,:b,:commit)"
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as connection:
            connection.execute(
                text(sql),
                {
                    "commit": own.commit_id,
                    "a": locals().get("a"),
                    "b": locals().get("b"),
                },
            )
    assert_sqlstate(exc, "23503")


@pytest.mark.parametrize(
    "foreign_scope",
    [("another-book", "main"), ("book", "other")],
    ids=["project", "branch"],
)
@pytest.mark.parametrize("target", ["head", "event", "receipt", "entity", "parent"])
def test_commit_references_cannot_cross_project_or_branch(
    engine, foreign_scope, target
):
    _service, ticket = provision(engine)
    _other, _foreign_ticket, foreign = initialize(engine, *foreign_scope)
    statement = {
        "head": "UPDATE anovel_canon.branches SET head_id=:foreign WHERE project_id='book' AND branch_id='main'",
        "event": "INSERT INTO anovel_canon.events VALUES ('book','main',:foreign,'ROOT_INITIALIZED','ROOT-1')",
        "receipt": "INSERT INTO anovel_canon.receipts VALUES ('book','main',:request,:foreign,:payload)",
        "entity": "INSERT INTO anovel_canon.entities VALUES ('book','main','bad-entity',:foreign)",
        "parent": "INSERT INTO anovel_canon.commits(project_id,branch_id,commit_id,parent_id,sequence,request_id,payload_hash,canonical_bytes) VALUES ('book','main',:new_id,:foreign,1,:request,:payload,:content)",
    }[target]
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as connection:
            connection.execute(
                text(statement),
                {
                    "foreign": foreign.commit_id,
                    "request": ticket.request_id,
                    "payload": foreign.payload_hash,
                    "new_id": "sha256:" + "a" * 64,
                    "content": b"{}",
                },
            )
    assert_sqlstate(exc, "23503")
    assert Repository(engine).head("book", "main") is None


def test_two_real_connections_compete_for_exactly_one_root(engine):
    service, first = provision(engine)
    second = service.begin_root("book", "main", "owner", "second-request")
    start = threading.Barrier(3)
    names = ["v2009_" + uuid.uuid4().hex for _ in range(2)]
    worker_engines = [
        create_engine(
            engine.url,
            pool_size=1,
            max_overflow=0,
            connect_args={"application_name": name},
        )
        for name in names
    ]

    def attempt(index, ticket):
        worker = worker_engines[index]
        with worker.connect() as connection:
            pid = connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
        start.wait(timeout=10)
        try:
            result = CanonCommitService(worker).initialize_root(ticket, seed(), PROSE)
        except CanonConflict as error:
            result = error
        return pid, result

    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            # Hold the actual branch lock until both independent workers are
            # demonstrably waiting on a PostgreSQL lock, not just Python threads.
            with engine.begin() as blocker:
                blocker.execute(
                    text(
                        "SELECT 1 FROM anovel_canon.branches WHERE project_id='book' AND branch_id='main' FOR UPDATE"
                    )
                )
                futures = [
                    workers.submit(attempt, 0, first),
                    workers.submit(attempt, 1, second),
                ]
                start.wait(timeout=10)
                deadline = time.monotonic() + 15
                waiting = 0
                while time.monotonic() < deadline:
                    with engine.connect() as observer:
                        waiting = observer.execute(
                            text(
                                "SELECT count(*) FROM pg_stat_activity WHERE application_name IN (:one,:two) AND wait_event_type='Lock'"
                            ),
                            {"one": names[0], "two": names[1]},
                        ).scalar_one()
                    if waiting == 2:
                        break
                    time.sleep(0.02)
                assert waiting == 2, (
                    "Both independent backend transactions must contend"
                )
            results = [future.result(timeout=20) for future in futures]
        assert len({pid for pid, _result in results}) == 2
        assert sum(isinstance(result, CommitReceipt) for _pid, result in results) == 1
        assert sum(isinstance(result, CanonConflict) for _pid, result in results) == 1
        assert counts(engine)["commits"] == counts(engine)["receipts"] == 1
        assert counts(engine)["artifacts"] == 3
    finally:
        for worker in worker_engines:
            worker.dispose()


def test_cancel_before_commit_fences_the_original_ticket(engine):
    service, ticket = provision(engine)
    assert service.cancel(ticket) is None
    with pytest.raises(CanonPermissionError):
        service.initialize_root(ticket, seed(), PROSE)
    assert all(value == 0 for value in counts(engine).values())
    assert Repository(engine).head("book", "main") is None


def test_revoke_before_commit_fences_the_original_ticket(engine):
    service, ticket = provision(engine)
    assert (
        service.revoke_initializer("book", "main", "owner")
        > ticket.authorization_version
    )
    with pytest.raises(CanonPermissionError):
        service.initialize_root(ticket, seed(), PROSE)
    assert all(value == 0 for value in counts(engine).values())


def test_commit_before_cancel_preserves_success_and_receipt(engine):
    service, ticket, receipt = initialize(engine)
    assert service.cancel(ticket) == receipt
    assert service.initialize_root(ticket, seed(), PROSE) == receipt
    assert counts(engine)["commits"] == 1


def test_successful_request_recovers_after_authority_revocation(engine):
    service, ticket, receipt = initialize(engine)
    service.revoke_initializer("book", "main", "owner")
    assert service.initialize_root(ticket, seed(), PROSE) == receipt
    assert service.cancel(ticket) == receipt
    assert (
        Repository(engine).load_root("book", "main", receipt.commit_id).prose == PROSE
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("actor", "untrusted-writer"),
        ("authorization_version", 999),
        ("execution_version", 999),
        ("request_id", "missing-request"),
        ("project", "foreign-book"),
        ("branch", "foreign-branch"),
    ],
)
def test_forged_or_stale_ticket_cannot_initialize(engine, field, value):
    service, ticket = provision(engine)
    with pytest.raises(CanonError):
        service.initialize_root(replace(ticket, **{field: value}), seed(), PROSE)
    assert all(value == 0 for value in counts(engine).values())


def test_successful_receipt_does_not_authorize_another_actor(engine):
    service, ticket, _receipt = initialize(engine)
    with pytest.raises(CanonPermissionError):
        service.initialize_root(
            replace(ticket, actor="untrusted-writer"), seed(), PROSE
        )


def test_same_request_changed_payload_and_second_root_are_rejected(engine):
    service, ticket, receipt = initialize(engine)
    with pytest.raises(CanonConflict):
        service.initialize_root(ticket, seed(), PROSE + b"changed")
    other = service.begin_root("book", "main", "owner", "another-request")
    with pytest.raises(CanonConflict):
        service.initialize_root(other, seed(), PROSE)
    assert Repository(engine).head("book", "main") == receipt.commit_id
    assert counts(engine)["commits"] == counts(engine)["receipts"] == 1


@pytest.mark.parametrize("autocommit", [False, True])
def test_event_insert_failure_rolls_back_artifacts_commit_indexes_and_head(
    engine, autocommit
):
    service_engine = (
        engine.execution_options(isolation_level="AUTOCOMMIT") if autocommit else engine
    )
    service, ticket = provision(service_engine)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE FUNCTION anovel_canon.reject_test_event() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected event failure' USING ERRCODE='23514'; END $$"
        )
        connection.exec_driver_sql(
            "CREATE TRIGGER injected_event_failure BEFORE INSERT ON anovel_canon.events FOR EACH ROW EXECUTE FUNCTION anovel_canon.reject_test_event()"
        )
    with pytest.raises((DBAPIError, CanonError)):
        service.initialize_root(ticket, seed(), PROSE)
    assert all(value == 0 for value in counts(engine).values())
    assert Repository(engine).head("book", "main") is None
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "DROP TRIGGER injected_event_failure ON anovel_canon.events"
        )
    receipt = service.initialize_root(ticket, seed(), PROSE)
    assert Repository(engine).head("book", "main") == receipt.commit_id


@pytest.mark.parametrize("table", AUTHORITATIVE_TABLES)
@pytest.mark.parametrize("action", ["UPDATE", "DELETE"])
def test_accepted_history_cannot_be_modified_or_deleted(engine, table, action):
    _service, _ticket, receipt = initialize(engine)
    sql = (
        f"UPDATE {SCHEMA}.{table} SET project_id=project_id"
        if action == "UPDATE"
        else f"DELETE FROM {SCHEMA}.{table}"
    )
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as connection:
            connection.execute(text(sql))
    assert_sqlstate(exc, "23514")
    assert (
        Repository(engine).load_root("book", "main", receipt.commit_id).prose == PROSE
    )


def test_privileged_storage_corruption_is_detected_on_read(engine):
    _service, _ticket, receipt = initialize(engine)
    # Deliberate administrator tampering is a negative integrity probe, never
    # an application initialization path or claim of protection from DB owners.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.artifacts DISABLE TRIGGER immutable_artifacts"
        )
        connection.execute(
            text(
                "UPDATE anovel_canon.artifacts SET content=:bad WHERE artifact_type='RAW_PROSE'"
            ),
            {"bad": b"corrupted"},
        )
        connection.exec_driver_sql(
            "ALTER TABLE anovel_canon.artifacts ENABLE TRIGGER immutable_artifacts"
        )
    with pytest.raises(CanonIntegrityError):
        Repository(engine).load_root("book", "main", receipt.commit_id)


def test_service_rejects_wrong_project_seed_and_invalid_utf8_without_writes(engine):
    service, ticket = provision(engine)
    for data, prose in ((seed("foreign-book"), PROSE), (seed(), b"\xff")):
        with pytest.raises((CanonError, ValueError)):
            service.initialize_root(ticket, data, prose)
    assert all(value == 0 for value in counts(engine).values())


@pytest.mark.parametrize("autocommit", [False, True])
def test_failed_migration_rolls_back_all_ddl(database, autocommit):
    # A real server-side DDL failure after several CREATE TABLE statements.
    with database.begin() as conn:
        conn.exec_driver_sql(
            "CREATE FUNCTION public.fail_test_migration() RETURNS event_trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_TAG = 'CREATE INDEX' THEN RAISE EXCEPTION 'injected migration failure'; END IF; END $$"
        )
        conn.exec_driver_sql(
            "CREATE EVENT TRIGGER fail_test_migration ON ddl_command_start EXECUTE FUNCTION public.fail_test_migration()"
        )
    installer = (
        database.execution_options(isolation_level="AUTOCOMMIT")
        if autocommit
        else database
    )
    try:
        with pytest.raises(DBAPIError):
            migrate(installer)
        with database.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT to_regnamespace('anovel_canon')")
                ).scalar_one()
                is None
            )
    finally:
        with database.begin() as conn:
            conn.exec_driver_sql("DROP EVENT TRIGGER fail_test_migration")
            conn.exec_driver_sql("DROP FUNCTION public.fail_test_migration()")
    assert migrate(installer)
    assert all(value == 0 for value in counts(database).values())
