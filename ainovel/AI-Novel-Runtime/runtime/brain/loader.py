"""loader.py — load & validate the authored Novel Brain (ANES v2, roadmap P15).

The Brain is an AUTHORED input, not a fact and not a derived artifact. It lives
at sources/novel-brain.yaml. Consumers treat its ABSENCE as "no brain authored
yet" and fall back to defaults — exactly like load_market_snapshot returns None
when no snapshot exists. This module only READS; it never writes facts (ADR-006).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import yaml
from jsonschema import Draft202012Validator

# The Brain schema is a Standard artifact contract. Resolve it relative to the
# Runtime repo's sibling Standard, matching how execution.agent finds prompts.
_SCHEMA_REL = ("contracts", "novel-brain.schema.json")


def brain_path(project_path: str | Path) -> Path:
    return Path(project_path) / "sources" / "novel-brain.yaml"


def _schema_path(standard_root: Optional[str | Path]) -> Path:
    if standard_root is not None:
        return Path(standard_root).joinpath(*_SCHEMA_REL)
    # default: the sibling AI-Novel-Standard (parents[3] == repo root, as in agent)
    standard = Path(__file__).resolve().parents[3] / "AI-Novel-Standard"
    return standard.joinpath(*_SCHEMA_REL)


def validate_brain(brain: dict, *, standard_root: Optional[str | Path] = None) -> List[str]:
    """Return a list of schema-validation error messages (empty == valid)."""
    schema = _schema_path(standard_root)
    validator = Draft202012Validator(
        json.loads(schema.read_text(encoding="utf-8")))
    errs = []
    for e in sorted(validator.iter_errors(brain), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs


def load_brain(project_path: str | Path) -> Optional[dict]:
    """Return the authored Novel Brain if one exists, else None.

    Absence is not an error: a project may have no Brain yet, and consumers fall
    back to their defaults. Returns the parsed dict WITHOUT validating (call
    validate_brain to check it); a malformed file surfaces via `brain check`.
    """
    path = brain_path(project_path)
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def brain_style_directive(brain: dict) -> str:
    """Render the Brain's writing_style + forbidden_style into the single string
    the chapter-draft prompt's `style` variable expects. Deterministic: same
    Brain => same directive (stable ordering, no time/randomness)."""
    ws = brain.get("writing_style", {}) or {}
    lines: List[str] = []
    voice = ws.get("voice")
    if voice:
        lines.append(f"Voice: {voice}")
    for key, label in (("pov", "POV"), ("pacing", "Pacing")):
        val = ws.get(key)
        if val:
            lines.append(f"{label}: {val}")
    devices = ws.get("devices") or []
    if devices:
        lines.append("Devices: " + ", ".join(devices))
    forbidden = brain.get("forbidden_style") or []
    if forbidden:
        lines.append("Never: " + "; ".join(forbidden))
    return "\n".join(lines) if lines else "neutral literary prose"
