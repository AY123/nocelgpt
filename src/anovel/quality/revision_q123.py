"""Native offline Q1–Q3 runs for one exact saved Draft revision."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import TYPE_CHECKING, ClassVar, Final, Literal

from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.quality import q0
from anovel.quality import q1 as local_q1
from anovel.quality import q2 as local_q2
from anovel.quality import q3 as local_q3

if TYPE_CHECKING:
    from anovel.workflow.chapter_revision import ChapterRevision
    from anovel.workflow.extractor import ExtractionObservation


# Preserve old exact policy bytes in the readback list when updating the active
# local configuration. Nested method decoders retain their own format rules.
REVISION_Q123_POLICY_BYTES: Final[bytes] = canonical_bytes(
    {
        "record_type": "local_revision_q123_policy",
        "schema_version": "1.0",
        "policy_id": "draft-revision-q123",
        "policy_version": "1.0",
        "q1": {
            "registry_hash": local_q1.REGISTRY_HASH,
            "checks": list(local_q1.CHECK_IDS),
        },
        "q2": {
            "method_policy_hash": local_q2.METHOD_POLICY_HASH,
            "checks": list(local_q2.CHECK_IDS),
        },
        "q3": {
            "method_policy_hash": local_q3.METHOD_POLICY_HASH,
            "checks": list(local_q3.CHECK_IDS),
        },
        "authority": "LOCAL_DRAFT_ONLY",
    }
)
REVISION_Q123_POLICY_HASH: Final[str] = sha256(REVISION_Q123_POLICY_BYTES).hexdigest()
_KNOWN_POLICY_BYTES: Final[tuple[bytes, ...]] = (REVISION_Q123_POLICY_BYTES,)
_PUBLICATION_TOKEN = object()


class RevisionQ123Error(ValueError):
    """Stable local audit diagnostic."""


def _input_hash(
    revision: ChapterRevision,
    observation: ExtractionObservation,
    annotations: local_q1.BoundQ1Annotations,
    policy_bytes: bytes,
) -> str:
    return sha256(
        canonical_bytes(
            {
                "record_type": "local_revision_q123_input",
                "schema_version": "1.0",
                "revision_hash": revision.record_hash,
                "candidate_payload_hash": revision.candidate.payload_hash,
                "observation_hash": observation.record_hash,
                "annotations_hash": annotations.record_hash,
                "policy_hash": sha256(policy_bytes).hexdigest(),
            }
        )
    ).hexdigest()


def _document(
    revision: ChapterRevision,
    policy_bytes: bytes,
    input_hash: str,
    one: local_q1.Q1Run,
    two: local_q2.Q2Run,
    three: local_q3.Q3Run,
) -> dict[str, object]:
    observation = one.observation
    return {
        "record_type": "local_revision_q123_run",
        "schema_version": "1.0",
        "evidence_scope": "LOCAL_DRAFT_ONLY",
        "revision_base64": q0._encoded(revision.payload_bytes()),
        "revision_hash": revision.record_hash,
        "observation_hash": observation.record_hash,
        "annotations_hash": one.annotations_hash,
        "policy_base64": q0._encoded(policy_bytes),
        "policy_hash": sha256(policy_bytes).hexdigest(),
        "input_hash": input_hash,
        "q1_base64": q0._encoded(one.payload_bytes()),
        "q2_base64": q0._encoded(two.payload_bytes()),
        "q3_base64": q0._encoded(three.payload_bytes()),
        "q1_hash": one.record_hash,
        "q2_hash": two.record_hash,
        "q3_hash": three.record_hash,
        "q1_status": one.q1_status,
        "q2_status": two.q2_status,
        "q3_status": three.q3_status,
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
    "observation_hash",
    "annotations_hash",
    "policy_base64",
    "policy_hash",
    "input_hash",
    "q1_base64",
    "q2_base64",
    "q3_base64",
    "q1_hash",
    "q2_hash",
    "q3_hash",
    "q1_status",
    "q2_status",
    "q3_status",
    "aggregate_status",
    "semantic_status",
    *q0._FALSE,
}


@dataclass(frozen=True, slots=True)
class RevisionQ123Run:
    """Local composition evidence; nested native records retain their own IDs."""

    payload: bytes = field(repr=False)
    revision: ChapterRevision = field(init=False, repr=False, compare=False)
    q1: local_q1.Q1Run = field(init=False, repr=False, compare=False)
    q2: local_q2.Q2Run = field(init=False, repr=False, compare=False)
    q3: local_q3.Q3Run = field(init=False, repr=False, compare=False)
    policy_hash: str = field(init=False, compare=False)
    input_hash: str = field(init=False, compare=False)
    _publication_token: object | None = field(
        init=False, default=None, repr=False, compare=False
    )
    _publication_hash: str | None = field(
        init=False, default=None, repr=False, compare=False
    )
    _publication_owner: int | None = field(
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

        try:
            row = q0._row(decode_canonical(self.payload), _FIELDS)
            revision = ChapterRevision.from_bytes(q0._decoded(row["revision_base64"]))
            policy = q0._decoded(row["policy_base64"])
            if policy not in _KNOWN_POLICY_BYTES:
                raise ValueError
            one = local_q1.Q1Run.from_bytes(q0._decoded(row["q1_base64"]))
            two = local_q2.Q2Run.from_bytes(q0._decoded(row["q2_base64"]))
            three = local_q3.Q3Run.from_bytes(q0._decoded(row["q3_base64"]))
            observation = one.observation
            revision.require_observation(observation)
            if (
                two.observation.payload_bytes() != observation.payload_bytes()
                or three.observation.payload_bytes() != observation.payload_bytes()
            ):
                raise ValueError
            input_hash = _input_hash(revision, observation, one.annotations, policy)
            if (
                canonical_bytes(
                    _document(revision, policy, input_hash, one, two, three)
                )
                != self.payload
            ):
                raise ValueError
        except (TypeError, ValueError, KeyError, StopIteration, RecursionError):
            raise RevisionQ123Error("INVALID_REVISION_Q123_RUN") from None
        object.__setattr__(self, "revision", revision)
        object.__setattr__(self, "q1", one)
        object.__setattr__(self, "q2", two)
        object.__setattr__(self, "q3", three)
        object.__setattr__(self, "policy_hash", sha256(policy).hexdigest())
        object.__setattr__(self, "input_hash", input_hash)

    @classmethod
    def from_bytes(cls, raw: bytes) -> RevisionQ123Run:
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
    def observation(self) -> ExtractionObservation:
        return self.q1.observation

    @property
    def observation_hash(self) -> str:
        return self.q1.observation_hash

    @property
    def annotations_hash(self) -> str:
        return self.q1.annotations_hash

    @property
    def q1_status(self) -> str:
        return self.q1.q1_status

    @property
    def q2_status(self) -> str:
        return self.q2.q2_status

    @property
    def q3_status(self) -> str:
        return self.q3.q3_status

    def require_sources(
        self,
        revision: ChapterRevision,
        observation: ExtractionObservation,
        annotations: local_q1.BoundQ1Annotations,
    ) -> None:
        if (
            self.revision.payload_bytes() != revision.payload_bytes()
            or self.observation.payload_bytes() != observation.payload_bytes()
            or self.q1.annotations.payload_bytes() != annotations.payload_bytes()
        ):
            raise RevisionQ123Error("REVISION_Q123_SOURCE_CHANGED")


def require_native_revision_q123(run: RevisionQ123Run) -> None:
    if (
        type(run) is not RevisionQ123Run
        or run.policy_hash != REVISION_Q123_POLICY_HASH
        or run._publication_token is not _PUBLICATION_TOKEN
        or run._publication_hash != run.record_hash
        or run._publication_owner != id(run)
    ):
        raise RevisionQ123Error("REVISION_Q123_NATIVE_EXECUTION_REQUIRED")


def execute_revision_q123(
    revision: ChapterRevision,
    observation: ExtractionObservation,
    annotations: local_q1.BoundQ1Annotations,
) -> RevisionQ123Run:
    """Freeze composition inputs before running every fixed native method."""
    from anovel.workflow.chapter_revision import ChapterRevision
    from anovel.workflow.extractor import ExtractionObservation

    if (
        type(revision) is not ChapterRevision
        or type(observation) is not ExtractionObservation
        or type(annotations) is not local_q1.BoundQ1Annotations
    ):
        raise RevisionQ123Error("REVISION_Q123_SOURCE_REQUIRED")
    revision.require_observation(observation)
    local_q1.validate_bindings(annotations, observation)
    policy = REVISION_Q123_POLICY_BYTES
    input_hash = _input_hash(revision, observation, annotations, policy)
    one = local_q1.execute_local_q1(observation, annotations)
    two = local_q2.execute_local_q2(observation)
    three = local_q3.execute_local_q3(observation)
    local_q1.require_local_execution_q1(one)
    local_q2.require_local_execution_q2(two)
    local_q3.require_local_execution_q3(three)
    result = RevisionQ123Run(
        canonical_bytes(_document(revision, policy, input_hash, one, two, three))
    )
    result.require_sources(revision, observation, annotations)
    object.__setattr__(result, "_publication_token", _PUBLICATION_TOKEN)
    object.__setattr__(result, "_publication_hash", result.record_hash)
    object.__setattr__(result, "_publication_owner", id(result))
    return result
