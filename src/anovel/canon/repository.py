"""Internal PostgreSQL persistence; public Canon writes belong to commit_service.

A privileged database operator can bypass Python. Workers must never receive the
management engine; scoped keys are integrity constraints, not authentication.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, Engine, RowMapping, text

from anovel.canon.chapter import ChapterCandidate, StoredChapter
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
from anovel.domain.delta import FactBaseline, preview_delta

TEST_CHECKS = ["TEST_CANDIDATE_BINDING-1", "TEST_DELTA_PREVIEW-1"]
TEST_AUTHORIZATION = "TEST-AUTHORIZATION-1"


def _stored_json(raw: bytes) -> Any:
    """Normalize malformed retained bytes to a Canon integrity rejection."""
    try:
        return decode_canonical(raw)
    except ValueError as exc:
        raise CanonIntegrityError("invalid retained canonical JSON") from exc


def _test_database(engine: Engine, expected: str) -> None:
    identifier(expected)
    if not expected.startswith("anovel_test_") or engine.dialect.name != "postgresql":
        raise CanonPermissionError("an explicitly isolated test database is required")
    with engine.connect() as conn:
        if conn.execute(text("SELECT current_database()")).scalar_one() != expected:
            raise CanonPermissionError("test database identity mismatch")


def _policy(project: str, branch: str, version: str) -> dict[str, Any]:
    return {
        "kind": "CHAPTER_POLICY",
        "schema_version": "1.0",
        "profile": "ISOLATED_TEST",
        "project": project,
        "branch": branch,
        "version": identifier(version),
        "required_checks": list(TEST_CHECKS),
        "authorization_refs": [TEST_AUTHORIZATION],
    }


def _authority(conn: Connection, params: dict[str, Any]) -> RowMapping:
    row = _one(
        conn,
        "SELECT * FROM anovel_canon.chapter_authorities WHERE project_id=:project AND branch_id=:branch",
        params,
    )
    if row is None:
        raise CanonPermissionError("no chapter grant; initializer is not a writer")
    policy = _stored_json(bytes(row["policy_bytes"]))
    if (
        type(policy) is not dict
        or "version" not in policy
        or policy != _policy(params["project"], params["branch"], policy["version"])
        or sha256(bytes(row["policy_bytes"])).hexdigest() != row["policy_hash"]
        or row["profile"] != "ISOLATED_TEST"
    ):
        raise CanonIntegrityError("chapter policy is malformed or unsupported")
    return row


def _chapter_request(
    conn: Connection, params: dict[str, Any], parent: str
) -> RowMapping:
    row = _request(conn, params)
    if row["purpose"] != "CHAPTER" or row["expected_parent"] != parent:
        raise CanonConflict("request purpose or frozen parent mismatch")
    return row


def _chapter_fence(
    authority: RowMapping, request: RowMapping, ticket: ExecutionTicket
) -> None:
    if (
        not authority["enabled"]
        or authority["actor"] != ticket.actor
        or authority["version"] != ticket.authorization_version
        or request["authorization_version"] != ticket.authorization_version
        or request["cancelled"]
        or request["execution_version"] != ticket.execution_version
    ):
        raise CanonPermissionError(
            "chapter grant/execution revoked, cancelled or stale"
        )


def _binding(ticket: ExecutionTicket, candidate: ChapterCandidate) -> dict[str, Any]:
    if type(ticket) is not ExecutionTicket or type(candidate) is not ChapterCandidate:
        raise CanonError("exact chapter ticket/candidate types required")
    # Reparse all nested evidence and finite operations; never trust an outer id alone.
    ChapterCandidate.from_dict(candidate.to_dict())
    if ticket.project != candidate.project or ticket.branch != candidate.branch:
        raise CanonError("candidate crosses ticket scope")
    return {
        "project": ticket.project,
        "branch": ticket.branch,
        "request_id": ticket.request_id,
        "actor": ticket.actor,
        "parent": candidate.parent_ref,
        "candidate_id": candidate.to_dict()["id"],
        "candidate_version": candidate.version,
        "candidate_hash": candidate.payload_hash,
        "raw_prose_hash": raw_prose_hash(candidate.prose),
        "delta_hash": sha256(canonical_bytes(candidate.delta.to_dict())).hexdigest(),
        "dependencies": [
            item.to_dict()
            for item in sorted(candidate.dependencies, key=lambda item: item.kind)
        ],
        "authorization_version": ticket.authorization_version,
        "execution_version": ticket.execution_version,
    }


def _permit_time(value: object) -> datetime:
    if type(value) is not str:
        raise CanonIntegrityError("invalid permit time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if utc_timestamp(parsed) != value:
            raise ValueError("noncanonical time")
        return parsed
    except (ValueError, OverflowError) as exc:
        raise CanonIntegrityError("invalid permit time") from exc


def _permit_document(
    row: RowMapping, ticket: ExecutionTicket, candidate: ChapterCandidate
) -> dict[str, Any]:
    raw = bytes(row["content"])
    if sha256(raw).hexdigest() != row["content_hash"]:
        raise CanonIntegrityError("permit content hash mismatch")
    body = _stored_json(raw)
    if type(body) is not dict or type(body.get("policy")) is not dict:
        raise CanonIntegrityError("malformed durable permit")
    policy = body["policy"]
    if "version" not in policy or policy != _policy(
        ticket.project, ticket.branch, policy["version"]
    ):
        raise CanonIntegrityError("invalid permit policy")
    issued = _permit_time(body.get("issued_at"))
    expires = _permit_time(body.get("expires_at"))
    if not timedelta(0) < expires - issued <= timedelta(hours=1):
        raise CanonIntegrityError("invalid permit validity interval")
    bind = _binding(ticket, candidate)
    expected = {
        "kind": "COMMIT_PERMIT",
        "schema_version": "1.0",
        "profile": "ISOLATED_TEST",
        "permit_ref": row["permit_ref"],
        "issuer_id": row["issuer_id"],
        "binding": bind,
        "policy": policy,
        "policy_hash": sha256(canonical_bytes(policy)).hexdigest(),
        "issued_at": utc_timestamp(issued),
        "expires_at": utc_timestamp(expires),
        "checks": [
            {
                "id": check,
                "status": "PASS",
                "issuer_id": row["issuer_id"],
                "input_hash": candidate.payload_hash,
                "performed_at": utc_timestamp(issued),
            }
            for check in TEST_CHECKS
        ],
    }
    if raw != canonical_bytes(expected) or (
        row["actor"],
        row["request_id"],
        row["parent_id"],
        row["payload_hash"],
        row["authority_version"],
        row["execution_version"],
        row["policy_hash"],
        row["expires_at"],
    ) != (
        ticket.actor,
        ticket.request_id,
        candidate.parent_ref,
        candidate.payload_hash,
        ticket.authorization_version,
        ticket.execution_version,
        expected["policy_hash"],
        expires,
    ):
        raise CanonPermissionError(
            "permit identity, checks or candidate binding mismatch"
        )
    return body


def _put_artifact(
    conn: Connection, params: dict[str, Any], kind: str, raw: bytes
) -> dict[str, str]:
    digest = sha256(raw).hexdigest()
    identity = kind + ":" + digest
    encoding = "RAW-UTF8" if kind == "RAW_PROSE" else "ANOVELOS-CJSON-1"
    values = {
        **params,
        "id": identity,
        "type": kind,
        "encoding": encoding,
        "hash": digest,
        "content": raw,
    }
    conn.execute(
        text("""INSERT INTO anovel_canon.artifacts(project_id,branch_id,artifact_id,artifact_type,encoding,content_hash,content)
        VALUES (:project,:branch,:id,:type,:encoding,:hash,:content) ON CONFLICT DO NOTHING"""),
        values,
    )
    stored = _one(
        conn,
        "SELECT artifact_type,encoding,content_hash,content FROM anovel_canon.artifacts WHERE project_id=:project AND branch_id=:branch AND artifact_id=:id",
        values,
    )
    if stored is None or (
        stored["artifact_type"],
        stored["encoding"],
        stored["content_hash"],
        bytes(stored["content"]),
    ) != (kind, encoding, digest, raw):
        raise CanonIntegrityError(
            "content-addressed artifact conflicts with stored bytes"
        )
    return {"type": kind, "id": identity, "hash": digest}


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
            envelope = _stored_json(raw)
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
            root_input = _stored_json(contents["ROOT_INPUT"])
            authority = _stored_json(contents["INITIALIZER_AUTHORITY"])
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
            if request.get("purpose", "ROOT") != "ROOT":
                raise CanonConflict("request belongs to another operation")
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
            if request.get("purpose", "ROOT") != "ROOT":
                raise CanonConflict("chapter request cannot initialize a root")
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

    def _configure_chapter_authority(
        self, project: str, branch: str, actor: str, issuer_id: str, policy_version: str
    ) -> int:
        params = {
            **_scope(project, branch),
            "actor": identifier(actor),
            "issuer": identifier(issuer_id),
        }
        policy = canonical_bytes(_policy(project, branch, policy_version))
        with _transaction(self._engine) as conn:
            _branch(conn, params)
            row = _one(
                conn,
                """INSERT INTO anovel_canon.chapter_authorities
                (project_id,branch_id,actor,issuer_id,version,enabled,profile,policy_hash,policy_bytes)
                VALUES (:project,:branch,:actor,:issuer,0,true,'ISOLATED_TEST',:hash,:bytes)
                ON CONFLICT(project_id,branch_id) DO UPDATE SET
                actor=EXCLUDED.actor,issuer_id=EXCLUDED.issuer_id,
                version=chapter_authorities.version+1,enabled=true,
                policy_hash=EXCLUDED.policy_hash,policy_bytes=EXCLUDED.policy_bytes
                RETURNING version""",
                {**params, "hash": sha256(policy).hexdigest(), "bytes": policy},
            )
            if row is None:
                raise CanonIntegrityError("chapter grant was not stored")
            return int(row["version"])

    def _begin_chapter(
        self, project: str, branch: str, actor: str, request_id: str, parent_ref: str
    ) -> ExecutionTicket:
        params = {
            **_scope(project, branch),
            "actor": identifier(actor),
            "request": identifier(request_id),
            "parent": identifier(parent_ref),
        }
        with _transaction(self._engine) as conn:
            branch_row = _branch(conn, params)
            existing = _one(
                conn,
                "SELECT * FROM anovel_canon.requests WHERE project_id=:project AND branch_id=:branch AND request_id=:request",
                params,
            )
            if existing is not None:
                request = _chapter_request(conn, params, parent_ref)
                if _receipt(conn, params) is not None:
                    # A receipt is an already committed fact, not a new grant.
                    return ExecutionTicket(
                        project,
                        branch,
                        request_id,
                        actor,
                        request["authorization_version"],
                        request["execution_version"],
                    )
            authority = _authority(conn, params)
            if not authority["enabled"] or authority["actor"] != actor:
                raise CanonPermissionError("no active chapter authority")
            if existing is None:
                if branch_row["head_id"] != parent_ref:
                    raise CanonConflict("chapter parent is not current HEAD")
                conn.execute(
                    text("""INSERT INTO anovel_canon.requests
                    (project_id,branch_id,request_id,actor,authorization_version,purpose,expected_parent)
                    VALUES (:project,:branch,:request,:actor,:version,'CHAPTER',:parent)"""),
                    {**params, "version": authority["version"]},
                )
            request = _chapter_request(conn, params, parent_ref)
            ticket = ExecutionTicket(
                project,
                branch,
                request_id,
                actor,
                request["authorization_version"],
                request["execution_version"],
            )
            _chapter_fence(authority, request, ticket)
            return ticket

    def _revoke_chapter_authority(self, project: str, branch: str, actor: str) -> int:
        params = {**_scope(project, branch), "actor": identifier(actor)}
        with _transaction(self._engine) as conn:
            _branch(conn, params)
            row = _authority(conn, params)
            if row["actor"] != actor:
                raise CanonPermissionError("chapter actor mismatch")
            version = int(row["version"]) + 1
            conn.execute(
                text(
                    "UPDATE anovel_canon.chapter_authorities SET enabled=false,version=:version WHERE project_id=:project AND branch_id=:branch"
                ),
                {**params, "version": version},
            )
            return version

    def load_baseline(self, project: str, branch: str, commit_id: str) -> FactBaseline:
        params = {**_scope(project, branch), "commit": identifier(commit_id)}
        with self._engine.connect() as conn:
            row = _one(
                conn,
                "SELECT parent_id FROM anovel_canon.commits WHERE project_id=:project AND branch_id=:branch AND commit_id=:commit",
                params,
            )
            if row is None:
                raise CanonIntegrityError("parent commit is not in this scope")
        if row["parent_id"] is None:
            root = self.load_root(project, branch, commit_id)
            return FactBaseline.from_world_facts(
                project, branch, commit_id, root.seed.facts
            )
        stored = self.load_commit(project, branch, commit_id)
        return FactBaseline(project, branch, commit_id, stored.state.facts)

    def _issue_permit(
        self,
        ticket: ExecutionTicket,
        candidate: ChapterCandidate,
        issuer_id: str,
        ttl_seconds: int,
    ) -> str:
        binding = _binding(ticket, candidate)
        identifier(issuer_id)
        if type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 3600:
            raise CanonError("permit TTL must be an integer from1 to3600 seconds")
        baseline = self.load_baseline(
            ticket.project, ticket.branch, candidate.parent_ref
        )
        params = {
            **_scope(ticket.project, ticket.branch),
            "actor": ticket.actor,
            "request": ticket.request_id,
        }
        with _transaction(self._engine) as conn:
            branch = _branch(conn, params)
            request = _chapter_request(conn, params, candidate.parent_ref)
            authority = _authority(conn, params)
            _chapter_fence(authority, request, ticket)
            if authority["issuer_id"] != issuer_id:
                raise CanonPermissionError("issuer is not enrolled for this branch")
            if branch["head_id"] != candidate.parent_ref:
                raise CanonConflict("permit parent is stale")
            # These are actual deterministic P2 checks, never a claim of Q0-Q3.
            preview_delta(
                baseline,
                candidate.delta,
                source_id=candidate.id,
                authorization_refs=frozenset([TEST_AUTHORIZATION]),
            )
            issued = (
                conn.execute(text("SELECT clock_timestamp()"))
                .scalar_one()
                .astimezone(timezone.utc)
            )
            expires = issued + timedelta(seconds=ttl_seconds)
            ref = "test-permit:" + uuid4().hex
            policy = _stored_json(bytes(authority["policy_bytes"]))
            body = {
                "kind": "COMMIT_PERMIT",
                "schema_version": "1.0",
                "profile": "ISOLATED_TEST",
                "permit_ref": ref,
                "issuer_id": issuer_id,
                "binding": binding,
                "policy": policy,
                "policy_hash": authority["policy_hash"],
                "issued_at": utc_timestamp(issued),
                "expires_at": utc_timestamp(expires),
                "checks": [
                    {
                        "id": check,
                        "status": "PASS",
                        "issuer_id": issuer_id,
                        "input_hash": candidate.payload_hash,
                        "performed_at": utc_timestamp(issued),
                    }
                    for check in TEST_CHECKS
                ],
            }
            raw = canonical_bytes(body)
            conn.execute(
                text("""INSERT INTO anovel_canon.commit_permits
                (project_id,branch_id,permit_ref,request_id,actor,parent_id,payload_hash,issuer_id,authority_version,execution_version,policy_hash,expires_at,content_hash,content)
                VALUES (:project,:branch,:ref,:request,:actor,:parent,:payload,:issuer,:authority,:execution,:policy,:expires,:hash,:bytes)"""),
                {
                    **params,
                    "ref": ref,
                    "parent": candidate.parent_ref,
                    "payload": candidate.payload_hash,
                    "issuer": issuer_id,
                    "authority": ticket.authorization_version,
                    "execution": ticket.execution_version,
                    "policy": authority["policy_hash"],
                    "expires": expires,
                    "hash": sha256(raw).hexdigest(),
                    "bytes": raw,
                },
            )
            return ref

    def _revoke_permit(
        self, project: str, branch: str, permit_ref: str, issuer_id: str
    ) -> None:
        params = {**_scope(project, branch), "ref": identifier(permit_ref)}
        with _transaction(self._engine) as conn:
            _branch(conn, params)
            row = _one(
                conn,
                "SELECT issuer_id,revoked FROM anovel_canon.commit_permits WHERE project_id=:project AND branch_id=:branch AND permit_ref=:ref",
                params,
            )
            if row is None or row["issuer_id"] != issuer_id:
                raise CanonPermissionError("permit not owned by this issuer")
            if not row["revoked"]:
                conn.execute(
                    text(
                        "UPDATE anovel_canon.commit_permits SET revoked=true WHERE project_id=:project AND branch_id=:branch AND permit_ref=:ref"
                    ),
                    params,
                )

    def _commit_chapter(
        self,
        ticket: ExecutionTicket,
        candidate: ChapterCandidate,
        permit_ref: str,
        *,
        accept_test: bool,
    ) -> CommitReceipt:
        _binding(ticket, candidate)
        identifier(permit_ref)
        payload = candidate.payload_bytes()
        payload_hash = candidate.payload_hash
        baseline = self.load_baseline(
            ticket.project, ticket.branch, candidate.parent_ref
        )
        params = {
            **_scope(ticket.project, ticket.branch),
            "request": ticket.request_id,
            "actor": ticket.actor,
            "ref": permit_ref,
        }
        with _transaction(self._engine) as conn:
            branch = _branch(conn, params)
            request = _chapter_request(conn, params, candidate.parent_ref)
            receipt = _receipt(conn, params)
            if receipt is not None:
                if receipt.payload_hash != payload_hash:
                    raise CanonConflict(
                        "request already accepted a different candidate"
                    )
                return receipt
            if not accept_test:
                raise CanonPermissionError("production does not accept P2 test Permit")
            authority = _authority(conn, params)
            _chapter_fence(authority, request, ticket)
            permit = _one(
                conn,
                "SELECT * FROM anovel_canon.commit_permits WHERE project_id=:project AND branch_id=:branch AND permit_ref=:ref",
                params,
            )
            if permit is None:
                raise CanonPermissionError(
                    "durable Permit is required; caller ALLOW is not authority"
                )
            permit_body = _permit_document(permit, ticket, candidate)
            now = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
            if (
                now < _permit_time(permit_body["issued_at"])
                or permit["revoked"]
                or now >= permit["expires_at"]
                or (
                    permit["issuer_id"] != authority["issuer_id"]
                    or permit["policy_hash"] != authority["policy_hash"]
                )
            ):
                raise CanonPermissionError(
                    "permit revoked, expired or no longer current"
                )
            if branch["head_id"] != candidate.parent_ref:
                raise CanonConflict("chapter parent is not current HEAD")
            preview = preview_delta(
                baseline,
                candidate.delta,
                source_id=candidate.id,
                authorization_refs=frozenset([TEST_AUTHORIZATION]),
            )
            parent = _one(
                conn,
                "SELECT sequence FROM anovel_canon.commits WHERE project_id=:project AND branch_id=:branch AND commit_id=:parent",
                {**params, "parent": candidate.parent_ref},
            )
            if parent is None:
                raise CanonIntegrityError("parent disappeared")
            sequence = int(parent["sequence"]) + 1
            docs = {
                "CHAPTER_INPUT": payload,
                "RAW_PROSE": candidate.prose,
                "NARRATIVE_DELTA": canonical_bytes(candidate.delta.to_dict()),
                "DEPENDENCY_BUNDLE": canonical_bytes(
                    {
                        "kind": "DEPENDENCY_BUNDLE",
                        "schema_version": "1.0",
                        "project": ticket.project,
                        "branch": ticket.branch,
                        "items": [
                            x.to_dict()
                            for x in sorted(
                                candidate.dependencies, key=lambda x: x.kind
                            )
                        ],
                    }
                ),
                "COMMIT_PERMIT": bytes(permit["content"]),
                "STATE_SNAPSHOT": canonical_bytes(preview.candidate.to_dict()),
            }
            bindings = [
                _put_artifact(conn, params, kind, raw)
                for kind, raw in sorted(docs.items())
            ]
            envelope = canonical_bytes(
                {
                    "kind": "CHAPTER_COMMIT",
                    "schema_version": "1.0",
                    "producer": "anovel.canon.chapter/1.0",
                    "project": ticket.project,
                    "branch": ticket.branch,
                    "parent": candidate.parent_ref,
                    "sequence": sequence,
                    "request_id": ticket.request_id,
                    "payload_hash": payload_hash,
                    "artifacts": bindings,
                }
            )
            commit = "sha256:" + sha256(envelope).hexdigest()
            values = {
                **params,
                "commit": commit,
                "parent": candidate.parent_ref,
                "sequence": sequence,
                "payload": payload_hash,
                "bytes": envelope,
            }
            conn.execute(
                text("""INSERT INTO anovel_canon.commits
                (project_id,branch_id,commit_id,parent_id,sequence,request_id,payload_hash,canonical_bytes)
                VALUES (:project,:branch,:commit,:parent,:sequence,:request,:payload,:bytes)"""),
                values,
            )
            for item in bindings:
                conn.execute(
                    text(
                        "INSERT INTO anovel_canon.commit_artifacts VALUES (:project,:branch,:commit,:id,:type)"
                    ),
                    {**values, **item},
                )
            conn.execute(
                text(
                    "INSERT INTO anovel_canon.events VALUES (:project,:branch,:commit,'CHAPTER_COMMITTED','FACT_DELTA-1')"
                ),
                values,
            )
            conn.execute(
                text(
                    "INSERT INTO anovel_canon.receipts VALUES (:project,:branch,:request,:commit,:payload)"
                ),
                values,
            )
            updated = conn.execute(
                text(
                    "UPDATE anovel_canon.branches SET head_id=:commit WHERE project_id=:project AND branch_id=:branch AND head_id=:parent"
                ),
                values,
            )
            if updated.rowcount != 1:
                raise CanonConflict("chapter HEAD compare-and-swap failed")
            receipt = _receipt(conn, params)
            if receipt is None:
                raise CanonIntegrityError("chapter receipt missing")
            return receipt

    def load_commit(self, project: str, branch: str, commit_id: str) -> StoredChapter:
        params = {**_scope(project, branch), "commit": identifier(commit_id)}
        with self._engine.connect() as conn:
            commit = _one(
                conn,
                "SELECT * FROM anovel_canon.commits WHERE project_id=:project AND branch_id=:branch AND commit_id=:commit",
                params,
            )
            if commit is None or commit["parent_id"] is None or commit["sequence"] < 1:
                raise CanonIntegrityError("scoped chapter commit does not exist")
            raw = bytes(commit["canonical_bytes"])
            if "sha256:" + sha256(raw).hexdigest() != commit_id:
                raise CanonIntegrityError("chapter commit hash mismatch")
            rows = (
                conn.execute(
                    text("""SELECT a.* FROM anovel_canon.commit_artifacts l
                JOIN anovel_canon.artifacts a USING(project_id,branch_id,artifact_id,artifact_type)
                WHERE l.project_id=:project AND l.branch_id=:branch AND l.commit_id=:commit ORDER BY a.artifact_type"""),
                    params,
                )
                .mappings()
                .all()
            )
            docs: dict[str, bytes] = {}
            bindings = []
            for row in rows:
                content = bytes(row["content"])
                kind = row["artifact_type"]
                digest = sha256(content).hexdigest()
                if (
                    row["artifact_id"] != kind + ":" + digest
                    or row["content_hash"] != digest
                    or row["encoding"]
                    != ("RAW-UTF8" if kind == "RAW_PROSE" else "ANOVELOS-CJSON-1")
                ):
                    raise CanonIntegrityError("chapter artifact identity mismatch")
                docs[kind] = content
                bindings.append(
                    {"type": kind, "id": row["artifact_id"], "hash": digest}
                )
            if set(docs) != {
                "CHAPTER_INPUT",
                "RAW_PROSE",
                "NARRATIVE_DELTA",
                "DEPENDENCY_BUNDLE",
                "COMMIT_PERMIT",
                "STATE_SNAPSHOT",
            }:
                raise CanonIntegrityError("chapter evidence closure incomplete")
            expected = {
                "kind": "CHAPTER_COMMIT",
                "schema_version": "1.0",
                "producer": "anovel.canon.chapter/1.0",
                "project": project,
                "branch": branch,
                "parent": commit["parent_id"],
                "sequence": commit["sequence"],
                "request_id": commit["request_id"],
                "payload_hash": commit["payload_hash"],
                "artifacts": bindings,
            }
            if _stored_json(raw) != expected:
                raise CanonIntegrityError("chapter envelope mismatch")
            candidate = ChapterCandidate.from_dict(_stored_json(docs["CHAPTER_INPUT"]))
            state = FactBaseline.from_dict(_stored_json(docs["STATE_SNAPSHOT"]))
            dependencies = canonical_bytes(
                {
                    "kind": "DEPENDENCY_BUNDLE",
                    "schema_version": "1.0",
                    "project": project,
                    "branch": branch,
                    "items": [
                        x.to_dict()
                        for x in sorted(candidate.dependencies, key=lambda x: x.kind)
                    ],
                }
            )
            if (
                candidate.project != project
                or candidate.branch != branch
                or candidate.parent_ref != commit["parent_id"]
                or candidate.payload_hash != commit["payload_hash"]
                or candidate.prose != docs["RAW_PROSE"]
                or canonical_bytes(candidate.delta.to_dict()) != docs["NARRATIVE_DELTA"]
                or dependencies != docs["DEPENDENCY_BUNDLE"]
                or state.project != project
                or state.branch != branch
                or state.parent_ref != candidate.parent_ref
            ):
                raise CanonIntegrityError("chapter evidence cross-binding mismatch")
            permit_body = _stored_json(docs["COMMIT_PERMIT"])
            if (
                type(permit_body) is not dict
                or type(permit_body.get("permit_ref")) is not str
            ):
                raise CanonIntegrityError("invalid retained permit")
            permit = _one(
                conn,
                "SELECT * FROM anovel_canon.commit_permits WHERE project_id=:project AND branch_id=:branch AND permit_ref=:ref",
                {**params, "ref": permit_body["permit_ref"]},
            )
            if permit is None or bytes(permit["content"]) != docs["COMMIT_PERMIT"]:
                raise CanonIntegrityError("durable retained Permit missing")
            ticket = ExecutionTicket(
                project,
                branch,
                commit["request_id"],
                permit["actor"],
                permit["authority_version"],
                permit["execution_version"],
            )
            _permit_document(permit, ticket, candidate)
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
                or tuple(event.values()) != ("CHAPTER_COMMITTED", "FACT_DELTA-1")
            ):
                raise CanonIntegrityError("chapter event/receipt mismatch")
            return StoredChapter(receipt, candidate, state, docs["COMMIT_PERMIT"])

    def review_submission(
        self, ticket: ExecutionTicket, candidate: ChapterCandidate
    ) -> dict[str, Any]:
        _binding(ticket, candidate)
        blockers = []
        try:
            baseline = self.load_baseline(
                ticket.project, ticket.branch, candidate.parent_ref
            )
            params = {
                **_scope(ticket.project, ticket.branch),
                "request": ticket.request_id,
                "actor": ticket.actor,
            }
            with self._engine.connect() as conn:
                authority = _authority(conn, params)
                request = _chapter_request(conn, params, candidate.parent_ref)
                _chapter_fence(authority, request, ticket)
                head = _one(
                    conn,
                    "SELECT head_id FROM anovel_canon.branches WHERE project_id=:project AND branch_id=:branch",
                    params,
                )
                if head is None or head["head_id"] != candidate.parent_ref:
                    raise CanonConflict("candidate parent is stale")
            preview_delta(
                baseline,
                candidate.delta,
                source_id=candidate.id,
                authorization_refs=frozenset([TEST_AUTHORIZATION]),
            )
        except ValueError as exc:
            blockers.append(str(exc))
        return {
            "prose": candidate.prose.decode("utf-8"),
            "delta": candidate.delta.to_dict(),
            "parent": candidate.parent_ref,
            "version": candidate.version,
            "candidate_hash": candidate.payload_hash,
            "blockers": blockers,
            "permit_issued": False,
        }
