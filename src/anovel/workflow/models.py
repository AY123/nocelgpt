"""Frozen offline chapter inputs and retained Draft evidence, never authority."""

from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass, field
from hashlib import sha256
from typing import cast

from anovel.canon.identity import canonical_bytes, decode_canonical, raw_prose_hash
from anovel.context.compiler import compile_context
from anovel.context.models import (
    ContextArtifact,
    ContextBudget,
    ContextRequest,
    ContextRole,
    ContextSource,
    FrozenContextInputs,
)
from anovel.contracts.compiler import compile_contract
from anovel.contracts.models import (
    CanonView,
    CompiledContract,
    ContinuationEvidence,
    KnowledgeSnapshot,
)
from anovel.domain.identity import EntityId
from anovel.gateway.models import (
    GatewayRequest,
    GatewayResult,
    ModelPolicy,
    validate_output,
)
from anovel.planning.models import StoryFixture
from anovel.planning.versions import PlanHistory

WORKFLOW_STATES = frozenset(
    {"PREPARED", "DISPATCHING", "DRAFT_SAVED", "UNKNOWN", "FAILED", "BLOCKED"}
)
PENDING_CAPABILITIES = ("EXTRACTION", "SCENE_OVERLAY", "Q0_Q3", "PERMIT")
WRITER_SCHEMA = canonical_bytes(
    {
        "type": "object",
        "properties": {"text": {"type": "string", "minLength": 1}},
        "required": ["text"],
        "additionalProperties": False,
    }
)


class WorkflowError(ValueError):
    """Stable diagnostic codes do not interpolate story or credential content."""


