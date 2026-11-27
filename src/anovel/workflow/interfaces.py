"""Closed task requests delegate every operation to the same application service."""

from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path
from typing import TypedDict, cast

from anovel.canon.identity import canonical_bytes
from anovel.context.models import ContextError
from anovel.context.scene import SceneDeltaBinding, SceneSpan
from anovel.contracts.models import KnowledgeSnapshot
from anovel.domain.identity import EntityId
from anovel.gateway.models import GatewayRequest, ModelPolicy
from anovel.quality.q0 import Q0Run
from anovel.quality.q1 import (
    BoundQ1Annotations,
    DeathTiming,
    Q1Claim,
    Q1Error,
    Q1Run,
    claim_from_dict,
)
from anovel.quality.q2 import Q2Finding, Q2Run
from anovel.quality.q3 import PROFILE as Q3_PROFILE
from anovel.quality.q3 import Q3Run

from .assembly import ChapterAssembly
from .chapter import (
    ChapterWorkflow,
    DraftChapterBrief,
    DraftCommitmentReview,
    NextChapterDraftInput,
    NextChapterWrittenDraft,
    RevisionAnnotationBinding,
    RevisionQualityReadback,
    WrittenDraftImpact,
)
from .chapter_revision import ChapterRevision
from .extractor import ExtractionObservation
from .generation import SceneGenerationSnapshot
from .models import FrozenChapterInput, WorkflowError, WorkflowSnapshot
from .run import RunAssessment
from .scene import SceneProjection
from .written_draft import (
    DraftAnchorResolution,
    DraftContinuity,
    DraftEditPreview,
    WrittenDraftRevision,
)

_REVISION_QUALITY_FIELDS = {
    "operation",
    "current_input",
    "project",
    "branch",
    "run_id",
    "annotations",
}

_DRAFT_SELECTION_FIELDS = {"version", "request_id", "expected_revision_hash"}
_FINISH_DRAFT_FIELDS = {
    "operation",
    "current_input",
    "output",
} | _DRAFT_SELECTION_FIELDS
_NEXT_CHAPTER_FIELDS = {
    "operation",
    "current_input",
    "project",
    "branch",
    "run_id",
    "expected_revision_hash",
}
_NEXT_CHAPTER_WRITE_FIELDS = _NEXT_CHAPTER_FIELDS | {"handoff", "output"}
_REPLACE_DRAFT_FIELDS = {
    "operation",
    "current_input",
    "project",
    "branch",
    "run_id",
    "expected_revision",
    "expected_prose_hash",
    "text",
}

_FIELDS = {
    "SAVE_NEXT_CHAPTER_DRAFT": _NEXT_CHAPTER_FIELDS | {"draft"},
    "INSPECT_WRITTEN_DRAFT": (_NEXT_CHAPTER_FIELDS - {"expected_revision_hash"})
    | {"chapter_id"},
    "INSPECT_WRITTEN_DRAFT_IMPACT": _NEXT_CHAPTER_FIELDS | {"source_chapter_id"},
    "REVIEW_WRITTEN_DRAFT_COMMITMENTS": _NEXT_CHAPTER_FIELDS | {"chapter_id", "review"},
    "PREVIEW_WRITTEN_DRAFT_EDIT": _NEXT_CHAPTER_FIELDS
    | {"chapter_id", "text", "output"},
    "APPLY_WRITTEN_DRAFT_EDIT_PREVIEW": (
        _NEXT_CHAPTER_FIELDS - {"expected_revision_hash"}
    )
    | {"chapter_id", "text", "preview"},
    "EDIT_WRITTEN_DRAFT": _NEXT_CHAPTER_FIELDS | {"chapter_id", "text", "choice"},
    "ANNOTATE_WRITTEN_DRAFT": _NEXT_CHAPTER_FIELDS | {"chapter_id", "annotations"},
    "PROJECT_NEXT_CHAPTER": _NEXT_CHAPTER_FIELDS | {"output"},
    "VERIFY_NEXT_CHAPTER": _NEXT_CHAPTER_FIELDS | {"handoff"},
    "PREPARE_NEXT_CHAPTER_MODEL_REQUEST": _NEXT_CHAPTER_WRITE_FIELDS | {"policy"},
    "WRITE_NEXT_CHAPTER_DRAFT": _NEXT_CHAPTER_WRITE_FIELDS,
    "REWRITE_NEXT_CHAPTER_DRAFT": _NEXT_CHAPTER_WRITE_FIELDS
    | {"source_chapter_id", "expected_target_revision_hash"},
    "INSPECT_CHAPTER_REVISION": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
    },
    "EXPORT_CHAPTER_REVISION": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "expected_revision_hash",
        "output",
    },
    "INSPECT_REVISION_QUALITY": _REVISION_QUALITY_FIELDS,
    "CHECK_REVISION_QUALITY": _REVISION_QUALITY_FIELDS | {"expected_revision_hash"},
    "BIND_REVISION_ANNOTATIONS": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "expected_revision_hash",
        "author_input",
        "output",
    },
    "SAVE_CHAPTER_REVISION": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
        "expected_observation_hash",
    }
    | _DRAFT_SELECTION_FIELDS,
    "FINISH_CHAPTER_DRAFT": _FINISH_DRAFT_FIELDS
    | {"project", "branch", "run_id", "step_id"},
    "CONTINUE_CHAPTER_DRAFT": _FINISH_DRAFT_FIELDS
    | {"projection", "attempt_id", "policy_id"},
    "CHECK_Q3": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
    },
    "INSPECT_Q3": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
    },
    "CHECK_Q2": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
    },
    "INSPECT_Q2": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
    },
    "CHECK_Q1": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
        "annotations",
    },
    "INSPECT_Q1": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
        "annotations",
    },
    "CHECK_Q0": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
    },
    "INSPECT_Q0": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
    },
    "EXTRACT_CHAPTER": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
    },
    "INSPECT_EXTRACTION": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
    },
    "ASSESS_RUN": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
    },
    "ASSEMBLE_CHAPTER": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
    },
    "EXPORT_CHAPTER": {"operation", "current_input", "assembly", "output"},
    "VERIFY_CHAPTER_EXPORT": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
        "output",
    },
    "START": {
        "operation",
        "current_input",
        "run_id",
        "logical_id",
        "attempt_id",
        "policy_id",
    },
    "START_SCENE": {
        "operation",
        "current_input",
        "projection",
        "attempt_id",
        "policy_id",
    },
    "PROJECT_SCENE": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "expected_record_hash",
        "selection",
    },
    "INSPECT_SCENE": {"operation", "project", "branch", "run_id", "step_id"},
    "RECOVER_SCENE": {
        "operation",
        "current_input",
        "project",
        "branch",
        "run_id",
        "step_id",
    },
    "INSPECT": {"operation", "project", "branch", "run_id"},
    "RECOVER": {"operation", "current_input", "project", "branch", "run_id"},
    "REPLACE_DRAFT": _REPLACE_DRAFT_FIELDS,
    "REPLACE_DRAFT_AND_PROJECT_SCENE": _REPLACE_DRAFT_FIELDS | {"fact_edits"},
    "EXPORT": {"operation", "project", "branch", "run_id", "output"},
}


