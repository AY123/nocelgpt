"""pipeline.py — the control-flow spine (ANES v2, ADR-005).

Orchestrates one Task end-to-end. This is the control-flow path: it sequences
stages and GATES on the deterministic validator (ADR-003). It calls into the
resource-resolution path (loader/resolver/normalizer/compiler) but keeps the two
concerns separate — a build failure here is an orchestration outcome, distinct
from a stale resource on the resolution path.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from . import (catalog, compiler, contracts, manifest, normalizer,
               registry_loader, resolver, validator)


@dataclass
class BuildResult:
    ok: bool
    stage: str                       # last stage reached
    validation: validator.ValidationReport
    package: Optional[dict] = None
    package_path: Optional[str] = None
    manifest: Optional[manifest.BuildManifest] = None
    manifest_path: Optional[str] = None
    message: str = ""


def build_task_package(
    *,
    project_path: str | Path,
    schema_dir: str | Path,
    task: compiler.TaskDefinition,
    out_dir: str | Path,
    standard_version: str = "2.0.0",
    standard_root: Optional[str | Path] = None,
    max_depth: int = 2,
    token_budget: Optional[int] = None,
) -> BuildResult:
    out_dir = Path(out_dir)
    # Standard root holds contracts/; default: two levels up from schema_dir
    # (<standard>/phase-1/generated/json-schema -> <standard>).
    if standard_root is None:
        standard_root = Path(schema_dir).resolve().parents[2]

    # Stage 0 — load Standard contracts + catalog (resource path).
    contract_set = contracts.ContractSet(standard_root)
    cat = catalog.Catalog.load(schema_dir)

    # Stage 0b — capability gate (ADR-002): reject unknown capabilities early.
    if not contract_set.has_capability(task.capability):
        rep = validator.ValidationReport(findings=[validator.Finding(
            "capability", validator.SEVERITY_ERROR, task.task_id,
            f"unknown capability {task.capability!r}")])
        return BuildResult(ok=False, stage="capability", validation=rep,
                           message=f"unknown capability {task.capability!r}")

    # Stage 0c — input-constraint gate (ADR-002): the task must be semantically
    # valid for the capability (seed types/count, required extra), not just
    # name-valid.
    input_errs = contract_set.capability(task.capability).check_input(task)
    if input_errs:
        rep = validator.ValidationReport(findings=[validator.Finding(
            "capability-input", validator.SEVERITY_ERROR, task.task_id, m)
            for m in input_errs])
        return BuildResult(ok=False, stage="capability-input", validation=rep,
                           message=f"task violates {task.capability} input contract")

    # Stage 1 — load (resource path); catalog enforces fact directory layout.
    reg = registry_loader.load(project_path, catalog=cat)

    # Stage 2 — validate (deterministic GATE; ADR-003). Build stops on error.
    report = validator.validate(reg, schema_dir, standard_version)
    if not report.ok:
        return BuildResult(ok=False, stage="validate", validation=report,
                           message=f"deterministic gate failed: {report.summary()}")

    # Stage 3 — resolve (resource path)
    res = resolver.resolve(reg, task.seeds, max_depth=max_depth)

    # Stage 4 — normalize (resource path); emit order from the Standard catalog.
    bundle = normalizer.normalize(res, emit_order=cat.emit_order())

    # Stage 5 — compile to Task Package (build artifact; ADR-001)
    package = compiler.compile_package(
        bundle, task, standard_version=standard_version,
        token_budget=token_budget)

    # Stage 5b — validate the package against the Standard's authored envelope
    # contract (ADR-002). Downstream consumers rely on this shape, not on the
    # compiler's internals. A malformed envelope blocks the build.
    envelope_errs = contract_set.validate_package(package)
    if envelope_errs:
        rep = validator.ValidationReport(findings=[validator.Finding(
            "package-contract", validator.SEVERITY_ERROR, task.task_id, m)
            for m in envelope_errs])
        return BuildResult(ok=False, stage="package-contract", validation=rep,
                           message="package failed envelope contract")

    out_dir.mkdir(parents=True, exist_ok=True)
    package_path = out_dir / f"{task.task_id}.package.json"
    package_path.write_text(compiler.serialize(package), encoding="utf-8")

    # Stage 6 — emit build manifest (rollback/repro)
    bm = manifest.make(
        task_id=task.task_id,
        capability=task.capability,
        seeds=task.seeds,
        standard_version=standard_version,
        registry_version=reg.version,
        package=package,
        package_path=str(package_path),
        validation_summary=report.summary(),
    )
    manifest_path = out_dir / f"{bm.build_id}.manifest.json"
    manifest_path.write_text(bm.to_json(), encoding="utf-8")

    return BuildResult(
        ok=True, stage="done", validation=report, package=package,
        package_path=str(package_path), manifest=bm,
        manifest_path=str(manifest_path),
        message=f"built {package_path.name} ({package['entity_count']} entities)")
