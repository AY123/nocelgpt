"""test_mint.py — the mint executor (roadmap Phase 5.2), the EXECUTION half.

Pins the invariants of the system's ONLY fact-writer:
  - HUMAN-AUTHORIZED (ADR-009): no write without confirmed=True; a preview writes
    nothing and issues no receipt.
  - ADDITIVE + NEW (5.2 + 5.4b): additive fills an empty field on an existing
    entity; new establishes a brand-new entity by name at a ledger-minted id. A
    conflicting/consistent/unverifiable accepted candidate is REFUSED, not
    silently skipped; an out-of-scope `new` (ambiguous type, structured-required
    type, non-name field) is REFUSED with a specific reason.
  - VALIDATE-THEN-WRITE: a mint that would break the deterministic gate is refused
    and writes NOTHING (the SSOT is never left invalid).
  - STALE PLANS REFUSED (ADR-006): a plan whose pinned fact advanced cannot mint.
  - NEW never overwrites: an id is allocated strictly above the ledger max AND the
    highest existing registry ordinal (a divergent ledger cannot clobber a fact).
  - A committed mint bumps fact_version + the monotone registry-version and emits
    a schema-valid MintReceipt.

Deterministic + fixture-validated — no live model.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from runtime.registry_loader import load as load_registry
from runtime.candidates.reconcile import RawCandidate, reconcile
from runtime.candidates import plan as planmod
from runtime import mint, idmint
from runtime.mint import MintRefused

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA_DIR = STANDARD / "phase-1" / "generated" / "json-schema"
_RECEIPT_SCHEMA = Draft202012Validator(json.loads(
    (STANDARD / "contracts" / "mint-receipt.schema.json").read_text(encoding="utf-8")))


def _receipt_errors(r: dict) -> list:
    return [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
            for e in _RECEIPT_SCHEMA.iter_errors(r)]


# --------------------------------------------------------------------------- #
# Fixtures — a real (schema-valid) project so the re-gate actually runs        #
# --------------------------------------------------------------------------- #
def _make_project(tmp_path) -> Path:
    """A minimal but SCHEMA-VALID project: two characters + one timeline + one
    event, so the post-mint validator has real facts (and refs) to check."""
    facts = tmp_path / "registry" / "facts"
    (facts / "characters").mkdir(parents=True)
    (facts / "timelines").mkdir(parents=True)
    (facts / "events").mkdir(parents=True)
    (facts / "characters" / "CHR-00001.yaml").write_text(yaml.safe_dump({
        "id": "CHR-00001", "name": "Edric", "status": "active",
        "fact_version": 1, "importance": "central",
        "aliases": [], "notes": "",
        "physical_facts": {"eye_color": "amber"},
    }, allow_unicode=True), encoding="utf-8")
    (facts / "timelines" / "TML-00001.yaml").write_text(yaml.safe_dump({
        "id": "TML-00001", "name": "main", "status": "active",
        "fact_version": 1, "kind": "main", "ordering": "relative",
    }, allow_unicode=True), encoding="utf-8")
    (facts / "events" / "EVT-00001.yaml").write_text(yaml.safe_dump({
        "id": "EVT-00001", "name": "rescue", "status": "active",
        "fact_version": 1, "timeline": "TML-00001", "sequence_index": 1,
        "participants": ["CHR-00001"], "causes": [], "effects": [],
    }, allow_unicode=True), encoding="utf-8")
    meta = tmp_path / "registry" / "_meta"
    meta.mkdir(parents=True)
    (meta / "registry-version").write_text("1", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0", encoding="utf-8")
    return tmp_path


def _stage_additive(project, *, field="aliases", value=None, entity="CHR-00001"):
    value = ["流亡骑士"] if value is None else value
    reg = load_registry(project, schema_dir=SCHEMA_DIR)
    draft = {"task_id": "TASK-00001", "content_hash": "sha256:x",
             "provenance": {"derived_from": [f"{entity}@v1"]}}
    recon = reconcile(reg, [RawCandidate("Character", field, value, "prose", entity, 0.9)])
    plan, _ = planmod.stage_plan(project_path=project, plan_id="FCP-00001",
                                 draft=draft, recon=recon, extractor_id="det")
    return plan


def _stage_new(project, *, target_type="Character", name="薇拉", field="name"):
    """Stage a plan whose single candidate is `new` (no matching entity), so it
    routes through the 5.4b ledger-mint path. matched_entity_id=None forces the
    reconciler's `new` branch."""
    reg = load_registry(project, schema_dir=SCHEMA_DIR)
    draft = {"task_id": "TASK-00002", "content_hash": "sha256:y",
             "provenance": {"derived_from": []}}
    recon = reconcile(reg, [RawCandidate(target_type, field, name, "prose", None, 0.9)])
    plan, _ = planmod.stage_plan(project_path=project, plan_id="FCP-00002",
                                 draft=draft, recon=recon, extractor_id="det")
    return plan


