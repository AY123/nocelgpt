"""Scoped in-memory facts, acquired knowledge, beliefs and future intentions.

Observation is supplied structured evidence, not a claim that this module checked
the prose. These values and this projection never commit Canon or apply events.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import cast

from anovel.domain.character import Character
from anovel.domain.identity import EntityId, _record, _text

Scalar = str | bool | int | float


def _id(value: object, field: str) -> EntityId:
    if not isinstance(value, EntityId):
        raise ValueError(f"{field} must be an EntityId")
    return value


def _scope(project: str, value: EntityId, field: str) -> None:
    if value.project != project:
        raise ValueError(f"{field} belongs to a different project")


def _scalar(value: object) -> Scalar:
    if type(value) not in (str, bool, int, float):
        raise ValueError("proposition value must be a non-null JSON scalar")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("proposition value must be finite")
    return cast(Scalar, value)


def _enum[EnumT: Enum](value: object, enum_type: type[EnumT], field: str) -> EnumT:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an enum string")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ValueError(f"unknown {field}") from exc


def _kind(record: dict[str, object], expected: str) -> None:
    if record["kind"] != expected:
        raise ValueError(f"kind must be {expected}")


def _array(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    return value


def _same_value(first: Scalar, second: Scalar) -> bool:
    if isinstance(first, bool) or isinstance(second, bool):
        return type(first) is type(second) and first == second
    return first == second


class KnowledgeLevel(Enum):
    UNKNOWN = "UNKNOWN"
    KNOWN = "KNOWN"
    BELIEVED = "BELIEVED"
    SUSPECTED = "SUSPECTED"
    CONTRADICTORY = "CONTRADICTORY"


class GoalStatus(Enum):
    OPEN = "OPEN"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    ACHIEVED = "ACHIEVED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"
    SUPERSEDED = "SUPERSEDED"


class IntentStatus(Enum):
    PLANNED = "PLANNED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True, eq=False)
class Proposition:
    subject: EntityId
    predicate: str
    value: Scalar

    def __post_init__(self) -> None:
        _id(self.subject, "subject")
        _text(self.predicate, "predicate")
        _scalar(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Proposition):
            return NotImplemented
        return (
            self.subject == other.subject
            and self.predicate == other.predicate
            and _same_value(self.value, other.value)
        )

    def __hash__(self) -> int:
        scalar_type = (
            "boolean"
            if isinstance(self.value, bool)
            else "string"
            if isinstance(self.value, str)
            else "number"
        )
        return hash((self.subject, self.predicate, scalar_type, self.value))

    @classmethod
    def from_dict(cls, value: object) -> Proposition:
        record = _record(
            value,
            required={"subject", "predicate", "value"},
            optional=set(),
            field="proposition",
        )
        return cls(
            EntityId.from_dict(record["subject"]),
            _text(record["predicate"], "predicate"),
            _scalar(record["value"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "subject": self.subject.to_dict(),
            "predicate": self.predicate,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class WorldFact:
    id: EntityId
    proposition: Proposition
    evidence_ref: str

    def __post_init__(self) -> None:
        _id(self.id, "id")
        if not isinstance(self.proposition, Proposition):
            raise ValueError("proposition must be a Proposition")
        _scope(self.id.project, self.proposition.subject, "proposition subject")
        _text(self.evidence_ref, "evidence_ref")

    @classmethod
    def from_dict(cls, value: object) -> WorldFact:
        record = _record(
            value,
            required={"kind", "id", "proposition", "evidence_ref"},
            optional=set(),
            field="world fact",
        )
        _kind(record, "WORLD_FACT")
        return cls(
            EntityId.from_dict(record["id"]),
            Proposition.from_dict(record["proposition"]),
            _text(record["evidence_ref"], "evidence_ref"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "WORLD_FACT",
            "id": self.id.to_dict(),
            "proposition": self.proposition.to_dict(),
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class Observation:
    id: EntityId
    fact_id: EntityId
    witnesses: frozenset[EntityId]
    evidence_ref: str

    def __post_init__(self) -> None:
        _id(self.id, "id")
        _scope(self.id.project, _id(self.fact_id, "fact_id"), "fact_id")
        if not isinstance(self.witnesses, frozenset):
            raise ValueError("witnesses must be a frozenset")
        for witness in self.witnesses:
            _scope(self.id.project, _id(witness, "witness"), "witness")
        _text(self.evidence_ref, "evidence_ref")

    @classmethod
    def from_dict(cls, value: object) -> Observation:
        record = _record(
            value,
            required={"kind", "id", "fact_id", "witnesses", "evidence_ref"},
            optional=set(),
            field="observation",
        )
        _kind(record, "OBSERVATION")
        witnesses = tuple(
            EntityId.from_dict(item)
            for item in _array(record["witnesses"], "witnesses")
        )
        if len(set(witnesses)) != len(witnesses):
            raise ValueError("witnesses must be unique")
        return cls(
            EntityId.from_dict(record["id"]),
            EntityId.from_dict(record["fact_id"]),
            frozenset(witnesses),
            _text(record["evidence_ref"], "evidence_ref"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "OBSERVATION",
            "id": self.id.to_dict(),
            "fact_id": self.fact_id.to_dict(),
            "witnesses": [
                witness.to_dict()
                for witness in sorted(
                    self.witnesses, key=lambda item: (item.project, item.local_id)
                )
            ],
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class Belief:
    id: EntityId
    holder: EntityId
    proposition: Proposition
    source_ref: str
    confidence: float = 1.0
    level: KnowledgeLevel = KnowledgeLevel.BELIEVED

    def __post_init__(self) -> None:
        _id(self.id, "id")
        _scope(self.id.project, _id(self.holder, "holder"), "holder")
        if not isinstance(self.proposition, Proposition):
            raise ValueError("proposition must be a Proposition")
        _scope(self.id.project, self.proposition.subject, "proposition subject")
        _text(self.source_ref, "source_ref")
        if type(self.confidence) not in (int, float) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be a finite number between 0 and 1")
        if self.level not in (KnowledgeLevel.BELIEVED, KnowledgeLevel.SUSPECTED):
            raise ValueError("belief level must be BELIEVED or SUSPECTED")

    @classmethod
    def from_dict(cls, value: object) -> Belief:
        record = _record(
            value,
            required={"kind", "id", "holder", "proposition", "source_ref"},
            optional={"confidence", "level"},
            field="belief",
        )
        _kind(record, "BELIEF")
        confidence = record.get("confidence", 1.0)
        if type(confidence) not in (int, float):
            raise ValueError("confidence must be a number")
        return cls(
            EntityId.from_dict(record["id"]),
            EntityId.from_dict(record["holder"]),
            Proposition.from_dict(record["proposition"]),
            _text(record["source_ref"], "source_ref"),
            cast(float, confidence),
            _enum(record.get("level", "BELIEVED"), KnowledgeLevel, "level"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "BELIEF",
            "id": self.id.to_dict(),
            "holder": self.holder.to_dict(),
            "proposition": self.proposition.to_dict(),
            "source_ref": self.source_ref,
            "confidence": self.confidence,
            "level": self.level.value,
        }


@dataclass(frozen=True, slots=True)
class Goal:
    id: EntityId
    owner: EntityId
    description: str
    status: GoalStatus = GoalStatus.OPEN
    priority: int = 0

    def __post_init__(self) -> None:
        _id(self.id, "id")
        _scope(self.id.project, _id(self.owner, "owner"), "owner")
        _text(self.description, "description")
        if not isinstance(self.status, GoalStatus):
            raise ValueError("status must be a GoalStatus")
        if type(self.priority) is not int:
            raise ValueError("priority must be an integer")

    @classmethod
    def from_dict(cls, value: object) -> Goal:
        record = _record(
            value,
            required={"kind", "id", "owner", "description"},
            optional={"status", "priority"},
            field="goal",
        )
        _kind(record, "GOAL")
        priority = record.get("priority", 0)
        if type(priority) is not int:
            raise ValueError("priority must be an integer")
        return cls(
            EntityId.from_dict(record["id"]),
            EntityId.from_dict(record["owner"]),
            _text(record["description"], "description"),
            _enum(record.get("status", "OPEN"), GoalStatus, "status"),
            priority,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "GOAL",
            "id": self.id.to_dict(),
            "owner": self.owner.to_dict(),
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
        }


@dataclass(frozen=True, slots=True)
class Intent:
    id: EntityId
    owner: EntityId
    goal_id: EntityId
    action: str
    based_on: tuple[EntityId, ...]
    expected_cost: str = ""
    status: IntentStatus = IntentStatus.PLANNED

    def __post_init__(self) -> None:
        _id(self.id, "id")
        _scope(self.id.project, _id(self.owner, "owner"), "owner")
        _scope(self.id.project, _id(self.goal_id, "goal_id"), "goal_id")
        _text(self.action, "action")
        if not isinstance(self.based_on, tuple):
            raise ValueError("based_on must be a tuple")
        for reference in self.based_on:
            _scope(self.id.project, _id(reference, "based_on reference"), "based_on")
        if not isinstance(self.expected_cost, str):
            raise ValueError("expected_cost must be a string")
        if not isinstance(self.status, IntentStatus):
            raise ValueError("status must be an IntentStatus")

    @classmethod
    def from_dict(cls, value: object) -> Intent:
        record = _record(
            value,
            required={"kind", "id", "owner", "goal_id", "action", "based_on"},
            optional={"expected_cost", "status"},
            field="intent",
        )
        _kind(record, "INTENT")
        expected_cost = record.get("expected_cost", "")
        if not isinstance(expected_cost, str):
            raise ValueError("expected_cost must be a string")
        return cls(
            EntityId.from_dict(record["id"]),
            EntityId.from_dict(record["owner"]),
            EntityId.from_dict(record["goal_id"]),
            _text(record["action"], "action"),
            tuple(
                EntityId.from_dict(item)
                for item in _array(record["based_on"], "based_on")
            ),
            expected_cost,
            _enum(record.get("status", "PLANNED"), IntentStatus, "status"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "INTENT",
            "id": self.id.to_dict(),
            "owner": self.owner.to_dict(),
            "goal_id": self.goal_id.to_dict(),
            "action": self.action,
            "based_on": [reference.to_dict() for reference in self.based_on],
            "expected_cost": self.expected_cost,
            "status": self.status.value,
        }


class KnowledgeState:
    """Mutable local projection with immutable records and explicit acquisition.

    All record IDs, including characters, share one project-local namespace. Only
    a registered Observation can establish knowledge; an author-visible fact or
    another character's belief cannot. This is not a persistence/write service.
    """

    def __init__(self, project: str, characters: Iterable[Character]) -> None:
        _text(project, "project", identifier=True)
        prepared: dict[EntityId, Character] = {}
        try:
            entries = tuple(characters)
        except TypeError as exc:
            raise ValueError("characters must be iterable") from exc
        for character in entries:
            if not isinstance(character, Character):
                raise ValueError("characters must contain Character values")
            _scope(project, character.id, "character")
            if character.id in prepared:
                raise ValueError(f"duplicate id {character.id}")
            prepared[character.id] = character
        self._project = project
        self._characters = prepared
        self._ids = set(prepared)
        self._facts: dict[EntityId, WorldFact] = {}
        self._observations: dict[EntityId, Observation] = {}
        self._beliefs: dict[EntityId, Belief] = {}
        self._goals: dict[EntityId, Goal] = {}
        self._intents: dict[EntityId, Intent] = {}
        self._knowledge: dict[tuple[EntityId, EntityId, EntityId], None] = {}

    @property
    def project(self) -> str:
        return self._project

    @property
    def characters(self) -> tuple[Character, ...]:
        return tuple(self._characters.values())

    @property
    def facts(self) -> tuple[WorldFact, ...]:
        return tuple(self._facts.values())

    @property
    def observations(self) -> tuple[Observation, ...]:
        return tuple(self._observations.values())

    @property
    def beliefs(self) -> tuple[Belief, ...]:
        return tuple(self._beliefs.values())

    @property
    def goals(self) -> tuple[Goal, ...]:
        return tuple(self._goals.values())

    @property
    def intents(self) -> tuple[Intent, ...]:
        return tuple(self._intents.values())

    @property
    def knowledge(self) -> tuple[tuple[EntityId, EntityId, EntityId], ...]:
        """Return immutable (holder, fact_id, source_id) acquisition records."""
        return tuple(self._knowledge)

    def _new_id(self, value: EntityId) -> None:
        _scope(self.project, _id(value, "id"), "id")
        if value in self._ids:
            raise ValueError(f"duplicate id {value}")

    def _character(self, value: EntityId) -> Character:
        _scope(self.project, _id(value, "holder"), "holder")
        if value not in self._characters:
            raise ValueError(f"unknown character {value}")
        return self._characters[value]

    def _has_acquired(self, holder: EntityId, fact_id: EntityId) -> bool:
        return any(
            known_holder == holder and known_fact == fact_id
            for known_holder, known_fact, _ in self._knowledge
        )

    def add_fact(self, fact: WorldFact) -> None:
        if not isinstance(fact, WorldFact):
            raise ValueError("fact must be a WorldFact")
        self._new_id(fact.id)
        self._facts[fact.id] = fact
        self._ids.add(fact.id)

    def add_observation(self, observation: Observation) -> None:
        if not isinstance(observation, Observation):
            raise ValueError("observation must be an Observation")
        self._new_id(observation.id)
        if observation.fact_id not in self._facts:
            raise ValueError("observation refers to an unknown fact")
        for witness in observation.witnesses:
            self._character(witness)
        self._observations[observation.id] = observation
        self._ids.add(observation.id)

    def add_belief(self, belief: Belief) -> None:
        if not isinstance(belief, Belief):
            raise ValueError("belief must be a Belief")
        self._new_id(belief.id)
        self._character(belief.holder)
        self._beliefs[belief.id] = belief
        self._ids.add(belief.id)

    def add_goal(self, goal: Goal) -> None:
        if not isinstance(goal, Goal):
            raise ValueError("goal must be a Goal")
        self._new_id(goal.id)
        self._character(goal.owner)
        self._goals[goal.id] = goal
        self._ids.add(goal.id)

    def add_intent(self, intent: Intent) -> None:
        if not isinstance(intent, Intent):
            raise ValueError("intent must be an Intent")
        self._new_id(intent.id)
        self._character(intent.owner)
        goal = self._goals.get(intent.goal_id)
        if goal is None or goal.owner != intent.owner:
            raise ValueError("intent must reference its owner's goal")
        for reference in intent.based_on:
            belief = self._beliefs.get(reference)
            if belief is not None and belief.holder == intent.owner:
                continue
            if reference in self._facts and self._has_acquired(intent.owner, reference):
                continue
            raise ValueError("intent basis must be owner's belief or acquired fact")
        self._intents[intent.id] = intent
        self._ids.add(intent.id)

    def learn(self, holder: EntityId, fact_id: EntityId, source_id: EntityId) -> None:
        """Acquire a fact through a matching observation witnessed by holder."""
        self._character(holder)
        _scope(self.project, _id(fact_id, "fact_id"), "fact_id")
        _scope(self.project, _id(source_id, "source_id"), "source_id")
        if fact_id not in self._facts:
            raise ValueError("cannot learn an unknown fact")
        source = self._observations.get(source_id)
        if source is None:
            raise ValueError("knowledge requires a registered observation source")
        if source.fact_id != fact_id:
            raise ValueError("observation source refers to a different fact")
        if holder not in source.witnesses:
            raise ValueError("holder did not witness the observation")
        self._knowledge[(holder, fact_id, source_id)] = None

    def query(self, holder: EntityId, proposition: Proposition) -> KnowledgeLevel:
        self._character(holder)
        if not isinstance(proposition, Proposition):
            raise ValueError("proposition must be a Proposition")
        _scope(self.project, proposition.subject, "proposition subject")
        known = tuple(
            fact.proposition
            for fact in self._facts.values()
            if self._has_acquired(holder, fact.id)
        )
        beliefs = tuple(
            belief for belief in self._beliefs.values() if belief.holder == holder
        )
        if isinstance(proposition.value, bool):
            visible_values = {
                item.value
                for item in (*known, *(belief.proposition for belief in beliefs))
                if item.subject == proposition.subject
                and item.predicate == proposition.predicate
                and isinstance(item.value, bool)
            }
            if visible_values == {True, False}:
                return KnowledgeLevel.CONTRADICTORY
        if proposition in known:
            return KnowledgeLevel.KNOWN
        levels = {
            belief.level for belief in beliefs if belief.proposition == proposition
        }
        if KnowledgeLevel.BELIEVED in levels:
            return KnowledgeLevel.BELIEVED
        if KnowledgeLevel.SUSPECTED in levels:
            return KnowledgeLevel.SUSPECTED
        return KnowledgeLevel.UNKNOWN

    def require_known(self, holder: EntityId, fact_id: EntityId) -> WorldFact:
        self._character(holder)
        _scope(self.project, _id(fact_id, "fact_id"), "fact_id")
        fact = self._facts.get(fact_id)
        if fact is None or not self._has_acquired(holder, fact_id):
            raise ValueError("fact has not been acquired by holder")
        if self.query(holder, fact.proposition) is not KnowledgeLevel.KNOWN:
            raise ValueError("fact is contradictory rather than known")
        return fact

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "project": self.project,
            "characters": [character.to_dict() for character in self.characters],
            "facts": [fact.to_dict() for fact in self.facts],
            "observations": [source.to_dict() for source in self.observations],
            "beliefs": [belief.to_dict() for belief in self.beliefs],
            "knowledge": [
                {
                    "holder": holder.to_dict(),
                    "fact_id": fact_id.to_dict(),
                    "source_id": source_id.to_dict(),
                }
                for holder, fact_id, source_id in self.knowledge
            ],
            "goals": [goal.to_dict() for goal in self.goals],
            "intents": [intent.to_dict() for intent in self.intents],
        }

    @classmethod
    def from_dict(cls, value: object) -> KnowledgeState:
        record = _record(
            value,
            required={
                "schema_version",
                "project",
                "characters",
                "facts",
                "observations",
                "beliefs",
                "knowledge",
                "goals",
                "intents",
            },
            optional=set(),
            field="knowledge state",
        )
        if record["schema_version"] != "1.0":
            raise ValueError("unsupported knowledge state schema_version")
        state = cls(
            _text(record["project"], "project", identifier=True),
            (
                Character.from_dict(item)
                for item in _array(record["characters"], "characters")
            ),
        )
        for item in _array(record["facts"], "facts"):
            state.add_fact(WorldFact.from_dict(item))
        for item in _array(record["observations"], "observations"):
            state.add_observation(Observation.from_dict(item))
        for item in _array(record["beliefs"], "beliefs"):
            state.add_belief(Belief.from_dict(item))
        for item in _array(record["knowledge"], "knowledge"):
            acquisition = _record(
                item,
                required={"holder", "fact_id", "source_id"},
                optional=set(),
                field="knowledge acquisition",
            )
            key = (
                EntityId.from_dict(acquisition["holder"]),
                EntityId.from_dict(acquisition["fact_id"]),
                EntityId.from_dict(acquisition["source_id"]),
            )
            if key in state._knowledge:
                raise ValueError("duplicate knowledge acquisition")
            state.learn(*key)
        for item in _array(record["goals"], "goals"):
            state.add_goal(Goal.from_dict(item))
        for item in _array(record["intents"], "intents"):
            state.add_intent(Intent.from_dict(item))
        return state
