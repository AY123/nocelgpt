"""Bound-annotation conditional Q1 checks, not automatic prose or Canon authority.

The caller supplies untrusted semantic annotations. Exact source binding and
actual finite rule execution do not certify that the annotations exhaust or
correctly interpret natural prose. No checker mutates the supplied domain state.
"""

from __future__ import annotations

import re
from base64 import b64decode, b64encode
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Callable, cast
from uuid import uuid4

from anovel.canon.identity import canonical_bytes, decode_canonical, utc_timestamp
from anovel.contracts.models import CanonView, KnowledgeSnapshot
from anovel.domain.character import Lifecycle
from anovel.domain.delta import (
    FactBaseline,
    FactState,
    FactStatus,
    MarkUnknown,
    NarrativeDelta,
    NoChange,
    RetractFact,
    ScalarKind,
    SetFact,
)
from anovel.domain.events import StoryTime, TimeKind
from anovel.domain.identity import Entity, EntityId
from anovel.domain.knowledge import KnowledgeState

if TYPE_CHECKING:
    from anovel.workflow.extractor import ExactSpan, ExtractionObservation

PROFILE = "BOUND_ANNOTATIONS_LOCAL_TEST"
CHECK_IDS = (
    "Q1_PRECONDITIONS_V1",
    "Q1_RELATIONS_V1",
    "Q1_LIFECYCLE_V1",
    "Q1_KNOWLEDGE_V1",
)
REGISTRY_HASH = sha256(
    canonical_bytes(
        {
            "profile": PROFILE,
            "version": "1.0",
            "checks": list(CHECK_IDS),
            "coverage": "NOT_VERIFIED",
            "source": "AUTHOR_INPUT_LOCAL_TEST",
            "time": "STRICT_INTERVAL_ORDER_NO_LAST_ACQUISITION_OVERRIDE",
            "knowledge": "NO_ABSENCE_IMPLIES_IGNORANCE_NO_SUBJECT_IMPLIES_HOLDER",
        }
    )
).hexdigest()
_TOKEN = object()
_FALSE = {
    "can_commit": False,
    "can_issue_permit": False,
    "can_dispatch": False,
    "accepted": False,
    "published": False,
}


class Q1Error(ValueError):
    """Stable diagnostics without private text interpolation."""