def _chr(project, cid="CHR-00001") -> dict:
    return yaml.safe_load(
        (project / f"registry/facts/characters/{cid}.yaml").read_text(encoding="utf-8"))


def _rv(project) -> int:
    return int((project / "registry/_meta/registry-version").read_text(encoding="utf-8").strip())


# --------------------------------------------------------------------------- #
# Happy path: a committed additive mint                                        #
# --------------------------------------------------------------------------- #
def test_additive_mint_writes_fact_and_bumps_versions(tmp_path):
    project = _make_project(tmp_path)
    plan = _stage_additive(project)
    assert _chr(project)["aliases"] == []
    assert _rv(project) == 1

    receipt = mint.execute_mint(project_path=project, plan=plan,
                                accepted=["CAND-00001"], schema_dir=SCHEMA_DIR,
                                confirmed=True, actor="tester")

    # fact written, versions bumped
    assert _chr(project)["aliases"] == ["流亡骑士"]
    assert _chr(project)["fact_version"] == 2
    assert _rv(project) == 2
    # receipt records the transition
    m = receipt["minted"][0]
    assert m["classification"] == "additive"
    assert m["fact_version"] == {"before": 1, "after": 2}
    assert receipt["registry_version"] == {"before": 1, "after": 2}
    assert receipt["authority"] == "human"
    assert receipt["gating"] is False
    assert receipt["authorized"]["confirmed"] is True
    assert receipt["revalidation"]["passed"] is True


def test_receipt_validates_against_standard_schema(tmp_path):
    project = _make_project(tmp_path)
    plan = _stage_additive(project)
    receipt = mint.execute_mint(project_path=project, plan=plan,
                                accepted=["CAND-00001"], schema_dir=SCHEMA_DIR,
                                confirmed=True)
    assert _receipt_errors(receipt) == []


def test_receipt_is_persisted_as_derived_never_facts(tmp_path):
    project = _make_project(tmp_path)
    plan = _stage_additive(project)
    receipt = mint.execute_mint(project_path=project, plan=plan,
                                accepted=["CAND-00001"], schema_dir=SCHEMA_DIR,
                                confirmed=True)
    rid = receipt["id"]
    assert (project / "registry" / "derived" / "mint-receipts" / f"{rid}.json").exists()


# --------------------------------------------------------------------------- #
# Human authority (ADR-009)                                                    #
# --------------------------------------------------------------------------- #
def test_mint_requires_confirmation(tmp_path):
    project = _make_project(tmp_path)
    plan = _stage_additive(project)
    try:
        mint.execute_mint(project_path=project, plan=plan, accepted=["CAND-00001"],
                          schema_dir=SCHEMA_DIR, confirmed=False)
        assert False, "expected refusal"
    except MintRefused as e:
        assert e.reason == "not_confirmed"
    # nothing written
    assert _chr(project)["aliases"] == []
    assert _rv(project) == 1


def test_preview_writes_nothing_but_reports_gate(tmp_path):
    project = _make_project(tmp_path)
    plan = _stage_additive(project)
    mint_plan, report = mint.preview_mint(project_path=project, plan=plan,
                                          accepted=["CAND-00001"], schema_dir=SCHEMA_DIR)
    assert report.ok is True
    assert len(mint_plan.items) == 1
    # preview is inert
    assert _chr(project)["aliases"] == []
    assert _rv(project) == 1
    assert not (project / "registry" / "derived" / "mint-receipts").exists()


# --------------------------------------------------------------------------- #
# Additive-only scope: non-additive accepted candidates are REFUSED            #
# --------------------------------------------------------------------------- #
def test_conflicting_accepted_candidate_is_refused(tmp_path):
    project = _make_project(tmp_path)
    # eye_color amber already declared → asserting blue is `conflicting`
    reg = load_registry(project, schema_dir=SCHEMA_DIR)
    draft = {"task_id": "T", "content_hash": "sha256:x",
             "provenance": {"derived_from": ["CHR-00001@v1"]}}
    recon = reconcile(reg, [RawCandidate(
        "Character", "physical_facts.eye_color", "blue", "prose", "CHR-00001", 0.9)])
    plan, _ = planmod.stage_plan(project_path=project, plan_id="FCP-00001",
                                 draft=draft, recon=recon, extractor_id="det")
    assert plan["items"][0]["classification"] == "conflicting"
    try:
        mint.execute_mint(project_path=project, plan=plan, accepted=["CAND-00001"],
                          schema_dir=SCHEMA_DIR, confirmed=True)
        assert False, "expected refusal"
    except MintRefused as e:
        assert e.reason == "non_mintable_class"
    # the declared fact is untouched — no retcon
    assert _chr(project)["physical_facts"]["eye_color"] == "amber"
    assert _rv(project) == 1


