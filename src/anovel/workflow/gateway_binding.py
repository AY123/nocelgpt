"""Read-only existing Gateway bindings, before any recovery can change its state."""

from __future__ import annotations

import os
import sqlite3
import stat
import unicodedata
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from anovel.canon.identity import decode_canonical
from anovel.gateway.models import (
    BudgetLimit,
    GatewayRequest,
    GatewayResult,
    ModelPolicy,
)

from .ledger_pin import SceneLedgerPin
from .models import WorkflowError, WorkflowSnapshot, result_prose
from .store import WorkflowStore

if TYPE_CHECKING:
    from .generation import SceneGenerationSnapshot


def _valid_estimate_fee_table(connection: sqlite3.Connection) -> bool:
    columns = [
        (
            row["name"],
            row["type"].upper(),
            row["notnull"],
            row["dflt_value"],
            row["pk"],
            row["hidden"],
        )
        for row in connection.execute("PRAGMA table_xinfo(estimate_fee_bounds)")
    ]
    foreign_key = sorted(
        tuple(row)
        for row in connection.execute("PRAGMA foreign_key_list(estimate_fee_bounds)")
    )
    return columns == [
        ("run_id", "TEXT", 1, None, 1, 0),
        ("attempt_id", "TEXT", 1, None, 2, 0),
        ("fee_record", "BLOB", 1, None, 0, 0),
    ] and foreign_key == [
        (0, 0, "attempts", "run_id", "run_id", "NO ACTION", "NO ACTION", "NONE"),
        (
            0,
            1,
            "attempts",
            "attempt_id",
            "attempt_id",
            "NO ACTION",
            "NO ACTION",
            "NONE",
        ),
    ]


def _require_gateway_schema(connection: sqlite3.Connection) -> None:
    objects = connection.execute(
        "SELECT name, type FROM sqlite_master "
        "WHERE (type='table' AND name NOT GLOB 'sqlite_*') "
        "OR lower(name)='estimate_fee_bounds'"
    ).fetchall()
    tables = {row["name"] for row in objects if row["type"] == "table"}
    required = {
        "budgets": {"run_id", "limit_record", "blocked", "block_reason"},
        "logical_requests": {
            "run_id",
            "logical_id",
            "semantic_hash",
            "request_record",
            "first_success_attempt",
        },
        "attempts": {
            "run_id",
            "attempt_id",
            "logical_id",
            "request_record",
            "policy_record",
            "state",
            "result_record",
        },
    }
    base_tables = set(required)
    current_tables = base_tables | {"estimate_fee_bounds"}
    if len(objects) != len(tables) or tables not in (base_tables, current_tables):
        raise WorkflowError("INVALID_GATEWAY_LEDGER")
    if tables == current_tables and not _valid_estimate_fee_table(connection):
        raise WorkflowError("INVALID_GATEWAY_LEDGER")
    for name, columns in required.items():
        # Names come only from the constants above, never a task/CLI value.
        actual = {
            row["name"] for row in connection.execute("PRAGMA table_info(" + name + ")")
        }
        if not columns <= actual:
            raise WorkflowError("INVALID_GATEWAY_LEDGER")


def _gateway_ledger_path(path: Path, store: WorkflowStore) -> Path:
    info = path.lstat()
    candidate = path.resolve(strict=True)
    database = store.path.resolve()
    identity = unicodedata.normalize("NFC", str(candidate)).casefold()
    reserved = {
        unicodedata.normalize(
            "NFC", str(database.with_name(database.name + s))
        ).casefold()
        for s in ("", "-wal", "-shm", "-journal")
    }
    lock = unicodedata.normalize("NFC", str(store.lock_directory.resolve())).casefold()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_uid != os.getuid()
        or identity in reserved
        or identity == lock
        or identity.startswith(lock + os.sep)
        or os.path.samefile(candidate, database)
    ):
        raise WorkflowError("INVALID_GATEWAY_LEDGER")
    return candidate


