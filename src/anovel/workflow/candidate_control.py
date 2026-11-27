"""Isolated SQLite control for local Draft candidate replacement diagnostics."""

from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import ClassVar, Literal

from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.canon.models import ExecutionTicket, identifier
from anovel.domain.identity import EntityId

from .chapter_revision import ChapterRevision
from .models import WorkflowError
from .store import (
    WorkflowStore,
    _inode,
    _make_directory,
    _private_directory,
    _private_file,
)

_APPLICATION_ID = 0x414E5643
_REQUESTS = """CREATE TABLE candidate_requests (
    project TEXT NOT NULL, branch TEXT NOT NULL, request_id TEXT NOT NULL,
    actor TEXT NOT NULL, chapter_id TEXT NOT NULL, parent_ref TEXT NOT NULL,
    authorization_version INTEGER NOT NULL CHECK (authorization_version >= 0),
    execution_version INTEGER NOT NULL CHECK (execution_version >= 0),
    PRIMARY KEY (project, branch, request_id)
)"""
_BINDINGS = """CREATE TABLE candidate_bindings (
    project TEXT NOT NULL, branch TEXT NOT NULL, request_id TEXT NOT NULL,
    execution_version INTEGER NOT NULL CHECK (execution_version > 0),
    operation_id TEXT NOT NULL, payload BLOB NOT NULL, payload_hash TEXT NOT NULL,
    PRIMARY KEY (project, branch, request_id, execution_version),
    UNIQUE (project, branch, request_id, operation_id),
    FOREIGN KEY (project, branch, request_id)
        REFERENCES candidate_requests(project, branch, request_id)
)"""
_DIGEST = re.compile(r"[0-9a-f]{64}")
_PARENT = re.compile(r"sha256:[0-9a-f]{64}")
_SQLITE_MAX = (1 << 63) - 1


def _hash(value: str) -> None:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise ValueError


def _number(value: int, lower: int = 0) -> None:
    if type(value) is not int or not lower <= value <= _SQLITE_MAX:
        raise ValueError


@dataclass(frozen=True, slots=True)
class CandidateBindingReceipt:
    """History of one local control update; no Permit or acceptance capability."""

    project: str
    branch: str
    request_id: str
    actor: str
    authorization_version: int
    execution_version: int
    chapter_id: str
    parent_ref: str
    operation_id: str
    expected_revision_hash: str | None
    revision_hash: str
    candidate_payload_hash: str
    draft_version: int

    artifact_state: ClassVar[Literal["DRAFT"]] = "DRAFT"
    can_issue_permit: ClassVar[Literal[False]] = False
    can_commit: ClassVar[Literal[False]] = False
    can_dispatch: ClassVar[Literal[False]] = False
    accepted: ClassVar[Literal[False]] = False
    published: ClassVar[Literal[False]] = False

    def __post_init__(self) -> None:
        _number(self.execution_version, 1)
        _number(self.authorization_version)
        for value in (self.project, self.branch, self.request_id, self.actor):
            identifier(value)
        _number(self.draft_version, 1)
        identifier(self.chapter_id)
        identifier(self.operation_id)
        if _PARENT.fullmatch(self.parent_ref) is None:
            raise ValueError
        if self.expected_revision_hash is not None:
            _hash(self.expected_revision_hash)
        _hash(self.revision_hash)
        _hash(self.candidate_payload_hash)

    def payload_bytes(self) -> bytes:
        return canonical_bytes(
            {
                "record_type": "offline_candidate_binding_receipt",
                "schema_version": "1.0",
                **asdict(self),
            }
        )

    @classmethod
    def from_bytes(cls, raw: bytes) -> CandidateBindingReceipt:
        data = decode_canonical(raw)
        if not isinstance(data, dict):
            raise ValueError
        if (
            data.pop("record_type", None) != "offline_candidate_binding_receipt"
            or data.pop("schema_version", None) != "1.0"
        ):
            raise ValueError
        receipt = cls(**data)
        if receipt.payload_bytes() != raw:
            raise ValueError
        return receipt


