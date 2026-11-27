"""Private SQLite Draft snapshots with scoped reads and compare-and-swap writes.

This store retains offline evidence. It grants no Canon or acceptance authority.
Run locks are persistent files: unlinking a lock after use could let two
processes hold different inodes for the same logical run.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
import sqlite3
import stat
import threading
from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, cast

from anovel.canon.identity import decode_canonical

from .chapter_revision import ChapterRevision
from .models import WORKFLOW_STATES, WorkflowError, WorkflowSnapshot

if TYPE_CHECKING:
    from anovel.canon.chapter import ChapterCandidate
    from anovel.domain.identity import EntityId
    from anovel.quality.q0 import Q0Run
    from anovel.quality.q1 import Q1Run
    from anovel.quality.q2 import Q2Run
    from anovel.quality.q3 import Q3Run
    from anovel.quality.revision_q0 import RevisionQ0Run
    from anovel.quality.revision_q123 import RevisionQ123Run

    from .extractor import ExtractionObservation
    from .generation import SceneGenerationSnapshot
    from .written_draft import WrittenDraftRevision

_SCENE_DECODE_LIMIT = 16
_SCENE_DECODE_CACHE: OrderedDict[str, tuple[bytes, SceneGenerationSnapshot]] = (
    OrderedDict()
)
_SCENE_DECODE_LOCK = threading.Lock()

_OBSERVATION_DECODE_LIMIT = 8
_OBSERVATION_DECODE_MAX_PAYLOAD = 4 * 1024 * 1024
_observation_decodes: ContextVar[
    OrderedDict[tuple[Callable[[bytes], object], bytes], object] | None
] = ContextVar("retained_observation_decodes", default=None)


def _decode_retained_payload[T](raw: bytes, decoder: Callable[[bytes], T]) -> T:
    cache = _observation_decodes.get()
    if cache is None or len(raw) > _OBSERVATION_DECODE_MAX_PAYLOAD:
        return decoder(raw)
    # Reuse only successful typed decodes of exactly the same bytes. Callers
    # still validate the freshly read row's digest, index fields and sources.
    key = (decoder, raw)
    if key in cache:
        cache.move_to_end(key)
        return cast(T, cache[key])
    decoded = decoder(raw)
    cache[key] = decoded
    if len(cache) > _OBSERVATION_DECODE_LIMIT:
        cache.popitem(last=False)
    return decoded


_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY NOT NULL,
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    payload BLOB NOT NULL,
    payload_hash TEXT NOT NULL
)
"""
_SCENE_SCHEMA = """
CREATE TABLE IF NOT EXISTS scene_generations (
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    payload BLOB NOT NULL,
    payload_hash TEXT NOT NULL,
    PRIMARY KEY (run_id, step_id),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
)
"""
_EXTRACTION_SCHEMA = """
CREATE TABLE IF NOT EXISTS extraction_observations (
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    assembly_hash TEXT NOT NULL,
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    payload BLOB NOT NULL,
    payload_hash TEXT NOT NULL,
    PRIMARY KEY (run_id, step_id, assembly_hash),
    FOREIGN KEY (run_id, step_id) REFERENCES scene_generations(run_id, step_id)
)
"""
_CHAPTER_REVISION_SCHEMA = """
CREATE TABLE IF NOT EXISTS chapter_revisions (
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 1),
    request_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    assembly_hash TEXT NOT NULL,
    previous_revision_hash TEXT,
    payload BLOB NOT NULL,
    payload_hash TEXT NOT NULL,
    PRIMARY KEY (project, branch, chapter_id, version),
    UNIQUE (project, branch, chapter_id, request_id),
    FOREIGN KEY (run_id, step_id, assembly_hash)
        REFERENCES extraction_observations(run_id, step_id, assembly_hash)
)
"""
_WRITTEN_DRAFT_SCHEMA = """
CREATE TABLE IF NOT EXISTS written_draft_revisions (
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 1),
    run_id TEXT NOT NULL,
    previous_revision_hash TEXT,
    payload BLOB NOT NULL,
    payload_hash TEXT NOT NULL,
    PRIMARY KEY (project, branch, chapter_id, version),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
)
"""
_REVISION_Q0_SCHEMA = """
CREATE TABLE IF NOT EXISTS revision_q0_executions (
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    revision_hash TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    version INTEGER NOT NULL,
    payload BLOB NOT NULL,
    payload_hash TEXT NOT NULL,
    PRIMARY KEY (project, branch, chapter_id, revision_hash, policy_hash),
    FOREIGN KEY (project, branch, chapter_id, version)
        REFERENCES chapter_revisions(project, branch, chapter_id, version)
)
"""
_REVISION_Q123_SCHEMA = """
CREATE TABLE IF NOT EXISTS revision_q123_executions (
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    revision_hash TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    annotations_hash TEXT NOT NULL,
    version INTEGER NOT NULL,
    payload BLOB NOT NULL,
    payload_hash TEXT NOT NULL,
    PRIMARY KEY (project, branch, chapter_id, revision_hash, policy_hash, annotations_hash),
    FOREIGN KEY (project, branch, chapter_id, version)
        REFERENCES chapter_revisions(project, branch, chapter_id, version)
)
"""
_Q0_SCHEMA = """
CREATE TABLE IF NOT EXISTS q0_executions (
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    observation_hash TEXT NOT NULL,
    assembly_hash TEXT NOT NULL,
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    payload BLOB NOT NULL,
    payload_hash TEXT NOT NULL,
    PRIMARY KEY (run_id, step_id, observation_hash),
    FOREIGN KEY (run_id, step_id, assembly_hash)
        REFERENCES extraction_observations(run_id, step_id, assembly_hash)
)
"""
_Q1_SCHEMA = """
CREATE TABLE IF NOT EXISTS q1_executions (
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    observation_hash TEXT NOT NULL,
    annotations_hash TEXT NOT NULL,
    assembly_hash TEXT NOT NULL,
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    payload BLOB NOT NULL,
    payload_hash TEXT NOT NULL,
    PRIMARY KEY (run_id, step_id, observation_hash, annotations_hash),
    FOREIGN KEY (run_id, step_id, assembly_hash)
        REFERENCES extraction_observations(run_id, step_id, assembly_hash)
)
"""
_Q2_SCHEMA = """
CREATE TABLE IF NOT EXISTS q2_executions (
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    observation_hash TEXT NOT NULL,
    method_policy_hash TEXT NOT NULL,
    assembly_hash TEXT NOT NULL,
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    payload BLOB NOT NULL,
    payload_hash TEXT NOT NULL,
    PRIMARY KEY (run_id, step_id, observation_hash, method_policy_hash),
    FOREIGN KEY (run_id, step_id, assembly_hash)
        REFERENCES extraction_observations(run_id, step_id, assembly_hash)
)
"""
_Q3_SCHEMA = """
CREATE TABLE IF NOT EXISTS q3_executions (
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    observation_hash TEXT NOT NULL,
    method_policy_hash TEXT NOT NULL,
    assembly_hash TEXT NOT NULL,
    project TEXT NOT NULL,
    branch TEXT NOT NULL,
    payload BLOB NOT NULL,
    payload_hash TEXT NOT NULL,
    PRIMARY KEY (run_id, step_id, observation_hash, method_policy_hash),
    FOREIGN KEY (run_id, step_id, assembly_hash)
        REFERENCES extraction_observations(run_id, step_id, assembly_hash)
)
"""
_TRANSITIONS: dict[str, frozenset[str]] = {
    "PREPARED": frozenset({"DISPATCHING", "BLOCKED"}),
    "DISPATCHING": frozenset({"DRAFT_SAVED", "UNKNOWN", "FAILED", "BLOCKED"}),
    "BLOCKED": frozenset({"BLOCKED", "UNKNOWN", "FAILED", "DRAFT_SAVED"}),
    "DRAFT_SAVED": frozenset({"DRAFT_SAVED"}),
    "UNKNOWN": frozenset(),
    "FAILED": frozenset(),
}
_SCENE_TRANSITIONS: dict[str, frozenset[str]] = {
    "PREPARED": frozenset({"DISPATCHING", "BLOCKED", "STALE_SOURCE"}),
    "DISPATCHING": frozenset(
        {"DRAFT_SAVED", "UNKNOWN", "FAILED", "BLOCKED", "STALE_SOURCE"}
    ),
    "BLOCKED": frozenset(
        {"BLOCKED", "UNKNOWN", "FAILED", "DRAFT_SAVED", "STALE_SOURCE"}
    ),
    "DRAFT_SAVED": frozenset({"STALE_SOURCE"}),
    "UNKNOWN": frozenset({"STALE_SOURCE"}),
    "FAILED": frozenset({"STALE_SOURCE"}),
    "STALE_SOURCE": frozenset({"STALE_SOURCE"}),
}


def _identity(project: str, branch: str, run_id: str) -> tuple[str, str, str]:
    values = (project, branch, run_id)
    if any(type(value) is not str or not value.strip() for value in values):
        raise WorkflowError("INVALID_WORKFLOW_IDENTITY")
    return values


def _inode(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _ancestors(directory: Path) -> None:
    for parent in reversed((directory, *directory.parents)):
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise WorkflowError("WORKFLOW_DIRECTORY_LINK_OR_TYPE")


def _private_directory(directory: Path) -> os.stat_result:
    _ancestors(directory)
    info = directory.lstat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise WorkflowError("WORKFLOW_DIRECTORY_NOT_PRIVATE")
    return info


def _private_file(info: os.stat_result) -> None:
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
    ):
        raise WorkflowError("WORKFLOW_FILE_NOT_PRIVATE")


def _make_directory(directory: Path) -> None:
    """Create only missing directories; never chmod an existing user path."""
    missing: list[Path] = []
    current = directory
    while not current.exists() and not current.is_symlink():
        missing.append(current)
        current = current.parent
    _ancestors(current)
    for item in reversed(missing):
        try:
            item.mkdir(mode=0o700)
        except FileExistsError:
            pass
        _private_directory(item)
    _private_directory(directory)


def _snapshot(snapshot: WorkflowSnapshot) -> tuple[WorkflowSnapshot, bytes, str]:
    """Normalize constructor/hash failures without exposing serialized content."""
    try:
        if type(snapshot) is not WorkflowSnapshot:
            raise ValueError
        raw = snapshot.payload_bytes()
        value_hash = snapshot.record_hash
        if type(raw) is not bytes or value_hash != hashlib.sha256(raw).hexdigest():
            raise ValueError
        decoded = WorkflowSnapshot.from_bytes(raw)
        if decoded.payload_bytes() != raw or decoded.record_hash != value_hash:
            raise ValueError
        if decoded.state not in WORKFLOW_STATES:
            raise ValueError
        _identity(decoded.project, decoded.branch, decoded.run_id)
        return decoded, raw, value_hash
    except Exception:
        raise WorkflowError("INVALID_WORKFLOW_SNAPSHOT") from None


def _decode_workflow_payload(raw: bytes) -> tuple[WorkflowSnapshot, str]:
    snapshot, canonical, value_hash = _snapshot(WorkflowSnapshot.from_bytes(raw))
    if canonical != raw:
        raise ValueError
    return snapshot, value_hash


def _decode(row: sqlite3.Row) -> WorkflowSnapshot:
    try:
        raw: object = row["payload"]
        value_hash: object = row["payload_hash"]
        if type(raw) is not bytes or type(value_hash) is not str:
            raise ValueError
        if hashlib.sha256(raw).hexdigest() != value_hash:
            raise ValueError
        snapshot, actual_hash = _decode_retained_payload(raw, _decode_workflow_payload)
        if actual_hash != value_hash:
            raise ValueError
        if (snapshot.project, snapshot.branch, snapshot.run_id) != (
            row["project"],
            row["branch"],
            row["run_id"],
        ):
            raise ValueError
        return snapshot
    except Exception:
        raise WorkflowError("CORRUPT_WORKFLOW_RECORD") from None


def _request_binding(
    snapshot: WorkflowSnapshot,
) -> tuple[bytes, bytes, bytes, bytes, str, str]:
    return (
        snapshot.frozen_input.payload,
        snapshot.request_bytes,
        snapshot.contract_bytes,
        snapshot.context_bytes,
        snapshot.attempt_id,
        snapshot.policy_id,
    )


