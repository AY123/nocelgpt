"""Closed, immutable planning inputs; human review metadata is not authentication.

Only registered scalar-fact transitions are represented. Character knowledge,
goals and beliefs remain explicit retained author inputs, not a second Canon.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from base64 import b64decode, b64encode
from binascii import Error as Base64Error
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import ClassVar, cast

from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.canon.models import RootSeed
from anovel.domain.delta import FactPath, FactState
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import EntityId
from anovel.domain.knowledge import KnowledgeState, Scalar
from anovel.genre.registry import ProjectGenreBinding


class PlanningError(ValueError):
    """Malformed, cross-project or unsupported planning input."""


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise PlanningError(f"{field} must be nonempty text")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise PlanningError(f"{field} must be valid Unicode") from error
    return value


def _integer(value: object, field: str) -> int:
    if type(value) is not int or value < 1:
        raise PlanningError(f"{field} must be a strict positive integer")
    return value


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise PlanningError("a lowercase SHA256 identity is required")
    return value


def _id(value: object) -> EntityId:
    if type(value) is not EntityId:
        raise PlanningError("an exact EntityId is required")
    _text(value.project, "project")
    _text(value.local_id, "local ID")
    return value


def _ids(value: object, field: str) -> tuple[EntityId, ...]:
    if type(value) is not tuple or any(type(v) is not EntityId for v in value):
        raise PlanningError(f"{field} must be an immutable EntityId tuple")
    items = cast(tuple[EntityId, ...], value)
    if len(set(items)) != len(items):
        raise PlanningError(f"{field} identities repeat")
    for item in items:
        _id(item)
    return items


def _strings(value: object, field: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise PlanningError(f"{field} must be immutable text tuple")
    return tuple(_text(v, field) for v in value)


def _members[T](value: object, cls: type[T], field: str) -> tuple[T, ...]:
    if type(value) is not tuple or any(type(v) is not cls for v in value):
        raise PlanningError(f"{field} needs exact immutable typed members")
    return cast(tuple[T, ...], value)


def _scope(project: str, values: tuple[EntityId, ...] | frozenset[EntityId]) -> None:
    if any(_id(v).project != project for v in values):
        raise PlanningError("planning references cross project")


def _record(value: object, kind: str, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields | {"kind", "schema_version"}:
        raise PlanningError(f"{kind} fields must be exact and closed")
    row = cast(dict[str, object], value)
    if row["kind"] != kind or row["schema_version"] != "1.0":
        raise PlanningError(f"unsupported {kind} format")
    return row


def _array(value: object) -> list[object]:
    if type(value) is not list:
        raise PlanningError("serialized members must be arrays")
    return cast(list[object], value)


def _data(kind: str, fields: dict[str, object]) -> dict[str, object]:
    return {"kind": kind, "schema_version": "1.0", **fields}


class _Value(ABC):
    __slots__ = ()

    @abstractmethod
    def to_dict(self) -> dict[str, object]: ...

    @property
    def content_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @property
    def content_hash(self) -> str:
        return sha256(self.content_bytes).hexdigest()


class TransitionKind(str, Enum):
    SET_FACT = "SET_FACT"
    MARK_UNKNOWN = "MARK_UNKNOWN"
    RETRACT_FACT = "RETRACT_FACT"
    NO_CHANGE = "NO_CHANGE"


def _transition(operation: object, value: Scalar | None) -> None:
    if type(operation) is not TransitionKind:
        raise PlanningError("only registered TransitionKind operations are supported")
    if operation is TransitionKind.SET_FACT:
        FactState.known(cast(Scalar, value))
    elif value is not None:
        raise PlanningError("only SET_FACT carries a value")


@dataclass(frozen=True, slots=True)
class RequiredTransition(_Value):
    target_id: EntityId
    operation: TransitionKind
    value: Scalar | None = None
    expected_state: FactState | None = None
    path: ClassVar[FactPath] = FactPath.VALUE
    version: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        _id(self.target_id)
        _transition(self.operation, self.value)
        if (
            self.expected_state is not None
            and type(self.expected_state) is not FactState
        ):
            raise PlanningError("expected_state must be an exact FactState or absent")

    def to_dict(self) -> dict[str, object]:
        return _data(
            "REQUIRED_TRANSITION",
            {
                "target_id": self.target_id.to_dict(),
                "operation": self.operation.value,
                "operation_version": self.version,
                "path": self.path.value,
                "expected_state": None
                if self.expected_state is None
                else self.expected_state.to_dict(),
                **(
                    {"value": self.value}
                    if self.operation is TransitionKind.SET_FACT
                    else {}
                ),
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> RequiredTransition:
        has_value = type(value) is dict and value.get("operation") == "SET_FACT"
        row = _record(
            value,
            "REQUIRED_TRANSITION",
            {"target_id", "operation", "operation_version", "path", "expected_state"}
            | ({"value"} if has_value else set()),
        )
        if row["operation_version"] != "1.0" or row["path"] != FactPath.VALUE.value:
            raise PlanningError("unregistered transition path or operation version")
        return cls(
            EntityId.from_dict(row["target_id"]),
            TransitionKind(_text(row["operation"], "operation")),
            cast(Scalar | None, row.get("value")),
            None
            if row["expected_state"] is None
            else FactState.from_dict(row["expected_state"]),
        )


@dataclass(frozen=True, slots=True)
class ForbiddenTransition(_Value):
    target_id: EntityId
    operation: TransitionKind
    value: Scalar | None = None
    path: ClassVar[FactPath] = FactPath.VALUE
    version: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        _id(self.target_id)
        _transition(self.operation, self.value)

    def to_dict(self) -> dict[str, object]:
        return _data(
            "FORBIDDEN_TRANSITION",
            {
                "target_id": self.target_id.to_dict(),
                "operation": self.operation.value,
                "operation_version": self.version,
                "path": self.path.value,
                **(
                    {"value": self.value}
                    if self.operation is TransitionKind.SET_FACT
                    else {}
                ),
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> ForbiddenTransition:
        has_value = type(value) is dict and value.get("operation") == "SET_FACT"
        row = _record(
            value,
            "FORBIDDEN_TRANSITION",
            {"target_id", "operation", "operation_version", "path"}
            | ({"value"} if has_value else set()),
        )
        if row["operation_version"] != "1.0" or row["path"] != FactPath.VALUE.value:
            raise PlanningError("unregistered transition path or operation version")
        return cls(
            EntityId.from_dict(row["target_id"]),
            TransitionKind(_text(row["operation"], "operation")),
            cast(Scalar | None, row.get("value")),
        )


@dataclass(frozen=True, slots=True)
class KnowledgeBoundary(_Value):
    actor_id: EntityId
    must_know: tuple[EntityId, ...] = ()
    must_not_know: tuple[EntityId, ...] = ()

    def __post_init__(self) -> None:
        _id(self.actor_id)
        _ids(self.must_know, "must_know")
        _ids(self.must_not_know, "must_not_know")
        _scope(self.actor_id.project, (*self.must_know, *self.must_not_know))
        if set(self.must_know) & set(self.must_not_know):
            raise PlanningError("a knowledge boundary contradicts itself")

    def to_dict(self) -> dict[str, object]:
        return _data(
            "KNOWLEDGE_BOUNDARY",
            {
                "actor_id": self.actor_id.to_dict(),
                "must_know": [v.to_dict() for v in self.must_know],
                "must_not_know": [v.to_dict() for v in self.must_not_know],
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> KnowledgeBoundary:
        row = _record(
            value, "KNOWLEDGE_BOUNDARY", {"actor_id", "must_know", "must_not_know"}
        )
        return cls(
            EntityId.from_dict(row["actor_id"]),
            tuple(EntityId.from_dict(v) for v in _array(row["must_know"])),
            tuple(EntityId.from_dict(v) for v in _array(row["must_not_know"])),
        )


@dataclass(frozen=True, slots=True)
class RevealBoundary(_Value):
    fact_id: EntityId
    not_before: NarrativePosition

    def __post_init__(self) -> None:
        _id(self.fact_id)
        if type(self.not_before) is not NarrativePosition:
            raise PlanningError("reveal boundary needs an exact narrative position")

    def to_dict(self) -> dict[str, object]:
        return _data(
            "REVEAL_BOUNDARY",
            {
                "fact_id": self.fact_id.to_dict(),
                "not_before": self.not_before.to_dict(),
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> RevealBoundary:
        row = _record(value, "REVEAL_BOUNDARY", {"fact_id", "not_before"})
        return cls(
            EntityId.from_dict(row["fact_id"]),
            NarrativePosition.from_dict(row["not_before"]),
        )


@dataclass(frozen=True, slots=True)
class ScenePlan(_Value):
    id: EntityId
    order: int
    purpose: str
    required: tuple[RequiredTransition, ...] = ()
    forbidden: tuple[ForbiddenTransition, ...] = ()
    protected_fact_ids: tuple[EntityId, ...] = ()
    intent_ids: tuple[EntityId, ...] = ()
    preferences: tuple[str, ...] = ()
    knowledge_boundaries: tuple[KnowledgeBoundary, ...] = ()
    reveal_fact_ids: tuple[EntityId, ...] = ()

    def __post_init__(self) -> None:
        _id(self.id)
        _integer(self.order, "scene order")
        _text(self.purpose, "purpose")
        _members(self.required, RequiredTransition, "required")
        _members(self.forbidden, ForbiddenTransition, "forbidden")
        _ids(self.protected_fact_ids, "protected facts")
        _ids(self.intent_ids, "intents")
        _strings(self.preferences, "preferences")
        _members(self.knowledge_boundaries, KnowledgeBoundary, "knowledge boundaries")
        _ids(self.reveal_fact_ids, "reveals")
        refs = [v.target_id for v in self.required] + [
            v.target_id for v in self.forbidden
        ]
        refs += [*self.protected_fact_ids, *self.intent_ids, *self.reveal_fact_ids]
        for boundary in self.knowledge_boundaries:
            refs += [boundary.actor_id, *boundary.must_know, *boundary.must_not_know]
        _scope(self.id.project, tuple(refs))

    def to_dict(self) -> dict[str, object]:
        return _data(
            "SCENE_PLAN",
            {
                "id": self.id.to_dict(),
                "order": self.order,
                "purpose": self.purpose,
                "required": [v.to_dict() for v in self.required],
                "forbidden": [v.to_dict() for v in self.forbidden],
                "protected_fact_ids": [v.to_dict() for v in self.protected_fact_ids],
                "intent_ids": [v.to_dict() for v in self.intent_ids],
                "preferences": list(self.preferences),
                "knowledge_boundaries": [
                    v.to_dict() for v in self.knowledge_boundaries
                ],
                "reveal_fact_ids": [v.to_dict() for v in self.reveal_fact_ids],
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> ScenePlan:
        row = _record(
            value,
            "SCENE_PLAN",
            {
                "id",
                "order",
                "purpose",
                "required",
                "forbidden",
                "protected_fact_ids",
                "intent_ids",
                "preferences",
                "knowledge_boundaries",
                "reveal_fact_ids",
            },
        )
        return cls(
            EntityId.from_dict(row["id"]),
            _integer(row["order"], "order"),
            _text(row["purpose"], "purpose"),
            tuple(RequiredTransition.from_dict(v) for v in _array(row["required"])),
            tuple(ForbiddenTransition.from_dict(v) for v in _array(row["forbidden"])),
            tuple(EntityId.from_dict(v) for v in _array(row["protected_fact_ids"])),
            tuple(EntityId.from_dict(v) for v in _array(row["intent_ids"])),
            tuple(_text(v, "preference") for v in _array(row["preferences"])),
            tuple(
                KnowledgeBoundary.from_dict(v)
                for v in _array(row["knowledge_boundaries"])
            ),
            tuple(EntityId.from_dict(v) for v in _array(row["reveal_fact_ids"])),
        )


CONTINUATION_MODES = frozenset({"DIRECT", "RECAP", "FLASHBACK", "ALTERNATE_VIEWPOINT"})


@dataclass(frozen=True, slots=True)
class ChapterPlan(_Value):
    id: EntityId
    number: int
    purpose: str
    scenes: tuple[ScenePlan, ...]
    continuation_mode: str = "DIRECT"
    start_intent: str = "Continue from the explicitly bound preceding state."

    def __post_init__(self) -> None:
        _id(self.id)
        _integer(self.number, "chapter number")
        _text(self.purpose, "purpose")
        _members(self.scenes, ScenePlan, "scenes")
        if (
            not self.scenes
            or len({v.id for v in self.scenes}) != len(self.scenes)
            or sorted(v.order for v in self.scenes)
            != list(range(1, len(self.scenes) + 1))
        ):
            raise PlanningError("chapter needs unique consecutive scenes from one")
        _scope(self.id.project, tuple(v.id for v in self.scenes))
        if (
            type(self.continuation_mode) is not str
            or self.continuation_mode not in CONTINUATION_MODES
        ):
            raise PlanningError("unsupported explicit continuation mode")
        _text(self.start_intent, "start intent")
        object.__setattr__(
            self, "scenes", tuple(sorted(self.scenes, key=lambda v: v.order))
        )

    def to_dict(self) -> dict[str, object]:
        return _data(
            "CHAPTER_PLAN",
            {
                "id": self.id.to_dict(),
                "number": self.number,
                "purpose": self.purpose,
                "scenes": [v.to_dict() for v in self.scenes],
                "continuation_mode": self.continuation_mode,
                "start_intent": self.start_intent,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> ChapterPlan:
        row = _record(
            value,
            "CHAPTER_PLAN",
            {"id", "number", "purpose", "scenes", "continuation_mode", "start_intent"},
        )
        return cls(
            EntityId.from_dict(row["id"]),
            _integer(row["number"], "number"),
            _text(row["purpose"], "purpose"),
            tuple(ScenePlan.from_dict(v) for v in _array(row["scenes"])),
            _text(row["continuation_mode"], "continuation mode"),
            _text(row["start_intent"], "start intent"),
        )


@dataclass(frozen=True, slots=True)
class ArcPlan(_Value):
    id: EntityId
    purpose: str
    chapters: tuple[ChapterPlan, ...]

    def __post_init__(self) -> None:
        _id(self.id)
        _text(self.purpose, "purpose")
        _members(self.chapters, ChapterPlan, "chapters")
        if (
            not self.chapters
            or len({v.id for v in self.chapters}) != len(self.chapters)
            or len({v.number for v in self.chapters}) != len(self.chapters)
        ):
            raise PlanningError("arc needs unique chapter identities and numbers")
        _scope(self.id.project, tuple(v.id for v in self.chapters))
        object.__setattr__(
            self, "chapters", tuple(sorted(self.chapters, key=lambda v: v.number))
        )

    def to_dict(self) -> dict[str, object]:
        return _data(
            "ARC_PLAN",
            {
                "id": self.id.to_dict(),
                "purpose": self.purpose,
                "chapters": [v.to_dict() for v in self.chapters],
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> ArcPlan:
        row = _record(value, "ARC_PLAN", {"id", "purpose", "chapters"})
        return cls(
            EntityId.from_dict(row["id"]),
            _text(row["purpose"], "purpose"),
            tuple(ChapterPlan.from_dict(v) for v in _array(row["chapters"])),
        )


@dataclass(frozen=True, slots=True)
class SeriesVision(_Value):
    id: EntityId
    premise: str
    protagonist_goal: str
    arcs: tuple[ArcPlan, ...]

    def __post_init__(self) -> None:
        _id(self.id)
        _text(self.premise, "premise")
        _text(self.protagonist_goal, "protagonist goal")
        _members(self.arcs, ArcPlan, "arcs")
        if not self.arcs:
            raise PlanningError("vision needs at least one concrete arc")
        ids = [
            self.id,
            *(v.id for v in self.arcs),
            *(v.id for v in self.chapters),
            *(s.id for c in self.chapters for s in c.scenes),
        ]
        if len(set(ids)) != len(ids):
            raise PlanningError("plan identities repeat across hierarchy")
        _scope(self.id.project, tuple(ids))
        if sorted(v.number for v in self.chapters) != list(
            range(1, len(self.chapters) + 1)
        ):
            raise PlanningError("vision chapter numbers must be consecutive from one")

    @property
    def project(self) -> str:
        return self.id.project

    @property
    def chapters(self) -> tuple[ChapterPlan, ...]:
        return tuple(
            sorted(
                (v for arc in self.arcs for v in arc.chapters), key=lambda v: v.number
            )
        )

    def chapter(self, chapter_id: EntityId) -> ChapterPlan:
        _scope(self.project, (_id(chapter_id),))
        found = next((v for v in self.chapters if v.id == chapter_id), None)
        if found is None:
            raise PlanningError("chapter is not registered in this vision")
        return found

    def to_dict(self) -> dict[str, object]:
        return _data(
            "SERIES_VISION",
            {
                "id": self.id.to_dict(),
                "premise": self.premise,
                "protagonist_goal": self.protagonist_goal,
                "arcs": [v.to_dict() for v in self.arcs],
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> SeriesVision:
        row = _record(
            value, "SERIES_VISION", {"id", "premise", "protagonist_goal", "arcs"}
        )
        return cls(
            EntityId.from_dict(row["id"]),
            _text(row["premise"], "premise"),
            _text(row["protagonist_goal"], "protagonist goal"),
            tuple(ArcPlan.from_dict(v) for v in _array(row["arcs"])),
        )


@dataclass(frozen=True, slots=True)
class StoryFixture(_Value):
    fixture_id: EntityId
    partition: str
    pack_binding: ProjectGenreBinding
    root_seed: RootSeed
    knowledge_bytes: bytes
    reader_boundaries: tuple[RevealBoundary, ...]
    vision: SeriesVision
    review_status: str = "DRAFT"
    review_ref: str | None = None
    world_boundaries: tuple[str, ...] = ()
    conflict_engine: str = ""
    choice_costs: tuple[str, ...] = ()
    opponent_adaptation: tuple[str, ...] = ()
    reader_promises: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _id(self.fixture_id)
        if type(self.partition) is not str or self.partition not in {
            "development",
            "holdout",
        }:
            raise PlanningError("fixture partition must be development or holdout")
        if (
            type(self.pack_binding) is not ProjectGenreBinding
            or type(self.root_seed) is not RootSeed
            or type(self.vision) is not SeriesVision
        ):
            raise PlanningError(
                "fixture needs exact registered Pack/root/vision values"
            )
        if {
            self.project,
            self.pack_binding.project,
            self.root_seed.project,
            self.vision.project,
        } != {self.project}:
            raise PlanningError("fixture inputs cross project")
        if type(self.knowledge_bytes) is not bytes or not self.knowledge_bytes:
            raise PlanningError("fixture knowledge needs complete canonical bytes")
        knowledge = self.knowledge
        if (
            knowledge.project != self.project
            or canonical_bytes(knowledge.to_dict()) != self.knowledge_bytes
        ):
            raise PlanningError(
                "knowledge source must be exact same-project canonical export"
            )
        entity_ids = {v.id for v in self.root_seed.entities}
        facts = {v.id: v for v in self.root_seed.facts}
        if any(v.id not in entity_ids for v in knowledge.characters) or any(
            facts.get(v.id) != v for v in knowledge.facts
        ):
            raise PlanningError(
                "initial knowledge facts and characters must match fixture root"
            )
        if any(v.proposition.subject not in entity_ids for v in knowledge.beliefs):
            raise PlanningError("belief subject is not a fixture root entity")
        _members(self.reader_boundaries, RevealBoundary, "reader boundaries")
        if len({v.fact_id for v in self.reader_boundaries}) != len(
            self.reader_boundaries
        ) or any(v.fact_id not in facts for v in self.reader_boundaries):
            raise PlanningError(
                "reveal boundaries must uniquely reference actual root facts"
            )
        for binding in self.root_seed.extensions:
            if binding.pack_bytes != canonical_bytes(self.pack_binding.to_dict()):
                raise PlanningError("root retains a different Pack binding")
        if type(self.review_status) is not str or self.review_status not in {
            "DRAFT",
            "APPROVED",
        }:
            raise PlanningError("unknown fixture review status")
        if self.review_status == "DRAFT" and self.review_ref is not None:
            raise PlanningError("DRAFT is not an approval record")
        if self.review_status == "APPROVED":
            _text(self.review_ref, "human review reference")
        for name in (
            "world_boundaries",
            "choice_costs",
            "opponent_adaptation",
            "reader_promises",
        ):
            _strings(getattr(self, name), name)
        if type(self.conflict_engine) is not str:
            raise PlanningError("conflict engine must be text")
        canonical_bytes(self._payload())

    @property
    def project(self) -> str:
        return self.fixture_id.project

    @property
    def knowledge(self) -> KnowledgeState:
        return KnowledgeState.from_dict(decode_canonical(self.knowledge_bytes))

    def _payload(self) -> dict[str, object]:
        return {
            "fixture_id": self.fixture_id.to_dict(),
            "partition": self.partition,
            "pack_binding": self.pack_binding.to_dict(),
            "root_seed": self.root_seed.to_dict(),
            "knowledge_base64": b64encode(self.knowledge_bytes).decode("ascii"),
            "reader_boundaries": [v.to_dict() for v in self.reader_boundaries],
            "vision": self.vision.to_dict(),
            "world_boundaries": list(self.world_boundaries),
            "conflict_engine": self.conflict_engine,
            "choice_costs": list(self.choice_costs),
            "opponent_adaptation": list(self.opponent_adaptation),
            "reader_promises": list(self.reader_promises),
        }

    @property
    def content_hash(self) -> str:
        """Freeze reviewed story content without a review-ref self-reference."""
        return sha256(
            canonical_bytes(_data("STORY_FIXTURE_CONTENT", self._payload()))
        ).hexdigest()

    @property
    def snapshot_hash(self) -> str:
        return sha256(self.content_bytes).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return _data(
            "STORY_FIXTURE",
            {
                **self._payload(),
                "review_status": self.review_status,
                "review_ref": self.review_ref,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> StoryFixture:
        row = _record(
            value,
            "STORY_FIXTURE",
            {
                "fixture_id",
                "partition",
                "pack_binding",
                "root_seed",
                "knowledge_base64",
                "reader_boundaries",
                "vision",
                "review_status",
                "review_ref",
                "world_boundaries",
                "conflict_engine",
                "choice_costs",
                "opponent_adaptation",
                "reader_promises",
            },
        )
        encoded = _text(row["knowledge_base64"], "knowledge bytes")
        try:
            raw = b64decode(encoded, validate=True)
        except (ValueError, Base64Error) as error:
            raise PlanningError("invalid knowledge base64") from error
        if b64encode(raw).decode("ascii") != encoded:
            raise PlanningError("noncanonical knowledge base64")
        return cls(
            EntityId.from_dict(row["fixture_id"]),
            _text(row["partition"], "partition"),
            ProjectGenreBinding.from_dict(row["pack_binding"]),
            RootSeed.from_dict(row["root_seed"]),
            raw,
            tuple(
                RevealBoundary.from_dict(v) for v in _array(row["reader_boundaries"])
            ),
            SeriesVision.from_dict(row["vision"]),
            _text(row["review_status"], "review status"),
            None
            if row["review_ref"] is None
            else _text(row["review_ref"], "review ref"),
            tuple(_text(v, "world boundary") for v in _array(row["world_boundaries"])),
            cast(str, row["conflict_engine"]),
            tuple(_text(v, "choice cost") for v in _array(row["choice_costs"])),
            tuple(_text(v, "adaptation") for v in _array(row["opponent_adaptation"])),
            tuple(_text(v, "reader promise") for v in _array(row["reader_promises"])),
        )
