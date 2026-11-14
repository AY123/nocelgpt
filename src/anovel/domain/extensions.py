"""Versioned, source-retaining extension ports for reserved scalar facts.

No genre implementation, Canon writer or dynamic plugin loader lives here.
Compiled application composition supplies the actual immutable validators.
An empty registry refuses reserved facts rather than treating them as core data.
"""

from __future__ import annotations

import re
from base64 import b64decode, b64encode
from binascii import Error as Base64Error
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from anovel.domain.identity import EntityId
from anovel.domain.knowledge import WorldFact

if TYPE_CHECKING:
    from anovel.domain.delta import FactBaseline, FactSnapshot


class ExtensionValidationError(ValueError):
    """Missing, unsupported, malformed or inconsistent extension input."""


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise ExtensionValidationError(f"{field} must be a nonempty string")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise ExtensionValidationError(f"{field} is not valid Unicode") from error
    return value


def _namespace(value: object) -> str:
    text = _text(value, "namespace")
    if re.fullmatch(r"[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*", text) is None:
        raise ExtensionValidationError("namespace must be a canonical identifier")
    return text


def _version(value: object) -> str:
    text = _text(value, "version")
    if re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", text) is None:
        raise ExtensionValidationError(
            "extension version must be exact major.minor.patch"
        )
    return text


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ExtensionValidationError("extension identity requires lowercase SHA256")
    return value


def _bytes(value: object, field: str) -> bytes:
    if type(value) is not bytes or not value:
        raise ExtensionValidationError(f"{field} needs complete immutable bytes")
    try:
        value.decode("utf-8")
    except UnicodeError as error:
        raise ExtensionValidationError(f"{field} is not valid UTF-8") from error
    return value


def _encoded(value: bytes) -> str:
    return b64encode(value).decode("ascii")


def _decoded(value: object) -> bytes:
    if type(value) is not str:
        raise ExtensionValidationError("extension bytes must be base64 strings")
    try:
        raw = b64decode(value, validate=True)
    except (ValueError, Base64Error) as error:
        raise ExtensionValidationError("invalid extension base64 bytes") from error
    if _encoded(raw) != value:
        raise ExtensionValidationError("noncanonical extension base64 bytes")
    return raw


def _entity_ids(value: object) -> tuple[EntityId, ...]:
    if (
        type(value) is not tuple
        or not value
        or any(type(item) is not EntityId for item in value)
    ):
        raise ExtensionValidationError("binding needs immutable registered EntityIds")
    if len(set(value)) != len(value) or len({item.project for item in value}) != 1:
        raise ExtensionValidationError(
            "binding entity identities repeat or cross project"
        )
    return tuple(sorted(value, key=lambda item: (item.project, item.local_id)))


@dataclass(frozen=True, slots=True)
class ExtensionBinding:
    namespace: str
    version: str
    schema_id: str
    schema_hash: str
    pack_id: str
    pack_version: str
    pack_hash: str
    pack_bytes: bytes
    schema_bytes: bytes
    entity_ids: tuple[EntityId, ...]

    def __post_init__(self) -> None:
        _namespace(self.namespace)
        _version(self.version)
        _text(self.schema_id, "schema ID")
        _digest(self.schema_hash)
        _text(self.pack_id, "Pack ID")
        _version(self.pack_version)
        _digest(self.pack_hash)
        _bytes(self.pack_bytes, "retained Pack")
        _bytes(self.schema_bytes, "retained Schema")
        if sha256(self.schema_bytes).hexdigest() != self.schema_hash:
            raise ExtensionValidationError(
                "retained Schema bytes do not match their hash"
            )
        object.__setattr__(self, "entity_ids", _entity_ids(self.entity_ids))

    def to_dict(self) -> dict[str, object]:
        return {
            "namespace": self.namespace,
            "version": self.version,
            "schema_id": self.schema_id,
            "schema_hash": self.schema_hash,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "pack_hash": self.pack_hash,
            "pack_base64": _encoded(self.pack_bytes),
            "schema_base64": _encoded(self.schema_bytes),
            "entity_ids": [item.to_dict() for item in self.entity_ids],
        }

    @classmethod
    def from_dict(cls, value: object) -> ExtensionBinding:
        keys = {
            "namespace",
            "version",
            "schema_id",
            "schema_hash",
            "pack_id",
            "pack_version",
            "pack_hash",
            "pack_base64",
            "schema_base64",
            "entity_ids",
        }
        if type(value) is not dict or set(value) != keys:
            raise ExtensionValidationError("extension binding fields are not closed")
        record = cast(dict[str, object], value)
        ids = record["entity_ids"]
        if type(ids) is not list:
            raise ExtensionValidationError("binding entity IDs must be an array")
        return cls(
            _namespace(record["namespace"]),
            _version(record["version"]),
            _text(record["schema_id"], "schema ID"),
            _digest(record["schema_hash"]),
            _text(record["pack_id"], "Pack ID"),
            _version(record["pack_version"]),
            _digest(record["pack_hash"]),
            _decoded(record["pack_base64"]),
            _decoded(record["schema_base64"]),
            tuple(EntityId.from_dict(item) for item in ids),
        )


