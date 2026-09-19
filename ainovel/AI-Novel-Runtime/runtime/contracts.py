"""contracts.py — load & enforce Standard contracts (ANES v2, ADR-002).

Resource-resolution path. Reads two things from the Standard:
  - capability contracts (contracts/capabilities/*.capability.yaml)
  - the Task Package artifact contract (contracts/task-package.schema.json)

This is what stops downstream consumers from depending on the Runtime compiler's
internal dict shape: the package is validated against the AUTHORED envelope, and
a Task's capability must be one the Standard declares.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import yaml
from jsonschema import Draft202012Validator


@dataclass(frozen=True)
class CapabilityContract:
    capability: str
    determinism: str            # deterministic | generative
    gating: str                 # deterministic | evaluative
    safe_to_retry: bool
    cacheable: bool
    max_attempts: int
    output_kind: str            # prose | structured
    output_schema: "str | None"  # output Artifact Contract filename (from contract)
    seed_types: "list[str] | None"   # allowed seed type codes (None = any)
    min_seeds: int
    max_seeds: "int | None"
    required_extra: "list[str]"
    raw: dict

    @property
    def is_generative(self) -> bool:
        return self.determinism == "generative"

    def check_input(self, task) -> "list[str]":
        """Return a list of input-constraint violation messages (empty = ok).

        Makes a task SEMANTICALLY valid, not just name-valid: the seeds must be
        of types the capability can consume, within count bounds, and any
        required task.extra keys must be present.
        """
        errs = []
        seeds = list(task.seeds or [])
        if len(seeds) < self.min_seeds:
            errs.append(f"needs >= {self.min_seeds} seed(s), got {len(seeds)}")
        if self.max_seeds is not None and len(seeds) > self.max_seeds:
            errs.append(f"allows <= {self.max_seeds} seed(s), got {len(seeds)}")
        if self.seed_types is not None:
            allowed = set(self.seed_types)
            for s in seeds:
                tc = s.split("-", 1)[0]
                if tc not in allowed:
                    errs.append(f"seed {s} type {tc} not in allowed {sorted(allowed)}")
        extra = getattr(task, "extra", {}) or {}
        for key in self.required_extra:
            if key not in extra:
                errs.append(f"missing required task.extra key {key!r}")
        return errs


class ContractSet:
    """All contracts the Standard publishes, resolved from a Standard root."""

    def __init__(self, standard_root: str | Path):
        self.root = Path(standard_root)
        self._caps: Dict[str, CapabilityContract] = {}
        self._package_validator: Draft202012Validator | None = None
        self._artifact_validators: Dict[str, Draft202012Validator] = {}
        self._load_capabilities()

    def _load_capabilities(self):
        cap_dir = self.root / "contracts" / "capabilities"
        for path in sorted(cap_dir.glob("*.capability.yaml")):
            d = yaml.safe_load(path.read_text(encoding="utf-8"))
            idem = d.get("idempotency", {})
            retry = d.get("retry", {})
            inp = d.get("input", {})
            con = inp.get("constraints", {})
            outp = d.get("output", {})
            cap = CapabilityContract(
                capability=d["capability"],
                determinism=d.get("determinism", "generative"),
                gating=d.get("gating", "evaluative"),
                safe_to_retry=bool(idem.get("safe_to_retry", False)),
                cacheable=bool(idem.get("cacheable", False)),
                max_attempts=int(retry.get("max_attempts", 1)),
                output_kind=outp.get("kind", "prose"),
                output_schema=outp.get("schema"),
                seed_types=con.get("seed_types"),
                min_seeds=int(con.get("min_seeds", 1)),
                max_seeds=con.get("max_seeds"),
                required_extra=list(con.get("required_extra", [])),
                raw=d,
            )
            self._caps[cap.capability] = cap

    def capability(self, name: str) -> CapabilityContract:
        if name not in self._caps:
            raise ValueError(
                f"unknown capability {name!r}; declared: {sorted(self._caps)}")
        return self._caps[name]

    def has_capability(self, name: str) -> bool:
        return name in self._caps

    def package_validator(self) -> Draft202012Validator:
        if self._package_validator is None:
            path = self.root / "contracts" / "task-package.schema.json"
            schema = json.loads(path.read_text(encoding="utf-8"))
            self._package_validator = Draft202012Validator(schema)
        return self._package_validator

    def _artifact_validator(self, schema_filename: str) -> Draft202012Validator:
        if schema_filename not in self._artifact_validators:
            path = self.root / "contracts" / schema_filename
            schema = json.loads(path.read_text(encoding="utf-8"))
            self._artifact_validators[schema_filename] = Draft202012Validator(schema)
        return self._artifact_validators[schema_filename]

    @staticmethod
    def _collect(validator, doc) -> List[str]:
        errs = []
        for e in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
            loc = "/".join(str(p) for p in e.path) or "(root)"
            errs.append(f"{loc}: {e.message}")
        return errs

    def validate_package(self, package: dict) -> List[str]:
        """Return a list of envelope-validation error messages (empty == valid)."""
        return self._collect(self.package_validator(), package)

    def validate_artifact(self, artifact: dict, schema_filename: str) -> List[str]:
        """Validate an OUTPUT artifact against its Standard contract (empty == valid)."""
        return self._collect(self._artifact_validator(schema_filename), artifact)