def _text(row: dict[str, object], key: str) -> str:
    value = row[key]
    if type(value) is not str or not value.strip():
        raise WorkflowError("INVALID_WORKFLOW_TASK_REQUEST")
    return value


def _draft_selection(row: dict[str, object]) -> tuple[int, str, str | None]:
    version, predecessor = row["version"], row["expected_revision_hash"]
    if type(version) is not int or (
        predecessor is not None and type(predecessor) is not str
    ):
        raise WorkflowError("INVALID_WORKFLOW_TASK_REQUEST")
    return version, _text(row, "request_id"), predecessor


def _author_annotation_input(
    document: object,
) -> tuple[tuple[Q1Claim, ...], KnowledgeSnapshot | None, tuple[DeathTiming, ...]]:
    if (
        type(document) is not dict
        or "claims" not in document
        or set(document) - {"claims", "author_knowledge", "death_times"}
    ):
        raise WorkflowError("INVALID_Q1_AUTHOR_INPUT")
    claims, knowledge, deaths = (
        document["claims"],
        document.get("author_knowledge"),
        document.get("death_times", []),
    )
    if type(claims) is not list or type(deaths) is not list:
        raise WorkflowError("INVALID_Q1_AUTHOR_INPUT")
    try:
        return (
            tuple(claim_from_dict(claim) for claim in claims),
            None if knowledge is None else KnowledgeSnapshot.from_dict(knowledge),
            tuple(DeathTiming.from_dict(death) for death in deaths),
        )
    except (ValueError, TypeError, KeyError):
        raise WorkflowError("INVALID_Q1_AUTHOR_INPUT") from None


class _WrittenDraftInspectionOptions(TypedDict, total=False):
    version: int


class _WrittenDraftEditOptions(TypedDict, total=False):
    continuity: tuple[DraftContinuity, ...]


