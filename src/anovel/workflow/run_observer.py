"""Observe one existing offline run; observations never grant capabilities.

Observes retained local inputs, Drafts, receipts, extraction and quality records.
The readback never executes checks, dispatches, issues a Permit or commits to Canon.
"""

from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from anovel.canon.identity import canonical_bytes
from anovel.quality.q2 import METHOD_POLICY_HASH as Q2_METHOD_POLICY_HASH
from anovel.quality.q3 import METHOD_POLICY_HASH as Q3_METHOD_POLICY_HASH

from .gateway_binding import verify_scene_receipt
from .generation import SceneGenerationSnapshot
from .models import FrozenChapterInput, WorkflowError
from .run import (
    EXTRACTION_STAGE,
    OBSERVED_STAGES,
    QUALITY_CHECKS,
    QUALITY_STAGE,
    QualityObservation,
    RunAssessment,
    RunStageObservation,
)

if TYPE_CHECKING:
    from anovel.quality.q0 import Q0Run
    from anovel.quality.q1 import Q1Run
    from anovel.quality.q2 import Q2Run
    from anovel.quality.q3 import Q3Run

    from .assembly import ChapterAssembly
    from .chapter import ChapterWorkflow

_INVALID_SCENE_RECORD = frozenset(
    {
        "CORRUPT_SCENE_GENERATION",
        "INVALID_SCENE_GENERATION",
        "INVALID_SCENE_GENERATION_SCHEMA",
    }
)
_STALE_SCENE_INPUT = frozenset(
    {
        "SCENE_SOURCE_CHANGED",
        "SCENE_CONTRACT_CHANGED",
        "SCENE_SOURCES_CHANGED",
        "SCENE_CONTEXT_CHANGED",
    }
)
_UPSTREAM_INPUT_ERROR = frozenset(
    {
        "WORKFLOW_INPUT_CHANGED",
        "INVALID_FROZEN_CHAPTER_INPUT",
        "CONTRACT_NOT_READY",
        "WRITER_CONTEXT_NOT_READY",
        "FROZEN_INPUT_COMPILATION_FAILED",
    }
)
_EXTRACTION_LOOKUP_STOPS = {
    "EXTRACTION_OBSERVATION_UNAVAILABLE": (
        "MISSING",
        "EXTRACTION_OBSERVATION_UNAVAILABLE",
    ),
    "CORRUPT_EXTRACTION_OBSERVATION": ("BLOCKED", "EXTRACTION_OBSERVATION_INVALID"),
    "INVALID_EXTRACTION_SCHEMA": ("BLOCKED", "EXTRACTION_OBSERVATION_INVALID"),
    "EXTRACTION_SOURCE_CHANGED": ("STALE", "EXTRACTION_SOURCE_CHANGED"),
}
_EXTRACTION_CORRESPONDENCE = {
    "PASS": ("CURRENT", "CURRENT"),
    "FAIL": ("BLOCKED", "EXTRACTION_CORRESPONDENCE_FAIL"),
    "UNKNOWN": ("BLOCKED", "EXTRACTION_CORRESPONDENCE_UNKNOWN"),
    "ERROR": ("BLOCKED", "EXTRACTION_CORRESPONDENCE_ERROR"),
}


def _refs(**values: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(values.items()))


def _observe_extraction(
    service: ChapterWorkflow, assembly: ChapterAssembly
) -> RunStageObservation:
    try:
        saved = service.store.load_extraction(
            project=assembly.project,
            branch=assembly.branch,
            run_id=assembly.run_id,
            step_id=assembly.step_id,
            assembly_hash=assembly.record_hash,
        )
        if saved.assembly.payload_bytes() != assembly.payload_bytes():
            raise WorkflowError("EXTRACTION_SOURCE_CHANGED")
    except WorkflowError as error:
        stop = _EXTRACTION_LOOKUP_STOPS.get(str(error))
        if stop is None:
            raise
        return RunStageObservation(EXTRACTION_STAGE, *stop)
    correspondence = _EXTRACTION_CORRESPONDENCE.get(saved.correspondence_status)
    if correspondence is None:
        return RunStageObservation(
            EXTRACTION_STAGE, "BLOCKED", "EXTRACTION_OBSERVATION_INVALID"
        )
    state, reason = correspondence
    return RunStageObservation(
        EXTRACTION_STAGE,
        state,
        reason,
        _refs(
            assembly_hash=assembly.record_hash,
            assembly_prose_hash=assembly.prose_hash,
            extraction_observation_hash=saved.record_hash,
        ),
    )


