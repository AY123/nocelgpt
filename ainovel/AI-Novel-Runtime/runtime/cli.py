"""cli.py — command-line entry to the runtime spine (ANES v2).

Usage:
    python -m runtime.cli build \
        --project <project-dir> \
        --schema-dir <standard>/phase-1/generated/json-schema \
        --task TASK-00018 --goal "draft chapter 18" \
        --capability ChapterDraft --seed CHR-00001 --seed EVT-00002 \
        --out build/ [--max-depth 2]

    python -m runtime.cli validate --project <dir> --schema-dir <dir>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import compiler, derived, registry_loader, validator
from .pipeline import build_task_package
from .execution.run import execute_package
from .mint import execute_mint
from . import recompute
from .outline.sources import load_reference_sources, render_source_report
from .outline.workflow import run_outline_bootstrap
from .director import (build_chapter_objective, build_director_brief,
                       build_rewrite_decision, build_director_critique,
                       build_version_comparison, build_version_selection,
                       validate_chapter_objective, validate_director_brief)


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1]
    return key, value


def _candidate_env_files(args) -> list[Path]:
    candidates = []
    explicit = getattr(args, "env_file", None)
    if explicit:
        candidates.append(Path(explicit))
    cwd = Path.cwd()
    candidates.extend([cwd / ".env", cwd.parent / ".env"])
    for attr in ("project", "package", "standard_root"):
        value = getattr(args, attr, None)
        if value:
            p = Path(value)
            base = p if p.is_dir() else p.parent
            candidates.extend([base / ".env", base.parent / ".env"])
    seen = set()
    unique = []
    for p in candidates:
        resolved = p.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def _load_dotenv(args) -> None:
    for env_path in _candidate_env_files(args):
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_dotenv_line(line)
            if parsed is None:
                continue
            key, value = parsed
            os.environ.setdefault(key, value)
        break
    _apply_model_defaults(args)


def _apply_model_defaults(args) -> None:
    """Use the repository's configured model when no CLI model was supplied."""
    if not hasattr(args, "model_id"):
        return
    # CODE92_MODEL belongs to the 92code relay. The other providers also use
    # deepseek-v4-pro as their CLI default, and an explicit DeepSeek selection
    # must never be replaced by a relay-specific environment setting.
    if getattr(args, "model_provider", None) != "92code":
        return
    current = getattr(args, "model_id", None)
    if current not in (None, "", "deepseek-v4-pro"):
        return
    default_model = os.environ.get("CODE92_MODEL")
    if default_model:
        args.model_id = default_model


def _cmd_validate(args) -> int:
    reg = registry_loader.load(args.project)
    report = validator.validate(reg, args.schema_dir, args.standard_version)
    for f in report.findings:
        print(f)
    print(report.summary())
    return 0 if report.ok else 1


def _cmd_build(args) -> int:
    task = compiler.TaskDefinition(
        task_id=args.task,
        goal=args.goal,
        capability=args.capability,
        seeds=args.seed,
    )
    result = build_task_package(
        project_path=args.project,
        schema_dir=args.schema_dir,
        task=task,
        out_dir=args.out,
        standard_version=args.standard_version,
        max_depth=args.max_depth,
        token_budget=args.token_budget,
    )
    print(f"stage={result.stage}: {result.message}")
    for f in result.validation.findings:
        print(f"  {f}")
    if result.ok:
        print(f"package : {result.package_path}")
        print(f"hash    : {result.package['content_hash']}")
        print(f"manifest: {result.manifest_path}")
    return 0 if result.ok else 1


def _cmd_prompt_replay(args) -> int:
    from .prompt.tools import manifest_view
    view = manifest_view(args.manifest)
    print(f"prompt   : {view['prompt_id']}@{view['version']}")
    print(f"rendered : {view['rendered_hash']}")
    print(f"template : {view['template_hash']}")
    print(f"binding  : {view['binding_hash']}")
    print(f"package  : {view['package_hash']}")
    print(f"sources  : {', '.join(view['derived_from'])}")
    if args.show_messages:
        for msg in view["messages"]:
            print(f"\n[{msg['role']}]\n{msg['content']}")
    return 0


def _cmd_prompt_diff(args) -> int:
    from .prompt.tools import diff_records
    for line in diff_records(args.left, args.right):
        print(line)
    return 0


def _cmd_prompt_audit(args) -> int:
    from .prompt.tools import audit_project
    for line in audit_project(args.project):
        print(line)
    return 0


def _cmd_execute(args) -> int:
    _load_dotenv(args)
    package = json.loads(Path(args.package).read_text(encoding="utf-8"))
    prompt_runtime = None
    if args.prompt_cache_dir or args.prompt_mode != "frozen":
        from .prompt.runtime import PromptRuntime
        prompt_root = (Path(args.prompt_root) if args.prompt_root
                       else Path(args.standard_root) / "contracts" / "prompts")
        prompt_runtime = PromptRuntime(
            prompt_root=prompt_root,
            cache_root=args.prompt_cache_dir,
            manifest_schema=Path(args.standard_root) / "contracts" / "prompt-manifest.schema.json",
            mode=args.prompt_mode,
        )
    model = None
    if args.model_provider == "paste" or args.paste_file:
        if not args.paste_file:
            raise SystemExit("--model-provider paste requires --paste-file")
        from .execution.paste_model import PastedTextModel
        model = PastedTextModel(paste_file=args.paste_file, model_id=args.model_id)
    elif args.model_provider not in ("deterministic", "paste"):
        from .execution.llm_model import LLMExecutionModel
        model = LLMExecutionModel(
            provider=args.model_provider,
            model_id=args.model_id,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            system_prompt=args.system_prompt,
            timeout_seconds=args.timeout,
            replay_dir=args.replay_dir,
            stream=args.stream,
        )
    # Evaluative reviewer selection (ADR-003: advisory, never gates). The judge
    # or panel reuses the model seam behind the DraftReviewer protocol without
    # touching the execution control flow.
    reviewer = _make_reviewer(args, model)

    result = execute_package(
        package=package,
        standard_root=args.standard_root,
        project_path=args.project,
        model=model,
        min_words=args.min_words,
        prompt_runtime=prompt_runtime,
        prompt_id=args.prompt_id,
        prompt_version=args.prompt_version,
        reviewer=reviewer,
    )
    print(f"stage={result.stage}: {result.message}")
    for f in (result.qa_findings or []):
        print(f"  {f}")
    for e in (result.contract_errors or []):
        print(f"  [error] {result.stage}: {e}")
    if result.ok:
        print(f"draft   : {result.artifact_path}")
        print(f"hash    : {result.artifact['content_hash']}")
        print(f"model   : {result.artifact['produced_by']['model_id']}")
        review = result.qa_review or {}
        if review.get("scores"):
            scores = review["scores"]
            print(f"quality : {review.get('reviewer', '?')} "
                  f"(evaluative, gating={review.get('gating')})")
            print("  scores: " + ", ".join(f"{k}={v}" for k, v in scores.items()))
            for item in review.get("revision_plan", []):
                print(f"  revise[{item.get('priority', '-')}] "
                      f"{item.get('dimension')}: {item.get('action')}")
    return 0 if result.ok else 1


def _build_llm_model(args, *, replay_suffix: str = "", stream: bool = False):
    """Construct an LLMExecutionModel from the shared execute/refine args. A
    replay_suffix isolates a role's replay bucket (so panel seats cache apart)."""
    from .execution.llm_model import LLMExecutionModel
    replay = args.replay_dir
    if replay and replay_suffix:
        replay = str(Path(replay).parent / f"{Path(replay).name}-{replay_suffix}")
    return LLMExecutionModel(
        provider=args.model_provider if args.model_provider != "deterministic" else "mock",
        model_id=args.model_id,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout,
        replay_dir=replay,
        stream=stream,
    )


def _parse_role_model_spec(spec: str, *, option: str) -> tuple[str, str]:
    """Parse a role-level ``PROVIDER:MODEL`` override used by serial production."""
    if ":" not in spec:
        raise SystemExit(f"{option} expects PROVIDER:MODEL")
    provider, model_id = (part.strip() for part in spec.split(":", 1))
    if not provider or not model_id or provider == "deterministic":
        raise SystemExit(f"{option} requires a live PROVIDER:MODEL")
    return provider, model_id


def _role_model_args(args, spec: str | None, *, option: str):
    """Return an args clone whose provider/model identify one production role.

    A missing override preserves the historical single-model behavior. Keeping
    all other sampling, timeout and replay settings shared makes the role split a
    routing change rather than an accidental generation-policy change.
    """
    if not spec:
        return args
    provider, model_id = _parse_role_model_spec(spec, option=option)
    role_args = argparse.Namespace(**vars(args))
    role_args.model_provider = provider
    role_args.model_id = model_id
    return role_args


def _build_role_model(args, spec: str | None, *, option: str, replay_suffix: str):
    role_args = _role_model_args(args, spec, option=option)
    if role_args.model_provider == "deterministic":
        raise SystemExit(
            f"{option} is not set and the primary --model-provider is deterministic; "
            "configure a live PROVIDER:MODEL")
    return _build_llm_model(role_args, replay_suffix=replay_suffix)


def _make_reviewer(args, gen_model):
    """Build the evaluative reviewer for execute/refine: a single LLM judge or a
    multi-model panel. Reuses gen_model when it is already an LLM."""
    kind = args.reviewer
    if kind == "unanchored":
        from .execution.draft_review import unanchored_entity_reviewer
        return unanchored_entity_reviewer()
    if kind == "llm-quality":
        from .execution.quality_center import llm_quality_judge
        model = gen_model if gen_model is not None else _build_llm_model(args)
        return llm_quality_judge(model)
    if kind == "panel":
        from .execution.review_panel import build_review_panel
        roles = [r.strip() for r in args.panel_roles.split(",") if r.strip()]
        # Each seat gets its own model instance + isolated replay bucket. With a
        # single live provider this is DeepSeek-in-4-hats; swap per-role models
        # here when more provider keys exist.
        role_to_model = {role: _build_llm_model(args, replay_suffix=role) for role in roles}
        return build_review_panel(role_to_model)
    raise SystemExit(f"unknown --reviewer {kind!r}")


def _cmd_refine(args) -> int:
    _load_dotenv(args)
    from .execution.refine import refine_package

    package = json.loads(Path(args.package).read_text(encoding="utf-8"))

    prompt_runtime = None
    if args.prompt_cache_dir or args.prompt_mode != "frozen":
        from .prompt.runtime import PromptRuntime
        prompt_root = (Path(args.prompt_root) if args.prompt_root
                       else Path(args.standard_root) / "contracts" / "prompts")
        prompt_runtime = PromptRuntime(
            prompt_root=prompt_root,
            cache_root=args.prompt_cache_dir,
            manifest_schema=Path(args.standard_root) / "contracts" / "prompt-manifest.schema.json",
            mode=args.prompt_mode,
        )

    gen_model = None
    if args.model_provider not in ("deterministic",):
        gen_model = _build_llm_model(args, replay_suffix="gen", stream=args.stream)

    reviewer = _make_reviewer(args, gen_model)

    # The rewriter is its own model instance (isolated replay bucket) so a rewrite
    # request never collides with a generation or judge request in the cache.
    rewrite_model = (_build_llm_model(args, replay_suffix="rewrite")
                     if args.model_provider != "deterministic"
                     else _build_llm_model(args, replay_suffix="rewrite"))

    result = refine_package(
        package=package,
        standard_root=args.standard_root,
        project_path=args.project,
        gen_model=gen_model,
        reviewer=reviewer,
        rewrite_model=rewrite_model,
        min_words=args.min_words,
        max_rounds=args.max_rounds,
        threshold=args.threshold,
        prompt_runtime=prompt_runtime,
        prompt_id=args.prompt_id,
        prompt_version=args.prompt_version,
    )

    print(f"stage={result.stage}: {result.message}")
    for f in (result.qa_findings or []):
        print(f"  {f}")
    if not result.ok:
        return 1

    print(f"verdict : {result.verdict} ({result.terminate_reason}, {result.rounds} round(s))")
    print(f"initial : {result.initial_hash}")
    print(f"final   : {result.final_hash}")
    print(f"draft   : {result.artifact_path}")
    before, after = result.scores_before or {}, result.scores_after or {}
    if before or after:
        print("scores (initial -> final):")
        for dim in sorted(set(before) | set(after)):
            b, a = before.get(dim), after.get(dim)
            mark = ""
            if isinstance(b, int) and isinstance(a, int) and a != b:
                mark = "  <=" if dim == "originality_risk" and a < b else (
                    "  ^" if a > b else "  v")
            print(f"  {dim:<24} {b} -> {a}{mark}")
    return 0


def _cmd_commercial(args) -> int:
    """Commercial Optimization Loop (roadmap P16): generate a draft, simulate
    readers, rewrite, re-simulate, and keep the rewrite ONLY if readers
    relatively improved. Comparison-only, advisory — never gates (ADR-003)."""
    _load_dotenv(args)
    from .execution.reader_sim import (
        llm_reader_simulator, commercial_reader_simulator,
        DEFAULT_PERSONAS, DEFAULT_COMMERCIAL_PERSONAS)
    from .execution.commercial import optimize_commercial
    from .execution.envelope import wrap
    from .execution.agent import serialize
    from . import derived
    from .execution.run import execute_package, DERIVED_CATEGORY

    package = json.loads(Path(args.package).read_text(encoding="utf-8"))

    gen_model = None
    if args.model_provider not in ("deterministic",):
        gen_model = _build_llm_model(args, replay_suffix="gen", stream=args.stream)

    # Stage 1 — generate + deterministic gate + write (reuses the execute loop).
    gen = execute_package(
        package=package, standard_root=args.standard_root,
        project_path=args.project, model=gen_model, min_words=args.min_words,
        prompt_id=args.prompt_id, prompt_version=args.prompt_version)
    print(f"stage={gen.stage}: {gen.message}")
    for f in (gen.qa_findings or []):
        print(f"  {f}")
    if not gen.ok:
        return 1

    # Stage 2 — the commercial loop. Simulator + rewriter get isolated replay
    # buckets so their requests never collide in the cache.
    sim_model = (_build_llm_model(args, replay_suffix="sim")
                 if args.model_provider != "deterministic"
                 else _build_llm_model(args, replay_suffix="sim"))
    rewrite_model = _build_llm_model(args, replay_suffix="rewrite")
    panel = getattr(args, "panel", "commercial")
    if panel == "appetite":
        simulator = llm_reader_simulator(sim_model)
    elif panel == "both":
        simulator = llm_reader_simulator(
            sim_model,
            personas=DEFAULT_PERSONAS + DEFAULT_COMMERCIAL_PERSONAS,
            reviewer_id="reader-simulator-v2-both")
    else:  # commercial (default) — the v2 pay-behavior panel
        simulator = commercial_reader_simulator(sim_model)

    result = optimize_commercial(
        simulator, rewrite_model, gen.artifact, package,
        max_rounds=args.max_rounds)
    session = result.session.to_dict()

    # Stage 3 — the FINAL selected draft must still pass the deterministic gate.
    from .execution.draft_qa import check_draft
    findings = check_draft(result.final_artifact, min_words=args.min_words)
    if findings:
        print(f"stage=final-draft-qa: commercial draft failed deterministic QA "
              f"({len(findings)} issue(s))")
        for f in findings:
            print(f"  {f}")
        return 1

    # Stage 4 — write the selected draft with the commercial session on the envelope.
    envelope = wrap(result.final_artifact, None, commercial_session=session)
    rel = derived.write_artifact(
        project_path=args.project, category=DERIVED_CATEGORY,
        artifact_id=result.final_artifact["task_id"], artifact=result.final_artifact,
        serialized=serialize(envelope))

    print(f"verdict : {session['verdict']} ({session['terminate_reason']}, "
          f"{len(session['rounds'])} round(s)) — advisory, comparison-only, never gates")
    print(f"initial : {gen.artifact['content_hash']}")
    print(f"final   : {result.final_artifact['content_hash']}")
    print(f"draft   : {rel}")
    for r in session["rounds"]:
        acc = "accepted" if r["accepted"] else "rejected"
        line = f"  round {r['round']}: reader={r['reader_verdict']} [{acc}]"
        if not r.get("degraded"):
            line += (f"  Δsatisfaction={r.get('mean_satisfaction_delta', 0):+d}"
                     f"  Δcontinue={r.get('continue_rate_delta', 0):+d}")
            if "mean_pay_probability_delta" in r:
                line += f"  Δpay={r['mean_pay_probability_delta']:+d}"
            if r.get("newly_dropped"):
                line += f"  newly_dropped={','.join(r['newly_dropped'])}"
            if r.get("newly_pay_lost"):
                line += f"  newly_pay_lost={','.join(r['newly_pay_lost'])}"
        print(line)
    return 0


