"""Closed context inputs, auditable selections and role-projected artifacts.

FrozenContextInputs retains complete author inputs for local audit/recovery.
Only ContextArtifact.model_bytes is a model-facing projection. Role labels are
trusted caller inputs, not an authentication system or semantic leak proof.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from base64 import b64decode, b64encode
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import cast

from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.contracts.models import CompiledContract
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import EntityId

POLICY_VERSION = "1.0.0"
COMPILER_VERSION = "1.0.0"
COUNT_METHOD = "UTF8_BYTES_ESTIMATE_V1"
ESTIMATE_STATUS = "ESTIMATE_NOT_PROVIDER_TOKENS"
SOURCE_KINDS = frozenset(
    {
        "SUMMARY",
        "RETRIEVAL",
        "REFERENCE_SIGNAL",
        "REVIEW_NOTE",
        "RAW_REFERENCE",
        "AUTHOR_FUTURE_PLAN",
    }
)
POLICY_HASH = sha256(
    canonical_bytes(
        {
            "version": POLICY_VERSION,
            "compiler_version": COMPILER_VERSION,
            "count_method": COUNT_METHOD,
            "estimate_status": ESTIMATE_STATUS,
            "roles": ["WRITER", "CHARACTER", "REVIEWER"],
            "selection": "scope/role/time before required; explicit priority and stable ID for optional",
            "budget": "complete final model JSON UTF8 bytes plus explicit framing reserve; no mandatory truncation",
            "visibility": "author audit inputs separate; visibility overrides requiredness; no raw reference forwarding",
            "recovery": "full frozen inputs; cache keyed by input identity and this policy",
            "limits": "no Provider token bound, semantic DLP, authentication, generation or Canon write authority",
        }
    )
).hexdigest()


class ContextError(ValueError):
    """Malformed, inconsistent, out-of-budget or unsupported context data."""


class ContextRole(str, Enum):
    WRITER = "WRITER"
    CHARACTER = "CHARACTER"
    REVIEWER = "REVIEWER"


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise ContextError(f"{field} must be nonempty text")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise ContextError(f"{field} must be valid Unicode") from error
    return value


def _integer(value: object, field: str, minimum: int | None = None) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        raise ContextError(
            f"{field} requires an exact integer"
            + ("" if minimum is None else f" >= {minimum}")
        )
    return value


def _boolean(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise ContextError(f"{field} must be an exact boolean")
    return value


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ContextError("expected lowercase SHA256")
    return value


def _commit(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
        raise ContextError("expected complete Canon commit identity")
    return value


def _project(value: object) -> str:
    result = _text(value, "project")
    try:
        EntityId(result, "context-scope-validation")
    except ValueError as error:
        raise ContextError("invalid project identity") from error
    return result


def _id(value: object) -> EntityId:
    if type(value) is not EntityId:
        raise ContextError("expected an exact EntityId")
    return value


def _role(value: object) -> ContextRole:
    if type(value) is not ContextRole:
        raise ContextError("role requires an actual ContextRole")
    return value


def _parsed_role(value: object) -> ContextRole:
    try:
        return ContextRole(_text(value, "role"))
    except ValueError as error:
        raise ContextError("unregistered context role") from error


def _record(
    value: object,
    fields: set[str],
    *,
    kind: str | None = None,
    record_type: str | None = None,
) -> dict[str, object]:
    fixed = {"schema_version"} | ({"kind"} if kind is not None else {"record_type"})
    if type(value) is not dict or set(value) != fields | fixed:
        raise ContextError("context fields must be exact and closed")
    row = cast(dict[str, object], value)
    if (
        row["schema_version"] != "1.0"
        or (kind is not None and row["kind"] != kind)
        or (record_type is not None and row["record_type"] != record_type)
    ):
        raise ContextError("unsupported context record kind/version")
    return row


def _array(value: object) -> list[object]:
    if type(value) is not list:
        raise ContextError("context array must be an exact list")
    return cast(list[object], value)


def _members[T](value: object, member_type: type[T], field: str) -> tuple[T, ...]:
    if type(value) is not tuple or any(type(v) is not member_type for v in value):
        raise ContextError(f"{field} requires an immutable tuple of exact values")
    return cast(tuple[T, ...], value)


def _raw(value: object, field: str) -> bytes:
    if type(value) is not bytes or not value:
        raise ContextError(f"{field} requires complete immutable bytes")
    try:
        value.decode("utf-8")
    except UnicodeError as error:
        raise ContextError(f"{field} is not valid UTF-8") from error
    return value


def _canonical(value: object, field: str) -> bytes:
    raw = _raw(value, field)
    if canonical_bytes(decode_canonical(raw)) != raw:
        raise ContextError(f"{field} must use exact canonical JSON bytes")
    return raw


def _encoded(value: bytes) -> str:
    return b64encode(value).decode("ascii")


def _decoded(value: object) -> bytes:
    if type(value) is not str:
        raise ContextError("context bytes require base64 strings")
    try:
        result = b64decode(value, validate=True)
    except ValueError as error:
        raise ContextError("invalid base64 bytes") from error
    if _encoded(result) != value:
        raise ContextError("noncanonical base64 bytes")
    return result


def _scoped_id(value: EntityId | None, project: str, field: str) -> None:
    if value is not None and _id(value).project != project:
        raise ContextError(f"{field} crosses project")


def _data(kind: str, fields: dict[str, object]) -> dict[str, object]:
    return {"kind": kind, "schema_version": "1.0", **fields}


class _Value(ABC):
    __slots__ = ()

    @abstractmethod
    def to_dict(self) -> dict[str, object]: ...

    def to_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @property
    def content_hash(self) -> str:
        return sha256(self.to_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class ContextBudget(_Value):
    max_units: int
    framing_reserve: int = 0

    def __post_init__(self) -> None:
        _integer(self.max_units, "maximum units", 1)
        _integer(self.framing_reserve, "framing reserve", 0)

    def to_dict(self) -> dict[str, object]:
        return _data(
            "CONTEXT_BUDGET",
            {
                "max_units": self.max_units,
                "framing_reserve": self.framing_reserve,
                "count_method": COUNT_METHOD,
                "estimate_status": ESTIMATE_STATUS,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> ContextBudget:
        row = _record(
            value,
            {"max_units", "framing_reserve", "count_method", "estimate_status"},
            kind="CONTEXT_BUDGET",
        )
        if (row["count_method"], row["estimate_status"]) != (
            COUNT_METHOD,
            ESTIMATE_STATUS,
        ):
            raise ContextError("unsupported local counting policy")
        return cls(
            _integer(row["max_units"], "maximum units", 1),
            _integer(row["framing_reserve"], "framing reserve", 0),
        )


@dataclass(frozen=True, slots=True)
class ContextRequest(_Value):
    project: str
    branch: str
    parent_ref: str
    contract_hash: str
    role: ContextRole
    budget: ContextBudget
    scene_id: EntityId | None = None
    actor_id: EntityId | None = None

    def __post_init__(self) -> None:
        _project(self.project)
        _text(self.branch, "branch")
        _commit(self.parent_ref)
        _digest(self.contract_hash)
        _role(self.role)
        if type(self.budget) is not ContextBudget:
            raise ContextError("request requires an actual context budget")
        _scoped_id(self.scene_id, self.project, "scene")
        _scoped_id(self.actor_id, self.project, "actor")
        if self.role is ContextRole.CHARACTER and self.actor_id is None:
            raise ContextError("character context requires an actual actor")
        if self.role is not ContextRole.CHARACTER and self.actor_id is not None:
            raise ContextError("only character context accepts an actor identity")

    def to_dict(self) -> dict[str, object]:
        return _data(
            "CONTEXT_REQUEST",
            {
                "project": self.project,
                "branch": self.branch,
                "parent_ref": self.parent_ref,
                "contract_hash": self.contract_hash,
                "role": self.role.value,
                "budget": self.budget.to_dict(),
                "scene_id": None if self.scene_id is None else self.scene_id.to_dict(),
                "actor_id": None if self.actor_id is None else self.actor_id.to_dict(),
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> ContextRequest:
        row = _record(
            value,
            {
                "project",
                "branch",
                "parent_ref",
                "contract_hash",
                "role",
                "budget",
                "scene_id",
                "actor_id",
            },
            kind="CONTEXT_REQUEST",
        )
        return cls(
            _project(row["project"]),
            _text(row["branch"], "branch"),
            _commit(row["parent_ref"]),
            _digest(row["contract_hash"]),
            _parsed_role(row["role"]),
            ContextBudget.from_dict(row["budget"]),
            None if row["scene_id"] is None else EntityId.from_dict(row["scene_id"]),
            None if row["actor_id"] is None else EntityId.from_dict(row["actor_id"]),
        )


@dataclass(frozen=True, slots=True)
class ContextSource(_Value):
    id: str
    project: str
    branch: str
    parent_ref: str
    source_ref: str
    source_version: str
    content: bytes
    roles: tuple[ContextRole, ...]
    available_from: NarrativePosition
    fact_ids: tuple[EntityId, ...] = ()
    actor_id: EntityId | None = None
    kind: str = "SUMMARY"
    priority: int = 0
    required: bool = False

    def __post_init__(self) -> None:
        for name in ("id", "branch", "source_ref", "source_version"):
            _text(getattr(self, name), name)
        _project(self.project)
        _commit(self.parent_ref)
        _raw(self.content, "source content")
        _members(self.roles, ContextRole, "source roles")
        if not self.roles or len(set(self.roles)) != len(self.roles):
            raise ContextError("source roles must be nonempty and unique")
        if type(self.available_from) is not NarrativePosition:
            raise ContextError(
                "source availability requires an exact narrative position"
            )
        _members(self.fact_ids, EntityId, "source fact IDs")
        if len(set(self.fact_ids)) != len(self.fact_ids):
            raise ContextError("source repeats a fact identity")
        for fact in self.fact_ids:
            _scoped_id(fact, self.project, "source fact")
        _scoped_id(self.actor_id, self.project, "source actor")
        if type(self.kind) is not str or self.kind not in SOURCE_KINDS:
            raise ContextError("unsupported context source kind")
        _integer(self.priority, "source priority")
        _boolean(self.required, "source required")

    @property
    def raw_content_hash(self) -> str:
        return sha256(self.content).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "context_source",
            "schema_version": "1.0",
            "id": self.id,
            "project": self.project,
            "branch": self.branch,
            "parent_ref": self.parent_ref,
            "source_ref": self.source_ref,
            "source_version": self.source_version,
            "content_base64": _encoded(self.content),
            "raw_content_hash": self.raw_content_hash,
            "roles": [v.value for v in self.roles],
            "available_from": self.available_from.to_dict(),
            "fact_ids": [v.to_dict() for v in self.fact_ids],
            "actor_id": None if self.actor_id is None else self.actor_id.to_dict(),
            "kind": self.kind,
            "priority": self.priority,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, value: object) -> ContextSource:
        row = _record(
            value,
            {
                "id",
                "project",
                "branch",
                "parent_ref",
                "source_ref",
                "source_version",
                "content_base64",
                "raw_content_hash",
                "roles",
                "available_from",
                "fact_ids",
                "actor_id",
                "kind",
                "priority",
                "required",
            },
            record_type="context_source",
        )
        result = cls(
            _text(row["id"], "id"),
            _project(row["project"]),
            _text(row["branch"], "branch"),
            _commit(row["parent_ref"]),
            _text(row["source_ref"], "source ref"),
            _text(row["source_version"], "source version"),
            _decoded(row["content_base64"]),
            tuple(_parsed_role(v) for v in _array(row["roles"])),
            NarrativePosition.from_dict(row["available_from"]),
            tuple(EntityId.from_dict(v) for v in _array(row["fact_ids"])),
            None if row["actor_id"] is None else EntityId.from_dict(row["actor_id"]),
            _text(row["kind"], "source kind"),
            _integer(row["priority"], "priority"),
            _boolean(row["required"], "required"),
        )
        if _digest(row["raw_content_hash"]) != result.raw_content_hash:
            raise ContextError("source raw content hash mismatch")
        return result


@dataclass(frozen=True, slots=True)
class FrozenContextInputs(_Value):
    contract_bytes: bytes
    request: ContextRequest
    sources: tuple[ContextSource, ...] = ()

    def __post_init__(self) -> None:
        _canonical(self.contract_bytes, "frozen contract")
        self.contract
        if type(self.request) is not ContextRequest:
            raise ContextError("frozen input requires an actual request")
        _members(self.sources, ContextSource, "frozen sources")
        if len({v.id for v in self.sources}) != len(self.sources):
            raise ContextError("frozen sources repeat stable IDs")
        object.__setattr__(
            self, "sources", tuple(sorted(self.sources, key=lambda v: v.id))
        )

    @property
    def contract(self) -> CompiledContract:
        return CompiledContract.from_dict(decode_canonical(self.contract_bytes))

    @classmethod
    def from_contract(
        cls,
        contract: CompiledContract,
        request: ContextRequest,
        sources: tuple[ContextSource, ...] = (),
    ) -> FrozenContextInputs:
        if type(contract) is not CompiledContract:
            raise ContextError("an actual immutable compiled contract is required")
        return cls(canonical_bytes(contract.to_dict()), request, sources)

    def to_dict(self) -> dict[str, object]:
        return _data(
            "FROZEN_CONTEXT_INPUTS",
            {
                "visibility": "AUDIT_ONLY",
                "contract_base64": _encoded(self.contract_bytes),
                "contract_hash": self.contract.content_hash,
                "request": self.request.to_dict(),
                "sources": [v.to_dict() for v in self.sources],
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> FrozenContextInputs:
        row = _record(
            value,
            {"visibility", "contract_base64", "contract_hash", "request", "sources"},
            kind="FROZEN_CONTEXT_INPUTS",
        )
        if row["visibility"] != "AUDIT_ONLY":
            raise ContextError("complete frozen author inputs must remain audit-only")
        result = cls(
            _decoded(row["contract_base64"]),
            ContextRequest.from_dict(row["request"]),
            tuple(ContextSource.from_dict(v) for v in _array(row["sources"])),
        )
        if _digest(row["contract_hash"]) != result.contract.content_hash:
            raise ContextError("frozen contract identity mismatch")
        return result


@dataclass(frozen=True, slots=True)
class ContextItem(_Value):
    id: str
    kind: str
    content: bytes
    source_ref: str
    source_hash: str
    required: bool
    reason: str

    def __post_init__(self) -> None:
        for name in ("id", "kind", "source_ref", "reason"):
            _text(getattr(self, name), name)
        _canonical(self.content, "selected item content")
        _digest(self.source_hash)
        _boolean(self.required, "item required")

    @property
    def data(self) -> object:
        return decode_canonical(self.content)

    @property
    def raw_content_hash(self) -> str:
        return sha256(self.content).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "context_item",
            "schema_version": "1.0",
            "id": self.id,
            "kind": self.kind,
            "content_base64": _encoded(self.content),
            "raw_content_hash": self.raw_content_hash,
            "source_ref": self.source_ref,
            "source_hash": self.source_hash,
            "required": self.required,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, value: object) -> ContextItem:
        row = _record(
            value,
            {
                "id",
                "kind",
                "content_base64",
                "raw_content_hash",
                "source_ref",
                "source_hash",
                "required",
                "reason",
            },
            record_type="context_item",
        )
        result = cls(
            _text(row["id"], "id"),
            _text(row["kind"], "kind"),
            _decoded(row["content_base64"]),
            _text(row["source_ref"], "source ref"),
            _digest(row["source_hash"]),
            _boolean(row["required"], "required"),
            _text(row["reason"], "reason"),
        )
        if _digest(row["raw_content_hash"]) != result.raw_content_hash:
            raise ContextError("selected item raw content hash mismatch")
        return result


@dataclass(frozen=True, slots=True)
class SelectionRecord(_Value):
    source_key: str
    included: bool
    required: bool
    reason: str
    units: int = 0

    def __post_init__(self) -> None:
        _digest(self.source_key)
        _boolean(self.included, "included")
        _boolean(self.required, "required")
        _text(self.reason, "reason")
        _integer(self.units, "selection units", 0)

    def to_dict(self) -> dict[str, object]:
        return _data(
            "CONTEXT_SELECTION",
            {
                "source_key": self.source_key,
                "included": self.included,
                "required": self.required,
                "reason": self.reason,
                "units": self.units,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> SelectionRecord:
        row = _record(
            value,
            {"source_key", "included", "required", "reason", "units"},
            kind="CONTEXT_SELECTION",
        )
        return cls(
            _digest(row["source_key"]),
            _boolean(row["included"], "included"),
            _boolean(row["required"], "required"),
            _text(row["reason"], "reason"),
            _integer(row["units"], "units", 0),
        )


@dataclass(frozen=True, slots=True)
class ContextArtifact(_Value):
    project: str
    branch: str
    parent_ref: str
    contract_hash: str
    pack_hash: str
    knowledge_hash: str
    role: ContextRole
    actor_id: EntityId | None
    scene_id: EntityId | None
    input_hash: str
    request_hash: str
    items: tuple[ContextItem, ...]
    selections: tuple[SelectionRecord, ...]
    budget: ContextBudget

    def __post_init__(self) -> None:
        _project(self.project)
        _text(self.branch, "branch")
        _commit(self.parent_ref)
        _role(self.role)
        for v in (
            self.contract_hash,
            self.pack_hash,
            self.knowledge_hash,
            self.input_hash,
            self.request_hash,
        ):
            _digest(v)
        _scoped_id(self.actor_id, self.project, "actor")
        _scoped_id(self.scene_id, self.project, "scene")
        if type(self.budget) is not ContextBudget:
            raise ContextError("artifact needs an actual budget")
        request = ContextRequest(
            self.project,
            self.branch,
            self.parent_ref,
            self.contract_hash,
            self.role,
            self.budget,
            self.scene_id,
            self.actor_id,
        )
        if request.content_hash != self.request_hash:
            raise ContextError("artifact metadata differs from its request identity")
        _members(self.items, ContextItem, "selected items")
        _members(self.selections, SelectionRecord, "selection records")
        if len({v.id for v in self.items}) != len(self.items):
            raise ContextError("selected item identities repeat")
        if len({v.source_key for v in self.selections}) != len(self.selections):
            raise ContextError("selection source identities repeat")
        if self.estimated_units > self.budget.max_units:
            raise ContextError("complete model payload exceeds explicit local budget")

    @property
    def model_bytes(self) -> bytes:
        return canonical_bytes(
            {
                "kind": "ROLE_CONTEXT",
                "schema_version": "1.0",
                "project": self.project,
                "branch": self.branch,
                "parent_ref": self.parent_ref,
                "contract_hash": self.contract_hash,
                "role": self.role.value,
                "actor_id": None if self.actor_id is None else self.actor_id.to_dict(),
                "scene_id": None if self.scene_id is None else self.scene_id.to_dict(),
                "items": [
                    {"id": v.id, "kind": v.kind, "content": v.data} for v in self.items
                ],
            }
        )

    @property
    def estimated_units(self) -> int:
        return len(self.model_bytes) + self.budget.framing_reserve

    @property
    def model_hash(self) -> str:
        return sha256(self.model_bytes).hexdigest()

    @property
    def cache_key(self) -> str:
        return sha256(
            canonical_bytes({"inputs": self.input_hash, "policy": POLICY_HASH})
        ).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return _data(
            "CONTEXT_ARTIFACT",
            {
                "project": self.project,
                "branch": self.branch,
                "parent_ref": self.parent_ref,
                "contract_hash": self.contract_hash,
                "pack_hash": self.pack_hash,
                "knowledge_hash": self.knowledge_hash,
                "role": self.role.value,
                "actor_id": None if self.actor_id is None else self.actor_id.to_dict(),
                "scene_id": None if self.scene_id is None else self.scene_id.to_dict(),
                "input_hash": self.input_hash,
                "request_hash": self.request_hash,
                "items": [v.to_dict() for v in self.items],
                "selections": [v.to_dict() for v in self.selections],
                "budget": self.budget.to_dict(),
                "compiler_version": COMPILER_VERSION,
                "policy_version": POLICY_VERSION,
                "policy_hash": POLICY_HASH,
                "count_method": COUNT_METHOD,
                "estimate_status": ESTIMATE_STATUS,
                "estimated_units": self.estimated_units,
                "model_hash": self.model_hash,
                "cache_key": self.cache_key,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> ContextArtifact:
        row = _record(
            value,
            {
                "project",
                "branch",
                "parent_ref",
                "contract_hash",
                "pack_hash",
                "knowledge_hash",
                "role",
                "actor_id",
                "scene_id",
                "input_hash",
                "request_hash",
                "items",
                "selections",
                "budget",
                "compiler_version",
                "policy_version",
                "policy_hash",
                "count_method",
                "estimate_status",
                "estimated_units",
                "model_hash",
                "cache_key",
            },
            kind="CONTEXT_ARTIFACT",
        )
        if (
            row["compiler_version"],
            row["policy_version"],
            row["policy_hash"],
            row["count_method"],
            row["estimate_status"],
        ) != (
            COMPILER_VERSION,
            POLICY_VERSION,
            POLICY_HASH,
            COUNT_METHOD,
            ESTIMATE_STATUS,
        ):
            raise ContextError("unsupported context compiler/counting policy")
        result = cls(
            _project(row["project"]),
            _text(row["branch"], "branch"),
            _commit(row["parent_ref"]),
            _digest(row["contract_hash"]),
            _digest(row["pack_hash"]),
            _digest(row["knowledge_hash"]),
            _parsed_role(row["role"]),
            None if row["actor_id"] is None else EntityId.from_dict(row["actor_id"]),
            None if row["scene_id"] is None else EntityId.from_dict(row["scene_id"]),
            _digest(row["input_hash"]),
            _digest(row["request_hash"]),
            tuple(ContextItem.from_dict(v) for v in _array(row["items"])),
            tuple(SelectionRecord.from_dict(v) for v in _array(row["selections"])),
            ContextBudget.from_dict(row["budget"]),
        )
        if (
            _integer(row["estimated_units"], "estimated units", 0)
            != result.estimated_units
            or _digest(row["model_hash"]) != result.model_hash
            or _digest(row["cache_key"]) != result.cache_key
        ):
            raise ContextError(
                "artifact counts or derived identity do not match actual content"
            )
        return result


@dataclass(frozen=True, slots=True)
class ContextDiagnostic(_Value):
    code: str
    message: str
    required_units: int | None = None

    def __post_init__(self) -> None:
        _text(self.code, "diagnostic code")
        _text(self.message, "diagnostic message")
        if self.required_units is not None:
            _integer(self.required_units, "required units", 0)

    def to_dict(self) -> dict[str, object]:
        return _data(
            "CONTEXT_DIAGNOSTIC",
            {
                "code": self.code,
                "message": self.message,
                "required_units": self.required_units,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> ContextDiagnostic:
        row = _record(
            value, {"code", "message", "required_units"}, kind="CONTEXT_DIAGNOSTIC"
        )
        return cls(
            _text(row["code"], "code"),
            _text(row["message"], "message"),
            None
            if row["required_units"] is None
            else _integer(row["required_units"], "required units", 0),
        )


@dataclass(frozen=True, slots=True)
class ContextResult(_Value):
    artifact: ContextArtifact | None
    diagnostics: tuple[ContextDiagnostic, ...] = ()
    cache_hit: bool = False

    def __post_init__(self) -> None:
        if self.artifact is not None and type(self.artifact) is not ContextArtifact:
            raise ContextError("result requires an actual artifact")
        _members(self.diagnostics, ContextDiagnostic, "context diagnostics")
        _boolean(self.cache_hit, "cache hit")
        if self.artifact is not None and self.diagnostics:
            raise ContextError(
                "an executable artifact cannot accompany hard diagnostics"
            )
        if self.artifact is None and not self.diagnostics:
            raise ContextError(
                "failed context compilation needs an explicit diagnostic"
            )
        if self.cache_hit and self.artifact is None:
            raise ContextError("a blocked result cannot claim a cache hit")

    @property
    def ok(self) -> bool:
        return self.artifact is not None and not self.diagnostics

    def to_dict(self) -> dict[str, object]:
        return _data(
            "CONTEXT_RESULT",
            {
                "artifact": None if self.artifact is None else self.artifact.to_dict(),
                "diagnostics": [v.to_dict() for v in self.diagnostics],
                "cache_hit": self.cache_hit,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> ContextResult:
        row = _record(
            value, {"artifact", "diagnostics", "cache_hit"}, kind="CONTEXT_RESULT"
        )
        return cls(
            None
            if row["artifact"] is None
            else ContextArtifact.from_dict(row["artifact"]),
            tuple(ContextDiagnostic.from_dict(v) for v in _array(row["diagnostics"])),
            _boolean(row["cache_hit"], "cache hit"),
        )
