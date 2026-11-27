"""Revisions of local chapters written from another Draft."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from hashlib import sha256
from typing import Literal, cast

from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.canon.models import identifier
from anovel.context.scene import SceneSpan
from anovel.domain.identity import EntityId

from .models import WorkflowError, checked_prose

type DraftContinuityKind = Literal["MOTIVE", "CONSEQUENCE", "FACT", "COMMITMENT"]
type DraftCommitmentStatus = Literal["NOT_DUE", "DUE_UNEXPLAINED", "FULFILLED"]
type DraftAnchorKind = DraftContinuityKind | Literal["CHOICE"]
type DraftAnchorIssueReason = Literal["QUOTE_MISSING", "QUOTE_AMBIGUOUS"]


@dataclass(frozen=True, slots=True)
class DraftCommitment:
    """An author's assessment of a promise at one point in the draft."""

    key: str
    due: str
    status: DraftCommitmentStatus

    def __post_init__(self) -> None:
        try:
            identifier(self.key)
            if (
                type(self.due) is not str
                or not self.due.strip()
                or type(self.status) is not str
                or self.status not in ("NOT_DUE", "DUE_UNEXPLAINED", "FULFILLED")
            ):
                raise ValueError
            self.due.encode("utf-8")
        except ValueError:
            raise WorkflowError("INVALID_DRAFT_CONTINUITY") from None

    def to_dict(self) -> dict[str, object]:
        return {"key": self.key, "due": self.due, "status": self.status}

    @classmethod
    def from_dict(cls, value: object) -> DraftCommitment:
        if type(value) is not dict or set(value) != {"key", "due", "status"}:
            raise WorkflowError("INVALID_DRAFT_CONTINUITY")
        return cls(
            cast(str, value["key"]),
            cast(str, value["due"]),
            cast(DraftCommitmentStatus, value["status"]),
        )


@dataclass(frozen=True, slots=True)
class DraftContinuity:
    """Author-selected continuity evidence anchored to exact prose."""

    kind: DraftContinuityKind
    span: SceneSpan
    carry_to_chapter: int | None = None
    commitment: DraftCommitment | None = None

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not str
            or self.kind not in ("MOTIVE", "CONSEQUENCE", "FACT", "COMMITMENT")
            or type(self.span) is not SceneSpan
            or (self.kind == "COMMITMENT") != (self.commitment is not None)
            or (
                self.commitment is not None
                and (
                    type(self.commitment) is not DraftCommitment
                    or self.carry_to_chapter is not None
                )
            )
            or (
                self.carry_to_chapter is not None
                and (
                    type(self.carry_to_chapter) is not int or self.carry_to_chapter < 1
                )
            )
        ):
            raise WorkflowError("INVALID_DRAFT_CONTINUITY")

    def to_dict(self) -> dict[str, object]:
        value: dict[str, object] = {"kind": self.kind, "span": self.span.to_dict()}
        if self.carry_to_chapter is not None:
            value["carry_to_chapter"] = self.carry_to_chapter
        if self.commitment is not None:
            value["commitment"] = self.commitment.to_dict()
        return value

    @classmethod
    def from_dict(cls, value: object) -> DraftContinuity:
        try:
            if type(value) is not dict or set(value) not in (
                {"kind", "span"},
                {"kind", "span", "carry_to_chapter"},
                {"kind", "span", "commitment"},
            ):
                raise ValueError
            carry_to_chapter = value.get("carry_to_chapter")
            if "carry_to_chapter" in value and type(carry_to_chapter) is not int:
                raise ValueError
            return cls(
                cast(DraftContinuityKind, value["kind"]),
                SceneSpan.from_dict(value["span"]),
                carry_to_chapter=carry_to_chapter,
                commitment=DraftCommitment.from_dict(value["commitment"])
                if "commitment" in value
                else None,
            )
        except (TypeError, ValueError):
            raise WorkflowError("INVALID_DRAFT_CONTINUITY") from None


@dataclass(frozen=True, slots=True)
class DraftAnchorIssue:
    """A prior annotation that needs an editor's review after a prose change."""

    kind: DraftAnchorKind
    note_index: int | None
    reason: DraftAnchorIssueReason
    span: SceneSpan

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "note_index": self.note_index,
            "reason": self.reason,
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class DraftAnchorResolution:
    """An editor's replacement or explicit removal of an unresolved annotation."""

    note_index: int | None
    span: SceneSpan | None

    def __post_init__(self) -> None:
        if (
            self.note_index is not None
            and (type(self.note_index) is not int or self.note_index < 0)
        ) or (self.span is not None and type(self.span) is not SceneSpan):
            raise WorkflowError("INVALID_DRAFT_EDIT_RESOLUTION")

    @classmethod
    def from_dict(cls, value: object) -> DraftAnchorResolution:
        try:
            if type(value) is not dict or set(value) != {"note_index", "span"}:
                raise ValueError
            span = value["span"]
            return cls(
                cast(int | None, value["note_index"]),
                None if span is None else SceneSpan.from_dict(span),
            )
        except (TypeError, ValueError):
            raise WorkflowError("INVALID_DRAFT_EDIT_RESOLUTION") from None


