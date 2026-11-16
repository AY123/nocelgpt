"""Durable request admission and mutually exclusive cost responsibilities.

SQLite transactions never contain network I/O. A prepared reservation is not
released by time alone, and dispatch is a one-way, atomic send claim. This file
stores Gateway records only; it has no credential or Canon write interface.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Never, SupportsIndex

from anovel.canon.identity import canonical_bytes, decode_canonical

from .models import (
    BudgetBlocked,
    BudgetLimit,
    GatewayError,
    GatewayRequest,
    GatewayResult,
    IdentityConflict,
    ModelPolicy,
    ProviderReply,
    RetryDecision,
    UnknownRetryRequired,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS budgets (
    run_id TEXT PRIMARY KEY,
    limit_record BLOB NOT NULL,
    blocked INTEGER NOT NULL DEFAULT 0,
    block_reason TEXT
);
CREATE TABLE IF NOT EXISTS logical_requests (
    run_id TEXT NOT NULL REFERENCES budgets(run_id),
    logical_id TEXT NOT NULL,
    semantic_hash TEXT NOT NULL,
    request_record BLOB NOT NULL,
    first_success_attempt TEXT,
    PRIMARY KEY (run_id, logical_id)
);
CREATE TABLE IF NOT EXISTS attempts (
    run_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    logical_id TEXT NOT NULL,
    request_record BLOB NOT NULL,
    policy_record BLOB NOT NULL,
    retry_record BLOB,
    state TEXT NOT NULL CHECK(state IN
        ('PREPARED', 'DISPATCHED', 'FINISHED', 'CANCELLED')),
    started_at TEXT NOT NULL,
    dispatched_at TEXT,
    finished_at TEXT,
    reserved_microusd TEXT NOT NULL,
    liability_microusd TEXT NOT NULL,
    reply_record BLOB,
    result_record BLOB,
    reconciliation_record BLOB,
    cancel_reason TEXT,
    PRIMARY KEY (run_id, attempt_id),
    FOREIGN KEY (run_id, logical_id)
        REFERENCES logical_requests(run_id, logical_id)
);
"""


