"""loader.py — load & validate the authored Serial Plan (ANES v2, roadmap P17).

The Serial Plan is an AUTHORED input (like the Novel Brain), not a fact and not a
derived artifact. It lives at sources/serial-plan.yaml. Consumers treat its
ABSENCE as "no plan authored yet" and fall back — like load_brain. This module
only READS; it never writes facts (ADR-006).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import yaml
from jsonschema import Draft202012Validator

_SCHEMA_REL = ("contracts", "serial-plan.schema.json")


def plan_path(project_path: str | Path) -> Path:
    return Path(project_path) / "sources" / "serial-plan.yaml"


def _schema_path(standard_root: Optional[str | Path]) -> Path:
    if standard_root is not None:
        return Path(standard_root).joinpath(*_SCHEMA_REL)
    standard = Path(__file__).resolve().parents[3] / "AI-Novel-Standard"
    return standard.joinpath(*_SCHEMA_REL)


def validate_plan(plan: dict, *, standard_root: Optional[str | Path] = None) -> List[str]:
    """Return a list of schema-validation error messages (empty == valid)."""
    schema = _schema_path(standard_root)
    validator = Draft202012Validator(json.loads(schema.read_text(encoding="utf-8")))
    errs = []
    for e in sorted(validator.iter_errors(plan), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs


def load_plan(project_path: str | Path) -> Optional[dict]:
    """Return the authored Serial Plan if one exists, else None. Absence is not
    an error. Returns the parsed dict WITHOUT validating (call validate_plan)."""
    path = plan_path(project_path)
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))
