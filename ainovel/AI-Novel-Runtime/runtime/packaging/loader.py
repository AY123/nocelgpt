"""loader.py — load & validate the authored Book Packaging (规范 §3).

Packaging is an AUTHORED input, not a fact and not a derived artifact. It lives at
sources/book-packaging.yaml. Consumers treat its ABSENCE as "no packaging authored
yet" and degrade — exactly like load_brain / load_market_snapshot return None. This
module only READS; it never writes facts (ADR-006).

Why a NEW artifact class instead of new fields on an existing one: both plausible
homes are frozen with `additionalProperties: false` — outline.schema.json (which has
title/logline/core_hook but no blurb/tags) and market-position.schema.json. Per §2,
a frozen product gets no new fields; a new runtime-level concern becomes its own
artifact. So packaging is a third authored source alongside novel-brain and
market-position, and neither frozen contract is touched.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import yaml
from jsonschema import Draft202012Validator

_SCHEMA_REL = ("contracts", "book-packaging.schema.json")


def packaging_path(project_path: str | Path) -> Path:
    return Path(project_path) / "sources" / "book-packaging.yaml"


def _schema_path(standard_root: Optional[str | Path]) -> Path:
    if standard_root is not None:
        return Path(standard_root).joinpath(*_SCHEMA_REL)
    standard = Path(__file__).resolve().parents[3] / "AI-Novel-Standard"
    return standard.joinpath(*_SCHEMA_REL)


def validate_packaging(packaging: dict, *,
                       standard_root: Optional[str | Path] = None) -> List[str]:
    """Return a list of schema-validation error messages (empty == valid)."""
    schema = _schema_path(standard_root)
    validator = Draft202012Validator(
        json.loads(schema.read_text(encoding="utf-8")))
    errs = []
    for e in sorted(validator.iter_errors(packaging), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs


def load_packaging(project_path: str | Path) -> Optional[dict]:
    """Return the authored packaging if one exists, else None.

    Absence is not an error: a project may have no packaging yet and consumers
    degrade. Returns the parsed dict WITHOUT validating (call validate_packaging);
    a malformed file surfaces through the check command, never mid-generation.
    """
    path = packaging_path(project_path)
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        # A corrupt packaging file must not crash a production run — the same
        # degrade discipline load_project_outline uses for corrupt outlines.
        return None


def packaging_promises(packaging: Optional[dict]) -> List[dict]:
    """The declared promises, normalized: every entry has `must_appear_by` filled
    in from the schema default (3 — the 黄金三章 window) and `evidence_terms` as a
    list. Malformed entries are dropped rather than raising, so a half-authored
    file still yields the promises that ARE complete.
    """
    out: List[dict] = []
    for p in (packaging or {}).get("promises") or []:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("promise_id") or "").strip()
        statement = str(p.get("statement") or "").strip()
        if not pid or not statement:
            continue
        by = p.get("must_appear_by")
        if not isinstance(by, int) or isinstance(by, bool) or by < 1:
            by = 3
        terms = [str(t).strip() for t in (p.get("evidence_terms") or [])
                 if str(t).strip()]
        out.append({
            "promise_id": pid,
            "promise_type": str(p.get("promise_type") or "").strip(),
            "statement": statement,
            "must_appear_by": by,
            "evidence_terms": terms,
        })
    return out