def _cmd_state(args) -> int:
    """Project the story state (ADR-008 fold) and optionally write it as a pinned
    Derived artifact. Pure + advisory — never gates (ADR-003)."""
    from .memory import project_state, state_artifact

    reg = registry_loader.load(args.project)
    state = project_state(reg, up_to_event=args.up_to_event)

    if args.json:
        print(json.dumps(state.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    else:
        cursor = args.up_to_event or "full log"
        print(f"story-state ({cursor}) — advisory, never gates")
        print(f"  state_hash : {state.state_hash}")
        print(f"  events     : {len(state.event_order)}")
        print(f"  open setups: {len(state.open_setups)}  "
              f"resolved: {len(state.resolved_setups)}")
        for s in state.open_setups:
            print(f"    [open] {s['event']}: {s['summary']}")
        active_rel = [r for r, v in state.relationships.items() if v["active"]]
        print(f"  characters : {len(state.characters)}  "
              f"items: {len(state.items)}  "
              f"relationships: {len(state.relationships)} ({len(active_rel)} active)")
        for tid, tl in state.timelines.items():
            print(f"    {tid} {tl['name']}: {tl['events_so_far']} event(s), "
                  f"latest={tl['latest_event']}")

    if args.write:
        artifact = state_artifact(reg, state)
        rel = derived.write_artifact(
            project_path=args.project, category="story-state",
            artifact_id=artifact["task_id"], artifact=artifact,
            serialized=json.dumps(artifact, indent=2, ensure_ascii=False,
                                  sort_keys=True) + "\n")
        print(f"  written    : {rel}")
    return 0


def _add_state_command(sub) -> None:
    ps = sub.add_parser(
        "state", help="project story state as a fold over facts (roadmap P14, ADR-008)")
    ps.add_argument("--project", required=True)
    ps.add_argument("--up-to-event", default=None,
                    help="fold only events up to and including this EVT id (story cursor)")
    ps.add_argument("--json", action="store_true", help="print the full projection as JSON")
    ps.add_argument("--write", action="store_true",
                    help="write the projection as a pinned Derived artifact (registry/derived/story-state/)")
    ps.set_defaults(func=_cmd_state)


def _cmd_narrative(args) -> int:
    """Project the UNIFIED narrative state (M3-B5): a read-side fold of StoryState
    + the persisted per-chapter mandate/ir/run artifacts into conflict phase +
    payoff debt + reader questions + emotion-curve fatigue. Pure + advisory —
    never gates (ADR-003), never a fact (ADR-006/008)."""
    from .narrative import project_narrative_state, narrative_state_artifact

    reg = registry_loader.load(args.project)
    ns = project_narrative_state(reg, args.project, up_to_event=args.up_to_event)

    if args.json:
        print(json.dumps(ns.to_dict(), indent=2, ensure_ascii=False, sort_keys=True))
    else:
        mc, sp, ec = ns.main_conflict, ns.setup_payoff, ns.emotional_curve
        print(f"narrative-state ({ns.chapters_folded} chapter(s) folded) — advisory, never gates")
        print(f"  content_hash : {ns.content_hash}")
        print(f"  main conflict: phase={mc.get('phase')} pressure={mc.get('pressure_level')} "
              f"kind={mc.get('latest_escalation_kind')}")
        arc = ns.protagonist_arc
        print(f"  protagonist  : {arc.get('dimension')}: {arc.get('from')} → {arc.get('to')}")
        print(f"  setup/payoff : open={sp.get('open_count')} resolved={sp.get('resolved_count')} "
              f"pressure={sp.get('payoff_pressure')}")
        print(f"  reader Qs    : {ns.reader_questions.get('active_count')} active")
        print(f"  emotion curve: temp={ec.get('current_temperature')} "
              f"fatigue_risk={ec.get('fatigue_risk')} peak_ch={ec.get('recent_peak_chapter')}")

    if args.write:
        artifact = narrative_state_artifact(reg, args.project, ns)
        rel = derived.write_artifact(
            project_path=args.project, category="narrative-state",
            artifact_id=artifact["task_id"], artifact=artifact,
            serialized=json.dumps(artifact, indent=2, ensure_ascii=False,
                                  sort_keys=True) + "\n")
        print(f"  written    : {rel}")
    return 0


def _add_narrative_command(sub) -> None:
    ps = sub.add_parser(
        "narrative",
        help="project the unified narrative state (M3-B5, ADR-008): conflict phase / "
             "payoff debt / reader questions / emotion-curve fatigue")
    ps.add_argument("--project", required=True)
    ps.add_argument("--up-to-event", default=None,
                    help="fold only events up to and including this EVT id (story cursor)")
    ps.add_argument("--json", action="store_true", help="print the full projection as JSON")
    ps.add_argument("--write", action="store_true",
                    help="write the projection as a pinned Derived artifact (registry/derived/narrative-state/)")
    ps.set_defaults(func=_cmd_narrative)


def _cmd_brain_check(args) -> int:
    """Validate the authored Novel Brain against its Standard schema and print a
    readable report. Advisory — never gates a build (ADR-003)."""
    from .brain import load_brain, validate_brain, brain_style_directive, brain_path

    brain = load_brain(args.project)
    if brain is None:
        print(f"no Novel Brain authored yet at {brain_path(args.project)}")
        print("  (absent is not an error; prompts fall back to defaults)")
        return 0

    errors = validate_brain(brain, standard_root=args.standard_root)
    if errors:
        print("Novel Brain FAILED schema validation:")
        for e in errors:
            print(f"  - {e}")
        return 2

    print(f"OK: Novel Brain {brain.get('id', '?')} v{brain.get('version', '?')} — "
          f"advisory, never gates")
    print(f"  mission : {brain.get('mission', '')}")
    genre = brain.get("genre", {})
    print(f"  genre   : {genre.get('primary', '?')} "
          f"({genre.get('channel', '-')})")
    print(f"  promise : {brain.get('promise', '')}")
    print("  style directive fed to chapter-draft prompt:")
    for line in brain_style_directive(brain).splitlines():
        print(f"    {line}")
    return 0


def _cmd_speech_check(args) -> int:
    """Validate the authored Character Speech Profiles against their Standard
    schema and print a readable report. Advisory — never gates a build (ADR-003).
    Absent / fully-commented pristine template is treated as no profiles."""
    from .speech import (load_speech, validate_speech, speech_path,
                         render_speech_profiles)

    profiles = load_speech(args.project)
    if profiles is None:
        print(f"no Character Speech Profiles authored yet at {speech_path(args.project)}")
        print("  (absent is not an error; the draft degrades to v6 behavior — no language block)")
        return 0

    errors = validate_speech(profiles, standard_root=args.standard_root)
    if errors:
        print("Character Speech Profiles FAILED schema validation:")
        for e in errors:
            print(f"  - {e}")
        return 2

    entries = profiles.get("profiles") or []
    print(f"OK: {len(entries)} character speech profile(s) — advisory, never gates")
    for p in entries:
        print(f"  {p.get('character_id')} {p.get('name')}")
    print("  language block fed to the v7 chapter-draft prompt:")
    block = render_speech_profiles(entries)
    for line in block.splitlines():
        print(f"    {line}")
    return 0


def _cmd_schedule_check(args) -> int:
    """Project the serialization schedule (backlog / break-risk / update-calendar)
    from the authored SerialPlan + the count of produced drafts. Advisory — never
    gates (ADR-003)."""
    from datetime import date
    from .schedule import load_plan, validate_plan, project_schedule, plan_path

    plan = load_plan(args.project)
    if plan is None:
        print(f"no Serial Plan authored yet at {plan_path(args.project)}")
        print("  (absent is not an error; the serial can still produce chapters)")
        return 0

    errors = validate_plan(plan, standard_root=args.standard_root)
    if errors:
        print("Serial Plan FAILED schema validation:")
        for e in errors:
            print(f"  - {e}")
        return 2

    today = date.fromisoformat(args.today) if args.today else None
    report = project_schedule(args.project, plan, today=today, upcoming_days=args.days)
    r = report.to_dict()
    print(f"OK: Serial Plan {plan.get('id', '?')} v{plan.get('version', '?')} — "
          f"advisory, never gates")
    print(f"  produced : {r['produced']} chapter(s)")
    print(f"  due      : {r['due']} (by plan, over {r['active_days_elapsed']} active day(s))")
    print(f"  backlog  : {r['backlog']} (库存; target {r['backlog_target']})")
    print(f"  risk     : {r['break_risk']}")
    for f in r["findings"]:
        if f["severity"] == "warning":
            print(f"  [warn] {f['message']}")
    print(f"  next {len(r['upcoming'])} publish date(s): {', '.join(r['upcoming'])}")
    return 0


def _export_out_dir(project: str) -> "Path":
    from pathlib import Path
    out = Path(project) / "workspace" / "exports"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _cmd_export_book(args) -> int:
    """Export a manuscript from produced chapter drafts (SOP stage 15). Pure
    read-side; never gates. Writes to workspace/exports/ — this is staging, NOT
    the outward publish transition (ADR-009): it never pushes to a platform and
    never writes the published log. Defaults to scope='published' so the natural
    export contains only human-authorized chapters."""
    from .export import assemble_book, render_markdown, render_txt

    book = assemble_book(args.project, scope=args.scope, title=args.title)
    if not book.chapters:
        hint = ("no chapters authorized as published (see sources/published-log.yaml); "
                "use --scope produced to export all drafts"
                if args.scope == "published" else "no drafts produced yet")
        print(f"export book: nothing to export — {hint}")
        return 0
    text = render_txt(book) if args.format == "txt" else render_markdown(book)
    ext = "txt" if args.format == "txt" else "md"
    out = _export_out_dir(args.project) / f"book.{args.scope}.{ext}"
    out.write_text(text, encoding="utf-8")
    print(f"export book: {len(book.chapters)} chapter(s), scope={args.scope}, "
          f"{book.word_count} chars -> {out}")
    return 0


def _cmd_export_ip(args) -> int:
    """Export the IP reference bible from the Story State projection (SOP stage
    16): characters / relationships / items / timeline / foreshadow. Pure
    read-side fold over facts; never mutates or writes them, never gates."""
    from .export import assemble_ip_bible, render_ip_markdown

    bible = assemble_ip_bible(args.project, title=args.title)
    out = _export_out_dir(args.project) / "ip-bible.md"
    out.write_text(render_ip_markdown(bible), encoding="utf-8")
    print(f"export ip: {len(bible.characters)} character(s), "
          f"{len(bible.event_order)} event(s) -> {out}")
    return 0


def _cmd_dashboard(args) -> int:
    """Aggregate the project's structured products into one panorama. Pure
    read-side; never gates."""
    from datetime import date
    from .dashboard import build_dashboard

    today = date.fromisoformat(args.today) if args.today else None
    report = build_dashboard(args.project, standard_root=args.standard_root,
                             today=today, upcoming_days=args.days)
    d = report.to_dict()

    if args.json:
        print(json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    narrative = d.get("narrative", {})
    ref_anchor = d.get("reference_anchor") or {}
    print("Novel Dashboard — advisory, never gates")
    print(f"  narrative  : chapters_folded={narrative.get('chapters_folded', 0)}")
    if narrative.get("reference_anchor"):
        ra = narrative["reference_anchor"]
        print(f"  ref anchor : {ra.get('id')}  genre={ra.get('market_positioning', {}).get('genre', '?')}"
              f"  core={ra.get('market_positioning', {}).get('core_promise', '')}")
    elif ref_anchor:
        print(f"  ref anchor : {ref_anchor.get('id')}  genre={ref_anchor.get('market_positioning', {}).get('genre', '?')}"
              f"  core={ref_anchor.get('market_positioning', {}).get('core_promise', '')}")
    return 0


def _cmd_quality_snapshot(args) -> int:
    from .serialize.quality_snapshot import build_quality_snapshot
    snapshot = build_quality_snapshot(
        chapter_id=args.chapter_id,
        body=args.body,
    )
    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"quality snapshot: {snapshot['chapter_id']} warnings={snapshot['warning_count']}")
    for finding in snapshot["findings"]:
        print(f"  - {finding['check']}: {finding['message']}")
    return 0


def _cmd_quality_snapshot_compare(args) -> int:
    from .serialize.quality_snapshot import build_quality_snapshot, compare_quality_snapshots
    left = build_quality_snapshot(chapter_id=args.left_id, body=args.left_body)
    right = build_quality_snapshot(chapter_id=args.right_id, body=args.right_body)
    cmp = compare_quality_snapshots(left, right)
    if args.json:
        print(json.dumps(cmp, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"quality snapshot compare: {cmp['left']['chapter_id']} -> {cmp['right']['chapter_id']} verdict={cmp['verdict']} delta={cmp['delta']}")
    return 0


def _add_export_commands(sub) -> None:
    pe = sub.add_parser(
        "export",
        help="export deliverables: manuscript (md/txt) + IP bible (SOP stages 15/16)")
    export_sub = pe.add_subparsers(dest="export_command", required=True)

    book = export_sub.add_parser(
        "book", help="assemble produced chapter drafts into a manuscript (staging; never publishes)")
    book.add_argument("--project", required=True)
    book.add_argument("--scope", choices=["published", "produced"], default="published",
                      help="published = only human-authorized chapters (ADR-009, default); "
                           "produced = all drafts (author's working copy)")
    book.add_argument("--format", choices=["md", "txt"], default="md")
    book.add_argument("--title", default=None, help="book title; defaults to the project dir name")
    book.set_defaults(func=_cmd_export_book)

    ip = export_sub.add_parser(
        "ip", help="assemble the IP reference bible from the Story State projection")
    ip.add_argument("--project", required=True)
    ip.add_argument("--title", default=None, help="bible title; defaults to the project dir name")
    ip.set_defaults(func=_cmd_export_ip)


def _cmd_director_plan(args) -> int:
    objective = build_chapter_objective(
        chapter_id=args.chapter,
        narrative_ir={"id": args.narrative_ir_id} if args.narrative_ir_id else None,
        state={"state_hash": args.state_hash} if args.state_hash else None,
        quality={"id": args.quality_ref} if args.quality_ref else None,
        commercial={"id": args.commercial_ref} if args.commercial_ref else None,
        signals={"id": args.signal_ref} if args.signal_ref else None,
        objective_id=args.objective_id,
    )
    errs = validate_chapter_objective(objective)
    if errs:
        print("chapter objective FAILED validation:")
        for e in errs:
            print(f"  - {e}")
        return 2
    print(json.dumps(objective, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _cmd_director_brief(args) -> int:
    objective = json.loads(Path(args.objective).read_text(encoding="utf-8"))
    brief = build_director_brief(
        chapter_id=args.chapter,
        objective=objective,
        state={"state_hash": args.state_hash} if args.state_hash else None,
        narrative_ir={"hash": args.narrative_ir_hash} if args.narrative_ir_hash else None,
        quality={"id": args.quality_ref, "rationale": args.quality_rationale or []} if args.quality_ref or args.quality_rationale else None,
        commercial={"id": args.commercial_ref, "rationale": args.commercial_rationale or []} if args.commercial_ref or args.commercial_rationale else None,
        signals={"id": args.signal_ref, "rationale": args.signal_rationale or []} if args.signal_ref or args.signal_rationale else None,
        brief_id=args.brief_id,
    )
    errs = validate_director_brief(brief)
    if errs:
        print("director brief FAILED validation:")
        for e in errs:
            print(f"  - {e}")
        return 2
    print(json.dumps(brief, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _cmd_director_critique(args) -> int:
    draft = json.loads(Path(args.draft).read_text(encoding="utf-8"))
    critique = build_director_critique(
        chapter_id=args.chapter,
        draft=draft,
        objective={"id": args.objective_id} if args.objective_id else None,
        quality={"problem_dimensions": json.loads(args.quality_problems) if args.quality_problems else []},
        commercial={"commercial_min": args.commercial_min} if args.commercial_min is not None else None,
        signals={"note": args.signal_note} if args.signal_note else None,
    )
    print(json.dumps(critique, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _cmd_director_compare(args) -> int:
    versions = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.versions]
    report = build_version_comparison(chapter_id=args.chapter, versions=versions,
                                      objective={"id": args.objective_id} if args.objective_id else None,
                                      brief={"id": args.brief_id} if args.brief_id else None)
    output = report
    if args.character_judge:
        if len(versions) != 2:
            raise SystemExit("--character-judge requires exactly two --versions")
        if ":" not in args.character_judge:
            raise SystemExit("--character-judge expects provider:model")
        _load_dotenv(args)
        provider, model_id = (part.strip() for part in args.character_judge.split(":", 1))
        if not provider or not model_id:
            raise SystemExit("--character-judge expects provider:model")
        from .execution.llm_model import LLMExecutionModel
        from .execution.pairwise_judge import compare_character
        model = LLMExecutionModel(
            provider=provider, model_id=model_id, temperature=0.0,
            max_tokens=args.character_judge_max_tokens,
            timeout_seconds=args.character_judge_timeout,
        )

        def _body(version):
            return str(version.get("after_text") or version.get("text") or "")

        def _label(version, index):
            return str(version.get("version_id") or version.get("id") or f"v{index}")

        character_pairwise = compare_character(
            _body(versions[0]), _body(versions[1]), model,
            label_a=_label(versions[0], 1), label_b=_label(versions[1], 2),
        ).to_dict()
        output = {
            "kind": "director_comparison_envelope",
            "comparison": report,
            "character_pairwise": character_pairwise,
            "gating": False,
            "comparison_only": True,
        }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _cmd_director_select(args) -> int:
    comparison = json.loads(Path(args.comparison).read_text(encoding="utf-8"))
    record = build_version_selection(chapter_id=args.chapter, comparison=comparison,
                                     selected_version=args.selected_version, reason=args.reason)
    print(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _cmd_director_consumption_ab(args) -> int:
    """Run CI-M2-04's same-chapter live A/B in isolated project copies."""
    if not args.confirm_mint:
        raise SystemExit("consumption-ab requires --confirm-mint")
    if args.model_provider in ("deterministic", "mock", "paste"):
        raise SystemExit("consumption-ab requires a live --model-provider")
    _load_dotenv(args)
    from .consumption_ab_runner import run_live_consumption_ab
    from .execution.llm_model import LLMExecutionModel

    replay_without = replay_with = None
    if args.replay_dir:
        replay_root = Path(args.replay_dir)
        replay_without = str(replay_root / "without")
        replay_with = str(replay_root / "with")

    def build_model(replay_dir):
        return LLMExecutionModel(
            provider=args.model_provider,
            model_id=args.model_id,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            timeout_seconds=args.timeout,
            replay_dir=replay_dir,
            stream=False,
        )

    standard_root = Path(args.standard_root or _sibling_standard())
    schema_dir = Path(
        args.schema_dir
        or standard_root / "phase-1" / "generated" / "json-schema")
    package = json.loads(Path(args.package).read_text(encoding="utf-8"))
    report = run_live_consumption_ab(
        project_path=args.project,
        package=package,
        standard_root=standard_root,
        schema_dir=schema_dir,
        output_dir=args.out,
        model_without=build_model(replay_without),
        model_with=build_model(replay_with),
        fact_name=args.fact_name,
        prompt_version=args.prompt_version,
        actor=args.actor,
        confirmed=True,
    )
    print(json.dumps({
        "kind": report["kind"],
        "chapter_id": report["chapter_id"],
        "all_criteria_met": report["all_criteria_met"],
        "criteria": report["criteria"],
        "report_hash": report["report_hash"],
        "output_dir": str(Path(args.out)),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["all_criteria_met"] else 2


def _add_director_command(sub) -> None:
    pd = sub.add_parser("director", help="Narrative Director commands (Phase 6)")
    dsub = pd.add_subparsers(dest="director_command", required=True)
    plan = dsub.add_parser("plan", help="generate a chapter objective")
    plan.add_argument("--chapter", required=True)
    plan.add_argument("--objective-id", default=None)
    plan.add_argument("--narrative-ir-id", default=None)
    plan.add_argument("--state-hash", default=None)
    plan.add_argument("--quality-ref", default=None)
    plan.add_argument("--commercial-ref", default=None)
    plan.add_argument("--signal-ref", default=None)
    plan.set_defaults(func=_cmd_director_plan)

    brief = dsub.add_parser("brief", help="generate a director brief from an objective")
    brief.add_argument("--chapter", required=True)
    brief.add_argument("--objective", required=True, help="path to chapter-objective JSON")
    brief.add_argument("--brief-id", default=None)
    brief.add_argument("--state-hash", default=None)
    brief.add_argument("--narrative-ir-hash", default=None)
    brief.add_argument("--quality-ref", default=None)
    brief.add_argument("--commercial-ref", default=None)
    brief.add_argument("--signal-ref", default=None)
    brief.add_argument("--quality-rationale", action="append", default=[])
    brief.add_argument("--commercial-rationale", action="append", default=[])
    brief.add_argument("--signal-rationale", action="append", default=[])
    brief.set_defaults(func=_cmd_director_brief)

    crt = dsub.add_parser("critique", help="generate a structured critique from a draft")
    crt.add_argument("--chapter", required=True)
    crt.add_argument("--draft", required=True, help="path to draft JSON")
    crt.add_argument("--objective-id", default=None)
    crt.add_argument("--quality-problems", default=None,
                     help="JSON array of problem_dimensions")
    crt.add_argument("--commercial-min", type=int, default=None)
    crt.add_argument("--signal-note", default=None)
    crt.set_defaults(func=_cmd_director_critique)

    cmp = dsub.add_parser("compare", help="compare multiple draft versions")
    cmp.add_argument("--chapter", required=True)
    cmp.add_argument("--versions", nargs="+", required=True, help="paths to version JSON files")
    cmp.add_argument("--objective-id", default=None)
    cmp.add_argument("--brief-id", default=None)
    cmp.add_argument(
        "--character-judge", default=None, metavar="PROVIDER:MODEL",
        help="optionally compare exactly two same-chapter versions with the character pairwise judge",
    )
    cmp.add_argument("--character-judge-timeout", type=float, default=120)
    cmp.add_argument("--character-judge-max-tokens", type=int, default=1200)
    cmp.add_argument("--env-file", default=None)
    cmp.set_defaults(func=_cmd_director_compare)

    sel = dsub.add_parser("select", help="select a version from a comparison report")
    sel.add_argument("--chapter", required=True)
    sel.add_argument("--comparison", required=True, help="path to comparison JSON")
    sel.add_argument("--selected-version", default=None)
    sel.add_argument("--reason", default=None)
    sel.set_defaults(func=_cmd_director_select)

    cab = dsub.add_parser(
        "consumption-ab",
        help="run a live same-chapter A/B proving Mint -> Recompute consumption",
    )
    cab.add_argument("--project", required=True, type=Path)
    cab.add_argument("--package", required=True, type=Path)
    cab.add_argument("--out", required=True, type=Path)
    cab.add_argument("--fact-name", required=True,
                     help="unique approved Item name that the WITH arm must consume")
    cab.add_argument("--confirm-mint", action="store_true",
                     help="explicitly authorize Mint inside the isolated WITH arm")
    cab.add_argument("--actor", default="human-ci-m2-04")
    cab.add_argument("--model-provider", required=True)
    cab.add_argument("--model-id", required=True)
    cab.add_argument("--prompt-version", default="14.0.0")
    cab.add_argument("--standard-root", default=None)
    cab.add_argument("--schema-dir", default=None)
    cab.add_argument("--temperature", type=float, default=0.0)
    cab.add_argument("--top-p", type=float, default=None)
    cab.add_argument("--max-tokens", type=int, default=5000)
    cab.add_argument("--timeout", type=float, default=180)
    cab.add_argument("--replay-dir", default=None)
    cab.add_argument("--env-file", default=None)
    cab.set_defaults(func=_cmd_director_consumption_ab)


def _add_dashboard_command(sub) -> None:
    pd = sub.add_parser(
        "dashboard",
        help="project-wide panorama: state + brain + schedule + production (roadmap P18)")
    pd.add_argument("--project", required=True)
    pd.add_argument("--standard-root", default=None,
                    help="Standard repo root; defaults to the sibling AI-Novel-Standard")
    pd.add_argument("--today", default=None,
                    help="ISO date (YYYY-MM-DD) to project schedule as of; defaults to today")
    pd.add_argument("--days", type=int, default=5,
                    help="how many upcoming publish dates to include")
    pd.add_argument("--json", action="store_true", help="print the full dashboard as JSON")
    pd.set_defaults(func=_cmd_dashboard)


def _add_brain_command(sub) -> None:
    pb = sub.add_parser(
        "brain", help="Novel Brain commands — the authored static constitution (roadmap P15)")
    brain_sub = pb.add_subparsers(dest="brain_command", required=True)
    check = brain_sub.add_parser(
        "check", help="validate sources/novel-brain.yaml against its Standard schema (advisory)")
    check.add_argument("--project", required=True)
    check.add_argument("--standard-root", default=None,
                       help="Standard repo root; defaults to the sibling AI-Novel-Standard")
    check.set_defaults(func=_cmd_brain_check)


def _add_speech_command(sub) -> None:
    ps = sub.add_parser(
        "speech", help="Character Speech Profile commands — the authored expression-layer spec (roadmap §15)")
    speech_sub = ps.add_subparsers(dest="speech_command", required=True)
    check = speech_sub.add_parser(
        "check", help="validate sources/character-speech-profiles.yaml against its Standard schema (advisory)")
    check.add_argument("--project", required=True)
    check.add_argument("--standard-root", default=None,
                       help="Standard repo root; defaults to the sibling AI-Novel-Standard")
    check.set_defaults(func=_cmd_speech_check)


def _sibling_standard() -> Path:
    """The sibling AI-Novel-Standard repo root (matches the positioning loader's
    resolution). Used when a command needs schemas but no --schema-dir was given."""
    return Path(__file__).resolve().parents[2] / "AI-Novel-Standard"


def _load_derived_artifact(project_path, artifact_id: str) -> dict:
    """Locate a derived artifact by id via the provenance index and load it.
    Reads only registry/derived/ — never facts (ADR-006).

    A ChapterDraft is stored inside a runtime-draft envelope (the Runtime
    Envelope, see the frozen-schema rationale): the canonical draft — carrying
    provenance pins + content_hash — lives under `draft`. Unwrap it so callers
    always get the inner artifact, whichever way it was written."""
    import yaml
    idx = Path(project_path) / "registry" / "derived" / "_index.yaml"
    if not idx.exists():
        raise SystemExit(f"no derived index at {idx}")
    index = yaml.safe_load(idx.read_text(encoding="utf-8")) or {}
    for entry in index.get("artifacts", []):
        if entry.get("id") == artifact_id:
            path = Path(project_path) / entry["path"]
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if str(loaded.get("envelope_format", "")).startswith("runtime-draft/") \
                    and isinstance(loaded.get("draft"), dict):
                return loaded["draft"]
            return loaded
    raise SystemExit(f"derived artifact {artifact_id!r} not found in index")


def _cmd_candidates_extract(args) -> int:
    """Fact Candidate Pipeline — PREPARATION half (roadmap Phase 5).

    Extract candidate facts from a produced ChapterDraft, reconcile each against
    the current Registry (deterministic 5-class), and stage a plan for human
    review. Writes ONLY registry/derived/fact-candidates/ — never facts (ADR-006);
    never mints (ADR-009); never gates (ADR-003)."""
    _load_dotenv(args)
    from .registry_loader import load as load_registry
    from .candidates.reconcile import reconcile
    from .candidates.extract import DeterministicExtractor, LLMExtractor
    from .candidates import plan as planmod

    draft = _load_derived_artifact(args.project, args.chapter_draft_id)
    reg = load_registry(args.project)

    # The extractor sees a ROSTER of known entities — id + name + aliases only,
    # NOT declared field values — so it can resolve a prose reference (e.g. a
    # 中译名) back to an existing id instead of proposing a phantom `new`. Value
    # comparison stays the deterministic reconciler's job. Covers ALL project
    # entities (prose may reference any, not just this draft's build pins).
    from .candidates.extract import entity_roster
    from .candidates.reconcile import build_field_constraints
    roster = entity_roster(reg, reg.all_ids())

    if args.model_provider == "deterministic":
        extractor = DeterministicExtractor()
    else:
        model = _build_llm_model(args, replay_suffix="fact-extract")
        extractor = LLMExtractor(model)

    candidates = extractor.extract(draft, known_entities=roster)

    # Field-enum constraints let reconcile reclassify an out-of-enum value (e.g.
    # a model writing narrative situation into the `status` lifecycle enum) as
    # `unverifiable` rather than a false `conflicting`. Degrades gracefully: if
    # the schema dir can't be read, constraints are empty and behavior is unchanged.
    schema_dir = (_sibling_standard() / "phase-1" / "generated" / "json-schema")
    try:
        constraints = build_field_constraints(schema_dir, None)
    except Exception:
        constraints = {}
    recon = reconcile(reg, candidates, field_constraints=constraints)

    plan_id = args.plan_id or planmod.next_plan_id(_existing_plan_ids(args.project))
    plan, rel = planmod.stage_plan(
        project_path=args.project, plan_id=plan_id, draft=draft,
        recon=recon, extractor_id=extractor.model_id)

    counts = recon.counts()
    print(f"candidates: {plan_id} — advisory, never gates, never mints "
          f"(authority={plan['authority']})")
    print(f"  source   : {plan['source']['chapter_draft_id']} "
          f"({plan['source']['content_hash'][:16]}…) via {plan['source']['extractor']}")
    print(f"  classes  : " + "  ".join(
        f"{c}={counts[c]}" for c in ("new", "additive", "consistent",
                                     "conflicting", "unverifiable")))
    if counts["conflicting"]:
        print(f"  ⚠ {counts['conflicting']} CONFLICT(S) — prose contradicts a declared "
              f"fact; a human decides (typo/retcon/new fact). Never auto-resolved.")
    print(f"  reconciled against: {', '.join(plan['reconciled_against']) or '(none)'}")
    print(f"  writes_facts={plan['policy']['writes_registry_facts']}  "
          f"requires_human_approval={plan['policy']['requires_human_approval']}")
    print(f"  staged   : {rel}")
    return 0


def _existing_plan_ids(project_path) -> list:
    import yaml
    idx = Path(project_path) / "registry" / "derived" / "_index.yaml"
    if not idx.exists():
        return []
    index = yaml.safe_load(idx.read_text(encoding="utf-8")) or {}
    return [e["id"] for e in index.get("artifacts", [])
            if e.get("category") == "fact-candidates"]


def _cmd_candidates_review(args) -> int:
    """Human-review VIEW of a staged FactCandidatePlan (read-only). Groups items
    by classification so a reviewer sees prose-vs-fact side by side. It does not
    accept, reject, or mint — those cross the ADR-009 boundary."""
    plan = _load_derived_artifact(args.project, args.plan_id)

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(f"FactCandidatePlan {plan['id']} — {plan['review_status']} "
          f"(authority={plan['authority']}, gating={plan['gating']})")
    print(f"  {plan['rationale']}")
    print(f"  source: {plan['source']['chapter_draft_id']} via {plan['source'].get('extractor')}")
    by_class: dict = {}
    for it in plan.get("items", []):
        by_class.setdefault(it["classification"], []).append(it)
    order = ["conflicting", "new", "additive", "unverifiable", "consistent"]
    for cls in order:
        items = by_class.get(cls, [])
        if not items:
            continue
        print(f"\n[{cls}] {len(items)}")
        for it in items:
            tgt = it.get("matched_entity_id") or f"(new {it['target_type']})"
            line = f"  {it['candidate_id']} {tgt}.{it['field']} = {it['extracted_value']!r}"
            if "existing_value" in it:
                line += f"  (fact: {it['existing_value']!r})"
            print(line)
            if it.get("evidence"):
                print(f"      ⤷ {it['evidence']}")
    print(f"\nnext: {plan['next_workflow']['mint']}")
    return 0


def _cmd_candidates_mint(args) -> int:
    """Fact Candidate Pipeline — EXECUTION half (roadmap Phase 5.2): cross the
    ADR-009 boundary and write human-accepted `additive` candidates into
    registry/facts/. This is the system's ONLY fact-writer.

    Without --confirm it PREVIEWS (writes nothing). --confirm is the distinct
    human authorization. Validate-then-write: a mint that would break the
    registry is refused and writes nothing; a stale plan is refused; a
    non-additive accepted candidate is refused."""
    from .mint import execute_mint, preview_mint, MintRefused

    plan = _load_derived_artifact(args.project, args.plan_id)
    schema_dir = (args.schema_dir if args.schema_dir
                  else str(_sibling_standard() / "phase-1" / "generated" / "json-schema"))
    accepted = args.accept or []

    try:
        if not args.confirm:
            mint_plan, report = preview_mint(
                project_path=args.project, plan=plan, accepted=accepted,
                schema_dir=schema_dir)
            n_new = sum(1 for it in mint_plan.items if it.classification == "new")
            n_add = len(mint_plan.items) - n_new
            print(f"PREVIEW {plan['id']} — nothing written (add --confirm to authorize)")
            print(f"  would mint {n_new} new + {n_add} additive fact(s):")
            for it in mint_plan.items:
                if it.classification == "new":
                    print(f"    {it.candidate_id} NEW {it.type_code} "
                          f"name={it.value!r} → {it.entity_id} (id not yet allocated)")
                else:
                    print(f"    {it.candidate_id} {it.entity_id}.{it.field} = {it.value!r}")
            print(f"  post-mint gate: {'PASS' if report.ok else 'FAIL'}"
                  + ("" if report.ok else " — mint would be REFUSED:"))
            for f in report.errors:
                print(f"    [error] {f}")
            return 0 if report.ok else 1

        receipt = execute_mint(
            project_path=args.project, plan=plan, accepted=accepted,
            schema_dir=schema_dir, confirmed=True, actor=args.actor)
    except MintRefused as e:
        print(f"REFUSED ({e.reason}): {e.detail}")
        print("  the human-authority boundary was NOT crossed; facts are untouched.")
        return 2

    rv = receipt["registry_version"]
    print(f"MINTED {receipt['id']} — {len(receipt['minted'])} fact(s) written "
          f"(authority={receipt['authority']})")
    for m in receipt["minted"]:
        fv = m["fact_version"]
        if m["classification"] == "new":
            print(f"  NEW {m['type_code']} {m['entity_id']} "
                  f"name={m['value']!r}  (fact_version {fv['before']}→{fv['after']})")
        else:
            print(f"  {m['entity_id']}.{m['field']} = {m['value']!r}  "
                  f"(fact_version {fv['before']}→{fv['after']})")
    print(f"  registry-version {rv['before']}→{rv['after']}  "
          f"revalidation={'PASS' if receipt['revalidation']['passed'] else 'FAIL'}")
    return 0


def _cmd_w12(args) -> int:
    _load_dotenv(args)
    from .candidates import plan as planmod
    from .mint import MintRefused
    from .registry_loader import load as load_registry

    result = planmod.run_w12_fact_reflow(
        project_path=args.project,
        plan_id=args.plan_id or planmod.next_plan_id(_existing_plan_ids(args.project)),
        chapter_draft_id=args.chapter_draft_id,
        model=_build_llm_model(args, replay_suffix="w12") if args.model_provider != "deterministic" else None,
        accepted=args.accept,
    )
    draft_id = result.get("draft_id", "chapter-final")
    print(f"w12 plan   : {result['plan']['id']} -> {result['derived_path']}")
    print(f"  draft     : {draft_id}")
    print(f"  source    : {result.get('draft_source', 'unknown')}")
    print(f"  candidate : {result['candidate_count']}")
    if result.get('extractor_error'):
        print(f"  ⚠ extractor: {result['extractor_error']} — 0 candidates may be a "
              f"call failure, not an empty chapter (try a larger --timeout)")
    print(f"  approval  : {result['approval_request_id']} [{result['approval_status']}]")
    print(f"  counts    : " + ", ".join(f"{k}={v}" for k, v in result['reconciled_counts'].items()))
    if result.get('review_findings'):
        print(f"  review    : {len(result['review_findings'])} finding(s)")
    if args.confirm and args.accept:
        schema_dir = getattr(args, "schema_dir", None)
        if schema_dir is None:
            schema_dir = str(_sibling_standard() / "phase-1" / "generated" / "json-schema")
        try:
            receipt = execute_mint(
                project_path=args.project,
                plan=result["plan"],
                accepted=args.accept,
                schema_dir=schema_dir,
                confirmed=True,
                actor=getattr(args, "actor", None),
            )
        except MintRefused as e:
            print(f"REFUSED ({e.reason}): {e.detail}")
            return 2
        print(f"  mint     : {receipt['id']} facts={len(receipt['minted'])}")
        rec = recompute.execute_recompute(None, args.project, mint_receipt=receipt)
        print(f"  recompute: {rec['id']} impacted={len(rec.get('impacted', []))}")
    return 0


def _cmd_recompute(args) -> int:
    """Derived Recompute Engine (roadmap Phase 5.3): after a mint, rebuild the
    stale DETERMINISTIC folds and STAGE the stale GENERATIVE artifacts.

    `recompute plan` previews (writes nothing). `recompute apply` auto-rebuilds
    the pure fact-folds (write-back + fresh pin) and stages the generative ones
    with the exact human regeneration command — it NEVER re-authors prose and
    never writes facts."""
    from .registry_loader import load as load_registry
    from . import recompute

    schema_dir = (args.schema_dir if args.schema_dir
                  else str(_sibling_standard() / "phase-1" / "generated" / "json-schema"))
    reg = load_registry(args.project, schema_dir=schema_dir)

    mint_receipt = None
    if args.from_mint:
        mint_receipt = _load_derived_artifact(args.project, args.from_mint)

    if args.apply:
        report = recompute.execute_recompute(reg, args.project, mint_receipt=mint_receipt)
        verb = "APPLIED"
    else:
        report = recompute.recompute_plan(reg, args.project, mint_receipt=mint_receipt)
        verb = "PLAN (nothing written)"

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    imp = report["impacted"]
    print(f"recompute {verb} — {report['id']} "
          f"(authority={report['authority']}, gating={report['gating']})")
    print(f"  {report['rationale']}")
    det = [i for i in imp if i["kind"] == "deterministic"]
    gen = [i for i in imp if i["kind"] == "generative"]
    if det:
        print(f"\n  deterministic (auto-rebuilt) — {len(det)}:")
        for i in det:
            print(f"    {i['artifact_id']} [{i['category']}] {i['reason']}")
    if gen:
        print(f"\n  generative (STAGED for human regeneration — never auto-authored) — {len(gen)}:")
        for s in report["staged"]:
            print(f"    {s['artifact_id']} [{s['category']}]")
            print(f"        ⤷ {s['regenerate_with']}")
    if not imp:
        print("  nothing stale — all derived artifacts are fresh.")
    return 0


def _add_recompute_command(sub) -> None:
    pr = sub.add_parser(
        "recompute",
        help="Derived Recompute Engine — rebuild stale deterministic folds, stage generative ones (roadmap Phase 5.3)")
    rsub = pr.add_subparsers(dest="recompute_command", required=True)
    for name, is_apply, helptext in (
        ("plan", False, "preview the impact of current staleness (writes nothing)"),
        ("apply", True, "rebuild stale deterministic folds + stage generative artifacts"),
    ):
        sp = rsub.add_parser(name, help=helptext)
        sp.add_argument("--project", required=True)
        sp.add_argument("--from-mint", default=None, metavar="MINT-#####",
                        help="attribute this recompute to a mint receipt (the 5.2→5.3 chain)")
        sp.add_argument("--schema-dir", default=None,
                        help="schema dir; defaults to the sibling <standard>/phase-1/generated/json-schema")
        sp.add_argument("--json", action="store_true", help="emit the raw report as JSON")
        sp.set_defaults(func=_cmd_recompute, apply=is_apply)


def _add_candidates_command(sub) -> None:
    pc = sub.add_parser(
        "candidates",
        help="Fact Candidate Pipeline — extract candidate facts from prose for human review (roadmap Phase 5)")
    csub = pc.add_subparsers(dest="candidates_command", required=True)

    ex = csub.add_parser(
        "extract",
        help="extract candidate facts from a ChapterDraft, reconcile vs registry, stage a plan (never mints)")
    ex.add_argument("--project", required=True)
    ex.add_argument("--chapter-draft-id", required=True,
                    help="the ChapterDraft derived-artifact id (e.g. its task_id)")
    ex.add_argument("--plan-id", default=None,
                    help="override the FCP-##### plan id (default: next available)")
    # Extraction seam: deterministic stub by default (CI, no network); a live
    # provider drops in the LLM extractor. These mirror the execute/refine flags
    # _build_llm_model + _load_dotenv read, without the build-only ones.
    ex.add_argument("--model-provider", default="deterministic",
                    help="deterministic (default, stub) or a live provider (deepseek/openai/claude/...)")
    ex.add_argument("--model-id", default="")
    ex.add_argument("--temperature", type=float, default=0.0)
    ex.add_argument("--top-p", type=float, default=None)
    ex.add_argument("--max-tokens", type=int, default=None)
    ex.add_argument("--timeout", type=float, default=60.0)
    ex.add_argument("--replay-dir", default=None)
    ex.add_argument("--env-file", default=None)
    ex.set_defaults(func=_cmd_candidates_extract)

    rv = csub.add_parser(
        "review",
        help="read-only view of a staged candidate plan, grouped by classification (does not mint)")
    rv.add_argument("--project", required=True)
    rv.add_argument("--plan-id", required=True)
    rv.add_argument("--json", action="store_true", help="emit the raw plan as JSON")
    rv.set_defaults(func=_cmd_candidates_review)

    mn = csub.add_parser(
        "mint",
        help="write human-accepted ADDITIVE + NEW candidates into facts (new mints an id via the ID Mint Ledger; crosses the ADR-009 boundary; --confirm required)")
    mn.add_argument("--project", required=True)
    mn.add_argument("--plan-id", required=True)
    mn.add_argument("--accept", action="append", metavar="CAND-#####",
                    help="a candidate id the human accepts for minting (repeatable)")
    mn.add_argument("--confirm", action="store_true",
                    help="the explicit human authorization to cross into facts (ADR-009); "
                         "omit to preview without writing")
    mn.add_argument("--actor", default=None, help="optional: who authorized the mint")
    mn.add_argument("--schema-dir", default=None,
                    help="schema dir; defaults to the sibling <standard>/phase-1/generated/json-schema")
    mn.set_defaults(func=_cmd_candidates_mint)

    w12 = csub.add_parser(
        "w12",
        help="W12事实回流：默认读取 registry/derived/drafts 的最新 ChapterDraft，输出 fact-candidates 计划，并在 --confirm + --accept 时 mint + recompute")
    w12.epilog = "Default draft source: registry/derived/drafts"
    w12.add_argument("--project", required=True)
    w12.add_argument("--chapter-draft-id", default=None,
                     help="ChapterDraft derived-artifact id; omitted to use the default draft resolver")
    w12.add_argument("--plan-id", default=None,
                     help="override the W12 plan id (default: next available)")
    w12.add_argument("--model-provider", default="deterministic")
    w12.add_argument("--model-id", default="deepseek-v4-pro",
                     help="live model name (ignored for deterministic); must be a "
                          "valid provider model — an empty id makes DeepSeek 400 and "
                          "the extractor silently yields 0 candidates")
    w12.add_argument("--temperature", type=float, default=0.0)
    w12.add_argument("--top-p", type=float, default=None)
    w12.add_argument("--max-tokens", type=int, default=None)
    w12.add_argument("--timeout", type=float, default=120.0,
                     help="per-call timeout (s); the extraction prompt carries full "
                          "chapter prose + declared-field lists and can exceed a 60s "
                          "budget on a slow model — a timeout is swallowed by extract() "
                          "as 0 candidates, so this matches the serial default of 120")
    w12.add_argument("--replay-dir", default=None)
    w12.add_argument("--env-file", default=None)
    w12.add_argument("--accept", action="append", default=[], metavar="CAND-#####",
                     help="candidate ids to approve for minting; repeatable")
    w12.add_argument("--confirm", action="store_true",
                     help="cross the mint boundary and write approved facts")
    w12.set_defaults(func=_cmd_w12)


def _cmd_positioning_admit(args) -> int:
    """Pre-book ADMISSION check (roadmap 4.5): fold the authored Market Position
    + Novel Brain + derived Market Snapshot into an advisory admit/revise/hold
    recommendation. Read-side, deterministic; never gates (ADR-003); the decision
    to open a book stays with a human (ADR-009)."""
    from .positioning import load_position, validate_position, project_admission
    from .positioning.admission import write_admission
    from .positioning.loader import position_path

    position = load_position(args.project)
    if position is not None:
        errors = validate_position(position, standard_root=args.standard_root)
        if errors:
            print("Market Position FAILED schema validation:")
            for e in errors:
                print(f"  - {e}")
            return 2

    verdict = project_admission(args.project, standard_root=args.standard_root)

    if args.json:
        print(json.dumps(verdict, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if position is None:
            print(f"no Market Position authored yet at {position_path(args.project)}")
            print("  (absent is not an error; the admission check recommends 'hold')")
        b = verdict["basis"]
        print(f"admission : {verdict['recommendation'].upper()} — advisory, never gates "
              f"(authority={verdict['authority']})")
        print(f"  why      : {verdict['rationale']}")
        print(f"  complete : authored={b['completeness']['position_authored']} "
              f"missing={b['completeness']['missing'] or '(none)'}")
        print(f"  internal : brain={b['internal']['brain_authored']} "
              f"conflicts={b['internal']['conflicts'] or '(none)'}")
        ext = b["external"]
        print(f"  external : snapshot={ext['snapshot_present']}"
              f"{' STALE' if ext.get('snapshot_stale') else ''} "
              f"align={len(ext['alignments'])} misalign={ext['misalignments'] or '(none)'}")

    if args.write:
        rel = write_admission(args.project, verdict)
        print(f"written  : {rel}")
    return 0


def _add_positioning_command(sub) -> None:
    pp = sub.add_parser(
        "positioning",
        help="Market Positioning commands — the pre-book admission check (roadmap 4.5)")
    positioning_sub = pp.add_subparsers(dest="positioning_command", required=True)
    admit = positioning_sub.add_parser(
        "admit",
        help="fold Market Position + Brain + Market Snapshot into an admit/revise/hold verdict (advisory)")
    admit.add_argument("--project", required=True)
    admit.add_argument("--standard-root", default=None,
                       help="Standard repo root; defaults to the sibling AI-Novel-Standard")
    admit.add_argument("--json", action="store_true", help="emit the raw verdict as JSON")
    admit.add_argument("--write", action="store_true",
                       help="persist the verdict under registry/derived/market-admission/")
    admit.set_defaults(func=_cmd_positioning_admit)


def _cmd_publishing_card(args) -> int:
    """Build a per-chapter Production Card (roadmap 4.6): fold status + quality +
    commercial + pacing + the CITED publish-readiness into one summary a human
    consults before publishing. Read-side; never gates (ADR-003)."""
    from .publishing import build_production_card, write_production_card
    from .inventory import load_published_log

    log = load_published_log(args.project)
    card = build_production_card(args.project, args.chapter, published_log=log)

    if args.json:
        print(json.dumps(card, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        pr = card["publish_readiness"]
        print(f"Production Card {card['chapter_id']} — advisory, never gates "
              f"(authority={card['authority']})")
        print(f"  status   : {card['status']}")
        rp = pr.get("redline_passed")
        publish_line = f"  publish  : {pr['recommendation']}"
        if rp is not None:
            publish_line += f" (redline_passed={rp})"
        print(publish_line)
        if card.get("quality"):
            q = card["quality"]
            print(f"  quality  : " + "  ".join(
                f"{k}={q[k]}" for k in ("retention", "subscription", "payoff", "reader_drop_risk")
                if k in q))
        if card.get("commercial"):
            c = card["commercial"]
            line = f"  commerce : {c.get('verdict')}"
            if "pay_probability_delta" in c:
                line += f"  Δpay={c['pay_probability_delta']:+d}"
            print(line)
        print(f"  flags    : {', '.join(card['flags']) or '(none)'}")

    if args.write:
        print(f"written  : {write_production_card(args.project, card)}")
    return 0


def _cmd_publishing_review(args) -> int:
    """Build a Volume (~10ch) or Direction (~30ch) review (roadmap 4.6): fold the
    window's cards into a health verdict. The Direction review additionally
    PROPOSES a Market Position revision where production diverged from the pre-book
    thesis (never auto-written, ADR-009). Read-side; never gates (ADR-003)."""
    from .publishing import build_review, write_review
    from .inventory import load_published_log

    log = load_published_log(args.project)
    review = build_review(args.project, scope=args.scope,
                          start_index=max(0, args.start - 1), size=args.size,
                          published_log=log, standard_root=args.standard_root)

    if args.json:
        print(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        s, w = review["summary"], review["window"]
        print(f"{args.scope.capitalize()} Review — advisory, never gates "
              f"(authority={review['authority']})")
        print(f"  window   : {w['chapters_in_window']}/{w['target_size']} chapter(s)"
              f"  [{w.get('start_chapter','-')}..{w.get('end_chapter','-')}]")
        print(f"  health   : {s['health'].upper()}")
        for obs in s["observations"]:
            print(f"    - {obs}")
        rev = review.get("market_position_revision")
        if rev is not None:
            if rev["proposed"]:
                print(f"  position : {len(rev['edits'])} revision(s) PROPOSED "
                      f"(human decides — never auto-applied):")
                for e in rev["edits"]:
                    print(f"    - {e['field']}: {e['suggestion']}")
            else:
                print("  position : no revision proposed")

    if args.write:
        print(f"written  : {write_review(args.project, review)}")
    return 0


def _cmd_publishing_sync_queue(args) -> int:
    """Spawn pending publish approval requests for publish-ready, not-yet-published
    chapters (M6). Idempotent — a chapter already carrying a request is skipped.
    Enqueues a decision to be made; it never publishes (ADR-009)."""
    from .publishing import sync_publish_requests
    from .inventory import load_published_log

    log = load_published_log(args.project)
    result = sync_publish_requests(args.project, published_log=log)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(f"publish queue sync — {len(result['created'])} new request(s), "
          f"{result['total_pending']} pending total")
    for rid in result["created"]:
        print(f"  + {rid}")
    if result["skipped_existing"]:
        print(f"  skipped (already queued): {len(result['skipped_existing'])}")
    if result["skipped_not_ready"]:
        print(f"  skipped (not publish-ready): {len(result['skipped_not_ready'])}")
    if result["published"]:
        print(f"  skipped (already published): {len(result['published'])}")
    if result["created"]:
        print("next: runtime approval list --project ... (then approve/reject)")
    return 0


def _add_publishing_command(sub) -> None:
    pp = sub.add_parser(
        "publishing",
        help="Publishing OS — Production Cards + Volume/Direction reviews (roadmap 4.6)")
    publishing_sub = pp.add_subparsers(dest="publishing_command", required=True)

    card = publishing_sub.add_parser(
        "card", help="build a per-chapter Production Card (cites publish-readiness)")
    card.add_argument("--project", required=True)
    card.add_argument("--chapter", required=True, help="chapter/task id, e.g. TASK-00001")
    card.add_argument("--json", action="store_true", help="emit the raw card as JSON")
    card.add_argument("--write", action="store_true",
                      help="persist under registry/derived/production-card/")
    card.set_defaults(func=_cmd_publishing_card)

    review = publishing_sub.add_parser(
        "review", help="build a Volume (~10ch) or Direction (~30ch) production review")
    review.add_argument("--project", required=True)
    review.add_argument("--scope", choices=("volume", "direction"), default="volume",
                        help="volume = 10-chapter 卷末复盘; direction = 30-chapter 大方向复盘 (proposes a positioning revision)")
    review.add_argument("--start", type=int, default=1,
                        help="1-based chapter index the window starts at (default 1)")
    review.add_argument("--size", type=int, default=None,
                        help="window size; defaults to the scope's nominal size (10/30)")
    review.add_argument("--standard-root", default=None,
                        help="Standard repo root; defaults to the sibling AI-Novel-Standard")
    review.add_argument("--json", action="store_true", help="emit the raw review as JSON")
    review.add_argument("--write", action="store_true",
                        help="persist under registry/derived/review-report/")
    review.set_defaults(func=_cmd_publishing_review)

    sync = publishing_sub.add_parser(
        "sync-queue",
        help="spawn pending publish approval requests for publish-ready chapters (M6; idempotent; never publishes)")
    sync.add_argument("--project", required=True)
    sync.add_argument("--json", action="store_true", help="emit the sync summary as JSON")
    sync.set_defaults(func=_cmd_publishing_sync_queue)


def _cmd_approval_list(args) -> int:
    """List approval requests (M6 audit ledger), optionally filtered by status
    and target type. Read-only view — a decision is recorded via approve/reject.
    Pending is the default view since that is the human's work queue."""
    from .approval import ApprovalStatus, load_approval_queue

    queue = load_approval_queue(args.project)
    status = args.status
    if status is None and not args.all:
        status = ApprovalStatus.PENDING.value
    requests = queue.list_requests(status=status, target_type=args.target_type)

    if not requests:
        scope = status or "any-status"
        print(f"no approval requests ({scope})")
        return 0

    print(f"approval requests — {len(requests)} shown "
          f"(status={status or 'any'}, target={args.target_type or 'any'}):")
    for r in sorted(requests, key=lambda x: x.id):
        print(f"  {r.id}  [{r.status}]  {r.target_type}/{r.action}  "
              f"→ {r.target_id}  ({r.reason})")
    return 0


def _cmd_approval_show(args) -> int:
    """Show one approval request plus the decision records made against it."""
    from .approval import load_approval_queue

    queue = load_approval_queue(args.project)
    request = queue.get_request(args.id)
    if request is None:
        print(f"approval request {args.id} not found")
        return 1

    if args.json:
        payload = {"request": request.to_dict(),
                   "records": [rec.to_dict() for rec in queue.records_for(args.id)]}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(f"{request.id}  [{request.status}]  (authority={request.authority})")
    print(f"  target : {request.target_type}/{request.action} → {request.target_id}")
    print(f"  reason : {request.reason}")
    print(f"  created: {request.created_at}   updated: {request.updated_at or request.created_at}")
    if request.requested_by:
        print(f"  by     : {request.requested_by}")
    records = queue.records_for(args.id)
    if records:
        print(f"  decisions ({len(records)}):")
        for rec in records:
            note = f" — {rec.notes}" if rec.notes else ""
            print(f"    {rec.id}  {rec.decision}  by {rec.decided_by}  at {rec.decided_at}{note}")
    else:
        print("  decisions: (none yet)")
    return 0


def _cmd_approval_decide(args, decision) -> int:
    """Record a human decision against a request and project it onto the request
    status. This is the audit ledger's write path; it does NOT execute the
    underlying action — crossing an ADR-009 boundary (mint/publish) still needs
    its own --confirm on that command."""
    from .approval import (
        ApprovalNotFound,
        ApprovalStateError,
        load_approval_queue,
        record_approval_decision,
    )

    queue = load_approval_queue(args.project)
    try:
        record = record_approval_decision(
            queue,
            request_id=args.id,
            decision=decision,
            decided_by=args.by,
            notes=args.notes or "",
        )
    except ApprovalNotFound:
        print(f"approval request {args.id} not found")
        return 1
    except ApprovalStateError as exc:
        print(f"refused: {exc}")
        return 1

    print(f"{record.decision}: {args.id} → {record.id} (by {record.decided_by})")
    return 0


def _cmd_approval_approve(args) -> int:
    from .approval import ApprovalDecision
    return _cmd_approval_decide(args, ApprovalDecision.APPROVED)


def _cmd_approval_reject(args) -> int:
    from .approval import ApprovalDecision
    return _cmd_approval_decide(args, ApprovalDecision.REJECTED)


def _cmd_approval_stats(args) -> int:
    """Aggregate counts across the approval ledger — totals by status and by
    target type. A run-through view of what is waiting and what has been decided."""
    from .approval import load_approval_queue

    queue = load_approval_queue(args.project)
    stats = queue.stats()
    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(f"approval ledger — {stats['total_requests']} request(s), "
          f"{stats['total_records']} decision record(s)")
    print("  by status:")
    for k, v in stats["by_status"].items():
        print(f"    {k}: {v}")
    print("  by target type:")
    for k, v in stats["by_target_type"].items():
        print(f"    {k}: {v}")
    return 0


def _cmd_signals_check(args) -> int:
    """Reader Signal Store (roadmap 5.6): validate + list REAL reader signals
    imported under sources/reader-signals/. Read-only, advisory — a signal is
    ground-truth DATA, not a build gate. NEVER calibrates the model."""
    from .signals import load_reader_signals, validate_signal

    signals = load_reader_signals(args.project)
    if not signals:
        print("no reader signals imported (sources/reader-signals/ is empty)")
        print("  a signal is real platform data (订阅/追读/掉粉); import one to compare vs predictions")
        return 0

    any_bad = False
    print(f"reader signals — {len(signals)} imported (advisory, never gates):")
    for s in signals:
        errs = validate_signal(s, standard_root=args.standard_root)
        scope = s.get("scope", "?")
        ident = s.get("chapter_id") if scope == "chapter" else "(book)"
        conf = (s.get("confidence") or {}).get("level", "?")
        if errs:
            any_bad = True
            print(f"  INVALID {ident} [{scope}] — {len(errs)} error(s):")
            for e in errs:
                print(f"    - {e}")
        else:
            m = s.get("metrics") or {}
            keys = ", ".join(f"{k}={v}" for k, v in m.items()) or "(no metrics)"
            print(f"  ok {ident} [{scope}] src={s.get('source','?')} "
                  f"conf={conf}  {keys}")
    return 1 if any_bad else 0


def _cmd_signals_compare(args) -> int:
    """Fold a chapter's REAL reader signal beside its PREDICTED reader-sim
    aggregate — comparison-only, never gates, never calibrates (roadmap 5.6). The
    predicted continue_rate may be supplied with --predicted-continue-rate (the
    commercial session persists deltas, not absolute aggregates); absent, it is a
    real-only readout."""
    from .signals import signal_for_chapter, reconcile_signal

    signal = signal_for_chapter(args.project, args.chapter)
    if signal is None:
        print(f"no chapter-scoped reader signal for {args.chapter!r} "
              f"(import one under sources/reader-signals/)")
        return 0

    predicted = None
    if args.predicted_continue_rate is not None:
        predicted = {"continue_rate": args.predicted_continue_rate}

    comparison = reconcile_signal(predicted, signal)
    if args.json:
        print(json.dumps(comparison, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(f"reader signal vs prediction — {args.chapter} "
          f"(comparison_only={comparison['comparison_only']}, "
          f"gating={comparison['gating']}, calibrates={comparison['calibrates']})")
    print(f"  source={comparison['source']} collected={comparison['collected_at']} "
          f"confidence={comparison['confidence']}")
    for c in comparison["comparisons"]:
        if c["gap"] is not None:
            print(f"  {c['metric']}: predicted {c['predicted']} vs real {c['real']} "
                  f"→ gap {c['gap']:+g} ({c['direction']})")
        else:
            print(f"  {c['metric']}: real {c['real']} ({c['direction']})")
    print(f"  note: {comparison['note']}")
    return 0


def _add_signals_command(sub) -> None:
    ps = sub.add_parser(
        "signals",
        help="Reader Signal Store — import REAL platform signals + compare vs predictions (roadmap 5.6; never gates, never calibrates)")
    signals_sub = ps.add_subparsers(dest="signals_command", required=True)

    check = signals_sub.add_parser(
        "check", help="validate + list reader signals under sources/reader-signals/ (advisory)")
    check.add_argument("--project", required=True)
    check.add_argument("--standard-root", default=None,
                       help="Standard repo root; defaults to the sibling AI-Novel-Standard")
    check.set_defaults(func=_cmd_signals_check)

    compare = signals_sub.add_parser(
        "compare",
        help="place a chapter's real signal beside its predicted simulation (comparison-only, never gates)")
    compare.add_argument("--project", required=True)
    compare.add_argument("--chapter", required=True, metavar="CHAPTER_ID",
                         help="the chapter/task id the signal is about")
    compare.add_argument("--predicted-continue-rate", type=int, default=None,
                         help="the predicted continue_rate to compare against real retention (optional)")
    compare.add_argument("--json", action="store_true", help="emit the raw comparison as JSON")
    compare.set_defaults(func=_cmd_signals_compare)


def _add_approval_command(sub) -> None:
    pa = sub.add_parser(
        "approval",
        help="Approval Queue — the M6 audit ledger of human decisions (view/decide; does NOT execute the underlying action)")
    approval_sub = pa.add_subparsers(dest="approval_command", required=True)

    ls = approval_sub.add_parser(
        "list", help="list approval requests (defaults to pending — the human work queue)")
    ls.add_argument("--project", required=True)
    ls.add_argument("--status", default=None,
                    help="filter by status (pending/approved/rejected/deferred/needs_more_info/executed/cancelled)")
    ls.add_argument("--target-type", default=None,
                    help="filter by target type (mint/publish/genesis/...)")
    ls.add_argument("--all", action="store_true",
                    help="show every status, not just pending")
    ls.set_defaults(func=_cmd_approval_list)

    show = approval_sub.add_parser(
        "show", help="show one request plus its decision records")
    show.add_argument("--project", required=True)
    show.add_argument("--id", required=True, help="the APR-##### request id")
    show.add_argument("--json", action="store_true", help="emit request + records as JSON")
    show.set_defaults(func=_cmd_approval_show)

    approve = approval_sub.add_parser(
        "approve", help="record an APPROVED decision (audit only; does not execute the action)")
    approve.add_argument("--project", required=True)
    approve.add_argument("--id", required=True, help="the APR-##### request id")
    approve.add_argument("--by", required=True, help="the deciding actor")
    approve.add_argument("--notes", default="", help="optional decision notes")
    approve.set_defaults(func=_cmd_approval_approve)

    reject = approval_sub.add_parser(
        "reject", help="record a REJECTED decision (audit only)")
    reject.add_argument("--project", required=True)
    reject.add_argument("--id", required=True, help="the APR-##### request id")
    reject.add_argument("--by", required=True, help="the deciding actor")
    reject.add_argument("--notes", default="", help="optional decision notes")
    reject.set_defaults(func=_cmd_approval_reject)

    stats = approval_sub.add_parser(
        "stats", help="aggregate counts by status and target type")
    stats.add_argument("--project", required=True)
    stats.add_argument("--json", action="store_true", help="emit the raw stats as JSON")
    stats.set_defaults(func=_cmd_approval_stats)


def _add_schedule_command(sub) -> None:
    ps = sub.add_parser(
        "schedule", help="Serialization schedule commands — backlog / break-risk / calendar (roadmap P17)")
    schedule_sub = ps.add_subparsers(dest="schedule_command", required=True)
    check = schedule_sub.add_parser(
        "check", help="project backlog / break-risk / update-calendar from sources/serial-plan.yaml (advisory)")
    check.add_argument("--project", required=True)
    check.add_argument("--standard-root", default=None,
                       help="Standard repo root; defaults to the sibling AI-Novel-Standard")
    check.add_argument("--today", default=None,
                       help="ISO date (YYYY-MM-DD) to project as of; defaults to the real today")
    check.add_argument("--days", type=int, default=7,
                       help="how many upcoming publish dates to list")
    check.set_defaults(func=_cmd_schedule_check)


def _cmd_serial_run(args) -> int:
    """Run the production chain over a planned chapter sequence, carrying state
    (a fold cursor) between chapters. Advisory — never gates the serial (ADR-003):
    a chapter that fails its own deterministic gate is skipped, the serial goes
    on (break/resume seed)."""
    _load_dotenv(args)
    from .serialize import run_serial

    # P0-1: Wire advanced check modules (makes them reachable from CLI).
    # These imports establish the import-graph path from cli.py to the modules,
    # satisfying the architecture fitness guard (test_fitness.py guard #26).
    # Actual integration into the production flow is staged separately.
    if getattr(args, "enable_advanced_checks", False):
        from . import (
            character_growth, character_arc_validator,
            commercial_constitution, constitution_validator,
            constitution_integration, constitution_aware_paywall,
            hook_enhanced, paywall_optimizer,
            promise_debt_tracker, reader_expectation,
            revision_task, world_consistency_checker
        )
        print("advanced checks modules loaded (P0-1 wiring)")

    # --preset 30ch selects a fixed 30-chapter launch profile. It sets the
    # production flags explicitly so the run is reproducible from a single name.
    if getattr(args, "preset", None) == "30ch":
        from .serialize.launch_30ch import build_30ch_run_preset
        preset = build_30ch_run_preset(
            project_path=args.project,
            standard_root=args.standard_root,
            model_provider=args.model_provider,
            model_id=args.model_id,
            budget_limit=args.budget_limit or 0.0,
        )
        args.max_chapters = preset["max_chapters"] if args.max_chapters is None else args.max_chapters
        args.long_arc = preset["long_arc"]
        args.vary_openings = preset["vary_openings"]
        args.mandate = preset["mandate"]
        args.speech = preset["speech"]
        if args.reviewer == "unanchored":
            args.reviewer = preset["reviewer"]
        if args.candidates == 1:
            args.candidates = preset["candidates"]
        if args.prompt_version == "6.0.0":
            args.prompt_version = preset["prompt_version"]

    # --genre-contract bumps to v14 (per-chapter genre contract: the discriminant
    # requirement the declared genre cannot lose + its degradation symptoms + the
    # book's own coined terms — genre-drift prevention, §4.3);
    # --meta-reference bumps to v13 (generation-side anti-leak guard over the
    # chapter body itself); --craft-texture bumps to v12 (measured prose-texture
    # constraints: no em-dash asides / sparse similes / dialogue-carried scenes —
    # the three defects the market anchor measured on the 30ch baseline);
    # --anti-anaphora bumps to v11 (within-chapter anti-anaphora, §14); --long-arc
    # bumps to v10 (long-arc coordinate per chapter, M3); --vary-openings
    # bumps to v9 (cross-chapter opening-diversity, §14 anti-AI prevention); --mandate
    # bumps to v8 (narrative mandate, the anti-流水账 layer); --speech bumps to v7
    # (per-character speech profiles). Higher wins:
    # v14 ⊃ v13 ⊃ v12 ⊃ v11 ⊃ v10 ⊃ v9 ⊃ v8 ⊃ v7
    # (each requires the lower's variables too). Resolved here so the whole command reads one version.
    if getattr(args, "genre_contract", False):
        prompt_version = "14.0.0"
    elif getattr(args, "meta_reference", False):
        prompt_version = "13.0.0"
    elif getattr(args, "craft_texture", False):
        prompt_version = "12.0.0"
    elif getattr(args, "anti_anaphora", False):
        prompt_version = "11.0.0"
    elif getattr(args, "long_arc", False):
        prompt_version = "10.0.0"
    elif getattr(args, "vary_openings", False):
        prompt_version = "9.0.0"
    elif getattr(args, "mandate", False):
        prompt_version = "8.0.0"
    elif getattr(args, "speech", False):
        prompt_version = "7.0.0"
    else:
        prompt_version = args.prompt_version

    schema_dir = (args.schema_dir if args.schema_dir
                  else str(Path(args.standard_root) / "phase-1" / "generated" / "json-schema"))
    out_dir = args.out if args.out else str(Path(args.project) / "build-serial")

    # The chapter GENERATION model. With a live provider, build the LLM adapter;
    # otherwise the serial falls back to the deterministic stub. (Previously this
    # was never built, so --model-provider was silently ignored for generation.)
    gen_model = None
    if args.model_provider not in ("deterministic",):
        gen_model = _build_llm_model(args, replay_suffix="gen")

    # C6 multi-version generation: --candidates N (>1) builds N generation models,
    # each with its OWN replay bucket and a stepped temperature, so a LIVE model
    # yields genuinely different drafts (identical requests otherwise hit the
    # replay cache and collapse to one draft). The director then picks the best by
    # reviewer score; only the winner is persisted. Needs a live provider (a
    # deterministic/mock model produces identical candidates → selection no-op →
    # byte-identical). Cost scales ~N×, so pair with --per-chapter-budget.
    candidate_models = None
    n_candidates = int(getattr(args, "candidates", 1) or 1)
    if n_candidates > 1:
        if args.model_provider in ("deterministic",):
            raise SystemExit("--candidates > 1 needs a live --model-provider (e.g. deepseek)")
        candidate_models = []
        base_temp = args.temperature if args.temperature is not None else 0.7
        for i in range(n_candidates):
            # step temperature (bounded to [0,1.3]) so candidates explore apart
            cargs = argparse.Namespace(**vars(args))
            cargs.temperature = max(0.0, min(1.3, base_temp + 0.15 * i))
            candidate_models.append(
                _build_llm_model(cargs, replay_suffix=f"cand{i}"))

    # Optional Prose Hygiene correction loop (§14.5) per chapter. A role-level
    # override lets a dedicated rewriter correct prose authored by another model.
    hygiene_model = None
    if getattr(args, "hygiene", False):
        hygiene_model = _build_role_model(
            args, getattr(args, "hygiene_model", None),
            option="--hygiene-model", replay_suffix="hygiene")

    # Per-chapter evaluative reviewer (ADR-003 advisory, never gates). A
    # --review-model override prevents the generation model from judging itself.
    # NEW: --quality-judge uses LLMQualityJudge (18 dimensions) instead of simple reviewer.
    reviewer = None
    if getattr(args, "quality_judge", False):
        # Use LLM quality judge (18 dimensions)
        from .execution.quality_center import llm_quality_judge
        judge_model = gen_model if gen_model is not None else _build_llm_model(args)
        reviewer = llm_quality_judge(judge_model)
        print("→ Using LLM quality judge (18 dimensions, evaluative)")
    elif getattr(args, "reviewer", "unanchored") == "unanchored":
        from .execution.draft_review import unanchored_entity_reviewer
        reviewer = unanchored_entity_reviewer()
    else:
        review_spec = getattr(args, "review_model", None)
        if review_spec:
            review_args = _role_model_args(
                args, review_spec, option="--review-model")
            reviewer = _make_reviewer(review_args, None)
        else:
            if args.model_provider in ("deterministic",):
                raise SystemExit(
                    f"--reviewer {args.reviewer} needs --review-model PROVIDER:MODEL "
                    "or a live --model-provider")
            reviewer = _make_reviewer(args, gen_model)

    # Optional LLM scene-plan enrichment. --scene-model can use a planning model
    # independently of the chapter author; without it the primary model is reused.
    scene_planner_model = None
    if getattr(args, "scene_planner", False) or getattr(args, "psych_beats", False):
        scene_planner_model = _build_role_model(
            args, getattr(args, "scene_model", None),
            option="--scene-model", replay_suffix="scene")

    # Optional Commercial Optimization Loop (P16), comparison-only and never a
    # build gate. Simulator and rewriter can now be independent model roles.
    simulator = rewrite_model = None
    if args.commercial:
        from .execution.reader_sim import (
            llm_reader_simulator, commercial_reader_simulator,
            DEFAULT_PERSONAS, DEFAULT_COMMERCIAL_PERSONAS)
        sim_model = _build_role_model(
            args, getattr(args, "commercial_sim_model", None),
            option="--commercial-sim-model", replay_suffix="sim")
        rewrite_model = _build_role_model(
            args, getattr(args, "rewrite_model", None),
            option="--rewrite-model", replay_suffix="rewrite")
        panel = getattr(args, "panel", "commercial")
        if panel == "appetite":
            simulator = llm_reader_simulator(sim_model)
        elif panel == "both":
            simulator = llm_reader_simulator(
                sim_model,
                personas=DEFAULT_PERSONAS + DEFAULT_COMMERCIAL_PERSONAS,
                reviewer_id="reader-simulator-v2-both")
        else:  # commercial (default) — the v2 pay-behavior panel
            simulator = commercial_reader_simulator(sim_model)

    # Auto-supply the outline genesis wrote (A.1): the serial's IR / scene-plan /
    # director objective (prompt v3+) are driven by the outline, but nothing fed
    # it in, so a genesis-opened book ran on event-only planning. Load the stable
    # derived outline unless --no-outline forces the old behavior. Missing/corrupt
    # degrades to None (event-only), never aborts — it's an enrich seam.
    outline = None
    if not getattr(args, "no_outline", False):
        from .outline.writer import load_project_outline
        outline = load_project_outline(args.project)
    if outline is not None:
        # M5 reference abstraction (Phase D): the standalone artifact is a runtime
        # sibling — it is NEVER persisted inside the frozen outline (outline.schema
        # is additionalProperties:false). We merge it onto the IN-MEMORY outline
        # here so the IR / long-arc / prompt-binding consumers (scene/ir.py,
        # arc/projection.py, prompt/binding.py) receive it on the REAL serial path,
        # while the outline on disk stays contract-clean. Absent artifact => key
        # simply absent => those consumers degrade cleanly (advisory, ADR-003).
        from .reference.abstract import load_reference_abstraction
        ref_abstract = load_reference_abstraction(args.project)
        if ref_abstract is not None:
            outline["reference_abstraction"] = ref_abstract
        print(f"outline    : {outline.get('id', 'OUTLINE-00001')} loaded "
              f"(drives IR/scene-plan/objective at prompt v3+)"
              + ("  +reference-abstraction" if ref_abstract is not None else ""))
    else:
        print("outline    : none on disk — chapters plan from events only")

    # M7 governance wiring (M8-01). The red-line gate runs on every chapter: load
    # the project's authored ruleset (falls back to the built-in default when the
    # project has none). Originality similarity is opt-in via --originality — it is
    # O(body·refs), so absent the flag the corpus is never loaded and the serial is
    # byte-identical. When either governance signal can recommend hold/block, an
    # ApprovalQueue is supplied so those chapters land on the human review queue
    # (ADR-009); the serial still never gates (ADR-003).
    from .execution.redline import load_ruleset
    redline_ruleset = load_ruleset(args.project)
    # Originality similarity is DEFAULT-ON when the project ships a reference
    # corpus (M1-B2): a reference-driven book should be checked against its
    # own sources on every chapter. It stays advisory (ADR-003) — a hold/block
    # recommendation is enqueued for human review (ADR-009), never gates. Absent
    # a corpus the check is a no-op (risk L0), so a book with no reference novels
    # is byte-identical. --no-originality forces it off (e.g. to skip the
    # O(body·refs) cost on a large corpus).
    originality_references = None
    if not getattr(args, "no_originality", False):
        from .outline.sources import load_reference_sources, iter_source_texts
        src = load_reference_sources(args.project)
        if not src.ok:
            # No corpus (or an invalid one) is not an error here: the serial
            # simply runs without the similarity arm. Only warn when the user
            # explicitly asked for it via --originality.
            if getattr(args, "originality", False):
                print(f"originality: reference load failed — {'; '.join(src.errors)}")
        else:
            originality_references = [
                {"source_id": s.id, "source_type": "reference_novel", "text": text}
                for s, text in iter_source_texts(args.project, src.sources)]
            print(f"originality: {len(originality_references)} reference novel(s) "
                  f"loaded for similarity check (default-on; --no-originality to skip)")
    from .approval import load_approval_queue
    approval_queue = load_approval_queue(args.project)

    # Stage A: Final Quality Review and Reader Simulation models
    # These are INDEPENDENT of per-chapter reviewer/simulator
    final_reviewer = None
    final_simulator = None

    if getattr(args, "enable_final_quality_review", False):
        # Stage A needs a SCORING judge (LLMQualityJudge), not a checker
        # The per-chapter reviewer (unanchored) doesn't produce scores
        # So we create a dedicated LLM quality judge for Stage A
        from .execution.quality_center import llm_quality_judge

        # Use the generation model for quality review (can be overridden later)
        review_model = gen_model if gen_model else None
        if review_model:
            final_reviewer = llm_quality_judge(
                review_model,
                reviewer_id="stage-a-quality-judge-v1"
            )
        else:
            import logging
            logging.warning("Stage A quality review enabled but no model available")

    if getattr(args, "enable_final_reader_simulation", False):
        # Create reader simulator if not already created for commercial optimization
        if simulator is None:
            from .execution.reader_sim import commercial_reader_simulator
            sim_model = gen_model if gen_model else None
            if sim_model:
                final_simulator = commercial_reader_simulator(sim_model)
            else:
                import logging
                logging.warning("Stage A reader simulation enabled but no model available")
        else:
            # Reuse existing simulator
            final_simulator = simulator

    from datetime import datetime, timezone
    started_at = datetime.now(timezone.utc).isoformat()
    result = run_serial(
        project_path=args.project,
        standard_root=args.standard_root,
        schema_dir=schema_dir,
        out_dir=out_dir,
        model=gen_model,
        reviewer=reviewer,
        simulator=simulator,
        rewrite_model=rewrite_model,
        commercial_rounds=args.commercial_rounds,
        prompt_version=prompt_version,
        max_chapters=args.max_chapters,
        start_chapter=getattr(args, "start_chapter", 1),
        rolling_plan_continuation=getattr(
            args, "rolling_plan_continuation", False),
        max_depth=args.max_depth,
        outline=outline,
        scene_planner_model=scene_planner_model,
        psych_beats=getattr(args, "psych_beats", False),
        hygiene_model=hygiene_model,
        hygiene_rounds=getattr(args, "hygiene_rounds", 2),
        redline_ruleset=redline_ruleset,
        originality_references=originality_references,
        approval_queue=approval_queue,
        budget_limit=getattr(args, "budget_limit", None),
        per_chapter_budget=getattr(args, "per_chapter_budget", None),
        candidate_models=candidate_models,
        w12_extract=getattr(args, "w12_extract", False),
        w12_model=(gen_model if getattr(args, "w12_extract", False) else None),
        contracts_dir=getattr(args, "contracts_dir", None),
        enable_contract_gate=getattr(args, "enable_contract_gate", False),
        strict_contract_mode=getattr(args, "strict_contract_mode", False),
        enable_final_quality_review=getattr(args, "enable_final_quality_review", False),
        final_review_threshold=getattr(args, "final_review_threshold", "always"),
        final_review_model=final_reviewer,
        enable_final_reader_simulation=getattr(args, "enable_final_reader_simulation", False),
        final_reader_threshold=getattr(args, "final_reader_threshold", "always"),  # Changed from commercial-revised
        final_reader_sim_model=final_simulator,
    )
    finished_at = datetime.now(timezone.utc).isoformat()

    for c in result.chapters:
        mark = "ok " if c.ok else "SKIP"
        line = (f"  [{mark}] ch{c.spec.index:>3} {c.spec.event_id} "
                f"stage={c.stage}")
        if c.ok:
            line += (f"  draft={c.draft_hash[:19]}  state={c.state_hash[:19]}  "
                     f"events={c.events_so_far} open_setups={c.open_setups}")
            if c.commercial_verdict:
                line += f"  commercial={c.commercial_verdict}"
            if c.hygiene:
                line += f"  hygiene={c.hygiene.get('verdict')}"
            if c.m7:
                line += f"  m7={c.m7.get('recommendation')}/{c.m7.get('risk_level')}"
                if c.m7_approval_id:
                    line += f"  approval={c.m7_approval_id}"
            if c.budget_note:
                line += f"  budget-capped"
            if c.w12:
                if c.w12.get("error"):
                    line += f"  w12=error"
                else:
                    line += (f"  w12={c.w12.get('candidate_count')}cand"
                             f"/{c.w12.get('approval_status')}")
            if c.contract_validation:
                if c.contract_validation.get("error"):
                    line += f"  contract=error"
                elif c.contract_validation.get("valid") is False:
                    issue_count = len(c.contract_validation.get("issues", []))
                    line += f"  contract=invalid({issue_count})"
                elif c.contract_validation.get("valid") is True:
                    line += f"  contract=ok"
        else:
            line += f"  ({c.message})"
        print(line)

    print(f"\nserial done — advisory, never gates (gating={result.gating})")
    print(f"  produced : {result.produced}")
    print(f"  skipped  : {result.skipped}")
    print(f"  final state_hash: {result.final_state_hash}")
    # 真花了钱却折不出金额时必须说出来:那意味着 --budget-limit 在这些调用上
    # 无效。此前这种情况完全静默(cost=None 被折成 0),已两次导致无预算保护的
    # 真实花费(deepseek-chat、92code:gpt-5.6-sol 各一次)。
    if getattr(result, "cost_warning", None):
        print(f"  ⚠️  成本告警: {result.cost_warning}")

    # Persist the run as an audit record (roadmap 5.5). Default-on, like the build
    # manifest; --no-manifest opts out. Folds cost/approvals from the drafts just
    # written; never gates, writes only to registry/derived/run-manifests/.
    if not getattr(args, "no_manifest", False):
        from .serialize import write_run_manifest, write_run_aggregate, write_30ch_run_summary
        role_models = {
            role: spec for role, spec in {
                "review": getattr(args, "review_model", None),
                "scene": getattr(args, "scene_model", None),
                "commercial_sim": getattr(args, "commercial_sim_model", None),
                "rewrite": getattr(args, "rewrite_model", None),
                "hygiene": getattr(args, "hygiene_model", None),
            }.items() if spec
        }
        params = {
            "prompt_version": prompt_version,
            "commercial": bool(args.commercial),
            "panel": getattr(args, "panel", None) if args.commercial else None,
            "model_provider": args.model_provider,
            "model_id": args.model_id if args.model_provider != "deterministic" else None,
            "max_chapters": args.max_chapters,
            "role_models": role_models,
        }
        manifest, rel = write_run_manifest(
            project_path=args.project, result=result, params=params,
            started_at=started_at, finished_at=finished_at)
        cost = manifest["totals"]["cost"]
        # "no live-model cost" 只在**真的没有调用模型**时才成立(确定性 stub)。
        # 有 live_calls 却折不出成本 = 模型未定价,真花了钱 —— 说成"无成本"
        # 是错的,那正是熔断器失效却看不出来的原因。
        if cost:
            cost_str = f"{cost['total_cost']} {cost['currency']}"
        elif manifest["totals"]["live_calls"]:
            cost_str = "cost UNKNOWN (模型未定价,非免费)"
        else:
            cost_str = "no live-model cost"
        print(f"  run manifest: {manifest['id']} → {rel}  "
              f"(live_calls={manifest['totals']['live_calls']}, {cost_str})")

        aggregate = write_run_aggregate(
            project_path=args.project,
            aggregate_id=manifest["id"],
            standard_root=args.standard_root,
            prompt_version=prompt_version,
            model_provider=args.model_provider,
            model_id=args.model_id if args.model_provider != "deterministic" else None,
            budget_limit=getattr(args, "budget_limit", None),
            launch_report_id=manifest["id"],
            run_manifest_ref=rel,
            notes=f"serial run aggregate for {manifest['id']}",
        )
        print(f"  run aggregate: {manifest['id']} → {aggregate}")

        if getattr(args, "preset", None) == "30ch":
            summary = write_30ch_run_summary(
                project_path=args.project,
                summary_id=manifest["id"],
                standard_root=args.standard_root,
                prompt_version=prompt_version,
                model_provider=args.model_provider,
                model_id=args.model_id if args.model_provider != "deterministic" else None,
                budget_limit=getattr(args, "budget_limit", None),
                launch_report_id=manifest["id"],
                run_manifest_ref=rel,
                notes=f"30ch summary for {manifest['id']}",
            )
            print(f"  30ch summary: {manifest['id']} → {summary}")
    return 0


def _run_serial_baseline(*, args, max_chapters: int, baseline_label: str,
                         baseline_id: str, notes_prefix: str) -> int:
    """Run a fixed live baseline and persist its audit artifacts."""
    _load_dotenv(args)
    from datetime import datetime, timezone
    from .serialize import (run_serial, write_run_manifest, write_run_aggregate,
                            build_precheck_environment, build_precheck_report,
                            write_live_baseline_report, build_baseline_freeze_record,
                            write_baseline_freeze_record, write_short_run_validation_report)
    prompt_version = args.prompt_version
    started_at = datetime.now(timezone.utc).isoformat()
    result = run_serial(
        project_path=args.project,
        standard_root=args.standard_root,
        schema_dir=(args.schema_dir or str(Path(args.standard_root) / "phase-1" / "generated" / "json-schema")),
        out_dir=(args.out or str(Path(args.project) / "build-serial")),
        model=_build_llm_model(args, replay_suffix="gen") if args.model_provider not in ("deterministic",) else None,
        reviewer=_make_reviewer(args, None),
        prompt_version=prompt_version,
        max_chapters=max_chapters,
        max_depth=args.max_depth,
        hygiene_model=None,
        scene_planner_model=None,
        budget_limit=args.budget_limit,
        per_chapter_budget=args.per_chapter_budget,
        candidate_models=None,
    )
    finished_at = datetime.now(timezone.utc).isoformat()
    params = {"prompt_version": prompt_version, "commercial": False, "panel": None,
              "model_provider": args.model_provider,
              "model_id": args.model_id if args.model_provider != "deterministic" else None,
              "max_chapters": max_chapters}
    manifest, rel = write_run_manifest(
        project_path=args.project, result=result, params=params,
        started_at=started_at, finished_at=finished_at)
    status = "passed" if result.produced == max_chapters and result.skipped == 0 else (
        "budget_held" if any(c.stage == "budget-held" for c in result.chapters) else "failed")
    env = build_precheck_environment(
        provider=args.model_provider, model=args.model_id,
        prompt_version=prompt_version, runtime_version="runtime")
    chapters = [c.to_dict() for c in result.chapters]
    failures = [c.to_dict() for c in result.chapters if not c.ok]
    report = build_precheck_report(
        project_path=args.project, status=status, environment=env, chapters=chapters,
        failures=failures, replay={"generation_records": 0, "replay_hits": 0, "live_calls": manifest["totals"]["live_calls"]},
        cost={"budget_limit": args.budget_limit, "actual_cost": (manifest["totals"]["cost"] or {}).get("total_cost", 0.0), "currency": (manifest["totals"]["cost"] or {}).get("currency", "CNY")},
        resume={"interrupted_after_chapter": None, "resumed": False, "duplicate_calls_detected": False},
        run_manifest=manifest, run_manifest_ref=rel)
    report["baseline_id"] = baseline_id
    report["run_summary"]["baseline_id"] = baseline_id
    rep_rel = write_live_baseline_report(project_path=args.project, report=report)
    print(f"{baseline_label}: {status}")
    print(f"  run manifest: {manifest['id']} → {rel}")
    print(f"  baseline rpt: {report['id']} → {rep_rel}")
    # Surface the folded quality result so the baseline reads on stdout, not only
    # in the JSON artifact. The integrity gate is the sole hard gate (ADR-003);
    # advisory flags are reported as flagged-chapter counts, never as a gate.
    q = report["quality_summary"]
    gate = q["integrity_gate"]
    print(f"  integrity gate: pass={gate['pass']} fail={gate['fail']} "
          f"review_required={gate['review_required']} not_assessed={gate['not_assessed']}")
    flagged = {name: c["flagged"] for name, c in q["advisory_flags"].items() if c["flagged"]}
    print(f"  advisory flags: {flagged or 'none'} (advisory, never gates)")
    if q["verdicts"]:
        print(f"  verdicts: {q['verdicts']}")
    freeze = build_baseline_freeze_record(
        baseline_id=baseline_id,
        chapter_ids=[c.spec.task_id for c in result.chapters],
        run_manifest_ref=rel,
        live_baseline_report_ref=rep_rel,
        prompt_version=prompt_version,
        replay_ref=rep_rel,
        quality_ref=rep_rel,
        provenance_ref=rel,
        notes=f"{status}; chapters={len(result.chapters)}; live_calls={manifest['totals']['live_calls']}",
    )
    freeze_rel = write_baseline_freeze_record(project_path=args.project, record=freeze)
    print(f"  baseline freeze: {freeze['kind']} v{freeze['version']} → {freeze_rel} "
          f"chapter_ids={','.join(freeze['chapter_ids'])}")
    snapshots = [c.quality_snapshot for c in result.chapters if getattr(c, "quality_snapshot", None)]
    if len(snapshots) >= 2:
        report_id = f"SRV-{manifest['id']}"
        report_rel = write_short_run_validation_report(
            project_path=args.project,
            report_id=report_id,
            snapshots=snapshots,
        )
        print(f"  short-run validation: {report_id} → {report_rel} snapshot_count={len(snapshots)}")
    aggregate = write_run_aggregate(
        project_path=args.project,
        aggregate_id=manifest["id"],
        standard_root=args.standard_root,
        prompt_version=prompt_version,
        model_provider=args.model_provider,
        model_id=args.model_id if args.model_provider != "deterministic" else None,
        budget_limit=args.budget_limit,
        launch_report_id=manifest["id"],
        run_manifest_ref=rel,
        notes=f"{notes_prefix} baseline aggregate for {manifest['id']}",
    )
    # write_run_aggregate returns the relative path (str); id is manifest["id"].
    print(f"  run aggregate: {manifest['id']} → {aggregate}")
    return 0 if status == "passed" else 1


def _cmd_serial_precheck(args) -> int:
    """Run the fixed 2-chapter live preflight and write audit artifacts."""
    from .serialize import PRECHECK_BASELINE_ID
    return _run_serial_baseline(
        args=args,
        max_chapters=2,
        baseline_label="precheck",
        baseline_id=PRECHECK_BASELINE_ID,
        notes_prefix="precheck",
    )


def _cmd_serial_freeze(args) -> int:
    """Run the fixed 3-chapter baseline freeze and write audit artifacts."""
    from .serialize import BASELINE_3CH_ID
    return _run_serial_baseline(
        args=args,
        max_chapters=3,
        baseline_label="baseline-freeze",
        baseline_id=BASELINE_3CH_ID,
        notes_prefix="freeze",
    )


def _cmd_serial_short_run(args) -> int:
    """Run a short 2- or 3-chapter verification run and write a validation report."""
    from .serialize import write_short_run_validation_report
    result = _run_serial_baseline(
        args=args,
        max_chapters=args.max_chapters,
        baseline_label="short-run",
        baseline_id=args.baseline_id,
        notes_prefix="short-run",
    )
    if hasattr(args, "write_validation_report") and args.write_validation_report and getattr(args, "project", None):
        # The baseline runner already persisted chapter-level snapshots on the chapters;
        # we only add a compact derived report here by summarizing the per-chapter quality
        # snapshots from the run output when available.
        return result
    return result


def _cmd_serial_validation_report(args) -> int:
    """Show a stored short-run validation report."""
    from .serialize import load_short_run_validation_report
    report = load_short_run_validation_report(args.project, args.report_id)
    if report is None:
        print("validation report: not found")
        return 2
    if getattr(args, "json", False):
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"validation report: {report['kind']} v{report['version']} id={args.report_id}")
    print(f"  verdict: {report.get('verdict')}")
    print(f"  chapters: {', '.join(report.get('chapter_ids') or [])}")
    print(f"  snapshot_count: {report.get('snapshot_count')}")
    return 0


def _cmd_serial_run_summary(args) -> int:
    """Show a stored 30ch run summary."""
    from .serialize import load_30ch_run_summary
    summary = load_30ch_run_summary(args.project, args.summary_id)
    if summary is None:
        print("run summary: not found")
        return 2
    if getattr(args, "json", False):
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"run summary: {summary['kind']} v{summary['version']} id={args.summary_id}")
    print(f"  notes: {summary.get('notes')}")
    return 0


def _cmd_serial_run_aggregate(args) -> int:
    """Show a stored run aggregate."""
    from .serialize import load_run_aggregate
    aggregate = load_run_aggregate(args.project, args.aggregate_id)
    if aggregate is None:
        print("run aggregate: not found")
        return 2
    if getattr(args, "json", False):
        print(json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"run aggregate: {aggregate['kind']} v{aggregate['version']} id={args.aggregate_id}")
    print(f"  project  : {aggregate.get('project_path')}")
    print(f"  summary  : {aggregate.get('run_summary', {}).get('kind')}")
    print(f"  hash     : {aggregate.get('content_hash')}")
    print(f"  notes    : {aggregate.get('notes')}")
    return 0


def _cmd_serial_inspect(args) -> int:
    """Inspect a serial-derived artifact by kind and id."""
    from .serialize import (load_30ch_launch_summary, load_run_aggregate,
                            load_short_run_validation_report, load_baseline_freeze_record,
                            load_run_manifest, load_rolling_plan)
    loaders = {
        "run-manifest": lambda project, artifact_id: load_run_manifest(project, artifact_id),
        "run-aggregate": lambda project, artifact_id: load_run_aggregate(project, artifact_id),
        "validation-report": lambda project, artifact_id: load_short_run_validation_report(project, artifact_id),
        "baseline-freeze": lambda project, artifact_id: load_baseline_freeze_record(project, artifact_id),
        "launch-summary": lambda project, artifact_id: load_30ch_launch_summary(project, artifact_id),
        # rolling-plan artifact_id is the checkpoint index (e.g. "10" / "020")
        "rolling-plan": lambda project, artifact_id: load_rolling_plan(project, int(str(artifact_id).lstrip("0") or "0")),
    }
    artifact = loaders[args.kind](args.project, args.artifact_id)
    if artifact is None:
        print(f"{args.kind}: not found")
        return 2
    if getattr(args, "json", False):
        print(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"{args.kind}: {artifact.get('kind')} v{artifact.get('version')} id={args.artifact_id}")
    if args.kind == "run-manifest":
        print(f"  status   : {artifact.get('run', {}).get('status', artifact.get('status'))}")
        print(f"  produced : {artifact.get('totals', {}).get('produced')}")
        print(f"  skipped  : {artifact.get('totals', {}).get('skipped')}")
    elif args.kind == "run-aggregate":
        print(f"  project  : {artifact.get('project_path')}")
        print(f"  summary  : {artifact.get('run_summary', {}).get('kind')}")
        print(f"  hash     : {artifact.get('content_hash')}")
    elif args.kind == "validation-report":
        print(f"  verdict  : {artifact.get('verdict')}")
        print(f"  chapters : {', '.join(artifact.get('chapter_ids') or [])}")
    elif args.kind == "baseline-freeze":
        print(f"  chapters : {', '.join(artifact.get('chapter_ids') or [])}")
        print(f"  run ref  : {artifact.get('run_manifest_ref')}")
    elif args.kind == "launch-summary":
        print(f"  plan     : {artifact.get('plan', {}).get('kind')}")
        print(f"  report   : {artifact.get('report', {}).get('kind')}")
        print(f"  link     : {artifact.get('link', {}).get('kind')}")
    return 0


def _cmd_reviewer_calibration_backfill(args) -> int:
    from .serialize.reviewer_calibration_cli import backfill_subset, backfill_all, show_results
    if args.action == "backfill":
        results = backfill_subset(args.project)
    elif args.action == "backfill-all":
        results = backfill_all(args.project)
    else:
        results = show_results(args.project)
        if getattr(args, "json", False):
            print(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        print(f"reviewer calibration results: {results.get('status')}")
        print(f"  sample_count: {results.get('sample_count')}")
        print(f"  report_hash  : {results.get('report', {}).get('content_hash')}")
        return 0
    print(f"reviewer calibration backfill: {results['status']}")
    print(f"  sample_count: {results['sample_count']}")
    print(f"  content_hash : {results['content_hash']}")
    print(f"  report       : {results['report']['content_hash']}")
    print(f"  trusted dims  : {', '.join(results['report']['trusted_dimensions']) or '(none)'}")
    if results['report']['missing_subset_ids']:
        print(f"  missing      : {', '.join(results['report']['missing_subset_ids'])}")
    return 0


def _cmd_reviewer_calibration_summary(args) -> int:
    from .serialize import (
        build_w9_summary,
        render_w9_summary_markdown,
        write_w9_summary,
        write_w9_summary_markdown,
    )
    summary = build_w9_summary(args.project)
    if getattr(args, "write", False):
        path = write_w9_summary(args.project)
        print(f"written: {path}")
    if getattr(args, "report", False):
        report_path = write_w9_summary_markdown(args.project)
        print(f"report : {report_path}")
    if getattr(args, "json", False):
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if getattr(args, "report_only", False):
        print(render_w9_summary_markdown(args.project), end="")
        return 0
    print(f"reviewer calibration summary: {summary.get('status')}")
    print(f"  sample_count: {summary.get('sample_count')}")
    print(f"  real        : {summary.get('real_sample_count')}")
    print(f"  skeleton    : {summary.get('skeleton_seed_count')}")
    print(f"  boundary    : {summary.get('boundary', {}).get('boundary_sample_count')}")
    for dim, stat in (summary.get('dimension_stats') or {}).items():
        print(f"  {dim}: n={stat['sample_count']} r={stat['correlation']} mae={stat['mean_abs_error']} ci95={stat['ci95_half_width']}")
    return 0
    if artifact is None:
        print(f"{args.kind}: not found")
        return 2
    if getattr(args, "json", False):
        print(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"{args.kind}: {artifact.get('kind')} v{artifact.get('version')} id={args.artifact_id}")
    if args.kind == "run-manifest":
        print(f"  status   : {artifact.get('run', {}).get('status', artifact.get('status'))}")
        print(f"  produced : {artifact.get('totals', {}).get('produced')}")
        print(f"  skipped  : {artifact.get('totals', {}).get('skipped')}")
    elif args.kind == "run-aggregate":
        print(f"  project  : {artifact.get('project_path')}")
        print(f"  summary  : {artifact.get('run_summary', {}).get('kind')}")
        print(f"  hash     : {artifact.get('content_hash')}")
    elif args.kind == "validation-report":
        print(f"  verdict  : {artifact.get('verdict')}")
        print(f"  chapters : {', '.join(artifact.get('chapter_ids') or [])}")
    elif args.kind == "baseline-freeze":
        print(f"  chapters : {', '.join(artifact.get('chapter_ids') or [])}")
        print(f"  run ref  : {artifact.get('run_manifest_ref')}")
    elif args.kind == "launch-summary":
        print(f"  plan     : {artifact.get('plan', {}).get('kind')}")
        print(f"  report   : {artifact.get('report', {}).get('kind')}")
        print(f"  link     : {artifact.get('link', {}).get('kind')}")
    elif args.kind == "rolling-plan":
        print(f"  checkpoint    : {artifact.get('checkpoint')}")
        print(f"  current chap  : {artifact.get('current_chapter')}")
        print(f"  active goals  : {len(artifact.get('active_goals') or [])}")
        print(f"  preview goals : {len(artifact.get('preview_goals') or [])}")
        print(f"  change records: {len(artifact.get('change_records') or [])}")
        print(f"  hash          : {artifact.get('content_hash')}")
    return 0


def _cmd_serial_baseline_compare(args) -> int:
    """Compare two frozen baselines and persist the diff as a derived report."""
    from .serialize import compare_and_write_baseline_report, compare_baseline_freeze_paths
    cmp = compare_baseline_freeze_paths(args.project, args.left_id, args.right_id)
    if cmp is None:
        print("baseline comparison: missing left or right baseline")
        return 2
    report_id = args.report_id or f"BCR-{args.left_id}-{args.right_id}"
    written = compare_and_write_baseline_report(
        project_path=args.project,
        left_id=args.left_id,
        right_id=args.right_id,
        report_id=report_id,
    )
    if written is None:
        print("baseline comparison: missing left or right baseline")
        return 2
    report, rel = written
    cmp = report["comparison"]
    if getattr(args, "json", False):
        out = dict(report)
        out["derived_path"] = rel
        print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"baseline comparison report: {report_id} -> {rel}")
    print(f"baseline comparison: {cmp['left']['baseline_id']} -> {cmp['right']['baseline_id']} ")
    print(f"  chapter_count: {cmp['left']['chapter_count']} -> {cmp['right']['chapter_count']} (delta={cmp['delta_chapter_count']})")
    print(f"  same_content_hash: {cmp['same_content_hash']}")
    print(f"  same_run_manifest_ref: {cmp['same_run_manifest_ref']}")
    print(f"  same_report_ref: {cmp['same_report_ref']}")
    if cmp.get("shared_chapter_ids"):
        print(f"  shared_chapter_ids: {', '.join(cmp['shared_chapter_ids'])}")
    return 0


def _cmd_serial_pipeline(args) -> int:
    """Print the book-level pipeline stage of every chapter (M8-01). Folds the
    draft index + envelope publish_readiness/M7 + approval queue + published log
    into ONE view. Pure projection; advisory, never gates (ADR-003)."""
    from .serialize import project_pipeline
    report = project_pipeline(args.project)
    if getattr(args, "json", False):
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    by = report.by_stage
    print(f"pipeline — {report.total} chapter(s), advisory (gating={report.gating})")
    print(f"  drafted={by['drafted']}  reviewed={by['reviewed']}  "
          f"assessed={by['assessed']}  approved={by['approved']}  "
          f"published={by['published']}")
    print(f"  blocked={report.blocked}  awaiting_approval={report.awaiting_approval}")
    for c in report.chapters:
        line = f"  {c['task_id']:<16} stage={c['stage']}"
        if c.get("publish_recommendation"):
            line += f"  publish={c['publish_recommendation']}"
        if c.get("m7_risk_level"):
            line += f"  m7={c['m7_risk_level']}"
        if c.get("approval_status"):
            line += f"  approval={c['approval_status']}"
        if c.get("blocked"):
            line += "  [BLOCKED]"
        print(line)
    return 0


def _cmd_serial_long_run_audit(args) -> int:
    """Fold CI-M5 admission/completion evidence without starting model calls."""
    from .serialize.long_run_acceptance import (
        build_long_run_acceptance_audit,
        write_long_run_acceptance_audit,
    )
    report = build_long_run_acceptance_audit(
        project_path=args.project,
        run_id=args.run_id,
        protocol_path=args.protocol,
        ledger_path=args.ledger,
        gate_30_path=args.gate_30,
        gate_60_path=args.gate_60,
        recovery_audit_path=args.recovery_audit,
        baseline_path=args.baseline,
    )
    out = Path(args.out or Path(args.project) / "analysis" / "ci-m5-long-run-audit.json")
    write_long_run_acceptance_audit(out, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"CI-M5 long-run audit: {report['status']}")
        print(f"  run                  : {report.get('run_id') or 'missing'}")
        print(f"  ready for 31-60      : {report['ready_for_31_60']}")
        print(f"  ready for 61-100     : {report['ready_for_61_100']}")
        print(f"  complete 100         : {report['complete_100']}")
        print(f"  produced / skipped   : {report['observed']['produced']} / {report['observed']['skipped']}")
        print(f"  report               : {out}")
        failed = [
            item for section in ("admission_checks", "sixty_chapter_checks", "completion_checks")
            for item in report[section] if not item["passed"]
        ]
        for item in failed:
            print(f"  HOLD {item['check_id']}: {item['detail']}")
    return 0


def _cmd_serial_long_run_freeze(args) -> int:
    """Freeze CI-M5's run config and fold the selected run into one evidence ledger."""
    from .serialize.chapter_evidence_ledger import (
        build_chapter_evidence_ledger,
        write_chapter_evidence_ledger,
    )
    from .serialize.experiment_protocol import (
        build_experiment_protocol,
        write_experiment_protocol,
    )

    project = Path(args.project)
    project_id_path = project / "registry" / "_meta" / "project-id"
    project_id = (
        project_id_path.read_text(encoding="utf-8").strip()
        if project_id_path.is_file() else project.name)
    standard_pin = project / "registry" / "_meta" / "standard.pin"
    standard_version = (
        standard_pin.read_text(encoding="utf-8").strip()
        if standard_pin.is_file() else "unknown")
    role_models = {
        role: spec for role, spec in {
            "review": args.review_model,
            "scene": args.scene_model,
            "hygiene": args.hygiene_model,
        }.items() if spec
    }
    protocol = build_experiment_protocol(
        protocol_id=args.protocol_id,
        project_id=project_id,
        model_provider=args.model_provider,
        model_id=args.model_id,
        prompt_version=args.prompt_version,
        prompt_bundle_ref=(
            f"AI-Novel-Standard/contracts/prompts/chapter-draft.v"
            f"{args.prompt_version.split('.', 1)[0]}.prompt.yaml"),
        schema_ref=f"AI-Novel-Standard@{standard_version}",
        budget_limit_cny=args.budget_limit_cny,
        temperature_contract={
            "temperature": args.temperature,
            "top_p": args.top_p,
        },
        max_output_tokens=args.max_output_tokens,
        role_models=role_models,
        reviewer_policy={
            "human_review_required": True,
            "human_checkpoints": [30, 60, 100],
            "llm_review_is_advisory": True,
            "review_model": args.review_model,
            "tie_break": "human",
        },
        notes=args.notes,
    )
    out_dir = Path(args.out_dir or project / "registry" / "derived" / "experiment-protocols")
    protocol_path = out_dir / f"{args.protocol_id}.json"
    write_experiment_protocol(protocol_path, protocol)

    run_ids = list(args.run_id)
    manifests = []
    for run_id in run_ids:
        manifest_path = (
            project / "registry" / "derived" / "run-manifests" / f"{run_id}.json")
        try:
            manifests.append(json.loads(manifest_path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            raise SystemExit(f"cannot load run manifest {run_id}: {exc}")
    from .serialize.long_run_acceptance import _combine_manifests
    run_manifest, chain_ok, chain_detail = _combine_manifests(manifests)
    if not chain_ok:
        raise SystemExit(f"invalid long-run chain: {chain_detail}")
    ledger = build_chapter_evidence_ledger(
        project_path=project,
        run_manifest=run_manifest,
        protocol=protocol,
    )
    ledger_path = project / "analysis" / "ci-m5-chapter-evidence-ledger.json"
    write_chapter_evidence_ledger(ledger_path, ledger)
    print(json.dumps({
        "kind": "long_run_freeze_result",
        "protocol_id": protocol["protocol_id"],
        "protocol_hash": protocol["content_hash"],
        "protocol_path": str(protocol_path),
        "ledger_path": str(ledger_path),
        "ledger_hash": ledger["content_hash"],
        "chapter_count": ledger["chapter_count"],
        "run_ids": run_ids,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _cmd_serial_frozen_rejudge(args) -> int:
    """Review persisted prose only; never invoke the generation path."""
    _load_dotenv(args)
    from .serialize.frozen_rejudge import rejudge_frozen_chapters
    model = _build_role_model(
        args, args.review_model, option="--review-model", replay_suffix="frozen-review")
    result = rejudge_frozen_chapters(
        project_path=args.project, package_dir=args.package_dir, model=model,
        start_chapter=args.start_chapter, end_chapter=args.end_chapter)
    out = Path(args.out or Path(args.project) / "analysis" /
               f"frozen-rejudge-{args.start_chapter:03d}-{args.end_chapter:03d}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["n_degraded"] else 0


def _workflow_scheduler_from_args(args, *, batch_runs=None):
    from .serialize import workflow_scheduler
    standard_root = Path(args.standard_root)
    return workflow_scheduler(
        project_path=args.project,
        standard_root=standard_root,
        schema_dir=args.schema_dir or standard_root / "phase-1" / "generated" / "json-schema",
        out_dir=args.out or Path(args.project) / "build-serial",
        prompt_version=args.prompt_version,
        max_chapters=args.max_chapters,
        reviewer_id=args.reviewer_id,
        outline=None,
        batch_runs=batch_runs,
    )


def _cmd_workflow_start(args) -> int:
    scheduler = _workflow_scheduler_from_args(args)
    result = scheduler.start(args.run_id)
    manifest = scheduler.store.load(args.run_id)
    print(f"workflow start: {args.run_id}")
    print(f"  status : {manifest.status}")
    print(f"  cursor : {manifest.cursor}")
    print(f"  done   : {len(manifest.completed_chapters)}")
    print(f"  failed : {len(manifest.failed_chapters)}")
    print(f"  result : produced={result.produced} skipped={result.skipped}")
    return 0


def _cmd_workflow_resume(args) -> int:
    scheduler = _workflow_scheduler_from_args(args)
    result = scheduler.resume(args.run_id)
    manifest = scheduler.store.load(args.run_id)
    print(f"workflow resume: {args.run_id}")
    print(f"  status : {manifest.status}")
    print(f"  cursor : {manifest.cursor}")
    print(f"  done   : {len(manifest.completed_chapters)}")
    print(f"  failed : {len(manifest.failed_chapters)}")
    print(f"  result : produced={result.produced} skipped={result.skipped}")
    return 0


def _cmd_workflow_status(args) -> int:
    scheduler = _workflow_scheduler_from_args(args)
    manifest = scheduler.store.load(args.run_id)
    print(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _cmd_workflow_batch(args) -> int:
    runs = [r.strip() for r in args.run_ids.split(",") if r.strip()]
    scheduler = _workflow_scheduler_from_args(args, batch_runs=runs)
    audit = scheduler.run_batch()
    print(json.dumps({"batch": audit}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _add_workflow_command(sub) -> None:
    pw = sub.add_parser("workflow", help="WorkflowScheduler commands — checkpoint/resume orchestration (M4)")
    wsub = pw.add_subparsers(dest="workflow_command", required=True)
    for name, handler in (("start", _cmd_workflow_start), ("resume", _cmd_workflow_resume), ("status", _cmd_workflow_status)):
        sp = wsub.add_parser(name)
        sp.add_argument("--project", required=True)
        sp.add_argument("--standard-root", required=True)
        sp.add_argument("--schema-dir", default=None)
        sp.add_argument("--out", default=None)
        sp.add_argument("--run-id", required=True)
        sp.add_argument("--prompt-version", default="1.0.0")
        sp.add_argument("--max-chapters", type=int, default=None)
        sp.add_argument("--reviewer-id", default="serial-v1")
        sp.set_defaults(func=handler)

    batch = wsub.add_parser("batch")
    batch.add_argument("--project", required=True)
    batch.add_argument("--standard-root", required=True)
    batch.add_argument("--schema-dir", default=None)
    batch.add_argument("--out", default=None)
    batch.add_argument("--run-ids", required=True, help="comma-separated run ids")
    batch.add_argument("--prompt-version", default="1.0.0")
    batch.add_argument("--max-chapters", type=int, default=None)
    batch.add_argument("--reviewer-id", default="serial-v1")
    batch.set_defaults(func=_cmd_workflow_batch)


def _add_serial_command(sub) -> None:
    pr = sub.add_parser(
        "serial", help="continuous serial production — the P14+P15 chain over many chapters (P17 seed)")
    serial_sub = pr.add_subparsers(dest="serial_command", required=True)
    run = serial_sub.add_parser(
        "run", help="run build->execute(Brain)->project-state per chapter, carrying state (advisory)")
    run.add_argument("--project", required=True)
    run.add_argument("--standard-root", required=True)
    run.add_argument("--schema-dir", default=None,
                     help="schema dir; defaults to <standard-root>/phase-1/generated/json-schema")
    run.add_argument("--out", default=None,
                     help="build output dir; defaults to <project>/build-serial")
    run.add_argument("--preset", choices=("30ch",), default=None,
                     help="apply a named run preset (e.g. 30ch fixed launch profile)")
    run.add_argument("--max-chapters", type=int, default=None,
                     help="cap the number of chapters produced")
    run.add_argument("--start-chapter", type=int, default=1,
                     help="first real chapter number to produce; existing earlier chapters are untouched")
    run.add_argument(
        "--rolling-plan-continuation", action="store_true",
        help="derive one 10-chapter continuation window from the rolling plan at the preceding "
             "checkpoint; the last minted event remains the Fact state anchor")
    run.add_argument("--max-depth", type=int, default=2)
    run.add_argument("--prompt-version", default="6.0.0",
                     help="chapter-draft prompt version. Default 6.0.0 runs the full stack "
                          "(director objective + chapter-IR + scene-plan + character-runtime). "
                          "1.0.0 = bare draft; 2.0.0 = +story-so-far recap; 7.0.0 = +speech profiles "
                          "(use --speech); 8.0.0 = +narrative mandate (use --mandate, the anti-流水账 "
                          "layer: why-now / escalation ladder / inner shift / net advance)")
    run.add_argument("--speech", action="store_true",
                     help="bump to prompt 7.0.0 (adds per-character speech profiles); "
                          "needs an authored sources/character-speech-profiles.yaml, else v7 ≈ v6")
    run.add_argument("--mandate", action="store_true",
                     help="bump to prompt 8.0.0 (adds the cross-chapter narrative mandate: "
                          "why this chapter must happen now, how far conflict escalates, how the "
                          "protagonist changes inside, what irreversible advance it commits); "
                          "folds from the outline's per-chapter beats, else degrades to v7 behavior")
    run.add_argument("--vary-openings", action="store_true", dest="vary_openings",
                     help="bump to prompt 9.0.0 (adds the cross-chapter opening-diversity "
                          "constraint, §14 anti-AI: shows the model recent chapter openings so "
                          "this chapter enters differently); wins over --mandate/--speech (v9 ⊃ v8 ⊃ v7)")
    run.add_argument("--long-arc", action="store_true", dest="long_arc",
                     help="bump to prompt 10.0.0 (adds each chapter's long-arc coordinate, M3: "
                          "which volume, distance to the volume climax, expected power tier, "
                          "conflict pressure, paywall/milestone); wins over --vary-openings (v10 ⊃ v9)")
    run.add_argument("--anti-anaphora", action="store_true", dest="anti_anaphora",
                     help="bump to prompt 11.0.0 (adds the within-chapter anti-anaphora "
                          "constraint, §14: never begin 3+ consecutive sentences with the same "
                          "word/subject 他…他…他; drop the pro-drop subject or vary the entrance); "
                          "wins over --long-arc (v11 ⊃ v10, requires the same variables)")
    run.add_argument("--genre-contract", action="store_true", dest="genre_contract",
                     help="bump to prompt 14.0.0 (adds the per-chapter GENRE CONTRACT: the one "
                          "discriminant requirement the declared genre cannot lose, its "
                          "degradation symptoms, and the book's own coined terms — prevention for "
                          "the genre drift where 异世大陆/武侠/仙侠/高武 slide toward generic 玄幻; "
                          "wins over --meta-reference (v14 ⊃ v13)")
    run.add_argument("--meta-reference", action="store_true", dest="meta_reference",
                     help="bump to prompt 13.0.0 (adds the generation-side anti-leak guard: never "
                          "echo chapter/outline/workflow meta into the story world; wins over "
                          "--craft-texture (v13 ⊃ v12, same variables)")
    run.add_argument("--craft-texture", action="store_true", dest="craft_texture",
                     help="bump to prompt 12.0.0 (adds the measured prose-texture constraints: "
                          "no em-dash asides, sparse similes, dialogue-carried scenes — the three "
                          "defects the market anchor measured on the 30ch baseline at 26/30, 22/30 "
                          "and 9/30); wins over --anti-anaphora (v12 ⊃ v11, same variables)")
    run.add_argument("--no-outline", action="store_true",
                     help="ignore the genesis outline on disk; plan chapters from events only (old behavior)")
    run.add_argument("--env-file", default=None)
    # Optional Commercial Optimization Loop (P16) per chapter — comparison-only,
    # never gates. Needs a live model provider for the reader-sim + rewriter.
    run.add_argument("--commercial", action="store_true",
                     help="run the Commercial Optimization Loop per chapter (P16, comparison-only)")
    run.add_argument("--commercial-rounds", type=int, default=2,
                     help="max commercial rewrite rounds per chapter (advisory)")
    # Optional Prose Hygiene correction loop (§14.5) per chapter — turns the
    # deterministic density + ai_taste warnings into a targeted rewrite. Needs a
    # live model provider for the rewriter. Never gates.
    run.add_argument("--hygiene", action="store_true",
                     help="run the Prose Hygiene correction loop per chapter (§14.5, deterministic re-check)")
    run.add_argument("--hygiene-rounds", type=int, default=2,
                     help="max prose-hygiene rewrite rounds per chapter (advisory)")
    run.add_argument("--scene-planner", action="store_true",
                     help="LLM-enrich each scene plan (pov/emotion/beats_within); needs a live provider")
    run.add_argument("--psych-beats", action="store_true",
                     help="hand the character-runtime psych block to the scene enricher so it lands "
                          "each lead's inner state as concrete in-scene actions (§12.1 ② follow-up); "
                          "implies --scene-planner, needs a live provider")
    run.add_argument("--panel", choices=("appetite", "commercial", "both"),
                     default="commercial",
                     help="reader panel for --commercial: appetite (v1 6 personas), "
                          "commercial (v2 6 pay-behavior personas, default), or both (12)")
    run.add_argument("--w12-extract", action="store_true", dest="w12_extract",
                     help="after each chapter, run W12 fact-candidate reflow on its prose: "
                          "extract candidates, reconcile vs registry, stage a plan + approval "
                          "request. STAGES only — never mints (ADR-009), never gates (ADR-003). "
                          "Uses the deterministic extractor unless --model-provider is live.")
    run.add_argument("--enable-contract-gate", action="store_true", dest="enable_contract_gate",
                     help="enable Contract Gate (Phase 3): verify each chapter against its "
                          "authored contract before generation (precheck) and after production "
                          "(validation). Only activates with --prompt-version 15.0.0. Precheck "
                          "skips chapters without valid contracts (ADR-003: never kills the serial). "
                          "Post-generation validation is advisory only, never gates.")
    run.add_argument("--contracts-dir", default=None, metavar="PATH",
                     help="directory containing chapter contract files (chapter_N_contract.json). "
                          "Defaults to PROJECT/contracts. Only used when --enable-contract-gate is set.")
    run.add_argument("--quality-judge", action="store_true",
                     help="Use LLM quality judge (18 dimensions) instead of simple reviewer (requires live model)")
    run.add_argument("--strict-contract-mode", action="store_true", dest="strict_contract_mode",
                     help="strict Contract Gate mode: precheck failures raise exceptions instead of "
                          "skipping chapters. Use with caution — can abort the serial mid-run. "
                          "Only meaningful with --enable-contract-gate.")
    run.add_argument("--reviewer", choices=("unanchored", "llm-quality", "panel"),
                     default="unanchored",
                     help=("per-chapter evaluative reviewer (ADR-003 advisory, never gates): "
                           "unanchored=deterministic proper-noun anchor check (default, no LLM cost); "
                           "llm-quality=Novel Quality Center 18-dim judge (+1 LLM call/chapter); "
                           "panel=multi-model review panel (+N LLM calls/chapter). "
                           "A scoring reviewer feeds the cross-chapter quality verdict."))
    run.add_argument("--panel-roles", default="literary,structural,commercial,logic",
                     help="comma-separated panel roles when --reviewer panel")
    run.add_argument("--model-provider", default="deterministic",
                     help="primary chapter-generation provider; also the fallback for roles without an override")
    run.add_argument("--model-id", default="deepseek-v4-pro",
                     help="primary chapter-generation model id")
    run.add_argument("--review-model", default=None, metavar="PROVIDER:MODEL",
                     help="independent llm-quality/panel reviewer; defaults to the generation model")
    run.add_argument("--scene-model", default=None, metavar="PROVIDER:MODEL",
                     help="scene-plan/psych-beat enricher; defaults to the generation model")
    run.add_argument("--commercial-sim-model", default=None, metavar="PROVIDER:MODEL",
                     help="commercial reader simulator; defaults to the generation model")
    run.add_argument("--rewrite-model", default=None, metavar="PROVIDER:MODEL",
                     help="commercial rewrite model; defaults to the generation model")
    run.add_argument("--hygiene-model", default=None, metavar="PROVIDER:MODEL",
                     help="prose-hygiene rewrite model; defaults to the generation model")
    run.add_argument("--temperature", type=float, default=0.7)
    run.add_argument("--top-p", type=float, default=None)
    run.add_argument("--max-tokens", type=int, default=None)
    run.add_argument("--timeout", type=float, default=120)
    run.add_argument("--replay-dir", default=None)
    run.add_argument("--budget-limit", type=float, default=None,
                     help="maximum cumulative live-model cost in the provider currency; hold remaining chapters once reached")
    run.add_argument("--per-chapter-budget", type=float, default=None,
                     help="maximum live-model cost for a SINGLE chapter (provider currency). Once a "
                          "chapter's generation cost reaches this, its optional enhancement loops "
                          "(commercial, hygiene) are skipped for that chapter — the base draft is "
                          "kept, the serial never gates (ADR-003). Bounds per-chapter spend the "
                          "run-level --budget-limit cannot (M4-B4)")
    run.add_argument("--candidates", type=int, default=1,
                     help="C6 multi-version generation: generate N candidate drafts per chapter "
                          "(each with its own replay bucket + stepped temperature), then the director "
                          "selects the highest-reviewer-score winner; only the winner is persisted, "
                          "losers ride the version-comparison lineage. Needs a live --model-provider; "
                          "cost scales ~N×, so pair with --per-chapter-budget. Default 1 (single draft, "
                          "byte-identical to before)")
    run.add_argument("--no-manifest", action="store_true",
                     help="skip writing the Production Run Manifest audit record (roadmap 5.5; written by default)")
    run.add_argument("--originality", action="store_true",
                     help="DEPRECATED (now default-on when a reference corpus exists, M1-B2): "
                          "kept for compatibility. Use --no-originality to disable. Warns if the "
                          "corpus fails to load.")
    run.add_argument("--no-originality", action="store_true",
                     help="skip the M7 originality similarity check even when the project ships a "
                          "sources/reference-novels corpus (M1-B2). The check is O(body·refs) and "
                          "default-on otherwise. The M7 red-line gate always runs regardless; a "
                          "hold/block recommendation is enqueued for human review (ADR-009), never "
                          "gates (ADR-003)")
    # Stage A: Final Draft Quality & Reader Simulation (Phase 2 & 3)
    run.add_argument("--enable-final-quality-review", action="store_true",
                     dest="enable_final_quality_review",
                     help="Stage A Phase 2: re-run Quality Center on the FINAL draft (after all "
                          "modifications: revision + commercial + hygiene) to track quality changes. "
                          "Advisory only, never gates (ADR-003). Adds LLM cost but provides true "
                          "quality delta tracking for Production Card")
    run.add_argument("--final-review-threshold", default="always",
                     choices=["always", "contract-warning", "quality-drop", "critical-only"],
                     help="When --enable-final-quality-review is set, controls which chapters get "
                          "re-reviewed: always (all chapters), contract-warning (only chapters with "
                          "contract deviations), quality-drop (initial score < 75), critical-only "
                          "(milestone chapters: 1,10,20,30,50,100). Default: always")
    run.add_argument("--enable-final-reader-simulation", action="store_true",
                     dest="enable_final_reader_simulation",
                     help="Stage A Phase 3: re-run reader simulation on the FINAL draft (after "
                          "commercial optimization) to detect new dropout risks introduced by "
                          "modifications. Runs standalone (no --commercial needed). Advisory only, "
                          "never gates (ADR-003)")
    run.add_argument("--final-reader-threshold", default="always",
                     choices=["always", "commercial-revised", "dropout-risk"],
                     help="When --enable-final-reader-simulation is set, controls which chapters "
                          "get re-simulated: always (all chapters), commercial-revised (only if "
                          "commercial optimization made changes), dropout-risk (only if initial "
                          "simulation showed risk). Default: always")
    run.set_defaults(func=_cmd_serial_run)

    pre = serial_sub.add_parser(
        "precheck", help="run a fixed 2-chapter live preflight and write manifest/report")
    pre.add_argument("--project", required=True)
    pre.add_argument("--standard-root", required=True)
    pre.add_argument("--schema-dir", default=None)
    pre.add_argument("--out", default=None)
    pre.add_argument("--prompt-version", default="6.0.0")
    pre.add_argument("--max-depth", type=int, default=2)
    pre.add_argument("--budget-limit", type=float, default=20.0)
    pre.add_argument("--per-chapter-budget", type=float, default=None)
    pre.add_argument("--reviewer", choices=("unanchored", "llm-quality", "panel"),
                     default="unanchored")
    pre.add_argument("--panel-roles", default="literary,structural,commercial,logic")
    pre.add_argument("--model-provider", default="deepseek")
    pre.add_argument("--model-id", default="deepseek-v4-pro")
    pre.add_argument("--temperature", type=float, default=0.7)
    pre.add_argument("--top-p", type=float, default=None)
    pre.add_argument("--max-tokens", type=int, default=None)
    pre.add_argument("--timeout", type=float, default=120)
    pre.add_argument("--replay-dir", default=None)
    pre.set_defaults(func=_cmd_serial_precheck)

    baseline = serial_sub.add_parser(
        "baseline", help="run the short live baseline (alias of precheck)")
    baseline.add_argument("--project", required=True)
    baseline.add_argument("--standard-root", required=True)
    baseline.add_argument("--schema-dir", default=None)
    baseline.add_argument("--out", default=None)
    baseline.add_argument("--prompt-version", default="6.0.0")
    baseline.add_argument("--max-depth", type=int, default=2)
    baseline.add_argument("--budget-limit", type=float, default=20.0)
    baseline.add_argument("--per-chapter-budget", type=float, default=None)
    baseline.add_argument("--reviewer", choices=("unanchored", "llm-quality", "panel"),
                          default="unanchored")
    baseline.add_argument("--panel-roles", default="literary,structural,commercial,logic")
    baseline.add_argument("--model-provider", default="deepseek")
    baseline.add_argument("--model-id", default="deepseek-v4-pro")
    baseline.add_argument("--temperature", type=float, default=0.7)
    baseline.add_argument("--top-p", type=float, default=None)
    baseline.add_argument("--max-tokens", type=int, default=None)
    baseline.add_argument("--timeout", type=float, default=120)
    baseline.add_argument("--replay-dir", default=None)
    baseline.set_defaults(func=_cmd_serial_precheck)

    freeze = serial_sub.add_parser(
        "freeze", help="run the fixed 3-chapter baseline freeze and write audit artifacts")
    freeze.add_argument("--project", required=True)
    freeze.add_argument("--standard-root", required=True)
    freeze.add_argument("--schema-dir", default=None)
    freeze.add_argument("--out", default=None)
    freeze.add_argument("--prompt-version", default="6.0.0")
    freeze.add_argument("--max-depth", type=int, default=2)
    freeze.add_argument("--budget-limit", type=float, default=15.0)
    freeze.add_argument("--per-chapter-budget", type=float, default=None)
    freeze.add_argument("--reviewer", choices=("unanchored", "llm-quality", "panel"),
                          default="unanchored")
    freeze.add_argument("--panel-roles", default="literary,structural,commercial,logic")
    freeze.add_argument("--model-provider", default="deepseek")
    freeze.add_argument("--model-id", default="deepseek-v4-pro")
    freeze.add_argument("--temperature", type=float, default=0.7)
    freeze.add_argument("--top-p", type=float, default=None)
    freeze.add_argument("--max-tokens", type=int, default=None)
    freeze.add_argument("--timeout", type=float, default=120)
    freeze.add_argument("--replay-dir", default=None)
    freeze.set_defaults(func=_cmd_serial_freeze)

    compare = serial_sub.add_parser(
        "baseline-compare", help="compare two frozen baselines (projection; advisory)")
    compare.add_argument("--project", required=True)
    compare.add_argument("--left-id", required=True)
    compare.add_argument("--right-id", required=True)
    compare.add_argument("--json", action="store_true", help="emit the raw comparison as JSON")
    compare.add_argument("--report-id", default=None, help="optional derived report id")
    compare.set_defaults(func=_cmd_serial_baseline_compare)

    vr = serial_sub.add_parser(
        "validation-report", help="show a stored short-run validation report")
    vr.add_argument("--project", required=True)
    vr.add_argument("--report-id", required=True)
    vr.add_argument("--json", action="store_true", help="emit the report as JSON")
    vr.set_defaults(func=_cmd_serial_validation_report)

    rs = serial_sub.add_parser(
        "run-summary", help="show a stored 30ch run summary")
    rs.add_argument("--project", required=True)
    rs.add_argument("--summary-id", required=True)
    rs.add_argument("--json", action="store_true", help="emit the summary as JSON")
    rs.set_defaults(func=_cmd_serial_run_summary)

    ra = serial_sub.add_parser(
        "run-aggregate", help="show a stored run aggregate")
    ra.add_argument("--project", required=True)
    ra.add_argument("--aggregate-id", required=True)
    ra.add_argument("--json", action="store_true", help="emit the aggregate as JSON")
    ra.set_defaults(func=_cmd_serial_run_aggregate)

    si = serial_sub.add_parser(
        "inspect", help="inspect a serial-derived artifact by kind and id")
    si.add_argument("--project", required=True)
    si.add_argument("--kind", required=True,
                     choices=("run-manifest", "run-aggregate", "validation-report",
                              "baseline-freeze", "launch-summary", "rolling-plan"))
    si.add_argument("--artifact-id", required=True)
    si.add_argument("--json", action="store_true", help="emit the artifact as JSON")
    si.set_defaults(func=_cmd_serial_inspect)

    # Book-level pipeline stage projection (M8-01): fold the draft index +
    # envelope publish_readiness/M7 + approval queue + published log into ONE
    # per-chapter stage view. Read-only, advisory, never gates (ADR-003).
    pipe = serial_sub.add_parser(
        "pipeline", help="show the book-level pipeline stage of every chapter (projection; advisory)")
    pipe.add_argument("--project", required=True)
    pipe.add_argument("--json", action="store_true", help="emit the raw projection as JSON")
    pipe.set_defaults(func=_cmd_serial_pipeline)

    audit = serial_sub.add_parser(
        "long-run-audit",
        help="audit CI-M5 30/60/100-chapter admission and completion evidence",
    )
    audit.add_argument("--project", required=True)
    audit.add_argument("--run-id", action="append", default=None,
                       help="run manifest id in chain order; repeat for continuation segments; "
                            "defaults to the run with most produced chapters")
    audit.add_argument("--protocol", default=None)
    audit.add_argument("--ledger", default=None)
    audit.add_argument("--gate-30", default=None)
    audit.add_argument("--gate-60", default=None)
    audit.add_argument("--recovery-audit", default=None)
    audit.add_argument("--baseline", default=None)
    audit.add_argument("--out", default=None)
    audit.add_argument("--json", action="store_true")
    audit.set_defaults(func=_cmd_serial_long_run_audit)

    freeze_long = serial_sub.add_parser(
        "long-run-freeze",
        help="freeze CI-M5 model/prompt/budget policy and write a chapter evidence ledger",
    )
    freeze_long.add_argument("--project", required=True)
    freeze_long.add_argument("--run-id", action="append", required=True,
                             help="run manifest id in chain order; repeat for continuation segments")
    freeze_long.add_argument("--protocol-id", default="CI-M5-PROTOCOL-0001")
    freeze_long.add_argument("--model-provider", required=True)
    freeze_long.add_argument("--model-id", required=True)
    freeze_long.add_argument("--prompt-version", default="14.0.0")
    freeze_long.add_argument("--review-model", default=None, metavar="PROVIDER:MODEL")
    freeze_long.add_argument("--scene-model", default=None, metavar="PROVIDER:MODEL")
    freeze_long.add_argument("--hygiene-model", default=None, metavar="PROVIDER:MODEL")
    freeze_long.add_argument("--temperature", type=float, default=0.7)
    freeze_long.add_argument("--top-p", type=float, default=None)
    freeze_long.add_argument("--max-output-tokens", type=int, default=5000)
    freeze_long.add_argument("--budget-limit-cny", type=float, default=20.0)
    freeze_long.add_argument("--out-dir", default=None)
    freeze_long.add_argument("--notes", default="")
    freeze_long.set_defaults(func=_cmd_serial_long_run_freeze)

    rejudge = serial_sub.add_parser(
        "frozen-rejudge", help="rejudge persisted chapter prose without regeneration")
    rejudge.add_argument("--project", required=True)
    rejudge.add_argument("--package-dir", required=True)
    rejudge.add_argument("--start-chapter", required=True, type=int)
    rejudge.add_argument("--end-chapter", required=True, type=int)
    rejudge.add_argument("--review-model", required=True, metavar="PROVIDER:MODEL")
    rejudge.add_argument("--model-provider", default="deterministic")
    rejudge.add_argument("--model-id", default="unused")
    rejudge.add_argument("--temperature", type=float, default=0.7)
    rejudge.add_argument("--top-p", type=float, default=None)
    rejudge.add_argument("--max-tokens", type=int, default=5000)
    rejudge.add_argument("--timeout", type=float, default=300)
    rejudge.add_argument("--replay-dir", default=None)
    rejudge.add_argument("--env-file", default=None)
    rejudge.add_argument("--out", default=None)
    rejudge.set_defaults(func=_cmd_serial_frozen_rejudge)


def _outline_sources_check(args: argparse.Namespace) -> int:
    result = load_reference_sources(args.project)
    print(render_source_report(result))
    return 0 if result.ok else 2


def _outline_bootstrap(args: argparse.Namespace) -> int:
    _load_dotenv(args)
    model = None
    if getattr(args, "model_provider", None) and args.model_provider != "deterministic":
        model = _build_llm_model(args, replay_suffix="outline")
    judge_models = None
    specs = getattr(args, "tournament_model", None)
    if specs:
        from .execution.llm_model import LLMExecutionModel
        judge_models = []
        for index, spec in enumerate(specs):
            if ":" not in spec:
                raise SystemExit(
                    f"invalid --tournament-model {spec!r}; expected provider:model")
            provider, model_id = (part.strip() for part in spec.split(":", 1))
            if not provider or not model_id or provider == "deterministic":
                raise SystemExit(
                    f"invalid --tournament-model {spec!r}; a live provider:model is required")
            replay = args.replay_dir
            if replay:
                safe_provider = "".join(ch for ch in provider if ch.isalnum() or ch in "-_")
                replay = str(Path(replay).parent / f"{Path(replay).name}-judge-{index}-{safe_provider}")
            judge_models.append((spec, LLMExecutionModel(
                provider=provider,
                model_id=model_id,
                temperature=args.temperature,
                top_p=args.top_p,
                max_tokens=args.max_tokens,
                timeout_seconds=args.timeout,
                replay_dir=replay,
                stream=args.stream,
            )))
    outline_qa_model = None
    qa_spec = getattr(args, "outline_qa_model", None)
    if qa_spec:
        if ":" not in qa_spec:
            raise SystemExit(
                f"invalid --outline-qa-model {qa_spec!r}; expected provider:model")
        provider, model_id = (part.strip() for part in qa_spec.split(":", 1))
        if not provider or not model_id or provider == "deterministic":
            raise SystemExit(
                f"invalid --outline-qa-model {qa_spec!r}; a live provider:model is required")
        from .execution.llm_model import LLMExecutionModel
        replay = args.replay_dir
        if replay:
            replay = str(Path(replay).parent / f"{Path(replay).name}-outline-qa")
        outline_qa_model = LLMExecutionModel(
            provider=provider,
            model_id=model_id,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            timeout_seconds=args.timeout,
            replay_dir=replay,
            stream=False,
        )
    result = run_outline_bootstrap(
        args.project, run_id=args.run_id, model=model, judge_models=judge_models,
        outline_qa_model=outline_qa_model)
    if not result.ok:
        print(result.message)
        for error in result.errors or []:
            print(f"- {error}")
        return 2

    print(result.message)
    print(f"run: {result.run_dir}")
    print(f"json: {result.outline_json}")
    print(f"markdown: {result.outline_markdown}")
    print(f"import-plan: {result.import_plan_json}")
    return 0


def _add_execution_args(p) -> None:
    """Shared args for `execute` and `refine` (single source of truth so the two
    commands cannot drift)."""
    p.add_argument("--package", required=True, help="path to a .package.json")
    p.add_argument("--standard-root", required=True, help="Standard repo root")
    p.add_argument("--project", required=True,
                   help="Project dir; draft is written under its registry/derived/")
    p.add_argument("--min-words", type=int, default=1)
    p.add_argument("--model-provider", default="deterministic",
                   help=("model adapter to use; one of deterministic, paste, mock, "
                         "deepseek, openai, claude, gemini, local, or a comma "
                         "fallback chain like deepseek,openai"))
    p.add_argument("--temperature", type=float, default=0.7,
                   help="sampling temperature for live LLM providers")
    p.add_argument("--top-p", type=float, default=None,
                   help="top_p nucleus sampling contract for live LLM providers")
    p.add_argument("--timeout", type=float, default=120,
                   help="provider request timeout in seconds")
    p.add_argument("--stream", action="store_true",
                   help="use provider streaming and aggregate deltas into the final draft")
    p.add_argument("--max-tokens", type=int, default=None,
                   help="maximum output tokens for live LLM providers")
    from .execution.llm_model import DEFAULT_SYSTEM_PROMPT
    p.add_argument("--system-prompt",
                   default=DEFAULT_SYSTEM_PROMPT,
                   help="system prompt for live LLM providers (default: 中文语域约束)")
    p.add_argument("--paste-file", default=None,
                   help="手动粘贴的文本文件路径（不传则用deterministic stub）")
    p.add_argument("--model-id", default="deepseek-v4-pro",
                   help="model id; for paste, used only as artifact metadata")
    p.add_argument("--env-file", default=None,
                   help="path to .env file; defaults to .env near cwd/package/project")
    p.add_argument("--replay-dir", default=None,
                   help="directory for LLM replay records; avoids repeat provider calls on matching requests")
    p.add_argument("--prompt-id", default="chapter-draft", help="prompt id to render")
    p.add_argument("--prompt-version", default="1.0.0", help="prompt version to render")
    p.add_argument("--prompt-root", default=None,
                   help="directory containing prompt templates; defaults to Standard contracts/prompts")
    p.add_argument("--prompt-cache-dir", default=None,
                   help="directory for rendered prompt cache records")
    p.add_argument("--prompt-mode", choices=("frozen", "dev"), default="frozen",
                   help="prompt loading mode; dev reloads templates on mtime change")
    p.add_argument("--reviewer", choices=("unanchored", "llm-quality", "panel"),
                   default="unanchored",
                   help=("evaluative reviewer (ADR-003 advisory, never gates): "
                         "unanchored=proper-noun anchor check (default); "
                         "llm-quality=Novel Quality Center LLM judge; "
                         "panel=multi-model review panel"))
    p.add_argument("--panel-roles", default="literary,structural,commercial,logic",
                   help="comma-separated panel roles when --reviewer panel")


def _cmd_genesis(args) -> int:
    """Auto Project Genesis (roadmap M2): open a producible book from reference
    sources — outline bootstrap → fold a Novel Brain → land the event/character/
    world batch via mint. Preview by default; --confirm crosses the ADR-009
    boundary and writes facts."""
    _load_dotenv(args)
    from .genesis import run_genesis

    schema_dir = (args.schema_dir if args.schema_dir
                  else str(_sibling_standard() / "phase-1" / "generated" / "json-schema"))
    standard_root = args.standard_root or str(_sibling_standard())

    # A live provider authors the original settings (candidates/characters/world);
    # deterministic keeps the template path. Isolated replay bucket ("outline") so
    # a re-run is reproducible without re-billing (same discipline as serial).
    model = None
    if args.model_provider not in ("deterministic",):
        model = _build_llm_model(args, replay_suffix="outline")

    result = run_genesis(
        args.project, schema_dir=schema_dir, standard_root=standard_root,
        confirm=args.confirm, overwrite_brain=args.overwrite_brain,
        run_id=args.run_id, actor=args.actor, model=model)

    print(f"genesis: stage={result.stage} — {result.message}")
    print(f"  outline    : {result.outline_id}  ({result.events_planned} events planned)")
    if result.brain_path:
        print(f"  brain      : {result.brain_path} "
              f"({'written' if result.brain_written else 'kept existing'})")
    if result.position_path:
        print(f"  position   : {result.position_path} "
              f"({'written' if result.position_written else 'kept existing'})")
    if result.admission_recommendation:
        print(f"  admission  : {result.admission_recommendation} — {result.admission_rationale}")
        print(f"               (advisory, never gates; human decides at approval — ADR-003/009)")
    if result.landed:
        print(f"  minted     : {result.minted_count} fact(s) — receipt {result.receipt_id}")
    elif result.preview_count:
        print(f"  preview    : would mint {result.preview_count} candidate(s) "
              f"(re-run with --confirm to open the book)")
    for e in result.errors:
        print(f"  [error] {e}")
    return 0 if result.ok else 2


def _add_genesis_command(sub) -> None:
    g = sub.add_parser(
        "genesis",
        help="Auto Project Genesis (M2): open a producible book from references")
    g.add_argument("--project", required=True, type=Path)
    g.add_argument("--schema-dir", default=None,
                   help="schema dir; defaults to the sibling Standard's json-schema")
    g.add_argument("--standard-root", default=None,
                   help="Standard repo root; defaults to the sibling AI-Novel-Standard")
    g.add_argument("--confirm", action="store_true",
                   help="cross the ADR-009 boundary and MINT the candidates (writes facts)")
    g.add_argument("--overwrite-brain", action="store_true",
                   help="replace an existing authored Novel Brain (default: keep it)")
    g.add_argument("--run-id", default=None, help="optional stable outline run id")
    g.add_argument("--actor", default=None, help="who authorized this genesis (for the receipt)")
    # Live-model authorship of the original settings. Default deterministic keeps
    # the template path (writes no facts differently, byte-identical outline).
    g.add_argument("--model-provider", default="deterministic",
                   help="model adapter that AUTHORS the settings (deepseek/openai/claude/...); "
                        "default deterministic (template outline)")
    g.add_argument("--model-id", default="deepseek-v4-pro")
    g.add_argument("--temperature", type=float, default=0.7)
    g.add_argument("--top-p", type=float, default=None)
    g.add_argument("--max-tokens", type=int, default=None)
    g.add_argument("--timeout", type=float, default=120)
    g.add_argument("--replay-dir", default=None,
                   help="replay bucket so a genesis re-run is reproducible without re-billing")
    g.add_argument("--env-file", default=None,
                   help="path to a .env supplying the provider API key")
    g.set_defaults(func=_cmd_genesis)


def _add_outline_commands(sub) -> None:
    outline = sub.add_parser("outline", help="Outline Bootstrap commands")
    outline_sub = outline.add_subparsers(dest="outline_command", required=True)

    sources_check = outline_sub.add_parser(
        "sources-check", help="Validate 1-5 reference novels"
    )
    sources_check.add_argument("--project", required=True, type=Path)
    sources_check.set_defaults(func=_outline_sources_check)

    bootstrap = outline_sub.add_parser(
        "bootstrap", help="Analyze reference novels and produce a v0.2 outline artifact"
    )
    bootstrap.add_argument("--project", required=True, type=Path)
    bootstrap.add_argument("--run-id", default=None, help="optional stable run id")
    bootstrap.add_argument("--model-provider", default="deterministic",
                           help=("outline model adapter; deterministic by default, or a live "
                                 "provider chain such as deepseek,openai"))
    bootstrap.add_argument("--model-id", default="deepseek-v4-pro",
                           help="model id for the selected live outline provider")
    bootstrap.add_argument(
        "--tournament-model", action="append", default=None, metavar="PROVIDER:MODEL",
        help=("repeatable Genesis pairwise judge. All judges reuse one frozen "
              "candidate snapshot; defaults to the outline generation model"),
    )
    bootstrap.add_argument(
        "--outline-qa-model", default=None, metavar="PROVIDER:MODEL",
        help=("independent advisory model for the synthesized outline; failures "
              "are archived as degraded and never gate bootstrap"),
    )
    bootstrap.add_argument("--temperature", type=float, default=0.7,
                           help="sampling temperature for live outline providers")
    bootstrap.add_argument("--top-p", type=float, default=None,
                           help="top_p nucleus sampling contract for live outline providers")
    bootstrap.add_argument("--timeout", type=float, default=120,
                           help="provider request timeout in seconds")
    bootstrap.add_argument("--stream", action="store_true",
                           help="use provider streaming and aggregate deltas into the final outline")
    bootstrap.add_argument("--max-tokens", type=int, default=None,
                           help="maximum output tokens for live outline providers")
    bootstrap.add_argument("--system-prompt", default=None,
                           help="system prompt for live outline providers")
    bootstrap.add_argument("--env-file", default=None,
                           help="path to a .env supplying the provider API key")
    bootstrap.add_argument("--replay-dir", default=None,
                           help="directory for outline replay records")
    bootstrap.set_defaults(func=_outline_bootstrap)


def _market_snapshot(args: argparse.Namespace) -> int:
    from .market.writer import build_market_intelligence
    result = build_market_intelligence(args.project, freshness_days=args.freshness_days)
    if not result.ok:
        print(result.message)
        for error in result.errors or []:
            print(f"- {error}")
        return 2
    print(result.message)
    print(f"snapshot: {result.snapshot_json}")
    if result.is_stale:
        print("[advisory] market observations are stale; refresh before trusting "
              "positioning (never gates, ADR-003)")
    return 0


def _add_market_commands(sub) -> None:
    market = sub.add_parser("market", help="Market Intelligence commands (roadmap P0)")
    market_sub = market.add_subparsers(dest="market_command", required=True)

    snap = market_sub.add_parser(
        "snapshot", help="Analyze dated market observations into a pinned Market Snapshot")
    snap.add_argument("--project", required=True, type=Path)
    snap.add_argument("--freshness-days", type=int, default=90,
                      help="staleness window; older observations mark the snapshot stale (advisory)")
    snap.set_defaults(func=_market_snapshot)


def _reference_profile(args: argparse.Namespace) -> int:
    """Build the Reference Quality Profile (M9): measure the project's reference
    novels with the SAME detectors as generated chapters, fold into a pinned
    market-validated anchor. Comparison-only, never gates (ADR-003)."""
    from .reference.writer import build_reference_intelligence

    # Deterministic arm by default (reviewer=None, zero API). The opt-in judge
    # arm (double-measure) fires only with a live provider.
    reviewer = None
    if args.model_provider not in ("deterministic",):
        _load_dotenv(args)
        from .execution.quality_center import llm_quality_judge
        reviewer = llm_quality_judge(_build_llm_model(args, replay_suffix="judge"))

    result = build_reference_intelligence(args.project, reviewer=reviewer)
    if not result.ok:
        print(f"stage={result.stage}: {result.message}")
        for error in result.errors or []:
            print(f"- {error}")
        return 2
    print(result.message)
    print(f"profile : {result.profile_json}")
    print(f"sources : {result.sources}  chapters_measured: {result.chapters_measured}")
    if result.has_judge_bands:
        print("judge bands: present (double-measure ran)")
    print("[advisory] the reference anchor is comparison-only; it never gates "
          "a build (ADR-003)")
    return 0


def _reference_abstract(args: argparse.Namespace) -> int:
    """Build the Phase D M5 Reference LM abstraction from the project's
    reference novels. This is advisory only and writes a derived artifact."""
    from .reference.abstract import build_reference_abstraction, write_reference_abstraction

    try:
        abstraction = build_reference_abstraction(args.project)
    except ValueError as exc:
        print(f"stage=sources: {exc}")
        return 2

    rel = write_reference_abstraction(args.project, abstraction)
    print("reference abstraction produced")
    print(f"abstract: {rel}")
    print(f"source_summaries: {len(abstraction.get('source_summaries', []))}")
    print(f"evidence_spans  : {len(abstraction.get('evidence_spans', []))}")
    print("[advisory] the reference abstraction is comparison-only; it never gates "
          "a build (ADR-003)")
    return 0


def _reference_abstract_show(args: argparse.Namespace) -> int:
    from .reference.abstract import load_reference_abstraction
    abstraction = load_reference_abstraction(args.project)
    if abstraction is None:
        print("no M5 reference abstraction authored yet")
        return 0
    if args.json:
        print(json.dumps(abstraction, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"{abstraction.get('id', 'REFABSTRACT-001')} — {abstraction.get('kind')}")
    mp = abstraction.get('market_positioning', {})
    print(f"  genre   : {mp.get('genre', '?')}")
    print(f"  promise : {mp.get('core_promise', '')}")
    print(f"  sources  : {len(abstraction.get('source_ids', []))}")
    print(f"  spans    : {len(abstraction.get('evidence_spans', []))}")
    return 0


def _reference_abstract_validate(args: argparse.Namespace) -> int:
    from .reference.abstract import build_reference_abstraction
    try:
        abstraction = build_reference_abstraction(args.project)
    except ValueError as exc:
        print(f"invalid: {exc}")
        return 2
    if not abstraction.get('source_ids'):
        print('invalid: no reference sources found')
        return 2
    print('OK: M5 reference abstraction input is valid')
    return 0


def _add_reference_commands(sub) -> None:
    ref = sub.add_parser("reference",
                         help="Reference Quality Anchor commands (roadmap M9)")
    ref_sub = ref.add_subparsers(dest="reference_command", required=True)

    prof = ref_sub.add_parser(
        "profile",
        help="Measure reference novels into a pinned Reference Quality Profile")
    prof.add_argument("--project", required=True, type=Path)
    # Deterministic by default; a live provider turns on the opt-in judge arm.
    prof.add_argument("--model-provider", default="deterministic",
                      help="deterministic (default, no API) or a live provider "
                           "(deepseek/openai/claude/...) to add the judge double-measure")
    prof.add_argument("--model-id", default="")
    prof.add_argument("--temperature", type=float, default=0.0)
    prof.add_argument("--top-p", type=float, default=1.0)
    prof.add_argument("--max-tokens", type=int, default=4096)
    prof.add_argument("--timeout", type=int, default=120)
    prof.add_argument("--replay-dir", default=None)
    prof.add_argument("--env-file", default=None)
    prof.set_defaults(func=_reference_profile)

    abs_cmd = ref_sub.add_parser(
        "abstract",
        help="Build the M5 reference LM abstraction from reference novels")
    abs_cmd.add_argument("--project", required=True, type=Path)
    abs_cmd.set_defaults(func=_reference_abstract)

    show = ref_sub.add_parser(
        "show",
        help="Show the authored M5 reference abstraction")
    show.add_argument("--project", required=True, type=Path)
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=_reference_abstract_show)

    validate = ref_sub.add_parser(
        "validate",
        help="Validate that an M5 abstraction can be built from the reference corpus")
    validate.add_argument("--project", required=True, type=Path)
    validate.set_defaults(func=_reference_abstract_validate)


def _cmd_m7_rules(args) -> int:
    from .execution.redline import DEFAULT_RULESET, RedlineRule, load_ruleset, save_ruleset
    project = Path(args.project)
    if args.action == "export":
        rules = load_ruleset(project, args.rule_set_id) or list(DEFAULT_RULESET)
        if args.json:
            print(json.dumps([r.to_dict() for r in rules], ensure_ascii=False, indent=2, sort_keys=True))
        else:
            for r in rules:
                print(f"{r.rule_id}	{r.severity}	{r.pattern}	{r.note}")
        return 0
    if args.action == "import":
        rules = []
        for item in json.loads(Path(args.input).read_text(encoding="utf-8")):
            rules.append(RedlineRule(
                rule_id=item["rule_id"],
                pattern=item["pattern"],
                severity=item.get("severity", "soft"),
                note=item.get("note", ""),
            ))
        save_ruleset(project, rules, args.rule_set_id)
        print(f"saved {len(rules)} rules to {args.rule_set_id}")
        return 0
    raise SystemExit(f"unknown m7 rules action {args.action!r}")


def _cmd_m7_audit(args) -> int:
    from .execution.m7 import assess_m7
    from .execution.m7_audit import evaluate_m7_samples, load_m7_regression_samples
    samples = load_m7_regression_samples(args.project)
    if not samples:
        print("no m7 regression samples")
        return 0

    def runner(sample: dict) -> dict:
        result = assess_m7(
            {"body": sample.get("body", "")},
            chapter_id=sample.get("id", ""),
            references=sample.get("references", []),
        )
        return result.to_dict()

    report = evaluate_m7_samples(args.project, runner)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"m7 regression — {report['passed']}/{report['total']} passed ({report['pass_rate']:.0%})")
    for r in report["results"]:
        mark = "PASS" if r["matches"] else "FAIL"
        print(f"{mark}	{r['sample_id']}	{r['sample_type']}	{r['expected_risk_level']}->{r['observed'].get('risk_level')}	{r['expected_recommendation']}->{r['observed'].get('recommendation')}")
    return 0 if report["failed"] == 0 else 1


def _add_m7_command(sub) -> None:
    pm = sub.add_parser("m7", help="M7 originality + red-line governance commands")
    m7_sub = pm.add_subparsers(dest="m7_command", required=True)

    rules = m7_sub.add_parser("rules", help="export/import redline rulesets")
    rules.add_argument("--project", required=True)
    rules.add_argument("--rule-set-id", default="default")
    rules.add_argument("--json", action="store_true")
    rules.add_argument("--action", choices=("export", "import"), required=True)
    rules.add_argument("--input", default=None, help="path to JSON rules list for import")
    rules.set_defaults(func=_cmd_m7_rules)

    audit = m7_sub.add_parser("audit", help="run M7 regression test suite")
    audit.add_argument("--samples-dir", required=True, help="directory with test samples")
    audit.add_argument("--project", required=True)
    audit.add_argument("--standard-root", required=True)
    audit.add_argument("--schema-dir", required=True)
    audit.add_argument("--out", required=True)
    audit.set_defaults(func=_cmd_m7_audit)


def _cmd_promise_ledger(args) -> int:
    """Display the Promise Ledger for a project."""
    from pathlib import Path
    from .packaging import load_packaging
    from .promise import project_promise_ledger
    from . import registry_loader

    project_path = Path(args.project).resolve()
    reg = registry_loader.load(project_path)
    packaging = load_packaging(project_path)

    if not packaging:
        print("No packaging found (sources/book-packaging.yaml)")
        return 1

    ledger = project_promise_ledger(reg, packaging)
    summary = ledger.to_dict()["summary"]

    print(f"Promise Ledger: {project_path.name}")
    print(f"  Total promises: {summary['total']}")
    print(f"    Open: {summary['open']}")
    print(f"    Delivered: {summary['delivered']}")
    if summary.get('missed', 0) > 0:
        print(f"    Missed: {summary['missed']}")
    print(f"\n  By Type:")
    print(f"    Packaging: {summary['by_type']['packaging']}")
    print(f"    Narrative: {summary['by_type']['narrative']}")
    print(f"    Thread: {summary['by_type']['thread']}")

    if args.detail:
        print(f"\n  All Promises:")
        for p in ledger.promises:
            status_mark = "✓" if p.status == "delivered" else "○"
            deadline = f"(due ch {p.must_deliver_by})" if p.must_deliver_by else ""
            print(f"    {status_mark} {p.id}: {p.statement[:60]} {deadline}")

    return 0


def _cmd_promise_check(args) -> int:
    """Check promises for a specific chapter."""
    from pathlib import Path
    from .packaging import load_packaging
    from .promise import project_promise_ledger, pending_promises_for_chapter, overdue_promises_for_chapter
    from . import registry_loader

    project_path = Path(args.project).resolve()
    reg = registry_loader.load(project_path)
    packaging = load_packaging(project_path)

    if not packaging:
        print("No packaging found (sources/book-packaging.yaml)")
        return 1

    ledger = project_promise_ledger(reg, packaging)
    chapter = args.chapter

    pending = pending_promises_for_chapter(ledger, chapter, lookahead=args.lookahead)
    overdue = overdue_promises_for_chapter(ledger, chapter)

    print(f"Promise Check: Chapter {chapter}")

    if overdue:
        print(f"\n  ⚠️ Overdue Promises: {len(overdue)}")
        for p in overdue:
            print(f"    • {p.statement} (was due ch {p.must_deliver_by}, {p.level})")

    if pending:
        print(f"\n  📋 Pending Promises: {len(pending)}")
        for p in pending:
            deadline = f"due ch {p.must_deliver_by}" if p.must_deliver_by else "no deadline"
            print(f"    • {p.statement} ({deadline}, {p.level})")

    if not overdue and not pending:
        print(f"\n  ✓ No promises pending for this chapter")

    return 0


def _add_promise_command(sub) -> None:
    """Add Promise Ledger CLI commands (Stage B.5)."""
    pp = sub.add_parser("promise", help="Promise Ledger: 承诺追踪 (packaging + narrative + threads)")
    promise_sub = pp.add_subparsers(dest="promise_command", required=True)

    # promise ledger: show all promises
    ledger = promise_sub.add_parser("ledger", help="Display Promise Ledger summary")
    ledger.add_argument("--project", required=True, help="Project directory")
    ledger.add_argument("--detail", action="store_true", help="Show all promises in detail")
    ledger.set_defaults(func=_cmd_promise_ledger)

    # promise check: check promises for a chapter
    check = promise_sub.add_parser("check", help="Check promises for a specific chapter")
    check.add_argument("--project", required=True, help="Project directory")
    check.add_argument("--chapter", type=int, required=True, help="Chapter number (1-based)")
    check.add_argument("--lookahead", type=int, default=2,
                      help="Include promises due in next N chapters (default 2)")
    check.set_defaults(func=_cmd_promise_check)


def _add_m7_command(sub) -> None:
    pm = sub.add_parser("m7", help="M7 originality + red-line governance commands")
    m7_sub = pm.add_subparsers(dest="m7_command", required=True)

    rules = m7_sub.add_parser("rules", help="export/import redline rulesets")
    rules.add_argument("--project", required=True)
    rules.add_argument("--rule-set-id", default="default")
    rules.add_argument("--json", action="store_true")
    rules.add_argument("--action", choices=("export", "import"), required=True)
    rules.add_argument("--input", default=None, help="path to JSON rules list for import")
    rules.set_defaults(func=_cmd_m7_rules)

    audit = m7_sub.add_parser("audit", help="run M7 regression evaluation")
    audit.add_argument("--project", required=True)
    audit.add_argument("--json", action="store_true")
    audit.set_defaults(func=_cmd_m7_audit)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="runtime")
    ap.add_argument("--standard-version", default="2.0.0")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="run deterministic gate only")
    pv.add_argument("--project", required=True)
    pv.add_argument("--schema-dir", required=True)
    pv.set_defaults(func=_cmd_validate)

    pb = sub.add_parser("build", help="build a Task Package")
    pb.add_argument("--project", required=True)
    pb.add_argument("--schema-dir", required=True)
    pb.add_argument("--task", required=True)
    pb.add_argument("--goal", required=True)
    pb.add_argument("--capability", required=True)
    pb.add_argument("--seed", action="append", required=True,
                    help="seed entity id (repeatable)")
    pb.add_argument("--out", required=True)
    pb.add_argument("--max-depth", type=int, default=2)
    pb.add_argument("--token-budget", type=int, default=None)
    pb.set_defaults(func=_cmd_build)

    pr = sub.add_parser("prompt-replay", help="inspect a prompt manifest/cache record")
    pr.add_argument("--manifest", required=True,
                    help="path to a prompt manifest/cache JSON record")
    pr.add_argument("--show-messages", action="store_true",
                    help="print rendered prompt messages")
    pr.set_defaults(func=_cmd_prompt_replay)

    pd = sub.add_parser("prompt-diff", help="diff two prompt manifest/cache records")
    pd.add_argument("--left", required=True)
    pd.add_argument("--right", required=True)
    pd.set_defaults(func=_cmd_prompt_diff)

    pa = sub.add_parser("prompt-audit", help="list project prompt manifests")
    pa.add_argument("--project", required=True)
    pa.set_defaults(func=_cmd_prompt_audit)

    pe = sub.add_parser("execute", help="execute a Task Package into a ChapterDraft")
    _add_execution_args(pe)
    pe.set_defaults(func=_cmd_execute)

    prf = sub.add_parser("refine",
                         help="generate -> review -> revise -> re-gate a ChapterDraft (full quality loop)")
    _add_execution_args(prf)
    prf.add_argument("--max-rounds", type=int, default=3,
                     help="max revision rounds (advisory loop; never gates)")
    prf.add_argument("--threshold", type=int, default=80,
                     help="per-dimension score a rewrite aims to reach (advisory)")
    prf.set_defaults(func=_cmd_refine)

    pc = sub.add_parser(
        "commercial",
        help="generate -> simulate readers -> rewrite -> re-simulate (comparison-only commercial loop, P16)")
    _add_execution_args(pc)
    pc.add_argument("--max-rounds", type=int, default=2,
                    help="max commercial rewrite rounds (advisory loop; never gates)")
    pc.add_argument("--panel", choices=("appetite", "commercial", "both"),
                    default="commercial",
                    help="reader panel: appetite (v1 6 personas), commercial "
                         "(v2 6 pay-behavior personas, default), or both (12)")
    pc.set_defaults(func=_cmd_commercial)

    _add_genesis_command(sub)
    _add_outline_commands(sub)
    _add_market_commands(sub)
    _add_reference_commands(sub)
    _add_state_command(sub)
    _add_narrative_command(sub)
    _add_brain_command(sub)
    _add_speech_command(sub)
    _add_positioning_command(sub)
    _add_candidates_command(sub)
    _add_recompute_command(sub)
    _add_publishing_command(sub)
    _add_schedule_command(sub)
    _add_workflow_command(sub)
    _add_serial_command(sub)
    reviewer_calibration = sub.add_parser(
        "reviewer-calibration",
        help="Backfill and inspect real reviewer calibration results (W9-01)")
    reviewer_calibration_sub = reviewer_calibration.add_subparsers(dest="reviewer_calibration_command", required=True)
    show = reviewer_calibration_sub.add_parser("show", help="show stored reviewer calibration results")
    show.add_argument("--project", required=True)
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=_cmd_reviewer_calibration_backfill, action="show")
    backfill_all = reviewer_calibration_sub.add_parser("backfill-all", help="backfill all 50 calibration samples")
    backfill_all.add_argument("--project", required=True)
    backfill_all.set_defaults(func=_cmd_reviewer_calibration_backfill, action="backfill-all")
    summary = reviewer_calibration_sub.add_parser("summary", help="summarize reviewer calibration results")
    summary.add_argument("--project", required=True)
    summary.add_argument("--json", action="store_true")
    summary.add_argument("--write", action="store_true")
    summary.add_argument("--report", action="store_true")
    summary.add_argument("--report-only", action="store_true")
    summary.set_defaults(func=_cmd_reviewer_calibration_summary)
    _add_signals_command(sub)
    _add_approval_command(sub)
    _add_director_command(sub)
    _add_dashboard_command(sub)
    _add_export_commands(sub)
    _add_promise_command(sub)  # Stage B.5: Promise Ledger CLI
    _add_m7_command(sub)

    qs = sub.add_parser("quality-snapshot", help="render a read-side chapter quality snapshot")
    qs.add_argument("--chapter-id", required=True)
    qs.add_argument("--body", required=True)
    qs.add_argument("--json", action="store_true", help="print the snapshot as JSON")
    qs.set_defaults(func=_cmd_quality_snapshot)

    qsc = sub.add_parser("quality-snapshot-compare", help="compare two chapter quality snapshots")
    qsc.add_argument("--left-id", required=True)
    qsc.add_argument("--left-body", required=True)
    qsc.add_argument("--right-id", required=True)
    qsc.add_argument("--right-body", required=True)
    qsc.add_argument("--json", action="store_true", help="print the comparison as JSON")
    qsc.set_defaults(func=_cmd_quality_snapshot_compare)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