def _hash(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise Q1Error("INVALID_Q1_HASH")
    return value


def _record(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields:
        raise Q1Error("INVALID_Q1_RECORD")
    return cast(dict[str, object], value)


def _encoded(raw: bytes) -> str:
    return b64encode(raw).decode("ascii")


def _decoded(value: object) -> bytes:
    if type(value) is not str:
        raise Q1Error("INVALID_Q1_BYTES")
    result = b64decode(value, validate=True)
    if _encoded(result) != value:
        raise Q1Error("INVALID_Q1_BYTES")
    return result


def _text(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise Q1Error("INVALID_Q1_IDENTITY")
    value.encode("utf-8")
    return value


def _time(value: object) -> datetime:
    parsed = datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
    if utc_timestamp(parsed) != value:
        raise Q1Error("INVALID_Q1_TIME")
    return parsed


class _ClaimBase:
    __slots__ = ()
    span: ExactSpan

    def __post_init__(self) -> None:
        _validate_claim(self)

    def to_dict(self) -> dict[str, object]:
        return _claim_dict(self)


@dataclass(frozen=True, slots=True)
class ActivityClaim(_ClaimBase):
    span: ExactSpan
    actor: EntityId | None
    at: StoryTime | None
    context: str = "ACTUAL"


@dataclass(frozen=True, slots=True)
class RelationClaim(_ClaimBase):
    span: ExactSpan
    party_a: EntityId | None
    party_b: EntityId | None


@dataclass(frozen=True, slots=True)
class KnowledgeUseClaim(_ClaimBase):
    span: ExactSpan
    holder: EntityId | None
    fact_id: EntityId | None
    at: StoryTime | None
    source_id: EntityId | None = None


@dataclass(frozen=True, slots=True)
class AcquisitionClaim(_ClaimBase):
    span: ExactSpan
    holder: EntityId | None
    fact_id: EntityId | None
    source_id: EntityId | None
    at: StoryTime | None


@dataclass(frozen=True, slots=True)
class BeliefClaim(_ClaimBase):
    span: ExactSpan
    holder: EntityId | None
    belief_id: EntityId | None


@dataclass(frozen=True, slots=True)
class ReaderRevealClaim(_ClaimBase):
    span: ExactSpan
    fact_id: EntityId | None


type Q1Claim = (
    ActivityClaim
    | RelationClaim
    | KnowledgeUseClaim
    | AcquisitionClaim
    | BeliefClaim
    | ReaderRevealClaim
)
_CLAIMS: dict[type[_ClaimBase], tuple[str, tuple[str, ...]]] = {
    ActivityClaim: ("ACTIVITY", ("actor", "at", "context")),
    RelationClaim: ("RELATION", ("party_a", "party_b")),
    KnowledgeUseClaim: ("KNOWLEDGE_USE", ("holder", "fact_id", "at", "source_id")),
    AcquisitionClaim: ("ACQUISITION", ("holder", "fact_id", "source_id", "at")),
    BeliefClaim: ("BELIEF", ("holder", "belief_id")),
    ReaderRevealClaim: ("READER_REVEAL", ("fact_id",)),
}


def _validate_claim(value: _ClaimBase) -> None:
    from anovel.workflow.extractor import ExactSpan

    if type(value) not in _CLAIMS or type(value.span) is not ExactSpan:
        raise Q1Error("INVALID_Q1_CLAIM")
    for name in _CLAIMS[type(value)][1]:
        item = getattr(value, name)
        if name == "context":
            if type(item) is not str or item not in {
                "ACTUAL",
                "RECOLLECTION",
                "DREAM",
                "QUOTATION",
            }:
                raise Q1Error("INVALID_Q1_CLAIM")
        elif name == "at":
            if item is not None and type(item) is not StoryTime:
                raise Q1Error("INVALID_Q1_CLAIM")
        elif item is not None and type(item) is not EntityId:
            raise Q1Error("INVALID_Q1_CLAIM")


def _claim_dict(value: _ClaimBase) -> dict[str, object]:
    _validate_claim(value)
    kind, names = _CLAIMS[type(value)]
    row: dict[str, object] = {"kind": kind, "span": value.span.to_dict()}
    for name in names:
        item = getattr(value, name)
        row[name] = item if name == "context" or item is None else item.to_dict()
    return row


def claim_from_dict(value: object) -> Q1Claim:
    from anovel.workflow.extractor import ExactSpan

    if type(value) is not dict:
        raise Q1Error("INVALID_Q1_CLAIM")
    for constructor, (kind, names) in _CLAIMS.items():
        if value.get("kind") != kind:
            continue
        row = _record(value, {"kind", "span", *names})
        kwargs: dict[str, object] = {"span": ExactSpan.from_dict(row["span"])}
        for name in names:
            item = row[name]
            kwargs[name] = (
                item
                if name == "context" or item is None
                else StoryTime.from_dict(item)
                if name == "at"
                else EntityId.from_dict(item)
            )
        return cast(Callable[..., Q1Claim], constructor)(**kwargs)
    raise Q1Error("INVALID_Q1_CLAIM")


@dataclass(frozen=True, slots=True)
class DeathTiming:
    """An explicit AUTHOR_INPUT time condition, not a Canon death event."""

    actor: EntityId
    death_at: StoryTime

    def __post_init__(self) -> None:
        if type(self.actor) is not EntityId or type(self.death_at) is not StoryTime:
            raise Q1Error("INVALID_Q1_DEATH_TIMING")

    def to_dict(self) -> dict[str, object]:
        return {
            "actor": self.actor.to_dict(),
            "death_at": self.death_at.to_dict(),
            "source": "AUTHOR_INPUT_LOCAL_TEST",
        }

    @classmethod
    def from_dict(cls, value: object) -> DeathTiming:
        row = _record(value, {"actor", "death_at", "source"})
        if row["source"] != "AUTHOR_INPUT_LOCAL_TEST":
            raise Q1Error("INVALID_Q1_DEATH_TIMING")
        return cls(
            EntityId.from_dict(row["actor"]), StoryTime.from_dict(row["death_at"])
        )


@dataclass(frozen=True, slots=True)
class Q1State:
    baseline: FactBaseline
    entities: tuple[Entity, ...]
    knowledge_bytes: bytes | None = field(default=None, repr=False)
    death_times: tuple[DeathTiming, ...] = ()

    def __post_init__(self) -> None:
        try:
            if (
                type(self.baseline) is not FactBaseline
                or type(self.entities) is not tuple
                or any(type(v) is not Entity for v in self.entities)
            ):
                raise ValueError
            ids = {v.id for v in self.entities}
            if (
                len(ids) != len(self.entities)
                or any(v.project != self.project for v in ids)
                or any(
                    v.seed_fact.proposition.subject not in ids
                    for v in self.baseline.facts
                )
            ):
                raise ValueError
            if (
                type(self.death_times) is not tuple
                or any(type(v) is not DeathTiming for v in self.death_times)
                or len({v.actor for v in self.death_times}) != len(self.death_times)
                or any(v.actor not in ids for v in self.death_times)
            ):
                raise ValueError
            knowledge = self.knowledge
            if knowledge is not None:
                if (
                    knowledge.project != self.project
                    or canonical_bytes(knowledge.to_dict()) != self.knowledge_bytes
                    or any(v.id not in ids for v in knowledge.characters)
                    or any(v.proposition.subject not in ids for v in knowledge.beliefs)
                ):
                    raise ValueError
                for fact in knowledge.facts:
                    actual = self.baseline.get(fact.id)
                    if (
                        actual is None
                        or actual.seed_fact.proposition.subject
                        != fact.proposition.subject
                        or actual.seed_fact.proposition.predicate
                        != fact.proposition.predicate
                        or actual.state != FactState.known(fact.proposition.value)
                    ):
                        raise ValueError
        except (TypeError, ValueError, AttributeError, KeyError):
            raise Q1Error("INVALID_Q1_STATE") from None

    @classmethod
    def freeze(
        cls,
        baseline: FactBaseline,
        entities: tuple[Entity, ...],
        *,
        knowledge: KnowledgeState | None = None,
        death_times: tuple[DeathTiming, ...] = (),
    ) -> Q1State:
        if knowledge is not None and type(knowledge) is not KnowledgeState:
            raise Q1Error("INVALID_Q1_STATE")
        return cls(
            baseline,
            tuple(sorted(entities, key=lambda v: str(v.id))),
            None if knowledge is None else canonical_bytes(knowledge.to_dict()),
            tuple(sorted(death_times, key=lambda v: str(v.actor))),
        )

    @property
    def project(self) -> str:
        return self.baseline.project

    @property
    def branch(self) -> str:
        return self.baseline.branch

    @property
    def parent_ref(self) -> str:
        return self.baseline.parent_ref

    @property
    def knowledge(self) -> KnowledgeState | None:
        return (
            None
            if self.knowledge_bytes is None
            else KnowledgeState.from_dict(decode_canonical(self.knowledge_bytes))
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "conditional_q1_state",
            "schema_version": "1.0",
            "source": "FROZEN_PARENT_AND_AUTHOR_INPUT_LOCAL_TEST",
            "baseline": self.baseline.to_dict(),
            "entities": [v.to_dict() for v in self.entities],
            "knowledge_base64": None
            if self.knowledge_bytes is None
            else _encoded(self.knowledge_bytes),
            "death_times": [v.to_dict() for v in self.death_times],
        }

    def payload_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> Q1State:
        row = _record(
            value,
            {
                "record_type",
                "schema_version",
                "source",
                "baseline",
                "entities",
                "knowledge_base64",
                "death_times",
            },
        )
        if type(row["entities"]) is not list or type(row["death_times"]) is not list:
            raise Q1Error("INVALID_Q1_STATE")
        result = cls(
            FactBaseline.from_dict(row["baseline"]),
            tuple(Entity.from_dict(v) for v in row["entities"]),
            None
            if row["knowledge_base64"] is None
            else _decoded(row["knowledge_base64"]),
            tuple(DeathTiming.from_dict(v) for v in row["death_times"]),
        )
        if result.payload_bytes() != canonical_bytes(row):
            raise Q1Error("INVALID_Q1_STATE")
        return result

    @classmethod
    def from_bytes(cls, raw: bytes) -> Q1State:
        result = cls.from_dict(decode_canonical(raw))
        if result.payload_bytes() != raw:
            raise Q1Error("INVALID_Q1_STATE")
        return result

    @property
    def content_hash(self) -> str:
        return _hash(self.payload_bytes())


_BIND_FIELDS = {
    "observation_hash",
    "assembly_hash",
    "prose_hash",
    "source_input_hash",
    "parent_ref",
    "contract_hash",
    "pack_hash",
    "frozen_knowledge_hash",
    "project",
    "branch",
    "run_id",
    "step_id",
}


def _bindings(observation: ExtractionObservation) -> dict[str, object]:
    source = observation.assembly.child.source
    contract = source.contract
    return {
        "observation_hash": observation.record_hash,
        "assembly_hash": observation.assembly_hash,
        "prose_hash": observation.prose_hash,
        "source_input_hash": source.input_hash,
        "parent_ref": contract.parent_ref,
        "contract_hash": contract.content_hash,
        "pack_hash": contract.pack_hash,
        "frozen_knowledge_hash": contract.knowledge_hash,
        "project": observation.project,
        "branch": observation.branch,
        "run_id": observation.run_id,
        "step_id": observation.step_id,
    }


_ANNOTATION_FIELDS = {
    "record_type",
    "schema_version",
    "profile",
    *_BIND_FIELDS,
    "author_knowledge",
    "author_knowledge_hash",
    "claims",
    "death_times",
}


@dataclass(frozen=True, slots=True)
class BoundQ1Annotations:
    payload: bytes = field(repr=False)
    _claims: tuple[Q1Claim, ...] = field(init=False, repr=False, compare=False)
    _author: KnowledgeSnapshot | None = field(init=False, repr=False, compare=False)
    _deaths: tuple[DeathTiming, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        try:
            row = _record(decode_canonical(self.payload), _ANNOTATION_FIELDS)
            if (
                row["record_type"] != "bound_q1_annotations"
                or row["schema_version"] != "1.0"
                or row["profile"] != PROFILE
            ):
                raise ValueError
            for name in _BIND_FIELDS:
                _digest(row[name]) if name.endswith(
                    "hash"
                ) or name == "step_id" else _text(row[name])
            if type(row["claims"]) is not list or type(row["death_times"]) is not list:
                raise ValueError
            claims = tuple(claim_from_dict(v) for v in row["claims"])
            deaths = tuple(DeathTiming.from_dict(v) for v in row["death_times"])
            if len({_hash(canonical_bytes(v.to_dict())) for v in claims}) != len(
                claims
            ) or len({v.actor for v in deaths}) != len(deaths):
                raise ValueError
            author = (
                None
                if row["author_knowledge"] is None
                else KnowledgeSnapshot.from_dict(row["author_knowledge"])
            )
            if row["author_knowledge_hash"] != (
                None if author is None else _hash(canonical_bytes(author.to_dict()))
            ):
                raise ValueError
            normalized = {
                **row,
                "claims": [v.to_dict() for v in claims],
                "death_times": [v.to_dict() for v in deaths],
                "author_knowledge": None if author is None else author.to_dict(),
            }
            if canonical_bytes(normalized) != self.payload:
                raise ValueError
            object.__setattr__(self, "_claims", claims)
            object.__setattr__(self, "_author", author)
            object.__setattr__(self, "_deaths", deaths)
        except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
            raise Q1Error("INVALID_Q1_ANNOTATIONS") from None

    @classmethod
    def freeze(
        cls,
        observation: ExtractionObservation,
        *,
        claims: tuple[Q1Claim, ...],
        author_knowledge: KnowledgeSnapshot | None = None,
        death_times: tuple[DeathTiming, ...] = (),
    ) -> BoundQ1Annotations:
        if (
            type(claims) is not tuple
            or type(death_times) is not tuple
            or (
                author_knowledge is not None
                and type(author_knowledge) is not KnowledgeSnapshot
            )
        ):
            raise Q1Error("INVALID_Q1_ANNOTATIONS")
        result = cls(
            canonical_bytes(
                {
                    "record_type": "bound_q1_annotations",
                    "schema_version": "1.0",
                    "profile": PROFILE,
                    **_bindings(observation),
                    "author_knowledge": None
                    if author_knowledge is None
                    else author_knowledge.to_dict(),
                    "author_knowledge_hash": None
                    if author_knowledge is None
                    else _hash(canonical_bytes(author_knowledge.to_dict())),
                    "claims": [v.to_dict() for v in claims],
                    "death_times": [v.to_dict() for v in death_times],
                }
            )
        )
        validate_bindings(result, observation)
        return result

    @property
    def claims(self) -> tuple[Q1Claim, ...]:
        return self._claims

    @property
    def author_knowledge(self) -> KnowledgeSnapshot | None:
        return self._author

    @property
    def death_times(self) -> tuple[DeathTiming, ...]:
        return self._deaths

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    def payload_bytes(self) -> bytes:
        return self.payload

    @classmethod
    def from_dict(cls, value: object) -> BoundQ1Annotations:
        return cls(canonical_bytes(value))

    @classmethod
    def from_bytes(cls, raw: bytes) -> BoundQ1Annotations:
        return cls(raw)

    @property
    def record_hash(self) -> str:
        return _hash(self.payload)

    @property
    def content_hash(self) -> str:
        return self.record_hash


def _bound_state(
    annotations: BoundQ1Annotations, observation: ExtractionObservation
) -> tuple[Q1State, str]:
    from anovel.workflow.extractor import ExtractionObservation

    if (
        type(annotations) is not BoundQ1Annotations
        or type(observation) is not ExtractionObservation
    ):
        raise Q1Error("Q1_BOUND_INPUT_REQUIRED")
    row = annotations.to_dict()
    if any(
        row[name] != value or type(row[name]) is not type(value)
        for name, value in _bindings(observation).items()
    ):
        raise Q1Error("Q1_ANNOTATION_SOURCE_CHANGED")
    for claim in annotations.claims:
        claim.span.verify(observation.assembly.prose)
    original_input = observation.assembly.child.source.frozen_input.to_dict()
    view = CanonView.from_dict(original_input["view"])
    original = (
        None
        if original_input["knowledge_snapshot"] is None
        else KnowledgeSnapshot.from_dict(original_input["knowledge_snapshot"])
    )
    extra = annotations.author_knowledge
    if (
        original is not None
        and extra is not None
        and canonical_bytes(original.to_dict()) != canonical_bytes(extra.to_dict())
    ):
        raise Q1Error("Q1_KNOWLEDGE_SOURCE_CONFLICT")
    effective = original if original is not None else extra
    if effective is not None:
        effective.validate_against(view)
    state = Q1State.freeze(
        view.baseline,
        view.root.seed.entities,
        knowledge=None if effective is None else effective.knowledge,
        death_times=annotations.death_times,
    )
    return (
        state,
        "EXISTING_AUTHOR_INPUT"
        if original is not None
        else "ADDITIONAL_AUTHOR_INPUT"
        if extra is not None
        else "MISSING",
    )


def validate_bindings(
    annotations: BoundQ1Annotations, observation: ExtractionObservation
) -> None:
    """Pure input binding, not execution, current HEAD validation or a capability."""
    try:
        _bound_state(annotations, observation)
    except Q1Error:
        raise
    except (TypeError, ValueError, KeyError, AttributeError, StopIteration):
        raise Q1Error("Q1_ANNOTATION_BINDING_INVALID") from None


@dataclass(frozen=True, slots=True)
class Q1Finding:
    code: str
    claim_index: int | None = None

    def __post_init__(self) -> None:
        if (
            type(self.code) is not str
            or re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", self.code) is None
            or (
                self.claim_index is not None
                and (type(self.claim_index) is not int or self.claim_index < 0)
            )
        ):
            raise Q1Error("INVALID_Q1_FINDING")

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "claim_index": self.claim_index}

    @classmethod
    def from_dict(cls, value: object) -> Q1Finding:
        row = _record(value, {"code", "claim_index"})
        return cls(cast(str, row["code"]), cast(int | None, row["claim_index"]))


@dataclass(frozen=True, slots=True)
class Q1CheckResult:
    applicability: str
    verdict: str | None
    findings: tuple[Q1Finding, ...] = ()
    reason: str = "CHECKED"

    def __post_init__(self) -> None:
        if (
            type(self.findings) is not tuple
            or any(type(v) is not Q1Finding for v in self.findings)
            or type(self.reason) is not str
            or re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", self.reason) is None
        ):
            raise Q1Error("INVALID_Q1_RESULT")
        if self.applicability == "NOT_APPLICABLE":
            if self.verdict is not None or self.findings or self.reason == "CHECKED":
                raise Q1Error("INVALID_Q1_RESULT")
        elif (
            self.applicability != "APPLICABLE"
            or type(self.verdict) is not str
            or self.verdict not in {"PASS", "FAIL", "UNKNOWN", "ERROR"}
            or ((self.verdict == "PASS") != (not self.findings))
        ):
            raise Q1Error("INVALID_Q1_RESULT")

    def to_dict(self) -> dict[str, object]:
        return {
            "applicability": self.applicability,
            "verdict": self.verdict,
            "findings": [v.to_dict() for v in self.findings],
            "reason": self.reason,
        }

    def payload_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> Q1CheckResult:
        row = _record(value, {"applicability", "verdict", "findings", "reason"})
        if type(row["findings"]) is not list:
            raise Q1Error("INVALID_Q1_RESULT")
        return cls(
            cast(str, row["applicability"]),
            cast(str | None, row["verdict"]),
            tuple(Q1Finding.from_dict(v) for v in row["findings"]),
            cast(str, row["reason"]),
        )


type _Issue = tuple[str, Q1Finding]


def _result(
    issues: list[_Issue],
    *,
    applicable: bool = True,
    reason: str = "NO_ANNOTATED_CLAIMS",
) -> Q1CheckResult:
    if not applicable:
        return Q1CheckResult("NOT_APPLICABLE", None, reason=reason)
    verdict = (
        "FAIL"
        if any(v[0] == "FAIL" for v in issues)
        else "UNKNOWN"
        if issues
        else "PASS"
    )
    return Q1CheckResult("APPLICABLE", verdict, tuple(v[1] for v in issues))


def _entity(
    state: Q1State, value: EntityId | None, index: int, label: str
) -> _Issue | None:
    if value is None:
        return "UNKNOWN", Q1Finding("MISSING_" + label, index)
    if value.project != state.project:
        return "FAIL", Q1Finding("CROSS_PROJECT_" + label, index)
    if value not in {v.id for v in state.entities}:
        return "FAIL", Q1Finding("UNREGISTERED_" + label, index)
    return None


def _fact(state: Q1State, value: EntityId | None, index: int) -> _Issue | None:
    if value is None:
        return "UNKNOWN", Q1Finding("MISSING_FACT_ID", index)
    if value.project != state.project or state.baseline.get(value) is None:
        return "FAIL", Q1Finding("UNREGISTERED_OR_FOREIGN_FACT", index)
    return None


def _order(first: StoryTime | None, second: StoryTime | None) -> str:
    if (
        first is None
        or second is None
        or first.kind is TimeKind.UNKNOWN
        or second.kind is TimeKind.UNKNOWN
    ):
        return "UNKNOWN"
    if cast(int, first.latest) < cast(int, second.earliest):
        return "BEFORE"
    if cast(int, first.earliest) > cast(int, second.latest):
        return "AFTER"
    return "UNKNOWN"


def check_preconditions(
    state: Q1State, delta: NarrativeDelta | None, *, source_id: EntityId
) -> Q1CheckResult:
    """Check core scalar conditions, not extension rules, authority or HEAD."""
    if (
        type(state) is not Q1State
        or type(source_id) is not EntityId
        or (delta is not None and type(delta) is not NarrativeDelta)
    ):
        raise Q1Error("INVALID_Q1_PRECONDITION_INPUT")
    if delta is None:
        return _result([], applicable=False, reason="NO_PROPOSED_DELTA")
    issues: list[_Issue] = []
    if state.baseline.extensions or any(
        v.seed_fact.proposition.predicate.startswith("ext:")
        for v in state.baseline.facts
    ):
        # No compiled extension registry is part of this finite local profile.
        # Valid core preconditions alone cannot certify extension transitions.
        issues.append(("UNKNOWN", Q1Finding("EXTENSION_TRANSITION_NOT_EVALUATED")))
    if (delta.project, delta.branch, delta.parent_ref, delta.source_id) != (
        state.project,
        state.branch,
        state.parent_ref,
        source_id,
    ):
        issues.append(("FAIL", Q1Finding("DELTA_SCOPE_PARENT_OR_SOURCE_MISMATCH")))
    for index, operation in enumerate(delta.operations):
        snapshot = state.baseline.get(operation.meta.target_id)
        if snapshot is None:
            issues.append(("FAIL", Q1Finding("UNREGISTERED_DELTA_TARGET", index)))
            continue
        if (
            operation.meta.expected.revision != snapshot.revision
            or operation.meta.expected.state != snapshot.state
        ):
            issues.append(("FAIL", Q1Finding("STALE_FACT_PRECONDITION", index)))
        if isinstance(operation, NoChange):
            continue
        if snapshot.state.status is FactStatus.RETRACTED:
            issues.append(("FAIL", Q1Finding("RETRACTED_FACT_TRANSITION", index)))
        elif isinstance(operation, SetFact):
            kind = (
                ScalarKind.BOOLEAN
                if type(operation.value) is bool
                else ScalarKind.STRING
                if type(operation.value) is str
                else ScalarKind.NUMBER
            )
            if kind is not snapshot.value_kind or snapshot.state == FactState.known(
                operation.value
            ):
                issues.append(("FAIL", Q1Finding("INVALID_SET_FACT_TRANSITION", index)))
        elif (
            isinstance(operation, MarkUnknown)
            and snapshot.state.status is not FactStatus.KNOWN
        ):
            issues.append(("FAIL", Q1Finding("INVALID_MARK_UNKNOWN_TRANSITION", index)))
        elif type(operation) not in {SetFact, MarkUnknown, RetractFact}:
            issues.append(("UNKNOWN", Q1Finding("UNSUPPORTED_DELTA_OPERATION", index)))
    return _result(issues)


def check_relations(state: Q1State, claims: tuple[RelationClaim, ...]) -> Q1CheckResult:
    if (
        type(state) is not Q1State
        or type(claims) is not tuple
        or any(type(v) is not RelationClaim for v in claims)
    ):
        raise Q1Error("INVALID_Q1_RELATION_INPUT")
    issues: list[_Issue] = []
    for index, claim in enumerate(claims):
        for value, label in (
            (claim.party_a, "RELATION_PARTY_A"),
            (claim.party_b, "RELATION_PARTY_B"),
        ):
            issue = _entity(state, value, index, label)
            if issue is not None:
                issues.append(issue)
    return _result(issues, applicable=bool(claims))


def check_lifecycle(state: Q1State, claims: tuple[ActivityClaim, ...]) -> Q1CheckResult:
    if (
        type(state) is not Q1State
        or type(claims) is not tuple
        or any(type(v) is not ActivityClaim for v in claims)
    ):
        raise Q1Error("INVALID_Q1_LIFECYCLE_INPUT")
    knowledge = state.knowledge
    characters = {} if knowledge is None else {v.id: v for v in knowledge.characters}
    deaths = {v.actor: v.death_at for v in state.death_times}
    issues: list[_Issue] = []
    for index, claim in enumerate(claims):
        issue = _entity(state, claim.actor, index, "ACTOR")
        if issue is not None:
            issues.append(issue)
            continue
        actor = cast(EntityId, claim.actor)
        character = characters.get(actor)
        if character is None or character.lifecycle is Lifecycle.UNKNOWN:
            issues.append(("UNKNOWN", Q1Finding("LIFECYCLE_SOURCE_UNAVAILABLE", index)))
            continue
        if claim.context in {"DREAM", "QUOTATION"}:
            continue
        if character.lifecycle in {Lifecycle.ACTIVE, Lifecycle.INACTIVE}:
            if claim.actor in deaths:
                issues.append(
                    ("UNKNOWN", Q1Finding("LIFECYCLE_SOURCE_CONFLICT", index))
                )
            continue
        order = _order(claim.at, deaths.get(actor))
        if order == "AFTER":
            issues.append(("FAIL", Q1Finding("DEAD_CHARACTER_ACTUAL_ACTIVITY", index)))
        elif order != "BEFORE":
            issues.append(("UNKNOWN", Q1Finding("LIFECYCLE_TIME_UNPROVEN", index)))
    return _result(issues, applicable=bool(claims))


type KnowledgeClaim = (
    KnowledgeUseClaim | AcquisitionClaim | BeliefClaim | ReaderRevealClaim
)


def check_knowledge(
    state: Q1State, claims: tuple[KnowledgeClaim, ...]
) -> Q1CheckResult:
    if (
        type(state) is not Q1State
        or type(claims) is not tuple
        or any(
            type(v)
            not in {KnowledgeUseClaim, AcquisitionClaim, BeliefClaim, ReaderRevealClaim}
            for v in claims
        )
    ):
        raise Q1Error("INVALID_Q1_KNOWLEDGE_INPUT")
    knowledge = state.knowledge
    observations = (
        {} if knowledge is None else {v.id: v for v in knowledge.observations}
    )
    beliefs = {} if knowledge is None else {v.id: v for v in knowledge.beliefs}
    acquisitions = tuple(v for v in claims if isinstance(v, AcquisitionClaim))
    issues: list[_Issue] = []

    def evidence(
        holder: EntityId | None,
        fact_id: EntityId | None,
        source_id: EntityId | None,
        index: int,
    ) -> _Issue | None:
        if source_id is None or knowledge is None:
            return "UNKNOWN", Q1Finding("KNOWLEDGE_SOURCE_UNAVAILABLE", index)
        if source_id.project != state.project:
            return "FAIL", Q1Finding("CROSS_PROJECT_KNOWLEDGE_SOURCE", index)
        source = observations.get(source_id)
        if source is None:
            return "UNKNOWN", Q1Finding("KNOWLEDGE_SOURCE_UNAVAILABLE", index)
        if source.fact_id != fact_id or holder not in source.witnesses:
            return "FAIL", Q1Finding("KNOWLEDGE_SOURCE_FACT_OR_WITNESS_MISMATCH", index)
        return None

    def parent_known(holder: EntityId, fact_id: EntityId) -> bool:
        if knowledge is None:
            return False
        try:
            knowledge.require_known(holder, fact_id)
        except ValueError:
            return False
        return any(h == holder and f == fact_id for h, f, _ in knowledge.knowledge)

    for index, claim in enumerate(claims):
        if isinstance(claim, ReaderRevealClaim):
            issue = _fact(state, claim.fact_id, index)
            if issue is not None:
                issues.append(issue)
            else:
                snapshot = state.baseline.get(cast(EntityId, claim.fact_id))
                if snapshot is None:
                    raise Q1Error("INVALID_Q1_KNOWLEDGE_INPUT")
                if snapshot.state.status is not FactStatus.KNOWN:
                    issues.append(
                        (
                            "UNKNOWN",
                            Q1Finding("READER_FACT_NOT_KNOWN_IN_FROZEN_VIEW", index),
                        )
                    )
            continue
        holder = claim.holder
        issue = _entity(state, holder, index, "HOLDER")
        if issue is not None:
            issues.append(issue)
            continue
        if isinstance(claim, BeliefClaim):
            if claim.belief_id is None or knowledge is None:
                issues.append(
                    ("UNKNOWN", Q1Finding("BELIEF_SOURCE_UNAVAILABLE", index))
                )
            elif claim.belief_id.project != state.project:
                issues.append(("FAIL", Q1Finding("CROSS_PROJECT_BELIEF", index)))
            elif claim.belief_id not in beliefs:
                issues.append(
                    ("UNKNOWN", Q1Finding("BELIEF_SOURCE_UNAVAILABLE", index))
                )
            elif beliefs[claim.belief_id].holder != holder:
                issues.append(("FAIL", Q1Finding("BELIEF_HOLDER_MISMATCH", index)))
            continue
        issue = _fact(state, claim.fact_id, index)
        if issue is not None:
            issues.append(issue)
            continue
        holder_id, fact_id = cast(EntityId, holder), cast(EntityId, claim.fact_id)
        if isinstance(claim, AcquisitionClaim):
            issue = evidence(holder_id, fact_id, claim.source_id, index)
            if issue is not None:
                issues.append(issue)
            if claim.at is None or claim.at.kind is TimeKind.UNKNOWN:
                issues.append(
                    ("UNKNOWN", Q1Finding("ACQUISITION_TIME_UNPROVEN", index))
                )
            continue
        if claim.source_id is not None:
            issue = evidence(holder_id, fact_id, claim.source_id, index)
            if issue is not None:
                issues.append(issue)
                continue
        if parent_known(holder_id, fact_id):
            # Validate a named source first, but never let its later confirmation
            # erase knowledge already established by a different valid source.
            continue
        matching = tuple(
            v
            for v in acquisitions
            if v.holder == holder_id
            and v.fact_id == fact_id
            and evidence(v.holder, v.fact_id, v.source_id, index) is None
        )
        orders = tuple(_order(v.at, claim.at) for v in matching)
        if "BEFORE" in orders:
            # An acquisition does not retract an existing contrary belief.
            # Project only this candidate learning on a private copy and retain
            # the domain's CONTRADICTORY result instead of fabricating KNOWN.
            earlier = next(v for v in matching if _order(v.at, claim.at) == "BEFORE")
            if knowledge is None:
                raise Q1Error("INVALID_Q1_KNOWLEDGE_INPUT")
            projected = KnowledgeState.from_dict(knowledge.to_dict())
            try:
                projected.learn(holder_id, fact_id, cast(EntityId, earlier.source_id))
                projected.require_known(holder_id, fact_id)
            except ValueError:
                issues.append(
                    ("UNKNOWN", Q1Finding("ACQUIRED_KNOWLEDGE_CONFLICT", index))
                )
            continue
        named_orders = tuple(
            _order(v.at, claim.at) for v in matching if v.source_id == claim.source_id
        )
        if (
            claim.source_id is not None
            and named_orders
            and all(v == "AFTER" for v in named_orders)
        ):
            issues.append(("FAIL", Q1Finding("KNOWLEDGE_SOURCE_AFTER_USE", index)))
        else:
            # UNKNOWN and an incomplete list are not evidence of prior ignorance.
            issues.append(("UNKNOWN", Q1Finding("KNOWLEDGE_AT_USE_UNPROVEN", index)))
    return _result(issues, applicable=bool(claims))


_EXEC_FIELDS = {
    "record_type",
    "schema_version",
    "profile",
    "registry_hash",
    "check_id",
    "input_hash",
    "request_id",
    "attempt_id",
    "execution_status",
    "started_at",
    "finished_at",
    "result_base64",
    "result_hash",
    "result",
}


def _request(check_id: str, input_hash: str) -> str:
    return _hash(
        canonical_bytes(
            {
                "registry_hash": REGISTRY_HASH,
                "check_id": check_id,
                "input_hash": input_hash,
            }
        )
    )


@dataclass(frozen=True, slots=True)
class Q1Execution:
    payload: bytes = field(repr=False)
    _result: Q1CheckResult | None = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        try:
            row = _record(decode_canonical(self.payload), _EXEC_FIELDS)
            if (
                row["record_type"] != "local_q1_execution"
                or row["schema_version"] != "1.0"
                or row["profile"] != PROFILE
                or row["registry_hash"] != REGISTRY_HASH
            ):
                raise ValueError
            check_id = row["check_id"]
            if (
                type(check_id) is not str
                or check_id not in CHECK_IDS
                or row["request_id"] != _request(check_id, _digest(row["input_hash"]))
                or type(row["attempt_id"]) is not str
                or re.fullmatch(r"[0-9a-f]{32}", row["attempt_id"]) is None
            ):
                raise ValueError
            started = _time(row["started_at"])
            status = row["execution_status"]
            if type(status) is not str or status not in {
                "RUNNING",
                "FINISHED",
                "INTERRUPTED",
            }:
                raise ValueError
            result = None
            if status == "FINISHED":
                if _time(row["finished_at"]) < started:
                    raise ValueError
                raw = _decoded(row["result_base64"])
                result = Q1CheckResult.from_dict(decode_canonical(raw))
                if (
                    result.payload_bytes() != raw
                    or _hash(raw) != row["result_hash"]
                    or canonical_bytes(result.to_dict())
                    != canonical_bytes(row["result"])
                ):
                    raise ValueError
            elif any(
                row[v] is not None
                for v in ("finished_at", "result_base64", "result_hash", "result")
            ):
                raise ValueError
            if canonical_bytes(row) != self.payload:
                raise ValueError
            object.__setattr__(self, "_result", result)
        except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
            raise Q1Error("INVALID_Q1_EXECUTION") from None

    @property
    def result(self) -> Q1CheckResult | None:
        return self._result

    @property
    def verdict(self) -> str | None:
        return None if self.result is None else self.result.verdict

    @property
    def check_id(self) -> str:
        return cast(str, self.to_dict()["check_id"])

    @property
    def input_hash(self) -> str:
        return cast(str, self.to_dict()["input_hash"])

    @property
    def execution_status(self) -> str:
        return cast(str, self.to_dict()["execution_status"])

    @property
    def result_bytes(self) -> bytes | None:
        return None if self.result is None else self.result.payload_bytes()

    @property
    def result_hash(self) -> str | None:
        return None if self.result_bytes is None else _hash(self.result_bytes)

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    def payload_bytes(self) -> bytes:
        return self.payload

    @classmethod
    def from_dict(cls, value: object) -> Q1Execution:
        return cls(canonical_bytes(value))

    @classmethod
    def from_bytes(cls, raw: bytes) -> Q1Execution:
        return cls(raw)

    @property
    def record_hash(self) -> str:
        return _hash(self.payload)


def _execute(
    check_id: str, input_hash: str, method: Callable[[], Q1CheckResult]
) -> Q1Execution:
    started = utc_timestamp(datetime.now(UTC))
    try:
        result = method()
        if type(result) is not Q1CheckResult:
            raise ValueError
    except Exception:
        result = Q1CheckResult(
            "APPLICABLE", "ERROR", (Q1Finding("Q1_NATIVE_EXECUTION_ERROR"),)
        )
    raw = result.payload_bytes()
    return Q1Execution.from_dict(
        {
            "record_type": "local_q1_execution",
            "schema_version": "1.0",
            "profile": PROFILE,
            "registry_hash": REGISTRY_HASH,
            "check_id": check_id,
            "input_hash": input_hash,
            "request_id": _request(check_id, input_hash),
            "attempt_id": uuid4().hex,
            "execution_status": "FINISHED",
            "started_at": started,
            "finished_at": utc_timestamp(datetime.now(UTC)),
            "result_base64": _encoded(raw),
            "result_hash": _hash(raw),
            "result": result.to_dict(),
        }
    )


def _input_hash(
    observation: ExtractionObservation, annotations: BoundQ1Annotations, state: Q1State
) -> str:
    return _hash(
        canonical_bytes(
            {
                "observation_hash": observation.record_hash,
                "annotations_hash": annotations.record_hash,
                "state_hash": state.content_hash,
                "registry_hash": REGISTRY_HASH,
            }
        )
    )


def _status(executions: tuple[Q1Execution, ...]) -> str:
    verdicts = tuple(v.verdict for v in executions)
    for value in ("FAIL", "ERROR", "UNKNOWN"):
        if value in verdicts:
            return value
    if (
        tuple(v.check_id for v in executions) != CHECK_IDS
        or any(v.execution_status != "FINISHED" for v in executions)
        or not any(v == "PASS" for v in verdicts)
    ):
        return "UNKNOWN"
    return "PASS"


def _run_record(
    observation: ExtractionObservation,
    annotations: BoundQ1Annotations,
    state: Q1State,
    knowledge_source: str,
    executions: tuple[Q1Execution, ...],
) -> dict[str, object]:
    return {
        "record_type": "local_q1_run",
        "schema_version": "1.0",
        "profile": PROFILE,
        "registry_hash": REGISTRY_HASH,
        "evidence_scope": PROFILE,
        "source_qualification": "AUTHOR_INPUT_LOCAL_TEST",
        "baseline_source": "FROZEN_SPECIFIED_PARENT_NOT_CURRENT_HEAD",
        "knowledge_source": knowledge_source,
        "canon_currentness": "UNKNOWN",
        "production_status": "UNKNOWN",
        "semantic_status": "UNKNOWN",
        "coverage_status": "NOT_VERIFIED",
        "aggregate_status": "BLOCKED",
        "observation_base64": _encoded(observation.payload_bytes()),
        "annotations_base64": _encoded(annotations.payload_bytes()),
        "state_hash": state.content_hash,
        "input_hash": _input_hash(observation, annotations, state),
        "observation_hash": observation.record_hash,
        "annotations_hash": annotations.record_hash,
        "assembly_hash": observation.assembly_hash,
        "prose_hash": observation.prose_hash,
        "project": observation.project,
        "branch": observation.branch,
        "run_id": observation.run_id,
        "step_id": observation.step_id,
        "executions": [v.to_dict() for v in executions],
        "q1_status": _status(executions),
        **_FALSE,
    }


_RUN_FIELDS = {
    "record_type",
    "schema_version",
    "profile",
    "registry_hash",
    "evidence_scope",
    "source_qualification",
    "baseline_source",
    "knowledge_source",
    "canon_currentness",
    "production_status",
    "semantic_status",
    "coverage_status",
    "aggregate_status",
    "observation_base64",
    "annotations_base64",
    "state_hash",
    "input_hash",
    "observation_hash",
    "annotations_hash",
    "assembly_hash",
    "prose_hash",
    "project",
    "branch",
    "run_id",
    "step_id",
    "executions",
    "q1_status",
    *_FALSE,
}


@dataclass(frozen=True, slots=True)
class Q1Run:
    payload: bytes = field(repr=False)
    _observation: ExtractionObservation = field(init=False, repr=False, compare=False)
    _annotations: BoundQ1Annotations = field(init=False, repr=False, compare=False)
    _executions: tuple[Q1Execution, ...] = field(init=False, repr=False, compare=False)
    _token: object | None = field(init=False, default=None, repr=False, compare=False)
    _token_hash: str | None = field(init=False, default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        from anovel.workflow.extractor import ExtractionObservation

        try:
            row = _record(decode_canonical(self.payload), _RUN_FIELDS)
            observation = ExtractionObservation.from_bytes(
                _decoded(row["observation_base64"])
            )
            annotations = BoundQ1Annotations.from_bytes(
                _decoded(row["annotations_base64"])
            )
            state, source = _bound_state(annotations, observation)
            if type(row["executions"]) is not list:
                raise ValueError
            executions = tuple(Q1Execution.from_dict(v) for v in row["executions"])
            input_hash = _input_hash(observation, annotations, state)
            if (
                tuple(v.check_id for v in executions) != CHECK_IDS
                or any(v.execution_status != "FINISHED" for v in executions)
                or any(v.input_hash != input_hash for v in executions)
                or canonical_bytes(
                    _run_record(observation, annotations, state, source, executions)
                )
                != self.payload
            ):
                raise ValueError
            object.__setattr__(self, "_observation", observation)
            object.__setattr__(self, "_annotations", annotations)
            object.__setattr__(self, "_executions", executions)
        except (
            TypeError,
            ValueError,
            KeyError,
            AttributeError,
            StopIteration,
            RecursionError,
        ):
            raise Q1Error("INVALID_Q1_RUN") from None

    @property
    def observation(self) -> ExtractionObservation:
        return self._observation

    @property
    def annotations(self) -> BoundQ1Annotations:
        return self._annotations

    @property
    def executions(self) -> tuple[Q1Execution, ...]:
        return self._executions

    def payload_bytes(self) -> bytes:
        return self.payload

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    @classmethod
    def from_dict(cls, value: object) -> Q1Run:
        return cls(canonical_bytes(value))

    @classmethod
    def from_bytes(cls, raw: bytes) -> Q1Run:
        return cls(raw)

    @property
    def record_hash(self) -> str:
        return _hash(self.payload)

    @property
    def content_hash(self) -> str:
        return self.record_hash

    @property
    def project(self) -> str:
        return self.observation.project

    @property
    def branch(self) -> str:
        return self.observation.branch

    @property
    def run_id(self) -> str:
        return self.observation.run_id

    @property
    def step_id(self) -> str:
        return self.observation.step_id

    @property
    def observation_hash(self) -> str:
        return self.observation.record_hash

    @property
    def annotations_hash(self) -> str:
        return self.annotations.record_hash

    @property
    def assembly_hash(self) -> str:
        return self.observation.assembly_hash

    @property
    def prose_hash(self) -> str:
        return self.observation.prose_hash

    @property
    def input_hash(self) -> str:
        return cast(str, self.to_dict()["input_hash"])

    @property
    def q1_status(self) -> str:
        return _status(self.executions)

    @property
    def source_qualification(self) -> str:
        return "AUTHOR_INPUT_LOCAL_TEST"

    @property
    def knowledge_source(self) -> str:
        return cast(str, self.to_dict()["knowledge_source"])

    @property
    def coverage_status(self) -> str:
        return "NOT_VERIFIED"

    @property
    def production_status(self) -> str:
        return "UNKNOWN"

    @property
    def semantic_status(self) -> str:
        return "UNKNOWN"

    @property
    def aggregate_status(self) -> str:
        return "BLOCKED"

    @property
    def diagnostics(self) -> tuple[Q1Finding, ...]:
        return tuple(
            f
            for v in self.executions
            if v.result is not None
            for f in v.result.findings
        )

    @property
    def can_commit(self) -> bool:
        return False

    @property
    def can_issue_permit(self) -> bool:
        return False

    @property
    def can_dispatch(self) -> bool:
        return False

    @property
    def accepted(self) -> bool:
        return False

    @property
    def published(self) -> bool:
        return False


def require_local_execution_q1(run: Q1Run) -> None:
    """A local publication guard, not a defense against a same-owner writer."""
    if (
        type(run) is not Q1Run
        or run._token is not _TOKEN
        or run._token_hash != run.record_hash
    ):
        raise Q1Error("Q1_NATIVE_EXECUTION_REQUIRED")


def execute_local_q1(
    observation: ExtractionObservation, annotations: BoundQ1Annotations
) -> Q1Run:
    """Execute four fixed conditional checks; no finder or authority arguments."""
    state, source = _bound_state(annotations, observation)
    input_hash = _input_hash(observation, annotations, state)
    relations = tuple(v for v in annotations.claims if type(v) is RelationClaim)
    activities = tuple(v for v in annotations.claims if type(v) is ActivityClaim)
    knowledge = tuple(
        v
        for v in annotations.claims
        if type(v)
        in {KnowledgeUseClaim, AcquisitionClaim, BeliefClaim, ReaderRevealClaim}
    )
    executions = (
        _execute(
            CHECK_IDS[0],
            input_hash,
            lambda: check_preconditions(
                state, observation.proposal_delta, source_id=observation.source_id
            ),
        ),
        _execute(CHECK_IDS[1], input_hash, lambda: check_relations(state, relations)),
        _execute(CHECK_IDS[2], input_hash, lambda: check_lifecycle(state, activities)),
        _execute(
            CHECK_IDS[3],
            input_hash,
            lambda: check_knowledge(state, cast(tuple[KnowledgeClaim, ...], knowledge)),
        ),
    )
    run = Q1Run(
        canonical_bytes(
            _run_record(observation, annotations, state, source, executions)
        )
    )
    object.__setattr__(run, "_token", _TOKEN)
    object.__setattr__(run, "_token_hash", run.record_hash)
    return run
