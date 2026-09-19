"""test_w12_serial_wiring.py — W12 fact-reflow is LIVE inside the serial loop.

run_w12_fact_reflow used to be CLI-only (built≠live): the serial production loop
never extracted fact candidates per chapter. These tests lock the wiring:
  - --w12-extract off  → ChapterRun.w12 is None, behavior unchanged (default).
  - --w12-extract on   → each produced chapter carries a w12 summary and a plan +
    approval request is staged (never minted — ADR-009; never gates — ADR-003).
"""
from runtime import registry_loader
from runtime.serialize import run_serial


class _FakeReg:
    def __init__(self):
        self.version = "v1"
        self.facts = {}

    def get(self, _eid):
        return None

    def all_ids(self):
        return []


def _drive(tmp_path, monkeypatch, *, n=3, w12_extract=False):
    specs = [type("Spec", (), {"index": i, "task_id": f"TASK-{i:05d}",
                               "event_id": f"EVT-{i:05d}",
                               "seeds": ["CHR-00001"], "goal": f"g{i}"})()
             for i in range(1, n + 1)]

    monkeypatch.setattr(registry_loader, "load", lambda _p: _FakeReg())
    # plan.py binds `from ..registry_loader import load as load_registry` at its own
    # import, so patch that name where it's USED (robust regardless of whether plan
    # was already imported by an earlier test). In production run_serial always has
    # a real registry; this only stands in for the tmp project's missing one.
    monkeypatch.setattr("runtime.candidates.plan.load_registry", lambda _p: _FakeReg())
    monkeypatch.setattr("runtime.serialize.loop.plan_chapters", lambda _reg: specs)
    pkg = lambda **kw: type("B", (), {"ok": True, "message": "ok", "stage": "ok",
        "package": {"provenance": {"derived_from": ["CHR-00001@v1"], "source_version": "v1"}}})()
    monkeypatch.setattr("runtime.pipeline.build_task_package", pkg)
    monkeypatch.setattr("runtime.serialize.loop.build_task_package", pkg)
    monkeypatch.setattr("runtime.serialize.loop.execute_package", lambda **kw: type("E", (), {
        "ok": True, "stage": "ok", "message": "ok",
        "artifact_path": "registry/derived/drafts/TASK.json",
        "artifact": {
            "task_id": kw["package"]["provenance"]["derived_from"][0].split("@", 1)[0],
            "content_hash": "hash-draft", "body": "周洛铭握紧了断裂的长剑，血珠顺着刃口滑落。",
            "provenance": {"derived_from": ["CHR-00001@v1"], "source_version": "v1"},
            "produced_by": {"llm": {"cost": {"total_cost": 0},
                                    "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}},
        },
        "qa_review": {"scores": {}},
        "envelope": {"artifact": {"task_id": "TASK-00001"}},
    })())

    return run_serial(
        project_path=tmp_path, standard_root=tmp_path, schema_dir=tmp_path,
        out_dir=tmp_path / "out", model=None, reviewer=None,
        prompt_version="1.0.0", max_chapters=n, w12_extract=w12_extract)


def test_w12_off_by_default_leaves_chapterrun_w12_none(tmp_path, monkeypatch):
    result = _drive(tmp_path, monkeypatch, n=3, w12_extract=False)
    assert result.produced == 3
    assert all(c.w12 is None for c in result.chapters)
    # no fact-candidate plans staged
    assert not (tmp_path / "registry" / "derived" / "fact-candidates").exists()


def test_w12_extract_stages_candidates_and_approval_per_chapter(tmp_path, monkeypatch):
    result = _drive(tmp_path, monkeypatch, n=3, w12_extract=True)
    assert result.produced == 3

    for c in result.chapters:
        assert c.w12 is not None
        assert "error" not in c.w12, c.w12
        assert c.w12["plan_id"] == f"W12-{c.spec.task_id}"
        assert c.w12["approval_request_id"] == f"APR-W12-W12-{c.spec.task_id}"
        # deferred, NOT approved/minted — the serial only stages (ADR-009)
        assert c.w12["approval_status"] == "pending"
        assert "reconciled_counts" in c.w12

    # plans + approval requests were actually written to derived/
    fc = tmp_path / "registry" / "derived" / "fact-candidates"
    assert fc.exists()
    assert len(list(fc.glob("*.json"))) == 3


def test_w12_extract_never_gates_the_serial(tmp_path, monkeypatch):
    # even if W12 raises, the serial still produces every chapter (advisory)
    import runtime.candidates.plan as planmod

    def _boom(**kwargs):
        raise RuntimeError("extractor blew up")

    monkeypatch.setattr(planmod, "run_w12_fact_reflow", _boom)
    result = _drive(tmp_path, monkeypatch, n=2, w12_extract=True)
    assert result.produced == 2
    assert result.gating is False
    for c in result.chapters:
        assert c.w12 is not None and "error" in c.w12
