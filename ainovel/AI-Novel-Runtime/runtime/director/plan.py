"""plan.py — Director chapter objective planning.

Produces the ChapterObjective artifact from chapter-level context. This module is
advisory and read-side: it never writes facts, never publishes, and never
calibrates real reader signals.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "AI-Novel-Standard" / "contracts" / "chapter-objective.schema.json"


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _next_id(prefix: str, seed: Optional[str] = None) -> str:
    if seed:
        return seed
    return f"{prefix}-00001"


def _prune_none(d: dict) -> dict:
    """Drop keys whose value is None. Optional string fields must be ABSENT, not
    null, or a `"type": "string"` schema rejects them (the fields are optional,
    so omission is the correct encoding of 'not supplied')."""
    return {k: v for k, v in d.items() if v is not None}


def build_chapter_objective(*, chapter_id: str, narrative_ir: Optional[dict] = None,
                            state: Optional[dict] = None,
                            quality: Optional[dict] = None,
                            commercial: Optional[dict] = None,
                            signals: Optional[dict] = None,
                            mandate: Optional[dict] = None,
                            long_arc_plan: Optional[dict] = None,
                            semantic_ledger: Optional[dict] = None,
                            consumption_evidence: Optional[dict] = None,
                            recomputed_state: Optional[dict] = None,
                            objective_id: Optional[str] = None) -> dict[str, Any]:
    narrative_ir = narrative_ir or {}
    quality = quality or {}
    commercial = commercial or {}
    signals = signals or {}
    long_arc_plan = long_arc_plan or {}
    semantic_ledger = semantic_ledger or {}
    objective = {
        "id": _next_id("OBJ", objective_id),
        "kind": "chapter_objective",
        "authority": "human",
        "gating": False,
        "schema_version": "1.0",
        "objective_id": _next_id("OBJ", objective_id),
        "chapter_id": chapter_id,
        "source": _prune_none({
            "narrative_ir_id": narrative_ir.get("id"),
            "state_hash": (state or {}).get("state_hash"),
            "quality_summary_ref": quality.get("id"),
            "commercial_summary_ref": commercial.get("id"),
            "signal_summary_ref": signals.get("id"),
        }),
        "primary_goal": narrative_ir.get("primary_goal") or narrative_ir.get("intent") or "推进章节核心冲突并兑现关键承诺",
        "secondary_goals": narrative_ir.get("secondary_goals") or [],
        "reader_question": narrative_ir.get("reader_question") or "主角接下来如何反应？",
        "promise_to_deliver": narrative_ir.get("payoff_target") or narrative_ir.get("promise_to_deliver") or [],
        "character_focus": narrative_ir.get("character_focus") or [],
        "plot_threads": narrative_ir.get("plot_threads") or [],
        "commercial_intent": _prune_none({
            "retention_focus": (commercial.get("retention_focus")
                                 or "next_chapter_pull"),
            "payoff_type": commercial.get("payoff_type") or "partial_payoff",
            "drop_risk_target": commercial.get("drop_risk_target") or "low",
            "payment_trigger": commercial.get("payment_trigger"),
        }),
        "pacing_role": narrative_ir.get("pacing_role") or "rising_action",
        "cliffhanger_type": narrative_ir.get("cliffhanger_type") or "reveal",
        "constraints": narrative_ir.get("constraints") or [
            "不得破坏角色连续性",
            "不得引入未授权新事实",
        ],
        "success_criteria": narrative_ir.get("success_criteria") or [
            "reader_question 明确",
            "章节末有追读动力",
            "角色行为符合 runtime 状态",
        ],
        "notes": narrative_ir.get("notes") or "",
    }
    if semantic_ledger:
        objective["semantic_ledger"] = semantic_ledger
    # Long-arc plan constraint (Phase 9.1): when a plan is supplied it sits
    # ABOVE the objective and can tighten the chapter band goal without changing
    # the existing default objective path.
    if long_arc_plan:
        bands = long_arc_plan.get("chapter_bands") or []
        for band in bands:
            if not isinstance(band, dict):
                continue
            start = int(band.get("start") or chapter_id)
            end = int(band.get("end") or chapter_id)
            # chapter_id may be non-numeric; fail open by only applying when the
            # chapter band clearly matches a chapter number suffix.
            try:
                chapter_no = int("".join(ch for ch in str(chapter_id) if ch.isdigit()) or 0)
            except Exception:
                chapter_no = 0
            if chapter_no and start <= chapter_no <= end:
                band_goal = band.get("goal")
                if band_goal:
                    objective["notes"] = (objective.get("notes") or "") + f"\n长弧目标：{band_goal}"
                    objective.setdefault("success_criteria", []).append(f"长弧目标达成：{band_goal}")
                break

    if consumption_evidence and consumption_evidence.get("mint_ids"):
        from .consumption import approved_state_constraints
        objective["source"]["consumption_evidence_hash"] = consumption_evidence.get("consumption_hash")
        if recomputed_state and recomputed_state.get("state_hash"):
            objective["source"]["recomputed_state_hash"] = recomputed_state["state_hash"]
        objective["constraints"] = list(objective["constraints"]) + approved_state_constraints(
            consumption_evidence, recomputed_state)

    # Narrative Mandate constraint (Phase 9.4): when a mandate is supplied it sits
    # ABOVE the objective — its escalation and inner shift are non-negotiable, so
    # they are appended as hard constraints the drafter must honor. Gated behind
    # `if mandate` so an objective built WITHOUT a mandate (every v6/v7 run) is
    # byte-identical to before this parameter existed.
    if mandate:
        esc = mandate.get("escalation") or {}
        ins = mandate.get("inner_shift") or {}
        wn = mandate.get("why_now") or {}
        extra_constraints = []
        if esc.get("kind") and esc.get("kind") != "flat":
            extra_constraints.append(
                f"冲突必须较上一章升级（{esc.get('from_level')}→{esc.get('to_level')}，"
                f"{esc.get('kind')}）")
        if ins.get("from") and ins.get("to"):
            extra_constraints.append(
                f"主角内在须发生变化（{ins.get('dimension')}：{ins['from']}→{ins['to']}）")
        if wn.get("cost_of_delay") == "none":
            extra_constraints.append("须补足行动紧迫性，避免温水章")
        if extra_constraints:
            objective["constraints"] = list(objective["constraints"]) + extra_constraints

    if semantic_ledger:
        from .semantic_ledger import render_semantic_ledger
        ledger_block = render_semantic_ledger(semantic_ledger)
        if ledger_block:
            ledger_block = "本章须遵守语义状态：\n" + ledger_block
            objective["constraints"] = list(objective["constraints"]) + [ledger_block]
    return objective


def validate_chapter_objective(obj: dict) -> list[str]:
    validator = Draft202012Validator(_load_schema())
    errs = []
    for e in sorted(validator.iter_errors(obj), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs


def render_chapter_objective(objective: dict) -> str:
    """Compress a ChapterObjective into a compact string for the v6 prompt's
    `chapter_objective` variable. Deterministic and bounded, mirroring
    render_chapter_ir's style. This is the TOP-LEVEL intent the drafter reads:
    what this chapter must accomplish for story + retention + commercial pull."""
    lines: list[str] = [f"章节主目标：{objective.get('primary_goal', '')}"]
    if objective.get("reader_question"):
        lines.append(f"读者核心疑问：{objective['reader_question']}")
    promises = objective.get("promise_to_deliver") or []
    if promises:
        lines.append("本章必须兑现：" + "；".join(str(p) for p in promises))
    ci = objective.get("commercial_intent") or {}
    ci_parts = []
    if ci.get("retention_focus"):
        ci_parts.append(f"留存焦点={ci['retention_focus']}")
    if ci.get("payoff_type"):
        ci_parts.append(f"回报类型={ci['payoff_type']}")
    if ci.get("drop_risk_target"):
        ci_parts.append(f"掉读目标={ci['drop_risk_target']}")
    if ci.get("payment_trigger"):
        ci_parts.append(f"付费触点={ci['payment_trigger']}")
    if ci_parts:
        lines.append("商业意图：" + "，".join(ci_parts))
    if objective.get("pacing_role"):
        lines.append(f"节奏定位：{objective['pacing_role']}")
    if objective.get("cliffhanger_type"):
        lines.append(f"章末钩子类型：{objective['cliffhanger_type']}")
    constraints = objective.get("constraints") or []
    if constraints:
        lines.append("硬约束：" + "；".join(str(c) for c in constraints))
    return "\n".join(lines)