def _gateway_limit(
    connection: sqlite3.Connection, saved: WorkflowSnapshot
) -> BudgetLimit:
    row = connection.execute(
        "SELECT limit_record FROM budgets WHERE run_id=?", (saved.run_id,)
    ).fetchone()
    if row is None:
        raise WorkflowError("GATEWAY_LEDGER_RUN_UNAVAILABLE")
    budget = BudgetLimit.from_dict(decode_canonical(row["limit_record"]))
    if (budget.project, budget.branch, budget.run_id) != (
        saved.project,
        saved.branch,
        saved.run_id,
    ):
        raise WorkflowError("GATEWAY_SCOPE_MISMATCH")
    return budget


def existing_gateway_ledger(
    path: Path, store: WorkflowStore, saved: WorkflowSnapshot
) -> Path:
    """Validate the existing ledger read only before its writable constructor.

    In particular, a mistaken --gateway-ledger must never initialize tables or
    change journal mode in a Draft store or an unrelated SQLite database.
    """
    connection: sqlite3.Connection | None = None
    try:
        candidate = _gateway_ledger_path(path, store)
        connection = sqlite3.connect(candidate.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        _require_gateway_schema(connection)
        _gateway_limit(connection, saved)
        attempt = connection.execute(
            "SELECT logical_id,request_record,policy_record FROM attempts WHERE run_id=? AND attempt_id=?",
            (saved.run_id, saved.attempt_id),
        ).fetchone()
        if attempt is not None:
            policy = next(p for p in saved.request.policies if p.id == saved.policy_id)
            if (
                attempt["logical_id"] != saved.request.logical_id
                or attempt["request_record"] != saved.request_bytes
                or attempt["policy_record"] != policy.to_bytes()
            ):
                raise WorkflowError("GATEWAY_REQUEST_BINDING_MISMATCH")
        return candidate
    except WorkflowError:
        raise
    except (OSError, ValueError, sqlite3.Error, RuntimeError):
        raise WorkflowError("INVALID_GATEWAY_LEDGER") from None
    finally:
        if connection is not None:
            connection.close()


def _scene_file_identity(path: Path) -> tuple[Path, int, int]:
    """Observe a regular, owned single-link file without accepting leaf links."""
    if not isinstance(path, Path):
        raise WorkflowError("INVALID_SCENE_LEDGER")
    info = path.lstat()
    resolved = path.resolve(strict=True)
    actual = resolved.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_nlink != 1
        or not stat.S_ISREG(actual.st_mode)
        or actual.st_uid != os.getuid()
        or actual.st_nlink != 1
        or (info.st_dev, info.st_ino) != (actual.st_dev, actual.st_ino)
    ):
        raise WorkflowError("INVALID_SCENE_LEDGER")
    return resolved, info.st_dev, info.st_ino


