"""test_conformance.py — boundary conformance proofs (ANES v2).

Complements test_spine.py. Where test_spine proves the build pipeline runs, this
proves the cross-repo BOUNDARIES hold:
  - catalog is the single source of the type->dir/entity mapping (no drift)
  - the contract layer gates capabilities and the package envelope
  - the Template scaffolds a Project that passes the Runtime gate

Run: python3 -m tests.test_conformance   (exit non-zero on any failure)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

from runtime import catalog, compiler, contracts, registry_loader, validator
from runtime.pipeline import build_task_package

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "proj-demo"
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"
TEMPLATE_INIT = HERE.parent.parent / "AI-Novel-Template" / "tools" / "init_project.py"

_passed = 0
_failed = 0


def check(name, cond, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed += 1
        print(f"  FAIL  {name}  {detail}")


def main() -> int:
    print("ANES v2 — boundary conformance proofs")

    # --- Catalog as single source of truth ---
    cat = catalog.Catalog.load(SCHEMA)
    check("catalog maps every fixture type code",
          all(cat.facts_dir(c) for c in ["CHR", "REL", "TML", "EVT", "MAG", "ITM"]))
    check("catalog maps TEC and MAG to same entity (WorldRule)",
          cat.entity_name("TEC") == cat.entity_name("MAG") == "WorldRule")
    # misfiled record is caught by the catalog-aware loader
    proj = Path(tempfile.mkdtemp(prefix="anes-mis-")) / "proj"
    shutil.copytree(FIXTURE, proj)
    src = proj / "registry" / "facts" / "items" / "ITM-00001.yaml"
    dst = proj / "registry" / "facts" / "characters" / "ITM-00001.yaml"
    shutil.move(str(src), str(dst))
    misfiled_caught = False
    try:
        registry_loader.load(proj, catalog=cat)
    except ValueError:
        misfiled_caught = True
    check("catalog-aware loader rejects a misfiled record", misfiled_caught)
    shutil.rmtree(proj.parent)

    # emit order comes from the catalog, not a hardcoded Runtime list
    eo = cat.emit_order()
    check("catalog supplies an emit order for every type code",
          all(isinstance(eo.get(c), int) for c in cat.type_codes()))
    check("catalog emit order matches frozen ranks (TML<EVT<CHR<REL<MAG<ITM)",
          eo["TML"] < eo["EVT"] < eo["CHR"] < eo["REL"] < eo["MAG"] < eo["ITM"])

    # --- Contract layer ---
    cs = contracts.ContractSet(STANDARD)
    check("Standard declares ChapterDraft capability",
          cs.has_capability("ChapterDraft"))
    check("ChapterDraft is generative + evaluative (never gates build)",
          cs.capability("ChapterDraft").is_generative
          and cs.capability("ChapterDraft").gating == "evaluative")
    check("unknown capability is rejected", not cs.has_capability("Bogus"))

    # --- Validator is a check registry, not a monolith (ADR-003) ---
    checks = dict(validator.registered_checks())
    check("validator exposes a check registry",
          {"schema", "dangling", "tombstone", "causality", "pin"} <= set(checks))
    check("every registered check declares a known QA axis",
          all(ax in (validator.AXIS_GATE, validator.AXIS_TREND)
              for ax in checks.values()))
    check("all current checks are deterministic (gate axis)",
          all(ax == validator.AXIS_GATE for ax in checks.values()))

    out = Path(tempfile.mkdtemp(prefix="anes-cap-"))
    bad = build_task_package(
        project_path=FIXTURE, schema_dir=SCHEMA,
        task=compiler.TaskDefinition("TASK-00001", "x", "Bogus", ["CHR-00001"]),
        out_dir=out)
    check("build refuses unknown capability", not bad.ok and bad.stage == "capability")

    # input-constraint gate: a known capability with the wrong seed type is
    # rejected as semantically invalid (not merely name-valid).
    wrong_type = build_task_package(
        project_path=FIXTURE, schema_dir=SCHEMA,
        task=compiler.TaskDefinition("TASK-00002", "x", "ChapterDraft",
                                     ["TML-00001"]),
        out_dir=out)
    check("build refuses disallowed seed type",
          not wrong_type.ok and wrong_type.stage == "capability-input")
    no_seeds = build_task_package(
        project_path=FIXTURE, schema_dir=SCHEMA,
        task=compiler.TaskDefinition("TASK-00003", "x", "ChapterDraft", []),
        out_dir=out)
    check("build refuses too few seeds",
          not no_seeds.ok and no_seeds.stage == "capability-input")

    good = build_task_package(
        project_path=FIXTURE, schema_dir=SCHEMA,
        task=compiler.TaskDefinition("TASK-00018", "draft ch18", "ChapterDraft",
                                     ["CHR-00001", "EVT-00002"]),
        out_dir=out)
    check("valid build passes envelope contract", good.ok, good.message)
    check("built package validates against Standard envelope",
          cs.validate_package(good.package) == [])
    shutil.rmtree(out)

    # --- Template -> Project ---
    if TEMPLATE_INIT.exists():
        tmp = Path(tempfile.mkdtemp(prefix="anes-tpl-"))
        newproj = tmp / "my-novel-test"
        r = subprocess.run(
            [sys.executable, str(TEMPLATE_INIT), "--standard", str(STANDARD),
             "--out", str(newproj), "--project-id", "my-novel-test"],
            capture_output=True, text=True)
        check("template init succeeds", r.returncode == 0, r.stderr)
        # the catalog's project-scoped dirs all exist
        facts = newproj / "registry" / "facts"
        check("template creates all catalog facts dirs",
              all((facts / cat.facts_dir(c)).is_dir()
                  for c in ["CHR", "REL", "TML", "EVT", "MAG", "ITM"]))
        reg = registry_loader.load(newproj, catalog=cat)
        rep = validator.validate(reg, SCHEMA, "2.0.0")
        check("empty template project passes the gate", rep.ok, rep.summary())
        shutil.rmtree(tmp)
    else:
        check("template init script present", False, str(TEMPLATE_INIT))

    print(f"\n{_passed} passed, {_failed} failed")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