def test_unknown_accepted_candidate_is_refused(tmp_path):
    project = _make_project(tmp_path)
    plan = _stage_additive(project)
    try:
        mint.execute_mint(project_path=project, plan=plan, accepted=["CAND-99999"],
                          schema_dir=SCHEMA_DIR, confirmed=True)
        assert False, "expected refusal"
    except MintRefused as e:
        assert e.reason == "unknown_candidate"


def test_nothing_accepted_is_refused(tmp_path):
    project = _make_project(tmp_path)
    plan = _stage_additive(project)
    try:
        mint.execute_mint(project_path=project, plan=plan, accepted=[],
                          schema_dir=SCHEMA_DIR, confirmed=True)
        assert False, "expected refusal"
    except MintRefused as e:
        assert e.reason == "nothing_accepted"


# --------------------------------------------------------------------------- #
# Validate-then-write: a registry-breaking mint writes NOTHING                 #
# --------------------------------------------------------------------------- #
def test_mint_that_breaks_the_gate_is_refused_and_writes_nothing(tmp_path):
    project = _make_project(tmp_path)
    # `abilities` requires MAG/TEC references by schema; free text fails the gate.
    plan = _stage_additive(project, field="abilities", value=["剑术"])
    assert plan["items"][0]["classification"] == "additive"
    try:
        mint.execute_mint(project_path=project, plan=plan, accepted=["CAND-00001"],
                          schema_dir=SCHEMA_DIR, confirmed=True)
        assert False, "expected refusal"
    except MintRefused as e:
        assert e.reason == "post_mint_gate_failed"
    # validate-then-write held: the SSOT is untouched, no version bump
    assert "abilities" not in _chr(project) or _chr(project)["abilities"] == []
    assert _chr(project)["fact_version"] == 1
    assert _rv(project) == 1


# --------------------------------------------------------------------------- #
# Staleness (ADR-006): a superseded reconciliation cannot mint                 #
# --------------------------------------------------------------------------- #
def test_stale_plan_is_refused(tmp_path):
    project = _make_project(tmp_path)
    plan = _stage_additive(project, field="aliases")
    # first mint succeeds and advances CHR-00001 to v2
    mint.execute_mint(project_path=project, plan=plan, accepted=["CAND-00001"],
                      schema_dir=SCHEMA_DIR, confirmed=True)
    # the SAME plan is now stale (it was reconciled against CHR-00001@v1)
    try:
        mint.execute_mint(project_path=project, plan=plan, accepted=["CAND-00001"],
                          schema_dir=SCHEMA_DIR, confirmed=True)
        assert False, "expected refusal"
    except MintRefused as e:
        assert e.reason == "plan_stale"
    # only ONE bump happened
    assert _chr(project)["fact_version"] == 2
    assert _rv(project) == 2


# --------------------------------------------------------------------------- #
# NEW path (5.4b): establish a brand-new entity by name at a ledger-minted id  #
# --------------------------------------------------------------------------- #
def _ledger_ids(project) -> list:
    return [e["id"] for e in idmint.load_ledger(project).get("entries", [])]


def test_new_character_mints_id_writes_fact_and_ledger_entry(tmp_path):
    project = _make_project(tmp_path)
    plan = _stage_new(project, name="薇拉")
    assert plan["items"][0]["classification"] == "new"
    assert _rv(project) == 1
    assert _ledger_ids(project) == []  # nothing minted yet

    receipt = mint.execute_mint(project_path=project, plan=plan,
                                accepted=["CAND-00001"], schema_dir=SCHEMA_DIR,
                                confirmed=True, actor="tester")

    m = receipt["minted"][0]
    new_id = m["entity_id"]
    # minted strictly above the seeded CHR-00001 (floor), never colliding with it
    assert new_id == "CHR-00002"
    assert m["classification"] == "new"
    assert m["type_code"] == "CHR"
    assert m["field"] == "name"
    assert m["value"] == "薇拉"
    assert m["fact_version"] == {"before": 0, "after": 1}
    assert receipt["registry_version"] == {"before": 1, "after": 2}
    # the ledger recorded exactly the id that was written to disk
    assert _ledger_ids(project) == [new_id]
    written = yaml.safe_load(
        (project / f"registry/facts/characters/{new_id}.yaml").read_text(encoding="utf-8"))
    assert written == {"id": new_id, "name": "薇拉", "status": "active", "fact_version": 1}
    # the pre-existing entity is untouched — a new mint never overwrites
    assert _chr(project)["name"] == "Edric"


