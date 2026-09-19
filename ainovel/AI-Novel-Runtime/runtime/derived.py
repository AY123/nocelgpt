"""derived.py — derived artifact lifecycle (ANES v2, ADR-006).

Phase 3 began producing derived artifacts (ChapterDraft). This module gives them
a lifecycle the spec always required but nothing enforced:

  - LOCATION: derived artifacts are written under the Project's
    registry/derived/<category>/, never to an arbitrary path and never to facts/.
  - INDEX:    a provenance index (registry/derived/_index.yaml) records each
    artifact's id, category, path, content hash, and the pinned sources it was
    derived from.
  - STALENESS: a derived artifact is STALE when any source it was derived from
    (`derived_from: ID@vN`) is now behind the entity's current fact_version, or
    when the source no longer exists. Stale artifacts must not be consumed as
    truth (ADR-006). This is a DETERMINISTIC check.

It never writes facts and never lets a derived artifact feed back into facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from . import refs
from .registry_loader import Registry

DERIVED_ROOT = ("registry", "derived")
INDEX_NAME = "_index.yaml"


@dataclass
class StalenessFinding:
    artifact_id: str
    reason: str

    def __str__(self):
        return f"[stale] {self.artifact_id}: {self.reason}"


def derived_dir(project_path: str | Path, category: str) -> Path:
    return Path(project_path).joinpath(*DERIVED_ROOT, category)


def index_path(project_path: str | Path) -> Path:
    return Path(project_path).joinpath(*DERIVED_ROOT, INDEX_NAME)


def _load_index(project_path: str | Path) -> dict:
    p = index_path(project_path)
    if not p.exists():
        return {"artifacts": []}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {"artifacts": []}


def write_artifact(
    *,
    project_path: str | Path,
    category: str,
    artifact_id: str,
    artifact: dict,
    serialized: str,
) -> str:
    """Write a derived artifact under registry/derived/<category>/ and register
    it in the provenance index. Returns the relative path written.

    Anchoring + indexing are what make the artifact governable (ADR-006): it has
    a known home and its provenance is queryable for staleness.
    """
    project_path = Path(project_path)
    out = derived_dir(project_path, category)
    out.mkdir(parents=True, exist_ok=True)
    rel = Path(*DERIVED_ROOT, category, f"{artifact_id}.json")
    (project_path / rel).write_text(serialized, encoding="utf-8")

    index = _load_index(project_path)
    entries = [
        entry for entry in index.get("artifacts", [])
        if not (entry.get("id") == artifact_id
                and entry.get("category") == category)
    ]
    entries.append({
        "id": artifact_id,
        "category": category,
        "path": str(rel),
        "content_hash": artifact.get("content_hash"),
        "derived_from": list(artifact.get("provenance", {}).get("derived_from", [])),
        "source_version": artifact.get("provenance", {}).get("source_version"),
    })
    index["artifacts"] = sorted(entries, key=lambda e: e["id"])
    index_path(project_path).write_text(
        yaml.safe_dump(index, sort_keys=False, allow_unicode=True),
        encoding="utf-8")
    return str(rel)


def check_staleness(reg: Registry, derived_from: List[str]) -> List[str]:
    """Return reasons a set of pinned sources is stale vs the current Registry
    (empty == fresh). A pin `ID@vN` is stale if the entity is gone or its current
    fact_version > N."""
    reasons = []
    for pin in derived_from:
        ref = refs.parse(pin)
        if not ref.is_local:
            continue  # cross-project staleness handled by the (future) resolver
        target = reg.get(ref.id)
        if target is None:
            reasons.append(f"{ref.id} no longer exists")
            continue
        current = int(target.get("fact_version", 0))
        pinned = ref.pinned_version
        if pinned is not None and current > pinned:
            reasons.append(f"{ref.id} advanced v{pinned} -> v{current}")
    return reasons


def audit_index(reg: Registry, project_path: str | Path) -> List[StalenessFinding]:
    """Check every indexed derived artifact for staleness against the Registry."""
    index = _load_index(project_path)
    findings = []
    for entry in index.get("artifacts", []):
        reasons = check_staleness(reg, entry.get("derived_from", []))
        for r in reasons:
            findings.append(StalenessFinding(entry["id"], r))
    return findings
