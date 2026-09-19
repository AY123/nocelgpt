"""compiler.py — compile a Task Package build artifact (ANES v2, ADR-001).

Resource-resolution path (ADR-005), final stage:
    Registry -> Resolver -> Normalizer -> [Compiler] -> TaskPackage

A Task Package is ALWAYS a build artifact (ADR-001): self-contained, read-only,
reproducible from (Registry version, sources). It is never hand-edited. The
compiler stamps it with the exact source versions (pins) so staleness is
detectable, and a content hash so reproducibility is verifiable.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .normalizer import NormalizedBundle

PACKAGE_FORMAT = "1.0"


@dataclass
class TaskDefinition:
    task_id: str            # e.g. TASK-00018
    goal: str               # what to do, in one line
    capability: str         # the Capability Contract invoked (ADR-002)
    seeds: List[str]        # entity IDs the task is about
    extra: dict = field(default_factory=dict)


def _canonical_json(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True)


def _content_hash(payload: dict) -> str:
    # Hash excludes volatile envelope fields (set by caller after hashing).
    blob = _canonical_json(payload).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def compile_package(
    bundle: NormalizedBundle,
    task: TaskDefinition,
    standard_version: str = "2.0.0",
    token_budget: Optional[int] = None,
) -> dict:
    """Produce the Task Package dict. Pure function of its inputs => reproducible."""

    context: Dict[str, list] = bundle.by_type

    # The hashable core: everything that determines the package's content.
    core = {
        "package_format": PACKAGE_FORMAT,
        "standard_version": standard_version,
        "registry_version": bundle.registry_version,
        "task": {
            "task_id": task.task_id,
            "goal": task.goal,
            "capability": task.capability,
            "seeds": sorted(task.seeds),
            "extra": task.extra,
        },
        "provenance": {
            # pinned source references (ADR-006 / Reference Grammar §5)
            "derived_from": list(bundle.pins),
            "source_version": bundle.registry_version,
        },
        "context": context,
    }

    package = dict(core)
    package["content_hash"] = _content_hash(core)
    # token_budget is metadata about how the bundle was bounded, not content.
    package["token_budget"] = token_budget
    package["entity_count"] = bundle.entity_count()
    return package


def serialize(package: dict) -> str:
    return _canonical_json(package) + "\n"
