"""test_candidate_normalize.py — W12 shape-only normalization (CLOSE-14).

Pins the invariants of runtime/candidates/normalize.py, the layer that sits
between extract() and reconcile(): it makes SHAPE fit the frozen schema (scalar
→ array, scalar leaf → string, name → live entity-id) so schema-shape mismatches
stop masquerading as un-mintable — WITHOUT inventing facts, minting, or mapping
prose onto enums (those stay for the human / for reconcile to mark unverifiable).

Schema-driven + deterministic; no live model needed.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from runtime.registry_loader import load as load_registry
from runtime.candidates.reconcile import RawCandidate, reconcile, build_field_constraints
from runtime.candidates.normalize import normalize_candidates, _field_shapes

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA_DIR = STANDARD / "phase-1" / "generated" / "json-schema"


def _make_project(tmp_path, *, ability_name="梦蚀之眼", ability_id="MAG-00001") -> Path:
    facts = tmp_path / "registry" / "facts"
    chars = facts / "characters"
    chars.mkdir(parents=True)
    (chars / "CHR-00001.yaml").write_text(yaml.safe_dump({
        "id": "CHR-00001", "name": "Edric", "status": "active",
        "fact_version": 1, "importance": "central",
        "physical_facts": {"eye_color": "amber"},
        "abilities": [],
    }, allow_unicode=True), encoding="utf-8")
    # a magic entity the abilities array can reference by id
    mag = facts / "magic"
    mag.mkdir(parents=True, exist_ok=True)
    (mag / f"{ability_id}.yaml").write_text(yaml.safe_dump({
        "id": ability_id, "name": ability_name, "status": "active",
        "fact_version": 1,
    }, allow_unicode=True), encoding="utf-8")
    meta = tmp_path / "registry" / "_meta"
    meta.mkdir(parents=True)
    (meta / "registry-version").write_text("1", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0", encoding="utf-8")
    return tmp_path


def _by_field(cands, field):
    return next(c for c in cands if c.field == field)


def test_field_shapes_read_from_schema():
    shapes = _field_shapes(SCHEMA_DIR, None)["Character"]
    assert shapes["abilities"] == "array_ref"      # items carry a MAG/TEC pattern
    assert shapes["aliases"] == "array_plain"       # items are plain strings
    assert shapes["physical_facts"] == "obj_str"    # additionalProperties: string
    assert shapes["status"] == "string"


def test_scalar_wraps_into_plain_array(tmp_path):
    reg = load_registry(_make_project(tmp_path))
    cands = [RawCandidate("Character", "aliases", "流亡骑士", "e", "CHR-00001")]
    out = normalize_candidates(cands, reg=reg, schema_dir=SCHEMA_DIR)
    assert out[0].value == ["流亡骑士"]


def test_scalar_leaf_coerced_to_string(tmp_path):
    reg = load_registry(_make_project(tmp_path))
    cands = [RawCandidate("Character", "physical_facts.height_cm", 180, "e", "CHR-00001")]
    out = normalize_candidates(cands, reg=reg, schema_dir=SCHEMA_DIR)
    assert out[0].value == "180"


def test_ability_name_resolves_to_live_entity_id(tmp_path):
    reg = load_registry(_make_project(tmp_path, ability_name="梦蚀之眼", ability_id="MAG-00001"))
    # prose names the ability; schema wants an array of MAG/TEC ids
    cands = [RawCandidate("Character", "abilities", "梦蚀之眼", "e", "CHR-00001")]
    out = normalize_candidates(cands, reg=reg, schema_dir=SCHEMA_DIR)
    assert out[0].value == ["MAG-00001"]  # wrapped AND resolved


def test_unresolved_ability_name_left_verbatim(tmp_path):
    # never invent a ref — an unknown ability name stays a name (reconcile will
    # surface it honestly rather than fabricate a MAG id)
    reg = load_registry(_make_project(tmp_path))
    cands = [RawCandidate("Character", "abilities", "不存在的能力", "e", "CHR-00001")]
    out = normalize_candidates(cands, reg=reg, schema_dir=SCHEMA_DIR)
    assert out[0].value == ["不存在的能力"]


def test_prose_into_enum_is_not_normalized(tmp_path):
    # narrative situation onto a lifecycle enum is a semantic mapping — NOT shape.
    # normalize must leave it; reconcile marks it unverifiable.
    reg = load_registry(_make_project(tmp_path))
    cands = [RawCandidate("Character", "status", "受伤、被追捕", "e", "CHR-00001")]
    out = normalize_candidates(cands, reg=reg, schema_dir=SCHEMA_DIR)
    assert out[0].value == "受伤、被追捕"  # unchanged
    cons = build_field_constraints(SCHEMA_DIR, None)
    recon = reconcile(reg, out, field_constraints=cons)
    assert recon.items[0].classification == "unverifiable"


def test_whole_object_prose_left_for_reconcile(tmp_path):
    # a bare string assigned to the whole physical_facts object is not a shape
    # fix (splitting prose into keys is semantic) — leave it untouched.
    reg = load_registry(_make_project(tmp_path))
    cands = [RawCandidate("Character", "physical_facts", "颅骨骨折、脾脏破裂", "e", "CHR-00001")]
    out = normalize_candidates(cands, reg=reg, schema_dir=SCHEMA_DIR)
    assert out[0].value == "颅骨骨折、脾脏破裂"


def test_already_correct_shapes_unchanged(tmp_path):
    reg = load_registry(_make_project(tmp_path))
    cands = [
        RawCandidate("Character", "abilities", ["MAG-00001"], "e", "CHR-00001"),
        RawCandidate("Character", "aliases", ["流亡骑士"], "e", "CHR-00001"),
        RawCandidate("Character", "physical_facts.eye_color", "green", "e", "CHR-00001"),
    ]
    out = normalize_candidates(cands, reg=reg, schema_dir=SCHEMA_DIR)
    assert [c.value for c in out] == [["MAG-00001"], ["流亡骑士"], "green"]


def test_totality_bad_input_never_drops_candidate(tmp_path):
    # a candidate with an odd value must survive normalization (never dropped,
    # never raises) so a normalization bug can't break the W12 reflow (ADR-003).
    reg = load_registry(_make_project(tmp_path))
    cands = [
        RawCandidate("Character", "abilities", {"weird": "dict"}, "e", "CHR-00001"),
        RawCandidate("UnknownType", "mystery_field", "x", "e", None),
    ]
    out = normalize_candidates(cands, reg=reg, schema_dir=SCHEMA_DIR)
    assert len(out) == 2


def test_no_schema_dir_is_noop(tmp_path):
    reg = load_registry(_make_project(tmp_path))
    cands = [RawCandidate("Character", "aliases", "solo", "e", "CHR-00001")]
    out = normalize_candidates(cands, reg=reg, schema_dir=None)
    assert out[0].value == "solo"  # unchanged, no shapes to apply
