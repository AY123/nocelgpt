"""manifest.py — build manifest for reproducibility & rollback (ANES v2).

Every build emits a manifest recording exactly what went into it, so a build can
be reproduced or rolled back. This is the runtime counterpart to the Standard's
PHASE-1-FREEZE manifest: that freezes the contract, this freezes one build.

Reproducibility semantics (two distinct guarantees — do not conflate):
  - The Task PACKAGE is byte-reproducible: same (Registry version, sources) =>
    identical content_hash. This is what downstream consumers depend on.
  - The MANIFEST is an auditable, time-stamped record: it embeds `created_at`
    and a wall-clock `build_id`, so two manifests of the same package differ.
    That is by design — the manifest answers "when/where was this built", not
    "what is the build" (the package hash answers that, and the manifest carries
    it as `package_hash`). Manifests are therefore NOT byte-reproducible and the
    test suite does not assert that they are.
"""
from __future__ import annotations

import json
import platform
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class BuildManifest:
    build_id: str
    created_at: str
    standard_version: str
    registry_version: int
    task_id: str
    capability: str
    seeds: List[str]
    package_hash: str
    package_path: str
    derived_from: List[str]
    validation: str                 # "PASS (...)" summary
    runtime_python: str = field(default_factory=platform.python_version)
    notes: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False,
                          sort_keys=True) + "\n"


def new_build_id(task_id: str, registry_version: int) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"build-{task_id}-rv{registry_version}-{ts}"


def make(
    *,
    task_id: str,
    capability: str,
    seeds: List[str],
    standard_version: str,
    registry_version: int,
    package: dict,
    package_path: str,
    validation_summary: str,
    notes: Optional[str] = None,
) -> BuildManifest:
    return BuildManifest(
        build_id=new_build_id(task_id, registry_version),
        created_at=datetime.now(timezone.utc).isoformat(),
        standard_version=standard_version,
        registry_version=registry_version,
        task_id=task_id,
        capability=capability,
        seeds=sorted(seeds),
        package_hash=package["content_hash"],
        package_path=package_path,
        derived_from=list(package["provenance"]["derived_from"]),
        validation=validation_summary,
        notes=notes,
    )
