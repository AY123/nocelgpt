"""Exact two-scene Draft composition, not extraction or acceptance.

This immutable audit value is structurally reproducible, not proof that its
sources are current or that its Gateway receipt is genuine. Those checks belong
to the application service. No source record or prose revision is overwritten.
"""

from __future__ import annotations

from base64 import b64encode
from dataclasses import dataclass, field
from hashlib import sha256
from typing import cast

from anovel.canon.identity import canonical_bytes, decode_canonical

from .generation import SceneGenerationSnapshot
from .models import WorkflowError, result_prose

SEPARATOR = b"\n\n"
ASSEMBLY_POLICY = "EXACT_TWO_SCENE_CONCAT_V1"
_FIXED: dict[str, object] = {
    "record_type": "offline_chapter_assembly",
    "schema_version": "1.0",
    "visibility": "AUDIT_ONLY",
    "assembly_policy": ASSEMBLY_POLICY,
    "whole_chapter_delta": "NOT_EXTRACTED_NOT_VALIDATED",
    "semantic_status": "UNKNOWN",
    "quality_status": "UNKNOWN",
    "accepted": False,
    "published": False,
}
_DERIVED = {
    "child",
    "project",
    "branch",
    "run_id",
    "step_id",
    "chapter_id",
    "contract_hash",
    "source_record_hash",
    "source_input_hash",
    "source_revision",
    "source_prose_hash",
    "child_record_hash",
    "child_prose_hash",
    "separator_base64",
    "prose_base64",
    "prose_hash",
    "segments",
}


