"""Immutable chapter inputs and retained evidence, never commit authority.

Hashes bind exact inputs. They do not certify semantic checks, ownership, a
Permit, or the identity of a caller supplying this candidate.
"""

from __future__ import annotations

import re
from base64 import b64decode, b64encode
from binascii import Error as Base64Error
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

from anovel.canon.identity import canonical_bytes, raw_prose_hash
from anovel.canon.models import (
    CanonError,
    CanonIntegrityError,
    CommitReceipt,
    identifier,
)
from anovel.domain.delta import FactBaseline, NarrativeDelta
from anovel.domain.identity import EntityId

EVIDENCE_KINDS = frozenset({"CONTRACT", "PACK", "MODEL", "CONTEXT"})


def _record(value: object, keys: set[str], name: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise CanonIntegrityError(f"invalid {name} record")
    return cast(dict[str, object], value)


def _encoded(content: bytes) -> str:
    return b64encode(content).decode("ascii")


def _decoded(value: object) -> bytes:
    if type(value) is not str:
        raise CanonIntegrityError("encoded evidence must be a base64 string")
    try:
        decoded = b64decode(value, validate=True)
    except (Base64Error, ValueError) as error:
        raise CanonIntegrityError("invalid base64 evidence") from error
    if _encoded(decoded) != value:
        raise CanonIntegrityError("noncanonical base64 evidence")
    return decoded


def _digest_matches(value: object, content: bytes) -> None:
    if type(value) is not str or value != sha256(content).hexdigest():
        raise CanonIntegrityError("evidence content hash mismatch")


@dataclass(frozen=True, slots=True)
class CandidateEvidence:
    kind: str
    content: bytes
    schema_id: str
    schema_version: str
    producer: str
    producer_version: str

    def __post_init__(self) -> None:
        if type(self.kind) is not str or self.kind not in EVIDENCE_KINDS:
            raise CanonError("unregistered candidate evidence kind")
        if type(self.content) is not bytes or not self.content:
            raise CanonError("candidate evidence needs complete nonempty bytes")
        for value in (
            self.schema_id,
            self.schema_version,
            self.producer,
            self.producer_version,
        ):
            identifier(value)

    @property
    def content_hash(self) -> str:
        return sha256(self.content).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "producer": self.producer,
            "producer_version": self.producer_version,
            "content_base64": _encoded(self.content),
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, value: object) -> CandidateEvidence:
        record = _record(
            value,
            {
                "kind",
                "schema_id",
                "schema_version",
                "producer",
                "producer_version",
                "content_base64",
                "content_hash",
            },
            "candidate evidence",
        )
        content = _decoded(record["content_base64"])
        _digest_matches(record["content_hash"], content)
        return cls(
            cast(str, record["kind"]),
            content,
            cast(str, record["schema_id"]),
            cast(str, record["schema_version"]),
            cast(str, record["producer"]),
            cast(str, record["producer_version"]),
        )


@dataclass(frozen=True, slots=True)
class ChapterCandidate:
    id: EntityId
    branch: str
    parent_ref: str
    version: int
    prose: bytes
    delta: NarrativeDelta
    dependencies: tuple[CandidateEvidence, ...]

    def __post_init__(self) -> None:
        if type(self.id) is not EntityId or type(self.delta) is not NarrativeDelta:
            raise CanonError(
                "candidate needs exact registered identity and Delta types"
            )
        identifier(self.id.project)
        identifier(self.id.local_id)
        identifier(self.branch)
        if (
            type(self.parent_ref) is not str
            or re.fullmatch(r"sha256:[0-9a-f]{64}", self.parent_ref) is None
        ):
            raise CanonError("candidate parent must be a Canon commit identity")
        if type(self.version) is not int or self.version < 1:
            raise CanonError("candidate version must be a positive integer")
        if type(self.prose) is not bytes or not self.prose:
            raise CanonError("candidate prose needs nonempty UTF-8 bytes")
        raw_prose_hash(self.prose)
        if (
            self.delta.source_id != self.id
            or self.delta.project != self.project
            or self.delta.branch != self.branch
            or self.delta.parent_ref != self.parent_ref
        ):
            raise CanonError("candidate and Delta input bindings differ")
        if (
            type(self.dependencies) is not tuple
            or any(type(item) is not CandidateEvidence for item in self.dependencies)
            or len(self.dependencies) != len(EVIDENCE_KINDS)
            or {item.kind for item in self.dependencies} != EVIDENCE_KINDS
        ):
            raise CanonError("candidate needs exactly one of each evidence kind")
        object.__setattr__(
            self,
            "dependencies",
            tuple(sorted(self.dependencies, key=lambda item: item.kind)),
        )
        # The domain adapter must produce only exact canonical JSON primitives.
        canonical_bytes(self.delta.to_dict())

    @property
    def project(self) -> str:
        return self.id.project

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "CHAPTER_CANDIDATE",
            "schema_version": "1.0",
            "id": self.id.to_dict(),
            "project": self.project,
            "branch": self.branch,
            "parent_ref": self.parent_ref,
            "version": self.version,
            "prose_base64": _encoded(self.prose),
            "raw_prose_hash": raw_prose_hash(self.prose),
            "delta": self.delta.to_dict(),
            "dependencies": [item.to_dict() for item in self.dependencies],
        }

    def payload_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @property
    def payload_hash(self) -> str:
        return sha256(self.payload_bytes()).hexdigest()

    @classmethod
    def from_dict(cls, value: object) -> ChapterCandidate:
        record = _record(
            value,
            {
                "kind",
                "schema_version",
                "id",
                "project",
                "branch",
                "parent_ref",
                "version",
                "prose_base64",
                "raw_prose_hash",
                "delta",
                "dependencies",
            },
            "chapter candidate",
        )
        if record["kind"] != "CHAPTER_CANDIDATE" or record["schema_version"] != "1.0":
            raise CanonIntegrityError("unknown candidate kind or version")
        if type(record["dependencies"]) is not list:
            raise CanonIntegrityError("candidate dependencies must be an array")
        prose = _decoded(record["prose_base64"])
        _digest_matches(record["raw_prose_hash"], prose)
        candidate = cls(
            EntityId.from_dict(record["id"]),
            cast(str, record["branch"]),
            cast(str, record["parent_ref"]),
            cast(int, record["version"]),
            prose,
            NarrativeDelta.from_dict(record["delta"]),
            tuple(CandidateEvidence.from_dict(item) for item in record["dependencies"]),
        )
        if type(record["project"]) is not str or record["project"] != candidate.project:
            raise CanonIntegrityError("candidate crosses project scope")
        return candidate


@dataclass(frozen=True, slots=True)
class StoredChapter:
    receipt: CommitReceipt
    candidate: ChapterCandidate
    state: FactBaseline
    permit_bytes: bytes

    def __post_init__(self) -> None:
        if (
            type(self.receipt) is not CommitReceipt
            or type(self.candidate) is not ChapterCandidate
            or type(self.state) is not FactBaseline
            or type(self.permit_bytes) is not bytes
            or not self.permit_bytes
        ):
            raise CanonIntegrityError("invalid retained chapter evidence types")
        if (
            self.receipt.project != self.candidate.project
            or self.receipt.branch != self.candidate.branch
            or self.receipt.payload_hash != self.candidate.payload_hash
            or self.state.project != self.candidate.project
            or self.state.branch != self.candidate.branch
            or self.state.parent_ref != self.candidate.parent_ref
        ):
            raise CanonIntegrityError("retained chapter evidence bindings differ")
