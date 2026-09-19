"""w12_mint_walkthrough.py — walk W12 stage→approve→mint→recompute with an AI approver.

Simulates the human authorization step (ADR-009) end-to-end IN AN ISOLATED SANDBOX,
never the live registry. Per chapter: LLM-extract fact candidates (replay-cached),
an AI "approver" decides which to accept, then execute_mint(confirmed=True) writes
the accepted additive/new facts and recompute rebuilds stale folds.

DISCIPLINE (hard):
  - Operates ONLY on a sandbox registry copy (arg1). NEVER writes live facts.
  - actor="AI-SIM-approver" on every mint receipt — the ADR-009 audit trail stays
    honest: these are AI-simulated authorizations, NOT human ones.
  - conflicting/consistent/unverifiable candidates are auto-refused by plan_mint
    (by design) — only additive + name-establishing new can mint. The AI approver
    cannot override that; ch14's 18 conflicts will NOT be minted (correct).
  - This proves the pipeline runs end-to-end; it is NOT a real fact commit.

Usage (from AI-Novel-Runtime/):
  PYTHONPATH=. python3 scripts/w12_mint_walkthrough.py <sandbox> [N]
"""
from __future__ import annotations

import json
import glob
import os
import sys
from collections import Counter
from pathlib import Path

RT = Path(__file__).resolve().parents[1]
PILOT = RT.parent / "genesis-pilot"
DRAFTS = PILOT / "analysis" / "run-00025-snapshot" / "derived" / "drafts"
SCHEMA_DIR = RT.parent / "AI-Novel-Standard" / "phase-1" / "generated" / "json-schema"
ACTOR = "AI-SIM-approver"


def _load_env() -> None:
    for f in (PILOT / ".env", RT.parent / ".env"):
        if f.is_file():
            for line in f.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


# Types whose whole required-field set can be synthesized from a name (mint's
# _SYNTHESIZABLE_REQUIRED = {id,name,fact_version,status}). Only these can mint a
# `new` entity this phase; Event/Relationship/Timeline/WorldRule need structured
# fields and are refused (a structured authoring workflow, not a name-mint).
_MINTABLE_NEW_TYPES = {"Character", "Item", "CHR", "ITM"}

# Additive fields whose value is a plain scalar/object-of-string in the frozen
# schema, so an LLM prose value validates directly. Fields like abilities /
# possessions are arrays of ENTITY REFERENCES (MAG-/TEC-/ITM-\d{5,}) — they need
# the referenced entity minted first, a multi-step workflow, so a prose value can
# never validate there. Restricting to physical_facts.* keeps the walkthrough to
# candidates that can actually complete a mint.
_DIRECT_ADDITIVE_PREFIXES = ("physical_facts.",)


def _ai_approve(plan_items: list[dict]) -> list[str]:
    """AI approver policy: accept only what execute_mint can actually WRITE AND
    PASS THE POST-MINT SCHEMA GATE:
      - additive on a directly-schema-valid field (physical_facts.* — object of
        strings). Skips abilities/possessions (entity-ref arrays needing a prior
        mint) and free-form fields whose prose value fails schema validation.
      - name-establishing new (field=='name') of a synthesizable type (CHR/ITM).
    conflicting/consistent/unverifiable are never accepted (human disambiguation).
    This is deliberately narrow: it exposes that most LLM 'actionable' candidates
    need a structured multi-step workflow, not a one-shot mint."""
    accepted = []
    for it in plan_items:
        cls = it.get("classification")
        field = it.get("field") or ""
        if cls == "additive" and field.startswith(_DIRECT_ADDITIVE_PREFIXES):
            accepted.append(it["candidate_id"])
        elif cls == "new" and field == "name" \
                and it.get("target_type") in _MINTABLE_NEW_TYPES:
            accepted.append(it["candidate_id"])
    return accepted


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: w12_mint_walkthrough.py <sandbox> [N]")
    sandbox = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 33
    _load_env()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY not set — cannot run LLM extraction")

    from runtime.candidates.plan import run_w12_fact_reflow
    from runtime.execution.llm_model import LLMExecutionModel
    from runtime.mint import execute_mint
    from runtime.mint.executor import MintRefused
    from runtime import recompute
    from runtime.registry_loader import load as load_registry

    replay = str(Path(sandbox) / "registry" / "derived" / "serial-replay-w12probe-gen")
    model = LLMExecutionModel(provider="deepseek", model_id="deepseek-chat",
                              temperature=0.0, replay_dir=replay)

    files = sorted(glob.glob(str(DRAFTS / "*.json")))[:n]
    print(f"AI-mint walkthrough over {len(files)} chapters (sandbox={sandbox})\n")

    totals = Counter()
    minted_facts = 0
    refused = 0
    receipts = []
    for f in files:
        env = json.load(open(f))
        draft = env["draft"]
        tid = draft["task_id"]
        res = run_w12_fact_reflow(project_path=sandbox, plan_id=f"W12-{tid}",
                                  draft=draft, model=model)
        plan = res["plan"]
        counts = res["reconciled_counts"]
        for k, v in counts.items():
            totals[k] += v
        accepted = _ai_approve(plan["items"])
        if not accepted:
            print(f"  {tid}: no mintable candidates (counts={counts})")
            continue
        try:
            receipt = execute_mint(
                project_path=sandbox, plan=plan, accepted=accepted,
                schema_dir=str(SCHEMA_DIR), confirmed=True, actor=ACTOR)
            rec = recompute.execute_recompute(
                load_registry(sandbox, schema_dir=str(SCHEMA_DIR)), sandbox,
                mint_receipt=receipt)
            minted_facts += len(receipt["minted"])
            receipts.append(receipt["id"])
            print(f"  {tid}: minted {len(receipt['minted'])}/{len(accepted)} "
                  f"({counts}) → {receipt['id']}, recompute {rec['id']} "
                  f"impacted={len(rec.get('impacted', []))}")
        except MintRefused as e:
            refused += 1
            print(f"  {tid}: REFUSED ({e.reason}) — {str(e.detail)[:80]}")

    print(f"\n=== walkthrough summary ===")
    print(f"chapters            : {len(files)}")
    print(f"reconciled totals   : {dict(totals)}")
    print(f"mint receipts        : {len(receipts)}")
    print(f"facts minted         : {minted_facts}")
    print(f"mints refused        : {refused}")
    print(f"conflicting (never minted, human-only): {totals['conflicting']}")

    reg = load_registry(sandbox, schema_dir=str(SCHEMA_DIR))
    print(f"sandbox facts after  : {len(reg.all_ids())} "
          f"(started 41; delta = new entities minted)")

    out = {
        "kind": "w12_mint_walkthrough",
        "mode": "AI-SIMULATED (actor=%s) — sandbox only, NOT live facts" % ACTOR,
        "chapters": len(files),
        "reconciled_totals": dict(totals),
        "mint_receipts": receipts,
        "facts_minted": minted_facts,
        "mints_refused": refused,
        "conflicting_never_minted": totals["conflicting"],
        "sandbox_facts_after": len(reg.all_ids()),
    }
    dest = PILOT / "analysis" / "w12-mint-walkthrough.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
