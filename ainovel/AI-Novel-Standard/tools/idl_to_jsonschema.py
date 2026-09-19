#!/usr/bin/env python3
"""idl_to_jsonschema.py — IDL -> JSON Schema generator (ANES v2 Phase 1).

The IDL (idl/*.idl.yaml) is the single hand-written source of the data contract
(ADR-007). This tool is the generator that produces read-only JSON Schema from
it. JSON Schema is NEVER hand-edited; same IDL => byte-identical output.

Usage:
    idl_to_jsonschema.py --idl-dir <dir> --out-dir <dir> [--check]

--check: regenerate in memory and compare to existing files; exit 1 on drift.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import yaml

IDL_FORMAT = "1.0"
JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

# Frozen ID type codes (mirrors spec/01-id-naming-specification.md §4).
TYPE_CODES = {
    "CHR", "LOC", "ITM", "MAG", "TEC", "FAC", "TML", "EVT", "REL", "ARC",
    "PLT", "THM", "VOL", "CHP", "SCN", "BEAT", "FOR", "INV", "TASK", "PKG",
    "AGT", "CON", "ADR",
}

# Reference grammar pieces (mirrors spec/02-reference-grammar.md).
# Allows optional <project-id>: prefix, required <code>-<ordinal>, optional
# #fragment and @version suffixes.
PROJECT_PREFIX = r"(?:[a-z0-9-]{1,32}:)?"
ORDINAL = r"\d{5,}"
FRAG_VER = r"(?:#[A-Za-z0-9_.\[\]-]+)?(?:@(?:v\d+|latest))?"


def ref_pattern(codes):
    """Build an anchored regex string for a reference constrained to `codes`."""
    alt = "|".join(sorted(codes))
    return f"^{PROJECT_PREFIX}(?:{alt})-{ORDINAL}{FRAG_VER}$"


def id_pattern(code):
    return f"^{code}-{ORDINAL}$"


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# Universal fields injected into every entity (spec/03-core-idl.md §4.2).
def universal_fields(entity_code):
    return {
        "id": {"type": "id", "code": entity_code, "required": True,
               "immutable": True, "doc": "permanent immutable identifier"},
        "name": {"type": "string", "required": True,
                 "doc": "mutable human label"},
        "status": {"type": "enum", "enum_ref": "status", "default": "active",
                   "doc": "lifecycle state"},
        "fact_version": {"type": "int", "min": 1, "required": True,
                         "doc": "Registry version of this record"},
    }


def resolve_enum(field, shared):
    """Return the value list for an enum field, via inline values or enum_ref."""
    if "values" in field:
        return field["values"]
    ref = field.get("enum_ref")
    if ref is None:
        raise ValueError("enum field needs 'values' or 'enum_ref'")
    enums = (shared or {}).get("enums", {})
    if ref not in enums:
        raise ValueError(f"unknown enum_ref: {ref}")
    return enums[ref]["values"]


def field_to_schema(field, shared):
    """Map one IDL field definition to a JSON Schema fragment."""
    t = field["type"]
    doc = field.get("doc")
    node = {}

    if t == "id":
        node = {"type": "string", "pattern": id_pattern(field["code"])}
    elif t == "string":
        node = {"type": "string"}
    elif t == "text":
        node = {"type": "string"}
    elif t == "int":
        node = {"type": "integer"}
        if "min" in field:
            node["minimum"] = field["min"]
        if "max" in field:
            node["maximum"] = field["max"]
    elif t == "float":
        node = {"type": "number"}
        if "min" in field:
            node["minimum"] = field["min"]
        if "max" in field:
            node["maximum"] = field["max"]
    elif t == "bool":
        node = {"type": "boolean"}
    elif t == "date":
        node = {"type": "string"}
        if "format" in field:
            node["description"] = f"date token ({field['format']})"
    elif t == "enum":
        node = {"type": "string", "enum": list(resolve_enum(field, shared))}
    elif t == "ref":
        node = {"type": "string", "pattern": ref_pattern(field["ref_types"])}
    elif t == "ref[]":
        node = {"type": "array",
                "items": {"type": "string",
                          "pattern": ref_pattern(field["ref_types"])}}
    elif t == "list":
        node = {"type": "array",
                "items": field_to_schema(field["of"], shared)}
    elif t == "map":
        node = {"type": "object",
                "additionalProperties": field_to_schema(field["of"], shared)}
    elif t == "struct":
        props, required = {}, []
        for fname, fdef in field["fields"].items():
            props[fname] = field_to_schema(fdef, shared)
            if fdef.get("required"):
                required.append(fname)
        node = {"type": "object", "properties": props,
                "additionalProperties": False}
        if required:
            node["required"] = required
    else:
        raise ValueError(f"unknown type: {t}")

    if "default" in field:
        node["default"] = field["default"]
    if doc and "description" not in node:
        node["description"] = doc
    return node


def entity_to_schema(idl, shared, src_name):
    code = idl["type_code"]
    also = idl.get("also_type_codes", [])
    # Build the ordered field set: universal first, then declared (declared
    # wins if it overrides a universal name).
    fields = universal_fields(code)
    for fname, fdef in idl.get("fields", {}).items():
        fields[fname] = fdef

    props, required = {}, []
    for fname, fdef in fields.items():
        # id field: if entity also covers extra codes (MAG+TEC), widen pattern.
        if fdef.get("type") == "id" and also:
            codes = {fdef["code"], *also}
            props[fname] = {"type": "string",
                            "pattern": ref_pattern(codes).replace(
                                FRAG_VER, "").replace(PROJECT_PREFIX, "")}
        else:
            props[fname] = field_to_schema(fdef, shared)
        if fdef.get("required"):
            required.append(fname)

    schema = {
        "$schema": JSON_SCHEMA_DIALECT,
        "$id": f"anes:phase-1:{idl['entity']}",
        "title": idl["entity"],
        "description": idl.get("description", ""),
        "x-anes-generated": "DO NOT EDIT — generated from "
                            f"{src_name} by tools/idl_to_jsonschema.py",
        "x-anes-idl-version": idl.get("idl_version", IDL_FORMAT),
        "x-anes-type-code": code,
        "type": "object",
        "properties": props,
        "required": sorted(required),
        "additionalProperties": False,
    }
    return schema


def generate(idl_dir):
    """Return {filename: schema_dict} for every entity IDL in idl_dir."""
    idl_dir = Path(idl_dir)
    shared = None
    shared_path = idl_dir / "_types.idl.yaml"
    if shared_path.exists():
        shared = load_yaml(shared_path)

    out = {}
    for path in sorted(idl_dir.glob("*.idl.yaml")):
        if path.name == "_types.idl.yaml":
            continue
        idl = load_yaml(path)
        if idl.get("idl_version") != IDL_FORMAT:
            raise ValueError(f"{path.name}: idl_version must be {IDL_FORMAT}")
        if idl["type_code"] not in TYPE_CODES:
            raise ValueError(f"{path.name}: unknown type_code {idl['type_code']}")
        schema = entity_to_schema(idl, shared, path.name)
        out[f"{idl['entity']}.schema.json"] = schema
    out["catalog.json"] = build_catalog(idl_dir)
    return out


def build_catalog(idl_dir):
    """Single source of the type_code -> {entity, facts_dir, scope, schema}
    mapping, generated from the IDL (ADR-007: no second hand-written source).

    Runtime reads this instead of hardcoding TYPE_DIR / TYPE_TO_ENTITY.
    """
    idl_dir = Path(idl_dir)
    entries = {}
    for path in sorted(idl_dir.glob("*.idl.yaml")):
        if path.name == "_types.idl.yaml":
            continue
        idl = load_yaml(path)
        entity = idl["entity"]
        reg = idl.get("registry", {})
        record = {
            "entity": entity,
            "schema_file": f"{entity}.schema.json",
            "facts_dir": reg.get("facts_dir"),
            "scope": reg.get("scope", "project"),
            "order": reg.get("order", 999),
            "idl_file": path.name,
        }
        # Every type code (primary + also_type_codes) maps to this entity.
        for code in [idl["type_code"], *idl.get("also_type_codes", [])]:
            if code in entries:
                raise ValueError(f"type_code {code} defined by two entities")
            entries[code] = dict(record, type_code=code)
    return {
        "catalog_format": "1.0",
        "x-anes-generated": "DO NOT EDIT — generated by tools/idl_to_jsonschema.py",
        "by_type_code": entries,
    }



def serialize(schema):
    return json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--idl-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--check", action="store_true",
                    help="compare to existing files; exit 1 on drift")
    args = ap.parse_args()

    generated = generate(args.idl_dir)
    out_dir = Path(args.out_dir)

    if args.check:
        drift = []
        for fname, schema in generated.items():
            target = out_dir / fname
            want = serialize(schema)
            have = target.read_text(encoding="utf-8") if target.exists() else None
            if have != want:
                drift.append(fname)
        if drift:
            print("DRIFT detected in:", ", ".join(sorted(drift)), file=sys.stderr)
            return 1
        print(f"OK: {len(generated)} schema(s) match.")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    for fname, schema in generated.items():
        (out_dir / fname).write_text(serialize(schema), encoding="utf-8")
    n_schemas = sum(1 for f in generated if f != "catalog.json")
    print(f"Generated {n_schemas} schema(s) + catalog into {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