def _scope(ticket: ExecutionTicket) -> tuple[str, str, str]:
    if type(ticket) is not ExecutionTicket:
        raise WorkflowError("INVALID_CANDIDATE_CONTROL_TICKET")
    try:
        _number(ticket.authorization_version)
        _number(ticket.execution_version)
    except ValueError:
        raise WorkflowError("INVALID_CANDIDATE_CONTROL_TICKET") from None
    return ticket.project, ticket.branch, ticket.request_id


def _revision(revision: ChapterRevision) -> ChapterRevision:
    if type(revision) is not ChapterRevision:
        raise WorkflowError("INVALID_CANDIDATE_CONTROL_REVISION")
    return ChapterRevision.from_bytes(revision.payload_bytes())


def _command(
    ticket: ExecutionTicket,
    revision: ChapterRevision,
    operation_id: str,
    expected_revision_hash: str | None,
) -> CandidateBindingReceipt:
    scope = _scope(ticket)
    try:
        return CandidateBindingReceipt(
            *scope,
            ticket.actor,
            ticket.authorization_version,
            ticket.execution_version + 1,
            revision.chapter_id.local_id,
            revision.candidate.parent_ref,
            operation_id,
            expected_revision_hash,
            revision.record_hash,
            revision.candidate.payload_hash,
            revision.version,
        )
    except (TypeError, ValueError):
        raise WorkflowError("INVALID_CANDIDATE_BINDING_INPUT") from None


def _existing_operation(
    history: list[CandidateBindingReceipt], command: CandidateBindingReceipt
) -> CandidateBindingReceipt | None:
    saved = next(
        (item for item in history if item.operation_id == command.operation_id), None
    )
    if saved is not None and saved != command:
        raise WorkflowError("CANDIDATE_BINDING_OPERATION_CONFLICT")
    return saved


