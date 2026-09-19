"""test_inventory.py — the serial production funnel projection (roadmap P19).

Proves the inventory is a PROJECTION folded from products that already exist:
drafted from the draft index, reviewed from the envelope's qa_review, published
ONLY from the authored published log (ADR-009 — never inferred), ready =
produced - published. Advisory, never gates (ADR-003). Degrades when no log.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from runtime.inventory import (project_inventory, load_published_log,
                               validate_published_log)

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
PUBLOG_SCHEMA = json.loads(
    (STANDARD / "contracts" / "published-log.schema.json").read_text(encoding="utf-8"))


def _write_draft(root: Path, i: int, *, reviewed: bool):
    """Write a draft file (optionally with a qa_review envelope) and its index
    entry, mirroring how the pipeline persists drafts."""
    task_id = f"TASK-{i:05d}"
    rel = f"registry/derived/drafts/{task_id}.json"
    inner = {"artifact_format": "1.0", "kind": "prose", "capability": "ChapterDraft",
             "task_id": task_id, "body": f"第{i}章正文。",
             "content_hash": f"sha256:{i:064d}"}
    if reviewed:
        obj = {"envelope_format": "runtime-draft/1.0", "draft": inner,
               "qa_review": {"reviewer": "judge-v1", "scores": {"voice": 80}}}
    else:
        obj = {"envelope_format": "runtime-draft/1.0", "draft": inner,
               "qa_review": None}
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return {"id": task_id, "category": "drafts", "path": rel,
            "content_hash": inner["content_hash"]}


def _scaffold(root: Path, *, n_drafts: int, n_reviewed: int):
    """n_drafts total; the first n_reviewed carry a qa_review."""
    entries = [_write_draft(root, i, reviewed=(i <= n_reviewed))
               for i in range(1, n_drafts + 1)]
    idx = root / "registry" / "derived"
    idx.mkdir(parents=True, exist_ok=True)
    (idx / "_index.yaml").write_text(
        yaml.safe_dump({"artifacts": entries}, allow_unicode=True), encoding="utf-8")


def _write_log(root: Path, task_ids):
    log = {"id": "PUBLOG-00001", "kind": "published_log", "version": "1.0",
           "published": [{"task_id": t} for t in task_ids]}
    (root / "sources").mkdir(parents=True, exist_ok=True)
    (root / "sources" / "published-log.yaml").write_text(
        yaml.safe_dump(log, allow_unicode=True), encoding="utf-8")
    return log


# --------------------------------------------------------------------------- #
# The funnel folds drafted / reviewed / published from real products          #
# --------------------------------------------------------------------------- #
def test_drafted_and_reviewed_from_index_and_envelope(tmp_path):
    _scaffold(tmp_path, n_drafts=5, n_reviewed=3)
    r = project_inventory(tmp_path)
    assert r.drafted == 5
    assert r.reviewed == 3
    assert r.gating is False


def test_published_only_from_authored_log(tmp_path):
    _scaffold(tmp_path, n_drafts=5, n_reviewed=3)
    log = _write_log(tmp_path, ["TASK-00001", "TASK-00002"])
    r = project_inventory(tmp_path, published_log=log)
    assert r.published == 2
    # ready = produced - published
    assert r.ready == 3


def test_published_never_inferred_without_log(tmp_path):
    # 5 drafts, all reviewed, but NO published log -> published must be 0.
    # Publishing is a human-authorized transition (ADR-009); the system must not
    # infer it from a draft merely existing or having passed review.
    _scaffold(tmp_path, n_drafts=5, n_reviewed=5)
    r = project_inventory(tmp_path, published_log=None)
    assert r.published == 0
    assert r.ready == 5


def test_per_chapter_status_is_highest_stage(tmp_path):
    _scaffold(tmp_path, n_drafts=3, n_reviewed=2)
    log = _write_log(tmp_path, ["TASK-00001"])
    r = project_inventory(tmp_path, published_log=log)
    by_id = {c["task_id"]: c["status"] for c in r.chapters}
    assert by_id["TASK-00001"] == "published"   # published outranks reviewed
    assert by_id["TASK-00002"] == "reviewed"    # reviewed but not published
    assert by_id["TASK-00003"] == "drafted"     # neither


def test_thin_stock_is_advisory(tmp_path):
    _scaffold(tmp_path, n_drafts=4, n_reviewed=0)
    log = _write_log(tmp_path, ["TASK-00001", "TASK-00002"])
    r = project_inventory(tmp_path, published_log=log, ready_target=10)
    assert r.ready == 2
    assert r.thin_stock is True     # 2 < 10
    assert r.gating is False        # but it never gates


def test_deterministic(tmp_path):
    _scaffold(tmp_path, n_drafts=5, n_reviewed=3)
    log = _write_log(tmp_path, ["TASK-00001"])
    a = project_inventory(tmp_path, published_log=log).to_dict()
    b = project_inventory(tmp_path, published_log=log).to_dict()
    assert a == b


def test_empty_project_degrades(tmp_path):
    r = project_inventory(tmp_path, published_log=None)
    assert r.drafted == r.reviewed == r.published == r.ready == 0
    assert r.gating is False


# --------------------------------------------------------------------------- #
# Authored published log: loader + contract                                   #
# --------------------------------------------------------------------------- #
def test_load_published_log_absence_is_not_an_error(tmp_path):
    assert load_published_log(tmp_path) is None


def test_authored_log_validates_against_contract(tmp_path):
    log = _write_log(tmp_path, ["TASK-00001", "TASK-00002"])
    Draft202012Validator(PUBLOG_SCHEMA).validate(log)
    assert validate_published_log(log, standard_root=STANDARD) == []


def test_loaded_log_drives_published_count(tmp_path):
    _scaffold(tmp_path, n_drafts=3, n_reviewed=0)
    _write_log(tmp_path, ["TASK-00001", "TASK-00003"])
    log = load_published_log(tmp_path)
    r = project_inventory(tmp_path, published_log=log)
    assert r.published == 2
    assert r.ready == 1
