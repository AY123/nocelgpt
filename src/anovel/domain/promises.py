"""Narrative promises with explicit windows and evidence-bound resolutions.

Resolution records an application's structured judgement, not proof that prose
fulfilled a literary promise. This projection never commits Canon or knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from anovel.domain.events import Event, NarrativePosition, Timeline
from anovel.domain.identity import EntityId, _record, _text


class PromiseValidationError(ValueError):
    """Invalid promise data at the domain boundary."""


class WindowKind(Enum):
    UNKNOWN = "UNKNOWN"
    KNOWN = "KNOWN"


class WindowResult(Enum):
    EARLY = "EARLY"
    IN_WINDOW = "IN_WINDOW"
    LATE = "LATE"
    UNKNOWN = "UNKNOWN"


class PromiseStatus(Enum):
    OPEN = "OPEN"
    PAID = "PAID"
    BROKEN = "BROKEN"
    ABANDONED = "ABANDONED"


def _position(value: object, name: str) -> NarrativePosition:
    if not isinstance(value, NarrativePosition):
        raise PromiseValidationError(f"{name} must be a NarrativePosition")
    return value


def _same_project(value: object, project: str, name: str) -> EntityId:
    if not isinstance(value, EntityId):
        raise PromiseValidationError(f"{name} must be an EntityId")
    if value.project != project:
        raise PromiseValidationError(f"{name} belongs to a different project")
    return value


def _constant(value: object, expected: str, name: str) -> None:
    if not isinstance(value, str) or value != expected:
        raise PromiseValidationError(f"{name} must be {expected}")


@dataclass(frozen=True, slots=True)
class PromiseWindow:
    """Inclusive reader-facing window; UNKNOWN has no fabricated bounds."""

    kind: WindowKind
    start: NarrativePosition | None = None
    end: NarrativePosition | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, WindowKind):
            raise PromiseValidationError("kind must be a WindowKind")
        if self.kind is WindowKind.UNKNOWN:
            if self.start is not None or self.end is not None:
                raise PromiseValidationError("UNKNOWN window must not contain bounds")
            return
        start = _position(self.start, "start")
        end = _position(self.end, "end")
        if start > end:
            raise PromiseValidationError("window start must not follow its end")

    @classmethod
    def unknown(cls) -> PromiseWindow:
        return cls(WindowKind.UNKNOWN)

    @classmethod
    def between(cls, start: NarrativePosition, end: NarrativePosition) -> PromiseWindow:
        return cls(WindowKind.KNOWN, start, end)

    def classify(self, position: NarrativePosition) -> WindowResult:
        checked = _position(position, "position")
        if self.kind is WindowKind.UNKNOWN:
            return WindowResult.UNKNOWN
        assert self.start is not None and self.end is not None
        if checked < self.start:
            return WindowResult.EARLY
        if checked > self.end:
            return WindowResult.LATE
        return WindowResult.IN_WINDOW

    @classmethod
    def from_dict(cls, value: object) -> PromiseWindow:
        record = _record(
            value,
            required={"kind", "start", "end"},
            optional=set(),
            field="promise window",
        )
        try:
            kind = WindowKind(_text(record["kind"], "kind"))
        except ValueError as error:
            raise PromiseValidationError("unsupported window kind") from error
        return cls(
            kind,
            None
            if record["start"] is None
            else NarrativePosition.from_dict(record["start"]),
            None
            if record["end"] is None
            else NarrativePosition.from_dict(record["end"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "start": None if self.start is None else self.start.to_dict(),
            "end": None if self.end is None else self.end.to_dict(),
        }


@dataclass(frozen=True, slots=True, init=False)
class Promise:
    """Reader-facing commitment, separate from character goals or intentions.

    New instances are OPEN. Callers adopt a returned resolved value explicitly;
    resolving two independent OPEN values is not a global single-commit protocol.
    """

    id: EntityId
    description: str
    opened_at: NarrativePosition
    window: PromiseWindow
    related_entities: frozenset[EntityId] = frozenset()
    evidence_ref: str = field(kw_only=True)
    status: PromiseStatus = field(default=PromiseStatus.OPEN, init=False)
    resolution_event: Event | None = field(default=None, init=False)
    resolution_evidence_ref: str | None = field(default=None, init=False)

    def __init__(
        self,
        id: EntityId,
        description: str,
        opened_at: NarrativePosition,
        window: PromiseWindow,
        related_entities: set[EntityId] | frozenset[EntityId] = frozenset(),
        *,
        evidence_ref: str,
    ) -> None:
        if not isinstance(related_entities, (set, frozenset)):
            raise PromiseValidationError("related_entities must be a set or frozenset")
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "opened_at", opened_at)
        object.__setattr__(self, "window", window)
        object.__setattr__(self, "related_entities", frozenset(related_entities))
        object.__setattr__(self, "evidence_ref", evidence_ref)
        object.__setattr__(self, "status", PromiseStatus.OPEN)
        object.__setattr__(self, "resolution_event", None)
        object.__setattr__(self, "resolution_evidence_ref", None)
        self.__post_init__()

    def __post_init__(self) -> None:
        if not isinstance(self.id, EntityId):
            raise PromiseValidationError("id must be an EntityId")
        _text(self.description, "description")
        _position(self.opened_at, "opened_at")
        if not isinstance(self.window, PromiseWindow):
            raise PromiseValidationError("window must be a PromiseWindow")
        if self.window.start is not None and self.window.start < self.opened_at:
            raise PromiseValidationError(
                "window must not begin before the promise opens"
            )
        if not isinstance(self.related_entities, frozenset):
            raise PromiseValidationError("related_entities must be a frozenset")
        for related in self.related_entities:
            _same_project(related, self.id.project, "related entity")
        _text(self.evidence_ref, "evidence_ref")

    def window_result(self, position: NarrativePosition) -> WindowResult:
        return self.window.classify(position)

    def _require_open(self) -> None:
        if self.status is not PromiseStatus.OPEN:
            raise PromiseValidationError("a terminal promise cannot transition again")

    def _copy(self) -> Promise:
        return Promise(
            self.id,
            self.description,
            self.opened_at,
            self.window,
            self.related_entities,
            evidence_ref=self.evidence_ref,
        )

    def _resolve(
        self,
        status: PromiseStatus,
        timeline: Timeline,
        event_id: EntityId,
        evidence_ref: str,
    ) -> Promise:
        self._require_open()
        if status not in (PromiseStatus.PAID, PromiseStatus.BROKEN):
            raise PromiseValidationError("event resolution must be PAID or BROKEN")
        if not isinstance(timeline, Timeline):
            raise PromiseValidationError("timeline must be a Timeline")
        checked_id = _same_project(event_id, self.id.project, "resolution event")
        checked_evidence = _text(evidence_ref, "resolution_evidence_ref")
        event = timeline.require_occurred(checked_id)
        if event.narrative_position < self.opened_at:
            raise PromiseValidationError(
                "resolution event must not precede promise opening"
            )
        resolved = self._copy()
        object.__setattr__(resolved, "status", status)
        object.__setattr__(resolved, "resolution_event", event)
        object.__setattr__(resolved, "resolution_evidence_ref", checked_evidence)
        return resolved

    def pay_off(
        self, timeline: Timeline, event_id: EntityId, evidence_ref: str
    ) -> Promise:
        return self._resolve(PromiseStatus.PAID, timeline, event_id, evidence_ref)

    def break_promise(
        self, timeline: Timeline, event_id: EntityId, evidence_ref: str
    ) -> Promise:
        return self._resolve(PromiseStatus.BROKEN, timeline, event_id, evidence_ref)

    def abandon(self, evidence_ref: str) -> Promise:
        self._require_open()
        checked_evidence = _text(evidence_ref, "resolution_evidence_ref")
        resolved = self._copy()
        object.__setattr__(resolved, "status", PromiseStatus.ABANDONED)
        object.__setattr__(resolved, "resolution_evidence_ref", checked_evidence)
        return resolved

    @classmethod
    def from_dict(cls, value: object, *, timeline: Timeline | None = None) -> Promise:
        record = _record(
            value,
            required={
                "kind",
                "schema_version",
                "id",
                "description",
                "opened_at",
                "window",
                "related_entities",
                "evidence_ref",
                "status",
                "resolution_event",
                "resolution_evidence_ref",
            },
            optional=set(),
            field="promise",
        )
        _constant(record["kind"], "PROMISE", "kind")
        _constant(record["schema_version"], "1.0", "schema_version")
        raw_related = record["related_entities"]
        if not isinstance(raw_related, list):
            raise PromiseValidationError("related_entities must be an array")
        related = tuple(EntityId.from_dict(item) for item in raw_related)
        if len(set(related)) != len(related):
            raise PromiseValidationError("related_entities must be unique")
        promise = cls(
            EntityId.from_dict(record["id"]),
            _text(record["description"], "description"),
            NarrativePosition.from_dict(record["opened_at"]),
            PromiseWindow.from_dict(record["window"]),
            frozenset(related),
            evidence_ref=_text(record["evidence_ref"], "evidence_ref"),
        )
        try:
            status = PromiseStatus(_text(record["status"], "status"))
        except ValueError as error:
            raise PromiseValidationError("unsupported promise status") from error
        event_payload = record["resolution_event"]
        evidence = record["resolution_evidence_ref"]
        if status is PromiseStatus.OPEN:
            if event_payload is not None or evidence is not None:
                raise PromiseValidationError(
                    "OPEN promise must not contain resolution data"
                )
            return promise
        checked_evidence = _text(evidence, "resolution_evidence_ref")
        if status is PromiseStatus.ABANDONED:
            if event_payload is not None:
                raise PromiseValidationError(
                    "ABANDONED promise must not contain an event"
                )
            return promise.abandon(checked_evidence)
        if timeline is None:
            raise PromiseValidationError(
                "event-bound terminal restoration requires a timeline"
            )
        if not isinstance(timeline, Timeline):
            raise PromiseValidationError("timeline must be a Timeline")
        event = Event.from_dict(event_payload)
        _same_project(event.id, promise.id.project, "resolution event")
        registered = timeline.require_occurred(event.id)
        if registered.to_dict() != event.to_dict():
            raise PromiseValidationError(
                "resolution event does not match the registered event"
            )
        return promise._resolve(status, timeline, event.id, checked_evidence)

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "PROMISE",
            "schema_version": "1.0",
            "id": self.id.to_dict(),
            "description": self.description,
            "opened_at": self.opened_at.to_dict(),
            "window": self.window.to_dict(),
            "related_entities": [
                entity.to_dict()
                for entity in sorted(
                    self.related_entities,
                    key=lambda item: (item.project, item.local_id),
                )
            ],
            "evidence_ref": self.evidence_ref,
            "status": self.status.value,
            "resolution_event": None
            if self.resolution_event is None
            else self.resolution_event.to_dict(),
            "resolution_evidence_ref": self.resolution_evidence_ref,
        }
