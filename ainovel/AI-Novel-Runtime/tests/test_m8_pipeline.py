"""test_m8_pipeline.py — M8-01: M7 wired into serial + book-level pipeline projection.

Two things proven here:

1. run_serial now runs the M7 gate on every produced chapter (built≠live fix: the
   gate existed but never ran on the serial path) and folds the result into the
   ChapterRun. A hold/block recommendation enqueues a human review request on the
   supplied ApprovalQueue (ADR-009) WITHOUT gating the serial (ADR-003).

2. project_pipeline folds the draft index + envelope publish_readiness/M7 +
   approval queue + published log into ONE per-chapter stage view. Pure
   projection (ADR-008), advisory, never gates (ADR-003), reads only (ADR-006/009).
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

import sys

from runtime.approval import ApprovalQueue, load_approval_queue
from runtime.serialize import (run_serial, project_pipeline,
                               STAGE_DRAFTED, STAGE_REVIEWED, STAGE_ASSESSED,
                               STAGE_APPROVED, STAGE_PUBLISHED)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_serial as T  # reuse the scaffold + _run helpers


def _scaffold_project(root: Path, **kw):
    return T._scaffold_project(root, **kw)


def _run(root: Path, **kw):
    return T._run(root, **kw)


# --------------------------------------------------------------------------- #
# 1. M7 is LIVE on the serial path                                            #
# --------------------------------------------------------------------------- #
def test_serial_folds_m7_into_every_chapter(tmp_path):
    _scaffold_project(tmp_path, n_events=3)
    result = _run(tmp_path)
    assert result.produced == 3
    # Every produced chapter carries an M7 assessment now (red-line half always
    # runs; deterministic stub prose is clean => recommend/L0).
    for c in result.chapters:
        assert c.m7 is not None
        assert c.m7["recommendation"] in ("recommend", "hold", "block")
        assert c.m7["risk_level"] in ("L0", "L1", "L2", "L3")


def test_serial_never_gates_and_no_queue_means_no_enqueue(tmp_path):
    # Absent an ApprovalQueue, M7 still runs but nothing is enqueued; the serial
    # produces all chapters regardless (ADR-003).
    _scaffold_project(tmp_path, n_events=2)
    result = _run(tmp_path)
    assert result.gating is False
    assert result.produced == 2
    assert all(c.m7_approval_id is None for c in result.chapters)


def test_serial_enqueues_human_review_on_hard_redline(tmp_path):
    # Force a hard red-line by injecting a project ruleset whose pattern matches
    # the deterministic stub body. A hard hit => M7 'block' => a review request is
    # enqueued (ADR-009) but the serial still produces the chapter (ADR-003).
    _scaffold_project(tmp_path, n_events=1)
    from runtime.execution.redline import RedlineRule
    # The deterministic stub body contains the chapter goal text; match a char
    # that is certain to appear in generated prose.
    ruleset = [RedlineRule(rule_id="test-hard", pattern="第", severity="hard",
                           scope="body", action="block", priority=1)]
    queue = ApprovalQueue(project_path=tmp_path)
    result = _run(tmp_path, redline_ruleset=ruleset, approval_queue=queue)

    # The chapter is still produced — the serial never gates.
    assert result.produced == 1
    ch = result.chapters[0]
    assert ch.m7["recommendation"] == "block"
    assert ch.m7["risk_level"] == "L3"
    # ... and a human review request now sits on the queue (ADR-009).
    assert ch.m7_approval_id is not None
    reloaded = load_approval_queue(tmp_path)
    pending = reloaded.list_requests(target_type="publish", action="review_m7_risk")
    assert len(pending) == 1
    assert pending[0].target_id == ch.spec.task_id
    assert pending[0].risk_level == "L3"


# --------------------------------------------------------------------------- #
# 2. Book-level pipeline projection                                           #
# --------------------------------------------------------------------------- #
def _write_draft_envelope(root: Path, task_id: str, *, reviewed=False,
                          publish_rec=None, m7_risk=None):
    """Write a draft envelope + its index entry the way the pipeline persists them.
    Optionally attach qa_review (reviewed), publish_readiness, and an M7 block."""
    rel = f"registry/derived/drafts/{task_id}.json"
    inner = {"artifact_format": "1.0", "kind": "prose", "capability": "ChapterDraft",
             "task_id": task_id, "body": f"{task_id} 正文。",
             "content_hash": f"sha256:{abs(hash(task_id)):064d}"[:71]}
    obj = {"envelope_format": "runtime-draft/1.0", "draft": inner}
    if reviewed:
        obj["qa_review"] = {"reviewer": "judge-v1", "scores": {"voice": 80}}
    if publish_rec is not None:
        obj["publish_readiness"] = {"recommendation": publish_rec}
    # M7 rides the envelope as its OWN sibling (not nested in publish_readiness —
    # the frozen readiness schema forbids it), mirroring how run.py persists it.
    if m7_risk is not None:
        obj["m7"] = {"risk_level": m7_risk, "recommendation": publish_rec}
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return {"id": task_id, "category": "drafts", "path": rel,
            "content_hash": inner["content_hash"]}


def _index(root: Path, entries):
    idx = root / "registry" / "derived"
    idx.mkdir(parents=True, exist_ok=True)
    (idx / "_index.yaml").write_text(
        yaml.safe_dump({"artifacts": entries}, allow_unicode=True), encoding="utf-8")


def test_pipeline_stage_is_highest_reached(tmp_path):
    entries = [
        _write_draft_envelope(tmp_path, "TASK-00001"),                               # drafted
        _write_draft_envelope(tmp_path, "TASK-00002", reviewed=True),                # reviewed
        _write_draft_envelope(tmp_path, "TASK-00003", reviewed=True,
                              publish_rec="recommend", m7_risk="L0"),                # assessed
    ]
    _index(tmp_path, entries)
    report = project_pipeline(tmp_path)
    by = {c["task_id"]: c["stage"] for c in report.chapters}
    assert by["TASK-00001"] == STAGE_DRAFTED
    assert by["TASK-00002"] == STAGE_REVIEWED
    assert by["TASK-00003"] == STAGE_ASSESSED
    assert report.gating is False
    assert report.total == 3


def test_pipeline_flags_blocked_without_lowering_stage(tmp_path):
    entries = [
        _write_draft_envelope(tmp_path, "TASK-00001", reviewed=True,
                              publish_rec="block", m7_risk="L3"),
    ]
    _index(tmp_path, entries)
    report = project_pipeline(tmp_path)
    ch = report.chapters[0]
    # A block does NOT demote the stage — the chapter WAS assessed.
    assert ch["stage"] == STAGE_ASSESSED
    assert ch["blocked"] is True
    assert ch["m7_risk_level"] == "L3"
    assert report.blocked == 1


def test_pipeline_folds_approval_and_published(tmp_path):
    entries = [
        _write_draft_envelope(tmp_path, "TASK-00001", reviewed=True,
                              publish_rec="recommend", m7_risk="L0"),
        _write_draft_envelope(tmp_path, "TASK-00002", reviewed=True,
                              publish_rec="recommend", m7_risk="L0"),
    ]
    _index(tmp_path, entries)

    # An approved M7 review lifts TASK-00001 to 'approved'.
    from runtime.approval import enqueue_m7_request
    from runtime.approval.queue import ApprovalDecision
    queue = ApprovalQueue(project_path=tmp_path)
    enqueue_m7_request(queue, request_id="APR-M7-TASK-00001",
                       chapter_id="TASK-00001", reason="ok", risk_level="L0")
    queue.decide("APR-M7-TASK-00001", decision=ApprovalDecision.APPROVED,
                 decided_by="human")

    # A human published TASK-00002 in the authored log => terminal 'published'.
    log = {"id": "PUBLOG-00001", "kind": "published_log", "version": "1.0",
           "published": [{"task_id": "TASK-00002"}]}

    report = project_pipeline(tmp_path, published_log=log,
                              approval_queue=load_approval_queue(tmp_path))
    by = {c["task_id"]: c["stage"] for c in report.chapters}
    assert by["TASK-00001"] == STAGE_APPROVED
    assert by["TASK-00002"] == STAGE_PUBLISHED


def test_pipeline_deterministic_and_empty_degrades(tmp_path):
    # Empty project: no drafts, everything zero, never gates.
    empty = project_pipeline(tmp_path)
    assert empty.total == 0
    assert empty.gating is False

    _index(tmp_path, [_write_draft_envelope(tmp_path, "TASK-00001", reviewed=True,
                                            publish_rec="recommend", m7_risk="L0")])
    a = project_pipeline(tmp_path).to_dict()
    b = project_pipeline(tmp_path).to_dict()
    assert a == b
