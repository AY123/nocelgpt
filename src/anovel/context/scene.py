"""Manually mapped first-scene candidates, never Canon or semantic approval.

The complete source prose and contract are retained for local audit only.
Model-facing consumers must separately select role-safe facts and ending text.
Each replay starts from the original retained Canon parent, never a fake commit
or a prior scene projection. This is one first-to-second step, not orchestration.
"""

from __future__ import annotations

import re
from base64 import b64decode, b64encode
from dataclasses import dataclass, field
from hashlib import sha256
from typing import cast

from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.contracts.models import CanonView, CompiledContract, CompiledScene
from anovel.domain.delta import (
    FactBaseline,
    FactState,
    NarrativeDelta,
    SetFact,
    preview_delta,
)
from anovel.domain.identity import EntityId
from anovel.genre.extensions.registration import registered_extensions

from .models import ContextError


def _text(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise ContextError("INVALID_SCENE_TEXT")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ContextError("INVALID_SCENE_TEXT") from None
    return value


def _integer(value: object, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ContextError("INVALID_SCENE_INTEGER")
    return value


def _hash(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ContextError("INVALID_SCENE_HASH")
    return value


def _id(value: object) -> EntityId:
    if type(value) is not EntityId:
        raise ContextError("INVALID_SCENE_IDENTITY")
    return value


def _record(value: object, keys: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise ContextError("INVALID_SCENE_RECORD")
    return cast(dict[str, object], value)


def _array(value: object) -> list[object]:
    if type(value) is not list:
        raise ContextError("INVALID_SCENE_ARRAY")
    return cast(list[object], value)


def _digest(value: object) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class SceneSpan:
    """Exact Unicode codepoint half-open span in the complete retained prose."""

    start: int
    end: int
    quote: str

    def __post_init__(self) -> None:
        _integer(self.start)
        _integer(self.end, 1)
        _text(self.quote)
        if self.end <= self.start or len(self.quote) != self.end - self.start:
            raise ContextError("INVALID_SCENE_SPAN")

    def to_dict(self) -> dict[str, object]:
        return {"start": self.start, "end": self.end, "quote": self.quote}

    @classmethod
    def from_dict(cls, value: object) -> SceneSpan:
        row = _record(value, {"start", "end", "quote"})
        return cls(_integer(row["start"]), _integer(row["end"], 1), _text(row["quote"]))


@dataclass(frozen=True, slots=True)
class OperationQuote:
    operation_id: EntityId
    span: SceneSpan

    def __post_init__(self) -> None:
        _id(self.operation_id)
        if type(self.span) is not SceneSpan:
            raise ContextError("INVALID_OPERATION_QUOTE")

    def to_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation_id.to_dict(),
            "span": self.span.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> OperationQuote:
        row = _record(value, {"operation_id", "span"})
        try:
            return cls(
                EntityId.from_dict(row["operation_id"]),
                SceneSpan.from_dict(row["span"]),
            )
        except (TypeError, ValueError):
            raise ContextError("INVALID_OPERATION_QUOTE") from None


@dataclass(frozen=True, slots=True)
class SceneDeltaBinding:
    """Explicit operator mapping, not identity authentication or prose analysis."""

    delta: NarrativeDelta | None
    review_ref: str
    operation_quotes: tuple[OperationQuote, ...] = ()
    ending_fact_ids: tuple[EntityId, ...] = ()

    def __post_init__(self) -> None:
        _text(self.review_ref)
        if self.delta is not None and type(self.delta) is not NarrativeDelta:
            raise ContextError("INVALID_SCENE_DELTA")
        if type(self.operation_quotes) is not tuple or any(
            type(v) is not OperationQuote for v in self.operation_quotes
        ):
            raise ContextError("INVALID_OPERATION_QUOTES")
        if type(self.ending_fact_ids) is not tuple or any(
            type(v) is not EntityId for v in self.ending_fact_ids
        ):
            raise ContextError("INVALID_ENDING_FACT_IDENTITIES")
        quoted = {v.operation_id for v in self.operation_quotes}
        if len(quoted) != len(self.operation_quotes) or len(
            set(self.ending_fact_ids)
        ) != len(self.ending_fact_ids):
            raise ContextError("DUPLICATE_SCENE_EVIDENCE")
        if self.delta is None:
            if self.operation_quotes:
                raise ContextError("UNCHANGED_SCENE_HAS_OPERATION_QUOTES")
        elif quoted != {v.meta.id for v in self.delta.operations} or any(
            v.meta.authorization_ref != self.review_ref for v in self.delta.operations
        ):
            raise ContextError("SCENE_OPERATION_MAPPING_MISMATCH")

    def to_dict(self) -> dict[str, object]:
        return {
            "delta": None if self.delta is None else self.delta.to_dict(),
            "review_ref": self.review_ref,
            "operation_quotes": [v.to_dict() for v in self.operation_quotes],
            "ending_fact_ids": [v.to_dict() for v in self.ending_fact_ids],
        }

    @classmethod
    def from_dict(cls, value: object) -> SceneDeltaBinding:
        row = _record(
            value, {"delta", "review_ref", "operation_quotes", "ending_fact_ids"}
        )
        try:
            return cls(
                None
                if row["delta"] is None
                else NarrativeDelta.from_dict(row["delta"]),
                _text(row["review_ref"]),
                tuple(
                    OperationQuote.from_dict(v) for v in _array(row["operation_quotes"])
                ),
                tuple(EntityId.from_dict(v) for v in _array(row["ending_fact_ids"])),
            )
        except (TypeError, ValueError):
            raise ContextError("INVALID_SCENE_DELTA_BINDING") from None


def evidence_ref(run_id: str, revision: int, prose_hash: str, span: SceneSpan) -> str:
    """Bind a manual quote to this exact persisted source revision and bytes."""
    _text(run_id)
    _integer(revision, 1)
    _hash(prose_hash)
    if type(span) is not SceneSpan:
        raise ContextError("INVALID_SCENE_SPAN")
    return "draft-scene-evidence:sha256:" + _digest(
        {
            "run_id": run_id,
            "revision": revision,
            "prose_hash": prose_hash,
            "span": span.to_dict(),
        }
    )


@dataclass(frozen=True, slots=True)
class _ProjectionData:
    contract: CompiledContract
    source_run_id: str
    source_revision: int
    source_record_hash: str
    source_input_hash: str
    source_prose: bytes
    source_prose_hash: str
    source_scene_id: EntityId
    target_scene_id: EntityId
    source_span: SceneSpan
    ending_span: SceneSpan
    binding: SceneDeltaBinding
    before_hash: str
    after_hash: str


def _source_text(prose: bytes) -> str:
    if type(prose) is not bytes:
        raise ContextError("INVALID_SCENE_PROSE")
    try:
        return _text(prose.decode("utf-8"))
    except UnicodeError:
        raise ContextError("INVALID_SCENE_PROSE") from None


def _check_spans(prose: bytes, source: SceneSpan, ending: SceneSpan) -> None:
    if type(source) is not SceneSpan or type(ending) is not SceneSpan:
        raise ContextError("INVALID_SCENE_SPAN")
    text = _source_text(prose)
    if (
        source.end > len(text)
        or text[source.start : source.end] != source.quote
        or ending.start < source.start
        or ending.end != source.end
        or text[ending.start : ending.end] != ending.quote
    ):
        raise ContextError("SCENE_SOURCE_OR_ENDING_MISMATCH")


def _source_requirements(source: CompiledScene, delta: NarrativeDelta | None) -> None:
    operations = () if delta is None else delta.operations
    for required in source.required:
        matches = [v for v in operations if v.meta.target_id == required.target_id]
        if len(matches) != 1 or canonical_bytes(
            required.materialize(matches[0].meta).to_dict()
        ) != canonical_bytes(matches[0].to_dict()):
            raise ContextError("SOURCE_SCENE_REQUIRED_TRANSITION_MISSING")
    for operation in operations:
        for forbidden in source.plan.forbidden:
            if (
                operation.meta.target_id == forbidden.target_id
                and operation.meta.path is forbidden.path
                and operation.OP == forbidden.operation.value
                and (
                    type(operation) is not SetFact
                    or (
                        forbidden.value is not None
                        and FactState.known(operation.value)
                        == FactState.known(forbidden.value)
                    )
                )
            ):
                raise ContextError("SOURCE_SCENE_FORBIDDEN_TRANSITION")


def _replay(
    contract: CompiledContract,
    source_scene_id: EntityId,
    target_scene_id: EntityId,
    prose: bytes,
    run_id: str,
    revision: int,
    source: SceneSpan,
    ending: SceneSpan,
    binding: SceneDeltaBinding,
) -> tuple[FactBaseline, FactBaseline, frozenset[EntityId]]:
    if type(contract) is not CompiledContract or len(contract.scenes) < 2:
        raise ContextError("SCENE_PAIR_REQUIRED")
    first, second = contract.scenes[:2]
    if first.id != source_scene_id or second.id != target_scene_id:
        raise ContextError("ONLY_FIRST_TO_SECOND_SCENE_SUPPORTED")
    if type(binding) is not SceneDeltaBinding:
        raise ContextError("INVALID_SCENE_DELTA_BINDING")
    _check_spans(prose, source, ending)
    retained = next(v for v in contract.retained_inputs if v.name == "canon")
    baseline = CanonView.from_dict(decode_canonical(retained.content)).baseline
    registry = registered_extensions()
    registry.validate_baseline(baseline)
    if any(
        v.project != contract.project or baseline.get(v) is None
        for v in binding.ending_fact_ids
    ):
        raise ContextError("UNREGISTERED_SCENE_ENDING_FACT")
    _source_requirements(first, binding.delta)
    if binding.delta is None:
        return baseline, baseline, frozenset()
    delta = binding.delta
    if (
        delta.source_id != source_scene_id
        or delta.project != contract.project
        or delta.branch != contract.branch
        or delta.parent_ref != contract.parent_ref
    ):
        raise ContextError("SCENE_DELTA_SCOPE_MISMATCH")
    by_id = {v.operation_id: v.span for v in binding.operation_quotes}
    prose_hash = sha256(prose).hexdigest()
    text = _source_text(prose)
    for operation in delta.operations:
        meta = operation.meta
        quote = by_id[meta.id]
        if (
            quote.start < source.start
            or quote.end > source.end
            or text[quote.start : quote.end] != quote.quote
            or meta.evidence.source_id != source_scene_id
            or meta.evidence.position.chapter != contract.chapter_number
            or meta.evidence.position.order != first.plan.order
            or meta.evidence.evidence_ref
            != evidence_ref(run_id, revision, prose_hash, quote)
            or meta.authorization_ref != binding.review_ref
        ):
            raise ContextError("SCENE_OPERATION_EVIDENCE_MISMATCH")
    result = preview_delta(
        baseline,
        delta,
        source_id=source_scene_id,
        authorization_refs=frozenset({binding.review_ref}),
        extension_registry=registry,
    )
    prior = {v.seed_fact.id: canonical_bytes(v.to_dict()) for v in baseline.facts}
    changed = frozenset(
        v.seed_fact.id
        for v in result.candidate.facts
        if canonical_bytes(v.to_dict()) != prior[v.seed_fact.id]
    )
    if changed.intersection(first.plan.protected_fact_ids):
        raise ContextError("SOURCE_SCENE_PROTECTED_FACT_CHANGED")
    return baseline, result.candidate, changed


_FIELDS = {
    "record_type",
    "schema_version",
    "authority",
    "semantic_status",
    "capability_scope",
    "projection_policy",
    "contract",
    "contract_hash",
    "project",
    "branch",
    "parent_ref",
    "chapter_id",
    "source_run_id",
    "source_revision",
    "source_record_hash",
    "source_input_hash",
    "source_prose_base64",
    "source_prose_hash",
    "source_scene_id",
    "target_scene_id",
    "source_span",
    "ending_span",
    "binding",
    "before_hash",
    "after_hash",
}
_FIXED = {
    "record_type": "candidate_scene_projection",
    "schema_version": "1.0",
    "authority": "DRAFT_NOT_CANON",
    "semantic_status": "MANUAL_MAPPING_NOT_SEMANTIC_VALIDATION",
    "capability_scope": "FIRST_TO_SECOND_SCENE_ONLY",
    "projection_policy": "SCENE_CANDIDATE_CONTEXT_V1",
}


@dataclass(frozen=True, slots=True)
class CandidateSceneProjection:
    """Closed immutable audit bytes, revalidated against their retained parent."""

    payload: bytes = field(repr=False)
    _data: _ProjectionData = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        try:
            if type(self.payload) is not bytes:
                raise ValueError
            row = _record(decode_canonical(self.payload), _FIELDS)
            if any(
                type(row[key]) is not str or row[key] != value
                for key, value in _FIXED.items()
            ):
                raise ValueError
            contract = CompiledContract.from_dict(row["contract"])
            if (
                row["contract_hash"] != contract.content_hash
                or row["project"] != contract.project
                or row["branch"] != contract.branch
                or row["parent_ref"] != contract.parent_ref
                or EntityId.from_dict(row["chapter_id"]) != contract.chapter_id
            ):
                raise ValueError
            encoded = _text(row["source_prose_base64"])
            prose = b64decode(encoded, validate=True)
            if (
                b64encode(prose).decode("ascii") != encoded
                or sha256(prose).hexdigest() != row["source_prose_hash"]
            ):
                raise ValueError
            data = _ProjectionData(
                contract,
                _text(row["source_run_id"]),
                _integer(row["source_revision"], 1),
                _hash(row["source_record_hash"]),
                _hash(row["source_input_hash"]),
                prose,
                _hash(row["source_prose_hash"]),
                EntityId.from_dict(row["source_scene_id"]),
                EntityId.from_dict(row["target_scene_id"]),
                SceneSpan.from_dict(row["source_span"]),
                SceneSpan.from_dict(row["ending_span"]),
                SceneDeltaBinding.from_dict(row["binding"]),
                _hash(row["before_hash"]),
                _hash(row["after_hash"]),
            )
            before, after, _ = _replay(
                contract,
                data.source_scene_id,
                data.target_scene_id,
                prose,
                data.source_run_id,
                data.source_revision,
                data.source_span,
                data.ending_span,
                data.binding,
            )
            if (
                _digest(before.to_dict()) != data.before_hash
                or _digest(after.to_dict()) != data.after_hash
            ):
                raise ValueError
            object.__setattr__(self, "_data", data)
        except (TypeError, ValueError, KeyError, AttributeError, StopIteration):
            raise ContextError("INVALID_CANDIDATE_SCENE_PROJECTION") from None

    @classmethod
    def create(
        cls,
        contract: CompiledContract,
        *,
        source_run_id: str,
        source_revision: int,
        source_record_hash: str,
        source_input_hash: str,
        source_prose: bytes,
        source_scene_id: EntityId,
        target_scene_id: EntityId,
        source_span: SceneSpan,
        ending_span: SceneSpan,
        binding: SceneDeltaBinding,
    ) -> CandidateSceneProjection:
        try:
            _text(source_run_id)
            _integer(source_revision, 1)
            _hash(source_record_hash)
            _hash(source_input_hash)
            _id(source_scene_id)
            _id(target_scene_id)
            before, after, _ = _replay(
                contract,
                source_scene_id,
                target_scene_id,
                source_prose,
                source_run_id,
                source_revision,
                source_span,
                ending_span,
                binding,
            )
            return cls(
                canonical_bytes(
                    {
                        **_FIXED,
                        "contract": contract.to_dict(),
                        "contract_hash": contract.content_hash,
                        "project": contract.project,
                        "branch": contract.branch,
                        "parent_ref": contract.parent_ref,
                        "chapter_id": contract.chapter_id.to_dict(),
                        "source_run_id": source_run_id,
                        "source_revision": source_revision,
                        "source_record_hash": source_record_hash,
                        "source_input_hash": source_input_hash,
                        "source_prose_base64": b64encode(source_prose).decode("ascii"),
                        "source_prose_hash": sha256(source_prose).hexdigest(),
                        "source_scene_id": source_scene_id.to_dict(),
                        "target_scene_id": target_scene_id.to_dict(),
                        "source_span": source_span.to_dict(),
                        "ending_span": ending_span.to_dict(),
                        "binding": binding.to_dict(),
                        "before_hash": _digest(before.to_dict()),
                        "after_hash": _digest(after.to_dict()),
                    }
                )
            )
        except (TypeError, ValueError, KeyError, AttributeError, StopIteration):
            raise ContextError("INVALID_CANDIDATE_SCENE_PROJECTION") from None

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    @classmethod
    def from_dict(cls, value: object) -> CandidateSceneProjection:
        try:
            return cls(canonical_bytes(value))
        except (TypeError, ValueError):
            raise ContextError("INVALID_CANDIDATE_SCENE_PROJECTION") from None

    @property
    def content_hash(self) -> str:
        return sha256(self.payload).hexdigest()

    def replay(self, contract: CompiledContract) -> FactBaseline:
        return self._checked_replay(contract)[1]

    def changed_ids(self, contract: CompiledContract) -> frozenset[EntityId]:
        return self._checked_replay(contract)[2]

    def _checked_replay(
        self, contract: CompiledContract
    ) -> tuple[FactBaseline, FactBaseline, frozenset[EntityId]]:
        try:
            data = self._data
            if (
                type(contract) is not CompiledContract
                or contract.content_bytes != data.contract.content_bytes
            ):
                raise ValueError
            before, after, changed = _replay(
                contract,
                data.source_scene_id,
                data.target_scene_id,
                data.source_prose,
                data.source_run_id,
                data.source_revision,
                data.source_span,
                data.ending_span,
                data.binding,
            )
            if (
                _digest(before.to_dict()) != data.before_hash
                or _digest(after.to_dict()) != data.after_hash
            ):
                raise ValueError
            return before, after, changed
        except (TypeError, ValueError, KeyError, AttributeError, StopIteration):
            raise ContextError("SCENE_REPLAY_BINDING_MISMATCH") from None

    @property
    def source_run_id(self) -> str:
        return self._data.source_run_id

    @property
    def source_revision(self) -> int:
        return self._data.source_revision

    @property
    def source_record_hash(self) -> str:
        return self._data.source_record_hash

    @property
    def source_input_hash(self) -> str:
        return self._data.source_input_hash

    @property
    def source_prose(self) -> bytes:
        return self._data.source_prose

    @property
    def source_prose_hash(self) -> str:
        return self._data.source_prose_hash

    @property
    def source_scene_id(self) -> EntityId:
        return self._data.source_scene_id

    @property
    def target_scene_id(self) -> EntityId:
        return self._data.target_scene_id

    @property
    def source_span(self) -> SceneSpan:
        return self._data.source_span

    @property
    def ending_span(self) -> SceneSpan:
        return self._data.ending_span

    @property
    def ending_fact_ids(self) -> tuple[EntityId, ...]:
        return self._data.binding.ending_fact_ids

    @property
    def binding(self) -> SceneDeltaBinding:
        return self._data.binding

    @property
    def before_hash(self) -> str:
        return self._data.before_hash

    @property
    def after_hash(self) -> str:
        return self._data.after_hash
