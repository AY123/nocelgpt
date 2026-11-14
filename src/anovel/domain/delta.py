"""Finite, evidence-bound fact proposals and pure in-memory preview.

The caller supplies the frozen parent, source and allowed authorization refs.
Matching those references does not authenticate prose, a Permit or Canon HEAD.
Nothing in this module commits facts or updates character knowledge.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from anovel.domain.events import NarrativePosition
from anovel.domain.extensions import ExtensionBinding, ExtensionRegistry
from anovel.domain.identity import EntityId, _record, _text
from anovel.domain.knowledge import Scalar, WorldFact, _same_value, _scalar


class DeltaValidationError(ValueError):
    """A proposal violates the finite delta contract."""


def _revision(value: object) -> int:
    if type(value) is not int or value < 0:
        raise DeltaValidationError("revision must be a non-negative integer")
    return value


def _id(value: object, field: str) -> EntityId:
    if not isinstance(value, EntityId):
        raise DeltaValidationError(f"{field} must be an EntityId")
    return value


def _scope(project: str, value: EntityId, field: str) -> None:
    if value.project != project:
        raise DeltaValidationError(f"{field} belongs to a different project")


def _enum[EnumT: Enum](value: object, enum_type: type[EnumT], field: str) -> EnumT:
    if not isinstance(value, str):
        raise DeltaValidationError(f"{field} must be an enum string")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise DeltaValidationError(f"unknown {field}") from exc


class FactPath(Enum):
    VALUE = "proposition.value"


class ScalarKind(Enum):
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    NUMBER = "NUMBER"


class FactStatus(Enum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    RETRACTED = "RETRACTED"


def _scalar_kind(value: Scalar) -> ScalarKind:
    _scalar(value)
    if isinstance(value, bool):
        return ScalarKind.BOOLEAN
    if isinstance(value, str):
        return ScalarKind.STRING
    return ScalarKind.NUMBER


@dataclass(frozen=True, slots=True, eq=False)
class FactState:
    status: FactStatus
    value: Scalar | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, FactStatus):
            raise DeltaValidationError("status must be a FactStatus")
        if self.status is FactStatus.KNOWN:
            _scalar(self.value)
        elif self.value is not None:
            raise DeltaValidationError("only KNOWN state may contain a value")

    @classmethod
    def known(cls, value: Scalar) -> FactState:
        return cls(FactStatus.KNOWN, value)

    @classmethod
    def unknown(cls) -> FactState:
        return cls(FactStatus.UNKNOWN)

    @classmethod
    def retracted(cls) -> FactState:
        return cls(FactStatus.RETRACTED)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FactState):
            return NotImplemented
        if self.status is not other.status:
            return False
        if self.status is not FactStatus.KNOWN:
            return True
        # Construction ensures both known values are valid, non-null scalars.
        return _same_value(_scalar(self.value), _scalar(other.value))

    def __hash__(self) -> int:
        if self.status is not FactStatus.KNOWN:
            return hash(self.status)
        return hash((self.status, _scalar_kind(_scalar(self.value)), self.value))

    @classmethod
    def from_dict(cls, value: object) -> FactState:
        record = _record(
            value,
            required={"status"},
            optional={"value"},
            field="fact state",
        )
        status = _enum(record["status"], FactStatus, "fact status")
        if status is FactStatus.KNOWN:
            if "value" not in record:
                raise DeltaValidationError("KNOWN state requires value")
            return cls.known(_scalar(record["value"]))
        if "value" in record:
            raise DeltaValidationError("non-KNOWN state must omit value")
        return cls(status)

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"status": self.status.value}
        if self.status is FactStatus.KNOWN:
            result["value"] = self.value
        return result


@dataclass(frozen=True, slots=True, init=False)
class FactSnapshot:
    seed_fact: WorldFact
    revision: int
    state: FactState

    def __init__(
        self,
        seed_fact: WorldFact,
        revision: int = 0,
        *,
        state: FactState | None = None,
    ) -> None:
        if not isinstance(seed_fact, WorldFact):
            raise DeltaValidationError("seed_fact must be a WorldFact")
        _revision(revision)
        initial_state = (
            FactState.known(seed_fact.proposition.value) if state is None else state
        )
        if not isinstance(initial_state, FactState):
            raise DeltaValidationError("state must be a FactState")
        if initial_state.status is FactStatus.KNOWN and _scalar_kind(
            _scalar(initial_state.value)
        ) is not _scalar_kind(seed_fact.proposition.value):
            raise DeltaValidationError("state value does not match the seed value kind")
        object.__setattr__(self, "seed_fact", seed_fact)
        object.__setattr__(self, "revision", revision)
        object.__setattr__(self, "state", initial_state)

    @property
    def value_kind(self) -> ScalarKind:
        return _scalar_kind(self.seed_fact.proposition.value)

    @classmethod
    def from_dict(cls, value: object) -> FactSnapshot:
        record = _record(
            value,
            required={"seed_fact", "revision", "state"},
            optional=set(),
            field="fact snapshot",
        )
        return cls(
            WorldFact.from_dict(record["seed_fact"]),
            _revision(record["revision"]),
            state=FactState.from_dict(record["state"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "seed_fact": self.seed_fact.to_dict(),
            "revision": self.revision,
            "state": self.state.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class FactBaseline:
    project: str
    branch: str
    parent_ref: str
    facts: tuple[FactSnapshot, ...]
    extensions: tuple[ExtensionBinding, ...] = ()

    def __post_init__(self) -> None:
        _text(self.project, "project", identifier=True)
        _text(self.branch, "branch")
        _text(self.parent_ref, "parent_ref")
        if not isinstance(self.facts, tuple):
            raise DeltaValidationError("facts must be a tuple")
        ids: set[EntityId] = set()
        for snapshot in self.facts:
            if not isinstance(snapshot, FactSnapshot):
                raise DeltaValidationError("facts must contain FactSnapshot values")
            fact_id = snapshot.seed_fact.id
            _scope(self.project, fact_id, "fact")
            if fact_id in ids:
                raise DeltaValidationError("baseline contains duplicate fact identity")
            ids.add(fact_id)
        if type(self.extensions) is not tuple or any(
            type(binding) is not ExtensionBinding for binding in self.extensions
        ):
            raise DeltaValidationError("baseline needs immutable extension bindings")
        if len({binding.namespace for binding in self.extensions}) != len(
            self.extensions
        ):
            raise DeltaValidationError("baseline repeats an extension namespace")
        if any(
            entity.project != self.project
            for binding in self.extensions
            for entity in binding.entity_ids
        ):
            raise DeltaValidationError("baseline extension crosses project")

    @classmethod
    def from_world_facts(
        cls,
        project: str,
        branch: str,
        parent_ref: str,
        facts: Iterable[WorldFact],
        *,
        extensions: tuple[ExtensionBinding, ...] = (),
    ) -> FactBaseline:
        return cls(
            project,
            branch,
            parent_ref,
            tuple(FactSnapshot(fact) for fact in facts),
            extensions,
        )

    def get(self, fact_id: EntityId) -> FactSnapshot | None:
        _scope(self.project, _id(fact_id, "fact_id"), "fact_id")
        return next(
            (snapshot for snapshot in self.facts if snapshot.seed_fact.id == fact_id),
            None,
        )

    @classmethod
    def from_dict(cls, value: object) -> FactBaseline:
        if not isinstance(value, dict):
            raise DeltaValidationError("fact baseline must be an object")
        extended = value.get("schema_version") == "1.1"
        record = _record(
            value,
            required={
                "kind",
                "schema_version",
                "project",
                "branch",
                "parent_ref",
                "facts",
            }
            | ({"extensions"} if extended else set()),
            optional=set(),
            field="fact baseline",
        )
        if record["kind"] != "FACT_BASELINE" or record["schema_version"] not in (
            "1.0",
            "1.1",
        ):
            raise DeltaValidationError(
                "unsupported fact baseline kind or schema version"
            )
        facts = record["facts"]
        if not isinstance(facts, list):
            raise DeltaValidationError("facts must be an array")
        bindings: tuple[ExtensionBinding, ...] = ()
        if extended:
            extension_values = record["extensions"]
            if type(extension_values) is not list or not extension_values:
                raise DeltaValidationError(
                    "extended baseline requires nonempty bindings"
                )
            bindings = tuple(
                ExtensionBinding.from_dict(item) for item in extension_values
            )
        return cls(
            _text(record["project"], "project", identifier=True),
            _text(record["branch"], "branch"),
            _text(record["parent_ref"], "parent_ref"),
            tuple(FactSnapshot.from_dict(item) for item in facts),
            bindings,
        )

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "kind": "FACT_BASELINE",
            "schema_version": "1.1" if self.extensions else "1.0",
            "project": self.project,
            "branch": self.branch,
            "parent_ref": self.parent_ref,
            "facts": [snapshot.to_dict() for snapshot in self.facts],
        }
        if self.extensions:
            result["extensions"] = [binding.to_dict() for binding in self.extensions]
        return result


@dataclass(frozen=True, slots=True)
class Precondition:
    revision: int
    state: FactState

    def __post_init__(self) -> None:
        _revision(self.revision)
        if not isinstance(self.state, FactState):
            raise DeltaValidationError("state must be a FactState")

    @classmethod
    def from_snapshot(cls, snapshot: FactSnapshot) -> Precondition:
        if not isinstance(snapshot, FactSnapshot):
            raise DeltaValidationError("snapshot must be a FactSnapshot")
        return cls(snapshot.revision, snapshot.state)

    @classmethod
    def from_dict(cls, value: object) -> Precondition:
        record = _record(
            value,
            required={"revision", "state"},
            optional=set(),
            field="precondition",
        )
        return cls(_revision(record["revision"]), FactState.from_dict(record["state"]))

    def to_dict(self) -> dict[str, object]:
        return {"revision": self.revision, "state": self.state.to_dict()}


@dataclass(frozen=True, slots=True)
class ProseEvidence:
    source_id: EntityId
    position: NarrativePosition
    evidence_ref: str

    def __post_init__(self) -> None:
        _id(self.source_id, "source_id")
        if not isinstance(self.position, NarrativePosition):
            raise DeltaValidationError("position must be a NarrativePosition")
        _text(self.evidence_ref, "evidence_ref")

    @classmethod
    def from_dict(cls, value: object) -> ProseEvidence:
        record = _record(
            value,
            required={"source_id", "position", "evidence_ref"},
            optional=set(),
            field="prose evidence",
        )
        return cls(
            EntityId.from_dict(record["source_id"]),
            NarrativePosition.from_dict(record["position"]),
            _text(record["evidence_ref"], "evidence_ref"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id.to_dict(),
            "position": self.position.to_dict(),
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class OperationMeta:
    id: EntityId
    target_id: EntityId
    path: FactPath
    expected: Precondition
    evidence: ProseEvidence
    authorization_ref: str

    def __post_init__(self) -> None:
        _id(self.id, "operation id")
        _scope(self.id.project, _id(self.target_id, "target_id"), "target_id")
        if not isinstance(self.path, FactPath):
            raise DeltaValidationError("path must be a registered FactPath")
        if not isinstance(self.expected, Precondition):
            raise DeltaValidationError("expected must be a Precondition")
        if not isinstance(self.evidence, ProseEvidence):
            raise DeltaValidationError("evidence must be ProseEvidence")
        _scope(self.id.project, self.evidence.source_id, "evidence source")
        _text(self.authorization_ref, "authorization_ref")

    @classmethod
    def from_dict(cls, value: object) -> OperationMeta:
        record = _record(
            value,
            required=_META_FIELDS,
            optional=set(),
            field="operation metadata",
        )
        return cls(
            EntityId.from_dict(record["id"]),
            EntityId.from_dict(record["target_id"]),
            _enum(record["path"], FactPath, "fact path"),
            Precondition.from_dict(record["expected"]),
            ProseEvidence.from_dict(record["evidence"]),
            _text(record["authorization_ref"], "authorization_ref"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id.to_dict(),
            "target_id": self.target_id.to_dict(),
            "path": self.path.value,
            "expected": self.expected.to_dict(),
            "evidence": self.evidence.to_dict(),
            "authorization_ref": self.authorization_ref,
        }


_META_FIELDS = {"id", "target_id", "path", "expected", "evidence", "authorization_ref"}


class _OperationMethods:
    __slots__ = ()

    OP: ClassVar[str]
    meta: OperationMeta

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "op": self.OP,
            "version": "1.0",
            **self.meta.to_dict(),
        }
        if isinstance(self, SetFact):
            result["value"] = self.value
        return result


def _operation_meta(value: object) -> None:
    if not isinstance(value, OperationMeta):
        raise DeltaValidationError("meta must be OperationMeta")


@dataclass(frozen=True, slots=True)
class SetFact(_OperationMethods):
    meta: OperationMeta
    value: Scalar
    OP: ClassVar[str] = "SET_FACT"

    def __post_init__(self) -> None:
        _operation_meta(self.meta)
        _scalar(self.value)


@dataclass(frozen=True, slots=True)
class MarkUnknown(_OperationMethods):
    meta: OperationMeta
    OP: ClassVar[str] = "MARK_UNKNOWN"

    def __post_init__(self) -> None:
        _operation_meta(self.meta)


@dataclass(frozen=True, slots=True)
class RetractFact(_OperationMethods):
    meta: OperationMeta
    OP: ClassVar[str] = "RETRACT_FACT"

    def __post_init__(self) -> None:
        _operation_meta(self.meta)


@dataclass(frozen=True, slots=True)
class NoChange(_OperationMethods):
    meta: OperationMeta
    OP: ClassVar[str] = "NO_CHANGE"

    def __post_init__(self) -> None:
        _operation_meta(self.meta)


Operation = SetFact | MarkUnknown | RetractFact | NoChange


def operation_from_dict(value: object) -> Operation:
    record = _record(
        value,
        required={"op", "version"} | _META_FIELDS,
        optional={"value"},
        field="delta operation",
    )
    if record["version"] != "1.0":
        raise DeltaValidationError("unsupported operation version")
    op = record["op"]
    if op not in ("SET_FACT", "MARK_UNKNOWN", "RETRACT_FACT", "NO_CHANGE"):
        raise DeltaValidationError("unregistered operation")
    meta = OperationMeta.from_dict({key: record[key] for key in _META_FIELDS})
    if op == "SET_FACT":
        if "value" not in record:
            raise DeltaValidationError("SET_FACT requires value")
        return SetFact(meta, _scalar(record["value"]))
    if "value" in record:
        raise DeltaValidationError("only SET_FACT may contain value")
    if op == "MARK_UNKNOWN":
        return MarkUnknown(meta)
    if op == "RETRACT_FACT":
        return RetractFact(meta)
    return NoChange(meta)


@dataclass(frozen=True, slots=True)
class NarrativeDelta:
    """A structural candidate, not an approved or applicable ChangeSet.

    Parsing cannot check an external seed, precondition or allowed refs;
    preview requires that context before producing an uncommitted candidate.
    """

    id: EntityId
    branch: str
    parent_ref: str
    source_id: EntityId
    operations: tuple[Operation, ...]

    def __post_init__(self) -> None:
        _id(self.id, "delta id")
        _text(self.branch, "branch")
        _text(self.parent_ref, "parent_ref")
        _scope(self.project, _id(self.source_id, "source_id"), "source_id")
        if not isinstance(self.operations, tuple) or not self.operations:
            raise DeltaValidationError("operations must be a non-empty tuple")
        ids: set[EntityId] = set()
        targets: set[tuple[EntityId, FactPath]] = set()
        for operation in self.operations:
            if type(operation) not in (SetFact, MarkUnknown, RetractFact, NoChange):
                raise DeltaValidationError("unregistered operation type")
            meta = operation.meta
            _scope(self.project, meta.id, "operation id")
            if meta.evidence.source_id != self.source_id:
                raise DeltaValidationError(
                    "operation source does not match delta source"
                )
            if meta.id in ids:
                raise DeltaValidationError("duplicate operation identity")
            target = (meta.target_id, meta.path)
            if target in targets:
                raise DeltaValidationError("duplicate operation target and path")
            ids.add(meta.id)
            targets.add(target)

    @property
    def project(self) -> str:
        return self.id.project

    @classmethod
    def from_dict(cls, value: object) -> NarrativeDelta:
        record = _record(
            value,
            required={
                "kind",
                "schema_version",
                "id",
                "branch",
                "parent_ref",
                "source_id",
                "operations",
            },
            optional=set(),
            field="narrative delta",
        )
        if record["kind"] != "NARRATIVE_DELTA" or record["schema_version"] != "1.0":
            raise DeltaValidationError(
                "unsupported narrative delta kind or schema version"
            )
        operations = record["operations"]
        if not isinstance(operations, list):
            raise DeltaValidationError("operations must be an array")
        return cls(
            EntityId.from_dict(record["id"]),
            _text(record["branch"], "branch"),
            _text(record["parent_ref"], "parent_ref"),
            EntityId.from_dict(record["source_id"]),
            tuple(operation_from_dict(operation) for operation in operations),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "NARRATIVE_DELTA",
            "schema_version": "1.0",
            "id": self.id.to_dict(),
            "branch": self.branch,
            "parent_ref": self.parent_ref,
            "source_id": self.source_id.to_dict(),
            "operations": [operation.to_dict() for operation in self.operations],
        }


@dataclass(frozen=True, slots=True)
class FactChange:
    operation_id: EntityId
    before: FactSnapshot
    after: FactSnapshot


@dataclass(frozen=True, slots=True)
class PreviewResult:
    """A local candidate projection, never a ChangeSet, Permit or Canon commit."""

    delta_id: EntityId
    candidate: FactBaseline
    changes: tuple[FactChange, ...]


def _preview_operation(snapshot: FactSnapshot, operation: Operation) -> FactSnapshot:
    expected = operation.meta.expected
    if snapshot.revision != expected.revision or snapshot.state != expected.state:
        raise DeltaValidationError("stale or mismatched fact precondition")
    if isinstance(operation, NoChange):
        return snapshot
    if snapshot.state.status is FactStatus.RETRACTED:
        raise DeltaValidationError("RETRACTED is terminal; only NO_CHANGE is permitted")
    if isinstance(operation, SetFact):
        if _scalar_kind(operation.value) is not snapshot.value_kind:
            raise DeltaValidationError(
                "SET_FACT value does not match the seed value kind"
            )
        state = FactState.known(operation.value)
        if state == snapshot.state:
            raise DeltaValidationError("same-value SET_FACT requires NO_CHANGE")
    elif isinstance(operation, MarkUnknown):
        if snapshot.state.status is not FactStatus.KNOWN:
            raise DeltaValidationError(
                "MARK_UNKNOWN requires a KNOWN fact; use NO_CHANGE"
            )
        state = FactState.unknown()
    else:
        state = FactState.retracted()
    return FactSnapshot(snapshot.seed_fact, snapshot.revision + 1, state=state)


def preview_delta(
    baseline: FactBaseline,
    delta: NarrativeDelta,
    *,
    source_id: EntityId,
    authorization_refs: frozenset[str],
    extension_registry: ExtensionRegistry | None = None,
) -> PreviewResult:
    """Validate against a frozen parent and return an uncommitted candidate.

    These caller-supplied references are not a Permit, authorization proof or
    prose verifier. Replaying against the same original baseline is pure;
    changing a fact makes its old revision fail against the returned candidate.
    """
    if not isinstance(baseline, FactBaseline) or not isinstance(delta, NarrativeDelta):
        raise DeltaValidationError("preview requires FactBaseline and NarrativeDelta")
    if (
        extension_registry is not None
        and type(extension_registry) is not ExtensionRegistry
    ):
        raise DeltaValidationError(
            "extension_registry must be an actual compiled registry"
        )
    registry = ExtensionRegistry() if extension_registry is None else extension_registry
    registry.validate_baseline(baseline)
    _id(source_id, "source_id")
    if source_id != delta.source_id:
        raise DeltaValidationError("source does not match caller-supplied source")
    if not isinstance(authorization_refs, frozenset):
        raise DeltaValidationError("authorization_refs must be a frozenset")
    for ref in authorization_refs:
        _text(ref, "authorization ref")
    if (
        baseline.project != delta.project
        or baseline.branch != delta.branch
        or baseline.parent_ref != delta.parent_ref
    ):
        raise DeltaValidationError(
            "delta does not match baseline project, branch and parent"
        )
    candidates = {snapshot.seed_fact.id: snapshot for snapshot in baseline.facts}
    changes: list[FactChange] = []
    for operation in delta.operations:
        meta = operation.meta
        if meta.authorization_ref not in authorization_refs:
            raise DeltaValidationError(
                "operation authorization ref is not allowed by caller"
            )
        before = baseline.get(meta.target_id)
        if before is None:
            raise DeltaValidationError("operation target is not registered in baseline")
        after = _preview_operation(before, operation)
        candidates[meta.target_id] = after
        if after is not before:
            changes.append(FactChange(meta.id, before, after))
    candidate = FactBaseline(
        baseline.project,
        baseline.branch,
        baseline.parent_ref,
        tuple(candidates[snapshot.seed_fact.id] for snapshot in baseline.facts),
        baseline.extensions,
    )
    registry.validate_transition(baseline, candidate)
    return PreviewResult(delta.id, candidate, tuple(changes))
