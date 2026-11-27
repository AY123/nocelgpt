"""Read-only local artifact observations, never freshness or authority tokens.

Only the application service observes current artifacts. A serialized assessment
does not authorize dispatch, checks, a Permit or a Canon commit, and cannot be
presented later as proof that the observed sources remain current.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

from anovel.canon.identity import canonical_bytes, decode_canonical

from .models import WorkflowError

RUN_STAGES = (
    "FROZEN_INPUTS",
    "SOURCE_DRAFT",
    "SCENE_BINDING",
    "SCENE_DRAFT",
    "CHAPTER_ASSEMBLY",
    "WHOLE_CHAPTER_EXTRACTION",
    "Q0_Q3",
    "PRODUCTION_PERMIT",
    "CANON_ACCEPTANCE",
)
LOCAL_STAGES = RUN_STAGES[:5]
EXTRACTION_STAGE = RUN_STAGES[5]
QUALITY_STAGE = RUN_STAGES[6]
OBSERVED_STAGES = RUN_STAGES[:7]
_OBSERVED_STAGE_COUNTS = {
    "1.0": len(LOCAL_STAGES),
    "1.1": len(OBSERVED_STAGES) - 1,
    "1.2": len(OBSERVED_STAGES),
    "1.3": len(OBSERVED_STAGES),
}
LOCAL_STATES = frozenset(
    {"CURRENT", "MISSING", "BLOCKED", "STALE", "NOT_REACHED", "UNSUPPORTED"}
)
_LEGACY_EXTRACTION = ("NOT_IMPLEMENTED", "DELEGATED_EXTRACTION_NOT_IMPLEMENTED")
_LEGACY_QUALITY = ("NOT_IMPLEMENTED", "DELEGATED_Q0_Q3_NOT_IMPLEMENTED")
_LOCAL_QUALITY_ONLY = ("BLOCKED", "LOCAL_QUALITY_OBSERVATIONS_ONLY")
_EXTRACTION_REFS = frozenset(
    {"assembly_hash", "assembly_prose_hash", "extraction_observation_hash"}
)
_EXTRACTION_STAGE_REFS = {
    _LEGACY_EXTRACTION: frozenset(),
    ("CURRENT", "CURRENT"): _EXTRACTION_REFS,
    ("MISSING", "EXTRACTION_OBSERVATION_UNAVAILABLE"): frozenset(),
    ("BLOCKED", "EXTRACTION_OBSERVATION_INVALID"): frozenset(),
    ("BLOCKED", "EXTRACTION_CORRESPONDENCE_FAIL"): _EXTRACTION_REFS,
    ("BLOCKED", "EXTRACTION_CORRESPONDENCE_UNKNOWN"): _EXTRACTION_REFS,
    ("BLOCKED", "EXTRACTION_CORRESPONDENCE_ERROR"): _EXTRACTION_REFS,
    ("STALE", "EXTRACTION_SOURCE_CHANGED"): frozenset(),
    ("NOT_REACHED", "PREREQUISITE_NOT_CURRENT"): frozenset(),
}
_Q0_REFS = _EXTRACTION_REFS | {"q0_input_hash", "q0_run_hash"}
_QUALITY_STAGE_REFS = {
    _LEGACY_QUALITY: frozenset(),
    _LOCAL_QUALITY_ONLY: frozenset(),
    ("MISSING", "Q0_EXECUTION_UNAVAILABLE"): frozenset(),
    ("BLOCKED", "Q0_EXECUTION_INVALID"): frozenset(),
    ("STALE", "Q0_SOURCE_CHANGED"): frozenset(),
    ("BLOCKED", "Q0_LOCAL_FAIL"): _Q0_REFS,
    ("BLOCKED", "Q0_LOCAL_UNKNOWN"): _Q0_REFS,
    ("BLOCKED", "Q0_LOCAL_ERROR"): _Q0_REFS,
    ("BLOCKED", "Q1_Q3_EVIDENCE_NOT_INSPECTED"): _Q0_REFS,
    ("NOT_REACHED", "PREREQUISITE_NOT_CURRENT"): frozenset(),
}
_OBSERVED_STATES = {
    EXTRACTION_STAGE: _EXTRACTION_STAGE_REFS,
    QUALITY_STAGE: _QUALITY_STAGE_REFS,
}
_FUTURE = {
    "PRODUCTION_PERMIT": ("NOT_AUTHORIZED", "PRODUCTION_PERMIT_NOT_AUTHORIZED"),
    "CANON_ACCEPTANCE": ("NOT_REACHED", "CANON_ACCEPTANCE_NOT_REACHED"),
}
_REF_KEYS = frozenset(
    {
        "input_hash",
        "source_record_hash",
        "source_request_hash",
        "source_result_hash",
        "source_prose_hash",
        "contract_hash",
        "context_hash",
        "pack_hash",
        "projection_hash",
        "child_record_hash",
        "child_request_hash",
        "child_result_hash",
        "child_prose_hash",
        "assembly_hash",
        "assembly_prose_hash",
    }
)
_CURRENT_REFS = {
    "FROZEN_INPUTS": frozenset(
        {
            "input_hash",
            "source_record_hash",
            "contract_hash",
            "context_hash",
            "pack_hash",
            "source_request_hash",
        }
    ),
    "SOURCE_DRAFT": frozenset(
        {"source_record_hash", "source_prose_hash", "source_result_hash"}
    ),
    "SCENE_BINDING": frozenset(
        {"child_record_hash", "projection_hash", "context_hash"}
    ),
    "SCENE_DRAFT": frozenset(
        {
            "child_record_hash",
            "child_request_hash",
            "child_result_hash",
            "child_prose_hash",
        }
    ),
    "CHAPTER_ASSEMBLY": frozenset({"assembly_hash", "assembly_prose_hash"}),
}
_OBSERVED_REFS = {EXTRACTION_STAGE: _EXTRACTION_REFS, QUALITY_STAGE: _Q0_REFS}
_STAGE_FIELDS = {"stage", "state", "reason", "refs"}
_FIXED: dict[str, object] = {
    "record_type": "offline_run_assessment",
    "observation_only": True,
    "can_commit": False,
    "can_issue_permit": False,
    "can_dispatch": False,
    "accepted": False,
    "published": False,
}
_DERIVED = {
    "schema_version",
    "evidence_scope",
    "project",
    "branch",
    "run_id",
    "input_hash",
    "source_record_hash",
    "step_id",
    "stages",
    "draft_ready",
    "handoff",
    "stop_stage",
    "stop_code",
}
QUALITY_CHECKS = ("Q0", "Q1", "Q2", "Q3")
_QUALITY_REFS = {
    "Q0": ("input_hash", "observation_hash", "record_hash"),
    "Q1": ("annotations_hash", "observation_hash", "record_hash"),
    "Q2": ("method_policy_hash", "observation_hash", "record_hash"),
    "Q3": ("method_policy_hash", "observation_hash", "record_hash"),
}
_LOCAL_VERDICTS = frozenset({"PASS", "FAIL", "UNKNOWN", "ERROR"})
_QUALITY_STATES = _LOCAL_VERDICTS | {
    "NOT_REACHED",
    "INPUT_REQUIRED",
    "MISSING",
    "INVALID",
    "STALE",
}
_QUALITY_FIELDS = {"check", "state", "refs"}
_QUALITY_ASSESSMENT_FIELDS = {"quality_observations", "q1_annotations_hash"}


def _hash(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError
    return value


def _identity(value: object) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError
    value.encode("utf-8")
    return value


@dataclass(frozen=True, slots=True)
class RunStageObservation:
    stage: str
    state: str
    reason: str
    refs: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        try:
            if (
                type(self.stage) is not str
                or self.stage not in RUN_STAGES
                or type(self.state) is not str
                or type(self.reason) is not str
                or re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", self.reason) is None
                or type(self.refs) is not tuple
            ):
                raise ValueError
            keys: list[str] = []
            allowed_refs = _OBSERVED_REFS.get(self.stage, _REF_KEYS)
            for pair in self.refs:
                if type(pair) is not tuple or len(pair) != 2:
                    raise ValueError
                key, value = pair
                if type(key) is not str or key not in allowed_refs:
                    raise ValueError
                _hash(value)
                keys.append(key)
            if keys != sorted(set(keys)):
                raise ValueError
            if self.stage in _OBSERVED_STATES:
                if frozenset(keys) != _OBSERVED_STATES[self.stage].get(
                    (self.state, self.reason)
                ):
                    raise ValueError
            elif self.stage in _FUTURE:
                if (self.state, self.reason) != _FUTURE[self.stage] or self.refs:
                    raise ValueError
            elif (
                self.state not in LOCAL_STATES
                or (
                    self.state == "CURRENT"
                    and (
                        self.reason != "CURRENT"
                        or not _CURRENT_REFS[self.stage].issubset(keys)
                    )
                )
                or (
                    self.state == "NOT_REACHED"
                    and (self.reason != "PREREQUISITE_NOT_CURRENT" or self.refs)
                )
            ):
                raise ValueError
        except (TypeError, ValueError):
            raise WorkflowError("INVALID_RUN_STAGE_OBSERVATION") from None

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "state": self.state,
            "reason": self.reason,
            "refs": dict(self.refs),
        }

    @classmethod
    def from_dict(cls, value: object) -> RunStageObservation:
        try:
            if type(value) is not dict or set(value) != _STAGE_FIELDS:
                raise ValueError
            row = cast(dict[str, object], value)
            refs = row["refs"]
            if type(refs) is not dict:
                raise ValueError
            typed_refs = cast(dict[str, str], refs)
            observation = cls(
                cast(str, row["stage"]),
                cast(str, row["state"]),
                cast(str, row["reason"]),
                tuple(sorted(typed_refs.items())),
            )
            if canonical_bytes(observation.to_dict()) != canonical_bytes(row):
                raise ValueError
            return observation
        except (KeyError, TypeError, ValueError, RecursionError):
            raise WorkflowError("INVALID_RUN_STAGE_OBSERVATION") from None


@dataclass(frozen=True, slots=True)
class QualityObservation:
    """A scoped retained local verdict or an explicit readback stop."""

    check: str
    state: str
    refs: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        try:
            if (
                type(self.check) is not str
                or self.check not in QUALITY_CHECKS
                or type(self.state) is not str
                or self.state not in _QUALITY_STATES
                or (self.state == "INPUT_REQUIRED" and self.check != "Q1")
                or type(self.refs) is not tuple
            ):
                raise ValueError
            keys: list[str] = []
            for pair in self.refs:
                if (
                    type(pair) is not tuple
                    or len(pair) != 2
                    or type(pair[0]) is not str
                ):
                    raise ValueError
                key, value = pair
                keys.append(key)
                _hash(value)
            expected = (
                _QUALITY_REFS[self.check] if self.state in _LOCAL_VERDICTS else ()
            )
            if tuple(keys) != expected:
                raise ValueError
        except (TypeError, ValueError):
            raise WorkflowError("INVALID_QUALITY_OBSERVATION") from None

    def to_dict(self) -> dict[str, object]:
        return {"check": self.check, "state": self.state, "refs": dict(self.refs)}

    @classmethod
    def from_dict(cls, value: object) -> QualityObservation:
        try:
            if type(value) is not dict or set(value) != _QUALITY_FIELDS:
                raise ValueError
            row = cast(dict[str, object], value)
            refs = row["refs"]
            if type(refs) is not dict:
                raise ValueError
            return cls(
                cast(str, row["check"]),
                cast(str, row["state"]),
                tuple(sorted(cast(dict[str, str], refs).items())),
            )
        except (KeyError, TypeError, ValueError):
            raise WorkflowError("INVALID_QUALITY_OBSERVATION") from None


@dataclass(frozen=True, slots=True)
class RunAssessment:
    project: str
    branch: str
    run_id: str
    input_hash: str
    source_record_hash: str
    step_id: str | None
    stages: tuple[RunStageObservation, ...]
    schema_version: str = "1.0"
    quality_observations: tuple[QualityObservation, ...] = ()
    q1_annotations_hash: str | None = None

    def __post_init__(self) -> None:
        try:
            _identity(self.project)
            _identity(self.branch)
            _identity(self.run_id)
            _hash(self.input_hash)
            _hash(self.source_record_hash)
            if self.step_id is not None:
                _hash(self.step_id)
            if (
                type(self.schema_version) is not str
                or self.schema_version not in _OBSERVED_STAGE_COUNTS
                or type(self.stages) is not tuple
                or len(self.stages) != len(RUN_STAGES)
                or any(type(stage) is not RunStageObservation for stage in self.stages)
                or tuple(stage.stage for stage in self.stages) != RUN_STAGES
                or self.stages[0].state != "CURRENT"
                or type(self.quality_observations) is not tuple
            ):
                raise ValueError
            extraction = self.stages[RUN_STAGES.index(EXTRACTION_STAGE)]
            quality = self.stages[RUN_STAGES.index(QUALITY_STAGE)]
            if (self.schema_version == "1.0") != (
                (extraction.state, extraction.reason) == _LEGACY_EXTRACTION
            ) or (self.schema_version in {"1.0", "1.1"}) != (
                (quality.state, quality.reason) == _LEGACY_QUALITY
            ):
                raise ValueError
            stopped = False
            for stage in self.stages[: _OBSERVED_STAGE_COUNTS[self.schema_version]]:
                if stopped:
                    if stage.state != "NOT_REACHED":
                        raise ValueError
                elif stage.state != "CURRENT":
                    if stage.state == "NOT_REACHED":
                        raise ValueError
                    stopped = True
                for key, value in stage.refs:
                    if (key == "input_hash" and value != self.input_hash) or (
                        key == "source_record_hash" and value != self.source_record_hash
                    ):
                        raise ValueError
            extraction_refs = dict(extraction.refs)
            if extraction_refs:
                assembly_refs = dict(
                    self.stages[RUN_STAGES.index("CHAPTER_ASSEMBLY")].refs
                )
                if any(
                    extraction_refs[key] != assembly_refs[key]
                    for key in ("assembly_hash", "assembly_prose_hash")
                ):
                    raise ValueError
            if quality.refs:
                quality_refs = dict(quality.refs)
                if any(
                    quality_refs[key] != extraction_refs[key]
                    for key in _EXTRACTION_REFS
                ):
                    raise ValueError
            if self.schema_version == "1.3":
                self._validate_quality_observations(
                    extraction,
                    extraction_refs.get("extraction_observation_hash"),
                    quality,
                )
            elif (
                self.quality_observations
                or self.q1_annotations_hash is not None
                or (quality.state, quality.reason) == _LOCAL_QUALITY_ONLY
            ):
                raise ValueError
            if self.step_id is None and self.stages[2].state == "CURRENT":
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise WorkflowError("INVALID_RUN_ASSESSMENT") from None

    def _validate_quality_observations(
        self,
        extraction: RunStageObservation,
        observation_hash: str | None,
        combined: RunStageObservation,
    ) -> None:
        if self.q1_annotations_hash is not None:
            _hash(self.q1_annotations_hash)
        expected = (
            _LOCAL_QUALITY_ONLY
            if extraction.state == "CURRENT"
            else ("NOT_REACHED", "PREREQUISITE_NOT_CURRENT")
        )
        if (
            (combined.state, combined.reason) != expected
            or any(
                type(row) is not QualityObservation for row in self.quality_observations
            )
            or tuple(row.check for row in self.quality_observations) != QUALITY_CHECKS
        ):
            raise ValueError
        for row in self.quality_observations:
            if (row.state == "NOT_REACHED") != (observation_hash is None):
                raise ValueError
            if row.refs and dict(row.refs)["observation_hash"] != observation_hash:
                raise ValueError
        q1 = self.quality_observations[1]
        if observation_hash is not None and (q1.state == "INPUT_REQUIRED") != (
            self.q1_annotations_hash is None
        ):
            raise ValueError
        if q1.refs and dict(q1.refs)["annotations_hash"] != self.q1_annotations_hash:
            raise ValueError

    @property
    def draft_ready(self) -> bool:
        return all(
            stage.state == "CURRENT" for stage in self.stages[: len(LOCAL_STAGES)]
        )

    @property
    def handoff(self) -> str:
        return "LOCAL_DRAFT_HANDOFF" if self.draft_ready else "STOPPED"

    @property
    def first_blocker(self) -> RunStageObservation:
        return next(stage for stage in self.stages if stage.state != "CURRENT")

    @property
    def stop_stage(self) -> str:
        return self.first_blocker.stage

    @property
    def stop_code(self) -> str:
        return self.first_blocker.reason

    @property
    def observation_only(self) -> bool:
        return True

    @property
    def evidence_scope(self) -> str:
        if self.schema_version == "1.3":
            return "LOCAL_ARTIFACT_AND_QUALITY_OBSERVATIONS_NOT_PRODUCTION_QUALITY"
        if self.schema_version == "1.2":
            return "LOCAL_ARTIFACT_AND_Q0_OBSERVATION_NOT_PRODUCTION_QUALITY"
        return "LOCAL_ARTIFACT_OBSERVATION_NOT_Q0_Q3"

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

    def to_dict(self) -> dict[str, object]:
        value = {
            **_FIXED,
            "schema_version": self.schema_version,
            "evidence_scope": self.evidence_scope,
            "project": self.project,
            "branch": self.branch,
            "run_id": self.run_id,
            "input_hash": self.input_hash,
            "source_record_hash": self.source_record_hash,
            "step_id": self.step_id,
            "stages": [stage.to_dict() for stage in self.stages],
            "draft_ready": self.draft_ready,
            "handoff": self.handoff,
            "stop_stage": self.stop_stage,
            "stop_code": self.stop_code,
        }
        if self.schema_version == "1.3":
            value["quality_observations"] = [
                row.to_dict() for row in self.quality_observations
            ]
            value["q1_annotations_hash"] = self.q1_annotations_hash
        return value

    @classmethod
    def from_dict(cls, value: object) -> RunAssessment:
        try:
            if type(value) is not dict:
                raise ValueError
            row = cast(dict[str, object], value)
            version = row["schema_version"]
            fields = set(_FIXED) | _DERIVED
            if version == "1.3":
                fields |= _QUALITY_ASSESSMENT_FIELDS
            if set(row) != fields:
                raise ValueError
            raw_stages = row["stages"]
            raw_quality = row.get("quality_observations", [])
            if type(raw_stages) is not list or type(raw_quality) is not list:
                raise ValueError
            assessment = cls(
                cast(str, row["project"]),
                cast(str, row["branch"]),
                cast(str, row["run_id"]),
                cast(str, row["input_hash"]),
                cast(str, row["source_record_hash"]),
                cast(str | None, row["step_id"]),
                tuple(RunStageObservation.from_dict(stage) for stage in raw_stages),
                schema_version=cast(str, version),
                quality_observations=tuple(
                    QualityObservation.from_dict(v) for v in raw_quality
                ),
                q1_annotations_hash=cast(str | None, row.get("q1_annotations_hash")),
            )
            # Re-derive the graph and constants, including exact boolean types.
            if canonical_bytes(assessment.to_dict()) != canonical_bytes(row):
                raise ValueError
            return assessment
        except (KeyError, TypeError, ValueError, RecursionError):
            raise WorkflowError("INVALID_RUN_ASSESSMENT") from None

    def payload_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @classmethod
    def from_bytes(cls, raw: bytes) -> RunAssessment:
        try:
            if type(raw) is not bytes:
                raise ValueError
            return cls.from_dict(decode_canonical(raw))
        except (TypeError, ValueError, RecursionError):
            raise WorkflowError("INVALID_RUN_ASSESSMENT") from None

    @property
    def record_hash(self) -> str:
        return sha256(self.payload_bytes()).hexdigest()

    @property
    def content_hash(self) -> str:
        return self.record_hash
