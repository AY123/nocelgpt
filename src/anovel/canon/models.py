"""Immutable root persistence contracts; no authentication or database effects."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from anovel.canon.identity import utc_timestamp
from anovel.domain.character import Relationship
from anovel.domain.identity import Entity, EntityId
from anovel.domain.knowledge import WorldFact


class CanonError(ValueError):
    """Rejected Canon operation; transaction must not partially succeed."""


class CanonConflict(CanonError):
    """A stale intent, occupied root or changed payload conflicts."""


class CanonPermissionError(CanonError):
    """Missing, cancelled or revoked initialization authority."""


class CanonIntegrityError(CanonError):
    """Stored identity/content cannot be trusted."""


def identifier(value: str) -> str:
    if (
        type(value) is not str
        or not value.strip()
        or len(value) > 200
        or "\x00" in value
    ):
        raise CanonError("expected a nonempty bounded identifier")
    return value


@dataclass(frozen=True, slots=True)
class RootSeed:
    entities: tuple[Entity, ...]
    relationships: tuple[Relationship, ...]
    facts: tuple[WorldFact, ...]

    def __post_init__(self) -> None:
        groups = (
            (self.entities, Entity),
            (self.relationships, Relationship),
            (self.facts, WorldFact),
        )
        ids: list[EntityId] = []
        for items, cls in groups:
            if type(items) is not tuple or any(type(item) is not cls for item in items):
                raise CanonError("root accepts exact immutable domain types")
            ids.extend(item.id for item in items)
        if not ids or len(ids) != len(set(ids)):
            raise CanonError("root needs nonempty, unique domain identities")
        projects = {item.project for item in ids}
        if len(projects) != 1:
            raise CanonError("root crosses project scopes")
        entities = {item.id for item in self.entities}
        if any(
            item.party_a not in entities or item.party_b not in entities
            for item in self.relationships
        ):
            raise CanonError("relationship endpoint is not registered in root")
        if any(item.proposition.subject not in entities for item in self.facts):
            raise CanonError("fact subject is not registered in root")

    @property
    def project(self) -> str:
        return self.entities[0].id.project

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "ROOT_SEED",
            "schema_version": "1.0",
            "entities": [
                v.to_dict() for v in sorted(self.entities, key=lambda v: str(v.id))
            ],
            "relationships": [
                v.to_dict() for v in sorted(self.relationships, key=lambda v: str(v.id))
            ],
            "facts": [v.to_dict() for v in sorted(self.facts, key=lambda v: str(v.id))],
        }

    @classmethod
    def from_dict(cls, value: object) -> RootSeed:
        if type(value) is not dict or set(value) != {
            "kind",
            "schema_version",
            "entities",
            "relationships",
            "facts",
        }:
            raise CanonIntegrityError("invalid root seed record")
        if value["kind"] != "ROOT_SEED" or value["schema_version"] != "1.0":
            raise CanonIntegrityError("unknown root seed version")
        if any(
            type(value[key]) is not list
            for key in ("entities", "relationships", "facts")
        ):
            raise CanonIntegrityError("root members must be arrays")
        return cls(
            tuple(Entity.from_dict(v) for v in value["entities"]),
            tuple(Relationship.from_dict(v) for v in value["relationships"]),
            tuple(WorldFact.from_dict(v) for v in value["facts"]),
        )


@dataclass(frozen=True, slots=True)
class ExecutionTicket:
    project: str
    branch: str
    request_id: str
    actor: str
    authorization_version: int
    execution_version: int

    def __post_init__(self) -> None:
        for value in (self.project, self.branch, self.request_id, self.actor):
            identifier(value)
        for version in (self.authorization_version, self.execution_version):
            if type(version) is not int or version < 0:
                raise CanonError("control versions must be nonnegative integers")


@dataclass(frozen=True, slots=True)
class CommitReceipt:
    project: str
    branch: str
    request_id: str
    commit_id: str
    payload_hash: str
    created_at: str

    def __post_init__(self) -> None:
        for value in (self.project, self.branch, self.request_id):
            identifier(value)
        if (
            type(self.commit_id) is not str
            or re.fullmatch(r"sha256:[0-9a-f]{64}", self.commit_id) is None
        ):
            raise CanonError("invalid commit identity")
        if (
            type(self.payload_hash) is not str
            or re.fullmatch(r"[0-9a-f]{64}", self.payload_hash) is None
        ):
            raise CanonError("invalid receipt payload hash")
        if (
            type(self.created_at) is not str
            or re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z",
                self.created_at,
            )
            is None
        ):
            raise CanonError("receipt timestamp must be canonical UTC")
        try:
            parsed = datetime.fromisoformat(self.created_at)
        except ValueError as error:
            raise CanonError("invalid receipt calendar timestamp") from error
        if utc_timestamp(parsed) != self.created_at:
            raise CanonError("noncanonical receipt timestamp")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "COMMIT_RECEIPT",
            "schema_version": "1.0",
            "project": self.project,
            "branch": self.branch,
            "request_id": self.request_id,
            "commit_id": self.commit_id,
            "payload_hash": self.payload_hash,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, value: object) -> CommitReceipt:
        if type(value) is not dict or set(value) != {
            "kind",
            "schema_version",
            "project",
            "branch",
            "request_id",
            "commit_id",
            "payload_hash",
            "created_at",
        }:
            raise CanonIntegrityError("invalid receipt record")
        if value["kind"] != "COMMIT_RECEIPT" or value["schema_version"] != "1.0":
            raise CanonIntegrityError("unknown receipt kind or version")
        return cls(
            value["project"],
            value["branch"],
            value["request_id"],
            value["commit_id"],
            value["payload_hash"],
            value["created_at"],
        )


@dataclass(frozen=True, slots=True)
class StoredRoot:
    receipt: CommitReceipt
    seed: RootSeed
    prose: bytes
    authority_bytes: bytes