def _observe_quality(
    service: ChapterWorkflow,
    assembly: ChapterAssembly,
    extraction: RunStageObservation,
    check: str,
    q1_annotations_hash: str | None,
) -> QualityObservation:
    if check == "Q1" and q1_annotations_hash is None:
        return QualityObservation(check, "INPUT_REQUIRED")
    observation_hash = dict(extraction.refs)["extraction_observation_hash"]
    scope = {
        "project": assembly.project,
        "branch": assembly.branch,
        "run_id": assembly.run_id,
        "step_id": assembly.step_id,
        "observation_hash": observation_hash,
    }
    saved: Q0Run | Q1Run | Q2Run | Q3Run
    try:
        if check == "Q0":
            q0 = service.store.load_q0(**scope)
            saved, state = q0, q0.q0_status
            binding = {"input_hash": q0.input_hash}
        elif check == "Q1":
            assert q1_annotations_hash is not None
            q1 = service.store.load_q1(**scope, annotations_hash=q1_annotations_hash)
            if q1.annotations_hash != q1_annotations_hash:
                return QualityObservation(check, "STALE")
            saved, state = q1, q1.q1_status
            binding = {"annotations_hash": q1.annotations_hash}
        elif check == "Q2":
            q2 = service.store.load_q2(
                **scope, method_policy_hash=Q2_METHOD_POLICY_HASH
            )
            if q2.method_policy_hash != Q2_METHOD_POLICY_HASH:
                return QualityObservation(check, "STALE")
            saved, state = q2, q2.q2_status
            binding = {"method_policy_hash": q2.method_policy_hash}
        else:
            assert check == "Q3"
            q3 = service.store.load_q3(
                **scope, method_policy_hash=Q3_METHOD_POLICY_HASH
            )
            if q3.method_policy_hash != Q3_METHOD_POLICY_HASH:
                return QualityObservation(check, "STALE")
            saved, state = q3, q3.q3_status
            binding = {"method_policy_hash": q3.method_policy_hash}
    except WorkflowError as error:
        code = str(error)
        if code == f"{check}_EXECUTION_UNAVAILABLE":
            return QualityObservation(check, "MISSING")
        if code in {
            f"CORRUPT_{check}_EXECUTION",
            f"INVALID_{check}_SCHEMA",
            "CORRUPT_EXTRACTION_OBSERVATION",
            "INVALID_EXTRACTION_SCHEMA",
        }:
            return QualityObservation(check, "INVALID")
        if code in {
            f"{check}_SOURCE_CHANGED",
            f"{check}_METHOD_POLICY_CHANGED",
            "EXTRACTION_SOURCE_CHANGED",
        }:
            return QualityObservation(check, "STALE")
        raise
    if (
        saved.observation_hash != observation_hash
        or saved.assembly_hash != assembly.record_hash
        or saved.prose_hash != assembly.prose_hash
    ):
        return QualityObservation(check, "STALE")
    if state not in {"PASS", "FAIL", "UNKNOWN", "ERROR"}:
        return QualityObservation(check, "INVALID")
    return QualityObservation(
        check,
        state,
        _refs(
            observation_hash=observation_hash, record_hash=saved.record_hash, **binding
        ),
    )


