"""Actual local deterministic Q0 execution, never production authorization.

Decoding is audit only. Only this module's runner attaches the nonserialized
publication marker; the application still verifies actual persistent sources.
The marker is an in-process capability, not protection against an owner who
can modify Python objects, this module or the database directly.
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

if TYPE_CHECKING:
    from anovel.workflow.extractor import ExtractionObservation

PROFILE = "LOCAL_TEST"
PRODUCTION_PROFILE = "PRODUCTION_REQUIRED"
REQUIRED_ARTIFACT_KINDS = (
    "ASSEMBLY",
    "OBSERVATION",
    "RAW_PROSE",
    "FROZEN_INPUT",
    "CONTRACT",
    "CONTEXT",
    "PACK_BINDING",
    "PROPOSAL_RAW",
    "INVENTORY_RAW",
)
ARTIFACT_KINDS = frozenset((*REQUIRED_ARTIFACT_KINDS, "DELTA"))
LOCAL_CHECK_IDS = ("Q0_ARTIFACT_BYTES_V1", "Q0_OBSERVATION_BINDINGS_V1")
PRODUCTION_CHECK_IDS = (
    *LOCAL_CHECK_IDS,
    "Q1_CANON_V1",
    "Q2_WORLD_RULES_V1",
    "Q3_CONTRACT_V1",
)
_METHODS = {
    LOCAL_CHECK_IDS[0]: "native-artifact-bytes/1.0",
    LOCAL_CHECK_IDS[1]: "native-observation-bindings/1.0",
}
_REGISTRY = {
    "version": "1.0",
    "local_checks": _METHODS,
    "production_required": list(PRODUCTION_CHECK_IDS),
    "production_authority": "NOT_CONFIGURED",
    "artifact_kinds": list(REQUIRED_ARTIFACT_KINDS),
    "optional_artifact": "DELTA_ONLY_IF_OBSERVATION_HAS_DELTA",
}
REGISTRY_HASH = sha256(canonical_bytes(_REGISTRY)).hexdigest()
_PUBLISH_TOKEN = object()
_VERDICTS = frozenset({"PASS", "FAIL", "UNKNOWN", "ERROR"})
_FALSE = {
    "can_commit": False,
    "can_issue_permit": False,
    "can_dispatch": False,
    "accepted": False,
    "published": False,
}


class Q0Error(ValueError):
    """Stable diagnostics never interpolate private story or credential data."""


def _hash(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise Q0Error("INVALID_Q0_HASH")
    return value


def _row(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields:
        raise Q0Error("INVALID_Q0_RECORD")
    return cast(dict[str, object], value)


def _encoded(raw: bytes) -> str:
    return b64encode(raw).decode("ascii")


def _decoded(value: object) -> bytes:
    if type(value) is not str:
        raise Q0Error("INVALID_Q0_BYTES")
    raw = b64decode(value, validate=True)
    if _encoded(raw) != value:
        raise Q0Error("INVALID_Q0_BYTES")
    return raw


def _time(value: object) -> datetime:
    if type(value) is not str:
        raise Q0Error("INVALID_Q0_TIME")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if utc_timestamp(parsed) != value:
        raise Q0Error("INVALID_Q0_TIME")
    return parsed


@dataclass(frozen=True, slots=True)
class ArtifactInput:
    """Unverified bytes and a declared digest, not an authenticated Artifact."""

    kind: str
    payload: bytes = field(repr=False)
    expected_hash: str

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not str
            or self.kind not in ARTIFACT_KINDS
            or type(self.payload) is not bytes
        ):
            raise Q0Error("INVALID_Q0_ARTIFACT")
        _digest(self.expected_hash)


@dataclass(frozen=True, slots=True)
class Q0Finding:
    code: str
    artifact_kind: str | None = None

    def __post_init__(self) -> None:
        if (
            type(self.code) is not str
            or re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", self.code) is None
            or (
                self.artifact_kind is not None
                and (
                    type(self.artifact_kind) is not str
                    or self.artifact_kind not in ARTIFACT_KINDS
                )
            )
        ):
            raise Q0Error("INVALID_Q0_FINDING")

    def to_dict(self) -> dict[str, object]:
        return {"code": self.code, "artifact_kind": self.artifact_kind}

    @classmethod
    def from_dict(cls, value: object) -> Q0Finding:
        row = _row(value, {"code", "artifact_kind"})
        return cls(cast(str, row["code"]), cast(str | None, row["artifact_kind"]))


@dataclass(frozen=True, slots=True)
class CheckResult:
    verdict: str
    findings: tuple[Q0Finding, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.verdict) is not str
            or self.verdict not in _VERDICTS
            or type(self.findings) is not tuple
            or any(type(v) is not Q0Finding for v in self.findings)
            or ((self.verdict == "PASS") != (not self.findings))
        ):
            raise Q0Error("INVALID_Q0_RESULT")

    def to_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "findings": [v.to_dict() for v in self.findings],
        }

    def payload_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> CheckResult:
        row = _row(value, {"verdict", "findings"})
        if type(row["findings"]) is not list:
            raise Q0Error("INVALID_Q0_RESULT")
        return cls(
            cast(str, row["verdict"]),
            tuple(Q0Finding.from_dict(v) for v in row["findings"]),
        )


def check_artifacts(artifacts: tuple[ArtifactInput, ...]) -> CheckResult:
    """Execute bytes/presence/digest rules; this does not certify scope."""
    if type(artifacts) is not tuple or any(
        type(v) is not ArtifactInput for v in artifacts
    ):
        raise Q0Error("INVALID_Q0_ARTIFACT_INPUTS")
    findings: list[Q0Finding] = []
    kinds = [v.kind for v in artifacts]
    for kind in REQUIRED_ARTIFACT_KINDS:
        if kind not in kinds:
            findings.append(Q0Finding("MISSING_ARTIFACT", kind))
    for kind in sorted(set(kinds)):
        if kinds.count(kind) != 1:
            findings.append(Q0Finding("DUPLICATE_ARTIFACT", kind))
    for value in artifacts:
        if not value.payload:
            findings.append(Q0Finding("EMPTY_ARTIFACT", value.kind))
        if _hash(value.payload) != value.expected_hash:
            findings.append(Q0Finding("ARTIFACT_HASH_MISMATCH", value.kind))
    return CheckResult("FAIL" if findings else "PASS", tuple(findings))


@dataclass(frozen=True, slots=True)
class RequiredCheckPlan:
    profile: str
    input_hash: str

    def __post_init__(self) -> None:
        if type(self.profile) is not str or self.profile not in {
            PROFILE,
            PRODUCTION_PROFILE,
        }:
            raise Q0Error("INVALID_Q0_PLAN")
        _digest(self.input_hash)

    @property
    def requirements(self) -> tuple[str, ...]:
        return LOCAL_CHECK_IDS if self.profile == PROFILE else PRODUCTION_CHECK_IDS

    @property
    def registry_hash(self) -> str:
        return REGISTRY_HASH

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "required_check_plan",
            "schema_version": "1.0",
            "profile": self.profile,
            "input_hash": self.input_hash,
            "registry_hash": REGISTRY_HASH,
            "requirements": [
                {"check_id": v, "version": "1.0", "applicability": "APPLICABLE"}
                for v in self.requirements
            ],
            "authority": "LOCAL_TEST_ONLY"
            if self.profile == PROFILE
            else "PRODUCTION_AUTHORITY_NOT_CONFIGURED",
        }

    @classmethod
    def from_dict(cls, value: object) -> RequiredCheckPlan:
        row = _row(
            value,
            {
                "record_type",
                "schema_version",
                "profile",
                "input_hash",
                "registry_hash",
                "requirements",
                "authority",
            },
        )
        result = cls(cast(str, row["profile"]), _digest(row["input_hash"]))
        if canonical_bytes(result.to_dict()) != canonical_bytes(row):
            raise Q0Error("INVALID_Q0_PLAN")
        return result

    @property
    def record_hash(self) -> str:
        return _hash(canonical_bytes(self.to_dict()))


def local_required_plan(input_hash: str) -> RequiredCheckPlan:
    return RequiredCheckPlan(PROFILE, input_hash)


def production_required_plan(input_hash: str) -> RequiredCheckPlan:
    return RequiredCheckPlan(PRODUCTION_PROFILE, input_hash)


def _request_id(check_id: str, input_hash: str) -> str:
    return _hash(
        canonical_bytes(
            {
                "profile": PROFILE,
                "check_id": check_id,
                "input_hash": input_hash,
                "registry_hash": REGISTRY_HASH,
            }
        )
    )


_EXEC_FIELDS = {
    "record_type",
    "schema_version",
    "profile",
    "registry_hash",
    "authority",
    "check_id",
    "check_version",
    "method_id",
    "input_hash",
    "request_id",
    "attempt_id",
    "execution_status",
    "started_at",
    "finished_at",
    "verdict",
    "raw_result_base64",
    "raw_result_hash",
    "findings",
}


@dataclass(frozen=True, slots=True)
class CheckExecution:
    """Retained audit record; parsing never authenticates execution provenance."""

    payload: bytes = field(repr=False)
    _result: CheckResult | None = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        try:
            row = _row(decode_canonical(self.payload), _EXEC_FIELDS)
            fixed = {
                "record_type": "local_check_execution",
                "schema_version": "1.0",
                "profile": PROFILE,
                "registry_hash": REGISTRY_HASH,
                "authority": "LOCAL_TEST_NO_PRODUCTION_AUTHORITY",
                "check_version": "1.0",
            }
            if any(
                type(row[k]) is not type(v) or row[k] != v for k, v in fixed.items()
            ):
                raise ValueError
            check_id = row["check_id"]
            if (
                type(check_id) is not str
                or check_id not in _METHODS
                or row["method_id"] != _METHODS[check_id]
            ):
                raise ValueError
            input_hash = _digest(row["input_hash"])
            if row["request_id"] != _request_id(check_id, input_hash):
                raise ValueError
            if (
                type(row["attempt_id"]) is not str
                or re.fullmatch(r"[0-9a-f]{32}", row["attempt_id"]) is None
            ):
                raise ValueError
            started = _time(row["started_at"])
            state = row["execution_status"]
            if type(state) is not str or state not in {
                "RUNNING",
                "FINISHED",
                "INTERRUPTED",
            }:
                raise ValueError
            result = None
            if state == "FINISHED":
                if _time(row["finished_at"]) < started:
                    raise ValueError
                raw = _decoded(row["raw_result_base64"])
                if _hash(raw) != row["raw_result_hash"]:
                    raise ValueError
                result = CheckResult.from_dict(decode_canonical(raw))
                if (
                    result.payload_bytes() != raw
                    or row["verdict"] != result.verdict
                    or canonical_bytes(row["findings"])
                    != canonical_bytes([v.to_dict() for v in result.findings])
                ):
                    raise ValueError
            elif (
                any(
                    row[k] is not None
                    for k in (
                        "finished_at",
                        "verdict",
                        "raw_result_base64",
                        "raw_result_hash",
                    )
                )
                or row["findings"] != []
            ):
                raise ValueError
            if canonical_bytes(row) != self.payload:
                raise ValueError
            object.__setattr__(self, "_result", result)
        except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
            raise Q0Error("INVALID_CHECK_EXECUTION") from None

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    def payload_bytes(self) -> bytes:
        return self.payload

    @classmethod
    def from_dict(cls, value: object) -> CheckExecution:
        try:
            return cls(canonical_bytes(value))
        except (TypeError, ValueError, RecursionError):
            raise Q0Error("INVALID_CHECK_EXECUTION") from None

    @classmethod
    def from_bytes(cls, raw: bytes) -> CheckExecution:
        return cls(raw)

    @property
    def record_hash(self) -> str:
        return _hash(self.payload)

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
    def verdict(self) -> str | None:
        return None if self._result is None else self._result.verdict

    @property
    def findings(self) -> tuple[Q0Finding, ...]:
        return () if self._result is None else self._result.findings

    @property
    def result_bytes(self) -> bytes | None:
        return None if self._result is None else self._result.payload_bytes()

    @property
    def result_hash(self) -> str | None:
        return None if self.result_bytes is None else _hash(self.result_bytes)


@dataclass(frozen=True, slots=True)
class RequiredCheckAssessment:
    status: str
    missing: tuple[str, ...]
    diagnostics: tuple[Q0Finding, ...]

    def __post_init__(self) -> None:
        if (
            type(self.status) is not str
            or self.status not in {"PASS", "BLOCKED"}
            or type(self.missing) is not tuple
            or any(
                type(v) is not str or v not in PRODUCTION_CHECK_IDS
                for v in self.missing
            )
            or len(set(self.missing)) != len(self.missing)
            or type(self.diagnostics) is not tuple
            or any(type(v) is not Q0Finding for v in self.diagnostics)
            or ((self.status == "PASS") != (not self.missing and not self.diagnostics))
        ):
            raise Q0Error("INVALID_REQUIRED_CHECK_ASSESSMENT")

    @property
    def verdict(self) -> str:
        return self.status

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "missing": list(self.missing),
            "diagnostics": [v.to_dict() for v in self.diagnostics],
        }


def assess_required(
    plan: RequiredCheckPlan, executions: tuple[CheckExecution, ...]
) -> RequiredCheckAssessment:
    """Pure closure analysis; supplied audit records do not become authority."""
    if (
        type(plan) is not RequiredCheckPlan
        or type(executions) is not tuple
        or any(type(v) is not CheckExecution for v in executions)
    ):
        raise Q0Error("INVALID_REQUIRED_CHECK_INPUT")
    diagnostics: list[Q0Finding] = []
    if plan.profile == PRODUCTION_PROFILE:
        return RequiredCheckAssessment(
            "BLOCKED",
            plan.requirements,
            (Q0Finding("PRODUCTION_AUTHORITY_NOT_CONFIGURED"),),
        )
    grouped: dict[str, list[CheckExecution]] = {}
    for value in executions:
        if value.input_hash != plan.input_hash:
            diagnostics.append(Q0Finding("CHECK_INPUT_CHANGED"))
            continue
        grouped.setdefault(value.check_id, []).append(value)
    missing = tuple(key for key in plan.requirements if key not in grouped)
    diagnostics.extend(Q0Finding("MISSING_REQUIRED_CHECK") for _ in missing)
    for key in plan.requirements:
        values = grouped.get(key, [])
        if len(values) > 1:
            diagnostics.append(Q0Finding("CONFLICTING_CHECK_EXECUTIONS"))
        for value in values:
            if value.execution_status != "FINISHED":
                diagnostics.append(Q0Finding("CHECK_NOT_FINISHED"))
            elif value.verdict != "PASS":
                diagnostics.append(Q0Finding("CHECK_" + cast(str, value.verdict)))
    return RequiredCheckAssessment(
        "BLOCKED" if diagnostics else "PASS", missing, tuple(diagnostics)
    )


def _artifacts(observation: ExtractionObservation) -> tuple[ArtifactInput, ...]:
    assembly = observation.assembly
    source = assembly.child.source
    retained = {v.name: v for v in source.contract.retained_inputs}
    row = observation.to_dict()
    values = [
        ArtifactInput("ASSEMBLY", assembly.payload_bytes(), observation.assembly_hash),
        ArtifactInput(
            "OBSERVATION", observation.payload_bytes(), observation.record_hash
        ),
        ArtifactInput("RAW_PROSE", assembly.prose, observation.prose_hash),
        ArtifactInput("FROZEN_INPUT", source.frozen_input.payload, source.input_hash),
        ArtifactInput("CONTRACT", source.contract_bytes, assembly.contract_hash),
        ArtifactInput("CONTEXT", source.context_bytes, source.context.content_hash),
        ArtifactInput(
            "PACK_BINDING", retained["pack"].content, retained["pack"].content_hash
        ),
        ArtifactInput(
            "PROPOSAL_RAW", observation.proposal_raw, _digest(row["proposal_raw_hash"])
        ),
        ArtifactInput(
            "INVENTORY_RAW",
            observation.inventory_raw,
            _digest(row["inventory_raw_hash"]),
        ),
    ]
    if observation.proposal_delta is not None:
        raw = canonical_bytes(observation.proposal_delta.to_dict())
        values.append(ArtifactInput("DELTA", raw, _hash(raw)))
    return tuple(sorted(values, key=lambda v: v.kind))


def _manifest(artifacts: tuple[ArtifactInput, ...]) -> list[dict[str, object]]:
    return [
        {
            "kind": v.kind,
            "expected_hash": v.expected_hash,
            "actual_hash": _hash(v.payload),
            "bytes": len(v.payload),
        }
        for v in artifacts
    ]


def _input_hash(
    observation: ExtractionObservation, artifacts: tuple[ArtifactInput, ...]
) -> str:
    return _hash(
        canonical_bytes(
            {
                "profile": PROFILE,
                "registry_hash": REGISTRY_HASH,
                "observation_hash": observation.record_hash,
                "artifacts": _manifest(artifacts),
            }
        )
    )


def _check_bindings(
    observation: ExtractionObservation, artifacts: tuple[ArtifactInput, ...]
) -> CheckResult:
    """Run structural associations, leaving semantic verdicts unchanged."""
    from anovel.workflow.extractor import ExtractionObservation

    if type(observation) is not ExtractionObservation:
        return CheckResult("FAIL", (Q0Finding("OBSERVATION_TYPE_INVALID"),))
    reparsed = ExtractionObservation.from_bytes(observation.payload_bytes())
    if (
        reparsed.payload_bytes() != observation.payload_bytes()
        or artifacts != _artifacts(reparsed)
    ):
        return CheckResult("FAIL", (Q0Finding("OBSERVATION_BINDING_MISMATCH"),))
    return CheckResult("PASS")


def _execute(
    check_id: str, input_hash: str, method: Callable[[], CheckResult]
) -> CheckExecution:
    started = utc_timestamp(datetime.now(UTC))
    try:
        result = method()
        if type(result) is not CheckResult:
            raise ValueError
    except Exception:
        result = CheckResult("ERROR", (Q0Finding("NATIVE_CHECK_EXECUTION_ERROR"),))
    raw = result.payload_bytes()
    return CheckExecution.from_dict(
        {
            "record_type": "local_check_execution",
            "schema_version": "1.0",
            "profile": PROFILE,
            "registry_hash": REGISTRY_HASH,
            "authority": "LOCAL_TEST_NO_PRODUCTION_AUTHORITY",
            "check_id": check_id,
            "check_version": "1.0",
            "method_id": _METHODS[check_id],
            "input_hash": input_hash,
            "request_id": _request_id(check_id, input_hash),
            "attempt_id": uuid4().hex,
            "execution_status": "FINISHED",
            "started_at": started,
            "finished_at": utc_timestamp(datetime.now(UTC)),
            "verdict": result.verdict,
            "raw_result_base64": _encoded(raw),
            "raw_result_hash": _hash(raw),
            "findings": [v.to_dict() for v in result.findings],
        }
    )


def _q0_status(
    assessment: RequiredCheckAssessment, executions: tuple[CheckExecution, ...]
) -> str:
    for verdict in ("FAIL", "ERROR", "UNKNOWN"):
        if any(v.verdict == verdict for v in executions):
            return verdict
    return "PASS" if assessment.status == "PASS" else "UNKNOWN"


def _run_record(
    observation: ExtractionObservation, executions: tuple[CheckExecution, ...]
) -> dict[str, object]:
    artifacts = _artifacts(observation)
    input_hash = _input_hash(observation, artifacts)
    local, required = (
        local_required_plan(input_hash),
        production_required_plan(input_hash),
    )
    own = assess_required(local, executions)
    production = assess_required(required, executions)
    return {
        "record_type": "local_q0_run",
        "schema_version": "1.0",
        "profile": PROFILE,
        "evidence_scope": "LOCAL_DETERMINISTIC_Q0_NOT_PRODUCTION_QUALITY",
        "registry_hash": REGISTRY_HASH,
        "observation_base64": _encoded(observation.payload_bytes()),
        "observation_hash": observation.record_hash,
        "assembly_hash": observation.assembly_hash,
        "prose_hash": observation.prose_hash,
        "project": observation.project,
        "branch": observation.branch,
        "run_id": observation.run_id,
        "step_id": observation.step_id,
        "input_hash": input_hash,
        "artifacts": _manifest(artifacts),
        "local_plan": local.to_dict(),
        "required_plan": required.to_dict(),
        "executions": [v.to_dict() for v in executions],
        "q0_status": _q0_status(own, executions),
        "local_assessment": own.to_dict(),
        "required_assessment": production.to_dict(),
        "aggregate_status": "BLOCKED",
        "semantic_status": observation.semantic_status,
        "source_correspondence_status": observation.correspondence_status,
        **_FALSE,
    }


_RUN_FIELDS = {
    "record_type",
    "schema_version",
    "profile",
    "evidence_scope",
    "registry_hash",
    "observation_base64",
    "observation_hash",
    "assembly_hash",
    "prose_hash",
    "project",
    "branch",
    "run_id",
    "step_id",
    "input_hash",
    "artifacts",
    "local_plan",
    "required_plan",
    "executions",
    "q0_status",
    "local_assessment",
    "required_assessment",
    "aggregate_status",
    "semantic_status",
    "source_correspondence_status",
    *_FALSE,
}


@dataclass(frozen=True, slots=True)
class Q0Run:
    """Immutable audit data; only a fresh native run is publishable by Store."""

    payload: bytes = field(repr=False)
    _observation: ExtractionObservation = field(init=False, repr=False, compare=False)
    _executions: tuple[CheckExecution, ...] = field(
        init=False, repr=False, compare=False
    )
    _publication_token: object | None = field(
        init=False, default=None, repr=False, compare=False
    )
    _publication_hash: str | None = field(
        init=False, default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        from anovel.workflow.extractor import ExtractionObservation

        try:
            row = _row(decode_canonical(self.payload), _RUN_FIELDS)
            observation = ExtractionObservation.from_bytes(
                _decoded(row["observation_base64"])
            )
            if type(row["executions"]) is not list:
                raise ValueError
            executions = tuple(CheckExecution.from_dict(v) for v in row["executions"])
            if any(
                v.input_hash != _input_hash(observation, _artifacts(observation))
                for v in executions
            ):
                raise ValueError
            expected = _run_record(observation, executions)
            if canonical_bytes(expected) != self.payload:
                raise ValueError
            object.__setattr__(self, "_observation", observation)
            object.__setattr__(self, "_executions", executions)
        except (
            TypeError,
            ValueError,
            KeyError,
            AttributeError,
            StopIteration,
            RecursionError,
        ):
            raise Q0Error("INVALID_Q0_RUN") from None

    @property
    def observation(self) -> ExtractionObservation:
        return self._observation

    @property
    def executions(self) -> tuple[CheckExecution, ...]:
        return self._executions

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    def payload_bytes(self) -> bytes:
        return self.payload

    @classmethod
    def from_dict(cls, value: object) -> Q0Run:
        try:
            return cls(canonical_bytes(value))
        except (TypeError, ValueError, RecursionError):
            raise Q0Error("INVALID_Q0_RUN") from None

    @classmethod
    def from_bytes(cls, raw: bytes) -> Q0Run:
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
    def assembly_hash(self) -> str:
        return self.observation.assembly_hash

    @property
    def prose_hash(self) -> str:
        return self.observation.prose_hash

    @property
    def input_hash(self) -> str:
        return cast(str, self.to_dict()["input_hash"])

    @property
    def local_plan(self) -> RequiredCheckPlan:
        return local_required_plan(self.input_hash)

    @property
    def required_plan(self) -> RequiredCheckPlan:
        return production_required_plan(self.input_hash)

    @property
    def q0_status(self) -> str:
        return cast(str, self.to_dict()["q0_status"])

    @property
    def aggregate_status(self) -> str:
        return "BLOCKED"

    @property
    def diagnostics(self) -> tuple[Q0Finding, ...]:
        return (
            assess_required(self.local_plan, self.executions).diagnostics
            + assess_required(self.required_plan, self.executions).diagnostics
        )

    @property
    def semantic_status(self) -> str:
        return "UNKNOWN"

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


def require_local_execution(run: Q0Run) -> None:
    if (
        type(run) is not Q0Run
        or run._publication_token is not _PUBLISH_TOKEN
        or run._publication_hash != run.record_hash
    ):
        raise Q0Error("Q0_NATIVE_EXECUTION_REQUIRED")


def execute_local_q0(observation: ExtractionObservation) -> Q0Run:
    """Run fixed native methods; caller cannot select rules or supply verdicts."""
    from anovel.workflow.extractor import ExtractionObservation

    if type(observation) is not ExtractionObservation:
        raise Q0Error("Q0_OBSERVATION_REQUIRED")
    artifacts = _artifacts(observation)
    input_hash = _input_hash(observation, artifacts)
    executions = (
        _execute(LOCAL_CHECK_IDS[0], input_hash, lambda: check_artifacts(artifacts)),
        _execute(
            LOCAL_CHECK_IDS[1],
            input_hash,
            lambda: _check_bindings(observation, artifacts),
        ),
    )
    run = Q0Run(canonical_bytes(_run_record(observation, executions)))
    object.__setattr__(run, "_publication_token", _PUBLISH_TOKEN)
    object.__setattr__(run, "_publication_hash", run.record_hash)
    return run