def test_new_receipt_validates_against_standard_schema(tmp_path):
    project = _make_project(tmp_path)
    plan = _stage_new(project)
    receipt = mint.execute_mint(project_path=project, plan=plan,
                                accepted=["CAND-00001"], schema_dir=SCHEMA_DIR,
                                confirmed=True)
    assert _receipt_errors(receipt) == []


def test_new_preview_is_inert_no_ledger_no_fact(tmp_path):
    project = _make_project(tmp_path)
    plan = _stage_new(project)
    mint_plan, report = mint.preview_mint(project_path=project, plan=plan,
                                          accepted=["CAND-00001"], schema_dir=SCHEMA_DIR)
    assert report.ok is True
    # the provisional id is shown but NOTHING is written
    assert mint_plan.items[0].entity_id == "CHR-00002"
    assert mint_plan.items[0].classification == "new"
    assert _ledger_ids(project) == []
    assert not (project / "registry/facts/characters/CHR-00002.yaml").exists()
    assert _rv(project) == 1


def test_second_new_mint_allocates_next_sequential_id(tmp_path):
    project = _make_project(tmp_path)
    first = mint.execute_mint(project_path=project, plan=_stage_new(project, name="薇拉"),
                              accepted=["CAND-00001"], schema_dir=SCHEMA_DIR, confirmed=True)
    second = mint.execute_mint(project_path=project, plan=_stage_new(project, name="洛安"),
                               accepted=["CAND-00001"], schema_dir=SCHEMA_DIR, confirmed=True)
    assert first["minted"][0]["entity_id"] == "CHR-00002"
    assert second["minted"][0]["entity_id"] == "CHR-00003"  # monotone, no reuse
    assert _ledger_ids(project) == ["CHR-00002", "CHR-00003"]


# --------------------------------------------------------------------------- #
# NEW is deliberately narrow: out-of-scope new candidates are REFUSED          #
# --------------------------------------------------------------------------- #
def test_new_ambiguous_type_code_is_refused(tmp_path):
    # WorldRule → MAG|TEC: the mint must not guess magic-vs-tech.
    project = _make_project(tmp_path)
    plan = _stage_new(project, target_type="WorldRule", name="真气循环")
    try:
        mint.execute_mint(project_path=project, plan=plan, accepted=["CAND-00001"],
                          schema_dir=SCHEMA_DIR, confirmed=True)
        assert False, "expected refusal"
    except MintRefused as e:
        assert e.reason == "ambiguous_type_code"
    assert _ledger_ids(project) == []  # nothing minted
    assert _rv(project) == 1


def test_new_structured_required_type_is_refused(tmp_path):
    # Event requires `timeline` — not synthesizable from a name.
    project = _make_project(tmp_path)
    plan = _stage_new(project, target_type="Event", name="决战")
    try:
        mint.execute_mint(project_path=project, plan=plan, accepted=["CAND-00001"],
                          schema_dir=SCHEMA_DIR, confirmed=True)
        assert False, "expected refusal"
    except MintRefused as e:
        assert e.reason == "new_requires_structured_fields"
    assert _ledger_ids(project) == []
    assert _rv(project) == 1


def test_new_non_name_field_is_refused(tmp_path):
    # A not-yet-existent entity must be established by name first, not by a
    # secondary field. reconcile classifies an unmatched candidate as `new`
    # regardless of field, so the executor is the boundary that refuses it.
    project = _make_project(tmp_path)
    plan = _stage_new(project, target_type="Character", name=["流亡骑士"], field="aliases")
    assert plan["items"][0]["classification"] == "new"
    try:
        mint.execute_mint(project_path=project, plan=plan, accepted=["CAND-00001"],
                          schema_dir=SCHEMA_DIR, confirmed=True)
        assert False, "expected refusal"
    except MintRefused as e:
        assert e.reason == "new_needs_name"
    assert _ledger_ids(project) == []
    assert _rv(project) == 1
