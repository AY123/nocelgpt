"""test_candidates.py — Fact Candidate Pipeline (roadmap Phase 5).

Pins the pipeline's invariants: extraction is evaluative (a model reading prose)
and never gates; reconciliation is a DETERMINISTIC 5-class fold against the
Registry; a conflict is NEVER auto-resolved; a staged plan is a DERIVED artifact
(never facts, ADR-006) whose provenance is DOUBLE-PINNED (draft content_hash +
reconciled fact pins) so it inherits staleness for free; it never mints
(ADR-009, authority const human, gating const false); and the plan validates
against the Standard schema.

Deterministic + fixture-validated — no live model needed. The LLM extractor is
proven separately with a fake model (parse/degrade), same seam as the scene
planner.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from runtime import derived
from runtime.registry_loader import load as load_registry
from runtime.candidates.reconcile import RawCandidate, reconcile
from runtime.candidates.extract import DeterministicExtractor, LLMExtractor
from runtime.candidates import plan as planmod

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA_DIR = STANDARD / "phase-1" / "generated" / "json-schema"
_FCP_SCHEMA = Draft202012Validator(json.loads(
    (STANDARD / "contracts" / "fact-candidate-plan.schema.json").read_text(encoding="utf-8")))


def _fcp_errors(plan: dict) -> list:
    # The staged artifact carries a runtime provenance/content_hash block the
    # schema does not describe; validate the schema-owned core.
    core = {k: v for k, v in plan.items() if k not in ("provenance", "content_hash")}
    return [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
            for e in _FCP_SCHEMA.iter_errors(core)]


# --------------------------------------------------------------------------- #
# Fixtures — a tiny registry with one character carrying a declared fact       #
# --------------------------------------------------------------------------- #
def _make_project(tmp_path, *, eye_color="amber", version=1) -> Path:
    facts = tmp_path / "registry" / "facts" / "characters"
    facts.mkdir(parents=True)
    (facts / "CHR-00001.yaml").write_text(yaml.safe_dump({
        "id": "CHR-00001", "name": "Edric", "status": "active",
        "fact_version": version, "importance": "central",
        "physical_facts": {"eye_color": eye_color},
        "abilities": [],
    }, allow_unicode=True), encoding="utf-8")
    meta = tmp_path / "registry" / "_meta"
    meta.mkdir(parents=True)
    (meta / "registry-version").write_text(str(version), encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0", encoding="utf-8")
    return tmp_path


def _draft() -> dict:
    return {
        "task_id": "TASK-00001",
        "content_hash": "sha256:deadbeef",
        "body": "his amber eyes …",
        "provenance": {"derived_from": ["CHR-00001@v1"]},
    }


# --------------------------------------------------------------------------- #
# The deterministic 5-class reconciliation — the anti-rot core                 #
# --------------------------------------------------------------------------- #
def test_five_classifications(tmp_path):
    reg = load_registry(_make_project(tmp_path))
    cands = [
        RawCandidate("Character", "physical_facts.eye_color", "amber", "e", "CHR-00001"),  # consistent
        RawCandidate("Character", "physical_facts.eye_color", "blue", "e", "CHR-00001"),   # conflicting
        RawCandidate("Character", "abilities", ["sword"], "e", "CHR-00001"),               # additive (empty)
        RawCandidate("Character", "status", "active", "e", "CHR-99999"),                   # new (no entity)
        RawCandidate("Character", "physical_facts", "free text", "e", "CHR-00001"),        # unverifiable
    ]
    r = reconcile(reg, cands)
    got = [i.classification for i in r.items]
    assert got == ["consistent", "conflicting", "additive", "new", "unverifiable"], got


def test_conflict_surfaces_both_values_and_never_mutates_facts(tmp_path):
    project = _make_project(tmp_path, eye_color="amber")
    reg = load_registry(project)
    r = reconcile(reg, [
        RawCandidate("Character", "physical_facts.eye_color", "blue", "prose says blue", "CHR-00001")])
    item = r.items[0]
    assert item.classification == "conflicting"
    assert item.extracted_value == "blue"
    assert item.existing_value == "amber"   # reviewer sees prose-vs-fact side by side
    # Reconciliation is a pure fold — the fact on disk is untouched.
    on_disk = yaml.safe_load(
        (project / "registry/facts/characters/CHR-00001.yaml").read_text(encoding="utf-8"))
    assert on_disk["physical_facts"]["eye_color"] == "amber"
    assert on_disk["fact_version"] == 1


def test_case_and_whitespace_insensitive_consistency(tmp_path):
    reg = load_registry(_make_project(tmp_path, eye_color="Amber"))
    r = reconcile(reg, [
        RawCandidate("Character", "physical_facts.eye_color", "  amber ", "e", "CHR-00001")])
    assert r.items[0].classification == "consistent"


def test_extractor_named_missing_entity_is_new_not_conflict(tmp_path):
    reg = load_registry(_make_project(tmp_path))
    # extractor points at an id that does not exist — there is nothing to
    # contradict, so it is a `new` proposal, never a phantom conflict.
    r = reconcile(reg, [
        RawCandidate("Character", "status", "active", "e", "CHR-88888")])
    assert r.items[0].classification == "new"


# --------------------------------------------------------------------------- #
# Provenance double-pin + staleness inheritance                                #
# --------------------------------------------------------------------------- #
def test_reconciled_against_pins_current_versions(tmp_path):
    reg = load_registry(_make_project(tmp_path, version=1))
    r = reconcile(reg, [
        RawCandidate("Character", "abilities", ["x"], "e", "CHR-00001")])
    assert r.reconciled_against == ["CHR-00001@v1"]


def test_staged_plan_is_double_pinned_and_reproducible(tmp_path):
    project = _make_project(tmp_path)
    reg = load_registry(project)
    ex = DeterministicExtractor()
    draft = _draft()

    def stage():
        recon = reconcile(reg, ex.extract(draft))
        return planmod.stage_plan(project_path=project, plan_id="FCP-00001",
                                  draft=draft, recon=recon, extractor_id=ex.model_id)

    plan, rel = stage()
    # double pin: draft content_hash + reconciled fact pins
    assert plan["source"]["content_hash"] == "sha256:deadbeef"
    assert plan["reconciled_against"] == ["CHR-00001@v1"]
    assert plan["provenance"]["derived_from"] == ["CHR-00001@v1"]
    # written under derived, indexed
    assert rel == "registry/derived/fact-candidates/FCP-00001.json"
    assert (project / rel).exists()
    # reproducible: same draft + registry => same content_hash
    plan2, _ = stage()
    assert plan["content_hash"] == plan2["content_hash"]


def test_plan_goes_stale_when_a_pinned_fact_advances(tmp_path):
    project = _make_project(tmp_path, version=1)
    reg = load_registry(project)
    recon = reconcile(reg, [RawCandidate("Character", "abilities", ["x"], "e", "CHR-00001")])
    planmod.stage_plan(project_path=project, plan_id="FCP-00001",
                       draft=_draft(), recon=recon, extractor_id="det")
    # nothing stale yet
    assert derived.audit_index(reg, project) == []
    # advance the pinned fact (as a future mint would) and reload the registry
    chr_path = project / "registry/facts/characters/CHR-00001.yaml"
    rec = yaml.safe_load(chr_path.read_text(encoding="utf-8"))
    rec["fact_version"] = 2
    chr_path.write_text(yaml.safe_dump(rec, allow_unicode=True), encoding="utf-8")
    reg2 = load_registry(project)
    findings = derived.audit_index(reg2, project)
    # the plan is now stale — you must not mint from a superseded reconciliation
    assert any(f.artifact_id == "FCP-00001" for f in findings), findings


# --------------------------------------------------------------------------- #
# Structural invariants: never gates, authority human, never writes facts      #
# --------------------------------------------------------------------------- #
def test_plan_never_gates_and_stays_human_authority(tmp_path):
    reg = load_registry(_make_project(tmp_path))
    recon = reconcile(reg, [RawCandidate("Character", "abilities", ["x"], "e", "CHR-00001")])
    plan = planmod.build_plan(plan_id="FCP-00001", draft=_draft(),
                              recon=recon, extractor_id="det")
    assert plan["gating"] is False
    assert plan["authority"] == "human"
    assert plan["review_status"] == "needs_human_review"
    assert plan["policy"]["writes_registry_facts"] is False
    assert plan["policy"]["requires_human_approval"] is True
    assert plan["policy"]["requires_id_mint_review"] is True


def test_staging_writes_only_derived_never_facts(tmp_path):
    project = _make_project(tmp_path)
    reg = load_registry(project)
    before = (project / "registry/facts/characters/CHR-00001.yaml").read_text(encoding="utf-8")
    recon = reconcile(reg, [
        RawCandidate("Character", "physical_facts.eye_color", "blue", "e", "CHR-00001")])
    planmod.stage_plan(project_path=project, plan_id="FCP-00001",
                       draft=_draft(), recon=recon, extractor_id="det")
    after = (project / "registry/facts/characters/CHR-00001.yaml").read_text(encoding="utf-8")
    assert before == after  # a conflicting candidate did not touch the fact


def test_plan_validates_against_standard_schema(tmp_path):
    project = _make_project(tmp_path)
    reg = load_registry(project)
    recon = reconcile(reg, [
        RawCandidate("Character", "abilities", ["sword"], "e", "CHR-00001"),
        RawCandidate("Character", "status", "active", "e", "CHR-99999"),
    ])
    plan, _ = planmod.stage_plan(project_path=project, plan_id="FCP-00001",
                                 draft=_draft(), recon=recon, extractor_id="det")
    assert _fcp_errors(plan) == []


# --------------------------------------------------------------------------- #
# Extractor seam: deterministic stub + LLM drop-in (parse/degrade)             #
# --------------------------------------------------------------------------- #
def test_deterministic_extractor_reads_only_provenance_pins():
    cands = DeterministicExtractor().extract(_draft())
    assert [c.matched_entity_id for c in cands] == ["CHR-00001"]
    # the stub never invents a conflict — it only re-asserts declared identity
    assert all(c.field == "status" for c in cands)


class _FakeModel:
    model_id = "fake-extractor"

    def __init__(self, text):
        self._text = text

    def generate(self, prompt):
        class _R:
            model_id = "fake-extractor"
            text = self._text
        return _R()


def test_llm_extractor_parses_candidates():
    payload = json.dumps({"candidates": [
        {"target_type": "Character", "matched_entity_id": "CHR-00001",
         "field": "physical_facts.eye_color", "value": "amber",
         "evidence": "琥珀色的眼睛", "confidence": 90}]})
    cands = LLMExtractor(_FakeModel(payload)).extract(_draft())
    assert len(cands) == 1
    assert cands[0].field == "physical_facts.eye_color"
    assert cands[0].confidence == 0.9   # 0-100 coerced to 0-1


def test_llm_extractor_degrades_to_empty_on_bad_output():
    assert LLMExtractor(_FakeModel("not json")).extract(_draft()) == []


def test_llm_extractor_skips_malformed_items():
    payload = json.dumps({"candidates": [
        {"field": "x"},                                   # missing target_type
        {"target_type": "Character", "field": "abilities", "value": ["y"],
         "evidence": "z", "confidence": 0.5}]})
    cands = LLMExtractor(_FakeModel(payload)).extract(_draft())
    assert len(cands) == 1 and cands[0].field == "abilities"


# --------------------------------------------------------------------------- #
# Real-model finding fix (2026-07-05): the extractor must SEE entity names, and #
# the reconciler must RESOLVE a named-but-unidentified subject — else a chapter  #
# about an existing character yields all-phantom `new` (a duplicate-entity bug   #
# a real DeepSeek run exposed against id-only prompting).                        #
# --------------------------------------------------------------------------- #
from runtime.candidates.extract import entity_roster, build_extract_prompt


class _CapturingModel:
    """Records the prompt it was asked to generate, so a test can assert what the
    extractor showed the model (names yes, declared values no)."""
    model_id = "capturing"

    def __init__(self):
        self.prompt = None

    def generate(self, prompt):
        self.prompt = prompt
        class _R:
            model_id = "capturing"
            text = '{"candidates": []}'
        return _R()


def test_roster_carries_names_and_aliases_not_values(tmp_path):
    # add a Chinese alias so cross-language resolution has something to bridge on
    reg = load_registry(_make_project(tmp_path, eye_color="amber"))
    reg.facts["CHR-00001"]["aliases"] = ["埃德里克"]
    roster = entity_roster(reg, reg.all_ids())
    assert roster == [{"id": "CHR-00001", "type": "CHR", "name": "Edric",
                       "aliases": ["埃德里克"]}]
    # IDENTITY only — the declared eye_color must NOT be in the roster (value
    # comparison is the reconciler's job; leaking it would let the model prejudge)
    assert "amber" not in json.dumps(roster, ensure_ascii=False)


def test_prompt_shows_names_but_hides_declared_values(tmp_path):
    # use a declared value that does NOT appear in the prose body, so the only way
    # it could show up in the prompt is a roster leak (the thing we forbid).
    reg = load_registry(_make_project(tmp_path, eye_color="chartreuse"))
    reg.facts["CHR-00001"]["aliases"] = ["埃德里克"]
    roster = entity_roster(reg, reg.all_ids())
    model = _CapturingModel()
    LLMExtractor(model).extract(_draft(), known_entities=roster)
    assert "Edric" in model.prompt          # the model can now see the name
    assert "埃德里克" in model.prompt         # and the cross-language alias
    assert "chartreuse" not in model.prompt  # but never the declared value


def test_reconcile_resolves_name_in_id_slot(tmp_path):
    # a model that put the NAME where the id belongs must still resolve, not `new`
    reg = load_registry(_make_project(tmp_path, eye_color="amber"))
    cand = RawCandidate("Character", "physical_facts.eye_color", "blue", "prose",
                        matched_entity_id="Edric", confidence=0.9)
    recon = reconcile(reg, [cand])
    it = recon.items[0]
    assert it.matched_entity_id == "CHR-00001"      # resolved by name, not `new`
    assert it.classification == "conflicting"       # amber vs blue, a real conflict


def test_reconcile_resolves_alias(tmp_path):
    reg = load_registry(_make_project(tmp_path, eye_color="amber"))
    reg.facts["CHR-00001"]["aliases"] = ["埃德里克"]
    cand = RawCandidate("Character", "abilities", ["剑术"], "prose",
                        matched_entity_id="埃德里克", confidence=0.9)
    recon = reconcile(reg, [cand])
    assert recon.items[0].matched_entity_id == "CHR-00001"   # alias resolved
    assert recon.items[0].classification == "additive"        # abilities was empty


def test_reconcile_resolves_name_field_value(tmp_path):
    # the phantom-duplicate case: a `name` candidate with a BLANK id whose value
    # matches an existing entity must resolve to it (consistent), not mint `new`.
    reg = load_registry(_make_project(tmp_path))
    cand = RawCandidate("Character", "name", "Edric", "prose",
                        matched_entity_id=None, confidence=0.9)
    recon = reconcile(reg, [cand])
    assert recon.items[0].matched_entity_id == "CHR-00001"
    assert recon.items[0].classification == "consistent"     # same name, confirmed


def test_reconcile_genuinely_new_stays_new(tmp_path):
    # a name that matches nothing is still correctly `new` (the safety net does
    # not over-match — no false resolution).
    reg = load_registry(_make_project(tmp_path))
    cand = RawCandidate("Character", "name", "洛安", "prose",
                        matched_entity_id=None, confidence=0.9)
    recon = reconcile(reg, [cand])
    assert recon.items[0].classification == "new"


# --------------------------------------------------------------------------- #
# Second real-model finding fix (2026-07-05): the model mapped narrative        #
# situation (受伤/被追捕) onto Character.status, a LIFECYCLE enum — a false       #
# `conflicting` that pollutes the human review queue. Enum-aware reconcile       #
# reclassifies an out-of-enum value as `unverifiable`, not conflicting.          #
# --------------------------------------------------------------------------- #
from runtime.candidates.reconcile import build_field_constraints


def test_build_field_constraints_reads_status_enum():
    cons = build_field_constraints(SCHEMA_DIR, None)
    assert cons["Character"]["status"] == ["active", "deprecated", "tombstoned"]
    # importance is also enum-constrained; a free-text field like `notes` is not
    assert "importance" in cons["Character"]
    assert "notes" not in cons["Character"]


def test_out_of_enum_value_is_unverifiable_not_conflicting(tmp_path):
    reg = load_registry(_make_project(tmp_path))       # status declared "active"
    cons = build_field_constraints(SCHEMA_DIR, None)
    cand = RawCandidate("Character", "status", "受伤、被追捕", "prose",
                        matched_entity_id="CHR-00001", confidence=0.9)
    recon = reconcile(reg, [cand], field_constraints=cons)
    it = recon.items[0]
    assert it.classification == "unverifiable"          # NOT a false conflict
    assert "status only accepts" in it.reason


def test_valid_enum_value_still_conflicts(tmp_path):
    # a value that IS in the enum but differs from the declared one is a real
    # conflict — the enum check must not swallow genuine retcons.
    reg = load_registry(_make_project(tmp_path))       # status "active"
    cons = build_field_constraints(SCHEMA_DIR, None)
    cand = RawCandidate("Character", "status", "deprecated", "prose",
                        matched_entity_id="CHR-00001", confidence=0.9)
    recon = reconcile(reg, [cand], field_constraints=cons)
    assert recon.items[0].classification == "conflicting"


def test_reconcile_without_constraints_is_unchanged(tmp_path):
    # backward compatibility: absent constraints, an out-of-enum value is still a
    # conflicting (the pre-fix behavior), so existing callers are unaffected.
    reg = load_registry(_make_project(tmp_path))
    cand = RawCandidate("Character", "status", "受伤", "prose",
                        matched_entity_id="CHR-00001", confidence=0.9)
    recon = reconcile(reg, [cand])
    assert recon.items[0].classification == "conflicting"
