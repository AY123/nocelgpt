from __future__ import annotations

from .types import PromptBinding, PromptVariable
from ..director.semantic_ledger import render_semantic_ledger


def bind_chapter_draft(package: dict, extra: dict | None = None) -> PromptBinding:
    extra = extra or {}
    context_lines = []
    for type_code, records in package["context"].items():
        for rec in records:
            name = rec.get("name", rec["id"])
            summary = (
                rec.get("summary")
                or rec.get("statement")
                or rec.get("notes")
                or ""
            )
            context_lines.append(f"- {rec['id']} ({type_code}): {name}\n  {summary}")

    binding = {
        "task_id": PromptVariable("task_id", package["task"]["task_id"], "package"),
        "goal": PromptVariable("goal", package["task"]["goal"], "package"),
        "context_lines": PromptVariable(
            "context_lines", "\n".join(context_lines), "package", package["content_hash"]),
        "derived_from": PromptVariable(
            "derived_from",
            "\n".join(package["provenance"]["derived_from"]),
            "package",
            package["content_hash"],
        ),
        "style": PromptVariable(
            "style",
            extra.get("style", "中文网文叙述风格，要求自然、稳定、克制，不切换到英文语域"),
            "runtime",
        ),
        "chapter_role": PromptVariable(
            "chapter_role", extra.get("chapter_role", "advance"), "runtime"
        ),
        "target_length_cjk": PromptVariable(
            "target_length_cjk", extra.get("target_length_cjk", 700), "runtime"
        ),
    }

    # story_state (roadmap P18/Prompt Orchestrator) is bound ONLY when supplied,
    # so a v1 render (no story_state) has an unchanged binding — its binding_hash
    # is byte-identical to before this variable existed. The v2 template requires
    # it; the serial chain feeds it a compact "story so far" recap.
    if extra.get("story_state") is not None:
        binding["story_state"] = PromptVariable(
            "story_state", extra["story_state"], "runtime")

    # scene_plan (Scene DSL layer) is bound ONLY when supplied, same discipline
    # as story_state: a v1/v2 render omits it, so those bindings stay
    # byte-identical to before this variable existed. The v3 template requires
    # it; the serial chain feeds it a compact rendered beat skeleton.
    if extra.get("scene_plan") is not None:
        binding["scene_plan"] = PromptVariable(
            "scene_plan", extra["scene_plan"], "runtime")

    # chapter_ir (Narrative IR, Phase 4.2) is bound ONLY when supplied, same
    # discipline: a v1/v2/v3 render omits it, so those bindings stay
    # byte-identical to before this variable existed. The v4 template requires
    # it; the serial chain feeds it the rendered Chapter IR (chapter intent +
    # payoff target + per-beat narrative operations).
    if extra.get("chapter_ir") is not None:
        binding["chapter_ir"] = PromptVariable(
            "chapter_ir", extra["chapter_ir"], "runtime")

    # reference_anchor (M5 reference abstraction) is bound when supplied so the
    # chapter prompt can carry reusable market / structural guidance without
    # copying specifics. v4+ templates may optionally consume it; if absent, the
    # older render stays byte-identical.
    if extra.get("reference_anchor") is not None:
        binding["reference_anchor"] = PromptVariable(
            "reference_anchor", extra["reference_anchor"], "runtime")

    # reference_abstraction is kept as an alias for callers that already pass the
    # full M5 artifact under that key.
    if extra.get("reference_abstraction") is not None and "reference_anchor" not in binding:
        binding["reference_anchor"] = PromptVariable(
            "reference_anchor", extra["reference_abstraction"], "runtime")

    # character_runtime (Character Runtime, Phase 4.3) is bound ONLY when
    # supplied, same discipline: a v1-v4 render omits it, so those bindings stay
    # byte-identical to before this variable existed. The v5 template requires
    # it; the serial chain feeds it the rendered per-lead runtime (goal /
    # pressure / next_likely_action) so each lead's behavior stays continuous.
    if extra.get("character_runtime") is not None:
        binding["character_runtime"] = PromptVariable(
            "character_runtime", extra["character_runtime"], "runtime")

    # chapter_objective + director_brief (Narrative Director, Phase 7.1) are bound
    # ONLY when supplied, same discipline: a v1-v5 render omits them, so those
    # bindings stay byte-identical to before these variables existed. The v6
    # template requires them; the serial chain feeds each chapter the rendered
    # director objective (top-level intent: story + retention + commercial pull)
    # and brief (must-include / must-avoid / non-negotiables) folded above the IR.
    if extra.get("chapter_objective") is not None:
        binding["chapter_objective"] = PromptVariable(
            "chapter_objective", extra["chapter_objective"], "runtime")
    if extra.get("director_brief") is not None:
        binding["director_brief"] = PromptVariable(
            "director_brief", extra["director_brief"], "runtime")

    # speech_profiles (Character Speech Profile, roadmap §15) is bound ONLY when
    # supplied, same discipline: a v1-v6 render omits it, so those bindings stay
    # byte-identical to before this variable existed. The v7 template requires it;
    # the serial chain feeds it the rendered language block for the profiled leads
    # that APPEAR in this chapter (register / vocabulary / sentence shape / verbal
    # habits / taboo / thinking pattern / emotion), so each character sounds
    # distinct. Absent profiles => not bound => v7 degrades to v6 behavior.
    if extra.get("speech_profiles") is not None:
        binding["speech_profiles"] = PromptVariable(
            "speech_profiles", extra["speech_profiles"], "runtime")

    # narrative_mandate (Narrative Intelligence, Phase 9.4) is bound ONLY when
    # supplied, same discipline: a v1-v7 render omits it, so those bindings stay
    # byte-identical to before this variable existed. The v8 template requires it;
    # the serial chain feeds each chapter the rendered mandate (why-now / cost of
    # delay / escalation ladder / inner shift / net advance) folded ABOVE the
    # director objective — the highest cross-chapter intent, directly attacking
    # 流水账. Absent mandate => not bound => v8 degrades to v7 behavior.
    if extra.get("narrative_mandate") is not None:
        binding["narrative_mandate"] = PromptVariable(
            "narrative_mandate", extra["narrative_mandate"], "runtime")

    # recent_openings (Cross-chapter opening-diversity, §14 anti-AI prevention)
    # is bound ONLY when supplied, same discipline: a v1-v8 render omits it, so
    # those bindings stay byte-identical to before this variable existed. The v9
    # template requires it; the serial chain feeds each chapter the rendered
    # openings of the last K PRIOR chapters (fold cursor — the current chapter
    # never leaks in) so the model varies this chapter's entrance away from them.
    # This is the prevention half of the detection→prevention loop whose detection
    # half is scene/serial_humanization.check_serial_openings. Absent => not bound
    # => v9 degrades to v8 behavior.
    if extra.get("recent_openings") is not None:
        binding["recent_openings"] = PromptVariable(
            "recent_openings", extra["recent_openings"], "runtime")

    # long_arc (Long-Arc Planner, roadmap M3) is bound ONLY when supplied, same
    # discipline: a v1-v9 render omits it, so those bindings stay byte-identical
    # to before this variable existed. The v10 template requires it; the serial
    # chain feeds each chapter its long-arc coordinate (volume / distance to the
    # volume climax / expected power tier / conflict pressure / paywall+milestone)
    # projected from the outline, so long-range rhythm holds. Absent => not bound
    # => v10 degrades to v9 behavior.
    if extra.get("long_arc") is not None:
        binding["long_arc"] = PromptVariable(
            "long_arc", extra["long_arc"], "runtime")

    # genre_contract (genre-drift prevention, QIDIAN_SUBGENRE_DEEP_DIVE §4.3) is
    # bound ONLY when supplied, same discipline: a v1-v13 render omits it, so those
    # bindings stay byte-identical to before this variable existed. The v14 template
    # requires it; the serial chain feeds each chapter the rendered genre contract
    # (the discriminant requirement the genre cannot lose + its degradation
    # symptoms + the book's own coined terms) so the prose keeps BEING its declared
    # genre instead of sliding toward generic 升级流 — a slide that is invisible
    # chapter-by-chapter because each chapter still reads fine locally. Prevention
    # half of the loop whose detection half is
    # scene/serial_genre_drift.check_serial_genre_drift. Absent => not bound =>
    # v14 degrades to v13 behavior.
    if extra.get("genre_contract") is not None:
        binding["genre_contract"] = PromptVariable(
            "genre_contract", extra["genre_contract"], "runtime")

    # chapter_contract (Contract Gate, Phase 3 v15) is bound ONLY when supplied,
    # same discipline: a v1-v14 render omits it, so those bindings stay
    # byte-identical to before this variable existed. The v15 template requires it;
    # the serial chain feeds each chapter the rendered contract (authored entry/exit
    # requirements + chapter intent + character obligations) loaded from the contracts
    # directory. This is the PLANNED contract that the chapter MUST honor. Absent =>
    # not bound => v15 degrades to v14 behavior.
    if extra.get("chapter_contract") is not None:
        binding["chapter_contract"] = PromptVariable(
            "chapter_contract", extra["chapter_contract"], "runtime")

    # actual_entry_state (P0-3: Actual Exit Reflow, Phase 3 v15) is bound ONLY when
    # supplied, same discipline: a v1-v14 render omits it, so those bindings stay
    # byte-identical to before this variable existed. The v15 template requires it;
    # the serial chain feeds each chapter N+1 the ACTUAL exit state from chapter N
    # (location / present_characters / active_hooks / emotional_state / plot_threads)
    # extracted from the FINAL text, not the planned exit from the contract. This
    # closes the state-driven feedback loop: planned → actual → next chapter uses
    # actual. Chapter 1 and chapters where the actual exit file is missing get an
    # empty string (graceful degradation). Absent => not bound => v15 degrades to v14.
    if extra.get("actual_entry_state") is not None:
        binding["actual_entry_state"] = PromptVariable(
            "actual_entry_state", extra["actual_entry_state"], "runtime")

    if extra.get("approved_state") is not None:
        binding["approved_state"] = PromptVariable(
            "approved_state", extra["approved_state"], "runtime")
    if extra.get("approved_state_constraints") is not None:
        binding["approved_state_constraints"] = PromptVariable(
            "approved_state_constraints",
            extra.get("approved_state_constraints") or [],
            "runtime",
        )

    # semantic_ledger (W12 Semantic Ledger) is bound ONLY when supplied, same
    # discipline as approved_state: a render without it stays byte-identical to
    # before this variable existed. The serial chain feeds the next chapter the
    # rendered six-category ledger (knowledge / ability / injury / items /
    # relationship_expectation / promise) so the model reads and honors
    # accumulated long-form state instead of improvising continuity.
    if extra.get("semantic_ledger") is not None:
        binding["semantic_ledger"] = PromptVariable(
            "semantic_ledger", extra["semantic_ledger"], "runtime")

    if extra.get("semantic_ledger_raw") is not None:
        binding["semantic_ledger_raw"] = PromptVariable(
            "semantic_ledger_raw",
            extra["semantic_ledger_raw"],
            "runtime",
        )
    elif extra.get("semantic_ledger") is not None and isinstance(extra.get("semantic_ledger"), dict):
        binding["semantic_ledger_raw"] = PromptVariable(
            "semantic_ledger_raw",
            extra["semantic_ledger"],
            "runtime",
        )

    # Routing notes are optional. When present, they let the rendered prompt carry
    # a model-specific constraint summary without changing older render paths.
    if extra.get("model_profile_note") is not None:
        binding["model_profile_note"] = PromptVariable(
            "model_profile_note", extra["model_profile_note"], "runtime")
    if extra.get("constraint_pack_note") is not None:
        binding["constraint_pack_note"] = PromptVariable(
            "constraint_pack_note", extra["constraint_pack_note"], "runtime")

    # Phase B preparation: reader_signal/platform_feedback let the prompt carry
    # small, explicit audience and channel notes without forcing older templates
    # to change. Absent values keep older renders byte-identical.
    if extra.get("reader_signal") is not None:
        binding["reader_signal"] = PromptVariable(
            "reader_signal", extra["reader_signal"], "runtime")
    if extra.get("platform_feedback") is not None:
        binding["platform_feedback"] = PromptVariable(
            "platform_feedback", extra["platform_feedback"], "runtime")

    # semantic_ledger arrives in EITHER shape: the structured six-category dict
    # (outline/ledgers.build_semantic_ledger().to_dict()) or an already-RENDERED
    # text block — director/consumption_checkpoint.py feeds the live serial chain
    # `semantic_ledger_text`, i.e. a str. Rendering a str would crash
    # (render_semantic_ledger expects a Mapping), so only a Mapping gets rendered
    # and a str passes through as the finished block. The sibling branch at
    # semantic_ledger_raw above already keys on the same isinstance check.
    _ledger = extra.get("semantic_ledger")
    binding["semantic_ledger_text"] = PromptVariable(
        "semantic_ledger_text",
        _ledger if isinstance(_ledger, str) else render_semantic_ledger(_ledger or {}),
        "runtime",
    )

    return PromptBinding(binding)
