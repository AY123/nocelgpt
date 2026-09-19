from __future__ import annotations

import json

import yaml

from runtime.approval import load_approval_queue
from runtime.publishing import sync_publish_requests


def _draft_envelope(task_id, *, publish=None, qa=None, content_hash="sha256:x", body="正文", references=None):
    env = {"artifact_format": "anes.v2", "kind": "prose", "capability": "ChapterDraft",
           "task_id": task_id, "content_hash": content_hash, "body": body}
    if publish is not None:
        env["publish_readiness"] = publish
    if qa is not None:
        env["qa_review"] = qa
    if references is not None:
        env["references"] = references
    return env


def _scaffold_project(tmp_path, chapters):
    drafts_dir = tmp_path / "registry" / "derived" / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for task_id, env in chapters:
        rel = f"registry/derived/drafts/{task_id}.json"
        (tmp_path / rel).write_text(json.dumps(env, ensure_ascii=False), encoding="utf-8")
        artifacts.append({"id": task_id, "category": "drafts", "path": rel})
    index = {"artifacts": artifacts}
    meta = tmp_path / "registry" / "derived"
    (meta / "_index.json").write_text(json.dumps(index), encoding="utf-8")
    (meta / "_index.yaml").write_text(yaml.safe_dump(index, allow_unicode=True),
                                      encoding="utf-8")
    return tmp_path


_RECOMMEND = {"recommendation": "recommend", "basis": {"redline": {"passed": True}}}
_HOLD = {"recommendation": "hold", "basis": {"redline": {"passed": True}}}
_BLOCK = {"recommendation": "block", "basis": {"redline": {"passed": False}}}


def test_publish_ready_chapter_spawns_a_pending_request(tmp_path):
    _scaffold_project(tmp_path, [("TASK-00001", _draft_envelope("TASK-00001", publish=_RECOMMEND))])
    result = sync_publish_requests(tmp_path)
    assert result["created"] == ["APR-PUB-TASK-00001"]

    queue = load_approval_queue(tmp_path)
    pending = queue.list_pending()
    assert len(pending) == 1
    req = pending[0]
    assert req.target_type == "publish"
    assert req.target_id == "TASK-00001"
    assert req.context["recommendation"] == "recommend"


def test_hold_block_and_unknown_do_not_spawn(tmp_path):
    _scaffold_project(tmp_path, [
        ("TASK-00001", _draft_envelope("TASK-00001", publish=_HOLD)),
        ("TASK-00002", _draft_envelope("TASK-00002", publish=_BLOCK)),
        ("TASK-00003", _draft_envelope("TASK-00003")),  # no publish_readiness -> unknown
    ])
    result = sync_publish_requests(tmp_path)
    assert result["created"] == []
    assert sorted(result["skipped_not_ready"]) == ["TASK-00001", "TASK-00002", "TASK-00003"]
    assert load_approval_queue(tmp_path).list_pending() == []


def test_m7_risk_metadata_is_carried_into_publish_request(tmp_path):
    body = "少年推开门，雨夜里追查真相，妹妹被卷入家族争斗。"
    _scaffold_project(tmp_path, [
        ("TASK-00001", _draft_envelope("TASK-00001", body=body, references=[{
            "source_id": "REF-1",
            "source_type": "reference_novel",
            "text": body,
        }], publish=None)),
    ])
    result = sync_publish_requests(tmp_path)
    assert result["created"] == []
    assert load_approval_queue(tmp_path).list_pending() == []


def test_sync_is_idempotent(tmp_path):
    _scaffold_project(tmp_path, [("TASK-00001", _draft_envelope("TASK-00001", publish=_RECOMMEND))])
    first = sync_publish_requests(tmp_path)
    assert first["created"] == ["APR-PUB-TASK-00001"]

    second = sync_publish_requests(tmp_path)
    assert second["created"] == []
    assert second["skipped_existing"] == ["TASK-00001"]
    # exactly one request on disk, not two
    assert len(load_approval_queue(tmp_path).requests) == 1


def test_already_published_chapter_is_skipped(tmp_path):
    _scaffold_project(tmp_path, [("TASK-00001", _draft_envelope("TASK-00001", publish=_RECOMMEND))])
    published_log = {"published": [{"task_id": "TASK-00001"}]}
    result = sync_publish_requests(tmp_path, published_log=published_log)
    assert result["created"] == []
    assert result["published"] == ["TASK-00001"]
    assert load_approval_queue(tmp_path).list_pending() == []


def test_mixed_project_spawns_only_ready_unpublished(tmp_path):
    _scaffold_project(tmp_path, [
        ("TASK-00001", _draft_envelope("TASK-00001", publish=_RECOMMEND)),  # spawns
        ("TASK-00002", _draft_envelope("TASK-00002", publish=_RECOMMEND)),  # published -> skip
        ("TASK-00003", _draft_envelope("TASK-00003", publish=_HOLD)),       # not ready -> skip
    ])
    published_log = {"published": [{"task_id": "TASK-00002"}]}
    result = sync_publish_requests(tmp_path, published_log=published_log)
    assert result["created"] == ["APR-PUB-TASK-00001"]
    assert result["published"] == ["TASK-00002"]
    assert result["skipped_not_ready"] == ["TASK-00003"]


def test_card_uses_m7_when_publish_readiness_missing(tmp_path):
    body = "少年推开门，雨夜里追查真相，妹妹被卷入家族争斗。"
    _scaffold_project(tmp_path, [
        ("TASK-00001", _draft_envelope("TASK-00001", body=body, references=[{
            "source_id": "REF-1",
            "source_type": "reference_novel",
            "text": body,
        }], publish=None)),
    ])
    result = sync_publish_requests(tmp_path)
    assert result["created"] == []
    assert result["skipped_not_ready"] == ["TASK-00001"]
    assert load_approval_queue(tmp_path).list_pending() == []