@runtime_checkable
class ExtensionValidator(Protocol):
    @property
    def namespace(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def schema_id(self) -> str: ...

    @property
    def schema_hash(self) -> str: ...

    def validate_binding(self, binding: ExtensionBinding, project: str) -> None: ...

    def validate_state(
        self, binding: ExtensionBinding, facts: tuple[FactSnapshot, ...]
    ) -> None: ...

    def validate_transition(
        self,
        binding: ExtensionBinding,
        before: tuple[FactSnapshot, ...],
        after: tuple[FactSnapshot, ...],
    ) -> None: ...


def predicate_namespace(predicate: str) -> str | None:
    """Parse only the reserved namespace; concrete fields belong to validators."""
    if not isinstance(predicate, str):
        raise ExtensionValidationError("fact predicate must be a string")
    if not predicate.startswith("ext:"):
        return None
    _text(predicate, "reserved fact predicate")
    parts = predicate.split(":")
    if len(parts) != 3 or not parts[2] or "." not in parts[2]:
        raise ExtensionValidationError("malformed reserved extension predicate")
    return _namespace(parts[1])


@dataclass(frozen=True, slots=True)
class ExtensionRegistry:
    handlers: tuple[ExtensionValidator, ...] = ()

    def __post_init__(self) -> None:
        if type(self.handlers) is not tuple:
            raise ExtensionValidationError(
                "compiled validators must be an immutable tuple"
            )
        seen: set[tuple[str, str]] = set()
        for handler in self.handlers:
            if not isinstance(handler, ExtensionValidator):
                raise ExtensionValidationError(
                    "an actual registered validator is required"
                )
            key = (_namespace(handler.namespace), _version(handler.version))
            _text(handler.schema_id, "registered Schema ID")
            _digest(handler.schema_hash)
            if key in seen:
                raise ExtensionValidationError("duplicate compiled namespace/version")
            seen.add(key)

    def _handler(self, binding: ExtensionBinding) -> ExtensionValidator:
        matches = [
            handler
            for handler in self.handlers
            if (handler.namespace, handler.version)
            == (binding.namespace, binding.version)
        ]
        if len(matches) != 1:
            raise ExtensionValidationError("no compiled validator for frozen extension")
        handler = matches[0]
        if (handler.schema_id, handler.schema_hash) != (
            binding.schema_id,
            binding.schema_hash,
        ):
            raise ExtensionValidationError(
                "frozen extension Schema differs from validator"
            )
        return handler

    def _validate(
        self,
        project: str,
        bindings: tuple[ExtensionBinding, ...],
        facts: tuple[FactSnapshot, ...],
    ) -> dict[str, tuple[FactSnapshot, ...]]:
        from anovel.domain.delta import FactSnapshot

        _text(project, "project")
        if type(bindings) is not tuple or any(
            type(b) is not ExtensionBinding for b in bindings
        ):
            raise ExtensionValidationError(
                "extensions must be immutable exact bindings"
            )
        if len({b.namespace for b in bindings}) != len(bindings):
            raise ExtensionValidationError(
                "only one frozen version per namespace is allowed"
            )
        if type(facts) is not tuple or any(
            not isinstance(f, FactSnapshot) for f in facts
        ):
            raise ExtensionValidationError(
                "extension input must contain fact snapshots"
            )
        grouped: dict[str, list[FactSnapshot]] = {}
        for fact in facts:
            seed = fact.seed_fact
            if (
                seed.id.project != project
                or seed.proposition.subject.project != project
            ):
                raise ExtensionValidationError("fact crosses extension project")
            namespace = predicate_namespace(seed.proposition.predicate)
            if namespace is not None:
                grouped.setdefault(namespace, []).append(fact)
        if set(grouped) != {binding.namespace for binding in bindings}:
            raise ExtensionValidationError("reserved facts and frozen bindings differ")
        result = {namespace: tuple(items) for namespace, items in grouped.items()}
        retained_pack: bytes | None = None
        for binding in bindings:
            if any(entity.project != project for entity in binding.entity_ids):
                raise ExtensionValidationError("binding crosses project")
            if retained_pack is not None and retained_pack != binding.pack_bytes:
                raise ExtensionValidationError(
                    "one root cannot bind conflicting GenrePacks"
                )
            retained_pack = binding.pack_bytes
            handler = self._handler(binding)
            handler.validate_binding(binding, project)
            if any(
                item.seed_fact.proposition.subject not in binding.entity_ids
                for item in result[binding.namespace]
            ):
                raise ExtensionValidationError(
                    "reserved subject is not a registered root entity"
                )
            handler.validate_state(binding, result[binding.namespace])
        return result

    def validate_root(
        self,
        project: str,
        bindings: tuple[ExtensionBinding, ...],
        facts: tuple[WorldFact, ...],
        entity_ids: tuple[EntityId, ...],
    ) -> None:
        from anovel.domain.delta import FactSnapshot

        if type(facts) is not tuple or any(
            type(fact) is not WorldFact for fact in facts
        ):
            raise ExtensionValidationError(
                "root facts must be exact immutable WorldFacts"
            )
        if type(entity_ids) is not tuple or any(
            type(entity) is not EntityId for entity in entity_ids
        ):
            raise ExtensionValidationError("root entity IDs must be an immutable tuple")
        if len(set(entity_ids)) != len(entity_ids) or any(
            e.project != project for e in entity_ids
        ):
            raise ExtensionValidationError("root entity IDs repeat or cross project")
        if type(bindings) is not tuple or any(
            type(b) is not ExtensionBinding for b in bindings
        ):
            raise ExtensionValidationError("root extensions must be exact bindings")
        for binding in bindings:
            if set(binding.entity_ids) != set(entity_ids):
                raise ExtensionValidationError(
                    "binding must retain the complete root entity set"
                )
        self._validate(project, bindings, tuple(FactSnapshot(fact) for fact in facts))

    def validate_baseline(self, baseline: FactBaseline) -> None:
        from anovel.domain.delta import FactBaseline

        if type(baseline) is not FactBaseline:
            raise ExtensionValidationError("a frozen fact baseline is required")
        self._validate(baseline.project, baseline.extensions, baseline.facts)

    def validate_transition(self, before: FactBaseline, after: FactBaseline) -> None:
        from anovel.domain.delta import FactBaseline

        if type(before) is not FactBaseline or type(after) is not FactBaseline:
            raise ExtensionValidationError("transition needs two frozen fact baselines")
        if (before.project, before.branch, before.parent_ref, before.extensions) != (
            after.project,
            after.branch,
            after.parent_ref,
            after.extensions,
        ):
            raise ExtensionValidationError(
                "extension transition changed its frozen binding"
            )
        previous = self._validate(before.project, before.extensions, before.facts)
        proposed = self._validate(after.project, after.extensions, after.facts)
        for binding in before.extensions:
            first, last = previous[binding.namespace], proposed[binding.namespace]
            if {item.seed_fact.id: item.seed_fact for item in first} != {
                item.seed_fact.id: item.seed_fact for item in last
            }:
                raise ExtensionValidationError(
                    "extension fact identities/seed metadata changed"
                )
            self._handler(binding).validate_transition(binding, first, last)
