"""Frozen compiled inputs and source-bound chapter constraints.

Read ports establish an accepted historical target, not latest-HEAD freshness.
Restored values/hashes are reproducible data, never independent authorization.
Complete retained author inputs must not be sent directly to a Writer.
"""

from __future__ import annotations

import re
from base64 import b64decode, b64encode
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Protocol, cast

from anovel.canon.chapter import ChapterCandidate, StoredChapter
from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.canon.models import CommitReceipt, RootSeed, StoredRoot
from anovel.canon.projection import RebuiltSnapshot
from anovel.domain.delta import (
    FactBaseline,
    FactPath,
    FactState,
    FactStatus,
    MarkUnknown,
    NoChange,
    Operation,
    OperationMeta,
    Precondition,
    RetractFact,
    SetFact,
)
from anovel.domain.identity import EntityId
from anovel.domain.knowledge import KnowledgeState
from anovel.genre.policy import GenrePolicy
from anovel.planning.models import RequiredTransition, ScenePlan, StoryFixture
from anovel.planning.replanning import InputIdentity
from anovel.planning.versions import PlanHistory, PlanVersion

COMPILER_VERSION = "1.0.0"
COMPILER_HASH = sha256(
    canonical_bytes(
        {
            "version": COMPILER_VERSION,
            "delta": "FACT_DELTA-1",
            "preconditions": "actual frozen baseline; strict original reducer",
            "continuity": "accepted raw UTF-8 hash and Unicode ending span",
            "scope": "finite structured planning only; no prose or Permit approval",
        }
    )
).hexdigest()


class ContractError(ValueError):
    """Malformed, stale or inconsistent compilation input."""


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise ContractError(f"{field} must be nonempty text")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise ContractError(f"{field} must be valid Unicode") from error
    return value


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ContractError("expected lowercase SHA256")
    return value