class WorkflowTaskAdapter:
    def __init__(self, service: ChapterWorkflow) -> None:
        self.service = service

    def execute(
        self, request: object
    ) -> (
        WorkflowSnapshot
        | SceneGenerationSnapshot
        | SceneProjection
        | ChapterAssembly
        | ChapterRevision
        | NextChapterDraftInput
        | NextChapterWrittenDraft
        | GatewayRequest
        | DraftEditPreview
        | DraftCommitmentReview
        | WrittenDraftImpact
        | WrittenDraftRevision
        | RunAssessment
        | RevisionAnnotationBinding
        | RevisionQualityReadback
        | ExtractionObservation
        | Q0Run
        | Q1Run
        | Q2Run
        | Q3Run
    ):
        if type(request) is not dict:
            raise WorkflowError("INVALID_WORKFLOW_TASK_REQUEST")
        row = cast(dict[str, object], request)
        operation = row.get("operation")
        fields = set(row)
        if operation == "ASSESS_RUN":
            fields.discard("q1_annotations_hash")
        if operation == "INSPECT_WRITTEN_DRAFT":
            fields.discard("output")
            fields.discard("version")
        if operation == "REVIEW_WRITTEN_DRAFT_COMMITMENTS":
            fields.discard("output")
        if operation == "EDIT_WRITTEN_DRAFT":
            if "preserve_unprovided_annotations" in row:
                if row["preserve_unprovided_annotations"] is not True:
                    raise WorkflowError("INVALID_WORKFLOW_TASK_REQUEST")
                fields.discard("preserve_unprovided_annotations")
                fields.add("choice")
            fields.discard("continuity")
        if operation == "APPLY_WRITTEN_DRAFT_EDIT_PREVIEW":
            fields.discard("resolutions")
        if operation == "REPLACE_DRAFT_AND_PROJECT_SCENE":
            fields.discard("output")
        if operation in {
            "PROJECT_NEXT_CHAPTER",
            "VERIFY_NEXT_CHAPTER",
            "PREPARE_NEXT_CHAPTER_MODEL_REQUEST",
            "WRITE_NEXT_CHAPTER_DRAFT",
        }:
            fields.discard("source_chapter_id")
        if operation in {
            "PREPARE_NEXT_CHAPTER_MODEL_REQUEST",
            "WRITE_NEXT_CHAPTER_DRAFT",
            "REWRITE_NEXT_CHAPTER_DRAFT",
        }:
            fields.discard("brief")
        if (
            type(operation) is not str
            or operation not in _FIELDS
            or fields != _FIELDS[operation]
        ):
            raise WorkflowError("INVALID_WORKFLOW_TASK_REQUEST")
        if operation == "EXPORT_CHAPTER":
            return self.service.export_chapter_assembly(
                FrozenChapterInput.from_dict(row["current_input"]),
                ChapterAssembly.from_dict(row["assembly"]),
                output=Path(_text(row, "output")),
            )
        if operation == "START_SCENE":
            return self.service.start_scene(
                FrozenChapterInput.from_dict(row["current_input"]),
                SceneProjection.from_dict(row["projection"]),
                attempt_id=_text(row, "attempt_id"),
                policy_id=_text(row, "policy_id"),
            )
        if operation == "CONTINUE_CHAPTER_DRAFT":
            version, request_id, predecessor = _draft_selection(row)
            return self.service.continue_chapter_draft(
                FrozenChapterInput.from_dict(row["current_input"]),
                SceneProjection.from_dict(row["projection"]),
                attempt_id=_text(row, "attempt_id"),
                policy_id=_text(row, "policy_id"),
                version=version,
                request_id=request_id,
                expected_revision_hash=predecessor,
                output=Path(_text(row, "output")),
            )
        run_id = _text(row, "run_id")
        if operation == "START":
            return self.service.start(
                FrozenChapterInput.from_dict(row["current_input"]),
                run_id=run_id,
                logical_id=_text(row, "logical_id"),
                attempt_id=_text(row, "attempt_id"),
                policy_id=_text(row, "policy_id"),
            )
        project, branch = _text(row, "project"), _text(row, "branch")
        if operation == "SAVE_NEXT_CHAPTER_DRAFT":
            return self.service.save_next_chapter_draft(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                expected_revision_hash=_text(row, "expected_revision_hash"),
                draft_payload=canonical_bytes(row["draft"]),
            )
        if operation == "INSPECT_WRITTEN_DRAFT":
            options: _WrittenDraftInspectionOptions = {}
            if "version" in row:
                inspection_version = row["version"]
                if type(inspection_version) is not int or inspection_version < 1:
                    raise WorkflowError("INVALID_WORKFLOW_TASK_REQUEST")
                options["version"] = inspection_version
            return self.service.inspect_written_draft(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                chapter_id=EntityId.from_dict(row["chapter_id"]),
                output=Path(_text(row, "output")) if "output" in row else None,
                **options,
            )
        if operation == "INSPECT_WRITTEN_DRAFT_IMPACT":
            return self.service.inspect_written_draft_impact(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                source_chapter_id=EntityId.from_dict(row["source_chapter_id"]),
                expected_revision_hash=_text(row, "expected_revision_hash"),
            )
        if operation == "REVIEW_WRITTEN_DRAFT_COMMITMENTS":
            return self.service.review_written_draft_commitments(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                chapter_id=EntityId.from_dict(row["chapter_id"]),
                expected_revision_hash=_text(row, "expected_revision_hash"),
                review=row["review"],
                output=Path(_text(row, "output")) if "output" in row else None,
            )
        if operation == "PREVIEW_WRITTEN_DRAFT_EDIT":
            return self.service.preview_written_draft_edit(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                chapter_id=EntityId.from_dict(row["chapter_id"]),
                expected_revision_hash=_text(row, "expected_revision_hash"),
                prose=_text(row, "text").encode("utf-8"),
                output=Path(_text(row, "output")),
            )
        if operation == "APPLY_WRITTEN_DRAFT_EDIT_PREVIEW":
            resolutions = row.get("resolutions", [])
            if type(resolutions) is not list:
                raise WorkflowError("INVALID_DRAFT_EDIT_RESOLUTION")
            if type(row["preview"]) is not dict:
                raise WorkflowError("INVALID_DRAFT_EDIT_PREVIEW")
            try:
                preview_payload = canonical_bytes(row["preview"])
            except ValueError:
                raise WorkflowError("INVALID_DRAFT_EDIT_PREVIEW") from None
            return self.service.apply_written_draft_edit_preview(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                chapter_id=EntityId.from_dict(row["chapter_id"]),
                prose=_text(row, "text").encode("utf-8"),
                preview_payload=preview_payload,
                resolutions=tuple(
                    DraftAnchorResolution.from_dict(item) for item in resolutions
                ),
            )
        if operation == "ANNOTATE_WRITTEN_DRAFT":
            return self.service.annotate_written_draft(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                chapter_id=EntityId.from_dict(row["chapter_id"]),
                expected_revision_hash=_text(row, "expected_revision_hash"),
                annotations=row["annotations"],
            )
        if operation == "EDIT_WRITTEN_DRAFT":
            edit_options: _WrittenDraftEditOptions = {}
            choice = row.get("choice")
            preserve_unprovided = row.get("preserve_unprovided_annotations") is True
            if "continuity" in row:
                continuity = row["continuity"]
                if type(continuity) is not list:
                    raise WorkflowError("INVALID_DRAFT_CONTINUITY")
                edit_options["continuity"] = tuple(
                    DraftContinuity.from_dict(item) for item in continuity
                )
            return self.service.edit_written_draft(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                chapter_id=EntityId.from_dict(row["chapter_id"]),
                expected_revision_hash=_text(row, "expected_revision_hash"),
                prose=_text(row, "text").encode("utf-8"),
                choice=None if choice is None else SceneSpan.from_dict(choice),
                preserve_choice=preserve_unprovided and "choice" not in row,
                preserve_continuity=preserve_unprovided and "continuity" not in row,
                **edit_options,
            )
        brief = DraftChapterBrief.from_dict(row["brief"]) if "brief" in row else None
        if operation == "PREPARE_NEXT_CHAPTER_MODEL_REQUEST":
            try:
                policy = ModelPolicy.from_dict(row["policy"])
            except (ValueError, TypeError, KeyError):
                raise WorkflowError("INVALID_NEXT_CHAPTER_MODEL_POLICY") from None
            return self.service.prepare_next_chapter_model_request(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                expected_revision_hash=_text(row, "expected_revision_hash"),
                retained_payload=canonical_bytes(row["handoff"]),
                policy=policy,
                output=Path(_text(row, "output")),
                source_chapter_id=EntityId.from_dict(row["source_chapter_id"])
                if "source_chapter_id" in row
                else None,
                brief=brief,
            )
        if operation == "WRITE_NEXT_CHAPTER_DRAFT":
            return self.service.write_next_chapter_draft(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                expected_revision_hash=_text(row, "expected_revision_hash"),
                retained_payload=canonical_bytes(row["handoff"]),
                output=Path(_text(row, "output")),
                source_chapter_id=EntityId.from_dict(row["source_chapter_id"])
                if "source_chapter_id" in row
                else None,
                brief=brief,
            )
        if operation == "REWRITE_NEXT_CHAPTER_DRAFT":
            return self.service.rewrite_next_chapter_draft(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                expected_revision_hash=_text(row, "expected_revision_hash"),
                source_chapter_id=EntityId.from_dict(row["source_chapter_id"]),
                expected_target_revision_hash=_text(
                    row, "expected_target_revision_hash"
                ),
                retained_payload=canonical_bytes(row["handoff"]),
                output=Path(_text(row, "output")),
                brief=brief,
            )
        if operation in {"PROJECT_NEXT_CHAPTER", "VERIFY_NEXT_CHAPTER"}:
            return self.service.next_chapter_draft_input(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                expected_revision_hash=_text(row, "expected_revision_hash"),
                output=Path(_text(row, "output"))
                if operation == "PROJECT_NEXT_CHAPTER"
                else None,
                retained_payload=canonical_bytes(row["handoff"])
                if operation == "VERIFY_NEXT_CHAPTER"
                else None,
                source_chapter_id=EntityId.from_dict(row["source_chapter_id"])
                if "source_chapter_id" in row
                else None,
            )
        if operation == "INSPECT_CHAPTER_REVISION":
            return self.service.inspect_chapter_revision(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
            )
        if operation == "EXPORT_CHAPTER_REVISION":
            return self.service.export_chapter_revision(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                expected_revision_hash=_text(row, "expected_revision_hash"),
                output=Path(_text(row, "output")),
            )
        if operation == "BIND_REVISION_ANNOTATIONS":
            claims, knowledge, deaths = _author_annotation_input(row["author_input"])
            return self.service.bind_revision_annotations(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                expected_revision_hash=_text(row, "expected_revision_hash"),
                claims=claims,
                author_knowledge=knowledge,
                death_times=deaths,
                output=None if row["output"] is None else Path(_text(row, "output")),
            )
        if operation == "FINISH_CHAPTER_DRAFT":
            version, request_id, predecessor = _draft_selection(row)
            return self.service.finish_chapter_draft(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=_text(row, "step_id"),
                version=version,
                request_id=request_id,
                expected_revision_hash=predecessor,
                output=Path(_text(row, "output")),
            )
        if operation == "SAVE_CHAPTER_REVISION":
            version, request_id, predecessor = _draft_selection(row)
            return self.service.save_observed_chapter_revision(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=_text(row, "step_id"),
                expected_observation_hash=_text(row, "expected_observation_hash"),
                version=version,
                request_id=request_id,
                expected_revision_hash=predecessor,
            )
        if operation in {"INSPECT_REVISION_QUALITY", "CHECK_REVISION_QUALITY"}:
            current = FrozenChapterInput.from_dict(row["current_input"])
            chapter_id = EntityId.from_dict(current.to_dict()["chapter_id"])
            try:
                revision_annotations = BoundQ1Annotations.from_dict(row["annotations"])
            except Q1Error as error:
                raise WorkflowError(str(error)) from None
            if operation == "INSPECT_REVISION_QUALITY":
                return self.service.inspect_revision_quality(
                    current,
                    revision_annotations,
                    project=project,
                    branch=branch,
                    chapter_id=chapter_id,
                    expected_run_id=run_id,
                )
            expected_revision = _text(row, "expected_revision_hash")
            if re.fullmatch(r"[0-9a-f]{64}", expected_revision) is None:
                raise WorkflowError("INVALID_WORKFLOW_TASK_REQUEST")
            return self.service.check_revision_quality(
                current,
                revision_annotations,
                project=project,
                branch=branch,
                chapter_id=chapter_id,
                expected_run_id=run_id,
                expected_revision_hash=expected_revision,
            )
        if operation == "PROJECT_SCENE":
            scene_selection = row["selection"]
            expected = _text(row, "expected_record_hash")
            manual_fields = {
                "source_scene_id",
                "target_scene_id",
                "source_span",
                "ending_span",
                "delta_binding",
            }
            if (
                type(scene_selection) is not dict
                or set(scene_selection)
                not in (manual_fields, {"delta_binding"}, {"fact_edits"})
                or re.fullmatch(r"[0-9a-f]{64}", expected) is None
            ):
                raise WorkflowError("INVALID_SCENE_PROJECTION_SELECTION")
            try:
                source = target = source_span = ending_span = None
                if set(scene_selection) == manual_fields:
                    source = EntityId.from_dict(scene_selection["source_scene_id"])
                    target = EntityId.from_dict(scene_selection["target_scene_id"])
                    source_span = SceneSpan.from_dict(scene_selection["source_span"])
                    ending_span = SceneSpan.from_dict(scene_selection["ending_span"])
                binding = (
                    SceneDeltaBinding.from_dict(scene_selection["delta_binding"])
                    if "delta_binding" in scene_selection
                    else None
                )
            except ValueError:
                raise WorkflowError("INVALID_SCENE_PROJECTION_SELECTION") from None
            current = FrozenChapterInput.from_dict(row["current_input"])
            try:
                return self.service.project_scene(
                    current,
                    project=project,
                    branch=branch,
                    run_id=run_id,
                    expected_record_hash=expected,
                    source_scene_id=source,
                    target_scene_id=target,
                    source_span=source_span,
                    ending_span=ending_span,
                    delta_binding=binding,
                    fact_edits=scene_selection.get("fact_edits"),
                )
            except ContextError as error:
                raise WorkflowError(str(error)) from None
        if operation in {"CHECK_Q3", "INSPECT_Q3"}:
            q3_method = (
                self.service.check_q3
                if operation == "CHECK_Q3"
                else self.service.inspect_q3
            )
            return q3_method(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=_text(row, "step_id"),
            )
        if operation in {"CHECK_Q2", "INSPECT_Q2"}:
            q2_method = (
                self.service.check_q2
                if operation == "CHECK_Q2"
                else self.service.inspect_q2
            )
            return q2_method(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=_text(row, "step_id"),
            )
        if operation in {"CHECK_Q1", "INSPECT_Q1"}:
            q1_method = (
                self.service.check_q1
                if operation == "CHECK_Q1"
                else self.service.inspect_q1
            )
            try:
                annotations = BoundQ1Annotations.from_dict(row["annotations"])
                return q1_method(
                    FrozenChapterInput.from_dict(row["current_input"]),
                    annotations,
                    project=project,
                    branch=branch,
                    run_id=run_id,
                    step_id=_text(row, "step_id"),
                )
            except Q1Error as error:
                raise WorkflowError(str(error)) from None
        if operation in {"CHECK_Q0", "INSPECT_Q0"}:
            q0_method = (
                self.service.check_q0
                if operation == "CHECK_Q0"
                else self.service.inspect_q0
            )
            return q0_method(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=_text(row, "step_id"),
            )
        if operation in {"EXTRACT_CHAPTER", "INSPECT_EXTRACTION"}:
            method = (
                self.service.extract_chapter
                if operation == "EXTRACT_CHAPTER"
                else self.service.inspect_extraction
            )
            return method(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=_text(row, "step_id"),
            )
        if operation == "ASSESS_RUN":
            selected = row["step_id"]
            if selected is not None and (
                type(selected) is not str or not selected.strip()
            ):
                raise WorkflowError("INVALID_WORKFLOW_TASK_REQUEST")
            selection: dict[str, str] = {}
            if "q1_annotations_hash" in row:
                annotations_hash = _text(row, "q1_annotations_hash")
                if re.fullmatch(r"[0-9a-f]{64}", annotations_hash) is None:
                    raise WorkflowError("INVALID_WORKFLOW_TASK_REQUEST")
                selection["q1_annotations_hash"] = annotations_hash
            return self.service.assess_run(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=selected,
                **selection,
            )
        if operation == "ASSEMBLE_CHAPTER":
            return self.service.assemble_chapter(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=_text(row, "step_id"),
            )
        if operation == "VERIFY_CHAPTER_EXPORT":
            return self.service.verify_chapter_export(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=_text(row, "step_id"),
                output=Path(_text(row, "output")),
            )
        if operation == "INSPECT_SCENE":
            return self.service.inspect_scene(
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=_text(row, "step_id"),
            )
        if operation == "RECOVER_SCENE":
            return self.service.recover_scene(
                FrozenChapterInput.from_dict(row["current_input"]),
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=_text(row, "step_id"),
            )
        if operation == "INSPECT":
            return self.service.inspect(project=project, branch=branch, run_id=run_id)
        if operation == "EXPORT":
            return self.service.export_draft(
                project=project,
                branch=branch,
                run_id=run_id,
                output=Path(_text(row, "output")),
            )
        current = FrozenChapterInput.from_dict(row["current_input"])
        if operation == "RECOVER":
            return self.service.recover(
                current, project=project, branch=branch, run_id=run_id
            )
        revision = row["expected_revision"]
        if type(revision) is not int:
            raise WorkflowError("INVALID_WORKFLOW_TASK_REQUEST")
        expected_prose_hash = _text(row, "expected_prose_hash")
        prose = _text(row, "text").encode("utf-8")
        if operation == "REPLACE_DRAFT_AND_PROJECT_SCENE":
            try:
                return self.service.replace_draft_and_project_scene(
                    current,
                    project=project,
                    branch=branch,
                    run_id=run_id,
                    expected_revision=revision,
                    expected_prose_hash=expected_prose_hash,
                    prose=prose,
                    fact_edits=row["fact_edits"],
                    output=Path(_text(row, "output")) if "output" in row else None,
                )
            except ContextError as error:
                raise WorkflowError(str(error)) from None
        return self.service.replace_draft(
            current,
            project=project,
            branch=branch,
            run_id=run_id,
            expected_revision=revision,
            expected_prose_hash=expected_prose_hash,
            prose=prose,
        )


