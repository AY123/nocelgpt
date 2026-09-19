"""loader.py — load & validate the authored Published Log (ANES v2).

The Published Log is an AUTHORED input (like the Novel Brain and Serial Plan),
not a fact and not a derived artifact. It lives at sources/published-log.yaml and
records which chapters a human has AUTHORIZED as published (ADR-009). Consumers
treat its ABSENCE as "nothing authorized as published yet" and fall back. This
module only READS; it never writes the log (ADR-009) and never writes facts
(ADR-006).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import yaml
from jsonschema import Draft202012Validator

_SCHEMA_REL = ("contracts", "published-log.schema.json")


def published_log_path(project_path: str | Path) -> Path:
    return Path(project_path) / "sources" / "published-log.yaml"


def _schema_path(standard_root: Optional[str | Path]) -> Path:
    if standard_root is not None:
        return Path(standard_root).joinpath(*_SCHEMA_REL)
    standard = Path(__file__).resolve().parents[3] / "AI-Novel-Standard"
    return standard.joinpath(*_SCHEMA_REL)


def validate_published_log(log: dict, *,
                           standard_root: Optional[str | Path] = None) -> List[str]:
    """Return a list of schema-validation error messages (empty == valid)."""
    schema = _schema_path(standard_root)
    validator = Draft202012Validator(json.loads(schema.read_text(encoding="utf-8")))
    errs = []
    for e in sorted(validator.iter_errors(log), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs


def load_published_log(project_path: str | Path) -> Optional[dict]:
    """Return the authored Published Log if one exists, else None. Absence is not
    an error. Returns the parsed dict WITHOUT validating (call
    validate_published_log)."""
    path = published_log_path(project_path)
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))