def assess_workflow_run(
    service: ChapterWorkflow,
    current: FrozenChapterInput,
    *,
    project: str,
    branch: str,
    run_id: str,
    step_id: str | None = None,
    q1_annotations_hash: str | None = None,
) -> RunAssessment:
    """Inspect the fixed two-scene pipeline without changing its run state.

    The default slot is the existing generation-V1 identity derived from the
    current source record. An explicit historical slot can instead diagnose a
    stale child. Missing prerequisites never select or create another attempt.
    """
    if step_id is not None and (
        type(step_id) is not str or re.fullmatch(r"[0-9a-f]{64}", step_id) is None
    ):
        raise WorkflowError("INVALID_RUN_ASSESSMENT_REQUEST")
    if q1_annotations_hash is not None and (
        type(q1_annotations_hash) is not str
        or re.fullmatch(r"[0-9a-f]{64}", q1_annotations_hash) is None
    ):
        raise WorkflowError("INVALID_RUN_ASSESSMENT_REQUEST")
    with (
        service.store.exclusive(project=project, branch=branch, run_id=run_id),
        service.store.reuse_observation_decodes(),
    ):
        source = service.store.load(project=project, branch=branch, run_id=run_id)
        # Missing/corrupt roots, wrong scope and changed current inputs are
        # request failures, not an invented graph with placeholder identities.
        service._current(source, current)
        contract = source.contract
        observations = [
            RunStageObservation(
                "FROZEN_INPUTS",
                "CURRENT",
                "CURRENT",
                _refs(
                    input_hash=source.input_hash,
                    source_record_hash=source.record_hash,
                    source_request_hash=sha256(source.request_bytes).hexdigest(),
                    contract_hash=contract.content_hash,
                    context_hash=sha256(source.context_bytes).hexdigest(),
                    pack_hash=contract.pack_hash,
                ),
            )
        ]
        child: SceneGenerationSnapshot | None = None
        observed_slot = False
        lookup_error: str | None = None
        selected_step = step_id
        assembly: ChapterAssembly | None = None
        extraction: RunStageObservation | None = None
        quality: tuple[QualityObservation, ...] | None = None

        def read_quality(
            assembled: ChapterAssembly, observed: RunStageObservation
        ) -> tuple[QualityObservation, ...]:
            return tuple(
                _observe_quality(
                    service, assembled, observed, check, q1_annotations_hash
                )
                for check in QUALITY_CHECKS
            )

        def finish() -> RunAssessment:
            for stage in OBSERVED_STAGES[len(observations) :]:
                observations.append(
                    RunStageObservation(
                        stage, "NOT_REACHED", "PREREQUISITE_NOT_CURRENT"
                    )
                )
            observations.extend(
                (
                    RunStageObservation(
                        "PRODUCTION_PERMIT",
                        "NOT_AUTHORIZED",
                        "PRODUCTION_PERMIT_NOT_AUTHORIZED",
                    ),
                    RunStageObservation(
                        "CANON_ACCEPTANCE",
                        "NOT_REACHED",
                        "CANON_ACCEPTANCE_NOT_REACHED",
                    ),
                )
            )
            try:
                if assembly is not None and extraction is not None:
                    if (
                        quality is not None
                        and read_quality(assembly, extraction) != quality
                    ):
                        raise WorkflowError("RUN_CHANGED_DURING_ASSESSMENT")
                    if _observe_extraction(service, assembly) != extraction:
                        raise WorkflowError("RUN_CHANGED_DURING_ASSESSMENT")
                fresh_source = service.store.load(
                    project=project, branch=branch, run_id=run_id
                )
                if fresh_source.record_hash != source.record_hash:
                    raise WorkflowError("RUN_CHANGED_DURING_ASSESSMENT")
                if observed_slot:
                    assert selected_step is not None
                    try:
                        fresh_child = service.store.load_scene(
                            project=project,
                            branch=branch,
                            run_id=run_id,
                            step_id=selected_step,
                        )
                    except WorkflowError as error:
                        if lookup_error is None or str(error) != lookup_error:
                            raise WorkflowError(
                                "RUN_CHANGED_DURING_ASSESSMENT"
                            ) from None
                    else:
                        if (
                            child is None
                            or fresh_child.record_hash != child.record_hash
                        ):
                            raise WorkflowError("RUN_CHANGED_DURING_ASSESSMENT")
            except WorkflowError:
                raise WorkflowError("RUN_CHANGED_DURING_ASSESSMENT") from None
            return RunAssessment(
                project=project,
                branch=branch,
                run_id=run_id,
                input_hash=source.input_hash,
                source_record_hash=source.record_hash,
                step_id=selected_step,
                stages=tuple(observations),
                schema_version="1.3",
                q1_annotations_hash=q1_annotations_hash,
                quality_observations=(
                    quality
                    if quality is not None
                    else tuple(
                        QualityObservation(check, "NOT_REACHED")
                        for check in QUALITY_CHECKS
                    )
                ),
            )

        if source.state != "DRAFT_SAVED" or source.prose is None:
            observations.append(
                RunStageObservation(
                    "SOURCE_DRAFT",
                    "BLOCKED",
                    "GATEWAY_OUTCOME_UNKNOWN"
                    if source.state == "UNKNOWN"
                    else "SOURCE_DRAFT_NOT_READY",
                )
            )
            return finish()
        source_refs = {
            "source_record_hash": source.record_hash,
            "source_prose_hash": sha256(source.prose).hexdigest(),
        }
        if source.result_bytes is not None:
            source_refs["source_result_hash"] = sha256(source.result_bytes).hexdigest()
        observations.append(
            RunStageObservation(
                "SOURCE_DRAFT", "CURRENT", "CURRENT", _refs(**source_refs)
            )
        )
        if len(contract.scenes) != 2:
            observations.append(
                RunStageObservation(
                    "SCENE_BINDING", "UNSUPPORTED", "TWO_SCENE_PIPELINE_UNSUPPORTED"
                )
            )
            return finish()
        if selected_step is None:
            selected_step = sha256(
                canonical_bytes(
                    {
                        "run_id": run_id,
                        "source_record_hash": source.record_hash,
                        "target_scene_id": contract.scenes[1].id.to_dict(),
                    }
                )
            ).hexdigest()
        observed_slot = True
        try:
            child = service.store.load_scene(
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=selected_step,
            )
        except WorkflowError as error:
            lookup_error = str(error)
            if lookup_error == "SCENE_GENERATION_UNAVAILABLE":
                state, reason = "MISSING", "SCENE_BINDING_REQUIRED"
            elif lookup_error == "SCENE_SOURCE_CHANGED":
                state, reason = "STALE", "SCENE_SOURCE_CHANGED"
            elif lookup_error in _INVALID_SCENE_RECORD:
                state, reason = "BLOCKED", "SCENE_RECORD_INVALID"
            else:
                raise
            observations.append(RunStageObservation("SCENE_BINDING", state, reason))
            return finish()
        if child.state == "STALE_SOURCE":
            observations.append(
                RunStageObservation("SCENE_BINDING", "STALE", "SCENE_SOURCE_CHANGED")
            )
            return finish()
        try:
            context = service._scene_context(source, current, child.projection)
            if context.to_bytes() != child.projection.context.to_bytes():
                raise WorkflowError("SCENE_CONTEXT_CHANGED")
        except WorkflowError as error:
            code = str(error)
            if code in _UPSTREAM_INPUT_ERROR:
                raise
            state = "STALE" if code in _STALE_SCENE_INPUT else "BLOCKED"
            reason = code if code in _STALE_SCENE_INPUT else "SCENE_CONTEXT_INVALID"
            observations.append(RunStageObservation("SCENE_BINDING", state, reason))
            return finish()
        observations.append(
            RunStageObservation(
                "SCENE_BINDING",
                "CURRENT",
                "CURRENT",
                _refs(
                    child_record_hash=child.record_hash,
                    projection_hash=sha256(
                        canonical_bytes(child.projection.to_dict())
                    ).hexdigest(),
                    context_hash=context.content_hash,
                ),
            )
        )
        if child.state != "DRAFT_SAVED":
            observations.append(
                RunStageObservation(
                    "SCENE_DRAFT",
                    "BLOCKED",
                    "GATEWAY_OUTCOME_UNKNOWN"
                    if child.state == "UNKNOWN"
                    else "SCENE_DRAFT_NOT_READY",
                )
            )
            return finish()
        try:
            verify_scene_receipt(Path(child.ledger_pin.path), service.store, child)
        except WorkflowError:
            observations.append(
                RunStageObservation("SCENE_DRAFT", "BLOCKED", "SCENE_RECEIPT_INVALID")
            )
            return finish()
        # A typed DRAFT_SAVED record has both exact retained result and prose;
        # the preceding read has additionally checked the real ledger receipt.
        assert child.result_bytes is not None and child.prose is not None
        observations.append(
            RunStageObservation(
                "SCENE_DRAFT",
                "CURRENT",
                "CURRENT",
                _refs(
                    child_record_hash=child.record_hash,
                    child_request_hash=child.request.content_hash,
                    child_result_hash=sha256(child.result_bytes).hexdigest(),
                    child_prose_hash=sha256(child.prose).hexdigest(),
                ),
            )
        )
        try:
            assembly = service._chapter_assembly(
                current,
                project=project,
                branch=branch,
                run_id=run_id,
                step_id=selected_step,
            )
        except WorkflowError as error:
            if str(error) in _UPSTREAM_INPUT_ERROR:
                raise
            observations.append(
                RunStageObservation(
                    "CHAPTER_ASSEMBLY", "BLOCKED", "CHAPTER_ASSEMBLY_INVALID"
                )
            )
            return finish()
        if (
            assembly.source_record_hash != source.record_hash
            or assembly.child_record_hash != child.record_hash
        ):
            raise WorkflowError("RUN_CHANGED_DURING_ASSESSMENT")
        observations.append(
            RunStageObservation(
                "CHAPTER_ASSEMBLY",
                "CURRENT",
                "CURRENT",
                _refs(
                    assembly_hash=assembly.record_hash,
                    assembly_prose_hash=assembly.prose_hash,
                ),
            )
        )
        extraction = _observe_extraction(service, assembly)
        observations.append(extraction)
        if extraction.refs:
            quality = read_quality(assembly, extraction)
        if extraction.state == "CURRENT":
            observations.append(
                RunStageObservation(
                    QUALITY_STAGE, "BLOCKED", "LOCAL_QUALITY_OBSERVATIONS_ONLY"
                )
            )
        return finish()
