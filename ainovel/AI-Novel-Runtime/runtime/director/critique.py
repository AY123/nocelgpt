"""critique.py — Director critique generation.

Turns a draft and supporting context into a structured critique. This module is
advisory and read-side: it never writes facts, never publishes, and never
calibrates real reader signals.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "AI-Novel-Standard" / "contracts" / "director-critique.schema.json"


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def build_director_critique(*, chapter_id: str, draft: Optional[dict] = None,
                            objective: Optional[dict] = None,
                            quality: Optional[dict] = None,
                            commercial: Optional[dict] = None,
                            signals: Optional[dict] = None) -> dict[str, Any]:
    draft = draft or {}
    quality = quality or {}
    commercial = commercial or {}
    signals = signals or {}
    problems = []
    if quality.get("problem_dimensions"):
        problems.extend(quality["problem_dimensions"])
    if not problems:
        problems = [
            {"dimension": "pacing", "severity": "medium", "issue": "章节节奏需要进一步收束"},
            {"dimension": "hook_strength", "severity": "medium", "issue": "章节末钩子不够明确"},
        ]
    return {
        "id": draft.get("critique_id") or f"CRT-{chapter_id[-5:] if chapter_id else '00001'}",
        "kind": "director_critique",
        "authority": "human",
        "gating": False,
        "schema_version": "1.0",
        "chapter_id": chapter_id,
        "objective_ref": (objective or {}).get("id") or (objective or {}).get("objective_id"),
        "draft_ref": draft.get("id") or draft.get("content_hash"),
        "trigger_sources": [k for k, v in (("quality_center", quality), ("commercial_loop", commercial), ("reader_signals", signals)) if v],
        "problem_dimensions": problems,
        "strengths": draft.get("strengths") or ["基本事实连续", "角色关系未明显失真"],
        "scope": ["middle_section", "ending"],
        "actions": [
            "压缩说明性段落",
            "强化冲突推进",
            "增强结尾钩子",
        ],
        "priority": "high",
        "expected_improvement": [
            "提升 next_chapter_pull",
            "降低 drop_risk",
            "提高章节末悬念清晰度",
        ],
        "acceptance_threshold": {
            "quality_min": quality.get("quality_min", 80),
            "commercial_min": commercial.get("commercial_min", 75),
        },
        "human_notes": "优先保留核心冲突，不要把章节改成纯信息说明。",
        "notes": signals.get("note") or "",
    }


def validate_director_critique(obj: dict) -> list[str]:
    validator = Draft202012Validator(_load_schema())
    errs = []
    for e in sorted(validator.iter_errors(obj), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs
