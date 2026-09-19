"""Read-only audit of gptdoc. Writes evidence only beside this script.

Run: python3 architecture-review-2026-09-18/audit_specs.py
Requires PyYAML, jsonschema, referencing. Never retrieves remote schema resources.
Schema probes expose contract gaps; they do not execute or assess V2 runtime.
"""
from pathlib import Path
from collections import Counter, defaultdict
import copy
import hashlib
import importlib.metadata
import json
import re
import sys
from urllib.parse import urljoin, urldefrag

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent / "gptdoc"
files = [p for p in sorted(ROOT.rglob("*")) if p.is_file() and p.name != ".DS_Store"]
report = {
    "scope": "Static specification audit; no production/runtime certification",
    "environment": {"python": sys.version.split()[0], **{
        x: importlib.metadata.version(x) for x in ("PyYAML", "jsonschema", "referencing")}},
    "inventory": [], "parse_errors": [], "schema_errors": [],
    "manifest_errors": [], "manifest_checked_entries": 0,
    "duplicate_schema_ids": {}, "refs": [], "probes": [],
}
parsed = {}
schemas = {}
for p in files:
    raw = p.read_bytes()
    report["inventory"].append({"path": str(p.relative_to(ROOT.parent)),
                                "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    try:
        if p.suffix == ".json":
            parsed[p] = json.loads(raw)
        elif p.suffix == ".yaml":
            parsed[p] = yaml.safe_load(raw)
    except Exception as exc:
        report["parse_errors"].append({"file": str(p), "error": str(exc)})
    if p.name.endswith(".schema.json") and p in parsed:
        schemas[p.name] = (p, parsed[p])
        try:
            Draft202012Validator.check_schema(parsed[p])
        except Exception as exc:
            report["schema_errors"].append({"file": str(p), "error": str(exc)})

for p, v in parsed.items():
    if p.name == "MANIFEST.json":
        for item in v["files"]:
            name = item.get("name", item.get("path"))
            q = p.parent / name
            report["manifest_checked_entries"] += 1
            actual = hashlib.sha256(q.read_bytes()).hexdigest() if q.is_file() else None
            if actual != item["sha256"]:
                report["manifest_errors"].append({"file": str(q), "expected": item["sha256"], "actual": actual})

ids = defaultdict(list)
registry = Registry()
for name, (p, s) in schemas.items():
    ids[s["$id"]].append(str(p))
    registry = registry.with_resource(s["$id"], Resource.from_contents(s))
report["duplicate_schema_ids"] = {k: v for k, v in ids.items() if len(v) > 1}

def walk_refs(x, base, path=""):
    if isinstance(x, dict):
        if "$id" in x:
            base = urljoin(base, x["$id"])
        if "$ref" in x:
            absolute = urljoin(base, x["$ref"])
            ok, error = True, None
            try:
                registry.resolver(base).lookup(x["$ref"])
            except Exception as exc:
                ok, error = False, str(exc)
            report["refs"].append({"base": base, "pointer": path, "ref": x["$ref"],
                                   "resolved": ok, "absolute": absolute, "error": error})
        for k, v in x.items():
            walk_refs(v, base, path + "/" + k)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            walk_refs(v, base, path + "/" + str(i))

for p, s in schemas.values():
    walk_refs(s, s["$id"])

def validator(name):
    return Draft202012Validator(schemas[name][1], registry=registry, format_checker=FormatChecker())

def minimal(schema):
    if "$ref" in schema:
        return minimal(schemas[schema["$ref"].split("/")[-1]][1])
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    typ = schema.get("type", "object")
    if isinstance(typ, list):
        typ = next((t for t in typ if t != "null"), "null")
    if typ == "object":
        props = schema.get("properties", {})
        result = {k: minimal(props[k]) for k in schema.get("required", [])}
        for base in schema.get("allOf", []):
            result.update(minimal(base))
        return result
    if typ == "array":
        return [minimal(schema.get("items", {})) for _ in range(schema.get("minItems", 0))]
    if typ == "string":
        if schema.get("format") == "date-time":
            return "2026-09-18T00:00:00Z"
        return "x" * max(1, schema.get("minLength", 1))
    if typ in ("integer", "number"):
        return schema.get("minimum", 0)
    if typ == "boolean":
        return False
    return None

def base(name):
    return minimal(schemas[name][1])

def probe(pid, name, specimen, description, intended_valid):
    errors = sorted(validator(name).iter_errors(specimen), key=lambda e: str(list(e.path)))
    actual = not errors
    report["probes"].append({"id": pid, "schema": name, "description": description,
                             "desired_contract_acceptance": intended_valid,
                             "schema_accepts": actual, "matches_desired_contract": actual == intended_valid,
                             "specimen": specimen,
                             "errors": [{"path": list(e.path), "message": e.message} for e in errors]})

pack = parsed[next(p for p in files if p.name == "example-urban-business-realistic.genre-pack.yaml")]
probe("CONTROL-01", "genre-pack.schema.json", pack, "Supplied urban pack is structurally valid", True)
bad = copy.deepcopy(pack); bad["constitution"]["rules"][0]["on_violation"] = "ignore"
probe("CONTROL-02", "genre-pack.schema.json", bad, "Hard genre rule cannot ignore violation", False)
char = base("narrative-entity.schema.json"); char.update(entity_type="Character", lifecycle="ACTIVE", authority="canon")
probe("CONTROL-03", "character.schema.json", char, "Base entity without Character fields", True)
char["identity"] = {"species": "human"}
probe("PROBE-01", "character.schema.json", char, "Declared Character.identity cannot extend closed base schema", True)
char2 = base("narrative-entity.schema.json"); char2.update(entity_type="Location", lifecycle="受伤", authority="canon")
probe("PROBE-02", "character.schema.json", char2, "Character accepts wrong entity type and non-lifecycle condition", False)
delta = base("narrative-delta.schema.json"); delta["operations"] = [{"op": "SET_FACT", "subject": "char_1"}]
probe("PROBE-03", "narrative-delta.schema.json", delta, "SET_FACT without path/value/evidence", False)
cs = base("change-set.schema.json"); cs["operations"] = [{"op": "UNREGISTERED_OPERATION", "subject": "char_1"}]
probe("PROBE-04", "change-set.schema.json", cs, "ChangeSet accepts arbitrary operation and empty validation_summary", False)
permit = base("commit-permit.schema.json"); permit["decision"] = "ALLOW"
probe("PROBE-05", "commit-permit.schema.json", permit, "ALLOW with no validation refs and no issuer/issued_at", False)
quality = base("quality-report.schema.json"); quality["decision"] = "PASS"
probe("PROBE-06", "quality-report.schema.json", quality, "PASS with every quality layer empty", False)
ev = base("evidence-record.schema.json"); ev.update(severity="HARD_FAIL", status="CONFIRMED")
q2 = copy.deepcopy(quality); q2["layers"]["Q0"] = [ev]
probe("PROBE-07", "quality-report.schema.json", q2, "PASS despite confirmed Q0 HARD_FAIL", False)
cert = base("genre-certification.schema.json"); cert.update(level="C6", status="PASS")
probe("PROBE-08", "genre-certification.schema.json", cert, "C6 PASS with empty metrics and cases", False)
closed = base("implementation-task.schema.json"); closed["status"] = "CLOSED"
probe("PROBE-09", "implementation-task.schema.json", closed, "CLOSED task without tests, acceptance criteria or evidence", False)
scene = base("scene-contract.schema.json"); scene["genre_pack_hash"] = "a" * 64
probe("PROBE-10", "scene-contract.schema.json", scene, "SceneContract cannot carry directly required GenrePack binding", True)
item = base("context-item.schema.json")
probe("PROBE-11", "context-item.schema.json", item, "ContextItem has no project or branch binding", False)
model = base("model-run.schema.json"); model.update(status="FAILED"); model.pop("response_hash")
probe("PROBE-12", "model-run.schema.json", model, "Provider failure before response should be representable", True)
back = parsed[next(p for p in files if p.name == "implementation-backlog.yaml")]
tasks = back["tasks"]; by = {t["task_id"]: t for t in tasks}
def ancestors(tid, seen=None):
    seen = set() if seen is None else seen
    for dep in by[tid]["dependencies"]:
        if dep not in seen and dep in by:
            seen.add(dep); ancestors(dep, seen)
    return seen

test_ids = set()
for p, v in parsed.items():
    if p.name.endswith("test-matrix.yaml"):
        test_ids.update(t["id"] for t in v.get("tests", []))
report["backlog"] = {
    "count": len(tasks), "duplicate_ids": [i for i, n in Counter(t["task_id"] for t in tasks).items() if n > 1],
    "schema_failures": [{"task": t["task_id"], "error": e.message} for t in tasks for e in validator("implementation-task.schema.json").iter_errors(t)],
    "cycles": [i for i in by if i in ancestors(i)],
    "missing_dependencies": [{"task": t["task_id"], "missing": d} for t in tasks for d in t["dependencies"] if d not in by],
    "only_constitution_count": sum(t.get("normative_specs") == ["PROJECT_CONSTITUTION.md"] for t in tasks),
    "empty_artifacts_count": sum(not t.get("artifacts") for t in tasks),
    "empty_out_of_scope_count": sum(not t.get("out_of_scope") for t in tasks),
    "test_matrix_id_count": len(test_ids),
    "unmapped_test_refs": [r for t in tasks for r in t.get("tests", []) if r not in test_ids],
    "ancestry": {i: sorted(ancestors(i)) for i in by},
}
report["summary"] = {
    "files": len(files), "extensions": dict(Counter(p.suffix for p in files)),
    "schemas": len(schemas), "manifests": sum(p.name == "MANIFEST.json" for p in files),
    "schema_refs": len(report["refs"]), "unresolved_schema_refs": sum(not r["resolved"] for r in report["refs"]),
    "probes": len(report["probes"]),
    "probe_contract_mismatches": sum(not p["matches_desired_contract"] for p in report["probes"]),
}
(OUT / "audit-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
print("Parse/schema/manifest errors:", len(report["parse_errors"]), len(report["schema_errors"]), len(report["manifest_errors"]))
print("Manifest entries verified:", report["manifest_checked_entries"])
print("Backlog only constitution / empty artifacts:", report["backlog"]["only_constitution_count"], report["backlog"]["empty_artifacts_count"])
for p in report["probes"]:
    print(p["id"], "ACCEPT" if p["schema_accepts"] else "REJECT", p["description"])