def _private_writer_ledger_files(
    path: Path,
    provider: str,
) -> tuple[tuple[int, int], dict[str, tuple[int, int]]]:
    """Inspect a private ledger and its SQLite sidecars without opening them."""
    try:
        if (
            not isinstance(path, Path)
            or not path.is_absolute()
            or path.name in {"", "..", ":memory:"}
            or path.parent != path.parent.resolve(strict=True)
        ):
            raise ValueError
        directory = path.parent.lstat()
        if (
            not stat.S_ISDIR(directory.st_mode)
            or stat.S_IMODE(directory.st_mode) != 0o700
            or directory.st_uid != os.getuid()
        ):
            raise ValueError
        files: dict[str, tuple[int, int]] = {}
        for suffix in ("", "-wal", "-shm", "-journal"):
            try:
                info = path.with_name(path.name + suffix).lstat()
            except FileNotFoundError:
                continue
            if (
                not stat.S_ISREG(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_uid != os.getuid()
                or info.st_nlink != 1
            ):
                raise ValueError
            files[suffix] = (info.st_dev, info.st_ino)
        if files and "" not in files:
            raise ValueError
        return (directory.st_dev, directory.st_ino), files
    except (OSError, ValueError, RuntimeError):
        raise WorkflowError(f"INVALID_{provider}_DRAFT_LEDGER") from None


def require_private_writer_ledger_path(path: Path, provider: str) -> None:
    """Require an owned private directory and private ledger files if present."""
    _private_writer_ledger_files(path, provider)


def require_private_kimi_writer_ledger_path(path: Path) -> None:
    require_private_writer_ledger_path(path, "KIMI")


def _writer_attempt(
    connection: sqlite3.Connection,
    request: GatewayRequest,
    attempt_id: str,
    provider: str,
) -> GatewayResult | None:
    policy = request.policies[0]
    scope = (request.project, request.branch, request.run_id)
    budget_row = connection.execute(
        "SELECT limit_record FROM budgets WHERE run_id=?", (request.run_id,)
    ).fetchone()
    if budget_row is None:
        if connection.execute("SELECT 1 FROM budgets LIMIT 1").fetchone() is not None:
            raise WorkflowError(f"{provider}_DRAFT_RECEIPT_MISMATCH")
    else:
        limit = BudgetLimit.from_dict(decode_canonical(budget_row["limit_record"]))
        if (limit.project, limit.branch, limit.run_id) != scope:
            raise WorkflowError(f"{provider}_DRAFT_RECEIPT_MISMATCH")
    logical = connection.execute(
        "SELECT semantic_hash,request_record,first_success_attempt FROM logical_requests "
        "WHERE run_id=? AND logical_id=?",
        (request.run_id, request.logical_id),
    ).fetchone()
    attempts = connection.execute(
        "SELECT attempt_id,logical_id,request_record,policy_record,state,result_record "
        "FROM attempts WHERE run_id=? AND (attempt_id=? OR logical_id=?) LIMIT 2",
        (request.run_id, attempt_id, request.logical_id),
    ).fetchall()
    if not attempts and logical is None:
        return None
    if budget_row is None or logical is None or len(attempts) != 1:
        raise WorkflowError(f"{provider}_DRAFT_RECEIPT_MISMATCH")
    row = attempts[0]
    request_bytes = request.to_bytes()
    if (
        logical["semantic_hash"] != request.semantic_hash
        or logical["request_record"] != request_bytes
        or row["attempt_id"] != attempt_id
        or row["logical_id"] != request.logical_id
        or row["request_record"] != request_bytes
        or row["policy_record"] != policy.to_bytes()
    ):
        raise WorkflowError(f"{provider}_DRAFT_RECEIPT_MISMATCH")
    if row["state"] != "FINISHED":
        raise WorkflowError(f"{provider}_DRAFT_ATTEMPT_NOT_COMPLETE")
    result = GatewayResult.from_dict(decode_canonical(row["result_record"]))
    if (
        result.to_bytes() != row["result_record"]
        or (result.project, result.branch, result.run_id) != scope
        or result.logical_id != request.logical_id
        or result.attempt_id != attempt_id
        or result.request_hash != request.semantic_hash
        or result.policy_hash != policy.content_hash
        or result.replayed
        or logical["first_success_attempt"]
        != (attempt_id if result.status == "SUCCESS" else None)
    ):
        raise WorkflowError(f"{provider}_DRAFT_RECEIPT_MISMATCH")
    return result


def read_provider_writer_receipt(
    path: Path, request: GatewayRequest, attempt_id: str, provider: str
) -> GatewayResult | None:
    """Read the exact attempt receipt, without initializing or recovering a ledger."""
    if (
        type(request) is not GatewayRequest
        or len(request.policies) != 1
        or request.policies[0].is_kimi != (provider == "KIMI")
        or type(attempt_id) is not str
        or not attempt_id.strip()
    ):
        raise WorkflowError(f"{provider}_DRAFT_RECEIPT_MISMATCH")
    identity = _private_writer_ledger_files(path, provider)
    _, files = identity
    if not files:
        return None
    if ("-wal" in files) != ("-shm" in files) or "-journal" in files:
        raise WorkflowError(f"{provider}_DRAFT_ATTEMPT_NOT_COMPLETE")
    # A checkpointed ledger can be read without letting SQLite create a WAL or
    # shared-memory file. With a WAL present both required sidecars must exist.
    query = "?mode=ro" if "-wal" in files else "?mode=ro&immutable=1"
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(path.as_uri() + query, uri=True)
        connection.row_factory = sqlite3.Row
        if _private_writer_ledger_files(path, provider) != identity:
            raise WorkflowError(f"INVALID_{provider}_DRAFT_LEDGER")
        connection.execute("BEGIN")
        _require_gateway_schema(connection)
        result = _writer_attempt(connection, request, attempt_id, provider)
        if _private_writer_ledger_files(path, provider) != identity:
            raise WorkflowError(f"INVALID_{provider}_DRAFT_LEDGER")
        return result
    except WorkflowError as error:
        if str(error) == "INVALID_GATEWAY_LEDGER":
            raise WorkflowError(f"INVALID_{provider}_DRAFT_LEDGER") from None
        raise
    except (OSError, TypeError, ValueError, sqlite3.Error, RuntimeError):
        raise WorkflowError(f"INVALID_{provider}_DRAFT_LEDGER") from None
    finally:
        if connection is not None:
            connection.close()


def read_kimi_writer_receipt(
    path: Path, request: GatewayRequest, attempt_id: str
) -> GatewayResult | None:
    return read_provider_writer_receipt(path, request, attempt_id, "KIMI")


def _parent_result_bytes(result: GatewayResult) -> bytes:
    # A replay is an observation of the same original result, not a new receipt.
    return replace(result, replayed=False).to_bytes()


def _checkpoint_attempt_result(
    connection: sqlite3.Connection,
    checkpoint: WorkflowSnapshot | SceneGenerationSnapshot,
) -> GatewayResult | None:
    request = checkpoint.request
    policy = next(p for p in request.policies if p.id == checkpoint.policy_id)
    row = connection.execute(
        "SELECT logical_id,request_record,policy_record,state,result_record "
        "FROM attempts WHERE run_id=? AND attempt_id=?",
        (checkpoint.run_id, checkpoint.attempt_id),
    ).fetchone()
    if row is None:
        return None
    if (
        row["logical_id"] != request.logical_id
        or row["request_record"] != checkpoint.request_bytes
        or row["policy_record"] != policy.to_bytes()
    ):
        raise WorkflowError("GATEWAY_REQUEST_BINDING_MISMATCH")
    raw = row["result_record"]
    if raw is None and row["state"] in {"PREPARED", "DISPATCHED", "CANCELLED"}:
        return None
    if row["state"] != "FINISHED" or type(raw) is not bytes:
        raise WorkflowError("RECOVERY_LEDGER_RESULT_INVALID")
    result = GatewayResult.from_dict(decode_canonical(raw))
    if (
        result.to_bytes() != raw
        or result.replayed
        or (
            result.project,
            result.branch,
            result.run_id,
            result.logical_id,
            result.attempt_id,
            result.request_hash,
            result.policy_hash,
        )
        != (
            request.project,
            request.branch,
            request.run_id,
            request.logical_id,
            checkpoint.attempt_id,
            request.content_hash,
            policy.content_hash,
        )
    ):
        raise WorkflowError("RECOVERY_LEDGER_RESULT_MISMATCH")
    return result


def _checkpoint_sidecars(path: Path) -> dict[str, tuple[Path, int, int]]:
    files = {}
    for suffix in ("-wal", "-shm", "-journal"):
        try:
            files[suffix] = _scene_file_identity(path.with_name(path.name + suffix))
        except FileNotFoundError:
            continue
    if files.keys() not in (set(), {"-wal", "-shm"}):
        raise WorkflowError("RECOVERY_LEDGER_NOT_STABLE")
    return files


def read_checkpoint_attempt(
    path: Path,
    store: WorkflowStore,
    source: WorkflowSnapshot,
    child: SceneGenerationSnapshot | None = None,
) -> GatewayResult | None:
    """Read only the exact attempt; never create a ledger or recover a dispatch."""
    connection: sqlite3.Connection | None = None
    try:
        candidate = _gateway_ledger_path(path, store)
        identity = _scene_file_identity(path)
        if identity[0] != candidate:
            raise WorkflowError("RECOVERY_LEDGER_NOT_STABLE")
        info = candidate.stat()
        sidecars = _checkpoint_sidecars(candidate)
        if child is not None and identity != (
            Path(child.ledger_pin.path),
            child.ledger_pin.device,
            child.ledger_pin.inode,
        ):
            raise WorkflowError("SCENE_LEDGER_PIN_CHANGED")

        query = "?mode=ro" if sidecars else "?mode=ro&immutable=1"
        connection = sqlite3.connect(candidate.as_uri() + query, uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN")
        _require_gateway_schema(connection)
        limit = _gateway_limit(connection, source)
        if child is None:
            result = _checkpoint_attempt_result(connection, source)
        else:
            parent = _checkpoint_attempt_result(connection, source)
            if parent is None or source.result is None:
                raise WorkflowError("SCENE_PARENT_RECEIPT_UNAVAILABLE")
            normalized = _parent_result_bytes(parent)
            if normalized != _parent_result_bytes(source.result):
                raise WorkflowError("SCENE_PARENT_RECEIPT_MISMATCH")
            if (
                limit.to_bytes() != child.ledger_pin.limit_bytes
                or sha256(normalized).hexdigest() != child.ledger_pin.parent_result_hash
            ):
                raise WorkflowError("SCENE_LEDGER_PIN_CHANGED")
            result = _checkpoint_attempt_result(connection, child)
        actual = candidate.stat()
        if (
            _scene_file_identity(path) != identity
            or _checkpoint_sidecars(candidate) != sidecars
            or (actual.st_mtime_ns, actual.st_size) != (info.st_mtime_ns, info.st_size)
        ):
            raise WorkflowError("RECOVERY_LEDGER_NOT_STABLE")
        return result
    except WorkflowError:
        raise
    except (OSError, ValueError, TypeError, sqlite3.Error, RuntimeError, StopIteration):
        raise WorkflowError("INVALID_GATEWAY_LEDGER") from None
    finally:
        if connection is not None:
            connection.close()


def _child_policy(
    source: WorkflowSnapshot,
    request: GatewayRequest | None,
    attempt_id: str | None,
    policy_id: str | None,
) -> ModelPolicy | None:
    if request is None and attempt_id is None and policy_id is None:
        return None
    if (
        type(request) is not GatewayRequest
        or type(attempt_id) is not str
        or not attempt_id.strip()
        or type(policy_id) is not str
        or not policy_id.strip()
        or attempt_id == source.attempt_id
        or request.logical_id == source.request.logical_id
        or (request.project, request.branch, request.run_id)
        != (source.project, source.branch, source.run_id)
    ):
        raise WorkflowError("INVALID_SCENE_GATEWAY_REQUEST")
    policy = next((p for p in request.policies if p.id == policy_id), None)
    if policy is None or not any(
        p.to_bytes() == policy.to_bytes() for p in source.request.policies
    ):
        raise WorkflowError("SCENE_GATEWAY_POLICY_NOT_FROZEN")
    return policy


def _scene_ledger_binding(
    path: Path,
    store: WorkflowStore,
    source: WorkflowSnapshot,
    pin: SceneLedgerPin | None = None,
    *,
    request: GatewayRequest | None = None,
    attempt_id: str | None = None,
    policy_id: str | None = None,
) -> tuple[Path, int, int, bytes, str]:
    connection: sqlite3.Connection | None = None
    try:
        if (
            type(source) is not WorkflowSnapshot
            or source.state != "DRAFT_SAVED"
            or source.result is None
            or (pin is not None and type(pin) is not SceneLedgerPin)
        ):
            raise WorkflowError("SCENE_SOURCE_DRAFT_REQUIRED")
        policy = _child_policy(source, request, attempt_id, policy_id)
        identity = _scene_file_identity(path)
        candidate, device, inode = identity
        if pin is not None and (
            (str(candidate), device, inode) != (pin.path, pin.device, pin.inode)
            or (pin.limit.project, pin.limit.branch, pin.limit.run_id)
            != (source.project, source.branch, source.run_id)
        ):
            raise WorkflowError("SCENE_LEDGER_PIN_CHANGED")

        # Preserve the legacy recovery helper's semantics. This scene path adds
        # stronger parent-receipt requirements without changing old callers.
        if existing_gateway_ledger(path, store, source) != candidate:
            raise WorkflowError("SCENE_LEDGER_FILE_CHANGED")
        if _scene_file_identity(path) != identity:
            raise WorkflowError("SCENE_LEDGER_FILE_CHANGED")
        connection = sqlite3.connect(candidate.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        if _scene_file_identity(path) != identity:
            raise WorkflowError("SCENE_LEDGER_FILE_CHANGED")
        connection.execute("BEGIN")
        row = connection.execute(
            "SELECT limit_record FROM budgets WHERE run_id=?", (source.run_id,)
        ).fetchone()
        if row is None or type(row["limit_record"]) is not bytes:
            raise WorkflowError("SCENE_LEDGER_RUN_UNAVAILABLE")
        limit_bytes: bytes = row["limit_record"]
        limit = BudgetLimit.from_dict(decode_canonical(limit_bytes))
        if limit.to_bytes() != limit_bytes or (
            limit.project,
            limit.branch,
            limit.run_id,
        ) != (source.project, source.branch, source.run_id):
            raise WorkflowError("SCENE_LEDGER_BUDGET_MISMATCH")

        parent = connection.execute(
            "SELECT logical_id,request_record,policy_record,state,result_record "
            "FROM attempts WHERE run_id=? AND attempt_id=?",
            (source.run_id, source.attempt_id),
        ).fetchone()
        parent_policy = next(
            p for p in source.request.policies if p.id == source.policy_id
        )
        if (
            parent is None
            or parent["logical_id"] != source.request.logical_id
            or parent["request_record"] != source.request_bytes
            or parent["policy_record"] != parent_policy.to_bytes()
            or parent["state"] != "FINISHED"
            or type(parent["result_record"]) is not bytes
        ):
            raise WorkflowError("SCENE_PARENT_RECEIPT_UNAVAILABLE")
        result = GatewayResult.from_dict(decode_canonical(parent["result_record"]))
        normalized = _parent_result_bytes(result)
        if normalized != _parent_result_bytes(source.result):
            raise WorkflowError("SCENE_PARENT_RECEIPT_MISMATCH")
        result_hash = sha256(normalized).hexdigest()
        if pin is not None and (
            limit_bytes != pin.limit_bytes or result_hash != pin.parent_result_hash
        ):
            raise WorkflowError("SCENE_LEDGER_PIN_CHANGED")

        if request is not None and policy is not None:
            child = connection.execute(
                "SELECT logical_id,request_record,policy_record FROM attempts "
                "WHERE run_id=? AND attempt_id=?",
                (source.run_id, attempt_id),
            ).fetchone()
            # Absence is not dispatch/retry permission. The service may retain
            # BLOCKED; it must never recover the parent's existing attempt.
            if child is not None and (
                child["logical_id"] != request.logical_id
                or child["request_record"] != request.to_bytes()
                or child["policy_record"] != policy.to_bytes()
            ):
                raise WorkflowError("SCENE_GATEWAY_REQUEST_BINDING_MISMATCH")
        if _scene_file_identity(path) != identity:
            raise WorkflowError("SCENE_LEDGER_FILE_CHANGED")
    except WorkflowError:
        raise
    except (OSError, ValueError, TypeError, sqlite3.Error, RuntimeError, StopIteration):
        raise WorkflowError("INVALID_SCENE_LEDGER") from None
    finally:
        if connection is not None:
            connection.close()
    try:
        if _scene_file_identity(path) != identity:
            raise WorkflowError("SCENE_LEDGER_FILE_CHANGED")
    except (OSError, ValueError, RuntimeError):
        raise WorkflowError("SCENE_LEDGER_FILE_CHANGED") from None
    return candidate, device, inode, limit_bytes, result_hash


def freeze_scene_ledger(
    path: Path, store: WorkflowStore, source: WorkflowSnapshot
) -> SceneLedgerPin:
    """Pin the supplied matching ledger and current limit without provisioning.

    Legacy source snapshots did not record an initial ledger pin. This first
    binding cannot certify which matching ledger was historically unique.
    """
    candidate, device, inode, limit, parent_hash = _scene_ledger_binding(
        path, store, source
    )
    return SceneLedgerPin(str(candidate), device, inode, limit, parent_hash)


def verify_scene_ledger(
    path: Path,
    store: WorkflowStore,
    source: WorkflowSnapshot,
    pin: SceneLedgerPin,
    *,
    request: GatewayRequest | None = None,
    attempt_id: str | None = None,
    policy_id: str | None = None,
) -> None:
    """Recheck physical identity, budget and exact parent/optional child records."""
    if type(pin) is not SceneLedgerPin:
        raise WorkflowError("INVALID_SCENE_LEDGER_PIN")
    _scene_ledger_binding(
        path,
        store,
        source,
        pin,
        request=request,
        attempt_id=attempt_id,
        policy_id=policy_id,
    )


def verify_scene_receipt(
    path: Path, store: WorkflowStore, child: SceneGenerationSnapshot
) -> None:
    """Read an actual completed child receipt; never initialize or recover it.

    A self-consistent copied Draft is insufficient: its entire normalized
    result and prose must match the result in the physically pinned ledger.
    """
    from .generation import SceneGenerationSnapshot

    connection: sqlite3.Connection | None = None
    try:
        if (
            type(child) is not SceneGenerationSnapshot
            or child.state != "DRAFT_SAVED"
            or child.result is None
            or child.prose is None
        ):
            raise WorkflowError("SCENE_RECEIPT_UNAVAILABLE")
        identity = _scene_file_identity(path)
        verify_scene_ledger(
            path,
            store,
            child.source,
            child.ledger_pin,
            request=child.request,
            attempt_id=child.attempt_id,
            policy_id=child.policy_id,
        )
        if _scene_file_identity(path) != identity:
            raise WorkflowError("SCENE_LEDGER_FILE_CHANGED")
        candidate = identity[0]
        connection = sqlite3.connect(candidate.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        if _scene_file_identity(path) != identity:
            raise WorkflowError("SCENE_LEDGER_FILE_CHANGED")
        connection.execute("BEGIN")
        row = connection.execute(
            "SELECT logical_id,request_record,policy_record,state,result_record "
            "FROM attempts WHERE run_id=? AND attempt_id=?",
            (child.run_id, child.attempt_id),
        ).fetchone()
        if (
            row is None
            or row["state"] != "FINISHED"
            or type(row["result_record"]) is not bytes
        ):
            raise WorkflowError("SCENE_RECEIPT_UNAVAILABLE")
        policy = next(p for p in child.request.policies if p.id == child.policy_id)
        if (
            row["logical_id"] != child.request.logical_id
            or row["request_record"] != child.request_bytes
            or row["policy_record"] != policy.to_bytes()
        ):
            raise WorkflowError("SCENE_GATEWAY_REQUEST_BINDING_MISMATCH")
        result = GatewayResult.from_dict(decode_canonical(row["result_record"]))
        if (
            result.to_bytes() != row["result_record"]
            or _parent_result_bytes(result) != _parent_result_bytes(child.result)
            or result_prose(child.request, result) != child.prose
        ):
            raise WorkflowError("SCENE_RECEIPT_MISMATCH")
        budget = connection.execute(
            "SELECT limit_record FROM budgets WHERE run_id=?", (child.run_id,)
        ).fetchone()
        if budget is None or budget["limit_record"] != child.ledger_pin.limit_bytes:
            raise WorkflowError("SCENE_LEDGER_PIN_CHANGED")
        if _scene_file_identity(path) != identity:
            raise WorkflowError("SCENE_LEDGER_FILE_CHANGED")
    except WorkflowError:
        raise
    except (OSError, ValueError, TypeError, sqlite3.Error, RuntimeError, StopIteration):
        raise WorkflowError("INVALID_SCENE_RECEIPT") from None
    finally:
        if connection is not None:
            connection.close()
    try:
        if _scene_file_identity(path) != identity:
            raise WorkflowError("SCENE_LEDGER_FILE_CHANGED")
    except (OSError, ValueError, RuntimeError):
        raise WorkflowError("SCENE_LEDGER_FILE_CHANGED") from None
