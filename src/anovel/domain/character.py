"""Immutable characters and relationships with closed JSON boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite

from anovel.domain.identity import Entity, EntityId, _record, _text


class CharacterValidationError(ValueError):
    """Invalid character or relationship data at the domain boundary."""


def _constant(value: object, expected: str, field: str) -> str:
    if not isinstance(value, str) or value != expected:
        raise CharacterValidationError(f"{field} must be {expected}")
    return value


def _description(value: object) -> str:
    if not isinstance(value, str):
        raise CharacterValidationError("description must be a string")
    return value


class Lifecycle(Enum):
    """Character existence states; injuries and emotions are separate state."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DEAD = "DEAD"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CharacterIdentity:
    """Small, closed identity description with explicit unknown values."""

    species: str = "UNKNOWN"
    gender: str = "UNKNOWN"
    origin: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _text(self.species, "species")
        _text(self.gender, "gender")
        _text(self.origin, "origin")

    @classmethod
    def from_dict(cls, value: object) -> CharacterIdentity:
        record = _record(
            value,
            required=set(),
            optional={"species", "gender", "origin"},
            field="identity",
        )
        return cls(
            species=_text(record.get("species", "UNKNOWN"), "species"),
            gender=_text(record.get("gender", "UNKNOWN"), "gender"),
            origin=_text(record.get("origin", "UNKNOWN"), "origin"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "species": self.species,
            "gender": self.gender,
            "origin": self.origin,
        }


_UNKNOWN_IDENTITY = CharacterIdentity()


@dataclass(frozen=True, slots=True, init=False)
class Character(Entity):
    """An entity leaf that preserves all derived data when renamed or restored."""

    identity: CharacterIdentity
    lifecycle: Lifecycle
    description: str
    entity_type: str
    schema_version: str

    def __init__(
        self,
        id: EntityId,
        display_name: str,
        aliases: set[str] | frozenset[str] = frozenset(),
        *,
        identity: CharacterIdentity = _UNKNOWN_IDENTITY,
        lifecycle: Lifecycle = Lifecycle.ACTIVE,
        description: str = "",
        entity_type: str = "CHARACTER",
        schema_version: str = "1.0",
    ) -> None:
        if not isinstance(identity, CharacterIdentity):
            raise CharacterValidationError("identity must be a CharacterIdentity")
        if not isinstance(lifecycle, Lifecycle):
            raise CharacterValidationError("lifecycle must be a Lifecycle")
        checked_description = _description(description)
        checked_type = _constant(entity_type, "CHARACTER", "entity_type")
        checked_version = _constant(schema_version, "1.0", "schema_version")
        Entity.__init__(self, id, display_name, aliases)
        object.__setattr__(self, "identity", identity)
        object.__setattr__(self, "lifecycle", lifecycle)
        object.__setattr__(self, "description", checked_description)
        object.__setattr__(self, "entity_type", checked_type)
        object.__setattr__(self, "schema_version", checked_version)

    @classmethod
    def from_dict(cls, value: object) -> Character:
        record = _record(
            value,
            required={
                "id",
                "display_name",
                "entity_type",
                "schema_version",
                "lifecycle",
            },
            optional={"aliases", "identity", "description"},
            field="character",
        )
        entity_fields = {"id": record["id"], "display_name": record["display_name"]}
        if "aliases" in record:
            entity_fields["aliases"] = record["aliases"]
        entity = Entity.from_dict(entity_fields)
        lifecycle_value = _text(record["lifecycle"], "lifecycle")
        try:
            lifecycle = Lifecycle(lifecycle_value)
        except ValueError as error:
            raise CharacterValidationError(
                "lifecycle is not a supported character lifecycle"
            ) from error
        return cls(
            id=entity.id,
            display_name=entity.display_name,
            aliases=entity.aliases,
            identity=CharacterIdentity.from_dict(record.get("identity", {})),
            lifecycle=lifecycle,
            description=_description(record.get("description", "")),
            entity_type=_constant(record["entity_type"], "CHARACTER", "entity_type"),
            schema_version=_constant(record["schema_version"], "1.0", "schema_version"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **Entity.to_dict(self),
            "entity_type": self.entity_type,
            "schema_version": self.schema_version,
            "identity": self.identity.to_dict(),
            "lifecycle": self.lifecycle.value,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True, init=False)
class Relationship:
    """Project-scoped relationship snapshot, separate from character identity."""

    id: EntityId
    party_a: EntityId
    party_b: EntityId
    relationship_types: frozenset[str]
    trust: float
    entity_type: str
    schema_version: str

    def __init__(
        self,
        id: EntityId,
        party_a: EntityId,
        party_b: EntityId,
        relationship_types: set[str] | frozenset[str],
        trust: float = 0.0,
        *,
        entity_type: str = "RELATIONSHIP",
        schema_version: str = "1.0",
    ) -> None:
        for field, value in (("id", id), ("party_a", party_a), ("party_b", party_b)):
            if not isinstance(value, EntityId):
                raise CharacterValidationError(f"{field} must be an EntityId")
        if party_a.project != id.project or party_b.project != id.project:
            raise CharacterValidationError(
                "relationship IDs must belong to the same project"
            )
        if not isinstance(relationship_types, (set, frozenset)):
            raise CharacterValidationError(
                "relationship_types must be a set or frozenset"
            )
        checked_types = frozenset(
            _text(value, "relationship_type") for value in relationship_types
        )
        if not checked_types:
            raise CharacterValidationError("relationship_types cannot be empty")
        if (
            isinstance(trust, bool)
            or not isinstance(trust, (int, float))
            or not -1 <= trust <= 1
            or not isfinite(trust)
        ):
            raise CharacterValidationError(
                "trust must be a finite number between -1 and 1"
            )
        checked_type = _constant(entity_type, "RELATIONSHIP", "entity_type")
        checked_version = _constant(schema_version, "1.0", "schema_version")
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "party_a", party_a)
        object.__setattr__(self, "party_b", party_b)
        object.__setattr__(self, "relationship_types", checked_types)
        object.__setattr__(self, "trust", float(trust))
        object.__setattr__(self, "entity_type", checked_type)
        object.__setattr__(self, "schema_version", checked_version)

    @classmethod
    def from_dict(cls, value: object) -> Relationship:
        record = _record(
            value,
            required={
                "id",
                "party_a",
                "party_b",
                "relationship_types",
                "entity_type",
                "schema_version",
            },
            optional={"trust"},
            field="relationship",
        )
        type_values = record["relationship_types"]
        if not isinstance(type_values, list):
            raise CharacterValidationError("relationship_types must be an array")
        types = {_text(value, "relationship_type") for value in type_values}
        if len(types) != len(type_values):
            raise CharacterValidationError("relationship_types must be unique")
        trust = record.get("trust", 0.0)
        if isinstance(trust, bool) or not isinstance(trust, (int, float)):
            raise CharacterValidationError(
                "trust must be a finite number between -1 and 1"
            )
        return cls(
            id=EntityId.from_dict(record["id"]),
            party_a=EntityId.from_dict(record["party_a"]),
            party_b=EntityId.from_dict(record["party_b"]),
            relationship_types=types,
            trust=trust,
            entity_type=_constant(record["entity_type"], "RELATIONSHIP", "entity_type"),
            schema_version=_constant(record["schema_version"], "1.0", "schema_version"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id.to_dict(),
            "party_a": self.party_a.to_dict(),
            "party_b": self.party_b.to_dict(),
            "relationship_types": sorted(self.relationship_types),
            "trust": self.trust,
            "entity_type": self.entity_type,
            "schema_version": self.schema_version,
        }
