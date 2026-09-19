"""brief.py — Director brief generation.

Turns a ChapterObjective and supporting context into a compact, actionable brief
for drafting or rewriting. This module is advisory and read-side: it never
writes facts, never publishes, and never calibrates real reader signals.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "AI-Novel-Standard" / "contracts" / "director-brief.schema.json"


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _next_id(prefix: str, seed: Optional[str] = None) -> str:
    if seed:
        return seed
    return f"{prefix}-00001"


def _prune_none(d: dict) -> dict:
    """Drop keys whose value is None so optional string fields are ABSENT, not
    null (a `"type": "string"` schema rejects null)."""
    return {k: v for k, v in d.items() if v is not None}


def build_director_brief(*, chapter_id: str, objective: dict,
                         state: Optional[dict] = None,
                         narrative_ir: Optional[dict] = None,
                         quality: Optional[dict] = None,
                         commercial: Optional[dict] = None,
                         signals: Optional[dict] = None,
                         brief_id: Optional[str] = None) -> dict[str, Any]:
    state = state or {}
    narrative_ir = narrative_ir or {}
    quality = quality or {}
    commercial = commercial or {}
    signals = signals or {}
    brief = {
        "id": _next_id("DBR", brief_id),
        "kind": "director_brief",
        "authority": "human",
        "gating": False,
        "schema_version": "1.0",
        "brief_id": _next_id("DBR", brief_id),
        "chapter_id": chapter_id,
        "objective_ref": objective.get("id") or objective.get("objective_id"),
        "inputs": _prune_none({
            "state_hash": state.get("state_hash"),
            "character_runtime_hash": state.get("character_runtime_hash"),
            "narrative_ir_hash": narrative_ir.get("hash") or narrative_ir.get("state_hash"),
            "quality_summary_ref": quality.get("id"),
            "commercial_summary_ref": commercial.get("id"),
            "signal_summary_ref": signals.get("id"),
        }),
        "summary": {
            "chapter_purpose": objective.get("primary_goal") or "",
            "tone": narrative_ir.get("tone") or "紧张、克制",
            "priority": commercial.get("priority") or "push_conflict_and_hook",
        },
        "must_include": narrative_ir.get("must_include") or objective.get("promise_to_deliver") or [],
        "must_avoid": narrative_ir.get("must_avoid") or [
            "无意义说明性扩写",
            "角色行为与 runtime 冲突",
        ],
        "non_negotiables": objective.get("constraints") or [
            "保持事实一致",
            "保持人物连续",
        ],
        "rewrite_focus": quality.get("rewrite_focus") or [
            "强化动机",
            "压缩铺陈",
            "增强结尾钩子",
        ],
        "decision_rationale": [
            *(quality.get("rationale") or []),
            *(commercial.get("rationale") or []),
            *(signals.get("rationale") or []),
        ],
        "notes": narrative_ir.get("notes") or "",
    }
    return brief


def validate_director_brief(obj: dict) -> list[str]:
    validator = Draft202012Validator(_load_schema())
    errs = []
    for e in sorted(validator.iter_errors(obj), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs


def render_director_brief(brief: dict) -> str:
    """Compress a DirectorBrief into a compact string for the v6 prompt's
    `director_brief` variable. Deterministic and bounded, mirroring
    render_chapter_objective's style. This is the ACTIONABLE layer: the
    must-include / must-avoid / non-negotiable instructions and rewrite focus."""
    lines: list[str] = []
    summary = brief.get("summary") or {}
    if summary.get("chapter_purpose"):
        lines.append(f"章节目的：{summary['chapter_purpose']}")
    if summary.get("tone"):
        lines.append(f"基调：{summary['tone']}")
    if summary.get("priority"):
        lines.append(f"优先事项：{summary['priority']}")
    must_include = brief.get("must_include") or []
    if must_include:
        lines.append("必须包含：" + "；".join(str(x) for x in must_include))
    must_avoid = brief.get("must_avoid") or []
    if must_avoid:
        lines.append("必须避免：" + "；".join(str(x) for x in must_avoid))
    non_neg = brief.get("non_negotiables") or []
    if non_neg:
        lines.append("不可妥协：" + "；".join(str(x) for x in non_neg))
    rewrite_focus = brief.get("rewrite_focus") or []
    if rewrite_focus:
        lines.append("改写着力点：" + "；".join(str(x) for x in rewrite_focus))
    return "\n".join(lines)