def _q2_diagnostic_summary(finding: Q2Finding) -> dict[str, object]:
    span = finding.span
    return {
        "code": finding.code,
        "verdict": finding.verdict,
        "span": (
            None
            if span is None
            else {
                "start": span.start,
                "end": span.end,
                "byte_start": span.byte_start,
                "byte_end": span.byte_end,
            }
        ),
    }


def snapshot_summary(
    saved: WorkflowSnapshot
    | SceneGenerationSnapshot
    | SceneProjection
    | ChapterAssembly
    | ChapterRevision
    | NextChapterDraftInput
    | NextChapterWrittenDraft
    | GatewayRequest
    | DraftEditPreview
    | DraftCommitmentReview
    | WrittenDraftImpact
    | WrittenDraftRevision
    | RunAssessment
    | RevisionAnnotationBinding
    | RevisionQualityReadback
    | ExtractionObservation
    | Q0Run
    | Q1Run
    | Q2Run
    | Q3Run,
) -> dict[str, object]:
    """Display metadata and grounded quality values without printing prose."""
    if isinstance(saved, DraftCommitmentReview):
        return saved.summary()
    if isinstance(saved, GatewayRequest):
        return {
            "state": "DRAFT_NEXT_CHAPTER_MODEL_REQUEST_PREPARED",
            "artifact_state": "DRAFT",
            "project": saved.project,
            "branch": saved.branch,
            "run_id": saved.run_id,
            "logical_id": saved.logical_id,
            "semantic_hash": saved.semantic_hash,
            "model_hash": saved.context.model_hash,
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, DraftEditPreview):
        return {
            "state": "DRAFT_EDIT_PREVIEW",
            "artifact_state": "DRAFT",
            "chapter_id": saved.chapter_id.to_dict(),
            "revision_hash": saved.revision_hash,
            "prose_hash": saved.prose_hash,
            "continuity_count": len(saved.continuity),
            "review_required_count": len(saved.issues),
            "choice_retained": saved.choice is not None,
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, WrittenDraftImpact):
        return {
            **saved.to_dict(),
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, WrittenDraftRevision):
        return {
            "state": "WRITTEN_CHAPTER_DRAFT_SAVED",
            "artifact_state": "DRAFT",
            "project": saved.project,
            "branch": saved.branch,
            "run_id": saved.run_id,
            "chapter_id": saved.chapter_id.to_dict(),
            "chapter_number": saved.chapter_number,
            "candidate_version": saved.version,
            "revision_hash": saved.record_hash,
            "previous_revision_hash": saved.previous_revision_hash,
            "source_revision_hash": saved.source_revision_hash,
            "prose_hash": saved.prose_hash,
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, NextChapterWrittenDraft):
        return {
            "state": "DRAFT_NEXT_CHAPTER_WRITTEN",
            "artifact_state": "DRAFT",
            "source_revision_hash": saved.handoff.source.record_hash,
            "target_chapter_id": saved.handoff.target.id.to_dict(),
            "target_chapter_number": saved.handoff.target.number,
            "handoff_hash": saved.handoff.record_hash,
            "writer_input_hash": saved.writer_input_hash,
            "prose_hash": saved.prose_hash,
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, NextChapterDraftInput):
        return {
            "state": "DRAFT_NEXT_CHAPTER_INPUT",
            "artifact_state": "DRAFT",
            "source_revision_hash": saved.source.record_hash,
            "source_version": saved.source_version,
            "target_chapter_id": saved.target.id.to_dict(),
            "target_chapter_number": saved.target.number,
            "record_hash": saved.record_hash,
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, RevisionAnnotationBinding):
        return {
            "state": "DRAFT_REVISION_ANNOTATIONS_BOUND",
            "revision_hash": saved.revision_hash,
            "candidate_version": saved.candidate_version,
            "observation_hash": saved.observation_hash,
            "annotations_hash": saved.annotations.record_hash,
            "claim_count": len(saved.annotations.claims),
            "coverage_status": "NOT_VERIFIED",
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, ChapterRevision):
        return {
            "state": "DRAFT_CHAPTER_REVISION_SAVED",
            "artifact_state": saved.artifact_state,
            "project": saved.project,
            "branch": saved.branch,
            "run_id": saved.run_id,
            "step_id": saved.step_id,
            "chapter_id": saved.chapter_id.to_dict(),
            "candidate_version": saved.version,
            "revision_hash": saved.record_hash,
            "previous_revision_hash": saved.previous_revision_hash,
            "observation_hash": saved.observation_hash,
            "assembly_hash": saved.assembly_hash,
            "candidate_payload_hash": saved.candidate.payload_hash,
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, RevisionQualityReadback):
        checks = {
            name: {"status": check.status, "record_hash": check.record_hash}
            for name, check in (
                ("Q0", saved.q0),
                ("Q1", saved.q1),
                ("Q2", saved.q2),
                ("Q3", saved.q3),
            )
        }
        return {
            "state": "DRAFT_REVISION_QUALITY",
            "revision_hash": saved.revision_hash,
            "candidate_version": saved.candidate_version,
            "observation_hash": saved.observation_hash,
            "q0_policy_hash": saved.q0_policy_hash,
            "q123_policy_hash": saved.q123_policy_hash,
            "annotations_hash": saved.annotations_hash,
            "q123_record_hash": saved.q123_record_hash,
            "checks": checks,
            "missing_checks": [
                name for name, check in checks.items() if check["status"] == "MISSING"
            ],
            "q2_diagnostics": [
                _q2_diagnostic_summary(item) for item in saved.q2_diagnostics
            ],
            "q3_required_transition_diagnostics": [
                item.to_dict() for item in saved.q3_required_transition_diagnostics
            ],
            "aggregate_status": saved.aggregate_status,
            "semantic_status": saved.semantic_status,
            "can_commit": saved.can_commit,
            "can_issue_permit": saved.can_issue_permit,
            "can_dispatch": saved.can_dispatch,
            "accepted": saved.accepted,
            "published": saved.published,
        }
    if isinstance(saved, SceneProjection):
        candidate = saved.candidate
        return {
            "project": saved.inputs.request.project,
            "branch": saved.inputs.request.branch,
            "run_id": candidate.source_run_id,
            "state": "DRAFT_SCENE_PROJECTED",
            "source_record_hash": candidate.source_record_hash,
            "source_revision": candidate.source_revision,
            "candidate_hash": candidate.content_hash,
            "context_hash": saved.context.content_hash,
            "projection_hash": sha256(canonical_bytes(saved.to_dict())).hexdigest(),
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, Q3Run):
        return {
            "project": saved.project,
            "branch": saved.branch,
            "run_id": saved.run_id,
            "step_id": saved.step_id,
            "state": "DRAFT_Q3_CHECKED_LOCAL_ONLY",
            "record_hash": saved.record_hash,
            "observation_hash": saved.observation_hash,
            "assembly_hash": saved.assembly_hash,
            "prose_hash": saved.prose_hash,
            "method_policy_hash": saved.method_policy_hash,
            "q3_status": saved.q3_status,
            "evidence_scope": Q3_PROFILE,
            "source_qualification": saved.source_qualification,
            "coverage_status": saved.coverage_status,
            "finite_coverage_status": saved.evidence.finite_coverage_status,
            "correspondence_status": saved.evidence.correspondence_status,
            "transition_status": saved.transition_status,
            "required_transition_diagnostics": [
                item.to_dict()
                for item in saved.evidence.required_transition_diagnostics
            ],
            "continuation_status": saved.continuation_status,
            "knowledge_status": saved.knowledge_status,
            "semantic_status": saved.semantic_status,
            "production_source_status": saved.production_status,
            "source_correspondence_status": saved.observation.correspondence_status,
            "aggregate_status": saved.aggregate_status,
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, Q2Run):
        return {
            "project": saved.project,
            "branch": saved.branch,
            "run_id": saved.run_id,
            "step_id": saved.step_id,
            "state": "DRAFT_Q2_CHECKED_LOCAL_ONLY",
            "record_hash": saved.record_hash,
            "observation_hash": saved.observation_hash,
            "assembly_hash": saved.assembly_hash,
            "prose_hash": saved.prose_hash,
            "method_policy_hash": saved.method_policy_hash,
            "q2_status": saved.q2_status,
            "evidence_scope": "LOCAL_RAW_GENRE_V1",
            "source_qualification": "FINITE_RAW_GRAMMAR_LOCAL_TEST",
            "coverage_status": saved.coverage_status,
            "finite_coverage_status": saved.evidence.finite_coverage_status,
            "correspondence_status": saved.evidence.correspondence_status,
            "genre_status": saved.evidence.genre_status,
            "diagnostics": [_q2_diagnostic_summary(item) for item in saved.diagnostics],
            "production_source_status": saved.production_status,
            "source_correspondence_status": saved.observation.correspondence_status,
            "aggregate_status": saved.aggregate_status,
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, Q1Run):
        return {
            "project": saved.project,
            "branch": saved.branch,
            "run_id": saved.run_id,
            "step_id": saved.step_id,
            "state": "DRAFT_Q1_CHECKED_LOCAL_ONLY",
            "record_hash": saved.record_hash,
            "observation_hash": saved.observation_hash,
            "annotations_hash": saved.annotations_hash,
            "assembly_hash": saved.assembly_hash,
            "q1_status": saved.q1_status,
            "evidence_scope": "BOUND_ANNOTATIONS_LOCAL_TEST",
            "source_qualification": saved.source_qualification,
            "knowledge_source": saved.knowledge_source,
            "coverage_status": saved.coverage_status,
            "production_source_status": saved.production_status,
            "source_correspondence_status": saved.observation.correspondence_status,
            "aggregate_status": saved.aggregate_status,
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, Q0Run):
        return {
            "project": saved.project,
            "branch": saved.branch,
            "run_id": saved.run_id,
            "step_id": saved.step_id,
            "state": "DRAFT_Q0_CHECKED_LOCAL_ONLY",
            "record_hash": saved.record_hash,
            "observation_hash": saved.observation_hash,
            "assembly_hash": saved.assembly_hash,
            "prose_hash": saved.prose_hash,
            "q0_status": saved.q0_status,
            "evidence_scope": "LOCAL_DETERMINISTIC_Q0_NOT_PRODUCTION_QUALITY",
            "source_correspondence_status": saved.observation.correspondence_status,
            "aggregate_status": saved.aggregate_status,
            "semantic_status": "UNKNOWN",
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, ExtractionObservation):
        return {
            "project": saved.project,
            "branch": saved.branch,
            "run_id": saved.run_id,
            "step_id": saved.step_id,
            "state": "DRAFT_EXTRACTION_OBSERVED",
            "record_hash": saved.record_hash,
            "assembly_hash": saved.assembly_hash,
            "prose_hash": saved.prose_hash,
            "operation_count": saved.operation_count,
            "correspondence_status": saved.correspondence_status,
            "semantic_status": "UNKNOWN",
            "can_commit": False,
            "can_issue_permit": False,
            "can_dispatch": False,
            "accepted": False,
            "published": False,
        }
    if isinstance(saved, RunAssessment):
        return saved.to_dict()
    if isinstance(saved, ChapterAssembly):
        return {
            "project": saved.project,
            "branch": saved.branch,
            "run_id": saved.run_id,
            "step_id": saved.step_id,
            "state": "DRAFT_ASSEMBLED",
            "record_hash": saved.record_hash,
            "prose_hash": saved.prose_hash,
            "accepted": False,
            "published": False,
            "whole_chapter_delta": "NOT_EXTRACTED_NOT_VALIDATED",
        }
    if isinstance(saved, SceneGenerationSnapshot):
        return {
            "project": saved.project,
            "branch": saved.branch,
            "run_id": saved.run_id,
            "step_id": saved.step_id,
            "state": saved.state,
            "record_hash": saved.record_hash,
            "source_record_hash": saved.source.record_hash,
            "accepted": False,
            "has_draft": saved.state == "DRAFT_SAVED",
            "diagnostic": saved.diagnostic,
        }
    return {
        "project": saved.project,
        "branch": saved.branch,
        "run_id": saved.run_id,
        "state": saved.state,
        "revision": saved.revision,
        "prose_hash": saved.prose_hash,
        "input_hash": saved.input_hash,
        "record_hash": saved.record_hash,
        "accepted": saved.accepted,
        "diagnostic": saved.diagnostic,
        "invalidated_evidence": list(saved.invalidated_evidence),
        "pending_capabilities": list(saved.pending_capabilities),
    }
