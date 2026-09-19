from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .sources import load_reference_sources, load_genesis_preference
from .analyzer import analyze_project_sources, merge_reference_analysis
from .agents import (
    propose_candidates, review_candidate, synthesize_final_outline,
    _build_conflict_ladder, _build_first_30_chapters, _build_reward_loop,
)
from .qa import check_outline, review_outline, review_outline_with_model
from .import_plan import build_import_plan
from .writer import project_id, write_outline_run
from ..reference.abstract import build_reference_abstraction, load_reference_abstraction
from ..retrieval.genesis import build_narrative_evidence_pack
from .tournament import run_outline_tournament
from .ledgers import build_ci_m4_ledger, build_semantic_ledger
from ..serialize.multi_proposal_comparison import compare_multi_proposals
from ..serialize.promise_ledger import build_promise_ledger
from ..serialize.chapter_evidence import build_chapter_evidence_ledger


@dataclass(frozen=True)
class OutlineBootstrapResult:
    ok: bool
    stage: str
    message: str
    run_dir: str | None = None
    outline_json: str | None = None
    outline_markdown: str | None = None
    import_plan_json: str | None = None
    errors: list[str] | None = None


def run_outline_bootstrap(
    project_path: str | Path,
    *,
    run_id: str | None = None,
    model=None,
    judge_models: list[tuple[str, object]] | None = None,
    outline_qa_model=None,
    evidence_pack: dict | None = None,
) -> OutlineBootstrapResult:
    project = Path(project_path)
    source_result = load_reference_sources(project_path)
    if not source_result.ok:
        return OutlineBootstrapResult(
            ok=False,
            stage="sources",
            message="reference source validation failed",
            errors=source_result.errors,
        )

    analyses = analyze_project_sources(project, source_result.sources)
    merged = merge_reference_analysis(analyses)
    preference = load_genesis_preference(project)
    target_genre = (preference.get("target_genre") or "").strip()
    if target_genre:
        signals = [g for g in merged.get("genre_signals", []) if g != target_genre]
        merged["genre_signals"] = [target_genre] + signals
        merged["target_genre"] = target_genre
    reference_abstract = load_reference_abstraction(project)
    if reference_abstract is None:
        try:
            reference_abstract = build_reference_abstraction(project)
            from ..reference.abstract import write_reference_abstraction
            write_reference_abstraction(project, reference_abstract)
        except Exception:
            reference_abstract = None
    merged["reference_abstract"] = reference_abstract
    if isinstance(reference_abstract, dict):
        merged["reference_abstract_id"] = reference_abstract.get("id")
    if evidence_pack is not None:
        merged["narrative_evidence"] = {
            "id": evidence_pack.get("id"),
            "patterns": evidence_pack.get("patterns", []),
            "anti_patterns": evidence_pack.get("anti_patterns", []),
            "constraints": evidence_pack.get("constraints", []),
            "provenance": evidence_pack.get("provenance", {}),
        }
    if model is not None:
        from .llm_agents import LLMCandidateProposer, LLMCandidateReviewer
        candidates = LLMCandidateProposer(model).propose(merged)
    else:
        candidates = propose_candidates(merged)

    # Freeze one complete proposal snapshot before any judge runs.  Every judge
    # receives these exact bytes; adding a judge cannot trigger regeneration.
    # Some deterministic candidates predate authored cast/world fields, so derive
    # conservative proposal-only context for judging without changing selection.
    frozen_candidates = []
    reward_loop = _build_reward_loop(merged)
    for candidate in candidates:
        frozen = dict(candidate)
        engine = dict(frozen.get("protagonist_engine") or {})
        power = dict(frozen.get("power_system") or {})
        tiers = [str(item).split("——", 1)[0].strip() for item in power.get("tiers", [])]
        conflict_ladder = list(frozen.get("conflict_ladder") or _build_conflict_ladder(tiers))
        world = frozen.get("world")
        if not isinstance(world, dict):
            world = {
                "summary": f"围绕《{frozen.get('title', '')}》核心机制展开的原创世界。",
                "rules": [str(item) for item in power.get("hard_limits", [])],
            }
        characters = frozen.get("characters")
        if not isinstance(characters, list) or not characters:
            characters = [{
                "role": "protagonist",
                "name": "未命名主角",
                "arc": f"从{engine.get('flaw', '自身缺陷')}走向{engine.get('desire', '核心目标')}",
                "motivation": engine.get("desire", ""),
            }]
        frozen.update({
            "world": world,
            "characters": characters,
            "conflict_ladder": conflict_ladder,
            "first_30_chapters": list(
                frozen.get("first_30_chapters")
                or _build_first_30_chapters(engine, reward_loop, conflict_ladder)
            ),
        })
        frozen_candidates.append(frozen)
    candidates = frozen_candidates

    if model is not None:
        reviewer = LLMCandidateReviewer(model)
        reviews = [reviewer.review(candidate, merged) for candidate in candidates]
    else:
        reviews = [review_candidate(candidate, merged) for candidate in candidates]

    tournament = None
    if len(candidates) >= 2:
        effective_judges = judge_models
        if effective_judges is None and model is not None:
            provider = getattr(model, "primary_provider", getattr(model, "provider", "unknown"))
            effective_judges = [(f"{provider}:{getattr(model, 'model_id', 'unknown')}", model)]
        tournament_candidates = [
            {
                "id": candidate.get("id"),
                "proposal": {
                    key: candidate.get(key)
                    for key in (
                        "title", "genre", "logline", "protagonist_engine",
                        "power_system", "world", "characters",
                        "conflict_ladder", "first_30_chapters",
                    )
                },
            }
            for candidate in candidates
        ]
        tournament = run_outline_tournament(
            tournament_candidates,
            judge_models=effective_judges or [],
        )
        merged["tournament"] = tournament

    # Y365-03: deterministic multi-proposal comparison beside the tournament.
    # The tournament is a pairwise LLM judgement; this is the DETERMINISTIC
    # scoreboard over the same candidates, folded from the reviews that already
    # exist (critic score / risk level / structural completeness) so a human can
    # see WHY one proposal leads. Selection authority stays human (ADR-009) and
    # the winner never gates (ADR-003) — synthesize_final_outline below is
    # unchanged and still picks by its own rule.
    proposal_comparison = None
    if len(candidates) >= 2:
        review_by_id = {r.get("candidate_id"): r for r in reviews if isinstance(r, dict)}
        _RISK_FIT = {"low": 9.0, "medium": 7.0, "high": 4.0}
        proposals = []
        for c in candidates:
            review = review_by_id.get(c.get("id")) or {}
            risk = str(review.get("risk_level") or "unknown")
            score = review.get("score")
            engine = c.get("protagonist_engine") or {}
            power = c.get("power_system") or {}
            # opening_hook_strength: the critic's own score, the only hook
            # judgement already on record for a candidate.
            hook = float(score) if isinstance(score, (int, float)) else None
            # long_arc_clarity: structural completeness — a proposal that names a
            # desire, a cost, tiers and hard limits is a clearer long arc than one
            # that leaves them blank. Deterministic, no model.
            filled = sum(1 for v in (engine.get("desire"), engine.get("flaw"),
                                     engine.get("golden_finger"), engine.get("cost"),
                                     power.get("tiers"), power.get("hard_limits")) if v)
            proposals.append({
                "proposal_id": c.get("id"),
                "logline": c.get("logline") or c.get("title") or "",
                "originality_risk": risk,
                "market_fit": _RISK_FIT.get(risk),
                "opening_hook_strength": hook,
                "long_arc_clarity": round(filled / 6 * 10, 2),
            })
        proposal_comparison = compare_multi_proposals(
            project_id=project_id(project), proposals=proposals).to_dict()
        merged["proposal_comparison"] = proposal_comparison

    from ..market.writer import load_market_snapshot
    market_snapshot = load_market_snapshot(project)
    outline = synthesize_final_outline(
        candidates,
        reviews,
        merged,
        project_id(project),
        [source.__dict__ for source in source_result.sources],
        market_snapshot,
    )
    ci_m4_ledger = build_ci_m4_ledger(outline).to_dict()
    semantic_ledger = build_semantic_ledger(outline).to_dict()
    merged["ci_m4_ledger"] = ci_m4_ledger
    merged["semantic_ledger"] = semantic_ledger
    merged["first_30_goal_variation_check"] = {
        "unique_goal_count": len({c.get('goal') for c in outline.get('first_30_chapters', [])}),
        "chapter_count": len(outline.get('first_30_chapters', [])),
    }
    promise_ledger = build_promise_ledger(outline.get("first_30_chapters", [])).to_dict()
    merged["promise_ledger"] = promise_ledger

    # P0 整改：题材契约门禁验证
    from ..genre_contract import validate_outline_genre, GenreContractViolationError
    genre_contract_result = validate_outline_genre(outline)
    if not genre_contract_result.ok:
        return OutlineBootstrapResult(
            ok=False,
            stage="genre-contract",
            message="outline 违反题材契约",
            errors=[
                f"{v.violation_type}: {v.keyword} (context: {v.context[:50]}...)"
                for v in genre_contract_result.violations[:5]
            ] + ([f"...共 {len(genre_contract_result.violations)} 处违规"]
                 if len(genre_contract_result.violations) > 5 else []),
        )

    qa_findings = check_outline(outline)
    if qa_findings:
        return OutlineBootstrapResult(
            ok=False,
            stage="outline-qa",
            message="outline failed deterministic QA gate",
            errors=[str(f) for f in qa_findings],
        )

    # Keep deterministic heuristics and the LM opinion as explicit siblings.
    # The model report is always advisory; provider/parse failure is archived as
    # degraded provenance and cannot turn into a workflow gate (ADR-003).
    outline_review = review_outline(outline).to_dict()
    model_review = None
    if outline_qa_model is not None:
        model_review = review_outline_with_model(outline, outline_qa_model).to_dict()
    outline_review.update({
        "kind": "outline_review",
        "model_review": model_review,
        "model_integration": {
            "status": (
                "not_requested" if model_review is None
                else "integrated" if model_review["status"] == "completed"
                else "degraded"
            ),
            "gating": False,
        },
    })
    if tournament is not None and model_review is not None:
        tournament["outline_qa"] = {
            "status": (
                "model_integrated"
                if model_review["status"] == "completed"
                else "model_degraded"
            ),
            "reviewer": model_review["reviewer"],
            "gating": False,
            "outline_hash": model_review["provenance"]["outline_hash"],
            "request_hash": model_review["provenance"]["request_hash"],
            "error": model_review["provenance"]["error"],
        }

    import_plan = build_import_plan(outline)
    chapter_evidence_ledger = build_chapter_evidence_ledger(
        run_manifest={
            "id": f"OUTLINE-{project_id(project)}",
            "kind": "outline_bootstrap",
            "version": "1.0",
            "gating": False,
            "chapters": [
                {
                    "index": item.get("chapter_no"),
                    "task_id": f"CH-{item.get('chapter_no')}",
                    "event": f"EVENT-{item.get('chapter_no')}",
                    "ok": True,
                    "stage": "outline",
                    "message": "derived from outline first_30_chapters",
                    "draft_hash": None,
                    "state_hash": None,
                    "verdict": None,
                    "commercial_verdict": None,
                    "events_so_far": [],
                    "open_setups": [],
                    "chapter_final": {
                        "final_text": item.get("goal") or item.get("end_hook") or "",
                        "final_review": {"scores": {}, "overall_verdict": None},
                        "comparison_report": {"winner": None},
                    },
                }
                for item in outline.get("first_30_chapters", [])
            ],
            "totals": {
                "planned": len(outline.get("first_30_chapters", [])),
                "produced": len(outline.get("first_30_chapters", [])),
                "skipped": 0,
                "live_calls": 0,
                "final_state_hash": None,
                "token_usage": {"input": 0, "output": 0, "total": 0},
                "cost": None,
            },
        },
        project_path=project,
        protocol_id="N100-043",
        protocol_config_hash=str(merged.get("promise_ledger", {}).get("metadata", {}).get("chapter_count", "")),
        notes="outline-derived chapter evidence",
    )
    merged["chapter_evidence_ledger"] = chapter_evidence_ledger
    run_dir, json_path, md_path, import_plan_path = write_outline_run(
        project,
        sources=source_result.sources,
        analysis=[analysis.to_dict() for analysis in analyses],
        merged_analysis=merged,
        candidates=candidates,
        reviews=reviews,
        final_outline=outline,
        import_plan=import_plan,
        outline_review=outline_review,
        evidence_pack=evidence_pack,
        tournament=tournament,
        ci_m4_ledger=ci_m4_ledger,
        promise_ledger=promise_ledger,
        semantic_ledger=semantic_ledger,
        chapter_evidence_ledger=chapter_evidence_ledger,
        proposal_comparison=proposal_comparison,
        run_id=run_id,
    )
    return OutlineBootstrapResult(
        ok=True,
        stage="done",
        message="outline bootstrap v0.2 produced",
        run_dir=str(run_dir.relative_to(project)),
        outline_json=str(json_path.relative_to(project)),
        outline_markdown=str(md_path.relative_to(project)),
        import_plan_json=str(import_plan_path.relative_to(project)),
        errors=[],
    )


def run_mock_outline_bootstrap(project_path: str | Path) -> OutlineBootstrapResult:
    """Backward-compatible alias for callers from the v0.1 spike."""
    return run_outline_bootstrap(project_path)
