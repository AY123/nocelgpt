"""Immutable plan lineage and explicit adoption, not Canon history updates."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from anovel.canon.identity import canonical_bytes
from anovel.domain.identity import EntityId
from anovel.planning.models import (
    PlanningError,
    SeriesVision,
    _array,
    _data,
    _digest,
    _id,
    _ids,
    _integer,
    _members,
    _record,
    _scope,
    _text,
    _Value,
)


@dataclass(frozen=True, slots=True)
class PlanVersion(_Value):
    id: EntityId
    revision: int
    parent_hash: str | None
    vision: SeriesVision
    fixture_hash: str

    def __post_init__(self) -> None:
        _id(self.id)
        _integer(self.revision, "plan revision")
        if type(self.vision) is not SeriesVision:
            raise PlanningError("plan version needs an exact SeriesVision")
        _scope(self.id.project, (self.vision.id,))
        _digest(self.fixture_hash)
        if self.revision == 1:
            if self.parent_hash is not None:
                raise PlanningError("initial plan version has no parent")
        else:
            _digest(self.parent_hash)

    @property
    def project(self) -> str:
        return self.id.project

    def to_dict(self) -> dict[str, object]:
        return _data(
            "PLAN_VERSION",
            {
                "id": self.id.to_dict(),
                "revision": self.revision,
                "parent_hash": self.parent_hash,
                "vision": self.vision.to_dict(),
                "fixture_hash": self.fixture_hash,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> PlanVersion:
        row = _record(
            value,
            "PLAN_VERSION",
            {"id", "revision", "parent_hash", "vision", "fixture_hash"},
        )
        return cls(
            EntityId.from_dict(row["id"]),
            _integer(row["revision"], "plan revision"),
            None if row["parent_hash"] is None else _digest(row["parent_hash"]),
            SeriesVision.from_dict(row["vision"]),
            _digest(row["fixture_hash"]),
        )


@dataclass(frozen=True, slots=True)
class Supersession(_Value):
    old_hash: str
    new_hash: str
    reason: str
    authority_ref: str

    def __post_init__(self) -> None:
        _digest(self.old_hash)
        _digest(self.new_hash)
        if self.old_hash == self.new_hash:
            raise PlanningError("a revision cannot supersede itself")
        _text(self.reason, "supersession reason")
        _text(self.authority_ref, "adoption authority reference")

    def to_dict(self) -> dict[str, object]:
        return _data(
            "PLAN_SUPERSESSION",
            {
                "old_hash": self.old_hash,
                "new_hash": self.new_hash,
                "reason": self.reason,
                "authority_ref": self.authority_ref,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> Supersession:
        row = _record(
            value,
            "PLAN_SUPERSESSION",
            {"old_hash", "new_hash", "reason", "authority_ref"},
        )
        return cls(
            _digest(row["old_hash"]),
            _digest(row["new_hash"]),
            _text(row["reason"], "reason"),
            _text(row["authority_ref"], "authority ref"),
        )


def _chapter_context_hash(vision: SeriesVision, chapter_id: EntityId) -> str:
    arc = next(
        (a for a in vision.arcs if any(c.id == chapter_id for c in a.chapters)), None
    )
    if arc is None:
        raise PlanningError("frozen chapter has no enclosing arc")
    return sha256(
        canonical_bytes(
            {
                "vision_id": vision.id.to_dict(),
                "premise": vision.premise,
                "protagonist_goal": vision.protagonist_goal,
                "arc_id": arc.id.to_dict(),
                "arc_purpose": arc.purpose,
            }
        )
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class FrozenChapter(_Value):
    chapter_id: EntityId
    payload_hash: str
    context_hash: str

    def __post_init__(self) -> None:
        _id(self.chapter_id)
        _digest(self.payload_hash)
        _digest(self.context_hash)

    def to_dict(self) -> dict[str, object]:
        return _data(
            "FROZEN_CHAPTER",
            {
                "chapter_id": self.chapter_id.to_dict(),
                "payload_hash": self.payload_hash,
                "context_hash": self.context_hash,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> FrozenChapter:
        row = _record(
            value, "FROZEN_CHAPTER", {"chapter_id", "payload_hash", "context_hash"}
        )
        return cls(
            EntityId.from_dict(row["chapter_id"]),
            _digest(row["payload_hash"]),
            _digest(row["context_hash"]),
        )


@dataclass(frozen=True, slots=True)
class PlanHistory(_Value):
    versions: tuple[PlanVersion, ...]
    supersessions: tuple[Supersession, ...] = ()
    frozen_chapters: tuple[FrozenChapter, ...] = ()

    def __post_init__(self) -> None:
        _members(self.versions, PlanVersion, "plan versions")
        _members(self.supersessions, Supersession, "supersessions")
        _members(self.frozen_chapters, FrozenChapter, "frozen chapters")
        if not self.versions or len(self.supersessions) != len(self.versions) - 1:
            raise PlanningError(
                "history needs a complete initial version and adoption chain"
            )
        identity = self.versions[0].id
        if len({v.content_hash for v in self.versions}) != len(self.versions):
            raise PlanningError("plan history repeats a version")
        for index, version in enumerate(self.versions):
            if version.id != identity or version.revision != index + 1:
                raise PlanningError("history must retain one consecutive plan identity")
            if index:
                prior = self.versions[index - 1]
                edge = self.supersessions[index - 1]
                if version.parent_hash != prior.content_hash or (
                    edge.old_hash,
                    edge.new_hash,
                ) != (prior.content_hash, version.content_hash):
                    raise PlanningError(
                        "plan version and explicit adoption lineage differ"
                    )
        if len({v.chapter_id for v in self.frozen_chapters}) != len(
            self.frozen_chapters
        ):
            raise PlanningError("frozen chapter identities repeat")
        _scope(identity.project, tuple(v.chapter_id for v in self.frozen_chapters))
        for frozen in self.frozen_chapters:
            if (
                self.active.vision.chapter(frozen.chapter_id).content_hash
                != frozen.payload_hash
                or _chapter_context_hash(self.active.vision, frozen.chapter_id)
                != frozen.context_hash
            ):
                raise PlanningError("active plan changed a frozen chapter")

    @property
    def active(self) -> PlanVersion:
        return self.versions[-1]

    def require_active(self, version_hash: str) -> PlanVersion:
        if _digest(version_hash) != self.active.content_hash:
            raise PlanningError(
                "superseded plan version is not valid for new compilation"
            )
        return self.active

    def to_dict(self) -> dict[str, object]:
        return _data(
            "PLAN_HISTORY",
            {
                "versions": [v.to_dict() for v in self.versions],
                "supersessions": [v.to_dict() for v in self.supersessions],
                "frozen_chapters": [v.to_dict() for v in self.frozen_chapters],
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> PlanHistory:
        row = _record(
            value, "PLAN_HISTORY", {"versions", "supersessions", "frozen_chapters"}
        )
        return cls(
            tuple(PlanVersion.from_dict(v) for v in _array(row["versions"])),
            tuple(Supersession.from_dict(v) for v in _array(row["supersessions"])),
            tuple(FrozenChapter.from_dict(v) for v in _array(row["frozen_chapters"])),
        )


def freeze_chapters(
    history: PlanHistory, chapter_ids: tuple[EntityId, ...]
) -> PlanHistory:
    if type(history) is not PlanHistory:
        raise PlanningError("an exact plan history is required")
    _ids(chapter_ids, "frozen chapter IDs")
    frozen = {v.chapter_id: v for v in history.frozen_chapters}
    for chapter_id in chapter_ids:
        chapter = history.active.vision.chapter(chapter_id)
        frozen[chapter_id] = FrozenChapter(
            chapter_id,
            chapter.content_hash,
            _chapter_context_hash(history.active.vision, chapter_id),
        )
    return PlanHistory(
        history.versions,
        history.supersessions,
        tuple(sorted(frozen.values(), key=lambda v: str(v.chapter_id))),
    )


def _validate_revision(history: PlanHistory, version: PlanVersion) -> None:
    if type(history) is not PlanHistory or type(version) is not PlanVersion:
        raise PlanningError("exact history and proposed version are required")
    active = history.active
    if (
        version.id != active.id
        or version.revision != active.revision + 1
        or version.parent_hash != active.content_hash
        or version.vision.id != active.vision.id
    ):
        raise PlanningError("revision must extend the current active plan identity")
    for frozen in history.frozen_chapters:
        if (
            version.vision.chapter(frozen.chapter_id).content_hash
            != frozen.payload_hash
            or _chapter_context_hash(version.vision, frozen.chapter_id)
            != frozen.context_hash
        ):
            raise PlanningError("cannot revise a frozen or accepted chapter")


def adopt_revision(
    history: PlanHistory, version: PlanVersion, *, reason: str, authority_ref: str
) -> PlanHistory:
    """Apply an explicitly supplied adoption decision, not authenticate its actor."""
    _validate_revision(history, version)
    edge = Supersession(
        history.active.content_hash, version.content_hash, reason, authority_ref
    )
    return PlanHistory(
        (*history.versions, version),
        (*history.supersessions, edge),
        history.frozen_chapters,
    )
