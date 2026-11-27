"""Frozen second-scene requests and receipts, sharing the source run budget.

These private audit records never grant Provider, Canon or acceptance authority.
Ledger pins are data here; the application service verifies actual files and
the original Gateway attempt before any dispatch or recovery.
"""

from __future__ import annotations

import threading
from base64 import b64decode, b64encode
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from hashlib import sha256
from typing import cast

from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.context.compiler import compile_context
from anovel.context.models import ContextSource
from anovel.gateway.models import GatewayRequest, GatewayResult

from .ledger_pin import SceneLedgerPin
from .models import WORKFLOW_STATES, WorkflowError, WorkflowSnapshot, result_prose
from .scene import SceneProjection

SCENE_GENERATION_STATES = WORKFLOW_STATES | {"STALE_SOURCE"}
_INSTRUCTIONS = "\nSCENE_DRAFT_V1: Generate only the explicitly selected target scene as an unaccepted draft."
_FIELDS = {
    "record_type",
    "schema_version",
    "visibility",
    "maximum_artifact_state",
    "source",
    "projection",
    "attempt_id",
    "policy_id",
    "ledger_pin",
    "state",
    "result",
    "prose_base64",
    "prose_hash",
    "diagnostic",
    "accepted",
    "step_id",
    "request",
}
_AUDIT_CACHE_LIMIT = 16
_AUDIT_CACHE_LOCK = threading.Lock()
_SOURCE_CACHE: OrderedDict[str, tuple[bytes, WorkflowSnapshot]] = OrderedDict()
_PROJECTION_CACHE: OrderedDict[str, tuple[bytes, SceneProjection]] = OrderedDict()


