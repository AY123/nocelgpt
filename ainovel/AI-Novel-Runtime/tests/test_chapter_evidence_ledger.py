from pathlib import Path

from runtime.serialize.chapter_evidence_ledger import build_chapter_evidence_ledger, write_chapter_evidence_ledger


RUN_MANIFEST = {
    "id": "RUN-00025",
    "kind": "production_run_manifest",
    "version": "1.0",
    "gating": False,
    "chapters": [
        {
            "index": 1,
            "task_id": "CH-001",
            "event": "EV-001",
            "ok": True,
            "stage": "done",
            "message": "ok",
            "draft_hash": "sha256:draft1",
            "state_hash": "sha256:state1",
            "verdict": "pass",
            "commercial_verdict": "ok",
            "chapter_final": {"final_hash": "sha256:final1", "final_review": {"scores": {"quality": 9}, "overall_verdict": "pass"}},
            "publish_readiness": {"recommendation": "publish"},
            "llm": {"provider": "stub", "model": "stub", "token_usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}, "cost": {"currency": "USD", "total_cost": 0.01}},
        }
    ],
    "totals": {"planned": 1, "produced": 1, "skipped": 0, "live_calls": 1, "final_state_hash": "sha256:state1", "token_usage": {"input": 1, "output": 2, "total": 3}, "cost": {"currency": "USD", "total_cost": 0.01}},
}


def test_build_chapter_evidence_ledger():
    ledger = build_chapter_evidence_ledger(project_path="/tmp/project", run_manifest=RUN_MANIFEST, protocol={"protocol_id": "P-1", "content_hash": "sha256:abc"})
    assert ledger["kind"] == "chapter_evidence_ledger"
    assert ledger["chapter_count"] == 1
    assert ledger["chapters"][0]["chapter_index"] == 1
    assert ledger["chapters"][0]["checkpoint"]["present"] is False
    assert ledger["content_hash"].startswith("sha256:")


def test_write_chapter_evidence_ledger(tmp_path):
    ledger = build_chapter_evidence_ledger(project_path=tmp_path, run_manifest=RUN_MANIFEST)
    out = write_chapter_evidence_ledger(tmp_path / "chapter-evidence.json", ledger)
    assert out.exists()
