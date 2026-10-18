"""Project-scoped event claims and explicit narrative/story-time ordering.

These in-memory records validate supplied claims and their references. They do
not verify prose, execute intentions, update knowledge or commit Canon.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from anovel.domain.identity import EntityId, _record, _text


def _id(value: object, field: str) -> EntityId:
    if not isinstance(value, EntityId):
        raise ValueError(f"{field} must be an EntityId")
    return value


def _integer(value: object, field: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{field} must be a strict integer")
    return value


def _array(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    return value


def _enum[EnumT: Enum](value: object, enum_type: type[EnumT], field: str) -> EnumT:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an enum string")
    try:
        return enum_type(value)
    except ValueError as error:
        raise ValueError(f"unknown {field}") from error


class TimeKind(Enum):
    UNKNOWN = "UNKNOWN"
    EXACT = "EXACT"
    RANGE = "RANGE"


class Occurrence(Enum):
    OCCURRED = "OCCURRED"
    NOT_OCCURRED = "NOT_OCCURRED"
    UNKNOWN = "UNKNOWN"


class TemporalRelation(Enum):
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    SAME_TIME = "SAME_TIME"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True, order=True)
class NarrativePosition:
    """Primary reader-facing anchor, independent of fictional story time."""

    chapter: int
    order: int

    def __post_init__(self) -> None:
        if _integer(self.chapter, "chapter") < 1:
            raise ValueError("chapter must be positive")
        if _integer(self.order, "order") < 1:
            raise ValueError("order must be positive")

    @classmethod
    def from_dict(cls, value: object) -> NarrativePosition:
        record = _record(
            value,
            required={"chapter", "order"},
            optional=set(),
            field="narrative position",
        )
        return cls(
            _integer(record["chapter"], "chapter"),
            _integer(record["order"], "order"),
        )

    def to_dict(self) -> dict[str, int]:
        return {"chapter": self.chapter, "order": self.order}


@dataclass(frozen=True, slots=True)
class StoryTime:
    """Possible occurrence instant on a project-local logical integer clock.

    RANGE describes uncertainty about an instant, not an event's duration.
    Unknown bounds therefore never imply either infinite time or simultaneity.
    """

    kind: TimeKind
    earliest: int | None = None
    latest: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, TimeKind):
            raise ValueError("kind must be a TimeKind")
        if self.kind is TimeKind.UNKNOWN:
            if self.earliest is not None or self.latest is not None:
                raise ValueError("unknown story time cannot have bounds")
            return
        first = _integer(self.earliest, "earliest")
        last = _integer(self.latest, "latest")
        if self.kind is TimeKind.EXACT and first != last:
            raise ValueError("exact story time must have equal bounds")
        if self.kind is TimeKind.RANGE and first >= last:
            raise ValueError("story time range must have increasing bounds")

    @classmethod
    def unknown(cls) -> StoryTime:
        return cls(TimeKind.UNKNOWN)

    @classmethod
    def exact(cls, instant: int) -> StoryTime:
        return cls(TimeKind.EXACT, instant, instant)

    @classmethod
    def between(cls, earliest: int, latest: int) -> StoryTime:
        return cls(TimeKind.RANGE, earliest, latest)

    @classmethod
    def from_dict(cls, value: object) -> StoryTime:
        record = _record(
            value,
            required={"kind", "earliest", "latest"},
            optional=set(),
            field="story time",
        )
        first = record["earliest"]
        last = record["latest"]
        return cls(
            _enum(record["kind"], TimeKind, "story time kind"),
            None if first is None else _integer(first, "earliest"),
            None if last is None else _integer(last, "latest"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "earliest": self.earliest,
            "latest": self.latest,
        }


@dataclass(frozen=True, slots=True, init=False)
class Event:
    """A stable event claim with an explicit, never inferred occurrence state."""

    id: EntityId
    event_type: str
    narrative_position: NarrativePosition
    story_time: StoryTime
    occurrence: Occurrence
    evidence_ref: str
    description: str
    participants: frozenset[EntityId]
    location: EntityId | None

    def __init__(
        self,
        id: EntityId,
        event_type: str,
        narrative_position: NarrativePosition,
        story_time: StoryTime,
        occurrence: Occurrence,
        *,
        evidence_ref: str,
        description: str = "",
        participants: set[EntityId] | frozenset[EntityId] = frozenset(),
        location: EntityId | None = None,
    ) -> None:
        checked_id = _id(id, "id")
        _text(event_type, "event_type")
        _text(evidence_ref, "evidence_ref")
        if not isinstance(narrative_position, NarrativePosition):
            raise ValueError("narrative_position must be a NarrativePosition")
        if not isinstance(story_time, StoryTime):
            raise ValueError("story_time must be a StoryTime")
        if not isinstance(occurrence, Occurrence):
            raise ValueError("occurrence must be an Occurrence")
        if not isinstance(description, str):
            raise ValueError("description must be a string")
        if not isinstance(participants, (set, frozenset)):
            raise ValueError("participants must be a set or frozenset")
        checked_participants = frozenset(
            _id(item, "participant") for item in participants
        )
        if any(item.project != checked_id.project for item in checked_participants):
            raise ValueError("event participants belong to a different project")
        if (
            location is not None
            and _id(location, "location").project != checked_id.project
        ):
            raise ValueError("event location belongs to a different project")
        object.__setattr__(self, "id", checked_id)
        object.__setattr__(self, "event_type", event_type)
        object.__setattr__(self, "narrative_position", narrative_position)
        object.__setattr__(self, "story_time", story_time)
        object.__setattr__(self, "occurrence", occurrence)
        object.__setattr__(self, "evidence_ref", evidence_ref)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "participants", checked_participants)
        object.__setattr__(self, "location", location)

    @classmethod
    def from_dict(cls, value: object) -> Event:
        record = _record(
            value,
            required={
                "kind",
                "schema_version",
                "id",
                "event_type",
                "narrative_position",
                "story_time",
                "occurrence",
                "evidence_ref",
                "description",
                "participants",
                "location",
            },
            optional=set(),
            field="event",
        )
        if record["kind"] != "EVENT" or record["schema_version"] != "1.0":
            raise ValueError("unsupported event kind or schema_version")
        participant_values = _array(record["participants"], "participants")
        participants = frozenset(
            EntityId.from_dict(item) for item in participant_values
        )
        if len(participants) != len(participant_values):
            raise ValueError("participants must be unique")
        location = record["location"]
        description = record["description"]
        if not isinstance(description, str):
            raise ValueError("description must be a string")
        return cls(
            EntityId.from_dict(record["id"]),
            _text(record["event_type"], "event_type"),
            NarrativePosition.from_dict(record["narrative_position"]),
            StoryTime.from_dict(record["story_time"]),
            _enum(record["occurrence"], Occurrence, "occurrence"),
            evidence_ref=_text(record["evidence_ref"], "evidence_ref"),
            description=description,
            participants=participants,
            location=None if location is None else EntityId.from_dict(location),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "EVENT",
            "schema_version": "1.0",
            "id": self.id.to_dict(),
            "event_type": self.event_type,
            "narrative_position": self.narrative_position.to_dict(),
            "story_time": self.story_time.to_dict(),
            "occurrence": self.occurrence.value,
            "evidence_ref": self.evidence_ref,
            "description": self.description,
            "participants": [
                item.to_dict() for item in sorted(self.participants, key=str)
            ],
            "location": None if self.location is None else self.location.to_dict(),
        }


def _relation(first: StoryTime, second: StoryTime) -> TemporalRelation:
    if first.kind is TimeKind.UNKNOWN or second.kind is TimeKind.UNKNOWN:
        return TemporalRelation.UNKNOWN
    first_earliest = _integer(first.earliest, "earliest")
    first_latest = _integer(first.latest, "latest")
    second_earliest = _integer(second.earliest, "earliest")
    second_latest = _integer(second.latest, "latest")
    if first_latest < second_earliest:
        return TemporalRelation.BEFORE
    if first_earliest > second_latest:
        return TemporalRelation.AFTER
    if (
        first.kind is TimeKind.EXACT
        and second.kind is TimeKind.EXACT
        and first_earliest == second_earliest
    ):
        return TemporalRelation.SAME_TIME
    return TemporalRelation.UNKNOWN


class Timeline:
    """In-memory event index; no Canon writes or guessed temporal relations."""

    def __init__(self, project: str, events: Iterable[Event] = ()) -> None:
        self._project = _text(project, "project", identifier=True)
        self._events: dict[EntityId, Event] = {}
        self._positions: set[NarrativePosition] = set()
        for event in events:
            self.add_event(event)

    @property
    def project(self) -> str:
        return self._project

    @property
    def events(self) -> tuple[Event, ...]:
        return tuple(sorted(self._events.values(), key=lambda event: str(event.id)))

    def add_event(self, event: Event) -> None:
        if not isinstance(event, Event):
            raise ValueError("event must be an Event, not an intention or plan")
        self._check_id(event.id)
        if event.id in self._events:
            raise ValueError("event identity already registered")
        if event.narrative_position in self._positions:
            raise ValueError("narrative position already registered")
        self._events[event.id] = event
        self._positions.add(event.narrative_position)

    def _check_id(self, event_id: EntityId) -> None:
        if _id(event_id, "event_id").project != self.project:
            raise ValueError("event belongs to a different project")

    def get(self, event_id: EntityId) -> Event | None:
        self._check_id(event_id)
        return self._events.get(event_id)

    def require_occurred(self, event_id: EntityId) -> Event:
        event = self.get(event_id)
        if event is None or event.occurrence is not Occurrence.OCCURRED:
            raise ValueError("event is missing or not confirmed OCCURRED")
        return event

    def narration_order(self) -> tuple[Event, ...]:
        return tuple(
            sorted(self._events.values(), key=lambda event: event.narrative_position)
        )

    def story_relation(
        self, first_id: EntityId, second_id: EntityId
    ) -> TemporalRelation:
        first = self.get(first_id)
        second = self.get(second_id)
        if first is None or second is None:
            raise ValueError("both events must be registered")
        if (
            first.occurrence is not Occurrence.OCCURRED
            or second.occurrence is not Occurrence.OCCURRED
        ):
            return TemporalRelation.UNKNOWN
        return _relation(first.story_time, second.story_time)

    def story_order(self) -> tuple[Event, ...]:
        occurred = [
            event
            for event in self._events.values()
            if event.occurrence is Occurrence.OCCURRED
        ]
        if any(event.story_time.kind is TimeKind.UNKNOWN for event in occurred):
            raise ValueError("unknown story time prevents a determined total order")
        for index, first in enumerate(occurred):
            for second in occurred[index + 1 :]:
                if _relation(first.story_time, second.story_time) not in (
                    TemporalRelation.BEFORE,
                    TemporalRelation.AFTER,
                ):
                    raise ValueError(
                        "events do not have a determined strict total order"
                    )
        return tuple(
            sorted(
                occurred,
                key=lambda event: _integer(event.story_time.earliest, "earliest"),
            )
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "project": self.project,
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, value: object) -> Timeline:
        record = _record(
            value,
            required={"schema_version", "project", "events"},
            optional=set(),
            field="timeline",
        )
        if record["schema_version"] != "1.0":
            raise ValueError("unsupported timeline schema_version")
        return cls(
            _text(record["project"], "project", identifier=True),
            (Event.from_dict(item) for item in _array(record["events"], "events")),
        )
