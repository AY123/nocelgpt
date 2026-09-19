"""refine.py — the end-to-end production command (ANES v2).

One command runs the whole quality loop the North Star describes:

    generate --> review (single judge OR multi-model panel)
             --> revise (targeted rewrite, verify improvement)
             --> re-gate the FINAL draft deterministically
             --> write the best draft as a derived artifact, with the review +
                 revision session riding the Runtime envelope.

It is a THIN orchestrator: stage 1 reuses execute_package (generate + gate +
initial review + write), stage 2 reuses revise_until (the optimization loop),
and the deterministic gates still run on whichever draft is finally selected.
Nothing here can gate a build on an evaluative signal (ADR-003) — the loop only
selects a BETTER artifact; the deterministic draft QA is what may block.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .. import derived
from .agent import serialize
from .draft_qa import check_draft, DraftFinding
from .envelope import ENVELOPE_FORMAT
from .quality_center import SCORE_DIMENSIONS
from .revision import revise_until
from .run import execute_package, DERIVED_CATEGORY


@dataclass
class RefineResult:
    ok: bool
    stage: str
    message: str = ""
    initial_hash: Optional[str] = None
    final_hash: Optional[str] = None
    verdict: Optional[str] = None
    terminate_reason: Optional[str] = None
    rounds: int = 0
    scores_before: dict = field(default_factory=dict)
    scores_after: dict = field(default_factory=dict)
    artifact_path: Optional[str] = None
    qa_findings: Optional[List[DraftFinding]] = None
    session: Optional[dict] = None


def refine_package(
    *,
    package: dict,
    standard_root,
    project_path,
    gen_model=None,
    reviewer,
    rewrite_model,
    min_words: int = 1,
    max_rounds: int = 3,
    threshold: int = 80,
    prompt_runtime=None,
    prompt_id: str = "chapter-draft",
    prompt_version: str = "1.0.0",
) -> RefineResult:
    """Generate -> review -> revise -> re-gate -> write. `reviewer` is any
    DraftReviewer (a single LLMQualityJudge or a ReviewPanel — interchangeable).
    """
    # Stage 1 — generate + deterministic gate + initial review (reuses the whole
    # execute loop, including writing the first draft into the Project).
    gen = execute_package(
        package=package,
        standard_root=standard_root,
        project_path=project_path,
        model=gen_model,
        min_words=min_words,
        prompt_runtime=prompt_runtime,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        reviewer=reviewer,
    )
    if not gen.ok:
        return RefineResult(ok=False, stage=gen.stage, message=gen.message,
                            qa_findings=gen.qa_findings)

    initial_artifact = gen.artifact
    initial_report = gen.qa_review or {}

    # The M9 reference anchor (if pinned) rides the revision loop as a per-round
    # advisory gap reading — recorded, never part of accept/reject (ADR-003).
    from ..reference import load_reference_profile
    reference_profile = load_reference_profile(project_path)

    # Stage 2 — optimization loop. Advisory; returns the BEST draft seen.
    result = revise_until(
        reviewer, rewrite_model, initial_artifact, package,
        max_rounds=max_rounds, threshold=threshold,
        initial_report=initial_report if initial_report.get("scores") else None,
        reference_profile=reference_profile,
    )
    final_artifact = result.final_artifact
    final_report = result.final_report
    session = result.session.to_dict()

    # Stage 3 — the FINAL selected draft must still pass the deterministic gate
    # (ADR-003). Refinement never bypasses the gate.
    findings = check_draft(final_artifact, min_words=min_words)
    if findings:
        return RefineResult(
            ok=False, stage="final-draft-qa",
            message=f"refined draft failed deterministic QA ({len(findings)} issue(s))",
            initial_hash=initial_artifact.get("content_hash"),
            final_hash=final_artifact.get("content_hash"),
            qa_findings=findings, session=session)

    # Stage 4 — write the final draft as a derived artifact, with the consensus
    # review + revision session riding the envelope (never inside the frozen
    # ChapterDraft schema). If the loop changed nothing, this re-affirms stage 1's
    # draft with the session attached.
    from .envelope import wrap
    envelope = wrap(final_artifact, None,
                    qa_review=final_report, revision_session=session)
    rel = derived.write_artifact(
        project_path=project_path, category=DERIVED_CATEGORY,
        artifact_id=final_artifact["task_id"], artifact=final_artifact,
        serialized=serialize(envelope))

    return RefineResult(
        ok=True, stage="done",
        message=f"refined draft produced ({final_artifact.get('word_count')} words)",
        initial_hash=initial_artifact.get("content_hash"),
        final_hash=final_artifact.get("content_hash"),
        verdict=result.session.verdict,
        terminate_reason=result.session.terminate_reason,
        rounds=len(result.session.rounds),
        scores_before=initial_report.get("scores", {}),
        scores_after=final_report.get("scores", {}),
        artifact_path=rel,
        session=session)
