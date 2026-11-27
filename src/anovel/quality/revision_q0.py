"""Native local Q0 evidence keyed to an exact retained Draft revision."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import TYPE_CHECKING, ClassVar, Final, Literal

from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.quality import q0

if TYPE_CHECKING:
    from anovel.workflow.chapter_revision import ChapterRevision
    from anovel.workflow.extractor import ExtractionObservation


# Only workflow-owned code selects the active policy. When it changes, retain
# each previously accepted policy byte string here for audit-only readback.
REVISION_Q0_POLICY_BYTES: Final[bytes] = canonical_bytes(
    {
        "record_type": "local_revision_q0_policy",
        "schema_version": "1.0",
        "policy_id": "draft-revision-q0",
        "policy_version": "1.0",
        "check_registry_hash": q0.REGISTRY_HASH,
        "required_checks": [
            {"id": check_id, "method": q0._METHODS[check_id]}
            for check_id in q0.LOCAL_CHECK_IDS
        ],
        "authority": "LOCAL_DRAFT_ONLY",
    }
)
REVISION_Q0_POLICY_HASH: Final[str] = sha256(REVISION_Q0_POLICY_BYTES).hexdigest()
_KNOWN_POLICY_BYTES: Final[tuple[bytes, ...]] = (REVISION_Q0_POLICY_BYTES,)
_PUBLICATION_TOKEN = object()


def _input_hash(
    revision: ChapterRevision,
    observation: ExtractionObservation,
    artifacts: tuple[q0.ArtifactInput, ...],
    policy_bytes: bytes,
) -> str:
    """Domain-separated identity using exact policy bytes; no dispatch authority."""
    return sha256(
        canonical_bytes(
            {
                "record_type": "local_revision_q0_input",
                "schema_version": "1.0",
                "revision_hash": revision.record_hash,
                "candidate_payload_hash": revision.candidate.payload_hash,
                "policy_hash": sha256(policy_bytes).hexdigest(),
                "legacy_structural_input_hash": q0._input_hash(observation, artifacts),
            }
        )
    ).hexdigest()


def _document(
    revision: ChapterRevision,
    observation: ExtractionObservation,
    policy_bytes: bytes,
    input_hash: str,
    executions: tuple[q0.CheckExecution, ...],
) -> dict[str, object]:
    if tuple(run.check_id for run in executions) != q0.LOCAL_CHECK_IDS or any(
        run.input_hash != input_hash or run.execution_status != "FINISHED"
        for run in executions
    ):
        raise q0.Q0Error("INVALID_REVISION_Q0_EXECUTIONS")
    local = q0.assess_required(q0.local_required_plan(input_hash), executions)
    return {
        "record_type": "local_revision_q0_run",
        "schema_version": "1.0",
        "evidence_scope": "LOCAL_DRAFT_ONLY",
        "revision_base64": q0._encoded(revision.payload_bytes()),
        "revision_hash": revision.record_hash,
        "observation_base64": q0._encoded(observation.payload_bytes()),
        "observation_hash": observation.record_hash,
        "policy_base64": q0._encoded(policy_bytes),
        "policy_hash": sha256(policy_bytes).hexdigest(),
        "input_hash": input_hash,
        "executions": [run.to_dict() for run in executions],
        "q0_status": q0._q0_status(local, executions),
        "local_assessment": local.to_dict(),
        "aggregate_status": "BLOCKED",
        "semantic_status": "UNKNOWN",
        **q0._FALSE,
    }


_FIELDS = {
    "record_type",
    "schema_version",
    "evidence_scope",
    "revision_base64",
    "revision_hash",
    "observation_base64",
    "observation_hash",
    "policy_base64",
    "policy_hash",
    "input_hash",
    "executions",
    "q0_status",
    "local_assessment",
    "aggregate_status",
    "semantic_status",
    *q0._FALSE,
}


@dataclass(frozen=True, slots=True)
class RevisionQ0Run:
    """Canonical audit record; parsing cannot recover native publication."""

    payload: bytes = field(repr=False)
    revision: ChapterRevision = field(init=False, repr=False, compare=False)
    observation: ExtractionObservation = field(init=False, repr=False, compare=False)
    policy_hash: str = field(init=False, compare=False)
    input_hash: str = field(init=False, compare=False)
    executions: tuple[q0.CheckExecution, ...] = field(
        init=False, repr=False, compare=False
    )
    q0_status: str = field(init=False, compare=False)
    _publication_token: object | None = field(
        init=False, default=None, repr=False, compare=False
    )
    _publication_hash: str | None = field(
        init=False, default=None, repr=False, compare=False
    )

    aggregate_status: ClassVar[Literal["BLOCKED"]] = "BLOCKED"
    semantic_status: ClassVar[Literal["UNKNOWN"]] = "UNKNOWN"
    can_commit: ClassVar[Literal[False]] = False
    can_issue_permit: ClassVar[Literal[False]] = False
    can_dispatch: ClassVar[Literal[False]] = False
    accepted: ClassVar[Literal[False]] = False
    published: ClassVar[Literal[False]] = False

    def __post_init__(self) -> None:
        from anovel.workflow.chapter_revision import ChapterRevision
        from anovel.workflow.extractor import ExtractionObservation

        try:
            row = q0._row(decode_canonical(self.payload), _FIELDS)
            revision = ChapterRevision.from_bytes(q0._decoded(row["revision_base64"]))
            observation = ExtractionObservation.from_bytes(
                q0._decoded(row["observation_base64"])
            )
            revision.require_observation(observation)
            policy_bytes = q0._decoded(row["policy_base64"])
            if (
                policy_bytes not in _KNOWN_POLICY_BYTES
                or type(row["executions"]) is not list
            ):
                raise ValueError
            executions = tuple(
                q0.CheckExecution.from_dict(item) for item in row["executions"]
            )
            input_hash = _input_hash(
                revision, observation, q0._artifacts(observation), policy_bytes
            )
            expected = _document(
                revision, observation, policy_bytes, input_hash, executions
            )
            if canonical_bytes(expected) != self.payload:
                raise ValueError
        except (ValueError, TypeError, KeyError, StopIteration, RecursionError):
            raise q0.Q0Error("INVALID_REVISION_Q0_RUN") from None
        object.__setattr__(self, "revision", revision)
        object.__setattr__(self, "observation", observation)
        object.__setattr__(self, "policy_hash", expected["policy_hash"])
        object.__setattr__(self, "input_hash", input_hash)
        object.__setattr__(self, "executions", executions)
        object.__setattr__(self, "q0_status", expected["q0_status"])

    @classmethod
    def from_bytes(cls, raw: bytes) -> RevisionQ0Run:
        return cls(raw)

    def payload_bytes(self) -> bytes:
        return self.payload

    @property
    def record_hash(self) -> str:
        return sha256(self.payload).hexdigest()

    @property
    def revision_hash(self) -> str:
        return self.revision.record_hash

    @property
    def observation_hash(self) -> str:
        return self.observation.record_hash

    def require_sources(
        self, revision: ChapterRevision, observation: ExtractionObservation
    ) -> None:
        if (
            revision.payload_bytes() != self.revision.payload_bytes()
            or observation.payload_bytes() != self.observation.payload_bytes()
        ):
            raise q0.Q0Error("REVISION_Q0_SOURCE_CHANGED")


def require_native_revision_q0(run: RevisionQ0Run) -> None:
    if (
        type(run) is not RevisionQ0Run
        or run.policy_hash != REVISION_Q0_POLICY_HASH
        or run._publication_token is not _PUBLICATION_TOKEN
        or run._publication_hash != run.record_hash
    ):
        raise q0.Q0Error("REVISION_Q0_NATIVE_EXECUTION_REQUIRED")


def execute_revision_q0(
    revision: ChapterRevision, observation: ExtractionObservation
) -> RevisionQ0Run:
    """Execute the fixed local methods with their identity set before execution."""
    from anovel.workflow.chapter_revision import ChapterRevision
    from anovel.workflow.extractor import ExtractionObservation

    if (
        type(revision) is not ChapterRevision
        or type(observation) is not ExtractionObservation
    ):
        raise q0.Q0Error("REVISION_Q0_SOURCE_REQUIRED")
    revision.require_observation(observation)
    policy_bytes = REVISION_Q0_POLICY_BYTES
    artifacts = q0._artifacts(observation)
    input_hash = _input_hash(revision, observation, artifacts, policy_bytes)
    executions = (
        q0._execute(
            q0.LOCAL_CHECK_IDS[0], input_hash, lambda: q0.check_artifacts(artifacts)
        ),
        q0._execute(
            q0.LOCAL_CHECK_IDS[1],
            input_hash,
            lambda: q0._check_bindings(observation, artifacts),
        ),
    )
    run = RevisionQ0Run(
        canonical_bytes(
            _document(revision, observation, policy_bytes, input_hash, executions)
        )
    )
    object.__setattr__(run, "_publication_token", _PUBLICATION_TOKEN)
    object.__setattr__(run, "_publication_hash", run.record_hash)
    return run