def _text(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise WorkflowError("INVALID_SCENE_GENERATION")
    return value


def _record(value: object) -> dict[str, object]:
    if type(value) is not dict or set(value) != _FIELDS:
        raise WorkflowError("INVALID_SCENE_GENERATION")
    return cast(dict[str, object], value)


def _source_from_bytes(raw: bytes) -> WorkflowSnapshot:
    """Reuse only the immutable historical source, never a live Store read."""
    key = sha256(raw).hexdigest()
    with _AUDIT_CACHE_LOCK:
        entry = _SOURCE_CACHE.get(key)
        if entry is not None and entry[0] == raw:
            _SOURCE_CACHE.move_to_end(key)
            return entry[1]
    value = WorkflowSnapshot.from_bytes(raw)
    if value.payload_bytes() != raw:
        raise WorkflowError("INVALID_SCENE_GENERATION")
    with _AUDIT_CACHE_LOCK:
        _SOURCE_CACHE[key] = (raw, value)
        _SOURCE_CACHE.move_to_end(key)
        while len(_SOURCE_CACHE) > _AUDIT_CACHE_LIMIT:
            _SOURCE_CACHE.popitem(last=False)
    return value


def _projection_from_bytes(raw: bytes) -> SceneProjection:
    """Cache typed deterministic audit validation for exactly the same bytes.

    A service must still check current source/Context/ledger qualifications.
    This cache is neither a freshness receipt nor a model-facing Context cache.
    """
    key = sha256(raw).hexdigest()
    with _AUDIT_CACHE_LOCK:
        entry = _PROJECTION_CACHE.get(key)
        if entry is not None and entry[0] == raw:
            _PROJECTION_CACHE.move_to_end(key)
            return entry[1]
    value = SceneProjection.from_dict(decode_canonical(raw))
    compiled = compile_context(value.inputs)
    if (
        canonical_bytes(value.to_dict()) != raw
        or compiled.artifact is None
        or compiled.artifact.to_bytes() != value.context.to_bytes()
    ):
        raise WorkflowError("INVALID_SCENE_GENERATION")
    with _AUDIT_CACHE_LOCK:
        _PROJECTION_CACHE[key] = (raw, value)
        _PROJECTION_CACHE.move_to_end(key)
        while len(_PROJECTION_CACHE) > _AUDIT_CACHE_LIMIT:
            _PROJECTION_CACHE.popitem(last=False)
    return value


@dataclass(frozen=True, slots=True)
class SceneGenerationSnapshot:
    source: WorkflowSnapshot = field(repr=False)
    projection: SceneProjection = field(repr=False)
    attempt_id: str
    policy_id: str
    ledger_pin: SceneLedgerPin = field(repr=False)
    state: str = "PREPARED"
    result_bytes: bytes | None = field(default=None, repr=False)
    prose: bytes | None = field(default=None, repr=False)
    diagnostic: str | None = None

    def __post_init__(self) -> None:
        try:
            if (
                type(self.source) is not WorkflowSnapshot
                or type(self.projection) is not SceneProjection
                or type(self.ledger_pin) is not SceneLedgerPin
                or type(self.state) is not str
                or self.state not in SCENE_GENERATION_STATES
            ):
                raise ValueError
            _text(self.attempt_id)
            _text(self.policy_id)
            object.__setattr__(
                self,
                "projection",
                _projection_from_bytes(canonical_bytes(self.projection.to_dict())),
            )
            source = self.source
            candidate = self.projection.candidate
            if (
                source.state != "DRAFT_SAVED"
                or source.prose is None
                or source.result is None
                or source.run_id != candidate.source_run_id
                or source.record_hash != candidate.source_record_hash
                or source.input_hash != candidate.source_input_hash
                or source.revision != candidate.source_revision
                or source.prose != candidate.source_prose
                or source.contract_bytes != self.projection.inputs.contract_bytes
            ):
                raise ValueError
            raw_sources = cast(list[object], source.frozen_input.to_dict()["sources"])
            sources = tuple(
                sorted(
                    (ContextSource.from_dict(v) for v in raw_sources),
                    key=lambda v: v.id,
                )
            )
            if sources != self.projection.inputs.sources:
                raise ValueError
            request = self.request
            if (
                self.attempt_id == source.attempt_id
                or request.logical_id == source.request.logical_id
                or not all(p.test_mode for p in request.policies)
                or self.policy_id not in {p.id for p in request.policies}
            ):
                raise ValueError
            limit = self.ledger_pin.limit
            if (limit.project, limit.branch, limit.run_id) != (
                source.project,
                source.branch,
                source.run_id,
            ):
                raise ValueError
            original = replace(source.result, replayed=False)
            if (
                sha256(original.to_bytes()).hexdigest()
                != self.ledger_pin.parent_result_hash
            ):
                raise ValueError
            result = self.result
            if result is not None:
                policy = next(p for p in request.policies if p.id == self.policy_id)
                if (
                    result.project,
                    result.branch,
                    result.run_id,
                    result.logical_id,
                    result.attempt_id,
                    result.request_hash,
                    result.policy_hash,
                ) != (
                    request.project,
                    request.branch,
                    request.run_id,
                    request.logical_id,
                    self.attempt_id,
                    request.content_hash,
                    policy.content_hash,
                ):
                    raise ValueError
            if self.state == "DRAFT_SAVED":
                if (
                    result is None
                    or type(self.prose) is not bytes
                    or result_prose(request, result) != self.prose
                ):
                    raise ValueError
            elif self.prose is not None:
                raise ValueError
            if self.state in {"PREPARED", "DISPATCHING"} and result is not None:
                raise ValueError
            if self.state in {"UNKNOWN", "FAILED"} and (
                result is None or result.status != self.state
            ):
                raise ValueError
            if self.diagnostic is not None:
                _text(self.diagnostic)
        except Exception:
            raise WorkflowError("INVALID_SCENE_GENERATION") from None

    @property
    def step_id(self) -> str:
        return sha256(
            canonical_bytes(
                {
                    "run_id": self.source.run_id,
                    "source_record_hash": self.source.record_hash,
                    "target_scene_id": self.projection.candidate.target_scene_id.to_dict(),
                }
            )
        ).hexdigest()

    @property
    def request(self) -> GatewayRequest:
        source = self.source.request
        return replace(
            source,
            logical_id="scene-v1-" + self.step_id,
            context=self.projection.context,
            instructions=source.instructions + _INSTRUCTIONS,
            template_version=source.template_version + "/scene-v1",
        )

    @property
    def request_bytes(self) -> bytes:
        return self.request.to_bytes()

    @property
    def project(self) -> str:
        return self.source.project

    @property
    def branch(self) -> str:
        return self.source.branch

    @property
    def run_id(self) -> str:
        return self.source.run_id

    @property
    def result(self) -> GatewayResult | None:
        if self.result_bytes is None:
            return None
        if type(self.result_bytes) is not bytes:
            raise WorkflowError("INVALID_SCENE_GENERATION")
        return GatewayResult.from_dict(decode_canonical(self.result_bytes))

    @property
    def accepted(self) -> bool:
        return False

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "offline_scene_generation_snapshot",
            "schema_version": "1.0",
            "visibility": "AUDIT_ONLY",
            "maximum_artifact_state": "DRAFT",
            "source": self.source.to_dict(),
            "projection": self.projection.to_dict(),
            "attempt_id": self.attempt_id,
            "policy_id": self.policy_id,
            "ledger_pin": self.ledger_pin.to_dict(),
            "state": self.state,
            "result": None if self.result is None else self.result.to_dict(),
            "prose_base64": None
            if self.prose is None
            else b64encode(self.prose).decode("ascii"),
            "prose_hash": None
            if self.prose is None
            else sha256(self.prose).hexdigest(),
            "diagnostic": self.diagnostic,
            "accepted": False,
            "step_id": self.step_id,
            "request": self.request.to_dict(),
        }

    def payload_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @property
    def record_hash(self) -> str:
        return sha256(self.payload_bytes()).hexdigest()

    @classmethod
    def from_bytes(cls, raw: bytes) -> SceneGenerationSnapshot:
        try:
            row = _record(decode_canonical(raw))
            if (
                row["record_type"],
                row["schema_version"],
                row["visibility"],
                row["maximum_artifact_state"],
            ) != (
                "offline_scene_generation_snapshot",
                "1.0",
                "AUDIT_ONLY",
                "DRAFT",
            ) or row["accepted"] is not False:
                raise ValueError
            prose = None
            if row["prose_base64"] is not None:
                encoded = _text(row["prose_base64"])
                prose = b64decode(encoded, validate=True)
                if (
                    b64encode(prose).decode("ascii") != encoded
                    or sha256(prose).hexdigest() != row["prose_hash"]
                ):
                    raise ValueError
            elif row["prose_hash"] is not None:
                raise ValueError
            value = cls(
                _source_from_bytes(canonical_bytes(row["source"])),
                _projection_from_bytes(canonical_bytes(row["projection"])),
                _text(row["attempt_id"]),
                _text(row["policy_id"]),
                SceneLedgerPin.from_dict(row["ledger_pin"]),
                _text(row["state"]),
                None if row["result"] is None else canonical_bytes(row["result"]),
                prose,
                None if row["diagnostic"] is None else _text(row["diagnostic"]),
            )
            if value.step_id != row[
                "step_id"
            ] or value.request_bytes != canonical_bytes(row["request"]):
                raise ValueError
            if value.payload_bytes() != raw:
                raise ValueError
            return value
        except Exception:
            raise WorkflowError("INVALID_SCENE_GENERATION") from None
