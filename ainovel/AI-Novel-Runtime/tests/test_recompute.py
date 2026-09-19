"""test_recompute.py — the Derived Recompute Engine (roadmap Phase 5.3).

Pins the invariants of the loop's final link:
  - DETERMINISTIC/GENERATIVE PARTITION: a pure fact-fold (story-state) is
    auto-rebuilt + written back with a fresh pin so it is no longer stale; a
    generative artifact (draft) is STAGED, never auto-rebuilt.
  - NEVER RE-AUTHORS PROSE: a stale draft stays stale after apply (only a human
    regenerates it), and its regeneration command is recorded.
  - NOT A FACT-WRITER: recompute touches only registry/derived/, never facts.
  - plan writes nothing; apply emits a schema-valid recompute-report.

Deterministic + fixture-validated — no live model.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from runtime.registry_loader import load as load_registry
from runtime.memory.state import project_state, state_artifact
from runtime import derived, recompute

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA_DIR = STANDARD / "phase-1" / "generated" / "json-schema"
_RCP_SCHEMA = Draft202012Validator(json.loads(
    (STANDARD / "contracts" / "recompute-report.schema.json").read_text(encoding="utf-8")))


def _rcp_errors(r: dict) -> list:
    return [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
            for e in _RCP_SCHEMA.iter_errors(r)]


# --------------------------------------------------------------------------- #
# Fixtures                                                                     #
# --------------------------------------------------------------------------- #
def _make_project(tmp_path) -> Path:
    facts = tmp_path / "registry" / "facts"
    (facts / "characters").mkdir(parents=True)
    (facts / "timelines").mkdir(parents=True)
    (facts / "events").mkdir(parents=True)
    (facts / "characters" / "CHR-00001.yaml").write_text(yaml.safe_dump({
        "id": "CHR-00001", "name": "Edric", "status": "active",
        "fact_version": 1, "importance": "central", "aliases": [],
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


def _seed_story_state(project) -> dict:
    """Persist a story-state artifact (pure fold) pinned to current facts."""
    reg = load_registry(project, schema_dir=SCHEMA_DIR)
    art = state_artifact(reg, project_state(reg))
    derived.write_artifact(project_path=project, category="story-state",
                           artifact_id=art["task_id"], artifact=art,
                           serialized=json.dumps(art, ensure_ascii=False, indent=2))
    return art


def _seed_generative_draft(project) -> None:
    """Persist a draft artifact (generative) pinned to CHR-00001@v1."""
    draft = {
        "artifact_format": "1.0", "kind": "prose", "capability": "ChapterDraft",
        "task_id": "TASK-00001", "content_hash": "sha256:deadbeef", "body": "…",
        "provenance": {"derived_from": ["CHR-00001@v1"], "source_version": 1},
    }
    derived.write_artifact(project_path=project, category="drafts",
                           artifact_id="TASK-00001", artifact=draft,
                           serialized=json.dumps(draft, ensure_ascii=False, indent=2))


def _advance_chr(project, cid="CHR-00001") -> None:
    p = project / f"registry/facts/characters/{cid}.yaml"
    rec = yaml.safe_load(p.read_text(encoding="utf-8"))
    rec["fact_version"] = int(rec.get("fact_version", 1)) + 1
    p.write_text(yaml.safe_dump(rec, allow_unicode=True), encoding="utf-8")


# --------------------------------------------------------------------------- #
# The deterministic/generative partition                                       #
# --------------------------------------------------------------------------- #
def test_deterministic_fold_is_rebuilt_generative_is_staged(tmp_path):
    project = _make_project(tmp_path)
    ss = _seed_story_state(project)
    _seed_generative_draft(project)
    _advance_chr(project)  # CHR-00001 v1 -> v2
    reg = load_registry(project, schema_dir=SCHEMA_DIR)

    report = recompute.execute_recompute(reg, project)

    kinds = {i["artifact_id"]: (i["kind"], i["action"]) for i in report["impacted"]}
    assert kinds[ss["task_id"]] == ("deterministic", "rebuilt")
    assert kinds["TASK-00001"] == ("generative", "staged")


def test_rebuilt_fold_is_no_longer_stale(tmp_path):
    project = _make_project(tmp_path)
    ss = _seed_story_state(project)
    _advance_chr(project)
    reg = load_registry(project, schema_dir=SCHEMA_DIR)

    # stale before
    before = [f.artifact_id for f in derived.audit_index(reg, project)]
    assert ss["task_id"] in before

    recompute.execute_recompute(reg, project)

    # fresh after — the rebuild re-pinned it to the current fact versions
    after = [f.artifact_id for f in derived.audit_index(reg, project)]
    assert ss["task_id"] not in after


def test_generative_draft_is_never_re_authored(tmp_path):
    project = _make_project(tmp_path)
    _seed_generative_draft(project)
    _advance_chr(project)
    reg = load_registry(project, schema_dir=SCHEMA_DIR)
    before = (project / "registry/derived/drafts/TASK-00001.json").read_text(encoding="utf-8")

    report = recompute.execute_recompute(reg, project)

    after = (project / "registry/derived/drafts/TASK-00001.json").read_text(encoding="utf-8")
    assert before == after  # the draft file was not touched
    # it stays stale (only a human regenerates it) and carries a regen command
    staged = {s["artifact_id"]: s for s in report["staged"]}
    assert "TASK-00001" in staged
    assert staged["TASK-00001"]["regenerate_with"]
    still_stale = [f.artifact_id for f in derived.audit_index(reg, project)]
    assert "TASK-00001" in still_stale


# --------------------------------------------------------------------------- #
# plan vs apply                                                                #
# --------------------------------------------------------------------------- #
def test_plan_writes_nothing(tmp_path):
    project = _make_project(tmp_path)
    ss = _seed_story_state(project)
    _advance_chr(project)
    reg = load_registry(project, schema_dir=SCHEMA_DIR)
    ss_before = (project / f"registry/derived/story-state/{ss['task_id']}.json").read_text(encoding="utf-8")

    report = recompute.recompute_plan(reg, project)

    # the plan says it WOULD rebuild, but wrote nothing
    assert any(i["action"] == "rebuilt" for i in report["impacted"])
    ss_after = (project / f"registry/derived/story-state/{ss['task_id']}.json").read_text(encoding="utf-8")
    assert ss_before == ss_after
    assert not (project / "registry/derived/recompute-reports").exists()


def test_apply_emits_schema_valid_report(tmp_path):
    project = _make_project(tmp_path)
    _seed_story_state(project)
    _seed_generative_draft(project)
    _advance_chr(project)
    reg = load_registry(project, schema_dir=SCHEMA_DIR)

    report = recompute.execute_recompute(reg, project)

    assert _rcp_errors(report) == []
    assert report["authority"] == "human"
    assert report["gating"] is False
    # persisted as derived
    assert (project / "registry/derived/recompute-reports" / f"{report['id']}.json").exists()


# --------------------------------------------------------------------------- #
# Not a fact-writer                                                            #
# --------------------------------------------------------------------------- #
def test_recompute_never_touches_facts(tmp_path):
    project = _make_project(tmp_path)
    _seed_story_state(project)
    _advance_chr(project)
    reg = load_registry(project, schema_dir=SCHEMA_DIR)
    facts_before = (project / "registry/facts/characters/CHR-00001.yaml").read_text(encoding="utf-8")
    rv_before = (project / "registry/_meta/registry-version").read_text(encoding="utf-8")

    recompute.execute_recompute(reg, project)

    facts_after = (project / "registry/facts/characters/CHR-00001.yaml").read_text(encoding="utf-8")
    rv_after = (project / "registry/_meta/registry-version").read_text(encoding="utf-8")
    assert facts_before == facts_after   # recompute does not write facts
    assert rv_before == rv_after          # nor bump the registry version


# --------------------------------------------------------------------------- #
# Trigger provenance (5.2 -> 5.3 chain) + no-op                                #
# --------------------------------------------------------------------------- #
def test_mint_receipt_trigger_is_recorded(tmp_path):
    project = _make_project(tmp_path)
    _seed_story_state(project)
    _advance_chr(project)
    reg = load_registry(project, schema_dir=SCHEMA_DIR)
    fake_receipt = {"id": "MINT-00001",
                    "minted": [{"entity_id": "CHR-00001",
                                "fact_version": {"before": 1, "after": 2}}]}

    report = recompute.execute_recompute(reg, project, mint_receipt=fake_receipt)

    assert report["trigger"]["kind"] == "mint"
    assert report["trigger"]["mint_receipt_id"] == "MINT-00001"
    assert report["trigger"]["advanced_entities"] == ["CHR-00001@v2"]


def test_nothing_stale_is_a_clean_noop(tmp_path):
    project = _make_project(tmp_path)
    _seed_story_state(project)
    # no fact advanced
    reg = load_registry(project, schema_dir=SCHEMA_DIR)
    report = recompute.execute_recompute(reg, project)
    assert report["impacted"] == []
    assert report["rebuilt"] == []
    assert report["staged"] == []
