"""Read-only probes against reviewed Markdown examples. No network or production DB.

Run: python3 ccdoc-review-2026-09-19/core-probes.py
The relational probe uses SQLite only to demonstrate equivalent simple FK logic;
it is NOT a PostgreSQL migration integration test.
"""
from __future__ import annotations

import ast
import dataclasses
from datetime import datetime
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "ccdoc"
OUT = Path(__file__).resolve().parent / "core-probe-results.json"
results = []


def classes_from(path, names=None):
    namespace = dict(dataclass=dataclasses.dataclass, field=dataclasses.field,
                     datetime=datetime, Enum=Enum, Dict=Dict, List=List,
                     Optional=Optional)
    source = path.read_text()
    for block in re.findall(r"```python\n(.*?)\n```", source, re.S):
        tree = ast.parse(block)
        nodes = [n for n in tree.body if isinstance(n, ast.ClassDef)
                 and (names is None or n.name in names)]
        module = ast.Module(body=[ast.ImportFrom(module="__future__",
                            names=[ast.alias(name="annotations")], level=0)] + nodes,
                            type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), str(path), "exec"), namespace)
    return namespace


models = classes_from(SRC / "13_DATA_MODEL_COMPLETE_DEFINITION.md")
fact_models = classes_from(SRC / "12_ARCHITECTURE_DECISION_RECORD_PART1.md", {"Fact"})
Fact = fact_models["Fact"]
zero = Fact("f0", "attribute", {}, 0, 0, None, "")
results.append({"probe": "interval_zero_end", "kind": "executed_exact_method",
                "expected": False, "actual": zero.is_valid_at_chapter(1),
                "note": "validity_end=0 is treated as unlimited; positive chapter-only domains must explicitly reject 0."})
old = Fact("old", "attribute", {"salary": 100}, 1, 5, "new", "growth")
new = Fact("new", "attribute", {"salary": 200}, 5, None, None, "growth")
results.append({"probe": "same_chapter_transition", "kind": "representation_counterexample",
                "actual": [old.is_valid_at_chapter(5), new.is_valid_at_chapter(5)],
                "note": "Closed chapter-only intervals cannot distinguish before/after two scenes inside chapter 5."})

X = models["XuanhuanCharacter"]
x = X("c1", "测试", cultivation_speed="genius", comprehension="excellent")
serialized = x.to_dict()
results.append({"probe": "xuanhuan_serialization_loss", "kind": "executed_exact_method",
                "missing_nondefault_fields": [k for k in ("cultivation_speed", "comprehension") if k not in serialized]})
try:
    X(**serialized).to_dict()
    result = "success"
except Exception as e:
    result = type(e).__name__ + ": " + str(e)
results.append({"probe": "documented_dictionary_roundtrip", "kind": "executed_exact_method",
                "actual": result,
                "note": "An explicit mapper must restore enums; dataclass annotations do not perform conversion."})
W = models["UrbanWorldview"]
w = W("w1", "都市", "urban", "测试世界", "现代", "城市", social_circles=["高校圈"])
results.append({"probe": "urban_worldview_serialization_loss", "kind": "executed_exact_method",
                "social_circles_in_dict": "social_circles" in w.to_dict()})

domain_char_keys = sorted(models["UrbanCharacter"]("u1", "测试").to_dict())
sql_text = (SRC / "18_DATABASE_SCHEMA_DESIGN.md").read_text()
char_body = re.search(r"CREATE TABLE characters \((.*?)\n\);", sql_text, re.S).group(1)
sql_char_keys = re.findall(r"^    (\w+) (?:UUID|VARCHAR|INTEGER|TEXT|TIMESTAMP|JSONB)", char_body, re.M)
results.append({"probe": "character_mapper_contract", "kind": "static_contract_comparison",
                "domain_keys_not_columns": sorted(set(domain_char_keys) - set(sql_char_keys)),
                "required_sql_scope_missing_in_domain": "novel_id" not in domain_char_keys,
                "genre_id_column_exists": "genre_id" in sql_char_keys})

db = sqlite3.connect(":memory:")
db.execute("PRAGMA foreign_keys=ON")
db.executescript("""
CREATE TABLE novels (id TEXT PRIMARY KEY);
CREATE TABLE characters (id TEXT PRIMARY KEY, novel_id TEXT NOT NULL REFERENCES novels(id));
CREATE TABLE relationships (
 id TEXT PRIMARY KEY,
 novel_id TEXT NOT NULL REFERENCES novels(id),
 character_a_id TEXT NOT NULL REFERENCES characters(id),
 character_b_id TEXT NOT NULL REFERENCES characters(id),
 relationship_type TEXT NOT NULL,
 intensity INTEGER DEFAULT 50 CHECK (intensity >= 0 AND intensity <= 100),
 CHECK(character_a_id != character_b_id),
 UNIQUE(novel_id, character_a_id, character_b_id, relationship_type)
);
INSERT INTO novels VALUES ('book-a'), ('book-b');
INSERT INTO characters VALUES ('alice', 'book-a'), ('bob', 'book-b');
INSERT INTO relationships(id, novel_id, character_a_id, character_b_id, relationship_type)
 VALUES ('r1', 'book-a', 'alice', 'bob', 'business');
""")
results.append({"probe": "cross_novel_relationship", "kind": "sqlite_equivalent_fk_logic_only",
                "insert_accepted": db.execute("SELECT count(*) FROM relationships").fetchone()[0] == 1,
                "foreign_key_check": db.execute("PRAGMA foreign_key_check").fetchall(),
                "note": "No PostgreSQL server was used; reproduced the same single-column FK predicates in SQLite."})
db.close()

chapter_body = re.search(r"CREATE TABLE chapters \((.*?)\n\);", sql_text, re.S).group(1)
chapter_cols = re.findall(r"^    (\w+) (?:UUID|VARCHAR|INTEGER|TEXT|TIMESTAMP|JSONB|FLOAT|BOOLEAN)", chapter_body, re.M)
view = re.search(r"CREATE OR REPLACE VIEW chapter_with_context AS(.*?);", sql_text, re.S).group(1)
results.append({"probe": "view_duplicate_genre_column", "kind": "static_ddl_analysis",
                "c_star_contains_genre_id": "genre_id" in chapter_cols,
                "view_reselects_n_genre_id_without_alias": bool(re.search(r"n\.genre_id,", view)),
                "postgres_executed": False})
results.append({"probe": "chinese_textsearch_configuration", "kind": "static_dependency_analysis",
                "uses_chinese": "to_tsvector('chinese'" in sql_text,
                "defines_text_search_configuration": "CREATE TEXT SEARCH CONFIGURATION" in sql_text,
                "declared_extensions": re.findall(r'CREATE EXTENSION IF NOT EXISTS "([^"]+)"', sql_text),
                "postgres_executed": False})

OUT.write_text(json.dumps({
    "scope": "Document example probes, not a deployed implementation audit",
    "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                      [SRC / "13_DATA_MODEL_COMPLETE_DEFINITION.md", SRC / "12_ARCHITECTURE_DECISION_RECORD_PART1.md", SRC / "18_DATABASE_SCHEMA_DESIGN.md"]},
    "probes": results,
}, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"probes": len(results), "output": str(OUT)}, ensure_ascii=False))
