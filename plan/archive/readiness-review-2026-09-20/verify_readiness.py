"""Independent, local readiness checks; does not modify source specifications.

Run from any directory: python3 /path/to/readiness-review-2026-09-20/verify_readiness.py
Requires the already installed PyYAML, jsonschema and referencing packages.
Results describe documents/schema contracts, not a running V2 or CI certification.
"""
from collections import Counter
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import copy
import io
import json
import runpy
import subprocess
import tempfile

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
CONV = ROOT / ".claude/convergence"


def read_json(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def line_matches(relative_path, terms):
    return [{"line": n, "text": line} for n, line in enumerate(
        (ROOT / relative_path).read_text().splitlines(), 1)
        if any(term in line for term in terms)]


def main():
    result = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "head": git("rev-parse", "HEAD"),
        "scope": "Local document, task registry, source hash and JSON Schema verification only",
        "not_executed": ["V2 runtime", "PostgreSQL integration", "CI pipeline", "live provider", "reader study"],
    }
    inventories = []
    for report_path, base in [
        (ROOT / "architecture-review-2026-09-18/audit-results.json", ROOT),
        (ROOT / "ccdoc-review-2026-09-19/audit-results.json", ROOT / "ccdoc"),
    ]:
        old = read_json(report_path)
        changed, missing = [], []
        for item in old["inventory"]:
            path = base / item["path"]
            if not path.is_file():
                missing.append(item["path"])
            elif digest(path) != item["sha256"]:
                changed.append(item["path"])
        inventories.append({"baseline": str(report_path.relative_to(ROOT)),
                            "checked": len(old["inventory"]), "changed": changed, "missing": missing})
    result["source_inventory_comparison"] = inventories

    backlog_path = ROOT / "gptdoc/ANovel_V2_Implementation_Plan_v1.0/implementation-backlog.yaml"
    tasks = yaml.safe_load(backlog_path.read_text())["tasks"]
    declared = read_json(CONV / "convergence-validation.json")
    counts = dict(Counter(t["phase"] for t in tasks))
    declared_counts = declared["task_validation"]["phase_distribution"]
    result["task_registry"] = {
        "total": len(tasks), "unique_ids": len({t["task_id"] for t in tasks}),
        "status_counts": dict(Counter(t["status"] for t in tasks)),
        "actual_phase_counts": counts, "recorded_phase_counts": declared_counts,
        "recorded_phase_count_sum": sum(declared_counts.values()),
        "phase_count_mismatches": {p: {"actual": counts.get(p), "recorded": declared_counts.get(p)}
                                   for p in counts.keys() | declared_counts.keys()
                                   if counts.get(p) != declared_counts.get(p)},
        "only_constitution_reference": sum(t["normative_specs"] == ["PROJECT_CONSTITUTION.md"] for t in tasks),
        "empty_artifacts": sum(not t["artifacts"] for t in tasks),
        "empty_out_of_scope": sum(not t["out_of_scope"] for t in tasks),
        "generic_test_reference": sum(t["tests"] == ["TEST-" + t["task_id"]] for t in tasks),
        "v2_005_dependencies": next(t["dependencies"] for t in tasks if t["task_id"] == "V2-005"),
    }
    namespace = runpy.run_path(str(CONV / "task-registry-generator.py"))
    with tempfile.TemporaryDirectory(prefix="anovel-registry-review-") as temp:
        generated = Path(temp) / "registry.md"
        namespace["main"].__globals__["OUTPUT_PATH"] = generated
        with redirect_stdout(io.StringIO()):
            namespace["main"]()
        result["task_registry"]["regenerated_registry_matches_bytes"] = (
            generated.read_bytes() == (CONV / "PHASE_TASK_REGISTRY.md").read_bytes())

    tracked = git("ls-files").splitlines()
    missing_names = ["GPTDOC_CONFORMANCE_AND_DEFECT_REGISTER.md", "BOUNDARY_SEPARATIONS_VERIFICATION.md",
                     "CONVERGENCE_CORRECTION_SUMMARY.md", "PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md"]
    result["referenced_deliverable_locations"] = {
        name: [p for p in tracked if Path(p).name == name] for name in missing_names}
    infrastructure = ["src", "tests", "pyproject.toml", "uv.lock", "poetry.lock", "requirements.lock",
                      ".gitlab-ci.yml", ".github/workflows", "compose.yaml", "docker-compose.yml"]
    result["root_engineering_artifact_presence"] = {p: (ROOT / p).exists() for p in infrastructure}
    result["tracked_non_document_engineering_candidates"] = [p for p in tracked if (
        Path(p).name in {"pyproject.toml", "uv.lock", "poetry.lock", ".gitlab-ci.yml", "docker-compose.yml", "compose.yaml"}
        or Path(p).name.startswith("test_") and Path(p).suffix == ".py")]

    signals = {
        ".claude/convergence/NORMATIVE_INDEX.md": ["Implementation Order", "P1: Genre", "P2: Domain", "Follow dependency order"],
        ".claude/convergence/TERMINOLOGY_BASELINE.md": ["E1=deterministic", "E3=simulated"],
        "DATA_OWNERSHIP_MATRIX.md": ["E4 evidence", "After commit or expiration", "**P2 (", "**P3 (", "**P8 ("],
        ".claude/convergence/ARCHITECTURE_READINESS_REPORT.md": ["97.5%", "Add to P0 remediation", "GPTDOC_CONFORMANCE", "BOUNDARY_SEPARATIONS"],
        "ARCHITECTURE_RISK_REGISTER.md": ["attempt_id", "E0-DETERMINISTIC", "E3-HUMAN", "E4-MARKET", "E3 (human/sim)"],
    }
    result["cross_document_review_signals"] = {p: line_matches(p, terms) for p, terms in signals.items()}

    original = read_json(ROOT / "architecture-review-2026-09-18/audit-results.json")
    schemas = {}
    registry = Registry()
    for item in original["inventory"]:
        path = ROOT / item["path"]
        if path.name.endswith(".schema.json"):
            schema = read_json(path)
            schemas[path.name] = schema
            registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    probes = []
    result["historical_fixture_corrections"] = []
    for old in original["probes"]:
        specimen = copy.deepcopy(old["specimen"])
        if old["id"] == "CONTROL-03" and "identity" in specimen:
            # The historical probe() stored the same dict later mutated by PROBE-01.
            # Recover the intended control from audit_specs.py, leaving that report intact.
            specimen.pop("identity")
            result["historical_fixture_corrections"].append({
                "probe": "CONTROL-03", "change": "Remove identity added by subsequent PROBE-01",
                "reason": "Historical script stored a mutable specimen reference; original control had no identity",
                "source": "architecture-review-2026-09-18/audit_specs.py"})
        validator = Draft202012Validator(schemas[old["schema"]], registry=registry, format_checker=FormatChecker())
        errors = list(validator.iter_errors(specimen))
        accepts = not errors
        probes.append({"id": old["id"], "schema": old["schema"], "description": old["description"],
                       "desired_contract_acceptance": old["desired_contract_acceptance"],
                       "current_schema_accepts": accepts,
                       "matches_desired_contract": accepts == old["desired_contract_acceptance"],
                       "matches_historical_acceptance": accepts == old["schema_accepts"],
                       "specimen": specimen,
                       "errors": [e.message for e in errors[:3]]})
    result["rerun_schema_probes"] = probes
    result["schema_probe_summary"] = {"total": len(probes),
        "contract_mismatches": sum(not p["matches_desired_contract"] for p in probes),
        "changed_vs_historical_result": sum(not p["matches_historical_acceptance"] for p in probes)}

    current_files = sorted(CONV.glob("*")) + [ROOT / name for name in [
        "ARCHITECTURE_RISK_REGISTER.md", "CCDOC_ADOPTION_MATRIX.md", "DATA_OWNERSHIP_MATRIX.md",
        "V1_REGRESSION_ASSET_REGISTER.md", "V1_REUSE_DECISION_MATRIX.md"]]
    result["convergence_source_hashes"] = [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)}
                                          for p in current_files if p.is_file()]
    (OUT / "readiness-evidence.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"head": result["head"], "source_hash_checks": inventories,
                      "task_registry": result["task_registry"],
                      "schema_probes": result["schema_probe_summary"],
                      "missing_reference_checks": result["referenced_deliverable_locations"],
                      "engineering_candidates": result["tracked_non_document_engineering_candidates"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
