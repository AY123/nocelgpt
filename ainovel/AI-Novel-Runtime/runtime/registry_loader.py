"""registry_loader.py — load a Project's Registry into memory (ANES v2).

Resource-resolution path (ADR-005). Reads the on-disk Registry layout defined by
the Standard's Registry Directory Specification:

    registry/facts/<type-dir>/<ID>.yaml   # one entity per file (SSOT)
    registry/derived/...                   # not loaded as facts (ADR-006)
    registry/_meta/registry-version        # monotone integer
    registry/_meta/standard.pin            # pinned Standard semver

Facts only. Nothing under derived/ is treated as authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import yaml

from .catalog import Catalog


@dataclass
class Registry:
    project_path: Path
    version: int
    standard_pin: str
    facts: Dict[str, dict] = field(default_factory=dict)  # id -> record

    def get(self, entity_id: str) -> dict | None:
        return self.facts.get(entity_id)

    def exists(self, entity_id: str) -> bool:
        return entity_id in self.facts

    def all_ids(self):
        return list(self.facts.keys())


def _read_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load(project_path: str | Path, catalog: Optional[Catalog] = None,
         schema_dir: Optional[str | Path] = None) -> Registry:
    """Load a Project's facts. If a catalog (or schema_dir to load one from) is
    provided, each fact's on-disk directory is checked against the catalog's
    declared facts_dir for its type — catching misfiled records and any drift
    between Project layout and the Standard."""
    project_path = Path(project_path)
    if catalog is None and schema_dir is not None:
        catalog = Catalog.load(schema_dir)

    meta = project_path / "registry" / "_meta"
    version = int((meta / "registry-version").read_text(encoding="utf-8").strip())
    pin = (meta / "standard.pin").read_text(encoding="utf-8").strip()

    facts: Dict[str, dict] = {}
    facts_root = project_path / "registry" / "facts"
    for record_path in sorted(facts_root.rglob("*.yaml")):
        record = _read_yaml(record_path)
        rid = record.get("id")
        if not rid:
            raise ValueError(f"{record_path}: record has no id")
        if rid in facts:
            raise ValueError(f"duplicate id {rid} at {record_path}")
        if catalog is not None:
            type_code = rid.split("-", 1)[0]
            expected = catalog.facts_dir(type_code)
            actual = record_path.parent.name
            if actual != expected:
                raise ValueError(
                    f"{record_path}: {type_code} record must live in "
                    f"facts/{expected}/, found in facts/{actual}/")
        # Stamp provenance the runtime needs but the file shouldn't carry.
        record["_source_path"] = str(record_path.relative_to(project_path))
        facts[rid] = record

    return Registry(project_path=project_path, version=version,
                    standard_pin=pin, facts=facts)
