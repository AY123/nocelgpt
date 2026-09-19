"""catalog.py — read the Standard's generated entity catalog (ANES v2).

The catalog (generated from the IDL by the Standard, ADR-007) is the single
source of the type_code -> {entity, facts_dir, scope, schema_file} mapping.

Before this module, Runtime hardcoded that mapping in two places
(registry_loader.TYPE_DIR and validator.TYPE_TO_ENTITY), which could drift from
the Standard whenever a new entity type was added. Now both read the catalog.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class CatalogEntry:
    type_code: str
    entity: str
    facts_dir: str
    scope: str
    schema_file: str
    order: int = 999


class Catalog:
    def __init__(self, by_type_code: Dict[str, CatalogEntry]):
        self._by_code = by_type_code

    @classmethod
    def load(cls, schema_dir: str | Path) -> "Catalog":
        path = Path(schema_dir) / "catalog.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = {}
        for code, rec in data["by_type_code"].items():
            entries[code] = CatalogEntry(
                type_code=rec["type_code"],
                entity=rec["entity"],
                facts_dir=rec["facts_dir"],
                scope=rec["scope"],
                schema_file=rec["schema_file"],
                order=rec.get("order", 999),
            )
        return cls(entries)

    def entry(self, type_code: str) -> CatalogEntry:
        if type_code not in self._by_code:
            raise ValueError(f"unknown type_code {type_code} (not in catalog)")
        return self._by_code[type_code]

    def facts_dir(self, type_code: str) -> str:
        return self.entry(type_code).facts_dir

    def entity_name(self, type_code: str) -> str:
        return self.entry(type_code).entity

    def schema_file(self, type_code: str) -> str:
        return self.entry(type_code).schema_file

    def type_codes(self):
        return list(self._by_code.keys())

    def facts_dirs(self):
        """Unique facts directories, for the loader to scan."""
        return sorted({e.facts_dir for e in self._by_code.values()})

    def emit_order(self) -> Dict[str, int]:
        """type_code -> declared emit order (from the Standard's IDL).

        The single source of bundle ordering, replacing the Runtime's old
        hardcoded TYPE_ORDER list.
        """
        return {code: e.order for code, e in self._by_code.items()}
