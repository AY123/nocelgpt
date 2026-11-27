"""Immutable whole-chapter Draft revisions anchored to retained observations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from hashlib import sha256
from typing import TYPE_CHECKING, cast

from anovel.canon.chapter import ChapterCandidate
from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.canon.models import identifier
from anovel.domain.identity import EntityId

from .models import WorkflowError, _record

if TYPE_CHECKING:
    from .extractor import ExtractionObservation

_FIELDS = {
    "record_type",
    "schema_version",
    "artifact_state",
    "chapter_id",
    "run_id",
    "step_id",
    "source_input_hash",
    "assembly_hash",
    "observation_hash",
    "request_id",
    "previous_revision_hash",
    "candidate",
    "candidate_payload_hash",
}


def _digest(value: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("expected exact SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class ChapterRevision:
    """Exact candidate bytes and evidence location; always Draft."""

    chapter_id: EntityId
    run_id: str
    step_id: str
    source_input_hash: str
    assembly_hash: str
    observation_hash: str
    request_id: str
    previous_revision_hash: str | None
    candidate: ChapterCandidate = field(repr=False)

    def __post_init__(self) -> None:
        try:
            if (
                type(self.chapter_id) is not EntityId
                or type(self.candidate) is not ChapterCandidate
            ):
                raise ValueError
            if self.chapter_id.project != self.candidate.project:
                raise ValueError
            identifier(self.chapter_id.local_id)
            identifier(self.run_id)
            identifier(self.request_id)
            for value in (
                self.step_id,
                self.source_input_hash,
                self.assembly_hash,
                self.observation_hash,
            ):
                _digest(value)
            if self.previous_revision_hash is not None:
                _digest(self.previous_revision_hash)
            if (self.previous_revision_hash is None) != (self.version == 1):
                raise ValueError
        except (TypeError, ValueError):
            raise WorkflowError("INVALID_CHAPTER_REVISION") from None

    @property
    def version(self) -> int:
        return self.candidate.version

    @property
    def project(self) -> str:
        return self.candidate.project

    @property
    def branch(self) -> str:
        return self.candidate.branch

    @property
    def artifact_state(self) -> str:
        return "DRAFT"

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "offline_chapter_revision",
            "schema_version": "1.0",
            "artifact_state": self.artifact_state,
            "chapter_id": self.chapter_id.to_dict(),
            "run_id": self.run_id,
            "step_id": self.step_id,
            "source_input_hash": self.source_input_hash,
            "assembly_hash": self.assembly_hash,
            "observation_hash": self.observation_hash,
            "request_id": self.request_id,
            "previous_revision_hash": self.previous_revision_hash,
            "candidate": self.candidate.to_dict(),
            "candidate_payload_hash": self.candidate.payload_hash,
        }

    def payload_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @property
    def record_hash(self) -> str:
        return sha256(self.payload_bytes()).hexdigest()

    @classmethod
    def from_bytes(cls, raw: bytes) -> ChapterRevision:
        try:
            row = _record(decode_canonical(raw), _FIELDS)
            record = cls(
                EntityId.from_dict(row["chapter_id"]),
                cast(str, row["run_id"]),
                cast(str, row["step_id"]),
                cast(str, row["source_input_hash"]),
                cast(str, row["assembly_hash"]),
                cast(str, row["observation_hash"]),
                cast(str, row["request_id"]),
                cast(str | None, row["previous_revision_hash"]),
                ChapterCandidate.from_dict(row["candidate"]),
            )
            if raw != record.payload_bytes():
                raise ValueError
            return record
        except (TypeError, ValueError, KeyError, RecursionError):
            raise WorkflowError("INVALID_CHAPTER_REVISION") from None

    @classmethod
    def from_observation(
        cls,
        observation: ExtractionObservation,
        candidate: ChapterCandidate,
        *,
        request_id: str,
        previous_revision_hash: str | None,
    ) -> ChapterRevision:
        if (candidate.project, candidate.branch) != (
            observation.project,
            observation.branch,
        ):
            raise WorkflowError("CANDIDATE_SCOPE_MISMATCH")
        record = cls(
            observation.chapter_id,
            observation.run_id,
            observation.step_id,
            observation.assembly.child.source.input_hash,
            observation.assembly_hash,
            observation.record_hash,
            request_id,
            previous_revision_hash,
            candidate,
        )
        record.require_observation(observation)
        return record

    def require_observation(self, observation: ExtractionObservation) -> None:
        candidate = self.candidate
        source = observation.assembly.child.source
        if (self.project, self.branch, self.chapter_id) != (
            observation.project,
            observation.branch,
            observation.chapter_id,
        ):
            raise WorkflowError("CANDIDATE_SCOPE_MISMATCH")
        if (
            candidate.id,
            self.run_id,
            self.step_id,
            self.source_input_hash,
            self.assembly_hash,
            self.observation_hash,
        ) != (
            observation.source_id,
            observation.run_id,
            observation.step_id,
            source.input_hash,
            observation.assembly_hash,
            observation.record_hash,
        ):
            raise WorkflowError("CANDIDATE_SOURCE_MISMATCH")
        if candidate.parent_ref != source.contract.parent_ref:
            raise WorkflowError("CANDIDATE_PARENT_MISMATCH")
        proposal = observation.proposal_delta
        if proposal is None:
            raise WorkflowError("Q0_NONEMPTY_PROPOSAL_REQUIRED")
        if canonical_bytes(candidate.delta.to_dict()) != canonical_bytes(
            proposal.to_dict()
        ):
            raise WorkflowError("CANDIDATE_DELTA_MISMATCH")
        if candidate.prose != observation.assembly.prose:
            raise WorkflowError("CANDIDATE_PROSE_CHANGED")
        frozen = {
            "CONTRACT": source.contract_bytes,
            "CONTEXT": source.context_bytes,
            "PACK": next(
                item.content
                for item in source.contract.retained_inputs
                if item.name == "pack"
            ),
        }
        if any(
            item.content != frozen[item.kind]
            for item in candidate.dependencies
            if item.kind in frozen
        ):
            raise WorkflowError("CANDIDATE_DEPENDENCY_MISMATCH")
