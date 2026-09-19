"""loader.py — load & validate REAL reader signals (ANES v2, roadmap P5.6).

A reader signal is external ground-truth (real platform 订阅/追读/掉粉/打赏),
imported by an operator under sources/reader-signals/*.yaml. Like the Novel Brain
and the Market Snapshot, its ABSENCE is not an error — a project has no real
signals until it ships. This module only READS; it never writes facts (ADR-006).

The signal is DATA, not a verdict. Comparing it against a prediction is a separate
step (reconcile.py), which is the comparison-only, never-gating, never-calibrating
part. Loading never touches the model.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import yaml
from jsonschema import Draft202012Validator

_SCHEMA_REL = ("contracts", "reader-signal.schema.json")
_SIGNALS_REL = ("sources", "reader-signals")


def signals_dir(project_path: str | Path) -> Path:
    return Path(project_path).joinpath(*_SIGNALS_REL)


def _schema_path(standard_root: Optional[str | Path]) -> Path:
    if standard_root is not None:
        return Path(standard_root).joinpath(*_SCHEMA_REL)
    standard = Path(__file__).resolve().parents[3] / "AI-Novel-Standard"
    return standard.joinpath(*_SCHEMA_REL)


def validate_signal(signal: dict, *, standard_root: Optional[str | Path] = None) -> List[str]:
    """Return schema-validation error messages (empty == valid)."""
    schema = _schema_path(standard_root)
    validator = Draft202012Validator(json.loads(schema.read_text(encoding="utf-8")))
    errs = []
    for e in sorted(validator.iter_errors(signal), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs


def load_reader_signals(project_path: str | Path) -> List[dict]:
    """Return every imported reader signal (parsed, NOT validated), in stable
    filename order. A project with no signals dir / no files yields [] — absence
    is not an error, exactly like load_brain/load_market_snapshot for their
    single-file inputs. A malformed file surfaces via `signals check`
    (validate_signal), not here."""
    d = signals_dir(project_path)
    if not d.exists():
        return []
    out: List[dict] = []
    for p in sorted(d.glob("*.yaml")):
        if p.name.startswith("_"):  # commented scaffold/example files
            continue
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data:
            out.append(data)
    return out


def signal_for_chapter(project_path: str | Path, chapter_id: str) -> Optional[dict]:
    """The most-recently-collected chapter-scoped signal for a chapter id, or None.
    'Most recent' by collected_at (lexicographic ISO-8601 sorts chronologically),
    so a later re-measurement supersedes an earlier one deterministically."""
    matches = [s for s in load_reader_signals(project_path)
               if s.get("scope") == "chapter" and s.get("chapter_id") == chapter_id]
    if not matches:
        return None
    return max(matches, key=lambda s: s.get("collected_at", ""))
