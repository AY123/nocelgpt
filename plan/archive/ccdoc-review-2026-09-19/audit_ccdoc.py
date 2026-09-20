#!/usr/bin/env python3
"""Read-only, dependency-free probes of ccdoc design examples, not runtime tests.

Only named, locally inspected definitions are extracted from document code blocks.
No original source is changed; no LLM, network, Git, deployment or database call is made.
Run: python3 audit_ccdoc.py --source ../ccdoc --output audit-results.json
"""
import argparse
import ast
import contextlib
import dataclasses
import hashlib
import io
import json
from pathlib import Path
import re
from types import SimpleNamespace
import typing
from abc import ABC, abstractmethod


def blocks(path, language="python"):
    source = path.read_text(encoding="utf-8")
    result = []
    for m in re.finditer(r"(?ms)^```" + language + r"[^\n]*\n(.*?)^```\s*$", source):
        result.append((source[:m.start()].count("\n") + 2, m.group(1)))
    return result


def load_definitions(path, names, scope):
    loaded = {}
    for line, code in blocks(path):
        tree = ast.parse(code)
        selected = []
        for node in tree.body:
            name = getattr(node, "name", None)
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
            if name in names:
                selected.append(node)
                loaded[name] = {"file": path.name, "line": line + node.lineno - 1}
        if selected:
            future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
            module = ast.fix_missing_locations(ast.Module(body=[future] + selected, type_ignores=[]))
            exec(compile(module, str(path), "exec"), scope)
    missing = set(names) - set(loaded)
    if missing:
        raise AssertionError("Missing definitions: " + str(missing))
    return loaded


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent / "ccdoc")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().with_name("audit-results.json"))
    args = parser.parse_args()
    source = args.source.resolve()
    files = sorted(p for p in source.rglob("*") if p.is_file() and p.name != ".DS_Store")
    inventory = []
    for path in files:
        data = path.read_bytes()
        inventory.append({"path": str(path.relative_to(source)), "bytes": len(data),
                          "lines": len(data.splitlines()), "sha256": hashlib.sha256(data).hexdigest()})
    g = source / "01_GENRE_SYSTEM_ARCHITECTURE_DESIGN.md"
    scope = dict(vars(typing), dataclass=dataclasses.dataclass, ABC=ABC, abstractmethod=abstractmethod)
    names = ["GenreConstraints", "URBAN_CONSTRAINTS", "XUANHUAN_CONSTRAINTS", "GenreProgressionModel",
             "PowerProgressionModel", "WealthProgressionModel", "TechProgressionModel", "GenreRegistry",
             "KeywordDetector", "URBAN_DETECTOR", "XUANHUAN_DETECTOR"]
    definitions = load_definitions(g, names, scope)
    registry = scope["GenreRegistry"]
    registry._genres = {
        "urban": SimpleNamespace(keyword_detector=scope["URBAN_DETECTOR"], constraints=scope["URBAN_CONSTRAINTS"],
                                 progression_model=scope["WealthProgressionModel"]()),
        "xuanhuan": SimpleNamespace(keyword_detector=scope["XUANHUAN_DETECTOR"], constraints=scope["XUANHUAN_CONSTRAINTS"]),
    }
    def detect(texts):
        with contextlib.redirect_stdout(io.StringIO()):
            chosen = registry.detect_from_references(texts)
        return {"chosen": chosen, "scores": {k: v.keyword_detector.score(texts) for k, v in registry._genres.items()}}
    probes = []
    def record(id, title, outcome, observation, category="reproduced_design_example"):
        probes.append({"id": id, "title": title, "category": category,
                       "expected_contract_holds": outcome, "observation": observation})
    cases = None
    for _, code in blocks(g):
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "test_genre_detection_accuracy":
                cases = ast.literal_eval(node.body[1].value)
    assert cases
    outcomes = []
    for texts, expected, minimum in cases:
        result = detect(texts)
        outcomes.append({"texts": texts, "expected": expected, "declared_min_confidence": minimum,
                         **result, "passes_document_test": expected == "?" or result["chosen"] == expected})
    accuracy = sum(r["passes_document_test"] for r in outcomes) / len(outcomes)
    record("G01", "Document's own example test reaches >=90%", accuracy >= .9,
           {"accuracy": accuracy, "cases": outcomes, "ambiguous_case_is_counted_correct_unconditionally": True,
            "minimum_confidence_is_never_asserted_by_document_test": True})
    unknown = detect(["窗外下着雨，她等了一整夜。"])
    record("G02", "All-zero classification abstains", unknown["chosen"] not in registry._genres, unknown)
    cbd = scope["KeywordDetector"](["CBD"], []).score(["CBD"])
    record("G03", "Keyword case normalization is symmetric", cbd == 1, {"input": "CBD", "score": cbd})
    metaphor = "他把谈判当成一门修炼，努力突破销售瓶颈。"
    violations = registry.validate_constraints("urban", metaphor)
    record("G04", "A realistic metaphor is not a world-rule violation", violations == [], {"text": metaphor, "violations": violations})
    magic = "他摊开手掌，隔空让整栋大楼升上天空。"
    violations = registry.validate_constraints("urban", magic)
    record("G05", "Supernatural causal assertion without banned terms is detected", bool(violations), {"text": magic, "violations": violations})
    rule = "这个世界存在力量等级压制。"
    violations = registry.validate_constraints("urban", rule)
    record("G06", "Explicit forbidden_world_rules field is checked", bool(violations), {"text": rule, "violations": violations,
           "configured_rule": "力量等级压制"})
    direct = registry.validate_constraints("urban", "主角吸收灵气。")
    record("G07", "Positive control: literal forbidden term is detected", bool(direct), {"violations": direct}, "positive_control")
    growth = scope["WealthProgressionModel"]().validate_transition("小康", "中产")
    record("G08", "Positive control: single-tier wealth advance passes", growth[0], growth, "positive_control")
    decline = scope["WealthProgressionModel"]().validate_transition("富豪", "富裕")
    record("G09", "A general state-transition validator can represent earned setbacks", decline[0],
           {"result": decline, "qualification": "If this API is promotion-only, it is correct as named by its docstring; a separate general state-change API is then required."},
           "scope_limitation_not_unconditional_bug")
    p = source / "04_GENRE_SPECIFIC_PROMPT_TEMPLATES.md"
    definitions.update(load_definitions(p, ["inject_constraints"], scope))
    for id, template, title in [
        ("G10", "禁止世界规则：{forbidden_world_rules}", "Constraint injection supplies declared world-rule placeholder"),
        ("G11", '输出 JSON：{"genre": "urban"}', "Constraint injection handles literal JSON braces in supplied templates"),
        ("G12", "参考分析：{reference_analysis}", "Constraint injection supports reference placeholder or explicit multi-stage rendering"),
    ]:
        try:
            result = scope["inject_constraints"](template, registry._genres["urban"])
            record(id, title, True, {"result": result})
        except (KeyError, ValueError) as error:
            record(id, title, False, {"template": template, "exception": type(error).__name__, "message": str(error)})
    result = {"audit_date": "2026-09-19", "source": str(source),
              "scope": "Document-level isolated probes. Not an implemented-system, PostgreSQL, CI, or live-provider certification.",
              "inventory": inventory, "counts": {"files": len(files), "bytes": sum(x["bytes"] for x in inventory),
              "lines": sum(x["lines"] for x in inventory)}, "extracted_definitions": definitions, "probes": probes}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"counts": result["counts"], "probes": [{"id": p["id"], "holds": p["expected_contract_holds"]} for p in probes],
                      "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