@dataclass(frozen=True, slots=True)
class DraftEditPreview:
    """Read-only annotation locations bound to a source revision and proposed prose."""

    chapter_id: EntityId
    revision_hash: str
    prose_hash: str
    choice: SceneSpan | None
    continuity: tuple[DraftContinuity, ...]
    issues: tuple[DraftAnchorIssue, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "written_draft_edit_preview",
            "schema_version": "1.0",
            "artifact_state": "DRAFT",
            "chapter_id": self.chapter_id.to_dict(),
            "revision_hash": self.revision_hash,
            "prose_hash": self.prose_hash,
            "choice": None if self.choice is None else self.choice.to_dict(),
            "continuity": [item.to_dict() for item in self.continuity],
            "review_required": [issue.to_dict() for issue in self.issues],
        }

    def payload_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    def resolve(
        self,
        revision: WrittenDraftRevision,
        resolutions: tuple[DraftAnchorResolution, ...],
    ) -> tuple[SceneSpan | None, tuple[DraftContinuity, ...]]:
        """Apply editor decisions to this verified preview in original note order."""
        if type(resolutions) is not tuple or any(
            type(resolution) is not DraftAnchorResolution for resolution in resolutions
        ):
            raise WorkflowError("INVALID_DRAFT_EDIT_RESOLUTION")
        decisions = {
            resolution.note_index: resolution.span for resolution in resolutions
        }
        if len(decisions) != len(resolutions) or decisions.keys() != {
            issue.note_index for issue in self.issues
        }:
            raise WorkflowError("DRAFT_EDIT_PREVIEW_REVIEW_REQUIRED")

        choice = decisions.get(None, self.choice)
        relocated = iter(self.continuity)
        continuity: list[DraftContinuity] = []
        for index, note in enumerate(revision.continuity):
            if index not in decisions:
                continuity.append(next(relocated))
            elif (span := decisions[index]) is not None:
                continuity.append(replace(note, span=span))
        return choice, tuple(continuity)


