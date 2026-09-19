from __future__ import annotations

import json

from runtime.candidates import plan as planmod
from runtime import derived


def test_default_draft_prefers_latest_derived_draft(tmp_path):
    draft = {
        "task_id": "TASK-12345",
        "content_hash": "sha256:abc",
        "body": "hello world",
        "provenance": {"derived_from": []},
    }
    rel = derived.write_artifact(
        project_path=tmp_path,
        category="drafts",
        artifact_id="TASK-12345",
        artifact=draft,
        serialized=json.dumps(draft, ensure_ascii=False, sort_keys=True, indent=2),
    )
    got = planmod._default_draft(tmp_path)
    assert got["task_id"] == "TASK-12345"
    assert (tmp_path / rel).exists()


def test_load_draft_from_index_by_id(tmp_path):
    draft = {
        "task_id": "TASK-88888",
        "content_hash": "sha256:def",
        "body": "goodbye world",
        "provenance": {"derived_from": []},
    }
    rel = derived.write_artifact(
        project_path=tmp_path,
        category="drafts",
        artifact_id="TASK-88888",
        artifact=draft,
        serialized=json.dumps(draft, ensure_ascii=False, sort_keys=True, indent=2),
    )
    got = planmod._load_draft_from_index(tmp_path, "TASK-88888")
    assert got["task_id"] == "TASK-88888"
    assert (tmp_path / rel).exists()


def test_unwrap_envelope_exposes_inner_body():
    # a persisted draft is an ENVELOPE {draft:{body}, director, qa_review, ...};
    # the extractor reads draft.get('body'), so the loader must unwrap to the
    # inner draft or the W12 --chapter-draft-id path yields 0 candidates
    # (the built≠live gap the real DeepSeek run exposed).
    envelope = {
        "draft": {"body": "章节正文", "task_id": "TASK-1", "word_count": 4},
        "director": {"x": 1},
        "qa_review": {"y": 2},
    }
    inner = planmod._unwrap_draft(envelope)
    assert inner.get("body") == "章节正文"
    assert inner.get("task_id") == "TASK-1"


def test_unwrap_flat_payload_passes_through():
    flat = {"body": "扁平正文", "task_id": "TASK-2"}
    assert planmod._unwrap_draft(flat) is flat


def test_load_draft_from_index_unwraps_envelope(tmp_path):
    envelope = {
        "task_id": "TASK-77777",
        "content_hash": "sha256:ghi",
        "draft": {"body": "被包裹的正文", "provenance": {"derived_from": []}},
        "qa_review": {"verdict": None},
    }
    derived.write_artifact(
        project_path=tmp_path,
        category="drafts",
        artifact_id="TASK-77777",
        artifact=envelope,
        serialized=json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2),
    )
    got = planmod._load_draft_from_index(tmp_path, "TASK-77777")
    assert got.get("body") == "被包裹的正文"  # inner body reachable by extractor
