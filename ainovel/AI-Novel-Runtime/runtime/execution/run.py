"""run.py — execute a Task Package into a ChapterDraft (ANES v2, Phase 3).

Control-flow for the execution loop (distinct from the build pipeline, ADR-005):

    Task Package -> render prompt -> Model -> ChapterDraft
                 -> deterministic draft QA gate
                 -> validate against the capability's declared output contract
                 -> write derived artifact (+ provenance) into the Project

The output is a DERIVED artifact (ADR-006). It is written under the Project's
registry/derived/ tree (anchored + indexed), NOT registry/facts/. Prose is not a
fact; extracting facts from prose would be a separate, future capability.

The output Artifact Contract is loaded FROM the capability contract
(`output.schema`), never a constant in this file — so a new capability cannot
drift from its declared output shape.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .. import contracts, derived, registry_loader
from .agent import ChapterDraftAgent, serialize
from .draft_qa import check_draft, DraftFinding
from .draft_review import DraftReviewer, unanchored_entity_reviewer
from .envelope import wrap
from .model import DeterministicModel, Model
from .redline import check_redlines, has_hard_hit, hits_to_dicts, RedlineRule
from .publish_readiness import assess_publish_readiness
from .m7 import assess_m7

DERIVED_CATEGORY = "drafts"
PROMPT_MANIFEST_CATEGORY = "prompt-manifests"


def _review_with_grounding(reviewer, artifact: dict, package: dict, grounding):
    """Call reviewer.review, passing `grounding` (Phase 4.2 Chapter IR
    payoff_target) ONLY when the reviewer's signature accepts it. The DraftReviewer
    seam is public; a reviewer written before 4.2 takes only (artifact, package),
    so probing keeps it working unchanged. When there is no grounding at all, the
    call is byte-identical to the pre-4.2 two-arg form."""
    import inspect
    if grounding is not None:
        try:
            params = inspect.signature(reviewer.review).parameters
            if "grounding" in params or any(
                    p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
                return reviewer.review(artifact, package, grounding=grounding)
        except (TypeError, ValueError):
            pass
    return reviewer.review(artifact, package)


def _director_audit(package: dict, artifact: dict, qa_review: dict | None,
                    publish_readiness: dict | None,
                    director_objective: dict | None = None,
                    director_brief: dict | None = None,
                    prompt_version: str | None = None) -> dict:
    """Build a schema-backed DirectorSession (Phase 7.2) for this chapter.

    It references the REAL director artifacts when they were produced (the v6
    serial loop folds a ChapterObjective + DirectorBrief and passes them here);
    when they are absent (the single-chapter `execute` path, or a v1-v5 run) the
    session degrades gracefully — objective_id/brief_id are null and the rationale
    notes the draft came straight from the task package. This replaces the ad-hoc
    dict Phase 6 stuffed with non-director values (task_id posing as an OBJ id,
    content_hash posing as a brief id). Rides the envelope, never the sealed draft."""
    from ..director import build_director_session
    task = package.get("task", {})
    chapter_id = task.get("task_id") or artifact.get("task_id") or ""
    draft_hash = artifact.get("content_hash")
    rationale = []
    if director_objective:
        rationale.append("draft generated from the chapter objective and director brief")
    else:
        rationale.append("draft generated from current task package (no director objective)")
    if qa_review:
        rationale.append("quality review attached to the envelope")
    if publish_readiness:
        rationale.append(f"publish readiness: {publish_readiness.get('recommendation', 'n/a')}")
    return build_director_session(
        chapter_id=chapter_id,
        objective=director_objective, brief=director_brief,
        selected_draft_hash=draft_hash,
        prompt_version=prompt_version,
        rationale=rationale)


@dataclass
class ExecutionResult:
    ok: bool
    stage: str
    artifact: Optional[dict] = None
    artifact_path: Optional[str] = None
    qa_findings: Optional[List[DraftFinding]] = None
    contract_errors: Optional[List[str]] = None
    qa_review: Optional[dict] = None
    redline_hits: Optional[List[dict]] = None
    publish_readiness: Optional[dict] = None
    m7: Optional[dict] = None
    director: Optional[dict] = None
    # The Runtime envelope built around the inner draft (draft + manifest +
    # qa_review/publish_readiness/director/m7 siblings). Populated even when
    # write=False so a caller that deferred the write (C6 multi-version) can
    # persist the SELECTED candidate byte-identically without re-generating it.
    envelope: Optional[dict] = None
    message: str = ""


def execute_package(
    *,
    package: dict,
    standard_root: str | Path,
    project_path: str | Path,
    model: Optional[Model] = None,
    min_words: int = 1,
    prompt_runtime=None,
    prompt_id: str = "chapter-draft",
    prompt_version: str = "1.0.0",
    reviewer: Optional[DraftReviewer] = None,
    extra_prompt_variables: Optional[dict] = None,
    redline_ruleset: Optional[List[RedlineRule]] = None,
    assess_publish: bool = True,
    originality_references: Optional[List[dict]] = None,
    review_grounding: Optional[dict] = None,
    director_objective: Optional[dict] = None,
    director_brief: Optional[dict] = None,
    consumption_evidence: Optional[dict] = None,
    recomputed_state: Optional[dict] = None,
    target_wordcount: Optional[int] = None,
    scene_beats: Optional[int] = None,
    chapter_no: Optional[int] = None,
    write: bool = True,
) -> ExecutionResult:
    contract_set = contracts.ContractSet(standard_root)
    capability_name = package["task"]["capability"]

    # The capability must be known and must declare its output contract.
    if not contract_set.has_capability(capability_name):
        return ExecutionResult(ok=False, stage="capability",
                               message=f"unknown capability {capability_name!r}")
    cap = contract_set.capability(capability_name)
    if not cap.output_schema:
        return ExecutionResult(ok=False, stage="capability",
                               message=f"{capability_name} declares no output.schema")

    agent = ChapterDraftAgent(
        model=model or DeterministicModel(),
        prompt_runtime=prompt_runtime,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
    )

    # Novel Brain (roadmap P15): the authored constitution feeds the prompt's
    # style directive. ABSENT Brain => no override => byte-identical draft (the
    # deterministic loop is unchanged for projects without a Brain). It is an
    # authored input, only READ here; nothing is written to facts (ADR-006).
    from ..brain import load_brain, brain_style_directive
    brain = load_brain(project_path)
    prompt_variables = dict(extra_prompt_variables or {})
    task = package.get("task", {})
    prompt_variables.setdefault("chapter_role", task.get("chapter_role", "advance"))
    prompt_variables.setdefault("target_length_cjk", task.get("target_length_cjk", target_wordcount or 700))
    if task.get("recent_openings") is not None:
        prompt_variables.setdefault("recent_openings", task.get("recent_openings"))
    if task.get("reader_signal") is not None:
        prompt_variables.setdefault("reader_signal", task.get("reader_signal"))
    if task.get("platform_feedback") is not None:
        prompt_variables.setdefault("platform_feedback", task.get("platform_feedback"))
    if brain:
        prompt_variables.setdefault("style", brain_style_directive(brain))
    if director_objective:
        from ..director import render_chapter_objective
        prompt_variables.setdefault("chapter_objective", render_chapter_objective(director_objective))
    if consumption_evidence and consumption_evidence.get("mint_ids"):
        # Inject the fact SEMANTICS (name/field/value), not just id+hash — the
        # model must know WHAT the approved fact is to reflect it in prose
        # (CI-M2-04: id-only injection left the fact unconsumable). The hashes stay
        # for audit/replay; approved_facts is what the drafter actually reads.
        from ..director.consumption import approved_state_constraints
        concrete_constraints = approved_state_constraints(
            consumption_evidence, recomputed_state)
        prompt_variables.setdefault("approved_state", json.dumps({
            "consumption_hash": consumption_evidence.get("consumption_hash"),
            "mint_ids": consumption_evidence.get("mint_ids"),
            "approved_facts": consumption_evidence.get("approved_facts") or [],
            "state_hash": (recomputed_state or {}).get("state_hash"),
            "constraints": concrete_constraints,
        }, ensure_ascii=False, sort_keys=True))
        prompt_variables.setdefault(
            "approved_state_constraints", concrete_constraints)
    # Length directive (A.3): the outline's target_wordcount finally reaches the
    # model. Appended to the style variable (no new prompt version — works on
    # every prompt version, keeps frozen templates untouched). ABSENT target =>
    # nothing appended; combined with an absent Brain the style var is never set,
    # so a project with neither renders a byte-identical draft.
    # P0-3: the old directive said "约 N 字（可上下浮动）" — no upper bound, and one
    # whole-chapter number while the model writes beat by beat. Measured result was
    # 1.56-1.65x the market p75. length_directive adds an explicit ceiling and, when
    # the scene plan is known, a PER-BEAT budget (the measurement showed overshoot is
    # per-beat verbosity, not beat count). Still appended to `style`, so no prompt
    # version changes and frozen templates stay untouched; absent target => "" =>
    # byte-identical draft.
    if target_wordcount:
        from ..chapter_length import length_directive
        directive = length_directive(
            target_wordcount,
            role=prompt_variables.get("chapter_role"),
            beats=scene_beats)
        base = prompt_variables.get("style")
        prompt_variables["style"] = f"{base}\n{directive}" if base else directive

    # 黄金三章 contract (规范 §7): chapters 1-3 have FIXED commercial jobs — hold the
    # reader, prove the mechanism works, show what the payoff will be — and until now
    # generation treated them exactly like chapter 17. Appended to `style` on the same
    # seam as the length directive above (no new prompt version, frozen templates
    # untouched). chapter_no outside 1-3 => "" => nothing appended => byte-identical
    # draft for the whole long-serial path. Shapes generation only; gates nothing
    # (ADR-003), and states what the chapter must ACCOMPLISH, never what is true, so
    # it cannot contradict a fact or the Brain.
    if chapter_no is not None:
        from ..golden_three_contract import golden_three_directive
        g3 = golden_three_directive(chapter_no)
        if g3:
            base = prompt_variables.get("style")
            prompt_variables["style"] = f"{base}\n{g3}" if base else g3
    # Pass None (not an empty dict) when nothing to override, so a project with
    # no Brain and no extras renders a byte-identical v1 draft.
    prompt_variables = prompt_variables or None

    # Stage 1 — generate (resource path: model)
    artifact = agent.run(package, variables=prompt_variables)

    # Stage 2 — deterministic draft QA gate (ADR-003). Blocks on failure.
    findings = check_draft(artifact, min_words=min_words)
    if findings:
        return ExecutionResult(ok=False, stage="draft-qa", artifact=artifact,
                               qa_findings=findings,
                               message=f"draft QA failed ({len(findings)} issue(s))")

    # Stage 2.1 — deterministic content red-line gate (ADR-003, Phase 4.1). This
    # is the OBJECTIVE half of the safety split: a HARD hit (platform ban-line) is
    # reproducible, so it legitimately gates the build. The SUBJECTIVE edginess
    # judgment lives on the evaluative axis (quality-report scores.safety_risk) and
    # never gates. Soft hits are advisory only and do not block here.
    redline_hits = check_redlines(artifact, ruleset=redline_ruleset)
    if has_hard_hit(redline_hits):
        return ExecutionResult(ok=False, stage="redline", artifact=artifact,
                               redline_hits=hits_to_dicts(redline_hits),
                               message="draft hit a HARD content red-line (build blocked)")

    # Stage 2.5 — EVALUATIVE QA hook (ADR-003). Advisory only: voice/pacing/
    # fact-fidelity judgments are reported, attached to the envelope, and NEVER
    # gate the loop. The placeholder reviewer is the seam a future LLM judge
    # plugs into (ROADMAP: no consumer = stub).
    # `review_grounding` (Phase 4.2) is the Chapter IR's payoff_target, passed to
    # the reviewer so a quality judge scores promise_delivery against the STATED
    # promise. The DraftReviewer seam is public (ADR-003) and pre-4.2 reviewers
    # take only (artifact, package); we pass grounding ONLY to reviewers whose
    # signature accepts it, so an older reviewer keeps working unchanged.
    review = _review_with_grounding(
        reviewer or unanchored_entity_reviewer(), artifact, package, review_grounding)
    qa_review = review.to_dict()

    # Stage 2.6 — publish readiness ('Build Gate ≠ Publish Readiness', Phase 4.1).
    # A human-authority (ADR-009) production decision derived from the deterministic
    # red-line result (soft hits only survive to here — a hard hit already gated
    # above) and the evaluative quality report. gates_build=false: it NEVER blocks
    # the build; it advises whether to PUBLISH. Rides the envelope like qa_review.
    # M7 (originality + red-line gate) is the UPSTREAM source of truth for the
    # publish decision. Until now this path only fed red-line hits + the quality
    # report into publish readiness, so the originality similarity signal never
    # reached it — the M7 gate was built (execution/m7.py) but never LIVE on the
    # production path (only publishing/card.py back-filled it downstream). We fold
    # it here so a hard red-line OR L3 originality risk forces 'block' at source.
    # Originality is opt-in: with no reference corpus we skip the (O(n·m)) window
    # match, assess_m7 sees no references => risk L0, and publish readiness is
    # byte-identical to before this wiring. The red-line half already ran above.
    m7_result = None
    m7_dict = None
    if assess_publish and originality_references:
        m7_result = assess_m7(
            artifact, chapter_id=artifact.get("task_id", ""),
            references=originality_references, redline_ruleset=redline_ruleset)
        m7_dict = m7_result.to_dict()

    publish_readiness = None
    if assess_publish:
        publish_readiness = assess_publish_readiness(
            chapter_id=artifact.get("task_id", ""),
            redline_hits=redline_hits,
            m7_result=m7_result,
            quality_report=qa_review,
            draft_content_hash=artifact.get("content_hash"),
        ).to_dict()
        # The M7 verdict is already FOLDED into the recommendation above. The raw
        # M7Result (similarity matches, red-line hits) rides the ENVELOPE as its
        # own sibling `m7` — NOT nested inside publish_readiness, whose frozen
        # schema is additionalProperties:false (nesting it there would write a
        # schema-invalid readiness block, breaking test_execution's conformance
        # check and ADR-007 Schema-First). Downstream read-side consumers read the
        # envelope's `m7` sibling. See envelope.wrap().

    # Stage 3 — output Artifact Contract (ADR-002), loaded from the capability
    # contract's declared output.schema (not a hardcoded constant).
    contract_errs = contract_set.validate_artifact(artifact, cap.output_schema)
    if contract_errs:
        print(f"!!! CONTRACT ERRORS !!!")
        for err in contract_errs[:10]:
            print(f"  - {err}")
        return ExecutionResult(ok=False, stage="artifact-contract",
                               artifact=artifact, contract_errors=contract_errs,
                               message="draft failed output artifact contract")

    # Stage 4 — staleness guard (ADR-006): the package's sources must not be
    # behind the Project's current Registry, or the draft is born stale.
    reg = registry_loader.load(project_path)
    stale = derived.check_staleness(reg, artifact["provenance"]["derived_from"])
    if stale:
        return ExecutionResult(ok=False, stage="staleness", artifact=artifact,
                               contract_errors=stale,
                               message="sources are stale; rebuild the package")

    prompt_manifest = getattr(agent, "last_prompt_manifest", None)
    if prompt_manifest is not None:
        from ..prompt.types import prompt_manifest_artifact
        pm_artifact = prompt_manifest_artifact(prompt_manifest)
        derived.write_artifact(
            project_path=project_path,
            category=PROMPT_MANIFEST_CATEGORY,
            artifact_id=pm_artifact["id"],
            artifact=pm_artifact,
            serialized=serialize(pm_artifact))

    # Stage 5 — write as a DERIVED artifact, anchored under the Project and
    # registered in the provenance index (ADR-006). Never into facts/.
    #
    # On disk the inner draft is wrapped in a Runtime envelope that also carries
    # the PromptManifest projection (the frozen Standard schema has no slot for
    # it). The envelope's inner `draft` is byte-identical to `artifact`, so the
    # draft's content_hash — and Stage-3 contract validity — are unaffected. The
    # provenance index keys on the inner draft's content_hash.
    # The director audit rides the ENVELOPE as a sibling of the draft — it is
    # advisory provenance and must never be injected into the inner ChapterDraft,
    # whose frozen schema is additionalProperties:false. (Injecting it would leave
    # a schema-invalid draft on disk; the content_hash is already sealed above.)
    director = _director_audit(package, artifact, qa_review, publish_readiness,
                               director_objective=director_objective,
                               director_brief=director_brief,
                               prompt_version=prompt_version)

    envelope = wrap(artifact, prompt_manifest, qa_review=qa_review,
                    publish_readiness=publish_readiness, director=director,
                    m7=m7_dict)
    # write=False (C6 multi-version): generate + score a candidate WITHOUT
    # persisting it. Only the selected winner is written back by the caller, so
    # losing candidates never clobber the draft artifact / derived index. The
    # envelope is still built so qa_review/publish_readiness ride the result.
    rel = None
    if write:
        rel = derived.write_artifact(
            project_path=project_path, category=DERIVED_CATEGORY,
            artifact_id=artifact["task_id"], artifact=artifact,
            serialized=serialize(envelope))

    return ExecutionResult(ok=True, stage="done", artifact=artifact,
                           artifact_path=rel, qa_review=qa_review,
                           redline_hits=hits_to_dicts(redline_hits),
                           publish_readiness=publish_readiness,
                           m7=m7_dict,
                           director=director,
                           envelope=envelope,
                           message=f"draft produced ({artifact['word_count']} words)")