class OfflineCandidateControl:
    """Dedicated private control store. Inputs come from the local Draft reader."""

    def __init__(self, path: Path) -> None:
        if (
            not isinstance(path, Path)
            or path.name in {"", ":memory:"}
            or ".." in path.parts
        ):
            raise WorkflowError("INVALID_CANDIDATE_CONTROL_STORE")
        self.path = path.absolute()
        try:
            _make_directory(self.path.parent)
            self._directory = _inode(_private_directory(self.path.parent))
            try:
                fd = os.open(
                    self.path,
                    os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                )
            except FileExistsError:
                info = self.path.lstat()
                created = False
            else:
                with closing(os.fdopen(fd, "rb")) as file:
                    info = os.fstat(file.fileno())
                    os.fsync(file.fileno())
                WorkflowStore._sync_directory(self.path.parent)
                created = True
            _private_file(info)
            self._file = _inode(info)
        except OSError:
            raise WorkflowError("CANDIDATE_CONTROL_UNAVAILABLE") from None
        with self._connect(write=created, initialize=created) as db:
            if created:
                db.execute(_REQUESTS)
                db.execute(_BINDINGS)
                db.execute(f"PRAGMA application_id={_APPLICATION_ID}")
            self._require_schema(db)

    def _verify_file(self) -> None:
        if _inode(_private_directory(self.path.parent)) != self._directory:
            raise WorkflowError("CANDIDATE_CONTROL_STORE_CHANGED")
        info = self.path.lstat()
        _private_file(info)
        if _inode(info) != self._file:
            raise WorkflowError("CANDIDATE_CONTROL_STORE_CHANGED")
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = self.path.with_name(self.path.name + suffix)
            try:
                _private_file(sidecar.lstat())
            except FileNotFoundError:
                pass

    @contextmanager
    def _connect(
        self, *, write: bool = False, initialize: bool = False
    ) -> Iterator[sqlite3.Connection]:
        try:
            self._verify_file()
            with closing(
                sqlite3.connect(
                    self.path.as_uri() + ("?mode=rw" if write else "?mode=ro"),
                    uri=True,
                    timeout=5,
                    isolation_level=None,
                )
            ) as db:
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA foreign_keys=ON")
                db.execute("PRAGMA synchronous=FULL")
                if not write:
                    db.execute("PRAGMA query_only=ON")
                db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
                if not initialize:
                    self._require_schema(db)
                yield db
                self._verify_file()
                db.commit()
        except (OSError, sqlite3.Error):
            raise WorkflowError("CANDIDATE_CONTROL_UNAVAILABLE") from None

    @staticmethod
    def _require_schema(db: sqlite3.Connection) -> None:
        application = db.execute("PRAGMA application_id").fetchone()[0]
        table_defs = dict(
            db.execute(
                "SELECT name, sql FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        )
        if application != _APPLICATION_ID or table_defs != {
            "candidate_requests": _REQUESTS,
            "candidate_bindings": _BINDINGS,
        }:
            raise WorkflowError("INVALID_CANDIDATE_CONTROL_STORE")

    @staticmethod
    def _request(
        db: sqlite3.Connection, scope: tuple[str, str, str]
    ) -> sqlite3.Row | None:
        row: sqlite3.Row | None = db.execute(
            "SELECT * FROM candidate_requests WHERE project=? AND branch=? AND request_id=?",
            scope,
        ).fetchone()
        return row

    @staticmethod
    def _bound_request(
        db: sqlite3.Connection, ticket: ExecutionTicket, revision: ChapterRevision
    ) -> sqlite3.Row:
        row = OfflineCandidateControl._request(db, _scope(ticket))
        if row is None:
            raise WorkflowError("CANDIDATE_CONTROL_REQUEST_UNAVAILABLE")
        if (
            row["actor"],
            row["chapter_id"],
            row["parent_ref"],
            ticket.project,
            ticket.branch,
        ) != (
            ticket.actor,
            revision.chapter_id.local_id,
            revision.candidate.parent_ref,
            revision.project,
            revision.branch,
        ):
            raise WorkflowError("CANDIDATE_CONTROL_SCOPE_MISMATCH")
        if row["authorization_version"] != ticket.authorization_version:
            raise WorkflowError("CANDIDATE_BINDING_STALE")
        return row

    @staticmethod
    def _history(
        db: sqlite3.Connection, ticket: ExecutionTicket, row: sqlite3.Row
    ) -> list[CandidateBindingReceipt]:
        scope = _scope(ticket)
        try:
            _number(row["execution_version"])
            history: list[CandidateBindingReceipt] = []
            for index, saved in enumerate(
                db.execute(
                    "SELECT * FROM candidate_bindings WHERE project=? AND branch=? "
                    "AND request_id=? ORDER BY execution_version",
                    scope,
                ),
                1,
            ):
                raw = saved["payload"]
                if (
                    type(raw) is not bytes
                    or sha256(raw).hexdigest() != saved["payload_hash"]
                ):
                    raise ValueError
                receipt = CandidateBindingReceipt.from_bytes(raw)
                previous = history[-1] if history else None
                if (
                    (receipt.project, receipt.branch, receipt.request_id) != scope
                    or receipt.actor != row["actor"]
                    or receipt.authorization_version != row["authorization_version"]
                    or receipt.execution_version != index
                    or receipt.execution_version != saved["execution_version"]
                    or receipt.operation_id != saved["operation_id"]
                    or receipt.chapter_id != row["chapter_id"]
                    or receipt.parent_ref != row["parent_ref"]
                    or receipt.expected_revision_hash
                    != (previous.revision_hash if previous else None)
                    or (
                        previous is not None
                        and receipt.draft_version <= previous.draft_version
                    )
                ):
                    raise ValueError
                history.append(receipt)
            if len(history) != row["execution_version"]:
                raise ValueError
        except (KeyError, TypeError, ValueError, RecursionError):
            raise WorkflowError("CORRUPT_CANDIDATE_BINDING") from None
        return history

    def begin(
        self, ticket: ExecutionTicket, *, chapter_id: EntityId, parent_ref: str
    ) -> None:
        """Register the fixed local request. Reopening it leaves its version alone."""
        scope = _scope(ticket)
        if (
            ticket.execution_version != 0
            or type(chapter_id) is not EntityId
            or chapter_id.project != ticket.project
            or type(parent_ref) is not str
            or _PARENT.fullmatch(parent_ref) is None
        ):
            raise WorkflowError("INVALID_CANDIDATE_CONTROL_REQUEST")
        identity = (
            ticket.actor,
            chapter_id.local_id,
            parent_ref,
            ticket.authorization_version,
        )
        with self._connect(write=True) as db:
            row = self._request(db, scope)
            if row is None:
                db.execute(
                    "INSERT INTO candidate_requests VALUES (?,?,?,?,?,?,?,0)",
                    (*scope, *identity),
                )
            elif (
                row["actor"],
                row["chapter_id"],
                row["parent_ref"],
                row["authorization_version"],
            ) != identity:
                raise WorkflowError("CANDIDATE_CONTROL_SCOPE_MISMATCH")

    def bind(
        self,
        ticket: ExecutionTicket,
        revision: ChapterRevision,
        *,
        operation_id: str,
        expected_revision_hash: str | None,
    ) -> CandidateBindingReceipt | None:
        """Apply a current binding or recover the same operation's receipt."""
        revision = _revision(revision)
        command = _command(ticket, revision, operation_id, expected_revision_hash)
        scope = _scope(ticket)
        with self._connect(write=True) as db:
            row = self._bound_request(db, ticket, revision)
            history = self._history(db, ticket, row)
            receipt = _existing_operation(history, command)
            if receipt is not None:
                return receipt
            previous = history[-1] if history else None
            if row[
                "execution_version"
            ] != ticket.execution_version or expected_revision_hash != (
                previous.revision_hash if previous else None
            ):
                raise WorkflowError("CANDIDATE_BINDING_STALE")
            if previous is not None and previous.revision_hash == command.revision_hash:
                if previous.candidate_payload_hash != command.candidate_payload_hash:
                    raise WorkflowError("CORRUPT_CANDIDATE_BINDING")
                return None
            if previous is not None and command.draft_version <= previous.draft_version:
                raise WorkflowError("CANDIDATE_BINDING_STALE")
            raw = command.payload_bytes()
            db.execute(
                "INSERT INTO candidate_bindings VALUES (?,?,?,?,?,?,?)",
                (
                    *scope,
                    command.execution_version,
                    operation_id,
                    raw,
                    sha256(raw).hexdigest(),
                ),
            )
            changed = db.execute(
                "UPDATE candidate_requests SET execution_version=? WHERE project=? "
                "AND branch=? AND request_id=? AND execution_version=?",
                (command.execution_version, *scope, ticket.execution_version),
            ).rowcount
            if changed != 1:
                raise WorkflowError("CANDIDATE_BINDING_STALE")
            return command

    def recover(
        self,
        ticket: ExecutionTicket,
        revision: ChapterRevision,
        *,
        operation_id: str,
        expected_revision_hash: str | None,
    ) -> CandidateBindingReceipt:
        """Read an exact historical operation without updating current state."""
        revision = _revision(revision)
        command = _command(ticket, revision, operation_id, expected_revision_hash)
        with self._connect() as db:
            row = self._bound_request(db, ticket, revision)
            receipt = _existing_operation(self._history(db, ticket, row), command)
            if receipt is None:
                raise WorkflowError("CANDIDATE_BINDING_OPERATION_UNAVAILABLE")
            return receipt

    def inspect(
        self, ticket: ExecutionTicket, revision: ChapterRevision
    ) -> CandidateBindingReceipt:
        """Read the exact current version; matching grants no submit capability."""
        revision = _revision(revision)
        with self._connect() as db:
            row = self._bound_request(db, ticket, revision)
            history = self._history(db, ticket, row)
            if row["execution_version"] != ticket.execution_version:
                raise WorkflowError("CANDIDATE_BINDING_STALE")
            if not history:
                raise WorkflowError("CANDIDATE_BINDING_REQUIRED")
            receipt = history[-1]
            if (
                receipt.revision_hash != revision.record_hash
                or receipt.candidate_payload_hash != revision.candidate.payload_hash
                or receipt.draft_version != revision.version
            ):
                raise WorkflowError("CANDIDATE_BINDING_STALE")
            return receipt
