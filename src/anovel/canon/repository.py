"""Internal PostgreSQL persistence; public Canon writes belong to commit_service.

A privileged database operator can bypass Python. Workers must never receive the
management engine; scoped keys are integrity constraints, not authentication.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from typing import Any

from sqlalchemy import Connection, Engine, RowMapping, text

from anovel.canon.identity import (
    canonical_bytes,
    decode_canonical,
    raw_prose_hash,
    utc_timestamp,
)
from anovel.canon.models import (
    CanonConflict,
    CanonError,
    CanonIntegrityError,
    CanonPermissionError,
    CommitReceipt,
    ExecutionTicket,
    RootSeed,
    StoredRoot,
    identifier,
)


@contextmanager
def _transaction(engine: Engine) -> Iterator[Connection]:
    # Apply at the connection, after inherited OptionEngine listeners; applying
    # only to a nested engine can leave a parent AUTOCOMMIT listener in effect.
    with engine.connect() as conn:
        conn.execution_options(isolation_level="READ COMMITTED")
        with conn.begin():
            yield conn


def _scope(project: str, branch: str) -> dict[str, Any]:
    return {"project": identifier(project), "branch": identifier(branch)}


def _one(conn: Connection, sql: str, params: dict[str, Any]) -> RowMapping | None:
    return conn.execute(text(sql), params).mappings().one_or_none()


def _receipt(conn: Connection, params: dict[str, Any]) -> CommitReceipt | None:
    row = _one(
        conn,
        """SELECT r.*, c.created_at FROM anovel_canon.receipts r
        JOIN anovel_canon.commits c USING(project_id,branch_id,commit_id)
        WHERE r.project_id=:project AND r.branch_id=:branch AND r.request_id=:request""",
        params,
    )
    if row is None:
        return None
    return CommitReceipt(
        row["project_id"],
        row["branch_id"],
        row["request_id"],
        row["commit_id"],
        row["payload_hash"],
        utc_timestamp(row["created_at"]),
    )


def _branch(conn: Connection, params: dict[str, Any]) -> RowMapping:
    row = _one(
        conn,
        "SELECT * FROM anovel_canon.branches WHERE project_id=:project AND branch_id=:branch FOR UPDATE",
        params,
    )
    if row is None:
        raise CanonPermissionError("scope is not provisioned")
    return row


def _request(conn: Connection, params: dict[str, Any]) -> RowMapping:
    row = _one(
        conn,
        "SELECT * FROM anovel_canon.requests WHERE project_id=:project AND branch_id=:branch AND request_id=:request",
        params,
    )
    if row is None or row["actor"] != params["actor"]:
        raise CanonPermissionError("request missing or belongs to another actor")
    return row


class Repository:
    """Scoped read API and service-internal transaction primitives."""

    def __init__(self, engine: Engine) -> None:
        if engine.dialect.name != "postgresql":
            raise CanonError("Canon requires PostgreSQL")
        self._engine = engine

    def head(self, project: str, branch: str) -> str | None:
        with self._engine.connect() as conn:
            row = _one(
                conn,
                "SELECT head_id FROM anovel_canon.branches WHERE project_id=:project AND branch_id=:branch",
                _scope(project, branch),
            )
            if row is None:
                raise CanonError("unknown branch")
            return row["head_id"] if row["head_id"] is not None else None

    def receipt(
        self, project: str, branch: str, request_id: str
    ) -> CommitReceipt | None:
        with self._engine.connect() as conn:
            return _receipt(
                conn, {**_scope(project, branch), "request": identifier(request_id)}
            )

    def load_root(self, project: str, branch: str, commit_id: str) -> StoredRoot:
        params = {**_scope(project, branch), "commit": identifier(commit_id)}
        with self._engine.connect() as conn:
            commit = _one(
                conn,
                "SELECT * FROM anovel_canon.commits WHERE project_id=:project AND branch_id=:branch AND commit_id=:commit",
                params,
            )
            if (
                commit is None
                or commit["parent_id"] is not None
                or commit["sequence"] != 0
            ):
                raise CanonIntegrityError("scoped root does not exist")
            raw = bytes(commit["canonical_bytes"])
            if "sha256:" + sha256(raw).hexdigest() != commit_id:
                raise CanonIntegrityError("commit content hash mismatch")
            envelope = decode_canonical(raw)
            if not isinstance(envelope, dict):
                raise CanonIntegrityError("invalid commit envelope")
            artifacts = (
                conn.execute(
                    text("""SELECT a.* FROM anovel_canon.commit_artifacts l
                JOIN anovel_canon.artifacts a USING(project_id,branch_id,artifact_id,artifact_type)
                WHERE l.project_id=:project AND l.branch_id=:branch AND l.commit_id=:commit
                ORDER BY a.artifact_type"""),
                    params,
                )
                .mappings()
                .all()
            )
            contents: dict[str, bytes] = {}
            bindings = []
            for artifact in artifacts:
                content = bytes(artifact["content"])
                kind = artifact["artifact_type"]
                digest = sha256(content).hexdigest()
                encoding = "RAW-UTF8" if kind == "RAW_PROSE" else "ANOVELOS-CJSON-1"
                if (
                    digest != artifact["content_hash"]
                    or artifact["artifact_id"] != kind + ":" + digest
                    or artifact["encoding"] != encoding
                ):
                    raise CanonIntegrityError("artifact identity mismatch")
                contents[kind] = content
                bindings.append(
                    {"type": kind, "id": artifact["artifact_id"], "hash": digest}
                )
            if set(contents) != {"ROOT_INPUT", "RAW_PROSE", "INITIALIZER_AUTHORITY"}:
                raise CanonIntegrityError("root evidence closure is incomplete")
            expected = {
                "kind": "ROOT_COMMIT",
                "schema_version": "1.0",
                "producer": "anovel.canon.root/1.0",
                "project": project,
                "branch": branch,
                "parent": None,
                "sequence": 0,
                "request_id": commit["request_id"],
                "payload_hash": commit["payload_hash"],
                "artifacts": bindings,
            }
            if envelope != expected:
                raise CanonIntegrityError("commit envelope metadata mismatch")
            root_input = decode_canonical(contents["ROOT_INPUT"])
            authority = decode_canonical(contents["INITIALIZER_AUTHORITY"])
            if not isinstance(root_input, dict) or not isinstance(authority, dict):
                raise CanonIntegrityError("invalid root artifacts")
            if (
                set(root_input)
                != {
                    "kind",
                    "schema_version",
                    "project",
                    "branch",
                    "request_id",
                    "actor",
                    "seed",
                    "raw_prose_hash",
                }
                or root_input["kind"] != "ROOT_INPUT"
                or root_input["schema_version"] != "1.0"
            ):
                raise CanonIntegrityError("invalid root input version")
            for key, value in (
                ("project", project),
                ("branch", branch),
                ("request_id", commit["request_id"]),
            ):
                if root_input[key] != value or authority.get(key) != value:
                    raise CanonIntegrityError("root artifacts cross identity")
            if (
                authority.get("kind") != "INITIALIZER_GRANT"
                or authority.get("policy") != "MANUAL_TEST_ROOT-1"
                or authority.get("actor") != root_input["actor"]
            ):
                raise CanonIntegrityError("initializer authority identity mismatch")
            if (
                sha256(contents["ROOT_INPUT"]).hexdigest() != commit["payload_hash"]
                or raw_prose_hash(contents["RAW_PROSE"]) != root_input["raw_prose_hash"]
            ):
                raise CanonIntegrityError("root payload/prose mismatch")
            seed = RootSeed.from_dict(root_input["seed"])
            if seed.project != project:
                raise CanonIntegrityError("seed crosses scope")
            receipt = _receipt(conn, {**params, "request": commit["request_id"]})
            event = _one(
                conn,
                "SELECT event_type,reducer_version FROM anovel_canon.events WHERE project_id=:project AND branch_id=:branch AND commit_id=:commit",
                params,
            )
            if (
                receipt is None
                or receipt.commit_id != commit_id
                or event is None
                or tuple(event.values()) != ("ROOT_INITIALIZED", "ROOT-1")
            ):
                raise CanonIntegrityError("root event/receipt missing")
            return StoredRoot(
                receipt, seed, contents["RAW_PROSE"], contents["INITIALIZER_AUTHORITY"]
            )

    def _provision(self, project: str, branch: str, initializer: str) -> None:
        params = {**_scope(project, branch), "actor": identifier(initializer)}
        with _transaction(self._engine) as conn:
            conn.execute(
                text(
                    "INSERT INTO anovel_canon.projects(project_id) VALUES (:project) ON CONFLICT DO NOTHING"
                ),
                params,
            )
            conn.execute(
                text(
                    "INSERT INTO anovel_canon.branches(project_id,branch_id,initializer) VALUES (:project,:branch,:actor)"
                ),
                params,
            )

    def _begin_root(
        self, project: str, branch: str, actor: str, request_id: str
    ) -> ExecutionTicket:
        params = {
            **_scope(project, branch),
            "actor": identifier(actor),
            "request": identifier(request_id),
        }
        with _transaction(self._engine) as conn:
            branch_row = _branch(conn, params)
            if not branch_row["enabled"] or branch_row["initializer"] != actor:
                raise CanonPermissionError("actor has no current initializer grant")
            conn.execute(
                text("""INSERT INTO anovel_canon.requests(project_id,branch_id,request_id,actor,authorization_version)
                VALUES (:project,:branch,:request,:actor,:version) ON CONFLICT DO NOTHING"""),
                {**params, "version": branch_row["authorization_version"]},
            )
            request = _request(conn, params)
            return ExecutionTicket(
                project,
                branch,
                request_id,
                actor,
                request["authorization_version"],
                request["execution_version"],
            )

    def _initialize_root(
        self, ticket: ExecutionTicket, seed: RootSeed, prose: bytes
    ) -> CommitReceipt:
        if (
            type(ticket) is not ExecutionTicket
            or type(seed) is not RootSeed
            or seed.project != ticket.project
        ):
            raise CanonError("invalid root scope/types")
        # Serialization and full domain validation occur before the transaction.
        payload = canonical_bytes(
            {
                "kind": "ROOT_INPUT",
                "schema_version": "1.0",
                "project": ticket.project,
                "branch": ticket.branch,
                "request_id": ticket.request_id,
                "actor": ticket.actor,
                "seed": seed.to_dict(),
                "raw_prose_hash": raw_prose_hash(prose),
            }
        )
        payload_hash = sha256(payload).hexdigest()
        authority = canonical_bytes(
            {
                "kind": "INITIALIZER_GRANT",
                "policy": "MANUAL_TEST_ROOT-1",
                "project": ticket.project,
                "branch": ticket.branch,
                "request_id": ticket.request_id,
                "actor": ticket.actor,
                "authorization_version": ticket.authorization_version,
                "execution_version": ticket.execution_version,
            }
        )
        documents = {
            "ROOT_INPUT": payload,
            "RAW_PROSE": prose,
            "INITIALIZER_AUTHORITY": authority,
        }
        bindings = [
            {
                "type": kind,
                "id": kind + ":" + sha256(raw).hexdigest(),
                "hash": sha256(raw).hexdigest(),
            }
            for kind, raw in sorted(documents.items())
        ]
        envelope = canonical_bytes(
            {
                "kind": "ROOT_COMMIT",
                "schema_version": "1.0",
                "producer": "anovel.canon.root/1.0",
                "project": ticket.project,
                "branch": ticket.branch,
                "parent": None,
                "sequence": 0,
                "request_id": ticket.request_id,
                "payload_hash": payload_hash,
                "artifacts": bindings,
            }
        )
        commit_id = "sha256:" + sha256(envelope).hexdigest()
        params = {
            **_scope(ticket.project, ticket.branch),
            "request": ticket.request_id,
            "actor": ticket.actor,
            "commit": commit_id,
            "payload": payload_hash,
        }
        with _transaction(self._engine) as conn:
            branch = _branch(conn, params)
            request = _request(conn, params)
            existing = _receipt(conn, params)
            if existing is not None:
                if existing.payload_hash != payload_hash:
                    raise CanonConflict("request already committed a different payload")
                return existing
            if (
                not branch["enabled"]
                or branch["initializer"] != ticket.actor
                or branch["authorization_version"] != ticket.authorization_version
                or request["authorization_version"] != ticket.authorization_version
            ):
                raise CanonPermissionError("initializer grant revoked or stale")
            if (
                request["cancelled"]
                or request["execution_version"] != ticket.execution_version
            ):
                raise CanonPermissionError("execution cancelled or stale")
            if branch["head_id"] is not None:
                raise CanonConflict("branch already has a root")
            for binding in bindings:
                kind = binding["type"]
                conn.execute(
                    text("""INSERT INTO anovel_canon.artifacts(project_id,branch_id,artifact_id,artifact_type,encoding,content_hash,content)
                    VALUES (:project,:branch,:id,:type,:encoding,:hash,:content)"""),
                    {
                        **params,
                        **binding,
                        "encoding": "RAW-UTF8"
                        if kind == "RAW_PROSE"
                        else "ANOVELOS-CJSON-1",
                        "content": documents[kind],
                    },
                )
            conn.execute(
                text("""INSERT INTO anovel_canon.commits(project_id,branch_id,commit_id,parent_id,sequence,request_id,payload_hash,canonical_bytes)
                VALUES (:project,:branch,:commit,NULL,0,:request,:payload,:bytes)"""),
                {**params, "bytes": envelope},
            )
            for binding in bindings:
                conn.execute(
                    text(
                        "INSERT INTO anovel_canon.commit_artifacts VALUES (:project,:branch,:commit,:id,:type)"
                    ),
                    {**params, **binding},
                )
            conn.execute(
                text(
                    "INSERT INTO anovel_canon.events VALUES (:project,:branch,:commit,'ROOT_INITIALIZED','ROOT-1')"
                ),
                params,
            )
            for entity in seed.entities:
                conn.execute(
                    text(
                        "INSERT INTO anovel_canon.entities VALUES (:project,:branch,:id,:commit)"
                    ),
                    {**params, "id": entity.id.local_id},
                )
            for relationship in seed.relationships:
                conn.execute(
                    text(
                        "INSERT INTO anovel_canon.relationships VALUES (:project,:branch,:id,:party_a,:party_b,:commit)"
                    ),
                    {
                        **params,
                        "id": relationship.id.local_id,
                        "party_a": relationship.party_a.local_id,
                        "party_b": relationship.party_b.local_id,
                    },
                )
            for fact in seed.facts:
                conn.execute(
                    text(
                        "INSERT INTO anovel_canon.facts VALUES (:project,:branch,:id,:subject,:commit)"
                    ),
                    {
                        **params,
                        "id": fact.id.local_id,
                        "subject": fact.proposition.subject.local_id,
                    },
                )
            conn.execute(
                text(
                    "INSERT INTO anovel_canon.receipts VALUES (:project,:branch,:request,:commit,:payload)"
                ),
                params,
            )
            changed = conn.execute(
                text(
                    "UPDATE anovel_canon.branches SET head_id=:commit WHERE project_id=:project AND branch_id=:branch AND head_id IS NULL"
                ),
                params,
            )
            if changed.rowcount != 1:
                raise CanonConflict("root HEAD compare-and-swap failed")
            receipt = _receipt(conn, params)
            if receipt is None:
                raise CanonIntegrityError("root receipt missing after insert")
            return receipt

    def _cancel(self, ticket: ExecutionTicket) -> CommitReceipt | None:
        if type(ticket) is not ExecutionTicket:
            raise CanonError("expected ExecutionTicket")
        params = {
            **_scope(ticket.project, ticket.branch),
            "request": ticket.request_id,
            "actor": ticket.actor,
        }
        with _transaction(self._engine) as conn:
            _branch(conn, params)
            request = _request(conn, params)
            existing = _receipt(conn, params)
            if existing is not None:
                return existing
            if request["cancelled"]:
                return None
            if (
                request["execution_version"] != ticket.execution_version
                or request["authorization_version"] != ticket.authorization_version
            ):
                raise CanonPermissionError("stale cancellation version")
            conn.execute(
                text(
                    "UPDATE anovel_canon.requests SET cancelled=true,execution_version=execution_version+1 WHERE project_id=:project AND branch_id=:branch AND request_id=:request"
                ),
                params,
            )
            return None

    def _revoke_initializer(self, project: str, branch: str, actor: str) -> int:
        params = {**_scope(project, branch), "actor": identifier(actor)}
        with _transaction(self._engine) as conn:
            current = _branch(conn, params)
            if current["initializer"] != actor:
                raise CanonPermissionError("initializer identity mismatch")
            version = int(current["authorization_version"]) + 1
            conn.execute(
                text(
                    "UPDATE anovel_canon.branches SET enabled=false,authorization_version=:version WHERE project_id=:project AND branch_id=:branch"
                ),
                {**params, "version": version},
            )
            return version
