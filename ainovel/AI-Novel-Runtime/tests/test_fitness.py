"""test_fitness.py — Architecture Fitness functions (ANES v2, audit §7).

These are not feature tests; they assert the ARCHITECTURE holds, and fail CI if
it drifts. They encode the rules learned across phases as executable guards.

Rules enforced:
  1. Runtime never hardcodes entity type maps (catalog is the SSOT).
  2. Runtime never imports Standard-internal modules (it reads catalog/contracts
     as data, not by reaching into the Standard's code/generators).
  3. The build pipeline must not depend on the execution subdomain (control-flow
     layering: execution consumes the build's output, not vice versa).
  4. Only deterministic checks are registered on the gate axis (ADR-003).
  5. No fact directory is hardcoded outside the catalog consumer.

Run: python3 -m tests.test_fitness
"""
from __future__ import annotations

import re
from pathlib import Path

from runtime import validator

HERE = Path(__file__).resolve().parent
RUNTIME_PKG = HERE.parent / "runtime"

_passed = 0
_failed = 0


def check(name, cond, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed += 1
        print(f"  FAIL  {name}  {detail}")


def _py_files(pkg: Path):
    return [p for p in pkg.rglob("*.py") if "__pycache__" not in str(p)]


def _source(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Guard #26 — the built-but-never-wired ratchet.                              #
#                                                                             #
# This repo's most-repeated defect is a module that is written, unit-tested,   #
# and then never called by any production path ("built != live"). It has now   #
# landed 20+ times. An earlier attempt to detect it with a heuristic orphan    #
# scan produced 34 candidates that were mostly FALSE POSITIVES, so it was      #
# abandoned — a detector that cries wolf gets ignored.                         #
#                                                                             #
# So this guard is a RATCHET, not a detector. The known-unreachable set below  #
# is frozen as an explicit allowlist and the only assertion is that it must    #
# NOT GROW. That gives a bounded, zero-false-positive check:                   #
#   - add a new module with no caller  -> RED immediately                      #
#   - wire an existing orphan up       -> delete its line here (anti-regress)  #
# Nothing forces the existing entries to be fixed; it only stops #22 onward.   #
#                                                                             #
# Reachability is computed by RESOLVING imports to files, never by matching    #
# module/symbol NAMES. Name matching is what made the earlier scan unusable:   #
# `long_arc_plan` appears as a dict PARAMETER in director/plan.py, and both    #
# corpus/snapshot.py and market/snapshot.py are "snapshot" — name-based checks #
# call all of those live when they are not.                                    #
# --------------------------------------------------------------------------- #
KNOWN_UNREACHABLE = {
    # Phase A.2 - Final quality gate: WIRED into serialize/loop.py (P0-3 fix).
    # Removed from the allowlist per the ratchet rule — an entry that is now
    # reachable must be deleted so it can never silently regress to dead code.

    # Phase A.3 - Genesis authenticity verification (LLM vs template fallback)
    # Awaiting Genesis stability before integration to avoid introducing instability
    # Unique function: records generation method per component, prevents all-template projects
    "genesis/authenticity.py",

    # Phase A.5 - Prediction error report (requires real reader data)
    # Depends on real platform data (currently zero), activate during market validation phase
    # ADR-003 compliant: comparison_only, never gates, never calibrates
    "signals/prediction_error.py",

    "corpus/snapshot.py",
    "director/consumption_checkpoint.py",
    "execution/deepseek_model.py",
    "narrative_mining/book_profile.py",
    "narrative_mining/consensus.py",
    "narrative_mining/llm_analyzer.py",
    "narrative_mining/validation.py",
    "prompt/routing_eval.py",
    "publishing/release_package.py",
    "serialize/ab_cleaning_artifacts.py",
    "serialize/ab_cleaning_flow.py",
    "serialize/ab_cleaning_query.py",
    "serialize/baseline_artifacts.py",
    "serialize/baseline_query.py",
    "serialize/baseline_report.py",
    "serialize/blind_evaluation.py",
    "serialize/calibration_protocol.py",
    "serialize/chapter_baseline.py",
    "serialize/gold_sample_seed.py",
    "serialize/golden_three.py",
    "serialize/golden_three_query.py",
    "serialize/golden_three_records.py",
    "serialize/launch_30ch_artifacts.py",
    "serialize/launch_30ch_bridge_query.py",
    "serialize/launch_30ch_query.py",
    "serialize/long_arc_plan.py",
    "serialize/long_run_baseline.py",
    "serialize/long_run_checkpoint.py",
    "serialize/long_run_execution_report.py",
    "serialize/long_run_readiness.py",
    "serialize/platform_feedback_profile.py",
    "serialize/register_length_report.py",
    "serialize/reviewer_calibration_summary.py",
    "serialize/selection_policy.py",
    "serialize/stage_graph.py",
    "serialize/version_matrix.py",
    "serialize/winner_drift.py",
    "serialize/winner_drift_artifacts.py",
    "serialize/winner_drift_query.py",
    # Phase 3 商业优化和留存模块（尚未接入 CLI）
    "commercial/hit_analyzer.py",
    "commercial/hit_analyzer_impl.py",
    "commercial/llm_integration.py",
    "commercial/paywall_optimizer.py",
    "commercial/paywall_optimizer_impl.py",
    "commercial/retention_optimizer.py",
    "commercial/retention_optimizer_impl.py",
    "retention/hook_enhancer.py",
    "retention/hook_enhancer_impl.py",
    # v15 prompt 辅助模块（从 binding.py 动态加载）
    "prompts/v15/chapter.py",
}


def _resolve_import(module: str, level: int, origin: Path):
    """Resolve one import statement to the actual file(s) it pulls in.

    `level` is the relative-import depth (`from ..x import y` => 2). Absolute
    imports are only followed when they start at `runtime`, so stdlib and
    third-party imports are ignored.
    """
    if level:
        base = origin.parent
        for _ in range(level - 1):
            base = base.parent
        parts = module.split(".") if module else []
    else:
        parts = module.split(".")
        if not parts or parts[0] != RUNTIME_PKG.name:
            return []
        base, parts = RUNTIME_PKG, parts[1:]
    target = base
    for part in parts:
        target = target / part
    found = []
    if target.with_suffix(".py").exists():
        found.append(target.with_suffix(".py"))
    if (target / "__init__.py").exists():
        found.append(target / "__init__.py")
    return found


def _import_edges(p: Path):
    """Every runtime file this file imports (following __init__ re-exports)."""
    import ast
    try:
        tree = ast.parse(_source(p))
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            targets = _resolve_import(node.module or "", node.level or 0, p)
            out += targets
            # `from .pkg import name` may name a SUBMODULE rather than a symbol,
            # which is how most of this runtime reaches its leaves.
            for t in list(targets):
                if t.name == "__init__.py":
                    for alias in node.names:
                        sub = t.parent / f"{alias.name}.py"
                        if sub.exists():
                            out.append(sub)
                        pkg_init = t.parent / alias.name / "__init__.py"
                        if pkg_init.exists():
                            out.append(pkg_init)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out += _resolve_import(alias.name, 0, p)
    return out


def _unreachable_modules():
    """Runtime modules not reachable from the CLI or any script/tool entry point.

    Returns paths relative to `runtime/`, matching KNOWN_UNREACHABLE.
    """
    repo = RUNTIME_PKG.parent
    entries = [RUNTIME_PKG / "cli.py"]
    scanned = _py_files(RUNTIME_PKG)
    for extra in ("scripts", "tools"):
        d = repo / extra
        if d.exists():
            found = _py_files(d)
            entries += found
            scanned += found

    graph = {p.resolve(): {t.resolve() for t in _import_edges(p)} for p in scanned}

    seen, stack = set(), [e.resolve() for e in entries if e.exists()]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(graph.get(cur, ()))

    return {str(p.relative_to(RUNTIME_PKG)) for p in _py_files(RUNTIME_PKG)
            if p.resolve() not in seen and p.name != "__init__.py"}


def main() -> int:
    print("ANES v2 — Architecture Fitness")
    files = _py_files(RUNTIME_PKG)

    # 1. No hardcoded entity-type maps anywhere in runtime (catalog is SSOT).
    #    A "map" = a dict/list literal keying multiple known type codes. We proxy
    #    this by forbidding the old constant names and multi-code literals.
    banned_names = ("TYPE_DIR", "TYPE_TO_ENTITY", "TYPE_ORDER")
    offenders = []
    for p in files:
        src = _source(p)
        for name in banned_names:
            # allow the words in comments/docstrings that describe the removal
            for line in src.splitlines():
                if name in line and "=" in line and not line.lstrip().startswith("#"):
                    # a real assignment to a banned name
                    if re.search(rf"\b{name}\b\s*=", line):
                        offenders.append(f"{p.name}: {line.strip()}")
    check("no hardcoded type map constants (TYPE_DIR/TYPE_TO_ENTITY/TYPE_ORDER)",
          not offenders, "; ".join(offenders))

    # 2. Runtime does not import Standard-internal code.
    bad_imports = []
    for p in files:
        for line in _source(p).splitlines():
            s = line.strip()
            if s.startswith(("import ", "from ")) and (
                    "AI_Novel_Standard" in s or "AI-Novel-Standard" in s
                    or "idl_to_jsonschema" in s):
                bad_imports.append(f"{p.name}: {s}")
    check("runtime never imports Standard-internal modules", not bad_imports,
          "; ".join(bad_imports))

    # 3. Build pipeline must not import the execution subdomain.
    pipeline_src = _source(RUNTIME_PKG / "pipeline.py")
    check("build pipeline does not depend on execution subdomain",
          "execution" not in pipeline_src,
          "pipeline.py references execution")

    # 4. Every registered validator check is on a known axis; gate checks are
    #    deterministic only (ADR-003).
    checks = dict(validator.registered_checks())
    check("all registered gate checks are deterministic (ADR-003)",
          all(ax == validator.AXIS_GATE for ax in checks.values()))

    # 5. fact directories are referenced via the catalog, not string literals
    #    in loader/validator/normalizer. Proxy: those modules don't contain a
    #    hardcoded "facts/<name>" path literal for known dirs.
    known_dirs = ["characters", "relationships", "timelines", "events",
                  "world_rules", "items"]
    literal_offenders = []
    for mod in ("registry_loader.py", "validator.py", "normalizer.py"):
        src = _source(RUNTIME_PKG / mod)
        for d in known_dirs:
            if f'"{d}"' in src or f"'{d}'" in src:
                literal_offenders.append(f"{mod}:{d}")
    check("no hardcoded facts-dir literals in resource modules",
          not literal_offenders, "; ".join(literal_offenders))

    # 6. Execution must not hardcode an output-contract schema filename; the
    #    output schema comes from the capability contract (output.schema). A new
    #    capability must not be able to silently reuse the wrong schema.
    exec_offenders = []
    for p in _py_files(RUNTIME_PKG / "execution"):
        for line in _source(p).splitlines():
            s = line.strip()
            if s.startswith("#"):
                continue
            if ".schema.json" in s and "=" in s:
                exec_offenders.append(f"{p.name}: {s}")
    check("execution does not hardcode an output-contract filename",
          not exec_offenders, "; ".join(exec_offenders))

    # 7. Outline bootstrap is a derived-artifact pipeline. It may create future
    #    import plans, but it must not directly write Project facts.
    outline_offenders = []
    for p in _py_files(RUNTIME_PKG / "outline"):
        src = _source(p)
        if "registry\" / \"facts" in src or "registry' / 'facts" in src:
            outline_offenders.append(p.name)
    check("outline bootstrap does not write registry facts directly",
          not outline_offenders, "; ".join(sorted(set(outline_offenders))))

    # 8. Market Intelligence is a pinned-snapshot derived pipeline. A market read
    #    is not a story fact; it must never write Project facts.
    market_dir = RUNTIME_PKG / "market"
    market_offenders = []
    if market_dir.exists():
        for p in _py_files(market_dir):
            src = _source(p)
            if "registry\" / \"facts" in src or "registry' / 'facts" in src:
                market_offenders.append(p.name)
    check("market intelligence does not write registry facts directly",
          not market_offenders, "; ".join(sorted(set(market_offenders))))

    # 9. Novel Brain is an AUTHORED input (roadmap P15), not a fact and not a
    #    derived artifact. Its loader only READS; it must never write Project
    #    facts (ADR-006), mirroring the outline/market guards.
    brain_dir = RUNTIME_PKG / "brain"
    brain_offenders = []
    if brain_dir.exists():
        for p in _py_files(brain_dir):
            src = _source(p)
            if "registry\" / \"facts" in src or "registry' / 'facts" in src:
                brain_offenders.append(p.name)
    check("novel brain does not write registry facts directly",
          not brain_offenders, "; ".join(sorted(set(brain_offenders))))

    # 10. Serial production (roadmap P17 seed) orchestrates build->execute->state.
    #     It writes drafts as derived artifacts (via execute_package) but must
    #     never write Project facts itself (ADR-006).
    serial_dir = RUNTIME_PKG / "serialize"
    serial_offenders = []
    if serial_dir.exists():
        for p in _py_files(serial_dir):
            src = _source(p)
            if "registry\" / \"facts" in src or "registry' / 'facts" in src:
                serial_offenders.append(p.name)
    check("serial production does not write registry facts directly",
          not serial_offenders, "; ".join(sorted(set(serial_offenders))))

    # 11. The serialization schedule (roadmap P17) is a PROJECTION over an
    #     authored plan + the produced-draft count. It reads only; it must never
    #     write Project facts (ADR-006), like the brain/serial guards.
    schedule_dir = RUNTIME_PKG / "schedule"
    schedule_offenders = []
    if schedule_dir.exists():
        for p in _py_files(schedule_dir):
            src = _source(p)
            if "registry\" / \"facts" in src or "registry' / 'facts" in src:
                schedule_offenders.append(p.name)
    check("serialization schedule does not write registry facts directly",
          not schedule_offenders, "; ".join(sorted(set(schedule_offenders))))

    # 12. The Novel Dashboard (roadmap P18) is a pure read-side aggregation. It
    #     reads existing artifacts/projections; it must never write Project facts
    #     (ADR-006), like every other read-side subdomain.
    dashboard_dir = RUNTIME_PKG / "dashboard"
    dashboard_offenders = []
    if dashboard_dir.exists():
        for p in _py_files(dashboard_dir):
            src = _source(p)
            if "registry\" / \"facts" in src or "registry' / 'facts" in src:
                dashboard_offenders.append(p.name)
    check("novel dashboard does not write registry facts directly",
          not dashboard_offenders, "; ".join(sorted(set(dashboard_offenders))))

    # 13. Market Positioning (roadmap 4.5) reads the authored Position + Brain +
    #     derived Market Snapshot into an advisory admission verdict. It writes
    #     that verdict as a DERIVED artifact (registry/derived/market-admission/)
    #     but must never write Project facts (ADR-006), like every read-side
    #     subdomain before it.
    positioning_dir = RUNTIME_PKG / "positioning"
    positioning_offenders = []
    if positioning_dir.exists():
        for p in _py_files(positioning_dir):
            src = _source(p)
            if "registry\" / \"facts" in src or "registry' / 'facts" in src:
                positioning_offenders.append(p.name)
    check("market positioning does not write registry facts directly",
          not positioning_offenders, "; ".join(sorted(set(positioning_offenders))))

    # 14. Publishing OS (roadmap 4.6) folds existing products into Production
    #     Cards + Volume/Direction reviews. It writes those as DERIVED artifacts
    #     (registry/derived/production-card|review-report/) but must never write
    #     Project facts (ADR-006), like every read-side subdomain before it.
    publishing_dir = RUNTIME_PKG / "publishing"
    publishing_offenders = []
    if publishing_dir.exists():
        for p in _py_files(publishing_dir):
            src = _source(p)
            if "registry\" / \"facts" in src or "registry' / 'facts" in src:
                publishing_offenders.append(p.name)
    check("publishing OS does not write registry facts directly",
          not publishing_offenders, "; ".join(sorted(set(publishing_offenders))))

    # 15. The Fact Candidate Pipeline (roadmap Phase 5) is the PREPARATION half of
    #     prose->fact evolution. It extracts candidates and stages a plan as a
    #     DERIVED artifact (registry/derived/fact-candidates/), but must never
    #     write Project facts (ADR-006) — minting is a separate human-authorized
    #     workflow (ADR-009). This is the whole point of the subdomain, so the
    #     guard is load-bearing, not decorative.
    candidates_dir = RUNTIME_PKG / "candidates"
    candidates_offenders = []
    if candidates_dir.exists():
        for p in _py_files(candidates_dir):
            src = _source(p)
            if "registry\" / \"facts" in src or "registry' / 'facts" in src:
                candidates_offenders.append(p.name)
    check("fact candidate pipeline does not write registry facts directly",
          not candidates_offenders, "; ".join(sorted(set(candidates_offenders))))

    # 16. The mint executor (roadmap Phase 5.2) is the EXECUTION half of
    #     prose->fact evolution and the SYSTEM'S ONLY FACT-WRITER (ADR-009). This
    #     guard is the inverse of 7-15: rather than "subdomain X must not write
    #     facts", it asserts that the ONLY modules naming the registry/facts path
    #     are the loader (which reads) and runtime/mint/ (which writes). Any new
    #     module that reaches for facts/ fails here — the human-authority boundary
    #     stays crossable in exactly one auditable place.
    facts_literal = ('registry" / "facts', "registry' / 'facts")
    allowed = {"registry_loader.py"}  # reads facts; not a writer
    fact_path_offenders = []
    for p in files:
        if any(lit in _source(p) for lit in facts_literal):
            rel = p.relative_to(RUNTIME_PKG)
            if p.name in allowed or rel.parts[0] == "mint":
                continue
            fact_path_offenders.append(str(rel))
    check("mint is the only fact-writer (only loader + mint/ name the facts path)",
          not fact_path_offenders, "; ".join(sorted(set(fact_path_offenders))))

    # 17. The Derived Recompute Engine (roadmap Phase 5.3) auto-rebuilds only
    #     DETERMINISTIC folds and STAGES generative artifacts for a human. It must
    #     never regenerate a generative artifact itself — so it must not depend on
    #     a model/LLM. This guard makes the deterministic/generative partition
    #     load-bearing: if recompute ever imported the model seam, it could
    #     silently re-author prose, crossing the ADR-009 boundary. (Rebuilders are
    #     pure folds like memory.state.project_state — no model.)
    recompute_dir = RUNTIME_PKG / "recompute"
    recompute_model_offenders = []
    if recompute_dir.exists():
        for p in _py_files(recompute_dir):
            for line in _source(p).splitlines():
                s = line.strip()
                if s.startswith(("import ", "from ")) and (
                        "llm" in s or "execution.model" in s or "execution.agent" in s
                        or "execution.run" in s or "execute_package" in s):
                    recompute_model_offenders.append(f"{p.name}: {s}")
    check("recompute engine does not depend on a model (stages generative work, never regenerates it)",
          not recompute_model_offenders, "; ".join(recompute_model_offenders))

    # 18. The ID Mint Ledger (roadmap Phase 5.4) allocates entity IDs into an
    #     append-only ledger under registry/_meta/. The ledger is a FACT (it
    #     records what was minted), but it is NOT a registry/facts/** write — so
    #     idmint/ sits OUTSIDE guard 16's fact-path allowlist and must never name
    #     the facts path. It also must not import a model: allocation is a pure,
    #     deterministic max+1 fold (ID spec §8), never a generative act. If idmint
    #     ever reached for facts/ or a model, the physical ADR-009 split (only
    #     mint/ writes facts; only humans author) would leak into ordinal
    #     allocation.
    idmint_dir = RUNTIME_PKG / "idmint"
    idmint_offenders = []
    if idmint_dir.exists():
        for p in _py_files(idmint_dir):
            src = _source(p)
            if any(lit in src for lit in facts_literal):
                idmint_offenders.append(f"{p.name}: names facts path")
            for line in src.splitlines():
                s = line.strip()
                if s.startswith(("import ", "from ")) and (
                        "llm" in s or "execution.model" in s or "execution.agent" in s
                        or "execution.run" in s or "execute_package" in s):
                    idmint_offenders.append(f"{p.name}: {s}")
    check("id mint ledger writes no facts and imports no model (pure allocation)",
          not idmint_offenders, "; ".join(sorted(set(idmint_offenders))))

    # 19. Allocating an id (idmint.mint_id) is the act that BIRTHS a new entity,
    #     and writing that entity is a fact-write — so id allocation must stay
    #     coupled to the one authorized fact-writer (runtime/mint/). This guard
    #     asserts `mint_id` is CALLED only from mint/ (idmint itself defines it;
    #     mint/ consumes it). If any other subdomain could allocate an id, it
    #     could mint an entity outside the ADR-009 human-authorized crossing —
    #     the same leak guard 16 forbids for the facts path, here for the id
    #     namespace. (Read-only ledger helpers — load_ledger/max_ordinal/
    #     format_id — are unrestricted; only the allocating write is fenced.)
    mint_id_callers = []
    for p in files:
        rel = p.relative_to(RUNTIME_PKG)
        if rel.parts[0] in ("idmint", "mint"):
            continue  # definer + authorized consumer
        for line in _source(p).splitlines():
            s = line.strip()
            if s.startswith("#"):
                continue
            if "mint_id(" in s or "idmint.mint_id" in s:
                mint_id_callers.append(f"{rel}: {s}")
    check("id allocation (mint_id) is called only from the authorized fact-writer (mint/)",
          not mint_id_callers, "; ".join(sorted(set(mint_id_callers))))

    # 20. The Reader Signal Store (roadmap 5.6) imports REAL platform signals and
    #     folds them beside predictions. Like every read-side subdomain (guards
    #     7-15), it must never write Project facts (ADR-006) — a real reader signal
    #     is external evidence under sources/, not a story fact. And, uniquely, it
    #     must never CALIBRATE the model: the roadmap wires the seam but does not
    #     fire it, so signals/ must not import the model/generation/execution seam
    #     (mirroring guard #17 for recompute). If it ever reached for a model, the
    #     comparison-only 'never feed reality back into generation' discipline
    #     would leak.
    signals_dir = RUNTIME_PKG / "signals"
    signals_offenders = []
    if signals_dir.exists():
        for p in _py_files(signals_dir):
            src = _source(p)
            if any(lit in src for lit in facts_literal):
                signals_offenders.append(f"{p.name}: names facts path")
            for line in src.splitlines():
                s = line.strip()
                if s.startswith(("import ", "from ")) and (
                        "llm" in s or "execution.model" in s or "execution.agent" in s
                        or "execution.run" in s or "execute_package" in s):
                    signals_offenders.append(f"{p.name}: {s}")
    check("reader signal store writes no facts and imports no model (comparison-only, never calibrates)",
          not signals_offenders, "; ".join(sorted(set(signals_offenders))))

    # 21. The Narrative Director (roadmap Phase 6/7) turns state/quality/
    #     commercial/signal inputs into chapter objectives, briefs, critiques,
    #     rewrite decisions, and version selections. It is a READ-SIDE PLANNER: it
    #     decides WHAT a chapter should do and WHICH version to keep, but it does
    #     not itself generate prose — generation stays behind the Model seam in
    #     execution/. So director/ must never write Project facts (ADR-006, like
    #     every read-side subdomain) AND must never import a model/generation seam
    #     (mirroring guards #17/#20): if the director could regenerate prose, the
    #     "arbiter over signals, not a third rewrite engine" discipline — and the
    #     ADR-009 boundary between planning and outward action — would leak.
    director_dir = RUNTIME_PKG / "director"
    director_offenders = []
    if director_dir.exists():
        for p in _py_files(director_dir):
            src = _source(p)
            if any(lit in src for lit in facts_literal):
                director_offenders.append(f"{p.name}: names facts path")
            for line in src.splitlines():
                s = line.strip()
                if s.startswith(("import ", "from ")) and (
                        "llm" in s or "execution.model" in s or "execution.agent" in s
                        or "execution.run" in s or "execute_package" in s):
                    director_offenders.append(f"{p.name}: {s}")
    check("narrative director writes no facts and imports no model (read-side planner, not a rewrite engine)",
          not director_offenders, "; ".join(sorted(set(director_offenders))))

    # 22. Character Speech Profiles (roadmap §15) are an AUTHORED source — the
    #     expression-layer spec for how each character talks. Like the Novel Brain
    #     (guard #9) they are neither a story fact (ADR-006: the Character fact
    #     schema has no language field) nor a recomputed projection (ADR-008:
    #     character_runtime folds motivation, which is orthogonal to expression).
    #     So speech/ only READS the authored source: it must never write Project
    #     facts, AND — because expression is AUTHORED, never generated here — it
    #     must never import a model/generation seam (mirroring guards #17/#20/#21).
    #     If speech/ ever wrote facts it would blur the source/fact boundary; if it
    #     imported a model it would silently auto-author a voice the human never
    #     confirmed, crossing the ADR-009 authored-input boundary.
    speech_dir = RUNTIME_PKG / "speech"
    speech_offenders = []
    if speech_dir.exists():
        for p in _py_files(speech_dir):
            src = _source(p)
            if any(lit in src for lit in facts_literal):
                speech_offenders.append(f"{p.name}: names facts path")
            for line in src.splitlines():
                s = line.strip()
                if s.startswith(("import ", "from ")) and (
                        "llm" in s or "execution.model" in s or "execution.agent" in s
                        or "execution.run" in s or "execute_package" in s):
                    speech_offenders.append(f"{p.name}: {s}")
    check("character speech profiles write no facts and import no model (authored source, never generated)",
          not speech_offenders, "; ".join(sorted(set(speech_offenders))))

    # 23. Auto Project Genesis (roadmap M2) opens a book: it folds an outline into
    #     a Novel Brain draft (an authored source) and orchestrates landing the
    #     event/character/world batch. But it must NEVER write Project facts itself
    #     — that boundary crossing belongs to runtime/mint/ alone (guard #16). Like
    #     candidates/ (#15), genesis/ PREPARES and ORCHESTRATES; the only fact-write
    #     it triggers is via mint (genesis_apply), always human-confirmed (ADR-009).
    #     If genesis/ ever named the facts path directly, book-opening would become
    #     a second, unauditable way to write facts outside the mint subdomain.
    genesis_dir = RUNTIME_PKG / "genesis"
    genesis_offenders = []
    if genesis_dir.exists():
        for p in _py_files(genesis_dir):
            if any(lit in _source(p) for lit in facts_literal):
                genesis_offenders.append(f"{p.name}: names facts path")
    check("genesis writes no facts directly (lands only via mint, human-confirmed)",
          not genesis_offenders, "; ".join(sorted(set(genesis_offenders))))

    # 24. The Reference Quality Anchor (roadmap M9) measures human-selected,
    #     market-validated reference novels with the SAME deterministic detectors
    #     the runtime runs on generated chapters, folding them into a pinned
    #     comparison anchor. Its deterministic arm must be PURE: it must never
    #     write Project facts (a reference measurement is a derived read, ADR-006,
    #     not a story fact), AND it must never import a model/generation seam
    #     (mirroring guards #17/#20/#21/#22). The optional judge double-measure is
    #     opt-in: the reviewer is INJECTED by the caller (build_reference_profile's
    #     `reviewer`), so reference/ itself never reaches for the LM stack. If it
    #     imported a model, the "same corpus => same profile" reproducibility that
    #     makes the anchor a trustworthy quality ground-truth would break.
    reference_dir = RUNTIME_PKG / "reference"
    reference_offenders = []
    if reference_dir.exists():
        for p in _py_files(reference_dir):
            src = _source(p)
            if any(lit in src for lit in facts_literal):
                reference_offenders.append(f"{p.name}: names facts path")
            for line in src.splitlines():
                s = line.strip()
                if s.startswith(("import ", "from ")) and (
                        "llm" in s or "execution.model" in s or "execution.agent" in s
                        or "execution.run" in s or "execute_package" in s
                        or "quality_center" in s or "reader_sim" in s):
                    reference_offenders.append(f"{p.name}: {s}")
    check("reference quality anchor writes no facts and imports no model "
          "(deterministic arm is pure; judge reviewer is injected, not imported)",
          not reference_offenders, "; ".join(sorted(set(reference_offenders))))

    # 25. A prompt template's variables must be DECLARED, not just referenced.
    #     render_template pre-fills only DECLARED optionals, so a body that
    #     references {foo} without declaring it raises KeyError for every caller
    #     that doesn't happen to inject foo. Found live: chapter-draft.v12
    #     referenced {model_profile_note} and {constraint_pack_note} while
    #     declaring neither — it rendered ONLY because ChapterDraftAgent always
    #     setdefault()s both, and any replay / non-agent render path crashed.
    #     This is the deterministic half of the "prompt var = 3 places" rule
    #     (bound in binding.py, passed by the caller, DECLARED in the yaml); a
    #     variable missing from the third place is a latent crash, and a variable
    #     the templates never reference is a dead path that silently carries
    #     nothing to the model.
    prompt_dir = (RUNTIME_PKG.parent.parent / "AI-Novel-Standard"
                  / "contracts" / "prompts")
    undeclared = []
    if prompt_dir.exists():
        import yaml
        for p in sorted(prompt_dir.glob("*.prompt.yaml")):
            try:
                spec = yaml.safe_load(_source(p)) or {}
            except yaml.YAMLError as exc:
                undeclared.append(f"{p.name}: unparseable ({exc.__class__.__name__})")
                continue
            declared = set()
            for bucket in ("required", "optional"):
                declared |= set((spec.get("variables") or {}).get(bucket) or [])
            referenced = set()
            for msg in spec.get("messages") or []:
                referenced |= set(re.findall(r"\{(\w+)\}", msg.get("content") or ""))
            missing = referenced - declared
            if missing:
                undeclared.append(f"{p.name}: {sorted(missing)}")
    check("every prompt template declares the variables its body references "
          "(undeclared => KeyError for any caller that omits them)",
          not undeclared, "; ".join(undeclared))

    # 26. The built-but-never-wired RATCHET (see KNOWN_UNREACHABLE above).
    #     A module unreachable from the CLI / scripts / tools has no production
    #     path, no matter how green its unit tests are. The frozen set may only
    #     SHRINK: growth means a new orphan just landed, which is this repo's
    #     single most-repeated defect.
    unreachable = _unreachable_modules()
    new_orphans = sorted(unreachable - KNOWN_UNREACHABLE)
    check("no NEW unreachable runtime module (built != live ratchet): a module "
          "with no path from the CLI/scripts is dead on arrival — wire it or "
          "don't add it",
          not new_orphans, f"new orphans: {new_orphans}")

    #     The other half of the ratchet: once an orphan is wired, its allowlist
    #     entry must be deleted, or the guard silently tolerates a regression
    #     back to unwired later.
    wired = sorted(KNOWN_UNREACHABLE - unreachable)
    check("KNOWN_UNREACHABLE contains no module that is now wired (delete the "
          "entry when you wire one, so it can never silently regress)",
          not wired, f"now reachable, remove from allowlist: {wired}")

    print(f"\n{_passed} passed, {_failed} failed")
    return 0 if _failed == 0 else 1


def test_architecture_fitness():
    """pytest entry point for the guards above.

    Until this existed, every guard in this file ran ONLY under
    `python3 -m tests.test_fitness`: the module defines no `def test_*`, so
    `pytest tests/` collected NOTHING from it and all 25 architecture guards were
    silently absent from the suite. A guard that never runs cannot catch drift —
    which is exactly how the defects this file is meant to prevent kept landing.
    """
    assert main() == 0, "architecture fitness guards failed (see output above)"


if __name__ == "__main__":
    import sys
    sys.exit(main())
