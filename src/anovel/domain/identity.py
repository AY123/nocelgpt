"""Project-scoped stable entity identities and exact alias resolution."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import Enum


def _text(value: object, field: str, *, identifier: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} cannot be empty and must be a string")
    if identifier and "/" in value:
        raise ValueError(f"{field} cannot contain '/'")
    return value


def _record(
    value: object, *, required: set[str], optional: set[str], field: str
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    record: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{field} keys must be strings")
        record[key] = item
    if not required <= record.keys() or record.keys() - required - optional:
        raise ValueError(f"{field} has missing or unknown fields")
    return record


class AliasResolutionResult(Enum):
    """An exact name may identify no entity, one entity, or several entities."""

    UNIQUE_MATCH = "unique_match"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class EntityId:
    """Stable identity; neither project nor local ID depends on a name."""

    project: str
    local_id: str

    def __post_init__(self) -> None:
        _text(self.project, "project", identifier=True)
        _text(self.local_id, "local_id", identifier=True)

    def __str__(self) -> str:
        return f"{self.project}/{self.local_id}"

    @classmethod
    def from_dict(cls, value: object) -> EntityId:
        record = _record(
            value, required={"project", "local_id"}, optional=set(), field="id"
        )
        return cls(
            project=_text(record["project"], "project", identifier=True),
            local_id=_text(record["local_id"], "local_id", identifier=True),
        )

    def to_dict(self) -> dict[str, str]:
        return {"project": self.project, "local_id": self.local_id}


@dataclass(frozen=True, slots=True, init=False)
class Entity:
    """Immutable entity snapshot; registry operations replace, never mutate it."""

    id: EntityId
    display_name: str
    aliases: frozenset[str]

    def __init__(
        self,
        id: EntityId,
        display_name: str,
        aliases: set[str] | frozenset[str] = frozenset(),
    ) -> None:
        if not isinstance(id, EntityId):
            raise ValueError("id must be an EntityId")
        _text(display_name, "display_name")
        if not isinstance(aliases, (set, frozenset)):
            raise ValueError("aliases must be a set or frozenset")
        checked_aliases = frozenset(_text(alias, "alias") for alias in aliases)
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "display_name", display_name)
        object.__setattr__(self, "aliases", checked_aliases)

    @classmethod
    def from_dict(cls, value: object) -> Entity:
        """Parse the JSON Schema boundary, rejecting coercion and extra fields."""
        record = _record(
            value,
            required={"id", "display_name"},
            optional={"aliases"},
            field="entity",
        )
        alias_values = record.get("aliases", [])
        if not isinstance(alias_values, list):
            raise ValueError("aliases must be an array")
        aliases = {_text(alias, "alias") for alias in alias_values}
        if len(aliases) != len(alias_values):
            raise ValueError("aliases must be unique")
        return cls(
            id=EntityId.from_dict(record["id"]),
            display_name=_text(record["display_name"], "display_name"),
            aliases=aliases,
        )

    def to_dict(self) -> dict[str, object]:
        """Return independent, deterministic JSON-compatible data."""
        return {
            "id": self.id.to_dict(),
            "display_name": self.display_name,
            "aliases": sorted(self.aliases),
        }


class EntityRegistry:
    """In-memory exact lookup; equal names never merge distinct identities."""

    def __init__(self) -> None:
        self._entities: dict[EntityId, Entity] = {}
        self._alias_index: dict[tuple[str, str], set[EntityId]] = {}

    def register(self, entity: Entity) -> None:
        if not isinstance(entity, Entity):
            raise ValueError("entity must be an Entity")
        if entity.id in self._entities:
            raise ValueError(f"entity {entity.id} already registered")
        self._entities[entity.id] = entity
        for name in entity.aliases | {entity.display_name}:
            self._alias_index.setdefault((entity.id.project, name), set()).add(
                entity.id
            )

    def resolve(
        self, project: str, name: str
    ) -> tuple[AliasResolutionResult, Entity | None]:
        """Require project scope; ambiguity returns no arbitrarily chosen entity."""
        _text(project, "project", identifier=True)
        _text(name, "name")
        matches = self._alias_index.get((project, name), set())
        if not matches:
            return AliasResolutionResult.NOT_FOUND, None
        if len(matches) > 1:
            return AliasResolutionResult.AMBIGUOUS, None
        return AliasResolutionResult.UNIQUE_MATCH, self._entities[next(iter(matches))]

    def rename(
        self, entity_id: EntityId, new_display_name: str, keep_old_as_alias: bool = True
    ) -> None:
        """Replace a snapshot, preserving ID; colliding names become ambiguous.

        True retains the old name as an alias. False removes the old name from
        aliases, even if it was already explicitly present. Renaming to the same
        name is a no-op. All other aliases are retained in either case.
        """
        entity = self.get(entity_id)
        if entity is None:
            raise ValueError(f"entity {entity_id} not found")
        _text(new_display_name, "new_display_name")
        if not isinstance(keep_old_as_alias, bool):
            raise ValueError("keep_old_as_alias must be a boolean")
        if new_display_name == entity.display_name:
            return
        aliases = set(entity.aliases)
        if keep_old_as_alias:
            aliases.add(entity.display_name)
        else:
            aliases.discard(entity.display_name)
        updated = replace(
            entity, display_name=new_display_name, aliases=frozenset(aliases)
        )
        old_names = entity.aliases | {entity.display_name}
        new_names = updated.aliases | {updated.display_name}
        for name in old_names - new_names:
            key = (entity_id.project, name)
            self._alias_index[key].remove(entity_id)
            if not self._alias_index[key]:
                del self._alias_index[key]
        for name in new_names - old_names:
            self._alias_index.setdefault((entity_id.project, name), set()).add(
                entity_id
            )
        self._entities[entity_id] = updated

    def get(self, entity_id: EntityId) -> Entity | None:
        if not isinstance(entity_id, EntityId):
            raise ValueError("entity_id must be an EntityId")
        return self._entities.get(entity_id)

    def list_in_project(self, project: str) -> Iterable[Entity]:
        _text(project, "project", identifier=True)
        return tuple(e for e in self._entities.values() if e.id.project == project)