@dataclass(frozen=True, slots=True)
class WrittenDraftRevision:
    chapter_id: EntityId
    chapter_number: int
    branch: str
    run_id: str
    input_hash: str
    source_chapter_id: EntityId
    source_revision_hash: str
    writer_input_hash: str
    version: int
    previous_revision_hash: str | None
    prose: bytes = field(repr=False)
    choice: SceneSpan | None = field(default=None, repr=False)
    continuity: tuple[DraftContinuity, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        try:
            if (
                type(self.chapter_id) is not EntityId
                or type(self.source_chapter_id) is not EntityId
                or self.source_chapter_id.project != self.chapter_id.project
                or self.source_chapter_id == self.chapter_id
                or type(self.chapter_number) is not int
                or self.chapter_number < 2
                or type(self.version) is not int
                or self.version < 1
                or (self.version == 1) != (self.previous_revision_hash is None)
            ):
                raise ValueError
            identifier(self.branch)
            identifier(self.run_id)
            hashes: tuple[str, ...] = (
                self.input_hash,
                self.source_revision_hash,
                self.writer_input_hash,
            )
            if self.previous_revision_hash is not None:
                hashes += (self.previous_revision_hash,)
            if any(
                type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None
                for value in hashes
            ):
                raise ValueError
            text = checked_prose(self.prose).decode("utf-8")
            if self.choice is not None and (
                type(self.choice) is not SceneSpan
                or self.choice.end > len(text)
                or text[self.choice.start : self.choice.end] != self.choice.quote
            ):
                raise ValueError
            if type(self.continuity) is not tuple or any(
                type(item) is not DraftContinuity
                or item.span.end > len(text)
                or text[item.span.start : item.span.end] != item.span.quote
                or (
                    item.carry_to_chapter is not None
                    and item.carry_to_chapter <= self.chapter_number + 1
                )
                for item in self.continuity
            ):
                raise ValueError
        except (TypeError, ValueError):
            raise WorkflowError("INVALID_WRITTEN_DRAFT") from None

    @property
    def project(self) -> str:
        return self.chapter_id.project

    @property
    def lineage_key(self) -> tuple[object, ...]:
        """Identity that stays fixed through edits and rewrites of this chapter."""
        return (
            self.chapter_id,
            self.chapter_number,
            self.branch,
            self.run_id,
            self.input_hash,
            self.source_chapter_id,
        )

    @property
    def prose_hash(self) -> str:
        return sha256(self.prose).hexdigest()

    def bind_annotation_quotes(
        self, annotations: object
    ) -> tuple[SceneSpan | None, tuple[DraftContinuity, ...]]:
        """Locate author-selected excerpts in this saved Draft."""
        if (
            type(annotations) is not dict
            or not annotations
            or not annotations.keys() <= {"choice", "add_continuity"}
        ):
            raise WorkflowError("INVALID_DRAFT_ANNOTATIONS")
        notes = annotations.get("add_continuity", [])
        if type(notes) is not list:
            raise WorkflowError("INVALID_DRAFT_ANNOTATIONS")
        text = self.prose.decode("utf-8")

        def locate(quote: object) -> SceneSpan:
            if type(quote) is not str or not quote.strip():
                raise WorkflowError("INVALID_DRAFT_ANNOTATION_QUOTE")
            start = text.find(quote)
            if start < 0:
                raise WorkflowError("DRAFT_ANNOTATION_QUOTE_MISSING")
            if text.find(quote, start + 1) >= 0:
                raise WorkflowError("DRAFT_ANNOTATION_QUOTE_AMBIGUOUS")
            return SceneSpan(start, start + len(quote), quote)

        choice = self.choice
        if "choice" in annotations:
            quote = annotations["choice"]
            choice = None if quote is None else locate(quote)

        continuity = list(self.continuity)
        seen = set(continuity)
        for note in notes:
            if type(note) is not dict or "quote" not in note or "span" in note:
                raise WorkflowError("INVALID_DRAFT_ANNOTATIONS")
            rule = dict(note)
            rule["span"] = locate(rule.pop("quote")).to_dict()
            item = DraftContinuity.from_dict(rule)
            if item not in seen:
                seen.add(item)
                continuity.append(item)
        return choice, tuple(continuity)

    def preview_edit(self, prose: bytes) -> DraftEditPreview:
        """Locate unchanged, unique annotation quotes in the proposed prose."""
        before = self.prose.decode("utf-8")
        after = checked_prose(prose).decode("utf-8")
        issues: list[DraftAnchorIssue] = []

        def relocate(
            span: SceneSpan, kind: DraftAnchorKind, note_index: int | None
        ) -> SceneSpan | None:
            quote = span.quote
            start = after.find(quote)
            if start < 0:
                issues.append(DraftAnchorIssue(kind, note_index, "QUOTE_MISSING", span))
                return None
            if (
                before.find(quote) != span.start
                or before.find(quote, span.start + 1) >= 0
                or after.find(quote, start + 1) >= 0
            ):
                issues.append(
                    DraftAnchorIssue(kind, note_index, "QUOTE_AMBIGUOUS", span)
                )
                return None
            return SceneSpan(start, start + len(quote), quote)

        choice = None if self.choice is None else relocate(self.choice, "CHOICE", None)
        continuity: list[DraftContinuity] = []
        for index, item in enumerate(self.continuity):
            span = relocate(item.span, item.kind, index)
            if span is not None:
                continuity.append(replace(item, span=span))
        return DraftEditPreview(
            self.chapter_id,
            self.record_hash,
            sha256(prose).hexdigest(),
            choice,
            tuple(continuity),
            tuple(issues),
        )

    def to_dict(self) -> dict[str, object]:
        value: dict[str, object] = {
            "record_type": "local_written_draft_revision",
            "schema_version": "1.0",
            "artifact_state": "DRAFT",
            "chapter_id": self.chapter_id.to_dict(),
            "chapter_number": self.chapter_number,
            "branch": self.branch,
            "run_id": self.run_id,
            "input_hash": self.input_hash,
            "source_chapter_id": self.source_chapter_id.to_dict(),
            "source_revision_hash": self.source_revision_hash,
            "writer_input_hash": self.writer_input_hash,
            "version": self.version,
            "previous_revision_hash": self.previous_revision_hash,
            "prose": self.prose.decode("utf-8"),
            "prose_hash": self.prose_hash,
            "choice": None if self.choice is None else self.choice.to_dict(),
        }
        if self.continuity:
            value["continuity"] = [item.to_dict() for item in self.continuity]
        return value

    def payload_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @property
    def record_hash(self) -> str:
        return sha256(self.payload_bytes()).hexdigest()

    @classmethod
    def from_bytes(cls, raw: bytes) -> WrittenDraftRevision:
        try:
            row = decode_canonical(raw)
            if type(row) is not dict or type(row["prose"]) is not str:
                raise ValueError
            continuity = row.get("continuity", [])
            if type(continuity) is not list:
                raise ValueError
            revision = cls(
                EntityId.from_dict(row["chapter_id"]),
                cast(int, row["chapter_number"]),
                cast(str, row["branch"]),
                cast(str, row["run_id"]),
                cast(str, row["input_hash"]),
                EntityId.from_dict(row["source_chapter_id"]),
                cast(str, row["source_revision_hash"]),
                cast(str, row["writer_input_hash"]),
                cast(int, row["version"]),
                cast(str | None, row["previous_revision_hash"]),
                row["prose"].encode("utf-8"),
                None if row["choice"] is None else SceneSpan.from_dict(row["choice"]),
                tuple(DraftContinuity.from_dict(item) for item in continuity),
            )
            if revision.payload_bytes() != raw:
                raise ValueError
            return revision
        except (KeyError, TypeError, ValueError):
            raise WorkflowError("INVALID_WRITTEN_DRAFT") from None