def _record(value: object, keys: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise WorkflowError("INVALID_WORKFLOW_RECORD")
    return cast(dict[str, object], value)


def _text(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise WorkflowError("INVALID_WORKFLOW_IDENTITY")
    return value


def _encoded(value: bytes) -> str:
    return b64encode(value).decode("ascii")


def _decoded(value: object) -> bytes:
    if type(value) is not str:
        raise WorkflowError("INVALID_WORKFLOW_BYTES")
    try:
        raw = b64decode(value, validate=True)
    except ValueError:
        raise WorkflowError("INVALID_WORKFLOW_BYTES") from None
    if _encoded(raw) != value:
        raise WorkflowError("INVALID_WORKFLOW_BYTES")
    return raw


def checked_prose(value: bytes) -> bytes:
    try:
        if type(value) is not bytes or not value.decode("utf-8").strip():
            raise ValueError
        raw_prose_hash(value)
    except (ValueError, UnicodeError):
        raise WorkflowError("INVALID_DRAFT_PROSE") from None
    return value


@dataclass(frozen=True, slots=True)
class FrozenChapterInput:
    """Complete audit input; only compiled ContextArtifact is model-visible."""

    payload: bytes = field(repr=False)

    def __post_init__(self) -> None:
        self._parts()

    @classmethod
    def freeze(
        cls,
        *,
        history: PlanHistory,
        chapter_id: EntityId,
        fixture: StoryFixture,
        view: CanonView,
        budget: ContextBudget,
        policies: tuple[ModelPolicy, ...],
        instructions: str,
        template_version: str,
        continuity: ContinuationEvidence | None = None,
        knowledge_snapshot: KnowledgeSnapshot | None = None,
        sources: tuple[ContextSource, ...] = (),
    ) -> FrozenChapterInput:
        try:
            return cls(
                canonical_bytes(
                    {
                        "record_type": "offline_chapter_input",
                        "schema_version": "1.0",
                        "history": history.to_dict(),
                        "chapter_id": chapter_id.to_dict(),
                        "fixture": fixture.to_dict(),
                        "view": view.to_dict(),
                        "budget": budget.to_dict(),
                        "policies": [p.to_dict() for p in policies],
                        "instructions": instructions,
                        "template_version": template_version,
                        "continuity": None
                        if continuity is None
                        else continuity.to_dict(),
                        "knowledge_snapshot": None
                        if knowledge_snapshot is None
                        else knowledge_snapshot.to_dict(),
                        "sources": [s.to_dict() for s in sources],
                    }
                )
            )
        except (AttributeError, TypeError, ValueError):
            raise WorkflowError("INVALID_FROZEN_CHAPTER_INPUT") from None

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    @classmethod
    def from_dict(cls, value: object) -> FrozenChapterInput:
        try:
            return cls(canonical_bytes(value))
        except (TypeError, ValueError):
            raise WorkflowError("INVALID_FROZEN_CHAPTER_INPUT") from None

    @property
    def content_hash(self) -> str:
        return sha256(self.payload).hexdigest()

    def _parts(
        self,
    ) -> tuple[
        dict[str, object],
        PlanHistory,
        EntityId,
        StoryFixture,
        CanonView,
        ContextBudget,
        tuple[ModelPolicy, ...],
        ContinuationEvidence | None,
        KnowledgeSnapshot | None,
        tuple[ContextSource, ...],
    ]:
        try:
            row = _record(
                decode_canonical(self.payload),
                {
                    "record_type",
                    "schema_version",
                    "history",
                    "chapter_id",
                    "fixture",
                    "view",
                    "budget",
                    "policies",
                    "instructions",
                    "template_version",
                    "continuity",
                    "knowledge_snapshot",
                    "sources",
                },
            )
            if (
                row["record_type"] != "offline_chapter_input"
                or row["schema_version"] != "1.0"
            ):
                raise WorkflowError("INVALID_FROZEN_CHAPTER_INPUT")
            _text(row["instructions"])
            _text(row["template_version"])
            if type(row["policies"]) is not list or type(row["sources"]) is not list:
                raise WorkflowError("INVALID_FROZEN_CHAPTER_INPUT")
            policies = tuple(ModelPolicy.from_dict(p) for p in row["policies"])
            if not policies or any(not p.test_mode for p in policies):
                raise WorkflowError("OFFLINE_POLICY_REQUIRED")
            return (
                row,
                PlanHistory.from_dict(row["history"]),
                EntityId.from_dict(row["chapter_id"]),
                StoryFixture.from_dict(row["fixture"]),
                CanonView.from_dict(row["view"]),
                ContextBudget.from_dict(row["budget"]),
                policies,
                None
                if row["continuity"] is None
                else ContinuationEvidence.from_dict(row["continuity"]),
                None
                if row["knowledge_snapshot"] is None
                else KnowledgeSnapshot.from_dict(row["knowledge_snapshot"]),
                tuple(ContextSource.from_dict(s) for s in row["sources"]),
            )
        except (TypeError, ValueError, KeyError):
            raise WorkflowError("INVALID_FROZEN_CHAPTER_INPUT") from None

    def request(
        self, run_id: str, logical_id: str
    ) -> tuple[CompiledContract, ContextArtifact, GatewayRequest]:
        try:
            (
                row,
                history,
                chapter,
                fixture,
                view,
                budget,
                policies,
                continuity,
                knowledge,
                sources,
            ) = self._parts()
            result = compile_contract(
                history,
                chapter,
                fixture,
                view,
                continuity,
                knowledge_snapshot=knowledge,
            )
            if result.contract is None:
                raise WorkflowError("CONTRACT_NOT_READY")
            contract = result.contract
            request = ContextRequest(
                contract.project,
                contract.branch,
                contract.parent_ref,
                contract.content_hash,
                ContextRole.WRITER,
                budget,
            )
            context = compile_context(
                FrozenContextInputs.from_contract(contract, request, sources)
            )
            if (
                context.artifact is None
                or context.artifact.role is not ContextRole.WRITER
            ):
                raise WorkflowError("WRITER_CONTEXT_NOT_READY")
            gateway = GatewayRequest(
                contract.project,
                contract.branch,
                _text(run_id),
                _text(logical_id),
                context.artifact,
                _text(row["instructions"]),
                _text(row["template_version"]),
                WRITER_SCHEMA,
                policies,
            )
            return contract, context.artifact, gateway
        except WorkflowError:
            raise
        except (TypeError, ValueError):
            raise WorkflowError("FROZEN_INPUT_COMPILATION_FAILED") from None


@dataclass(frozen=True, slots=True)
class DraftRevision:
    revision: int
    prose: bytes = field(repr=False)
    origin: str
    previous_hash: str | None

    def __post_init__(self) -> None:
        checked_prose(self.prose)
        if type(self.revision) is not int or self.revision < 1:
            raise WorkflowError("INVALID_DRAFT_REVISION")
        if self.origin not in {"MODEL", "MANUAL"}:
            raise WorkflowError("INVALID_DRAFT_ORIGIN")
        if (self.revision == 1) != (self.previous_hash is None):
            raise WorkflowError("INVALID_DRAFT_LINEAGE")

    @property
    def prose_hash(self) -> str:
        return sha256(self.prose).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "revision": self.revision,
            "prose_base64": _encoded(self.prose),
            "prose_hash": self.prose_hash,
            "origin": self.origin,
            "previous_hash": self.previous_hash,
        }

    @classmethod
    def from_dict(cls, value: object) -> DraftRevision:
        row = _record(
            value, {"revision", "prose_base64", "prose_hash", "origin", "previous_hash"}
        )
        if type(row["revision"]) is not int:
            raise WorkflowError("INVALID_DRAFT_REVISION")
        revision = cls(
            row["revision"],
            _decoded(row["prose_base64"]),
            _text(row["origin"]),
            None if row["previous_hash"] is None else _text(row["previous_hash"]),
        )
        if revision.prose_hash != row["prose_hash"]:
            raise WorkflowError("DRAFT_HASH_MISMATCH")
        return revision


@dataclass(frozen=True, slots=True)
class WorkflowSnapshot:
    frozen_input: FrozenChapterInput = field(repr=False)
    request_bytes: bytes = field(repr=False)
    contract_bytes: bytes = field(repr=False)
    context_bytes: bytes = field(repr=False)
    attempt_id: str
    policy_id: str
    state: str = "PREPARED"
    result_bytes: bytes | None = field(default=None, repr=False)
    versions: tuple[DraftRevision, ...] = field(default=(), repr=False)
    diagnostic: str | None = None

    def __post_init__(self) -> None:
        try:
            if (
                type(self.frozen_input) is not FrozenChapterInput
                or self.state not in WORKFLOW_STATES
            ):
                raise WorkflowError("INVALID_WORKFLOW_SNAPSHOT")
            _text(self.attempt_id)
            _text(self.policy_id)
            request = self.request
            contract, context, expected = self.frozen_input.request(
                request.run_id, request.logical_id
            )
            if (
                expected.to_bytes() != self.request_bytes
                or canonical_bytes(contract.to_dict()) != self.contract_bytes
                or context.to_bytes() != self.context_bytes
                or self.policy_id not in {p.id for p in request.policies}
            ):
                raise WorkflowError("WORKFLOW_INPUT_BINDING_MISMATCH")
            result = self.result
            if result is not None:
                policy = next(p for p in request.policies if p.id == self.policy_id)
                if (
                    result.project,
                    result.branch,
                    result.run_id,
                    result.logical_id,
                    result.attempt_id,
                    result.request_hash,
                    result.policy_hash,
                ) != (
                    request.project,
                    request.branch,
                    request.run_id,
                    request.logical_id,
                    self.attempt_id,
                    request.content_hash,
                    policy.content_hash,
                ):
                    raise WorkflowError("WORKFLOW_RESULT_BINDING_MISMATCH")
            if type(self.versions) is not tuple:
                raise WorkflowError("INVALID_DRAFT_LINEAGE")
            previous = None
            for index, version in enumerate(self.versions, 1):
                if (
                    type(version) is not DraftRevision
                    or version.revision != index
                    or version.previous_hash != previous
                    or version.origin != ("MODEL" if index == 1 else "MANUAL")
                ):
                    raise WorkflowError("INVALID_DRAFT_LINEAGE")
                previous = version.prose_hash
            if self.state == "DRAFT_SAVED":
                if (
                    not self.versions
                    or result is None
                    or self.versions[0].prose != result_prose(request, result)
                ):
                    raise WorkflowError("DRAFT_EVIDENCE_MISSING")
            elif self.versions:
                raise WorkflowError("NON_DRAFT_HAS_PROSE")
            if self.state in {"PREPARED", "DISPATCHING"} and result is not None:
                raise WorkflowError("UNPUBLISHED_RESULT")
            if self.state in {"UNKNOWN", "FAILED"} and (
                result is None or result.status != self.state
            ):
                raise WorkflowError("STOP_STATE_RESULT_MISMATCH")
            if self.diagnostic is not None:
                _text(self.diagnostic)
        except WorkflowError:
            raise
        except (TypeError, ValueError, StopIteration):
            raise WorkflowError("INVALID_WORKFLOW_SNAPSHOT") from None

    @property
    def request(self) -> GatewayRequest:
        return GatewayRequest.from_dict(decode_canonical(self.request_bytes))

    @property
    def contract(self) -> CompiledContract:
        return CompiledContract.from_dict(decode_canonical(self.contract_bytes))

    @property
    def context(self) -> ContextArtifact:
        return ContextArtifact.from_dict(decode_canonical(self.context_bytes))

    @property
    def result(self) -> GatewayResult | None:
        return (
            None
            if self.result_bytes is None
            else GatewayResult.from_dict(decode_canonical(self.result_bytes))
        )

    @property
    def project(self) -> str:
        return self.request.project

    @property
    def branch(self) -> str:
        return self.request.branch

    @property
    def run_id(self) -> str:
        return self.request.run_id

    @property
    def input_hash(self) -> str:
        return self.frozen_input.content_hash

    @property
    def revision(self) -> int:
        return len(self.versions)

    @property
    def prose(self) -> bytes | None:
        return None if not self.versions else self.versions[-1].prose

    @property
    def prose_hash(self) -> str | None:
        return None if not self.versions else self.versions[-1].prose_hash

    @property
    def accepted(self) -> bool:
        return False

    @property
    def invalidated_evidence(self) -> tuple[str, ...]:
        return () if self.revision < 2 else ("EXTRACTION", "CHECKS", "CONFIRMATION")

    @property
    def pending_capabilities(self) -> tuple[str, ...]:
        return PENDING_CAPABILITIES

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "offline_workflow_snapshot",
            "schema_version": "1.0",
            "frozen_input": self.frozen_input.to_dict(),
            "request": self.request.to_dict(),
            "contract": self.contract.to_dict(),
            "context": self.context.to_dict(),
            "attempt_id": self.attempt_id,
            "policy_id": self.policy_id,
            "state": self.state,
            "result": None if self.result is None else self.result.to_dict(),
            "versions": [v.to_dict() for v in self.versions],
            "diagnostic": self.diagnostic,
            "accepted": False,
            "pending_capabilities": list(PENDING_CAPABILITIES),
        }

    def payload_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @property
    def record_hash(self) -> str:
        return sha256(self.payload_bytes()).hexdigest()

    @classmethod
    def from_bytes(cls, raw: bytes) -> WorkflowSnapshot:
        try:
            row = _record(
                decode_canonical(raw),
                {
                    "record_type",
                    "schema_version",
                    "frozen_input",
                    "request",
                    "contract",
                    "context",
                    "attempt_id",
                    "policy_id",
                    "state",
                    "result",
                    "versions",
                    "diagnostic",
                    "accepted",
                    "pending_capabilities",
                },
            )
            if (
                row["record_type"] != "offline_workflow_snapshot"
                or row["schema_version"] != "1.0"
                or row["accepted"] is not False
                or row["pending_capabilities"] != list(PENDING_CAPABILITIES)
                or type(row["versions"]) is not list
            ):
                raise WorkflowError("INVALID_WORKFLOW_SNAPSHOT")
            return cls(
                FrozenChapterInput.from_dict(row["frozen_input"]),
                canonical_bytes(row["request"]),
                canonical_bytes(row["contract"]),
                canonical_bytes(row["context"]),
                _text(row["attempt_id"]),
                _text(row["policy_id"]),
                _text(row["state"]),
                None if row["result"] is None else canonical_bytes(row["result"]),
                tuple(DraftRevision.from_dict(v) for v in row["versions"]),
                None if row["diagnostic"] is None else _text(row["diagnostic"]),
            )
        except (TypeError, ValueError):
            raise WorkflowError("INVALID_WORKFLOW_SNAPSHOT") from None


def result_prose(request: GatewayRequest, result: GatewayResult) -> bytes:
    if (
        result.status != "SUCCESS"
        or result.charge_status == "PENDING"
        or result.reply.output_bytes is None
    ):
        raise WorkflowError("GATEWAY_RESULT_NOT_READY")
    try:
        output = decode_canonical(result.reply.output_bytes)
        validate_output(request.schema, output)
        text = cast(dict[str, object], output)["text"]
        if type(text) is not str:
            raise WorkflowError("INVALID_WRITER_OUTPUT")
        return checked_prose(text.encode("utf-8"))
    except (TypeError, ValueError, KeyError, UnicodeError):
        raise WorkflowError("INVALID_WRITER_OUTPUT") from None