def _commit(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
        raise ContractError("expected actual Canon commit identity")
    return value


def _integer(value: object, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ContractError(f"{field} requires an exact integer >= {minimum}")
    return value


def _record(value: object, keys: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise ContractError("contract fields must be exact and closed")
    return cast(dict[str, object], value)


def _array(value: object) -> list[object]:
    if type(value) is not list:
        raise ContractError("contract members must be arrays")
    return cast(list[object], value)


def _id(value: object) -> EntityId:
    if type(value) is not EntityId:
        raise ContractError("an exact EntityId is required")
    return value


def _encoded(value: bytes) -> str:
    return b64encode(value).decode("ascii")


def _decoded(value: object) -> bytes:
    if type(value) is not str:
        raise ContractError("retained bytes must be base64")
    try:
        result = b64decode(value, validate=True)
    except ValueError as error:
        raise ContractError("invalid base64") from error
    if _encoded(result) != value:
        raise ContractError("noncanonical base64")
    return result


class CanonReadPort(Protocol):
    def rebuild_snapshot(
        self, project: str, branch: str, commit_id: str
    ) -> RebuiltSnapshot: ...

    def load_root(self, project: str, branch: str, commit_id: str) -> StoredRoot: ...

    def load_commit(
        self, project: str, branch: str, commit_id: str
    ) -> StoredChapter: ...


@dataclass(frozen=True, slots=True)
class PredecessorSnapshot:
    """Only predecessor fields consumed by compilation, never nested artifacts.

    The full accepted candidate/Permit/dependencies remain in Canon. A restored
    projection is data, not independent proof that the source was accepted.
    """

    receipt: CommitReceipt
    candidate_id: EntityId
    parent_ref: str
    prose: bytes
    state: FactBaseline

    def __post_init__(self) -> None:
        if (
            type(self.receipt) is not CommitReceipt
            or type(self.state) is not FactBaseline
        ):
            raise ContractError("predecessor needs exact receipt and state")
        _id(self.candidate_id)
        _commit(self.parent_ref)
        if (
            self.candidate_id.project,
            self.state.project,
            self.state.branch,
            self.state.parent_ref,
        ) != (
            self.receipt.project,
            self.receipt.project,
            self.receipt.branch,
            self.parent_ref,
        ):
            raise ContractError("predecessor projection crosses scope or parent")
        if type(self.prose) is not bytes or not self.prose:
            raise ContractError("predecessor prose needs complete immutable bytes")
        try:
            self.prose.decode("utf-8")
        except UnicodeError as error:
            raise ContractError("predecessor prose must be UTF-8") from error

    @classmethod
    def from_stored(cls, previous: StoredChapter) -> PredecessorSnapshot:
        if (
            type(previous) is not StoredChapter
            or type(previous.candidate) is not ChapterCandidate
        ):
            raise ContractError("an exact accepted source chapter is required")
        candidate = previous.candidate
        if (
            candidate.payload_hash != previous.receipt.payload_hash
            or candidate.branch != previous.receipt.branch
        ):
            raise ContractError("accepted candidate and source receipt differ")
        return cls(
            previous.receipt,
            candidate.id,
            candidate.parent_ref,
            candidate.prose,
            previous.state,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "CANON_PREDECESSOR_COMPILATION_INPUT",
            "schema_version": "1.0",
            "receipt": self.receipt.to_dict(),
            "candidate_id": self.candidate_id.to_dict(),
            "parent_ref": self.parent_ref,
            "prose_base64": _encoded(self.prose),
            "state": self.state.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> PredecessorSnapshot:
        row = _record(
            value,
            {
                "kind",
                "schema_version",
                "receipt",
                "candidate_id",
                "parent_ref",
                "prose_base64",
                "state",
            },
        )
        if (row["kind"], row["schema_version"]) != (
            "CANON_PREDECESSOR_COMPILATION_INPUT",
            "1.0",
        ):
            raise ContractError("unsupported predecessor projection")
        return cls(
            CommitReceipt.from_dict(row["receipt"]),
            EntityId.from_dict(row["candidate_id"]),
            _commit(row["parent_ref"]),
            _decoded(row["prose_base64"]),
            FactBaseline.from_dict(row["state"]),
        )


@dataclass(frozen=True, slots=True, init=False)
class CanonView:
    root: StoredRoot
    baseline: FactBaseline
    previous: PredecessorSnapshot | None
    next_chapter: int

    def __init__(
        self,
        root: StoredRoot,
        baseline: FactBaseline,
        previous: StoredChapter | PredecessorSnapshot | None,
        next_chapter: int,
    ) -> None:
        object.__setattr__(self, "root", root)
        object.__setattr__(self, "baseline", baseline)
        object.__setattr__(
            self,
            "previous",
            PredecessorSnapshot.from_stored(previous)
            if type(previous) is StoredChapter
            else previous,
        )
        object.__setattr__(self, "next_chapter", next_chapter)
        self.__post_init__()

    def __post_init__(self) -> None:
        if type(self.root) is not StoredRoot or type(self.baseline) is not FactBaseline:
            raise ContractError("view needs exact root and baseline values")
        if (
            type(self.root.receipt) is not CommitReceipt
            or type(self.root.seed) is not RootSeed
            or type(self.root.prose) is not bytes
            or not self.root.prose
            or type(self.root.authority_bytes) is not bytes
            or not self.root.authority_bytes
        ):
            raise ContractError("root read values must retain immutable complete bytes")
        try:
            self.root.prose.decode("utf-8")
        except UnicodeError as error:
            raise ContractError("retained root prose must be UTF-8") from error
        _integer(self.next_chapter, "next chapter", 1)
        _commit(self.baseline.parent_ref)
        if (self.root.receipt.project, self.root.receipt.branch) != (
            self.project,
            self.branch,
        ):
            raise ContractError("root and read view cross project or branch")
        if self.root.seed.project != self.project:
            raise ContractError("root seed crosses project")
        if {v.id: v for v in self.root.seed.facts} != {
            v.seed_fact.id: v.seed_fact for v in self.baseline.facts
        } or self.baseline.extensions != self.root.seed.extensions:
            raise ContractError(
                "read view changes root fact identity or extension binding"
            )
        if self.previous is None:
            if self.next_chapter != 1 or self.root.receipt.commit_id != self.parent_ref:
                raise ContractError("first chapter must be anchored at the actual root")
            initial = FactBaseline.from_world_facts(
                self.project,
                self.branch,
                self.parent_ref,
                self.root.seed.facts,
                extensions=self.root.seed.extensions,
            )
            if {v.seed_fact.id: v for v in initial.facts} != {
                v.seed_fact.id: v for v in self.baseline.facts
            }:
                raise ContractError("root baseline differs from retained initial facts")
        elif type(self.previous) is not PredecessorSnapshot or self.next_chapter <= 1:
            raise ContractError("subsequent chapter needs its retained predecessor")
        elif (
            self.previous.receipt.commit_id != self.parent_ref
            or replace(self.previous.state, parent_ref=self.parent_ref) != self.baseline
        ):
            raise ContractError("predecessor and re-anchored read state differ")

    @property
    def project(self) -> str:
        return self.baseline.project

    @property
    def branch(self) -> str:
        return self.baseline.branch

    @property
    def parent_ref(self) -> str:
        return self.baseline.parent_ref

    @classmethod
    def from_service(
        cls, service: CanonReadPort, project: str, branch: str, parent_ref: str
    ) -> CanonView:
        _commit(parent_ref)
        rebuilt = service.rebuild_snapshot(project, branch, parent_ref)
        checks = rebuilt.checkpoints
        if (
            not checks
            or checks[0].sequence != 0
            or checks[0].event_type != "ROOT_INITIALIZED"
            or tuple(v.sequence for v in checks) != tuple(range(len(checks)))
        ):
            raise ContractError("accepted history checkpoints are incomplete")
        if (
            rebuilt.receipt.commit_id != parent_ref
            or rebuilt.baseline.parent_ref != parent_ref
            or (rebuilt.baseline.project, rebuilt.baseline.branch) != (project, branch)
            or checks[-1].commit_id != parent_ref
        ):
            raise ContractError(
                "read response does not match the requested accepted target"
            )
        root = service.load_root(project, branch, checks[0].commit_id)
        previous = (
            None
            if len(checks) == 1
            else service.load_commit(project, branch, parent_ref)
        )
        return cls(root, rebuilt.baseline, previous, len(checks))

    def to_dict(self) -> dict[str, object]:
        previous = self.previous
        return {
            "kind": "CANON_COMPILATION_VIEW",
            "schema_version": "1.0",
            "root": {
                "receipt": self.root.receipt.to_dict(),
                "seed": self.root.seed.to_dict(),
                "prose_base64": _encoded(self.root.prose),
                "authority_base64": _encoded(self.root.authority_bytes),
            },
            "baseline": self.baseline.to_dict(),
            "previous": None if previous is None else previous.to_dict(),
            "next_chapter": self.next_chapter,
        }

    @classmethod
    def from_dict(cls, value: object) -> CanonView:
        row = _record(
            value,
            {"kind", "schema_version", "root", "baseline", "previous", "next_chapter"},
        )
        if (row["kind"], row["schema_version"]) != ("CANON_COMPILATION_VIEW", "1.0"):
            raise ContractError("unsupported Canon view format")
        root = _record(
            row["root"], {"receipt", "seed", "prose_base64", "authority_base64"}
        )
        previous = None
        if row["previous"] is not None:
            previous = PredecessorSnapshot.from_dict(row["previous"])
        return cls(
            StoredRoot(
                CommitReceipt.from_dict(root["receipt"]),
                RootSeed.from_dict(root["seed"]),
                _decoded(root["prose_base64"]),
                _decoded(root["authority_base64"]),
            ),
            FactBaseline.from_dict(row["baseline"]),
            previous,
            _integer(row["next_chapter"], "next chapter", 1),
        )

    @property
    def content_hash(self) -> str:
        return sha256(canonical_bytes(self.to_dict())).hexdigest()


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    """Explicit current author input, never a claimed Canon knowledge store."""

    project: str
    parent_ref: str
    source_ref: str
    knowledge_bytes: bytes

    def __post_init__(self) -> None:
        _text(self.project, "project")
        _commit(self.parent_ref)
        _text(self.source_ref, "knowledge source")
        if type(self.knowledge_bytes) is not bytes or not self.knowledge_bytes:
            raise ContractError("knowledge needs complete immutable bytes")
        state = self.knowledge
        if (
            state.project != self.project
            or canonical_bytes(state.to_dict()) != self.knowledge_bytes
        ):
            raise ContractError("knowledge snapshot scope or canonical bytes differ")

    @property
    def knowledge(self) -> KnowledgeState:
        return KnowledgeState.from_dict(decode_canonical(self.knowledge_bytes))

    def validate_against(self, view: CanonView) -> None:
        if type(view) is not CanonView or (self.project, self.parent_ref) != (
            view.project,
            view.parent_ref,
        ):
            raise ContractError("knowledge snapshot belongs to a different parent")
        state = self.knowledge
        entities = {v.id for v in view.root.seed.entities}
        if any(v.id not in entities for v in state.characters) or any(
            v.proposition.subject not in entities for v in state.beliefs
        ):
            raise ContractError("knowledge character or belief subject is unregistered")
        for fact in state.facts:
            actual = view.baseline.get(fact.id)
            if (
                actual is None
                or actual.state.status is not FactStatus.KNOWN
                or (
                    fact.proposition.subject != actual.seed_fact.proposition.subject
                    or fact.proposition.predicate
                    != actual.seed_fact.proposition.predicate
                    or FactState.known(fact.proposition.value) != actual.state
                )
            ):
                raise ContractError("knowledge world facts differ from current Canon")

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "PLANNING_KNOWLEDGE_SNAPSHOT",
            "schema_version": "1.0",
            "project": self.project,
            "parent_ref": self.parent_ref,
            "source_ref": self.source_ref,
            "knowledge_base64": _encoded(self.knowledge_bytes),
        }

    @classmethod
    def from_dict(cls, value: object) -> KnowledgeSnapshot:
        row = _record(
            value,
            {
                "kind",
                "schema_version",
                "project",
                "parent_ref",
                "source_ref",
                "knowledge_base64",
            },
        )
        if (row["kind"], row["schema_version"]) != (
            "PLANNING_KNOWLEDGE_SNAPSHOT",
            "1.0",
        ):
            raise ContractError("unsupported knowledge snapshot format")
        return cls(
            _text(row["project"], "project"),
            _commit(row["parent_ref"]),
            _text(row["source_ref"], "source"),
            _decoded(row["knowledge_base64"]),
        )


@dataclass(frozen=True, slots=True)
class ContinuationEvidence:
    previous_commit_id: str
    candidate_id: EntityId
    prose_hash: str
    start: int
    end: int
    quote: str
    end_time: str = "UNKNOWN"
    end_location: str = "UNKNOWN"
    pov: str = "UNKNOWN"
    unfinished_action: str = "UNKNOWN"
    evidence_ref: str = "supplied-ending-evidence"

    def __post_init__(self) -> None:
        _commit(self.previous_commit_id)
        _id(self.candidate_id)
        _digest(self.prose_hash)
        _integer(self.start, "start")
        _integer(self.end, "end", 1)
        if self.end <= self.start:
            raise ContractError("ending span must be nonempty")
        for name in (
            "quote",
            "end_time",
            "end_location",
            "pov",
            "unfinished_action",
            "evidence_ref",
        ):
            _text(getattr(self, name), name)

    @classmethod
    def from_previous(
        cls,
        previous: StoredChapter | PredecessorSnapshot,
        start: int = 0,
        **semantics: str,
    ) -> ContinuationEvidence:
        if type(previous) is StoredChapter:
            previous = PredecessorSnapshot.from_stored(previous)
        if type(previous) is not PredecessorSnapshot:
            raise ContractError("retained accepted predecessor input is required")
        text = previous.prose.decode("utf-8")
        return cls(
            previous.receipt.commit_id,
            previous.candidate_id,
            sha256(previous.prose).hexdigest(),
            start,
            len(text),
            text[start:],
            **semantics,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "previous_commit_id": self.previous_commit_id,
            "candidate_id": self.candidate_id.to_dict(),
            "prose_hash": self.prose_hash,
            "start": self.start,
            "end": self.end,
            "quote": self.quote,
            "end_time": self.end_time,
            "end_location": self.end_location,
            "pov": self.pov,
            "unfinished_action": self.unfinished_action,
            "evidence_ref": self.evidence_ref,
        }

    @classmethod
    def from_dict(cls, value: object) -> ContinuationEvidence:
        row = _record(
            value,
            {
                "previous_commit_id",
                "candidate_id",
                "prose_hash",
                "start",
                "end",
                "quote",
                "end_time",
                "end_location",
                "pov",
                "unfinished_action",
                "evidence_ref",
            },
        )
        return cls(
            _commit(row["previous_commit_id"]),
            EntityId.from_dict(row["candidate_id"]),
            _digest(row["prose_hash"]),
            _integer(row["start"], "start"),
            _integer(row["end"], "end", 1),
            *(
                _text(row[n], n)
                for n in (
                    "quote",
                    "end_time",
                    "end_location",
                    "pov",
                    "unfinished_action",
                    "evidence_ref",
                )
            ),
        )

    @property
    def content_hash(self) -> str:
        return sha256(canonical_bytes(self.to_dict())).hexdigest()


@dataclass(frozen=True, slots=True)
class BoundTransition:
    spec: RequiredTransition
    expected: Precondition

    def __post_init__(self) -> None:
        if (
            type(self.spec) is not RequiredTransition
            or type(self.expected) is not Precondition
        ):
            raise ContractError("a bound transition needs actual registered types")
        if (
            self.spec.expected_state is not None
            and self.spec.expected_state != self.expected.state
        ):
            raise ContractError(
                "bound precondition differs from explicit plan expectation"
            )

    @property
    def target_id(self) -> EntityId:
        return self.spec.target_id

    def materialize(self, meta: OperationMeta) -> Operation:
        if (
            type(meta) is not OperationMeta
            or meta.target_id != self.target_id
            or meta.path is not FactPath.VALUE
            or meta.expected != self.expected
        ):
            raise ContractError(
                "future operation must preserve bound target, path and full precondition"
            )
        if self.spec.operation.value == "SET_FACT":
            if self.spec.value is None:
                raise ContractError("SET_FACT needs its finite scalar value")
            return SetFact(meta, self.spec.value)
        if self.spec.operation.value == "MARK_UNKNOWN":
            return MarkUnknown(meta)
        if self.spec.operation.value == "RETRACT_FACT":
            return RetractFact(meta)
        if self.spec.operation.value == "NO_CHANGE":
            return NoChange(meta)
        raise ContractError("unregistered transition operation")

    def to_dict(self) -> dict[str, object]:
        return {"spec": self.spec.to_dict(), "expected": self.expected.to_dict()}

    @classmethod
    def from_dict(cls, value: object) -> BoundTransition:
        row = _record(value, {"spec", "expected"})
        return cls(
            RequiredTransition.from_dict(row["spec"]),
            Precondition.from_dict(row["expected"]),
        )


@dataclass(frozen=True, slots=True)
class CompiledScene:
    plan: ScenePlan
    required: tuple[BoundTransition, ...]

    def __post_init__(self) -> None:
        if (
            type(self.plan) is not ScenePlan
            or type(self.required) is not tuple
            or any(type(v) is not BoundTransition for v in self.required)
        ):
            raise ContractError("compiled scene requires exact immutable members")
        if tuple(v.spec for v in self.required) != self.plan.required:
            raise ContractError(
                "compiled scene differs from its complete required plan"
            )

    @property
    def id(self) -> EntityId:
        return self.plan.id

    def to_dict(self) -> dict[str, object]:
        return {
            "plan": self.plan.to_dict(),
            "required": [v.to_dict() for v in self.required],
        }

    @classmethod
    def from_dict(cls, value: object) -> CompiledScene:
        row = _record(value, {"plan", "required"})
        return cls(
            ScenePlan.from_dict(row["plan"]),
            tuple(BoundTransition.from_dict(v) for v in _array(row["required"])),
        )


@dataclass(frozen=True, slots=True)
class RetainedInput:
    name: str
    content: bytes
    visibility: str = "AUTHOR_REVIEW_ONLY"

    def __post_init__(self) -> None:
        _text(self.name, "input name")
        if (
            type(self.content) is not bytes
            or canonical_bytes(decode_canonical(self.content)) != self.content
        ):
            raise ContractError("input needs complete canonical bytes")
        if self.visibility != "AUTHOR_REVIEW_ONLY":
            raise ContractError("unfiltered author inputs cannot be Writer-visible")

    @property
    def content_hash(self) -> str:
        return sha256(self.content).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "content_base64": _encoded(self.content),
            "sha256": self.content_hash,
            "visibility": self.visibility,
        }

    @classmethod
    def from_dict(cls, value: object) -> RetainedInput:
        row = _record(value, {"name", "content_base64", "sha256", "visibility"})
        result = cls(
            _text(row["name"], "name"),
            _decoded(row["content_base64"]),
            _text(row["visibility"], "visibility"),
        )
        if _digest(row["sha256"]) != result.content_hash:
            raise ContractError("retained input hash mismatch")
        return result


@dataclass(frozen=True, slots=True)
class CompiledContract:
    project: str
    branch: str
    parent_ref: str
    chapter_id: EntityId
    chapter_number: int
    plan_id: EntityId
    plan_revision: int
    plan_hash: str
    fixture_hash: str
    canon_hash: str
    pack_hash: str
    knowledge_hash: str
    continuity_hash: str
    policy_version: str
    policy_hash: str
    scenes: tuple[CompiledScene, ...]
    retained_inputs: tuple[RetainedInput, ...]
    compiler_version: str = COMPILER_VERSION

    def __post_init__(self) -> None:
        _text(self.project, "project")
        _text(self.branch, "branch")
        _commit(self.parent_ref)
        _id(self.chapter_id)
        _id(self.plan_id)
        _integer(self.chapter_number, "chapter number", 1)
        _integer(self.plan_revision, "plan revision", 1)
        if (
            self.chapter_id.project != self.project
            or self.plan_id.project != self.project
        ):
            raise ContractError("contract scope crosses project")
        for v in (
            self.plan_hash,
            self.fixture_hash,
            self.canon_hash,
            self.pack_hash,
            self.knowledge_hash,
            self.continuity_hash,
            self.policy_hash,
        ):
            _digest(v)
        _text(self.policy_version, "policy version")
        if self.compiler_version != COMPILER_VERSION:
            raise ContractError("unsupported compiler version")
        if (
            type(self.scenes) is not tuple
            or not self.scenes
            or any(type(v) is not CompiledScene for v in self.scenes)
        ):
            raise ContractError("contract needs exact immutable compiled scenes")
        if type(self.retained_inputs) is not tuple or any(
            type(v) is not RetainedInput for v in self.retained_inputs
        ):
            raise ContractError("contract needs complete immutable source inputs")
        retained = {v.name: v for v in self.retained_inputs}
        if len(retained) != len(self.retained_inputs) or set(retained) != {
            "fixture",
            "plan",
            "plan_history",
            "canon",
            "pack",
            "knowledge",
            "continuity",
        }:
            raise ContractError("retained source inventory is incomplete or duplicated")
        fixture = StoryFixture.from_dict(decode_canonical(retained["fixture"].content))
        plan = PlanVersion.from_dict(decode_canonical(retained["plan"].content))
        history = PlanHistory.from_dict(
            decode_canonical(retained["plan_history"].content)
        )
        if history.active != plan:
            raise ContractError("retained adoption history does not select this plan")
        canon = CanonView.from_dict(decode_canonical(retained["canon"].content))
        if (
            fixture.content_hash != self.fixture_hash
            or plan.content_hash != self.plan_hash
            or canon.content_hash != self.canon_hash
        ):
            raise ContractError("retained input identities differ from declared hashes")
        if (
            canonical_bytes(fixture.pack_binding.to_dict()) != retained["pack"].content
            or fixture.pack_binding.ref.content_hash != self.pack_hash
            or retained["knowledge"].content_hash != self.knowledge_hash
            or retained["continuity"].content_hash != self.continuity_hash
        ):
            raise ContractError("retained Pack/knowledge/continuity identity differs")
        knowledge = KnowledgeSnapshot.from_dict(
            decode_canonical(retained["knowledge"].content)
        )
        knowledge.validate_against(canon)
        if (canon.project, canon.branch, canon.parent_ref, canon.next_chapter) != (
            self.project,
            self.branch,
            self.parent_ref,
            self.chapter_number,
        ) or (plan.id, plan.revision, plan.fixture_hash) != (
            self.plan_id,
            self.plan_revision,
            self.fixture_hash,
        ):
            raise ContractError("contract scope/version differs from retained inputs")
        chapters = tuple(
            c
            for arc in plan.vision.arcs
            for c in arc.chapters
            if c.id == self.chapter_id
        )
        if (
            len(chapters) != 1
            or chapters[0].number != self.chapter_number
            or tuple(v.plan for v in self.scenes) != chapters[0].scenes
        ):
            raise ContractError("compiled scenes differ from retained chapter plan")
        if fixture.review_status != "APPROVED" or fixture.review_ref is None:
            raise ContractError(
                "compiled input cannot silently upgrade a DRAFT fixture"
            )
        if canonical_bytes(fixture.root_seed.to_dict()) != canonical_bytes(
            canon.root.seed.to_dict()
        ):
            raise ContractError("fixture and actual Canon root differ")
        for item in self.required:
            snapshot = canon.baseline.get(item.target_id)
            if snapshot is None or item.expected != Precondition.from_snapshot(
                snapshot
            ):
                raise ContractError(
                    "bound precondition differs from retained actual Canon"
                )
        policy = GenrePolicy(fixture.pack_binding).check_strategy(
            fixture.pack_binding.select_strategy()
        )
        if (self.policy_version, self.policy_hash) != (
            policy.policy_version,
            policy.policy_hash,
        ):
            raise ContractError("contract uses a different registered Genre policy")

    @property
    def required(self) -> tuple[BoundTransition, ...]:
        return tuple(v for scene in self.scenes for v in scene.required)

    @property
    def content_hash(self) -> str:
        return sha256(canonical_bytes(self.to_dict())).hexdigest()

    @property
    def content_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @property
    def input_identity(self) -> InputIdentity:
        return InputIdentity(
            self.parent_ref,
            self.canon_hash,
            self.pack_hash,
            self.knowledge_hash,
            self.plan_hash,
            self.continuity_hash,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "COMPILED_CHAPTER_CONTRACT",
            "schema_version": "1.0",
            "project": self.project,
            "branch": self.branch,
            "parent_ref": self.parent_ref,
            "chapter_id": self.chapter_id.to_dict(),
            "chapter_number": self.chapter_number,
            "plan_id": self.plan_id.to_dict(),
            "plan_revision": self.plan_revision,
            "plan_hash": self.plan_hash,
            "fixture_hash": self.fixture_hash,
            "canon_hash": self.canon_hash,
            "pack_hash": self.pack_hash,
            "knowledge_hash": self.knowledge_hash,
            "continuity_hash": self.continuity_hash,
            "policy_version": self.policy_version,
            "policy_hash": self.policy_hash,
            "compiler_version": self.compiler_version,
            "compiler_hash": COMPILER_HASH,
            "scenes": [v.to_dict() for v in self.scenes],
            "retained_inputs": [v.to_dict() for v in self.retained_inputs],
        }

    @classmethod
    def from_dict(cls, value: object) -> CompiledContract:
        row = _record(
            value,
            {
                "kind",
                "schema_version",
                "project",
                "branch",
                "parent_ref",
                "chapter_id",
                "chapter_number",
                "plan_id",
                "plan_revision",
                "plan_hash",
                "fixture_hash",
                "canon_hash",
                "pack_hash",
                "knowledge_hash",
                "continuity_hash",
                "policy_version",
                "policy_hash",
                "compiler_version",
                "compiler_hash",
                "scenes",
                "retained_inputs",
            },
        )
        if (row["kind"], row["schema_version"], row["compiler_hash"]) != (
            "COMPILED_CHAPTER_CONTRACT",
            "1.0",
            COMPILER_HASH,
        ):
            raise ContractError("unsupported compiled contract format or compiler")
        return cls(
            _text(row["project"], "project"),
            _text(row["branch"], "branch"),
            _commit(row["parent_ref"]),
            EntityId.from_dict(row["chapter_id"]),
            _integer(row["chapter_number"], "chapter number", 1),
            EntityId.from_dict(row["plan_id"]),
            _integer(row["plan_revision"], "plan revision", 1),
            _digest(row["plan_hash"]),
            _digest(row["fixture_hash"]),
            _digest(row["canon_hash"]),
            _digest(row["pack_hash"]),
            _digest(row["knowledge_hash"]),
            _digest(row["continuity_hash"]),
            _text(row["policy_version"], "policy version"),
            _digest(row["policy_hash"]),
            tuple(CompiledScene.from_dict(v) for v in _array(row["scenes"])),
            tuple(RetainedInput.from_dict(v) for v in _array(row["retained_inputs"])),
            _text(row["compiler_version"], "compiler version"),
        )


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    message: str
    scene_id: EntityId | None = None

    def __post_init__(self) -> None:
        _text(self.code, "diagnostic code")
        _text(self.message, "diagnostic message")
        if self.scene_id is not None:
            _id(self.scene_id)

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "scene_id": None if self.scene_id is None else self.scene_id.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> Diagnostic:
        row = _record(value, {"code", "message", "scene_id"})
        return cls(
            _text(row["code"], "code"),
            _text(row["message"], "message"),
            None if row["scene_id"] is None else EntityId.from_dict(row["scene_id"]),
        )


@dataclass(frozen=True, slots=True)
class ReplanRequest:
    base_plan_hash: str
    affected_chapter_ids: tuple[EntityId, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        _digest(self.base_plan_hash)
        if (
            type(self.affected_chapter_ids) is not tuple
            or not self.affected_chapter_ids
            or any(type(v) is not EntityId for v in self.affected_chapter_ids)
        ):
            raise ContractError("replan request needs exact scoped chapter identities")
        if (
            len(set(self.affected_chapter_ids)) != len(self.affected_chapter_ids)
            or len({v.project for v in self.affected_chapter_ids}) != 1
        ):
            raise ContractError("replan request repeats or crosses project")
        if type(self.reasons) is not tuple or not self.reasons:
            raise ContractError("replan request needs explicit reasons")
        for reason in self.reasons:
            _text(reason, "replan reason")

    def to_dict(self) -> dict[str, object]:
        return {
            "base_plan_hash": self.base_plan_hash,
            "affected_chapter_ids": [v.to_dict() for v in self.affected_chapter_ids],
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, value: object) -> ReplanRequest:
        row = _record(value, {"base_plan_hash", "affected_chapter_ids", "reasons"})
        return cls(
            _digest(row["base_plan_hash"]),
            tuple(EntityId.from_dict(v) for v in _array(row["affected_chapter_ids"])),
            tuple(_text(v, "reason") for v in _array(row["reasons"])),
        )


@dataclass(frozen=True, slots=True)
class CompilationResult:
    contract: CompiledContract | None
    diagnostics: tuple[Diagnostic, ...]
    replan: ReplanRequest | None = None

    def __post_init__(self) -> None:
        if type(self.diagnostics) is not tuple or any(
            type(v) is not Diagnostic for v in self.diagnostics
        ):
            raise ContractError("diagnostics must be immutable exact values")
        if self.contract is not None and (
            type(self.contract) is not CompiledContract
            or self.diagnostics
            or self.replan is not None
        ):
            raise ContractError("a compiled contract cannot accompany hard diagnostics")
        if self.contract is None and not self.diagnostics:
            raise ContractError("failed compilation must have a concrete diagnostic")
        if self.replan is not None and type(self.replan) is not ReplanRequest:
            raise ContractError("replanning must be an explicit immutable request")

    @property
    def ok(self) -> bool:
        return self.contract is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "contract": None if self.contract is None else self.contract.to_dict(),
            "diagnostics": [v.to_dict() for v in self.diagnostics],
            "replan": None if self.replan is None else self.replan.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> CompilationResult:
        row = _record(value, {"contract", "diagnostics", "replan"})
        return cls(
            None
            if row["contract"] is None
            else CompiledContract.from_dict(row["contract"]),
            tuple(Diagnostic.from_dict(v) for v in _array(row["diagnostics"])),
            None if row["replan"] is None else ReplanRequest.from_dict(row["replan"]),
        )