def _text(value: object, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise GatewayError(f"{name} must be nonempty text")
    return value


def _bytes(value: object) -> bytes:
    if type(value) is not bytes:
        raise GatewayError("corrupt persisted Gateway record")
    return value


def _money(value: object) -> int:
    # Decimal TEXT preserves exact Python integers beyond SQLite's int64 range.
    text = _text(value, "persisted micro-USD")
    if not text.isascii() or not text.isdecimal():
        raise GatewayError("corrupt persisted micro-USD")
    amount = int(text)
    if str(amount) != text:
        raise GatewayError("noncanonical persisted micro-USD")
    return amount


def _now(value: datetime | None) -> datetime:
    instant = datetime.now(UTC) if value is None else value
    if type(instant) is not datetime or instant.tzinfo is None:
        raise GatewayError("ledger time requires an aware datetime")
    if instant.utcoffset() is None:
        raise GatewayError("ledger time requires an aware datetime")
    return instant.astimezone(UTC)


def _stamp(instant: datetime) -> str:
    return instant.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _result(row: sqlite3.Row) -> GatewayResult | None:
    raw = row["result_record"]
    return (
        None if raw is None else GatewayResult.from_dict(decode_canonical(_bytes(raw)))
    )


_DISPATCH_SEAL = object()


class DispatchPermit:
    """An ephemeral single-send capability issued after durable admission.

    The private seal prevents accidental direct construction. This is an
    in-process boundary, not a cryptographic defence against code modification.
    A restarted process cannot reconstruct a permit from a persisted attempt.
    """

    __slots__ = (
        "_attempt_id",
        "_consumed",
        "_deadline_at",
        "_lock",
        "_policy_hash",
        "_request_hash",
        "_run_id",
    )

    def __init__(
        self,
        request_hash: str,
        policy_hash: str,
        run_id: str,
        attempt_id: str,
        deadline_at: str,
        *,
        _seal: object = None,
    ) -> None:
        if _seal is not _DISPATCH_SEAL:
            raise GatewayError("dispatch permit can only be issued by budget admission")
        self._request_hash = request_hash
        self._policy_hash = policy_hash
        self._run_id = run_id
        self._attempt_id = attempt_id
        self._deadline_at = deadline_at
        self._consumed = False
        self._lock = Lock()

    @property
    def request_hash(self) -> str:
        return self._request_hash

    @property
    def policy_hash(self) -> str:
        return self._policy_hash

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def attempt_id(self) -> str:
        return self._attempt_id

    @property
    def deadline_at(self) -> str:
        return self._deadline_at

    def consume(
        self,
        request: GatewayRequest,
        policy: ModelPolicy,
        attempt_id: str,
        *,
        now: datetime | None = None,
    ) -> None:
        """Claim this permit once before any transport operation."""
        if type(request) is not GatewayRequest or type(policy) is not ModelPolicy:
            raise GatewayError("dispatch requires exact frozen request and policy")
        instant = _now(now)
        with self._lock:
            if self._consumed:
                raise IdentityConflict("dispatch permit was already consumed")
            if (
                request.semantic_hash != self.request_hash
                or policy.content_hash != self.policy_hash
                or request.run_id != self.run_id
                or attempt_id != self.attempt_id
            ):
                raise IdentityConflict(
                    "dispatch permit belongs to another request or attempt"
                )
            if instant >= datetime.fromisoformat(self.deadline_at):
                raise BudgetBlocked("dispatch permit passed the frozen run deadline")
            if instant >= datetime.fromisoformat(policy.price_expires_at):
                raise BudgetBlocked("dispatch permit passed the frozen price expiry")
            self._consumed = True

    def __reduce_ex__(self, protocol: SupportsIndex) -> Never:
        raise TypeError("dispatch permits are ephemeral and cannot be serialized")


class BudgetLedger:
    """A dedicated durable file shared by all attempts in a frozen run."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path) or path.name in {"", ":memory:"}:
            raise GatewayError("budget ledger requires a dedicated file path")
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(_SCHEMA)
        except sqlite3.Error as error:
            raise GatewayError("cannot initialize the durable budget ledger") from error
        finally:
            if connection is not None:
                connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except sqlite3.Error as error:
            connection.rollback()
            raise GatewayError("durable budget transaction failed") from error
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _budget(
        connection: sqlite3.Connection, run_id: str
    ) -> tuple[sqlite3.Row, BudgetLimit]:
        _text(run_id, "run ID")
        row: sqlite3.Row | None = connection.execute(
            "SELECT * FROM budgets WHERE run_id=?", (run_id,)
        ).fetchone()
        if row is None:
            raise BudgetBlocked("run has no provisioned budget")
        return row, BudgetLimit.from_dict(decode_canonical(_bytes(row["limit_record"])))

    @staticmethod
    def _attempt(
        connection: sqlite3.Connection, run_id: str, attempt_id: str
    ) -> sqlite3.Row:
        _text(run_id, "run ID")
        _text(attempt_id, "attempt ID")
        row: sqlite3.Row | None = connection.execute(
            "SELECT * FROM attempts WHERE run_id=? AND attempt_id=?",
            (run_id, attempt_id),
        ).fetchone()
        if row is None:
            raise GatewayError("unknown attempt identity")
        return row

    @staticmethod
    def _totals(connection: sqlite3.Connection, run_id: str) -> dict[str, int]:
        totals = {
            "spent_microusd": 0,
            "inflight_microusd": 0,
            "unknown_microusd": 0,
            "attempts": 0,
            "inflight_attempts": 0,
            "unknown_attempts": 0,
        }
        for row in connection.execute(
            "SELECT * FROM attempts WHERE run_id=?", (run_id,)
        ):
            totals["attempts"] += 1
            state = row["state"]
            liability = _money(row["liability_microusd"])
            if state in {"PREPARED", "DISPATCHED"}:
                totals["inflight_microusd"] += liability
                totals["inflight_attempts"] += 1
            elif state == "FINISHED":
                result = _result(row)
                if result is None:
                    raise GatewayError("finished attempt lacks its durable result")
                if result.charge_status == "PENDING":
                    totals["unknown_microusd"] += liability
                    totals["unknown_attempts"] += 1
                else:
                    if result.charge_microusd is None:
                        raise GatewayError("settled attempt lacks its charge")
                    totals["spent_microusd"] += result.charge_microusd
            elif state != "CANCELLED":
                raise GatewayError("unrecognized durable attempt state")
        return totals

    def provision(self, limit: BudgetLimit) -> None:
        if type(limit) is not BudgetLimit:
            raise GatewayError("provision requires an exact BudgetLimit")
        with self._transaction() as connection:
            old = connection.execute(
                "SELECT limit_record FROM budgets WHERE run_id=?", (limit.run_id,)
            ).fetchone()
            if old is not None:
                if _bytes(old["limit_record"]) != limit.to_bytes():
                    raise IdentityConflict("run budget is already frozen differently")
                return
            connection.execute(
                "INSERT INTO budgets(run_id,limit_record) VALUES (?,?)",
                (limit.run_id, limit.to_bytes()),
            )

    def reserve(
        self,
        request: GatewayRequest,
        policy: ModelPolicy,
        attempt_id: str,
        decision: RetryDecision | None = None,
        now: datetime | None = None,
    ) -> GatewayResult | None:
        if type(request) is not GatewayRequest or type(policy) is not ModelPolicy:
            raise GatewayError("reservation requires exact request and model policy")
        if decision is not None and type(decision) is not RetryDecision:
            raise GatewayError("retry needs an exact RetryDecision")
        _text(attempt_id, "attempt ID")
        instant = _now(now)
        if not any(p.to_bytes() == policy.to_bytes() for p in request.policies):
            raise IdentityConflict("model policy is not frozen in the request")
        with self._transaction() as connection:
            budget, limit = self._budget(connection, request.run_id)
            if (limit.project, limit.branch) != (request.project, request.branch):
                raise IdentityConflict("request changed its frozen budget scope")
            logical = connection.execute(
                "SELECT * FROM logical_requests WHERE run_id=? AND logical_id=?",
                (request.run_id, request.logical_id),
            ).fetchone()
            if logical is not None:
                if logical["semantic_hash"] != request.semantic_hash:
                    raise IdentityConflict("logical request changed its frozen input")
                success = logical["first_success_attempt"]
                if success is not None:
                    stored = _result(self._attempt(connection, request.run_id, success))
                    if stored is None or stored.status != "SUCCESS":
                        raise GatewayError("corrupt successful logical request pointer")
                    return replace(stored, replayed=True)
            duplicate = connection.execute(
                "SELECT 1 FROM attempts WHERE run_id=? AND attempt_id=?",
                (request.run_id, attempt_id),
            ).fetchone()
            if duplicate is not None:
                raise IdentityConflict(
                    "attempt identity is already reserved; do not resend"
                )
            prior = list(
                connection.execute(
                    "SELECT * FROM attempts WHERE run_id=? AND logical_id=?",
                    (request.run_id, request.logical_id),
                )
            )
            if prior and decision is None:
                raise UnknownRetryRequired(
                    "another attempt requires an explicit retry decision"
                )
            if any(row["state"] in {"PREPARED", "DISPATCHED"} for row in prior):
                raise BudgetBlocked("logical request already has an active attempt")
            unknown = any(
                (result := _result(row)) is not None
                and result.charge_status == "PENDING"
                for row in prior
            )
            if unknown and (decision is None or not decision.accept_unknown):
                raise UnknownRetryRequired(
                    "retry must explicitly accept unresolved cost"
                )
            if budget["blocked"] != 0:
                raise BudgetBlocked("run is frozen after a cost or model anomaly")
            if instant >= datetime.fromisoformat(limit.deadline_at):
                raise BudgetBlocked("the frozen run deadline has expired")
            if instant >= datetime.fromisoformat(policy.price_expires_at):
                raise BudgetBlocked("the frozen price snapshot has expired")
            totals = self._totals(connection, request.run_id)
            if totals["attempts"] >= limit.max_attempts:
                raise BudgetBlocked("the frozen attempt limit is exhausted")
            if totals["inflight_attempts"] >= limit.max_inflight:
                raise BudgetBlocked("the frozen inflight limit is reached")
            if totals["unknown_attempts"] >= limit.max_unknown:
                raise BudgetBlocked("the frozen unknown liability limit is reached")
            liability = sum(
                totals[name]
                for name in ("spent_microusd", "inflight_microusd", "unknown_microusd")
            )
            if liability + policy.reserve_microusd > limit.total_microusd:
                raise BudgetBlocked(
                    "the original run budget cannot cover this reservation"
                )
            if logical is None:
                connection.execute(
                    "INSERT INTO logical_requests VALUES (?,?,?,?,NULL)",
                    (
                        request.run_id,
                        request.logical_id,
                        request.semantic_hash,
                        request.to_bytes(),
                    ),
                )
            connection.execute(
                """INSERT INTO attempts (
                    run_id,attempt_id,logical_id,request_record,policy_record,
                    retry_record,state,started_at,reserved_microusd,liability_microusd
                ) VALUES (?,?,?,?,?,?,'PREPARED',?,?,?)""",
                (
                    request.run_id,
                    attempt_id,
                    request.logical_id,
                    request.to_bytes(),
                    policy.to_bytes(),
                    None if decision is None else decision.to_bytes(),
                    _stamp(instant),
                    str(policy.reserve_microusd),
                    str(policy.reserve_microusd),
                ),
            )
        return None

    def mark_dispatch(
        self, run_id: str, attempt_id: str, now: datetime | None = None
    ) -> DispatchPermit:
        instant = _now(now)
        with self._transaction() as connection:
            budget, limit = self._budget(connection, run_id)
            row = self._attempt(connection, run_id, attempt_id)
            if row["state"] != "PREPARED":
                raise IdentityConflict("attempt cannot claim dispatch again")
            if budget["blocked"] != 0:
                raise BudgetBlocked("run is frozen after an anomaly")
            policy = ModelPolicy.from_dict(
                decode_canonical(_bytes(row["policy_record"]))
            )
            if instant >= datetime.fromisoformat(limit.deadline_at):
                raise BudgetBlocked("the frozen run deadline has expired")
            if instant >= datetime.fromisoformat(policy.price_expires_at):
                raise BudgetBlocked("the frozen price snapshot has expired")
            connection.execute(
                "UPDATE attempts SET state='DISPATCHED',dispatched_at=? "
                "WHERE run_id=? AND attempt_id=? AND state='PREPARED'",
                (_stamp(instant), run_id, attempt_id),
            )
            permit = DispatchPermit(
                sha256(_bytes(row["request_record"])).hexdigest(),
                policy.content_hash,
                run_id,
                attempt_id,
                limit.deadline_at,
                _seal=_DISPATCH_SEAL,
            )
        # The transaction must commit before the capability reaches transport.
        return permit

    @staticmethod
    def _freeze(connection: sqlite3.Connection, run_id: str, reason: str) -> None:
        connection.execute(
            "UPDATE budgets SET blocked=1,block_reason=COALESCE(block_reason,?) WHERE run_id=?",
            (reason, run_id),
        )

    def _finish(
        self,
        connection: sqlite3.Connection,
        request: GatewayRequest,
        policy: ModelPolicy,
        attempt_id: str,
        reply: ProviderReply,
        instant: datetime,
    ) -> GatewayResult:
        row = self._attempt(connection, request.run_id, attempt_id)
        if (
            _bytes(row["request_record"]) != request.to_bytes()
            or _bytes(row["policy_record"]) != policy.to_bytes()
        ):
            raise IdentityConflict(
                "reply does not belong to the reserved request and policy"
            )
        previous = _result(row)
        if previous is not None:
            if previous.reply.to_bytes() == reply.to_bytes():
                return previous
            recovered = previous.reply
            if not (
                recovered.outcome == "UNKNOWN"
                and recovered.error_code == "INTERRUPTED_AFTER_DISPATCH"
                and recovered.response_body is None
                and reply.response_body is not None
                and previous.charge_status == "PENDING"
                and row["reconciliation_record"] is None
            ):
                raise IdentityConflict(
                    "attempt already holds a different durable reply"
                )
        elif row["state"] != "DISPATCHED":
            raise IdentityConflict("only a dispatched attempt can receive a result")
        reserved = _money(row["reserved_microusd"])
        observed_cost = None if reply.usage is None else reply.usage.cost(policy)
        valid_model = reply.observed_model in policy.accepted_models
        valid_usage = reply.usage is not None and (
            reply.usage.input_tokens <= policy.context_window
            and reply.usage.output_tokens <= policy.max_output_tokens
            and reply.usage.total_tokens <= policy.context_window
        )
        anomaly = (
            reply.error_code == "UNEXPECTED_SERVICE_TIER"
            or (reply.observed_model is not None and not valid_model)
            or (reply.usage is not None and not valid_usage)
            or (observed_cost is not None and observed_cost > reserved)
        )
        estimated = (
            observed_cost is not None
            and valid_model
            and valid_usage
            and observed_cost <= reserved
        )
        result = GatewayResult(
            request.project,
            request.branch,
            request.run_id,
            request.logical_id,
            attempt_id,
            request.semantic_hash,
            policy.content_hash,
            _text(row["started_at"], "attempt start"),
            _stamp(instant),
            reply,
            "ESTIMATED" if estimated else "PENDING",
            observed_cost if estimated else None,
            reserved,
        )
        liability = observed_cost if estimated else max(reserved, observed_cost or 0)
        connection.execute(
            """UPDATE attempts SET state='FINISHED',finished_at=?,reply_record=?,
                result_record=?,liability_microusd=? WHERE run_id=? AND attempt_id=?""",
            (
                result.finished_at,
                reply.to_bytes(),
                result.to_bytes(),
                str(liability),
                request.run_id,
                attempt_id,
            ),
        )
        if anomaly:
            self._freeze(
                connection, request.run_id, "OBSERVED_MODEL_USAGE_OR_COST_ANOMALY"
            )
        if result.status == "SUCCESS":
            connection.execute(
                """UPDATE logical_requests SET first_success_attempt=?
                WHERE run_id=? AND logical_id=? AND first_success_attempt IS NULL""",
                (attempt_id, request.run_id, request.logical_id),
            )
        return result

    def finish(
        self,
        request: GatewayRequest,
        policy: ModelPolicy,
        attempt_id: str,
        reply: ProviderReply,
        now: datetime | None = None,
    ) -> GatewayResult:
        if (
            type(request) is not GatewayRequest
            or type(policy) is not ModelPolicy
            or type(reply) is not ProviderReply
        ):
            raise GatewayError("finish requires exact frozen request, policy and reply")
        instant = _now(now)
        with self._transaction() as connection:
            return self._finish(connection, request, policy, attempt_id, reply, instant)

    def lookup(self, run_id: str, logical_id: str) -> GatewayResult | None:
        _text(logical_id, "logical ID")
        with self._transaction() as connection:
            self._budget(connection, run_id)
            logical = connection.execute(
                "SELECT * FROM logical_requests WHERE run_id=? AND logical_id=?",
                (run_id, logical_id),
            ).fetchone()
            if logical is not None and logical["first_success_attempt"] is not None:
                return _result(
                    self._attempt(connection, run_id, logical["first_success_attempt"])
                )
            row = connection.execute(
                "SELECT * FROM attempts WHERE run_id=? AND logical_id=? "
                "AND result_record IS NOT NULL ORDER BY rowid DESC LIMIT 1",
                (run_id, logical_id),
            ).fetchone()
            return None if row is None else _result(row)

    def recover(
        self, run_id: str, attempt_id: str, now: datetime | None = None
    ) -> GatewayResult | None:
        instant = _now(now)
        with self._transaction() as connection:
            self._budget(connection, run_id)
            row = self._attempt(connection, run_id, attempt_id)
            if row["state"] != "DISPATCHED":
                return _result(row)
            request = GatewayRequest.from_dict(
                decode_canonical(_bytes(row["request_record"]))
            )
            policy = ModelPolicy.from_dict(
                decode_canonical(_bytes(row["policy_record"]))
            )
            return self._finish(
                connection,
                request,
                policy,
                attempt_id,
                ProviderReply("UNKNOWN", error_code="INTERRUPTED_AFTER_DISPATCH"),
                instant,
            )

    def cancel_prepared(
        self,
        run_id: str,
        attempt_id: str,
        reason: str,
        now: datetime | None = None,
    ) -> None:
        _text(reason, "proof of cancellation before send")
        instant = _now(now)
        with self._transaction() as connection:
            self._budget(connection, run_id)
            row = self._attempt(connection, run_id, attempt_id)
            if row["state"] != "PREPARED":
                raise IdentityConflict(
                    "only a never-dispatched prepared attempt can be cancelled"
                )
            connection.execute(
                "UPDATE attempts SET state='CANCELLED',finished_at=?,"
                "liability_microusd='0',cancel_reason=? WHERE run_id=? AND attempt_id=?",
                (_stamp(instant), reason, run_id, attempt_id),
            )

    def reconcile(
        self,
        run_id: str,
        attempt_id: str,
        amount_microusd: int,
        evidence_ref: str,
        authority_ref: str,
    ) -> GatewayResult:
        if type(amount_microusd) is not int or amount_microusd < 0:
            raise GatewayError("reconciliation requires exact nonnegative micro-USD")
        _text(evidence_ref, "reconciliation evidence")
        _text(authority_ref, "reconciliation authority")
        reconciliation = canonical_bytes(
            {
                "amount_microusd": amount_microusd,
                "evidence_ref": evidence_ref,
                "authority_ref": authority_ref,
            }
        )
        with self._transaction() as connection:
            self._budget(connection, run_id)
            row = self._attempt(connection, run_id, attempt_id)
            result = _result(row)
            if result is None:
                raise GatewayError("unfinished attempt cannot be reconciled")
            old = row["reconciliation_record"]
            if old is not None:
                if _bytes(old) != reconciliation:
                    raise IdentityConflict(
                        "attempt already has a different reconciliation"
                    )
                return result
            if result.charge_status != "PENDING":
                raise IdentityConflict("only pending liability can be reconciled")
            verified = replace(
                result, charge_status="VERIFIED", charge_microusd=amount_microusd
            )
            connection.execute(
                "UPDATE attempts SET result_record=?,liability_microusd=?,"
                "reconciliation_record=? WHERE run_id=? AND attempt_id=?",
                (
                    verified.to_bytes(),
                    str(amount_microusd),
                    reconciliation,
                    run_id,
                    attempt_id,
                ),
            )
            if amount_microusd > result.reserved_microusd:
                self._freeze(connection, run_id, "RECONCILED_COST_EXCEEDS_RESERVATION")
            return verified

    def summary(self, run_id: str) -> dict[str, object]:
        with self._transaction() as connection:
            row, limit = self._budget(connection, run_id)
            totals = self._totals(connection, run_id)
            return {
                **totals,
                "run_id": run_id,
                "project": limit.project,
                "branch": limit.branch,
                "total_microusd": limit.total_microusd,
                "deadline_at": limit.deadline_at,
                "blocked": row["blocked"] != 0,
                "block_reason": row["block_reason"],
            }
