"""loader.py — load & validate the authored Market Position (roadmap 4.5).

The Market Position is an AUTHORED input, not a fact and not a derived artifact.
It lives at sources/market-position.yaml. Consumers treat its ABSENCE as "no
positioning authored yet" and degrade — exactly like load_brain / load_market_
snapshot return None when nothing exists. This module only READS; it never writes
facts (ADR-006), mirroring the brain loader.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import yaml
from jsonschema import Draft202012Validator

_SCHEMA_REL = ("contracts", "market-position.schema.json")


def position_path(project_path: str | Path) -> Path:
    return Path(project_path) / "sources" / "market-position.yaml"


def _schema_path(standard_root: Optional[str | Path]) -> Path:
    if standard_root is not None:
        return Path(standard_root).joinpath(*_SCHEMA_REL)
    standard = Path(__file__).resolve().parents[3] / "AI-Novel-Standard"
    return standard.joinpath(*_SCHEMA_REL)


def validate_position(position: dict, *,
                      standard_root: Optional[str | Path] = None) -> List[str]:
    """Return a list of schema-validation error messages (empty == valid)."""
    schema = _schema_path(standard_root)
    validator = Draft202012Validator(
        json.loads(schema.read_text(encoding="utf-8")))
    errs = []
    for e in sorted(validator.iter_errors(position), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs


def load_position(project_path: str | Path) -> Optional[dict]:
    """Return the authored Market Position if one exists, else None.

    Absence is not an error: a project may have no positioning yet, and the
    admission check degrades to a 'hold' (nothing to admit). Returns the parsed
    dict WITHOUT validating (call validate_position to check it). A pristine
    all-commented scaffold parses to None/empty and is treated as absent, so the
    admission check never false-fails a fresh project.
    """
    path = position_path(project_path)
    if not path.exists():
        return None
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict) or not parsed:
        return None
    return parsed
