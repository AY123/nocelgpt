"""test_spine.py — locks in the Phase 2 end-to-end proofs (ANES v2).

Dependency-light: standard library + the runtime package. Run with:
    python3 -m tests.test_spine
Exits 0 if every proof holds, 1 otherwise. This is itself a deterministic gate
(ADR-003) and is suitable for CI.

Proves:
  1. clean fixture passes the deterministic gate
  2. a full build produces a Task Package + manifest
  3. rebuild is byte-reproducible (identical content hash)
  4. provenance pins every resolved entity at its fact_version
  5. each gate class blocks: dangling / tombstone / causal-cycle
  6. a failed gate blocks the build and emits NO artifact
  7. the entity's own id is not mistaken for an outbound reference
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import yaml

from runtime import compiler, registry_loader, validator
from runtime.pipeline import build_task_package

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "proj-demo"
SCHEMA = HERE.parent.parent / "AI-Novel-Standard" / "phase-1" / "generated" / "json-schema"

_passed = 0
_failed = 0


def check(name: str, cond: bool, detail: str = ""):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed += 1
        print(f"  FAIL  {name}  {detail}")


def _copy_fixture() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="anes-proj-"))
    dst = tmp / "proj"
    shutil.copytree(FIXTURE, dst)
    return dst


def _edit(project: Path, rel: str, mutate):
    p = project / "registry" / "facts" / rel
    d = yaml.safe_load(p.read_text())
    mutate(d)
    p.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))


def _gate(project) -> validator.ValidationReport:
    reg = registry_loader.load(project)
    return validator.validate(reg, SCHEMA, "2.0.0")


def _build(project, out, task_id="TASK-00018"):
    task = compiler.TaskDefinition(
        task_id=task_id, goal="draft chapter 18", capability="ChapterDraft",
        seeds=["CHR-00001", "EVT-00002"])
    return build_task_package(project_path=project, schema_dir=SCHEMA,
                              task=task, out_dir=out, max_depth=2)


def main() -> int:
    print("ANES v2 — Phase 2 spine proofs")

    # 1. clean gate
    rep = _gate(FIXTURE)
    check("clean fixture passes gate", rep.ok, rep.summary())

    # 2 + 3 + 4. build, reproducibility, provenance
    out = Path(tempfile.mkdtemp(prefix="anes-build-"))
    r1 = _build(FIXTURE, out)
    check("build succeeds", r1.ok, r1.message)
    check("build emits package + manifest",
          Path(r1.package_path).exists() and Path(r1.manifest_path).exists())
    r2 = _build(FIXTURE, out)
    check("rebuild is byte-reproducible",
          r1.package["content_hash"] == r2.package["content_hash"],
          f"{r1.package['content_hash']} != {r2.package['content_hash']}")
    pins = r1.package["provenance"]["derived_from"]
    check("provenance pins all 7 resolved entities at @version",
          len(pins) == 7 and all("@v" in p for p in pins), str(pins))

    # 5a. dangling
    proj = _copy_fixture()
    _edit(proj, "characters/CHR-00001.yaml",
          lambda d: d.__setitem__("abilities", ["MAG-09999"]))
    rep = _gate(proj)
    check("dangling reference blocks gate",
          any(f.check == "dangling" for f in rep.errors))
    shutil.rmtree(proj.parent)

    # 5b. tombstone (and proof 7: no self-ref false positive)
    proj = _copy_fixture()
    _edit(proj, "world_rules/MAG-00001.yaml",
          lambda d: d.__setitem__("status", "tombstoned"))
    rep = _gate(proj)
    tomb = [f for f in rep.errors if f.check == "tombstone"]
    check("tombstoned reference blocks gate", len(tomb) >= 1)
    check("entity id not mistaken for outbound ref (no self-tombstone)",
          not any(f.entity == "MAG-00001" for f in tomb), str(tomb))
    shutil.rmtree(proj.parent)

    # 5c. causal cycle
    proj = _copy_fixture()
    _edit(proj, "events/EVT-00001.yaml",
          lambda d: d.__setitem__("causes", ["EVT-00002"]))
    rep = _gate(proj)
    check("causal cycle blocks gate",
          any(f.check == "causality" for f in rep.errors))

    # 6. failed gate blocks build, emits nothing
    out2 = Path(tempfile.mkdtemp(prefix="anes-build2-")) / "nested"
    r = _build(proj, out2, task_id="TASK-00099")
    check("failed gate blocks the build", not r.ok and r.stage == "validate")
    check("blocked build emits no artifact", not out2.exists())
    shutil.rmtree(proj.parent)

    print(f"\n{_passed} passed, {_failed} failed")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