def _transition(before: WorkflowSnapshot, after: WorkflowSnapshot) -> None:
    if (before.project, before.branch, before.run_id) != (
        after.project,
        after.branch,
        after.run_id,
    ):
        raise WorkflowError("WORKFLOW_SCOPE_MISMATCH")
    if _request_binding(before) != _request_binding(after):
        raise WorkflowError("WORKFLOW_FROZEN_INPUT_CHANGED")
    if after.state not in _TRANSITIONS[before.state]:
        raise WorkflowError("INVALID_WORKFLOW_TRANSITION")
    if (
        before.state == "PREPARED"
        and after.state == "BLOCKED"
        and (after.result_bytes is not None or after.revision != 0)
    ):
        raise WorkflowError("INVALID_WORKFLOW_TRANSITION")
    if before.state == "BLOCKED" and before.result_bytes is not None:
        raise WorkflowError("WORKFLOW_RESULT_ALREADY_RETAINED")
    if before.result_bytes is not None and after.result_bytes != before.result_bytes:
        raise WorkflowError("WORKFLOW_RESULT_CHANGED")
    if after.revision not in {before.revision, before.revision + 1}:
        raise WorkflowError("INVALID_DRAFT_REVISION")
    if after.revision > before.revision and after.state != "DRAFT_SAVED":
        raise WorkflowError("INVALID_DRAFT_REVISION")
    if before.state == "DRAFT_SAVED" and after.revision != before.revision + 1:
        raise WorkflowError("INVALID_DRAFT_REVISION")
    if after.versions[: len(before.versions)] != before.versions:
        raise WorkflowError("DRAFT_HISTORY_CHANGED")