@dataclass(frozen=True, slots=True)
class ChapterAssembly:
    child: SceneGenerationSnapshot = field(repr=False)
    _payload: bytes | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        try:
            if type(self.child) is not SceneGenerationSnapshot:
                raise ValueError
            child = self.child
            source = child.source
            first_prose, second_prose = self._parts()
            result = child.result
            if (
                child.state != "DRAFT_SAVED"
                or result is None
                or result_prose(child.request, result) != second_prose
            ):
                raise ValueError
            contract = source.contract
            candidate = child.projection.candidate
            if (
                source.state != "DRAFT_SAVED"
                or len(contract.scenes) != 2
                or (contract.scenes[0].id, contract.scenes[1].id)
                != (candidate.source_scene_id, candidate.target_scene_id)
                or (contract.scenes[0].plan.order, contract.scenes[1].plan.order)
                != (1, 2)
                or candidate.source_record_hash != source.record_hash
                or candidate.source_prose != first_prose
            ):
                raise ValueError
            span = candidate.source_span
            if (
                span.start != 0
                or span.end != len(first_prose.decode("utf-8"))
                or span.quote.encode("utf-8") != first_prose
            ):
                raise ValueError
        except Exception:
            raise WorkflowError("INVALID_CHAPTER_ASSEMBLY") from None

    def _parts(self) -> tuple[bytes, bytes]:
        first, second = self.child.source.prose, self.child.prose
        if type(first) is not bytes or type(second) is not bytes:
            raise WorkflowError("INVALID_CHAPTER_ASSEMBLY")
        # Preserve Unicode, line endings, leading/trailing whitespace and BOM.
        first.decode("utf-8")
        second.decode("utf-8")
        return first, second

    @property
    def prose(self) -> bytes:
        first, second = self._parts()
        return first + SEPARATOR + second

    @property
    def prose_hash(self) -> str:
        return sha256(self.prose).hexdigest()

    @property
    def project(self) -> str:
        return self.child.project

    @property
    def branch(self) -> str:
        return self.child.branch

    @property
    def run_id(self) -> str:
        return self.child.run_id

    @property
    def step_id(self) -> str:
        return self.child.step_id

    @property
    def source_record_hash(self) -> str:
        return self.child.source.record_hash

    @property
    def child_record_hash(self) -> str:
        return self.child.record_hash

    @property
    def contract_hash(self) -> str:
        return self.child.source.contract.content_hash

    @property
    def assembly_policy(self) -> str:
        return ASSEMBLY_POLICY

    @property
    def whole_chapter_delta(self) -> str:
        return "NOT_EXTRACTED_NOT_VALIDATED"

    @property
    def semantic_status(self) -> str:
        return "UNKNOWN"

    @property
    def quality_status(self) -> str:
        return "UNKNOWN"

    @property
    def accepted(self) -> bool:
        return False

    @property
    def published(self) -> bool:
        return False

    def to_dict(self) -> dict[str, object]:
        first, second = self._parts()
        first_units, second_units = (
            len(first.decode("utf-8")),
            len(second.decode("utf-8")),
        )
        separator_units = len(SEPARATOR.decode("utf-8"))
        source = self.child.source
        contract = source.contract
        source_hash, child_hash = source.record_hash, self.child.record_hash
        parts = (
            (
                "SOURCE_SCENE",
                contract.scenes[0].id.to_dict(),
                1,
                source_hash,
                first,
                first_units,
            ),
            ("SEPARATOR", None, None, None, SEPARATOR, separator_units),
            (
                "GENERATED_SCENE",
                contract.scenes[1].id.to_dict(),
                2,
                child_hash,
                second,
                second_units,
            ),
        )
        byte_cursor, unicode_cursor = 0, 0
        segments: list[dict[str, object]] = []
        for kind, scene_id, order, record_hash, raw, units in parts:
            segments.append(
                {
                    "kind": kind,
                    "scene_id": scene_id,
                    "scene_order": order,
                    "source_record_hash": record_hash,
                    "unicode_start": unicode_cursor,
                    "unicode_end": unicode_cursor + units,
                    "byte_start": byte_cursor,
                    "byte_end": byte_cursor + len(raw),
                    "sha256": sha256(raw).hexdigest(),
                }
            )
            byte_cursor += len(raw)
            unicode_cursor += units
        prose = first + SEPARATOR + second
        return {
            **_FIXED,
            "child": self.child.to_dict(),
            "project": self.project,
            "branch": self.branch,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "chapter_id": contract.chapter_id.to_dict(),
            "contract_hash": contract.content_hash,
            "source_record_hash": source_hash,
            "source_input_hash": source.input_hash,
            "source_revision": source.revision,
            "source_prose_hash": sha256(first).hexdigest(),
            "child_record_hash": child_hash,
            "child_prose_hash": sha256(second).hexdigest(),
            "separator_base64": b64encode(SEPARATOR).decode("ascii"),
            "prose_base64": b64encode(prose).decode("ascii"),
            "prose_hash": sha256(prose).hexdigest(),
            "segments": segments,
        }

    @classmethod
    def from_dict(cls, value: object) -> ChapterAssembly:
        try:
            if type(value) is not dict or set(value) != set(_FIXED) | _DERIVED:
                raise ValueError
            row = cast(dict[str, object], value)
            child = SceneGenerationSnapshot.from_bytes(canonical_bytes(row["child"]))
            assembly = cls(child)
            # Re-derive every hash, metadata constant and segment. Canonical
            # comparison preserves exact types (False is not numeric zero).
            if assembly.payload_bytes() != canonical_bytes(row):
                raise ValueError
            return assembly
        except Exception:
            raise WorkflowError("INVALID_CHAPTER_ASSEMBLY") from None

    def payload_bytes(self) -> bytes:
        payload = self._payload
        if payload is None:
            # The child and its validated sources are frozen. Fresh records
            # still rederive and compare their own exact canonical bytes.
            payload = canonical_bytes(self.to_dict())
            object.__setattr__(self, "_payload", payload)
        return payload

    @classmethod
    def from_bytes(cls, raw: bytes) -> ChapterAssembly:
        try:
            if type(raw) is not bytes:
                raise ValueError
            return cls.from_dict(decode_canonical(raw))
        except Exception:
            raise WorkflowError("INVALID_CHAPTER_ASSEMBLY") from None

    @property
    def record_hash(self) -> str:
        return sha256(self.payload_bytes()).hexdigest()

    @property
    def content_hash(self) -> str:
        return self.record_hash