def _scene_hash(value: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise WorkflowError("INVALID_SCENE_GENERATION")
    return value


def _scene_snapshot(
    snapshot: SceneGenerationSnapshot,
) -> tuple[SceneGenerationSnapshot, bytes, str]:
    from .generation import SceneGenerationSnapshot

    try:
        if type(snapshot) is not SceneGenerationSnapshot:
            raise ValueError
        raw = snapshot.payload_bytes()
        value_hash = snapshot.record_hash
        if type(raw) is not bytes or hashlib.sha256(raw).hexdigest() != value_hash:
            raise ValueError
        normalized = _cached_scene_decode(raw)
        return normalized, raw, value_hash
    except Exception:
        raise WorkflowError("INVALID_SCENE_GENERATION") from None


def _cached_scene_decode(raw: bytes) -> SceneGenerationSnapshot:
    """Bounded pure decoding; never cache live freshness or authority.

    The key hashes actual bytes, never the database's claimed digest. Exact
    bytes guard even a digest collision. Only fully parsed, canonical records
    with deterministic Context validation enter this cache. The service still
    rechecks actual parent/ledger/Context qualifications on every operation.
    """
    from .generation import SceneGenerationSnapshot

    actual_hash = hashlib.sha256(raw).hexdigest()
    with _SCENE_DECODE_LOCK:
        entry = _SCENE_DECODE_CACHE.get(actual_hash)
        if entry is not None and entry[0] == raw:
            _SCENE_DECODE_CACHE.move_to_end(actual_hash)
            return entry[1]
    snapshot = SceneGenerationSnapshot.from_bytes(raw)
    if snapshot.payload_bytes() != raw or snapshot.record_hash != actual_hash:
        raise WorkflowError("INVALID_SCENE_GENERATION")
    with _SCENE_DECODE_LOCK:
        _SCENE_DECODE_CACHE[actual_hash] = (raw, snapshot)
        _SCENE_DECODE_CACHE.move_to_end(actual_hash)
        while len(_SCENE_DECODE_CACHE) > _SCENE_DECODE_LIMIT:
            _SCENE_DECODE_CACHE.popitem(last=False)
    return snapshot


def _decode_scene(row: sqlite3.Row) -> SceneGenerationSnapshot:
    try:
        raw: object = row["payload"]
        value_hash: object = row["payload_hash"]
        if (
            type(raw) is not bytes
            or type(value_hash) is not str
            or hashlib.sha256(raw).hexdigest() != value_hash
        ):
            raise ValueError
        snapshot = _cached_scene_decode(raw)
        if (snapshot.project, snapshot.branch, snapshot.run_id, snapshot.step_id) != (
            row["project"],
            row["branch"],
            row["run_id"],
            row["step_id"],
        ):
            raise ValueError
        return snapshot
    except Exception:
        raise WorkflowError("CORRUPT_SCENE_GENERATION") from None


def _scene_binding(
    snapshot: SceneGenerationSnapshot,
) -> tuple[bytes, bytes, str, str, str]:
    from anovel.canon.identity import canonical_bytes

    return (
        snapshot.source.payload_bytes(),
        canonical_bytes(snapshot.projection.to_dict()),
        snapshot.attempt_id,
        snapshot.policy_id,
        snapshot.ledger_pin.content_hash,
    )


def _scene_transition(
    before: SceneGenerationSnapshot, after: SceneGenerationSnapshot
) -> None:
    if _scene_binding(before) != _scene_binding(after) or (
        before.run_id,
        before.step_id,
    ) != (after.run_id, after.step_id):
        raise WorkflowError("SCENE_GENERATION_CONFLICT")
    if after.state not in _SCENE_TRANSITIONS[before.state]:
        raise WorkflowError("INVALID_SCENE_GENERATION_TRANSITION")
    if (
        before.state == "PREPARED"
        and after.state == "BLOCKED"
        and after.result_bytes is not None
    ):
        raise WorkflowError("INVALID_SCENE_GENERATION_TRANSITION")
    if (
        before.state == "BLOCKED"
        and before.result_bytes is not None
        and after.state != "STALE_SOURCE"
    ):
        raise WorkflowError("SCENE_GENERATION_RESULT_ALREADY_RETAINED")
    if before.result_bytes is not None and before.result_bytes != after.result_bytes:
        raise WorkflowError("SCENE_GENERATION_RESULT_CHANGED")


class WorkflowStore:
    """A dedicated private database, with a fresh connection for every call."""

    def __init__(self, path: Path) -> None:
        try:
            if (
                not isinstance(path, Path)
                or path.name in {"", ":memory:"}
                or ".." in path.parts
            ):
                raise WorkflowError("INVALID_WORKFLOW_STORE_PATH")
            self.path = path.absolute()
            _make_directory(self.path.parent)
            self._directory_identity = _inode(_private_directory(self.path.parent))
            try:
                descriptor = os.open(
                    self.path,
                    os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                )
            except FileExistsError:
                info = self.path.lstat()
            else:
                try:
                    info = os.fstat(descriptor)
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                self._sync_directory(self.path.parent)
            _private_file(info)
            self._database_identity = _inode(info)
            self.lock_directory = self.path.with_name(self.path.name + ".locks")
            _make_directory(self.lock_directory)
            self._lock_identity = _inode(_private_directory(self.lock_directory))
            with self._connection() as connection:
                tables = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
                names = {row["name"] for row in tables}
                if "written_draft_revisions" in names:
                    if "runs" not in names:
                        raise WorkflowError("INVALID_WORKFLOW_STORE_SCHEMA")
                    names.remove("written_draft_revisions")
                if "revision_q123_executions" in names:
                    if "chapter_revisions" not in names:
                        raise WorkflowError("INVALID_WORKFLOW_STORE_SCHEMA")
                    names.remove("revision_q123_executions")
                if "revision_q0_executions" in names:
                    if "chapter_revisions" not in names:
                        raise WorkflowError("INVALID_WORKFLOW_STORE_SCHEMA")
                    names.remove("revision_q0_executions")
                if "chapter_revisions" in names:
                    if "extraction_observations" not in names:
                        raise WorkflowError("INVALID_WORKFLOW_STORE_SCHEMA")
                    names.remove("chapter_revisions")
                if names and names not in (
                    {"runs"},
                    {"runs", "scene_generations"},
                    {"runs", "scene_generations", "extraction_observations"},
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q0_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q1_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q0_executions",
                        "q1_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q2_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q0_executions",
                        "q2_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q1_executions",
                        "q2_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q0_executions",
                        "q1_executions",
                        "q2_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q3_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q0_executions",
                        "q3_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q1_executions",
                        "q3_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q2_executions",
                        "q3_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q0_executions",
                        "q1_executions",
                        "q3_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q0_executions",
                        "q2_executions",
                        "q3_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q1_executions",
                        "q2_executions",
                        "q3_executions",
                    },
                    {
                        "runs",
                        "scene_generations",
                        "extraction_observations",
                        "q0_executions",
                        "q1_executions",
                        "q2_executions",
                        "q3_executions",
                    },
                ):
                    raise WorkflowError("INVALID_WORKFLOW_STORE_SCHEMA")
                connection.execute(_SCHEMA)
                columns = connection.execute("PRAGMA table_info(runs)").fetchall()
                if [row["name"] for row in columns] != [
                    "run_id",
                    "project",
                    "branch",
                    "payload",
                    "payload_hash",
                ]:
                    raise WorkflowError("INVALID_WORKFLOW_STORE_SCHEMA")
                if [row["type"].upper() for row in columns] != [
                    "TEXT",
                    "TEXT",
                    "TEXT",
                    "BLOB",
                    "TEXT",
                ] or columns[0]["pk"] != 1:
                    raise WorkflowError("INVALID_WORKFLOW_STORE_SCHEMA")
                self._scene_table(connection, create=False)
                self._extraction_table(connection, create=False)
                self._q0_table(connection, create=False)
                self._q1_table(connection, create=False)
                self._q2_table(connection, create=False)
                self._q3_table(connection, create=False)
                self._chapter_revision_table(connection, create=False)
                self._written_draft_table(connection, create=False)
                self._revision_q0_table(connection, create=False)
                self._revision_q123_table(connection, create=False)
        except WorkflowError:
            raise
        except Exception:
            raise WorkflowError("WORKFLOW_STORE_UNAVAILABLE") from None

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        descriptor = os.open(
            directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _verify(self) -> None:
        if _inode(_private_directory(self.path.parent)) != self._directory_identity:
            raise WorkflowError("WORKFLOW_DIRECTORY_CHANGED")
        info = self.path.lstat()
        _private_file(info)
        if _inode(info) != self._database_identity:
            raise WorkflowError("WORKFLOW_DATABASE_CHANGED")
        if _inode(_private_directory(self.lock_directory)) != self._lock_identity:
            raise WorkflowError("WORKFLOW_LOCK_DIRECTORY_CHANGED")
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = self.path.with_name(self.path.name + suffix)
            try:
                info = sidecar.lstat()
            except FileNotFoundError:
                continue
            _private_file(info)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection: sqlite3.Connection | None = None
        try:
            self._verify()
            connection = sqlite3.connect(self.path, timeout=0, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA synchronous=FULL")
            self._verify()
            yield connection
            self._verify()
        except WorkflowError:
            raise
        except (OSError, sqlite3.Error):
            raise WorkflowError("WORKFLOW_STORE_UNAVAILABLE") from None
        finally:
            if connection is not None:
                connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connection() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    @staticmethod
    def _scene_table(connection: sqlite3.Connection, *, create: bool) -> bool:
        exists = (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='scene_generations'"
            ).fetchone()
            is not None
        )
        if not exists:
            if not create:
                return False
            connection.execute(_SCENE_SCHEMA)
        columns = connection.execute("PRAGMA table_info(scene_generations)").fetchall()
        if (
            [row["name"] for row in columns]
            != ["run_id", "step_id", "project", "branch", "payload", "payload_hash"]
            or [row["type"].upper() for row in columns]
            != ["TEXT", "TEXT", "TEXT", "TEXT", "BLOB", "TEXT"]
            or [row["pk"] for row in columns] != [1, 2, 0, 0, 0, 0]
            or any(
                row["notnull"] != 1 or row["dflt_value"] is not None for row in columns
            )
        ):
            raise WorkflowError("INVALID_SCENE_GENERATION_SCHEMA")
        foreign = connection.execute(
            "PRAGMA foreign_key_list(scene_generations)"
        ).fetchall()
        if len(foreign) != 1 or (
            foreign[0]["table"],
            foreign[0]["from"],
            foreign[0]["to"],
        ) != ("runs", "run_id", "run_id"):
            raise WorkflowError("INVALID_SCENE_GENERATION_SCHEMA")
        return True

    @staticmethod
    def _scene_parent(
        connection: sqlite3.Connection, project: str, branch: str, run_id: str
    ) -> WorkflowSnapshot:
        row: sqlite3.Row | None = connection.execute(
            "SELECT * FROM runs WHERE project=? AND branch=? AND run_id=?",
            (project, branch, run_id),
        ).fetchone()
        if row is None:
            raise WorkflowError("SCENE_GENERATION_UNAVAILABLE")
        return _decode(row)

    @staticmethod
    def _run_scene_pins(
        connection: sqlite3.Connection, snapshot: SceneGenerationSnapshot
    ) -> None:
        for row in connection.execute(
            "SELECT * FROM scene_generations WHERE run_id=?", (snapshot.run_id,)
        ):
            existing = _decode_scene(row)
            if (existing.project, existing.branch) != (
                snapshot.project,
                snapshot.branch,
            ):
                raise WorkflowError("CORRUPT_SCENE_GENERATION")
            if existing.ledger_pin != snapshot.ledger_pin:
                raise WorkflowError("SCENE_GENERATION_CONFLICT")

    def _invalidate_scenes(
        self, connection: sqlite3.Connection, parent: WorkflowSnapshot
    ) -> None:
        if not self._scene_table(connection, create=False):
            return
        rows = connection.execute(
            "SELECT * FROM scene_generations WHERE run_id=?", (parent.run_id,)
        ).fetchall()
        for row in rows:
            child = _decode_scene(row)
            if (child.project, child.branch) != (parent.project, parent.branch):
                raise WorkflowError("CORRUPT_SCENE_GENERATION")
            if (
                child.source.record_hash == parent.record_hash
                or child.state == "STALE_SOURCE"
            ):
                continue
            stale = replace(
                child,
                state="STALE_SOURCE",
                prose=None,
                diagnostic="SCENE_SOURCE_CHANGED",
            )
            stale, raw, value_hash = _scene_snapshot(stale)
            count = connection.execute(
                "UPDATE scene_generations SET payload=?,payload_hash=? WHERE run_id=? AND step_id=? AND payload_hash=?",
                (raw, value_hash, child.run_id, child.step_id, child.record_hash),
            ).rowcount
            if count != 1:
                raise WorkflowError("SCENE_GENERATION_CONFLICT")

    def load(self, *, project: str, branch: str, run_id: str) -> WorkflowSnapshot:
        scope = _identity(project, branch, run_id)
        with self._connection() as connection:
            row: sqlite3.Row | None = connection.execute(
                "SELECT * FROM runs WHERE project=? AND branch=? AND run_id=?", scope
            ).fetchone()
            if row is None:
                raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE")
            return _decode(row)

    def create(self, snapshot: WorkflowSnapshot) -> bool:
        snapshot, raw, value_hash = _snapshot(snapshot)
        if snapshot.state != "PREPARED" or snapshot.revision != 0:
            raise WorkflowError("WORKFLOW_CREATE_REQUIRES_PREPARED")
        with self._transaction() as connection:
            row: sqlite3.Row | None = connection.execute(
                "SELECT * FROM runs WHERE run_id=?", (snapshot.run_id,)
            ).fetchone()
            if row is not None:
                if (row["project"], row["branch"]) != (
                    snapshot.project,
                    snapshot.branch,
                ):
                    raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE")
                existing = _decode(row)
                if _request_binding(existing) != _request_binding(snapshot):
                    raise WorkflowError("WORKFLOW_RUN_CONFLICT")
                return False
            connection.execute(
                "INSERT INTO runs(run_id,project,branch,payload,payload_hash) VALUES(?,?,?,?,?)",
                (snapshot.run_id, snapshot.project, snapshot.branch, raw, value_hash),
            )
            return True

    def publish(
        self, before: WorkflowSnapshot, after: WorkflowSnapshot
    ) -> WorkflowSnapshot:
        before, _, expected_hash = _snapshot(before)
        after, raw, value_hash = _snapshot(after)
        _transition(before, after)
        with self._transaction() as connection:
            row: sqlite3.Row | None = connection.execute(
                "SELECT * FROM runs WHERE project=? AND branch=? AND run_id=?",
                (before.project, before.branch, before.run_id),
            ).fetchone()
            if row is None:
                raise WorkflowError("WORKFLOW_RUN_UNAVAILABLE")
            current = _decode(row)
            if current.record_hash != expected_hash:
                raise WorkflowError("WORKFLOW_STALE_RECORD")
            changed = connection.execute(
                "UPDATE runs SET payload=?,payload_hash=? WHERE run_id=? AND project=? AND branch=? AND payload_hash=?",
                (
                    raw,
                    value_hash,
                    before.run_id,
                    before.project,
                    before.branch,
                    expected_hash,
                ),
            ).rowcount
            if changed != 1:
                raise WorkflowError("WORKFLOW_STALE_RECORD")
            self._invalidate_scenes(connection, after)
        return after

    def load_scene(
        self, *, project: str, branch: str, run_id: str, step_id: str
    ) -> SceneGenerationSnapshot:
        _identity(project, branch, run_id)
        _scene_hash(step_id)
        with self._connection() as connection:
            if not self._scene_table(connection, create=False):
                raise WorkflowError("SCENE_GENERATION_UNAVAILABLE")
            parent = self._scene_parent(connection, project, branch, run_id)
            row: sqlite3.Row | None = connection.execute(
                "SELECT * FROM scene_generations WHERE project=? AND branch=? AND run_id=? AND step_id=?",
                (project, branch, run_id, step_id),
            ).fetchone()
            if row is None:
                raise WorkflowError("SCENE_GENERATION_UNAVAILABLE")
            snapshot = _decode_scene(row)
            if (
                snapshot.state != "STALE_SOURCE"
                and parent.record_hash != snapshot.source.record_hash
            ):
                raise WorkflowError("SCENE_SOURCE_CHANGED")
            return snapshot

    def create_scene(self, snapshot: SceneGenerationSnapshot) -> bool:
        snapshot, raw, value_hash = _scene_snapshot(snapshot)
        if snapshot.state != "PREPARED":
            raise WorkflowError("SCENE_GENERATION_CREATE_REQUIRES_PREPARED")
        with self._transaction() as connection:
            parent = self._scene_parent(
                connection, snapshot.project, snapshot.branch, snapshot.run_id
            )
            if parent.record_hash != snapshot.source.record_hash:
                raise WorkflowError("SCENE_SOURCE_CHANGED")
            self._scene_table(connection, create=True)
            self._run_scene_pins(connection, snapshot)
            row: sqlite3.Row | None = connection.execute(
                "SELECT * FROM scene_generations WHERE run_id=? AND step_id=?",
                (snapshot.run_id, snapshot.step_id),
            ).fetchone()
            if row is not None:
                existing = _decode_scene(row)
                if _scene_binding(existing) != _scene_binding(snapshot):
                    raise WorkflowError("SCENE_GENERATION_CONFLICT")
                return False
            connection.execute(
                "INSERT INTO scene_generations(run_id,step_id,project,branch,payload,payload_hash) VALUES(?,?,?,?,?,?)",
                (
                    snapshot.run_id,
                    snapshot.step_id,
                    snapshot.project,
                    snapshot.branch,
                    raw,
                    value_hash,
                ),
            )
            return True

    def publish_scene(
        self,
        before: SceneGenerationSnapshot,
        after: SceneGenerationSnapshot,
        *,
        expected_parent_hash: str,
    ) -> SceneGenerationSnapshot:
        before, _, expected_hash = _scene_snapshot(before)
        after, raw, value_hash = _scene_snapshot(after)
        _scene_hash(expected_parent_hash)
        _scene_transition(before, after)
        with self._transaction() as connection:
            parent = self._scene_parent(
                connection, before.project, before.branch, before.run_id
            )
            if parent.record_hash != expected_parent_hash or (
                (
                    after.state != "STALE_SOURCE"
                    and parent.record_hash != after.source.record_hash
                )
                or (
                    after.state == "STALE_SOURCE"
                    and parent.record_hash == after.source.record_hash
                )
            ):
                raise WorkflowError("SCENE_SOURCE_CHANGED")
            if not self._scene_table(connection, create=False):
                raise WorkflowError("SCENE_GENERATION_UNAVAILABLE")
            self._run_scene_pins(connection, after)
            row: sqlite3.Row | None = connection.execute(
                "SELECT * FROM scene_generations WHERE project=? AND branch=? AND run_id=? AND step_id=?",
                (before.project, before.branch, before.run_id, before.step_id),
            ).fetchone()
            if row is None:
                raise WorkflowError("SCENE_GENERATION_UNAVAILABLE")
            if _decode_scene(row).record_hash != expected_hash:
                raise WorkflowError("SCENE_GENERATION_CONFLICT")
            count = connection.execute(
                "UPDATE scene_generations SET payload=?,payload_hash=? WHERE run_id=? AND step_id=? AND project=? AND branch=? AND payload_hash=?",
                (
                    raw,
                    value_hash,
                    before.run_id,
                    before.step_id,
                    before.project,
                    before.branch,
                    expected_hash,
                ),
            ).rowcount
            if count != 1:
                raise WorkflowError("SCENE_GENERATION_CONFLICT")
        return after

    @staticmethod
    @contextmanager
    def reuse_observation_decodes() -> Iterator[None]:
        """Keep decoder results only during one synchronous Workflow operation."""
        token = _observation_decodes.set(OrderedDict())
        try:
            yield
        finally:
            _observation_decodes.reset(token)

    @contextmanager
    def exclusive(self, *, project: str, branch: str, run_id: str) -> Iterator[None]:
        _identity(project, branch, run_id)
        descriptor: int | None = None
        directory: int | None = None
        try:
            self._verify()
            directory = os.open(
                self.lock_directory,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            if _inode(os.fstat(directory)) != self._lock_identity:
                raise WorkflowError("WORKFLOW_LOCK_DIRECTORY_CHANGED")
            name = hashlib.sha256(run_id.encode("utf-8")).hexdigest() + ".lock"
            descriptor = os.open(
                name,
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
                0o600,
                dir_fd=directory,
            )
            info = os.fstat(descriptor)
            _private_file(info)
            if _inode(info) != _inode(
                os.stat(name, dir_fd=directory, follow_symlinks=False)
            ):
                raise WorkflowError("WORKFLOW_LOCK_CHANGED")
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.fsync(directory)
            self._verify()
            yield
        except WorkflowError:
            raise
        except (OSError, UnicodeError):
            raise WorkflowError("WORKFLOW_RUN_LOCK_UNAVAILABLE") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if directory is not None:
                os.close(directory)

    @staticmethod
    def _extraction_table(connection: sqlite3.Connection, *, create: bool) -> bool:
        exists = (
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='extraction_observations'"
            ).fetchone()
            is not None
        )
        if not exists:
            if not create:
                return False
            connection.execute(_EXTRACTION_SCHEMA)
        columns = connection.execute(
            "PRAGMA table_info(extraction_observations)"
        ).fetchall()
        if (
            [row["name"] for row in columns]
            != [
                "run_id",
                "step_id",
                "assembly_hash",
                "project",
                "branch",
                "payload",
                "payload_hash",
            ]
            or [row["type"].upper() for row in columns]
            != ["TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "BLOB", "TEXT"]
            or [row["pk"] for row in columns] != [1, 2, 3, 0, 0, 0, 0]
            or any(
                row["notnull"] != 1 or row["dflt_value"] is not None for row in columns
            )
        ):
            raise WorkflowError("INVALID_EXTRACTION_SCHEMA")
        foreign = connection.execute(
            "PRAGMA foreign_key_list(extraction_observations)"
        ).fetchall()
        if (
            len(foreign) != 2
            or len({row["id"] for row in foreign}) != 1
            or {row["seq"] for row in foreign} != {0, 1}
            or any(
                (row["on_update"], row["on_delete"], row["match"])
                != ("NO ACTION", "NO ACTION", "NONE")
                for row in foreign
            )
            or {(row["table"], row["from"], row["to"]) for row in foreign}
            != {
                ("scene_generations", "run_id", "run_id"),
                ("scene_generations", "step_id", "step_id"),
            }
        ):
            raise WorkflowError("INVALID_EXTRACTION_SCHEMA")
        return True

    @staticmethod
    def _decode_extraction(row: sqlite3.Row) -> ExtractionObservation:
        from .extractor import ExtractionObservation

        try:
            raw = row["payload"]
            if (
                type(raw) is not bytes
                or hashlib.sha256(raw).hexdigest() != row["payload_hash"]
            ):
                raise ValueError
            saved = _decode_retained_payload(raw, ExtractionObservation.from_bytes)
            if (
                saved.project,
                saved.branch,
                saved.run_id,
                saved.step_id,
                saved.assembly_hash,
            ) != (
                row["project"],
                row["branch"],
                row["run_id"],
                row["step_id"],
                row["assembly_hash"],
            ):
                raise ValueError
            return saved
        except Exception:
            raise WorkflowError("CORRUPT_EXTRACTION_OBSERVATION") from None

    @staticmethod
    def _extraction_source(
        connection: sqlite3.Connection, saved: ExtractionObservation
    ) -> None:
        parent = WorkflowStore._scene_parent(
            connection, saved.project, saved.branch, saved.run_id
        )
        if not WorkflowStore._scene_table(connection, create=False):
            raise WorkflowError("EXTRACTION_SOURCE_CHANGED")
        row = connection.execute(
            "SELECT * FROM scene_generations WHERE project=? AND branch=? AND run_id=? AND step_id=?",
            (saved.project, saved.branch, saved.run_id, saved.step_id),
        ).fetchone()
        if row is None:
            raise WorkflowError("EXTRACTION_SOURCE_CHANGED")
        child = _decode_scene(row)
        if (
            child.state != "DRAFT_SAVED"
            or parent.record_hash != saved.assembly.source_record_hash
            or child.record_hash != saved.assembly.child_record_hash
        ):
            raise WorkflowError("EXTRACTION_SOURCE_CHANGED")

    def load_extraction(
        self,
        *,
        project: str,
        branch: str,
        run_id: str,
        step_id: str,
        assembly_hash: str,
    ) -> ExtractionObservation:
        _identity(project, branch, run_id)
        _scene_hash(step_id)
        _scene_hash(assembly_hash)
        with self._connection() as connection:
            self._scene_parent(connection, project, branch, run_id)
            if not self._extraction_table(connection, create=False):
                raise WorkflowError("EXTRACTION_OBSERVATION_UNAVAILABLE")
            row = connection.execute(
                "SELECT * FROM extraction_observations WHERE run_id=? AND step_id=? AND assembly_hash=?",
                (run_id, step_id, assembly_hash),
            ).fetchone()
            if row is None:
                # A damaged key must not turn a retained corrupt observation
                # into an apparently missing one and trigger new extraction.
                for existing in connection.execute(
                    "SELECT * FROM extraction_observations WHERE run_id=? AND step_id=?",
                    (run_id, step_id),
                ):
                    if (existing["project"], existing["branch"]) != (project, branch):
                        raise WorkflowError("CORRUPT_EXTRACTION_OBSERVATION")
                    self._decode_extraction(existing)
                raise WorkflowError("EXTRACTION_OBSERVATION_UNAVAILABLE")
            if (row["project"], row["branch"]) != (project, branch):
                raise WorkflowError("CORRUPT_EXTRACTION_OBSERVATION")
            saved = self._decode_extraction(row)
            self._extraction_source(connection, saved)
            return saved

    def create_extraction(self, observation: ExtractionObservation) -> bool:
        from .extractor import ExtractionObservation

        if type(observation) is not ExtractionObservation:
            raise WorkflowError("EXTRACTION_OBSERVATION_REQUIRED")
        raw = observation.payload_bytes()
        saved = ExtractionObservation.from_bytes(raw)
        value_hash = hashlib.sha256(raw).hexdigest()
        if saved.record_hash != observation.record_hash:
            raise WorkflowError("CORRUPT_EXTRACTION_OBSERVATION")
        with self._transaction() as connection:
            self._extraction_source(connection, saved)
            self._extraction_table(connection, create=True)
            row = connection.execute(
                "SELECT * FROM extraction_observations WHERE run_id=? AND step_id=? AND assembly_hash=?",
                (saved.run_id, saved.step_id, saved.assembly_hash),
            ).fetchone()
            if row is not None:
                existing = self._decode_extraction(row)
                if existing.payload_bytes() != raw:
                    raise WorkflowError("EXTRACTION_OBSERVATION_CONFLICT")
                return False
            connection.execute(
                "INSERT INTO extraction_observations VALUES(?,?,?,?,?,?,?)",
                (
                    saved.run_id,
                    saved.step_id,
                    saved.assembly_hash,
                    saved.project,
                    saved.branch,
                    raw,
                    value_hash,
                ),
            )
            return True

    @staticmethod
    def _chapter_revision_table(
        connection: sqlite3.Connection, *, create: bool
    ) -> bool:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chapter_revisions'"
        ).fetchone()
        if exists is None:
            if not create:
                return False
            connection.execute(_CHAPTER_REVISION_SCHEMA)
        columns = connection.execute("PRAGMA table_info(chapter_revisions)").fetchall()
        if [
            (row["name"], row["type"].upper(), row["pk"], row["notnull"])
            for row in columns
        ] != [
            ("project", "TEXT", 1, 1),
            ("branch", "TEXT", 2, 1),
            ("chapter_id", "TEXT", 3, 1),
            ("version", "INTEGER", 4, 1),
            ("request_id", "TEXT", 0, 1),
            ("run_id", "TEXT", 0, 1),
            ("step_id", "TEXT", 0, 1),
            ("assembly_hash", "TEXT", 0, 1),
            ("previous_revision_hash", "TEXT", 0, 0),
            ("payload", "BLOB", 0, 1),
            ("payload_hash", "TEXT", 0, 1),
        ] or any(row["dflt_value"] is not None for row in columns):
            raise WorkflowError("INVALID_CHAPTER_REVISION_SCHEMA")
        indexes = {
            (
                row["origin"],
                tuple(
                    col["name"]
                    for col in connection.execute(
                        "SELECT name FROM pragma_index_info(?) ORDER BY seqno",
                        (row["name"],),
                    )
                ),
            )
            for row in connection.execute("PRAGMA index_list(chapter_revisions)")
            if row["unique"] and not row["partial"]
        }
        if indexes != {
            ("pk", ("project", "branch", "chapter_id", "version")),
            ("u", ("project", "branch", "chapter_id", "request_id")),
        }:
            raise WorkflowError("INVALID_CHAPTER_REVISION_SCHEMA")
        foreign = connection.execute(
            "PRAGMA foreign_key_list(chapter_revisions)"
        ).fetchall()
        if (
            len(foreign) != 3
            or len({row["id"] for row in foreign}) != 1
            or {(row["seq"], row["table"], row["from"], row["to"]) for row in foreign}
            != {
                (i, "extraction_observations", name, name)
                for i, name in enumerate(("run_id", "step_id", "assembly_hash"))
            }
            or any(
                (row["on_update"], row["on_delete"], row["match"])
                != ("NO ACTION", "NO ACTION", "NONE")
                for row in foreign
            )
        ):
            raise WorkflowError("INVALID_CHAPTER_REVISION_SCHEMA")
        if (
            connection.execute("PRAGMA foreign_key_check(chapter_revisions)").fetchone()
            is not None
        ):
            raise WorkflowError("CORRUPT_CHAPTER_REVISION")
        return True

    @staticmethod
    def _retained_revision_observation(
        connection: sqlite3.Connection, *, run_id: str, step_id: str, assembly_hash: str
    ) -> ExtractionObservation:
        row = connection.execute(
            "SELECT * FROM extraction_observations WHERE run_id=? AND step_id=? AND assembly_hash=?",
            (run_id, step_id, assembly_hash),
        ).fetchone()
        if row is None:
            raise WorkflowError("EXTRACTION_OBSERVATION_UNAVAILABLE")
        return WorkflowStore._decode_extraction(row)

    @staticmethod
    def _chapter_revision_lineage(
        connection: sqlite3.Connection, scope: tuple[str, str, str]
    ) -> list[str]:
        rows = []
        previous = None
        for version, row in enumerate(
            connection.execute(
                "SELECT version, request_id, run_id, step_id, assembly_hash, "
                "previous_revision_hash, payload_hash, payload "
                "FROM chapter_revisions WHERE project=? AND branch=? AND chapter_id=? ORDER BY version",
                scope,
            ),
            1,
        ):
            raw = row["payload"]
            if (
                row["version"] != version
                or row["previous_revision_hash"] != previous
                or type(raw) is not bytes
                or hashlib.sha256(raw).hexdigest() != row["payload_hash"]
            ):
                raise WorkflowError("CORRUPT_CHAPTER_REVISION")
            try:
                body = decode_canonical(raw)
                if type(body) is not dict or type(body["candidate"]) is not dict:
                    raise ValueError
                candidate = body["candidate"]
                if (
                    (candidate["project"], candidate["branch"], body["chapter_id"])
                    != (scope[0], scope[1], {"project": scope[0], "local_id": scope[2]})
                    or type(candidate["version"]) is not int
                    or candidate["version"] != version
                    or any(
                        body[key] != row[key]
                        for key in (
                            "request_id",
                            "run_id",
                            "step_id",
                            "assembly_hash",
                            "previous_revision_hash",
                        )
                    )
                ):
                    raise ValueError
            except (TypeError, ValueError, KeyError, RecursionError):
                raise WorkflowError("CORRUPT_CHAPTER_REVISION") from None
            previous = row["payload_hash"]
            rows.append(row["request_id"])
        return rows

    @staticmethod
    def _chapter_revision_with_observation(
        connection: sqlite3.Connection, scope: tuple[str, str, str], version: int
    ) -> tuple[ChapterRevision, ExtractionObservation]:
        try:
            row = connection.execute(
                "SELECT * FROM chapter_revisions WHERE project=? AND branch=? AND chapter_id=? AND version=?",
                (*scope, version),
            ).fetchone()
            if row is None:
                raise ValueError
            raw = row["payload"]
            if (
                type(raw) is not bytes
                or hashlib.sha256(raw).hexdigest() != row["payload_hash"]
            ):
                raise ValueError
            saved = ChapterRevision.from_bytes(raw)
            if (
                saved.project,
                saved.branch,
                saved.chapter_id.local_id,
                saved.version,
                saved.request_id,
                saved.run_id,
                saved.step_id,
                saved.assembly_hash,
                saved.previous_revision_hash,
            ) != (
                *scope,
                version,
                row["request_id"],
                row["run_id"],
                row["step_id"],
                row["assembly_hash"],
                row["previous_revision_hash"],
            ):
                raise ValueError
            historical_source = WorkflowStore._retained_revision_observation(
                connection,
                run_id=saved.run_id,
                step_id=saved.step_id,
                assembly_hash=saved.assembly_hash,
            )
            saved.require_observation(historical_source)
            return saved, historical_source
        except (TypeError, ValueError, KeyError, IndexError, RecursionError):
            raise WorkflowError("CORRUPT_CHAPTER_REVISION") from None

    @staticmethod
    def _decode_chapter_revision(
        connection: sqlite3.Connection, scope: tuple[str, str, str], version: int
    ) -> ChapterRevision:
        saved, _ = WorkflowStore._chapter_revision_with_observation(
            connection, scope, version
        )
        return saved

    def append_chapter_revision(
        self,
        observation: ExtractionObservation,
        candidate: ChapterCandidate,
        *,
        request_id: str,
        expected_revision_hash: str | None,
    ) -> ChapterRevision:
        """Append a Draft revision using a scoped predecessor hash and stable request."""
        from anovel.canon.chapter import ChapterCandidate

        from .extractor import ExtractionObservation

        if (
            type(observation) is not ExtractionObservation
            or type(candidate) is not ChapterCandidate
        ):
            raise WorkflowError("INVALID_CHAPTER_REVISION")
        scope = _identity(
            observation.project, observation.branch, observation.chapter_id.local_id
        )
        with self._transaction() as connection:
            if not self._extraction_table(connection, create=False):
                raise WorkflowError("EXTRACTION_OBSERVATION_UNAVAILABLE")
            source = self._retained_revision_observation(
                connection,
                run_id=observation.run_id,
                step_id=observation.step_id,
                assembly_hash=observation.assembly_hash,
            )
            if source.payload_bytes() != observation.payload_bytes():
                raise WorkflowError("EXTRACTION_SOURCE_CHANGED")
            self._extraction_source(connection, source)
            self._chapter_revision_table(connection, create=True)
            lineage = self._chapter_revision_lineage(connection, scope)
            if request_id in lineage:
                saved = self._decode_chapter_revision(
                    connection, scope, lineage.index(request_id) + 1
                )
                if (
                    saved.previous_revision_hash != expected_revision_hash
                    or saved.candidate.payload_bytes() != candidate.payload_bytes()
                    or saved.observation_hash != source.record_hash
                ):
                    raise WorkflowError("CHAPTER_REVISION_CONFLICT")
                return saved
            before = None
            if lineage:
                before = self._decode_chapter_revision(connection, scope, len(lineage))
            if (before.record_hash if before else None) != expected_revision_hash:
                raise WorkflowError("CHAPTER_REVISION_CONFLICT")
            if candidate.version != len(lineage) + 1:
                raise WorkflowError("CHAPTER_REVISION_VERSION_MISMATCH")
            saved = ChapterRevision.from_observation(
                source,
                candidate,
                request_id=request_id,
                previous_revision_hash=expected_revision_hash,
            )
            raw = saved.payload_bytes()
            connection.execute(
                "INSERT INTO chapter_revisions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    *scope,
                    saved.version,
                    saved.request_id,
                    saved.run_id,
                    saved.step_id,
                    saved.assembly_hash,
                    saved.previous_revision_hash,
                    raw,
                    hashlib.sha256(raw).hexdigest(),
                ),
            )
            return saved

    def load_chapter_revision(
        self,
        *,
        project: str,
        branch: str,
        chapter_id: EntityId,
        version: int | None = None,
    ) -> ChapterRevision:
        """Read that exact Draft revision, or the latest stored one, for audit."""
        from anovel.domain.identity import EntityId

        if type(chapter_id) is not EntityId or chapter_id.project != project:
            raise WorkflowError("CHAPTER_REVISION_UNAVAILABLE")
        if version is not None and (type(version) is not int or version < 1):
            raise WorkflowError("INVALID_CHAPTER_REVISION")
        scope = _identity(project, branch, chapter_id.local_id)
        with self._connection() as connection:
            connection.execute("BEGIN")
            if not self._chapter_revision_table(connection, create=False):
                raise WorkflowError("CHAPTER_REVISION_UNAVAILABLE")
            lineage = self._chapter_revision_lineage(connection, scope)
            selected = len(lineage) if version is None else version
            if not 1 <= selected <= len(lineage):
                raise WorkflowError("CHAPTER_REVISION_UNAVAILABLE")
            return self._decode_chapter_revision(connection, scope, selected)

    @staticmethod
    def _written_draft_table(connection: sqlite3.Connection, *, create: bool) -> bool:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='written_draft_revisions'"
        ).fetchone()
        if exists is None:
            if not create:
                return False
            connection.execute(_WRITTEN_DRAFT_SCHEMA)
        columns = connection.execute(
            "PRAGMA table_info(written_draft_revisions)"
        ).fetchall()
        if [
            (row["name"], row["type"].upper(), row["pk"], row["notnull"])
            for row in columns
        ] != [
            ("project", "TEXT", 1, 1),
            ("branch", "TEXT", 2, 1),
            ("chapter_id", "TEXT", 3, 1),
            ("version", "INTEGER", 4, 1),
            ("run_id", "TEXT", 0, 1),
            ("previous_revision_hash", "TEXT", 0, 0),
            ("payload", "BLOB", 0, 1),
            ("payload_hash", "TEXT", 0, 1),
        ] or any(row["dflt_value"] is not None for row in columns):
            raise WorkflowError("INVALID_WRITTEN_DRAFT_SCHEMA")
        indexes = {
            (
                row["origin"],
                tuple(
                    column["name"]
                    for column in connection.execute(
                        "SELECT name FROM pragma_index_info(?) ORDER BY seqno",
                        (row["name"],),
                    )
                ),
            )
            for row in connection.execute("PRAGMA index_list(written_draft_revisions)")
            if row["unique"]
        }
        foreign = connection.execute(
            "PRAGMA foreign_key_list(written_draft_revisions)"
        ).fetchall()
        if indexes != {("pk", ("project", "branch", "chapter_id", "version"))} or [
            (
                row["seq"],
                row["table"],
                row["from"],
                row["to"],
                row["on_update"],
                row["on_delete"],
                row["match"],
            )
            for row in foreign
        ] != [(0, "runs", "run_id", "run_id", "NO ACTION", "NO ACTION", "NONE")]:
            raise WorkflowError("INVALID_WRITTEN_DRAFT_SCHEMA")
        if (
            connection.execute(
                "PRAGMA foreign_key_check(written_draft_revisions)"
            ).fetchone()
            is not None
        ):
            raise WorkflowError("CORRUPT_WRITTEN_DRAFT")
        return True

    @staticmethod
    def _written_draft_lineage(
        connection: sqlite3.Connection, scope: tuple[str, str, str]
    ) -> Iterator[WrittenDraftRevision]:
        from .written_draft import WrittenDraftRevision

        previous: WrittenDraftRevision | None = None
        expected_hash: str | None = None
        rows = connection.execute(
            "SELECT revisions.version, revisions.run_id, revisions.previous_revision_hash, "
            "revisions.payload, revisions.payload_hash, runs.project AS run_project, "
            "runs.branch AS run_branch FROM written_draft_revisions AS revisions "
            "JOIN runs ON runs.run_id=revisions.run_id "
            "WHERE revisions.project=? AND revisions.branch=? AND revisions.chapter_id=? "
            "ORDER BY revisions.version",
            scope,
        )
        for version, row in enumerate(rows, 1):
            raw = row["payload"]
            if (
                row["version"] != version
                or row["previous_revision_hash"] != expected_hash
                or (row["run_project"], row["run_branch"]) != scope[:2]
                or type(raw) is not bytes
                or hashlib.sha256(raw).hexdigest() != row["payload_hash"]
            ):
                raise WorkflowError("CORRUPT_WRITTEN_DRAFT")
            try:
                revision = _decode_retained_payload(
                    raw, WrittenDraftRevision.from_bytes
                )
                if (
                    revision.project,
                    revision.branch,
                    revision.chapter_id.local_id,
                    revision.version,
                    revision.run_id,
                    revision.previous_revision_hash,
                ) != (
                    *scope,
                    version,
                    row["run_id"],
                    expected_hash,
                ):
                    raise ValueError
                if previous is not None:
                    source_changed = (
                        revision.source_revision_hash != previous.source_revision_hash
                    )
                    input_changed = (
                        revision.writer_input_hash != previous.writer_input_hash
                    )
                    if (
                        revision.lineage_key != previous.lineage_key
                        or source_changed != input_changed
                        or (
                            source_changed
                            and (revision.choice is not None or revision.continuity)
                        )
                    ):
                        raise ValueError
            except (TypeError, ValueError, KeyError, RecursionError):
                raise WorkflowError("CORRUPT_WRITTEN_DRAFT") from None
            expected_hash = row["payload_hash"]
            previous = revision
            yield revision

    def load_written_draft(
        self,
        *,
        project: str,
        branch: str,
        chapter_id: EntityId,
        version: int | None = None,
    ) -> WrittenDraftRevision:
        """Read the requested revision or the current head of a local Draft."""
        from anovel.domain.identity import EntityId

        if type(chapter_id) is not EntityId or chapter_id.project != project:
            raise WorkflowError("WRITTEN_DRAFT_UNAVAILABLE")
        if version is not None and (type(version) is not int or version < 1):
            raise WorkflowError("INVALID_WRITTEN_DRAFT")
        scope = _identity(project, branch, chapter_id.local_id)
        with self._connection() as connection:
            connection.execute("BEGIN")
            if not self._written_draft_table(connection, create=False):
                raise WorkflowError("WRITTEN_DRAFT_UNAVAILABLE")
            selected = None
            for revision in self._written_draft_lineage(connection, scope):
                if version is None or revision.version == version:
                    selected = revision
            if selected is None:
                raise WorkflowError("WRITTEN_DRAFT_UNAVAILABLE")
            return selected

    def load_written_draft_heads(
        self, *, project: str, branch: str, run_id: str
    ) -> tuple[WrittenDraftRevision, ...]:
        """Read the current Drafts of one run in a single database snapshot."""
        scope = _identity(project, branch, run_id)
        with self._connection() as connection:
            connection.execute("BEGIN")
            if not self._written_draft_table(connection, create=False):
                return ()
            chapters = connection.execute(
                "SELECT DISTINCT chapter_id FROM written_draft_revisions "
                "WHERE project=? AND branch=? AND run_id=?",
                scope,
            )
            heads: list[WrittenDraftRevision] = []
            for chapter in chapters:
                head = None
                for revision in self._written_draft_lineage(
                    connection, (*scope[:2], chapter["chapter_id"])
                ):
                    head = revision
                if head is None or head.run_id != run_id:
                    raise WorkflowError("CORRUPT_WRITTEN_DRAFT")
                heads.append(head)
            return tuple(heads)

    def append_written_draft(
        self, revision: WrittenDraftRevision, *, rewrite: bool = False
    ) -> WrittenDraftRevision:
        """Append against an exact predecessor, rotating provenance only for a rewrite."""
        from .written_draft import WrittenDraftRevision

        if type(revision) is not WrittenDraftRevision or type(rewrite) is not bool:
            raise WorkflowError("INVALID_WRITTEN_DRAFT")
        raw = revision.payload_bytes()
        saved = WrittenDraftRevision.from_bytes(raw)
        scope = _identity(saved.project, saved.branch, saved.chapter_id.local_id)
        with self._transaction() as connection:
            self._written_draft_table(connection, create=True)
            if (
                connection.execute(
                    "SELECT 1 FROM runs WHERE run_id=? AND project=? AND branch=?",
                    (saved.run_id, *scope[:2]),
                ).fetchone()
                is None
            ):
                raise WorkflowError("WRITTEN_DRAFT_REVISION_CONFLICT")
            prior = existing = None
            for current in self._written_draft_lineage(connection, scope):
                if current.version < saved.version:
                    prior = current
                elif current.version == saved.version:
                    existing = current
            next_version = 1 if prior is None else prior.version + 1
            expected = None if prior is None else prior.record_hash
            source_changed = (
                prior is not None
                and saved.source_revision_hash != prior.source_revision_hash
            )
            input_changed = (
                prior is not None and saved.writer_input_hash != prior.writer_input_hash
            )
            if (
                saved.version != next_version
                or saved.previous_revision_hash != expected
                or (prior is not None and saved.lineage_key != prior.lineage_key)
                or source_changed != rewrite
                or input_changed != rewrite
                or (rewrite and (saved.choice is not None or saved.continuity))
            ):
                raise WorkflowError("WRITTEN_DRAFT_REVISION_CONFLICT")
            if existing is not None:
                if existing.payload_bytes() != raw:
                    raise WorkflowError("WRITTEN_DRAFT_REVISION_CONFLICT")
                return existing
            connection.execute(
                "INSERT INTO written_draft_revisions "
                "(project, branch, chapter_id, version, run_id, previous_revision_hash, payload, payload_hash) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (*scope, saved.version, saved.run_id, expected, raw, saved.record_hash),
            )
            return saved

    @staticmethod
    def _revision_q0_table(connection: sqlite3.Connection, *, create: bool) -> bool:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='revision_q0_executions'"
        ).fetchone()
        if exists is None:
            if not create:
                return False
            connection.execute(_REVISION_Q0_SCHEMA)
        columns = connection.execute(
            "PRAGMA table_info(revision_q0_executions)"
        ).fetchall()
        if [
            (row["name"], row["type"].upper(), row["pk"], row["notnull"])
            for row in columns
        ] != [
            ("project", "TEXT", 1, 1),
            ("branch", "TEXT", 2, 1),
            ("chapter_id", "TEXT", 3, 1),
            ("revision_hash", "TEXT", 4, 1),
            ("policy_hash", "TEXT", 5, 1),
            ("version", "INTEGER", 0, 1),
            ("payload", "BLOB", 0, 1),
            ("payload_hash", "TEXT", 0, 1),
        ] or any(row["dflt_value"] is not None for row in columns):
            raise WorkflowError("INVALID_REVISION_Q0_SCHEMA")
        indexes = {
            (
                row["origin"],
                tuple(
                    col["name"]
                    for col in connection.execute(
                        "SELECT name FROM pragma_index_info(?) ORDER BY seqno",
                        (row["name"],),
                    )
                ),
            )
            for row in connection.execute("PRAGMA index_list(revision_q0_executions)")
            if row["unique"] and not row["partial"]
        }
        if indexes != {
            ("pk", ("project", "branch", "chapter_id", "revision_hash", "policy_hash")),
        }:
            raise WorkflowError("INVALID_REVISION_Q0_SCHEMA")
        foreign = connection.execute(
            "PRAGMA foreign_key_list(revision_q0_executions)"
        ).fetchall()
        if (
            len(foreign) != 4
            or len({row["id"] for row in foreign}) != 1
            or {(row["seq"], row["table"], row["from"], row["to"]) for row in foreign}
            != {
                (i, "chapter_revisions", name, name)
                for i, name in enumerate(("project", "branch", "chapter_id", "version"))
            }
            or any(
                (row["on_update"], row["on_delete"], row["match"])
                != ("NO ACTION", "NO ACTION", "NONE")
                for row in foreign
            )
        ):
            raise WorkflowError("INVALID_REVISION_Q0_SCHEMA")
        if (
            connection.execute(
                "PRAGMA foreign_key_check(revision_q0_executions)"
            ).fetchone()
            is not None
        ):
            raise WorkflowError("CORRUPT_REVISION_Q0_EXECUTION")
        return True

    @staticmethod
    def _decode_revision_q0(row: sqlite3.Row) -> RevisionQ0Run:
        from anovel.quality.revision_q0 import RevisionQ0Run

        try:
            raw = row["payload"]
            if (
                type(raw) is not bytes
                or hashlib.sha256(raw).hexdigest() != row["payload_hash"]
            ):
                raise ValueError
            saved = _decode_retained_payload(raw, RevisionQ0Run.from_bytes)
            revision = saved.revision
            if (
                revision.project,
                revision.branch,
                revision.chapter_id.local_id,
                saved.revision_hash,
                saved.policy_hash,
                revision.version,
            ) != (
                row["project"],
                row["branch"],
                row["chapter_id"],
                row["revision_hash"],
                row["policy_hash"],
                row["version"],
            ):
                raise ValueError
            return saved
        except (TypeError, ValueError, KeyError, IndexError, RecursionError):
            raise WorkflowError("CORRUPT_REVISION_Q0_EXECUTION") from None

    def _current_revision_q0_sources(
        self,
        connection: sqlite3.Connection,
        scope: tuple[str, str, str],
        revision_hash: str,
    ) -> tuple[ChapterRevision, ExtractionObservation]:
        if not self._chapter_revision_table(connection, create=False):
            raise WorkflowError("CHAPTER_REVISION_UNAVAILABLE")
        lineage = self._chapter_revision_lineage(connection, scope)
        if not lineage:
            raise WorkflowError("CHAPTER_REVISION_UNAVAILABLE")
        revision, observation = self._chapter_revision_with_observation(
            connection, scope, len(lineage)
        )
        if revision.record_hash != revision_hash:
            raise WorkflowError("CHAPTER_REVISION_CHANGED")
        self._extraction_source(connection, observation)
        return revision, observation

    def _revision_q0_lookup(
        self,
        connection: sqlite3.Connection,
        scope: tuple[str, str, str],
        revision_hash: str,
        policy_hash: str,
    ) -> RevisionQ0Run | None:
        row = connection.execute(
            "SELECT * FROM revision_q0_executions WHERE project=? AND branch=? "
            "AND chapter_id=? AND revision_hash=? AND policy_hash=?",
            (*scope, revision_hash, policy_hash),
        ).fetchone()
        if row is not None:
            return self._decode_revision_q0(row)
        # A corrupt index key must never silently become a fresh execution.
        for previous in connection.execute(
            "SELECT * FROM revision_q0_executions WHERE (project=? AND branch=? "
            "AND chapter_id=?) OR revision_hash=?",
            (*scope, revision_hash),
        ):
            self._decode_revision_q0(previous)
        return None

    def load_revision_q0(
        self,
        *,
        project: str,
        branch: str,
        chapter_id: EntityId,
        revision_hash: str,
        policy_hash: str,
    ) -> RevisionQ0Run:
        """Read the exact current revision/policy pair in one SQLite snapshot."""
        from anovel.domain.identity import EntityId

        if type(chapter_id) is not EntityId or chapter_id.project != project:
            raise WorkflowError("CHAPTER_REVISION_UNAVAILABLE")
        scope = _identity(project, branch, chapter_id.local_id)
        _scene_hash(revision_hash)
        _scene_hash(policy_hash)
        with self._connection() as connection:
            connection.execute("BEGIN")
            revision, observation = self._current_revision_q0_sources(
                connection, scope, revision_hash
            )
            saved = self._read_revision_q0(
                connection, scope, revision, observation, policy_hash
            )
            if saved is None:
                raise WorkflowError("REVISION_Q0_EXECUTION_UNAVAILABLE")
            return saved

    def _read_revision_q0(
        self,
        connection: sqlite3.Connection,
        scope: tuple[str, str, str],
        revision: ChapterRevision,
        observation: ExtractionObservation,
        policy_hash: str,
    ) -> RevisionQ0Run | None:
        if not self._revision_q0_table(connection, create=False):
            return None
        saved = self._revision_q0_lookup(
            connection, scope, revision.record_hash, policy_hash
        )
        if saved is not None:
            try:
                saved.require_sources(revision, observation)
            except ValueError:
                raise WorkflowError("CORRUPT_REVISION_Q0_EXECUTION") from None
        return saved

    def create_revision_q0(self, result: RevisionQ0Run) -> bool:
        """Persist a native local run only if its revision is still current."""
        from anovel.quality.revision_q0 import RevisionQ0Run, require_native_revision_q0

        try:
            require_native_revision_q0(result)
            raw = result.payload_bytes()
            saved = _decode_retained_payload(raw, RevisionQ0Run.from_bytes)
        except ValueError as error:
            raise WorkflowError(str(error)) from None
        revision = saved.revision
        scope = _identity(
            revision.project, revision.branch, revision.chapter_id.local_id
        )
        with self._transaction() as connection:
            current, observation = self._current_revision_q0_sources(
                connection, scope, saved.revision_hash
            )
            try:
                saved.require_sources(current, observation)
            except ValueError as error:
                raise WorkflowError(str(error)) from None
            self._revision_q0_table(connection, create=True)
            prior = self._revision_q0_lookup(
                connection, scope, saved.revision_hash, saved.policy_hash
            )
            if prior is not None:
                if prior.payload_bytes() != raw:
                    raise WorkflowError("REVISION_Q0_EXECUTION_CONFLICT")
                return False
            connection.execute(
                "INSERT INTO revision_q0_executions VALUES(?,?,?,?,?,?,?,?)",
                (
                    *scope,
                    saved.revision_hash,
                    saved.policy_hash,
                    revision.version,
                    raw,
                    saved.record_hash,
                ),
            )
            return True

    @staticmethod
    def _revision_q123_table(connection: sqlite3.Connection, *, create: bool) -> bool:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='revision_q123_executions'"
        ).fetchone()
        if exists is None:
            if not create:
                return False
            connection.execute(_REVISION_Q123_SCHEMA)
        columns = connection.execute(
            "PRAGMA table_info(revision_q123_executions)"
        ).fetchall()
        if [
            (row["name"], row["type"].upper(), row["pk"], row["notnull"])
            for row in columns
        ] != [
            ("project", "TEXT", 1, 1),
            ("branch", "TEXT", 2, 1),
            ("chapter_id", "TEXT", 3, 1),
            ("revision_hash", "TEXT", 4, 1),
            ("policy_hash", "TEXT", 5, 1),
            ("annotations_hash", "TEXT", 6, 1),
            ("version", "INTEGER", 0, 1),
            ("payload", "BLOB", 0, 1),
            ("payload_hash", "TEXT", 0, 1),
        ] or any(row["dflt_value"] is not None for row in columns):
            raise WorkflowError("INVALID_REVISION_Q123_SCHEMA")
        indexes = {
            (
                row["origin"],
                tuple(
                    column["name"]
                    for column in connection.execute(
                        "SELECT name FROM pragma_index_info(?) ORDER BY seqno",
                        (row["name"],),
                    )
                ),
            )
            for row in connection.execute("PRAGMA index_list(revision_q123_executions)")
            if row["unique"]
        }
        primary = (
            "project",
            "branch",
            "chapter_id",
            "revision_hash",
            "policy_hash",
            "annotations_hash",
        )
        if indexes != {("pk", primary)}:
            raise WorkflowError("INVALID_REVISION_Q123_SCHEMA")
        foreign = connection.execute(
            "PRAGMA foreign_key_list(revision_q123_executions)"
        ).fetchall()
        if (
            len(foreign) != 4
            or len({row["id"] for row in foreign}) != 1
            or {(row["seq"], row["table"], row["from"], row["to"]) for row in foreign}
            != {
                (i, "chapter_revisions", name, name)
                for i, name in enumerate(("project", "branch", "chapter_id", "version"))
            }
            or any(
                (row["on_update"], row["on_delete"], row["match"])
                != ("NO ACTION", "NO ACTION", "NONE")
                for row in foreign
            )
        ):
            raise WorkflowError("INVALID_REVISION_Q123_SCHEMA")
        if (
            connection.execute(
                "PRAGMA foreign_key_check(revision_q123_executions)"
            ).fetchone()
            is not None
        ):
            raise WorkflowError("CORRUPT_REVISION_Q123_EXECUTION")
        return True

    @staticmethod
    def _decode_revision_q123(row: sqlite3.Row) -> RevisionQ123Run:
        from anovel.quality.revision_q123 import RevisionQ123Run

        try:
            raw = row["payload"]
            if (
                type(raw) is not bytes
                or hashlib.sha256(raw).hexdigest() != row["payload_hash"]
            ):
                raise ValueError
            saved = _decode_retained_payload(raw, RevisionQ123Run.from_bytes)
            revision = saved.revision
            if (
                revision.project,
                revision.branch,
                revision.chapter_id.local_id,
                saved.revision_hash,
                saved.policy_hash,
                saved.annotations_hash,
                revision.version,
            ) != (
                row["project"],
                row["branch"],
                row["chapter_id"],
                row["revision_hash"],
                row["policy_hash"],
                row["annotations_hash"],
                row["version"],
            ):
                raise ValueError
            return saved
        except (TypeError, ValueError, KeyError, IndexError, RecursionError):
            raise WorkflowError("CORRUPT_REVISION_Q123_EXECUTION") from None

    def _revision_q123_lookup(
        self,
        connection: sqlite3.Connection,
        scope: tuple[str, str, str],
        revision_hash: str,
        policy_hash: str,
        annotations_hash: str,
    ) -> RevisionQ123Run | None:
        row = connection.execute(
            "SELECT * FROM revision_q123_executions WHERE project=? AND branch=? "
            "AND chapter_id=? AND revision_hash=? AND policy_hash=? AND annotations_hash=?",
            (*scope, revision_hash, policy_hash, annotations_hash),
        ).fetchone()
        if row is not None:
            return self._decode_revision_q123(row)
        # On an active key miss, distinguish corrupted coordinates from a valid
        # earlier revision, policy or annotation set.
        for previous in connection.execute(
            "SELECT * FROM revision_q123_executions WHERE (project=? AND branch=? "
            "AND chapter_id=?) OR revision_hash=?",
            (*scope, revision_hash),
        ):
            self._decode_revision_q123(previous)
        return None

    def load_revision_q123(
        self,
        *,
        project: str,
        branch: str,
        chapter_id: EntityId,
        revision_hash: str,
        policy_hash: str,
        annotations_hash: str,
    ) -> RevisionQ123Run:
        """Read one current revision's local check bundle in a SQLite snapshot."""
        from anovel.domain.identity import EntityId

        if type(chapter_id) is not EntityId or chapter_id.project != project:
            raise WorkflowError("CHAPTER_REVISION_UNAVAILABLE")
        scope = _identity(project, branch, chapter_id.local_id)
        for value in (revision_hash, policy_hash, annotations_hash):
            _scene_hash(value)
        with self._connection() as connection:
            connection.execute("BEGIN")
            revision, observation = self._current_revision_q0_sources(
                connection, scope, revision_hash
            )
            saved = self._read_revision_q123(
                connection, scope, revision, observation, policy_hash, annotations_hash
            )
            if saved is None:
                raise WorkflowError("REVISION_Q123_EXECUTION_UNAVAILABLE")
            return saved

    def _read_revision_q123(
        self,
        connection: sqlite3.Connection,
        scope: tuple[str, str, str],
        revision: ChapterRevision,
        observation: ExtractionObservation,
        policy_hash: str,
        annotations_hash: str,
    ) -> RevisionQ123Run | None:
        if not self._revision_q123_table(connection, create=False):
            return None
        saved = self._revision_q123_lookup(
            connection, scope, revision.record_hash, policy_hash, annotations_hash
        )
        if saved is not None:
            try:
                saved.require_sources(revision, observation, saved.q1.annotations)
            except ValueError:
                raise WorkflowError("CORRUPT_REVISION_Q123_EXECUTION") from None
        return saved

    def load_revision_quality(
        self,
        *,
        revision: ChapterRevision,
        observation: ExtractionObservation,
        q0_policy_hash: str,
        q123_policy_hash: str,
        annotations_hash: str,
    ) -> tuple[RevisionQ0Run | None, RevisionQ123Run | None]:
        """Read both evidence groups and verify the selected sources in one snapshot."""
        scope = _identity(
            revision.project, revision.branch, revision.chapter_id.local_id
        )
        for value in (q0_policy_hash, q123_policy_hash, annotations_hash):
            _scene_hash(value)
        with self._connection() as connection:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("BEGIN")
            saved_revision, saved_observation = self._current_revision_q0_sources(
                connection, scope, revision.record_hash
            )
            if saved_observation.payload_bytes() != observation.payload_bytes():
                raise WorkflowError("CHAPTER_REVISION_OBSERVATION_CHANGED")
            zero = self._read_revision_q0(
                connection, scope, saved_revision, saved_observation, q0_policy_hash
            )
            remaining = self._read_revision_q123(
                connection,
                scope,
                saved_revision,
                saved_observation,
                q123_policy_hash,
                annotations_hash,
            )
            return zero, remaining

    def create_revision_q123(self, result: RevisionQ123Run) -> bool:
        """Persist a native local bundle only for the still-current Draft."""
        from anovel.quality.revision_q123 import (
            RevisionQ123Run,
            require_native_revision_q123,
        )

        try:
            require_native_revision_q123(result)
            raw = result.payload_bytes()
            saved = _decode_retained_payload(raw, RevisionQ123Run.from_bytes)
        except ValueError as error:
            raise WorkflowError(str(error)) from None
        revision = saved.revision
        scope = _identity(
            revision.project, revision.branch, revision.chapter_id.local_id
        )
        with self._transaction() as connection:
            current, observation = self._current_revision_q0_sources(
                connection, scope, saved.revision_hash
            )
            try:
                saved.require_sources(current, observation, saved.q1.annotations)
            except ValueError as error:
                raise WorkflowError(str(error)) from None
            self._revision_q123_table(connection, create=True)
            previous = self._revision_q123_lookup(
                connection,
                scope,
                saved.revision_hash,
                saved.policy_hash,
                saved.annotations_hash,
            )
            if previous is not None:
                if previous.payload_bytes() != raw:
                    raise WorkflowError("REVISION_Q123_EXECUTION_CONFLICT")
                return False
            connection.execute(
                "INSERT INTO revision_q123_executions VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    *scope,
                    saved.revision_hash,
                    saved.policy_hash,
                    saved.annotations_hash,
                    revision.version,
                    raw,
                    saved.record_hash,
                ),
            )
            return True

    @staticmethod
    def _q0_table(connection: sqlite3.Connection, *, create: bool) -> bool:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='q0_executions'"
        ).fetchone()
        if exists is None:
            if not create:
                return False
            connection.execute(_Q0_SCHEMA)
        columns = connection.execute("PRAGMA table_info(q0_executions)").fetchall()
        if (
            [row["name"] for row in columns]
            != [
                "run_id",
                "step_id",
                "observation_hash",
                "assembly_hash",
                "project",
                "branch",
                "payload",
                "payload_hash",
            ]
            or [row["type"].upper() for row in columns]
            != ["TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "BLOB", "TEXT"]
            or [row["pk"] for row in columns] != [1, 2, 3, 0, 0, 0, 0, 0]
            or any(
                row["notnull"] != 1 or row["dflt_value"] is not None for row in columns
            )
        ):
            raise WorkflowError("INVALID_Q0_SCHEMA")
        foreign = connection.execute(
            "PRAGMA foreign_key_list(q0_executions)"
        ).fetchall()
        if (
            len(foreign) != 3
            or len({row["id"] for row in foreign}) != 1
            or {row["seq"] for row in foreign} != {0, 1, 2}
            or any(
                (row["on_update"], row["on_delete"], row["match"])
                != ("NO ACTION", "NO ACTION", "NONE")
                for row in foreign
            )
            or {(row["table"], row["from"], row["to"]) for row in foreign}
            != {
                ("extraction_observations", "run_id", "run_id"),
                ("extraction_observations", "step_id", "step_id"),
                ("extraction_observations", "assembly_hash", "assembly_hash"),
            }
        ):
            raise WorkflowError("INVALID_Q0_SCHEMA")
        if (
            connection.execute("PRAGMA foreign_key_check(q0_executions)").fetchone()
            is not None
        ):
            raise WorkflowError("CORRUPT_Q0_EXECUTION")
        return True

    @staticmethod
    def _decode_q0(row: sqlite3.Row) -> Q0Run:
        from anovel.quality.q0 import Q0Run

        try:
            raw = row["payload"]
            if (
                type(raw) is not bytes
                or hashlib.sha256(raw).hexdigest() != row["payload_hash"]
            ):
                raise ValueError
            saved = _decode_retained_payload(raw, Q0Run.from_bytes)
            if (
                saved.project,
                saved.branch,
                saved.run_id,
                saved.step_id,
                saved.observation_hash,
                saved.assembly_hash,
            ) != (
                row["project"],
                row["branch"],
                row["run_id"],
                row["step_id"],
                row["observation_hash"],
                row["assembly_hash"],
            ):
                raise ValueError
            return saved
        except (TypeError, ValueError, KeyError, IndexError, RecursionError):
            raise WorkflowError("CORRUPT_Q0_EXECUTION") from None

    @staticmethod
    def _q0_source(connection: sqlite3.Connection, saved: Q0Run) -> None:
        if not WorkflowStore._extraction_table(connection, create=False):
            raise WorkflowError("Q0_SOURCE_CHANGED")
        row = connection.execute(
            "SELECT * FROM extraction_observations WHERE run_id=? AND step_id=? AND assembly_hash=?",
            (saved.run_id, saved.step_id, saved.assembly_hash),
        ).fetchone()
        if row is None:
            raise WorkflowError("Q0_SOURCE_CHANGED")
        observation = WorkflowStore._decode_extraction(row)
        if (
            observation.record_hash != saved.observation_hash
            or observation.payload_bytes() != saved.observation.payload_bytes()
        ):
            raise WorkflowError("Q0_SOURCE_CHANGED")
        WorkflowStore._extraction_source(connection, observation)

    def load_q0(
        self,
        *,
        project: str,
        branch: str,
        run_id: str,
        step_id: str,
        observation_hash: str,
    ) -> Q0Run:
        _identity(project, branch, run_id)
        _scene_hash(step_id)
        _scene_hash(observation_hash)
        with self._connection() as connection:
            self._scene_parent(connection, project, branch, run_id)
            if not self._q0_table(connection, create=False):
                raise WorkflowError("Q0_EXECUTION_UNAVAILABLE")
            row = connection.execute(
                "SELECT * FROM q0_executions WHERE run_id=? AND step_id=? AND observation_hash=?",
                (run_id, step_id, observation_hash),
            ).fetchone()
            if row is None:
                # Never turn a damaged retained key into a request for a new run.
                # Valid older executions remain history, not current evidence.
                for previous in connection.execute("SELECT * FROM q0_executions"):
                    self._decode_q0(previous)
                raise WorkflowError("Q0_EXECUTION_UNAVAILABLE")
            if (row["project"], row["branch"]) != (project, branch):
                raise WorkflowError("CORRUPT_Q0_EXECUTION")
            saved = self._decode_q0(row)
            self._q0_source(connection, saved)
            return saved

    def create_q0(self, result: Q0Run) -> bool:
        from anovel.quality.q0 import Q0Error, Q0Run, require_local_execution

        # Parsed JSON is an audit object, never a newly executed local receipt.
        try:
            require_local_execution(result)
        except Q0Error as error:
            raise WorkflowError(str(error)) from None
        raw = result.payload_bytes()
        saved = Q0Run.from_bytes(raw)
        value_hash = hashlib.sha256(raw).hexdigest()
        if saved.record_hash != result.record_hash:
            raise WorkflowError("CORRUPT_Q0_EXECUTION")
        with self._transaction() as connection:
            self._q0_source(connection, saved)
            self._q0_table(connection, create=True)
            row = connection.execute(
                "SELECT * FROM q0_executions WHERE run_id=? AND step_id=? AND observation_hash=?",
                (saved.run_id, saved.step_id, saved.observation_hash),
            ).fetchone()
            if row is not None:
                existing = self._decode_q0(row)
                if existing.payload_bytes() != raw:
                    raise WorkflowError("Q0_EXECUTION_CONFLICT")
                return False
            for previous in connection.execute("SELECT * FROM q0_executions"):
                self._decode_q0(previous)
            connection.execute(
                "INSERT INTO q0_executions VALUES(?,?,?,?,?,?,?,?)",
                (
                    saved.run_id,
                    saved.step_id,
                    saved.observation_hash,
                    saved.assembly_hash,
                    saved.project,
                    saved.branch,
                    raw,
                    value_hash,
                ),
            )
            return True

    @staticmethod
    def _q1_table(connection: sqlite3.Connection, *, create: bool) -> bool:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='q1_executions'"
        ).fetchone()
        if exists is None:
            if not create:
                return False
            connection.execute(_Q1_SCHEMA)
        columns = connection.execute("PRAGMA table_info(q1_executions)").fetchall()
        if (
            [row["name"] for row in columns]
            != [
                "run_id",
                "step_id",
                "observation_hash",
                "annotations_hash",
                "assembly_hash",
                "project",
                "branch",
                "payload",
                "payload_hash",
            ]
            or [row["type"].upper() for row in columns]
            != ["TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "BLOB", "TEXT"]
            or [row["pk"] for row in columns] != [1, 2, 3, 4, 0, 0, 0, 0, 0]
            or any(
                row["notnull"] != 1 or row["dflt_value"] is not None for row in columns
            )
        ):
            raise WorkflowError("INVALID_Q1_SCHEMA")
        foreign = connection.execute(
            "PRAGMA foreign_key_list(q1_executions)"
        ).fetchall()
        if (
            len(foreign) != 3
            or len({row["id"] for row in foreign}) != 1
            or {row["seq"] for row in foreign} != {0, 1, 2}
            or any(
                (row["on_update"], row["on_delete"], row["match"])
                != ("NO ACTION", "NO ACTION", "NONE")
                for row in foreign
            )
            or {(row["table"], row["from"], row["to"]) for row in foreign}
            != {
                ("extraction_observations", "run_id", "run_id"),
                ("extraction_observations", "step_id", "step_id"),
                ("extraction_observations", "assembly_hash", "assembly_hash"),
            }
        ):
            raise WorkflowError("INVALID_Q1_SCHEMA")
        if (
            connection.execute("PRAGMA foreign_key_check(q1_executions)").fetchone()
            is not None
        ):
            raise WorkflowError("CORRUPT_Q1_EXECUTION")
        return True

    @staticmethod
    def _decode_q1(row: sqlite3.Row) -> Q1Run:
        from anovel.quality.q1 import Q1Run

        try:
            raw = row["payload"]
            if (
                type(raw) is not bytes
                or hashlib.sha256(raw).hexdigest() != row["payload_hash"]
            ):
                raise ValueError
            saved = _decode_retained_payload(raw, Q1Run.from_bytes)
            if (
                saved.project,
                saved.branch,
                saved.run_id,
                saved.step_id,
                saved.observation_hash,
                saved.annotations_hash,
                saved.assembly_hash,
            ) != (
                row["project"],
                row["branch"],
                row["run_id"],
                row["step_id"],
                row["observation_hash"],
                row["annotations_hash"],
                row["assembly_hash"],
            ):
                raise ValueError
            return saved
        except (TypeError, ValueError, KeyError, IndexError, RecursionError):
            raise WorkflowError("CORRUPT_Q1_EXECUTION") from None

    @staticmethod
    def _q1_source(connection: sqlite3.Connection, saved: Q1Run) -> None:
        if not WorkflowStore._extraction_table(connection, create=False):
            raise WorkflowError("Q1_SOURCE_CHANGED")
        row = connection.execute(
            "SELECT * FROM extraction_observations WHERE run_id=? AND step_id=? AND assembly_hash=?",
            (saved.run_id, saved.step_id, saved.assembly_hash),
        ).fetchone()
        if row is None:
            raise WorkflowError("Q1_SOURCE_CHANGED")
        observation = WorkflowStore._decode_extraction(row)
        if (
            observation.record_hash != saved.observation_hash
            or observation.payload_bytes() != saved.observation.payload_bytes()
        ):
            raise WorkflowError("Q1_SOURCE_CHANGED")
        WorkflowStore._extraction_source(connection, observation)

    def load_q1(
        self,
        *,
        project: str,
        branch: str,
        run_id: str,
        step_id: str,
        observation_hash: str,
        annotations_hash: str,
    ) -> Q1Run:
        _identity(project, branch, run_id)
        for value in (step_id, observation_hash, annotations_hash):
            _scene_hash(value)
        with self._connection() as connection:
            self._scene_parent(connection, project, branch, run_id)
            if not self._q1_table(connection, create=False):
                raise WorkflowError("Q1_EXECUTION_UNAVAILABLE")
            row = connection.execute(
                "SELECT * FROM q1_executions WHERE run_id=? AND step_id=? AND observation_hash=? AND annotations_hash=?",
                (run_id, step_id, observation_hash, annotations_hash),
            ).fetchone()
            if row is None:
                # A retained corrupt identity must never trigger a fresh run.
                # Valid other annotation versions remain immutable history.
                for previous in connection.execute("SELECT * FROM q1_executions"):
                    self._decode_q1(previous)
                raise WorkflowError("Q1_EXECUTION_UNAVAILABLE")
            if (row["project"], row["branch"]) != (project, branch):
                raise WorkflowError("CORRUPT_Q1_EXECUTION")
            saved = self._decode_q1(row)
            self._q1_source(connection, saved)
            return saved

    def create_q1(self, result: Q1Run) -> bool:
        from anovel.quality.q1 import Q1Error, Q1Run, require_local_execution_q1

        try:
            require_local_execution_q1(result)
        except Q1Error as error:
            raise WorkflowError(str(error)) from None
        raw = result.payload_bytes()
        saved = Q1Run.from_bytes(raw)
        value_hash = hashlib.sha256(raw).hexdigest()
        if saved.record_hash != result.record_hash:
            raise WorkflowError("CORRUPT_Q1_EXECUTION")
        with self._transaction() as connection:
            self._q1_source(connection, saved)
            self._q1_table(connection, create=True)
            row = connection.execute(
                "SELECT * FROM q1_executions WHERE run_id=? AND step_id=? AND observation_hash=? AND annotations_hash=?",
                (
                    saved.run_id,
                    saved.step_id,
                    saved.observation_hash,
                    saved.annotations_hash,
                ),
            ).fetchone()
            if row is not None:
                existing = self._decode_q1(row)
                if existing.payload_bytes() != raw:
                    raise WorkflowError("Q1_EXECUTION_CONFLICT")
                return False
            for previous in connection.execute("SELECT * FROM q1_executions"):
                self._decode_q1(previous)
            connection.execute(
                "INSERT INTO q1_executions VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    saved.run_id,
                    saved.step_id,
                    saved.observation_hash,
                    saved.annotations_hash,
                    saved.assembly_hash,
                    saved.project,
                    saved.branch,
                    raw,
                    value_hash,
                ),
            )
            return True

    @staticmethod
    def _q2_table(connection: sqlite3.Connection, *, create: bool) -> bool:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='q2_executions'"
        ).fetchone()
        if exists is None:
            if not create:
                return False
            connection.execute(_Q2_SCHEMA)
        columns = connection.execute("PRAGMA table_info(q2_executions)").fetchall()
        if (
            [row["name"] for row in columns]
            != [
                "run_id",
                "step_id",
                "observation_hash",
                "method_policy_hash",
                "assembly_hash",
                "project",
                "branch",
                "payload",
                "payload_hash",
            ]
            or [row["type"].upper() for row in columns]
            != ["TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "BLOB", "TEXT"]
            or [row["pk"] for row in columns] != [1, 2, 3, 4, 0, 0, 0, 0, 0]
            or any(
                row["notnull"] != 1 or row["dflt_value"] is not None for row in columns
            )
        ):
            raise WorkflowError("INVALID_Q2_SCHEMA")
        foreign = connection.execute(
            "PRAGMA foreign_key_list(q2_executions)"
        ).fetchall()
        if (
            len(foreign) != 3
            or len({row["id"] for row in foreign}) != 1
            or {row["seq"] for row in foreign} != {0, 1, 2}
            or any(
                (row["on_update"], row["on_delete"], row["match"])
                != ("NO ACTION", "NO ACTION", "NONE")
                for row in foreign
            )
            or {(row["table"], row["from"], row["to"]) for row in foreign}
            != {
                ("extraction_observations", "run_id", "run_id"),
                ("extraction_observations", "step_id", "step_id"),
                ("extraction_observations", "assembly_hash", "assembly_hash"),
            }
        ):
            raise WorkflowError("INVALID_Q2_SCHEMA")
        if (
            connection.execute("PRAGMA foreign_key_check(q2_executions)").fetchone()
            is not None
        ):
            raise WorkflowError("CORRUPT_Q2_EXECUTION")
        return True

    @staticmethod
    def _decode_q2(row: sqlite3.Row) -> Q2Run:
        from anovel.quality.q2 import Q2Run

        try:
            raw = row["payload"]
            if (
                type(raw) is not bytes
                or hashlib.sha256(raw).hexdigest() != row["payload_hash"]
            ):
                raise ValueError
            saved = _decode_retained_payload(raw, Q2Run.from_bytes)
            if (
                saved.project,
                saved.branch,
                saved.run_id,
                saved.step_id,
                saved.observation_hash,
                saved.method_policy_hash,
                saved.assembly_hash,
            ) != (
                row["project"],
                row["branch"],
                row["run_id"],
                row["step_id"],
                row["observation_hash"],
                row["method_policy_hash"],
                row["assembly_hash"],
            ):
                raise ValueError
            return saved
        except (TypeError, ValueError, KeyError, IndexError, RecursionError):
            raise WorkflowError("CORRUPT_Q2_EXECUTION") from None

    @staticmethod
    def _q2_source(connection: sqlite3.Connection, saved: Q2Run) -> None:
        if not WorkflowStore._extraction_table(connection, create=False):
            raise WorkflowError("Q2_SOURCE_CHANGED")
        row = connection.execute(
            "SELECT * FROM extraction_observations WHERE run_id=? AND step_id=? AND assembly_hash=?",
            (saved.run_id, saved.step_id, saved.assembly_hash),
        ).fetchone()
        if row is None:
            raise WorkflowError("Q2_SOURCE_CHANGED")
        observation = WorkflowStore._decode_extraction(row)
        if (
            observation.record_hash != saved.observation_hash
            or observation.payload_bytes() != saved.observation.payload_bytes()
        ):
            raise WorkflowError("Q2_SOURCE_CHANGED")
        WorkflowStore._extraction_source(connection, observation)

    def load_q2(
        self,
        *,
        project: str,
        branch: str,
        run_id: str,
        step_id: str,
        observation_hash: str,
        method_policy_hash: str,
    ) -> Q2Run:
        _identity(project, branch, run_id)
        for value in (step_id, observation_hash, method_policy_hash):
            _scene_hash(value)
        with self._connection() as connection:
            self._scene_parent(connection, project, branch, run_id)
            if not self._q2_table(connection, create=False):
                raise WorkflowError("Q2_EXECUTION_UNAVAILABLE")
            row = connection.execute(
                "SELECT * FROM q2_executions WHERE run_id=? AND step_id=? AND observation_hash=? AND method_policy_hash=?",
                (run_id, step_id, observation_hash, method_policy_hash),
            ).fetchone()
            if row is None:
                # A retained corrupt identity must never trigger a fresh run.
                # Valid other method versions remain immutable history.
                for previous in connection.execute("SELECT * FROM q2_executions"):
                    self._decode_q2(previous)
                raise WorkflowError("Q2_EXECUTION_UNAVAILABLE")
            if (row["project"], row["branch"]) != (project, branch):
                raise WorkflowError("CORRUPT_Q2_EXECUTION")
            saved = self._decode_q2(row)
            self._q2_source(connection, saved)
            return saved

    def create_q2(self, result: Q2Run) -> bool:
        from anovel.quality.q2 import Q2Error, Q2Run, require_local_execution_q2

        try:
            require_local_execution_q2(result)
        except Q2Error as error:
            raise WorkflowError(str(error)) from None
        raw = result.payload_bytes()
        saved = Q2Run.from_bytes(raw)
        value_hash = hashlib.sha256(raw).hexdigest()
        if saved.record_hash != result.record_hash:
            raise WorkflowError("CORRUPT_Q2_EXECUTION")
        with self._transaction() as connection:
            self._q2_source(connection, saved)
            self._q2_table(connection, create=True)
            row = connection.execute(
                "SELECT * FROM q2_executions WHERE run_id=? AND step_id=? AND observation_hash=? AND method_policy_hash=?",
                (
                    saved.run_id,
                    saved.step_id,
                    saved.observation_hash,
                    saved.method_policy_hash,
                ),
            ).fetchone()
            if row is not None:
                existing = self._decode_q2(row)
                if existing.payload_bytes() != raw:
                    raise WorkflowError("Q2_EXECUTION_CONFLICT")
                return False
            for previous in connection.execute("SELECT * FROM q2_executions"):
                self._decode_q2(previous)
            connection.execute(
                "INSERT INTO q2_executions VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    saved.run_id,
                    saved.step_id,
                    saved.observation_hash,
                    saved.method_policy_hash,
                    saved.assembly_hash,
                    saved.project,
                    saved.branch,
                    raw,
                    value_hash,
                ),
            )
            return True

    @staticmethod
    def _q3_table(connection: sqlite3.Connection, *, create: bool) -> bool:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='q3_executions'"
        ).fetchone()
        if exists is None:
            if not create:
                return False
            connection.execute(_Q3_SCHEMA)
        columns = connection.execute("PRAGMA table_info(q3_executions)").fetchall()
        if (
            [row["name"] for row in columns]
            != [
                "run_id",
                "step_id",
                "observation_hash",
                "method_policy_hash",
                "assembly_hash",
                "project",
                "branch",
                "payload",
                "payload_hash",
            ]
            or [row["type"].upper() for row in columns]
            != ["TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "TEXT", "BLOB", "TEXT"]
            or [row["pk"] for row in columns] != [1, 2, 3, 4, 0, 0, 0, 0, 0]
            or any(
                row["notnull"] != 1 or row["dflt_value"] is not None for row in columns
            )
        ):
            raise WorkflowError("INVALID_Q3_SCHEMA")
        foreign = connection.execute(
            "PRAGMA foreign_key_list(q3_executions)"
        ).fetchall()
        if (
            len(foreign) != 3
            or len({row["id"] for row in foreign}) != 1
            or {row["seq"] for row in foreign} != {0, 1, 2}
            or any(
                (row["on_update"], row["on_delete"], row["match"])
                != ("NO ACTION", "NO ACTION", "NONE")
                for row in foreign
            )
            or {(row["table"], row["from"], row["to"]) for row in foreign}
            != {
                ("extraction_observations", "run_id", "run_id"),
                ("extraction_observations", "step_id", "step_id"),
                ("extraction_observations", "assembly_hash", "assembly_hash"),
            }
        ):
            raise WorkflowError("INVALID_Q3_SCHEMA")
        if (
            connection.execute("PRAGMA foreign_key_check(q3_executions)").fetchone()
            is not None
        ):
            raise WorkflowError("CORRUPT_Q3_EXECUTION")
        return True

    @staticmethod
    def _decode_q3(row: sqlite3.Row) -> Q3Run:
        from anovel.quality.q3 import Q3Run

        try:
            raw = row["payload"]
            if (
                type(raw) is not bytes
                or hashlib.sha256(raw).hexdigest() != row["payload_hash"]
            ):
                raise ValueError
            saved = _decode_retained_payload(raw, Q3Run.from_bytes)
            if (
                saved.project,
                saved.branch,
                saved.run_id,
                saved.step_id,
                saved.observation_hash,
                saved.method_policy_hash,
                saved.assembly_hash,
            ) != (
                row["project"],
                row["branch"],
                row["run_id"],
                row["step_id"],
                row["observation_hash"],
                row["method_policy_hash"],
                row["assembly_hash"],
            ):
                raise ValueError
            return saved
        except (TypeError, ValueError, KeyError, IndexError, RecursionError):
            raise WorkflowError("CORRUPT_Q3_EXECUTION") from None

    @staticmethod
    def _q3_source(connection: sqlite3.Connection, saved: Q3Run) -> None:
        if not WorkflowStore._extraction_table(connection, create=False):
            raise WorkflowError("Q3_SOURCE_CHANGED")
        row = connection.execute(
            "SELECT * FROM extraction_observations WHERE run_id=? AND step_id=? AND assembly_hash=?",
            (saved.run_id, saved.step_id, saved.assembly_hash),
        ).fetchone()
        if row is None:
            raise WorkflowError("Q3_SOURCE_CHANGED")
        observation = WorkflowStore._decode_extraction(row)
        if (
            observation.record_hash != saved.observation_hash
            or observation.payload_bytes() != saved.observation.payload_bytes()
        ):
            raise WorkflowError("Q3_SOURCE_CHANGED")
        WorkflowStore._extraction_source(connection, observation)

    def load_q3(
        self,
        *,
        project: str,
        branch: str,
        run_id: str,
        step_id: str,
        observation_hash: str,
        method_policy_hash: str,
    ) -> Q3Run:
        _identity(project, branch, run_id)
        for value in (step_id, observation_hash, method_policy_hash):
            _scene_hash(value)
        with self._connection() as connection:
            self._scene_parent(connection, project, branch, run_id)
            if not self._q3_table(connection, create=False):
                raise WorkflowError("Q3_EXECUTION_UNAVAILABLE")
            for retained in connection.execute("SELECT * FROM q3_executions"):
                self._decode_q3(retained)
            row = connection.execute(
                "SELECT * FROM q3_executions WHERE run_id=? AND step_id=? AND observation_hash=? AND method_policy_hash=?",
                (run_id, step_id, observation_hash, method_policy_hash),
            ).fetchone()
            if row is None:
                # All retained identities were audited before this lookup.
                raise WorkflowError("Q3_EXECUTION_UNAVAILABLE")
            if (row["project"], row["branch"]) != (project, branch):
                raise WorkflowError("CORRUPT_Q3_EXECUTION")
            saved = self._decode_q3(row)
            self._q3_source(connection, saved)
            return saved

    def create_q3(self, result: Q3Run) -> bool:
        from anovel.quality.q3 import Q3Error, Q3Run, require_local_execution_q3

        try:
            require_local_execution_q3(result)
        except Q3Error as error:
            raise WorkflowError(str(error)) from None
        raw = result.payload_bytes()
        saved = Q3Run.from_bytes(raw)
        value_hash = hashlib.sha256(raw).hexdigest()
        if saved.record_hash != result.record_hash:
            raise WorkflowError("CORRUPT_Q3_EXECUTION")
        with self._transaction() as connection:
            self._q3_source(connection, saved)
            self._q3_table(connection, create=True)
            for retained in connection.execute("SELECT * FROM q3_executions"):
                self._decode_q3(retained)
            row = connection.execute(
                "SELECT * FROM q3_executions WHERE run_id=? AND step_id=? AND observation_hash=? AND method_policy_hash=?",
                (
                    saved.run_id,
                    saved.step_id,
                    saved.observation_hash,
                    saved.method_policy_hash,
                ),
            ).fetchone()
            if row is not None:
                existing = self._decode_q3(row)
                if existing.payload_bytes() != raw:
                    raise WorkflowError("Q3_EXECUTION_CONFLICT")
                return False
            connection.execute(
                "INSERT INTO q3_executions VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    saved.run_id,
                    saved.step_id,
                    saved.observation_hash,
                    saved.method_policy_hash,
                    saved.assembly_hash,
                    saved.project,
                    saved.branch,
                    raw,
                    value_hash,
                ),
            )
            return True
