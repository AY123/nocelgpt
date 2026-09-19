"""test_rolling_plan.py — N100-074: rolling 10-chapter plan producer + read side.

Before this the module (build_rolling_plan) had NO producer on the real path and
NO reader — a built≠live gap. These tests cover:
  1. build_rolling_plan is a deterministic, forward-only projection (unit).
  2. run_serial writes a rolling plan at each checkpoint (producer, live path).
  3. load_rolling_plan(s) reads them back (reader, was write-only).
  4. reader degrades to None/[] when a project never ran.
"""
import json
from pathlib import Path

from runtime import derived
from runtime.long_arc.plan import build_long_arc_plan
from runtime.serialize import (run_serial, build_rolling_plan,
                               load_rolling_plan, load_rolling_plans,
                               ROLLING_PLAN_CATEGORY, CHECKPOINT_INDICES)

_FIXTURE_OUTLINE = (Path(__file__).resolve().parent / "fixtures" / "live-baseline-5ch"
                    / "registry" / "derived" / "outline" / "OUTLINE-00001.json")


def _outline() -> dict:
    return json.loads(_FIXTURE_OUTLINE.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 1. build_rolling_plan — deterministic, forward-only projection              #
# --------------------------------------------------------------------------- #
def test_build_rolling_plan_is_deterministic():
    la = build_long_arc_plan(_outline()).to_dict()
    a = build_rolling_plan(la, checkpoint="cp-010", current_chapter=10)
    b = build_rolling_plan(la, checkpoint="cp-010", current_chapter=10)
    assert a == b
    assert a["content_hash"] == b["content_hash"]


def test_rolling_plan_is_forward_only():
    la = build_long_arc_plan(_outline()).to_dict()
    plan = build_rolling_plan(la, checkpoint="cp-010", current_chapter=10)
    # never plans a completed chapter: every goal is after current_chapter
    for g in plan["active_goals"] + plan["preview_goals"]:
        assert g["chapter_no"] > 10


# --------------------------------------------------------------------------- #
# 2+3. producer (run_serial writes) + reader (loads back)                     #
# --------------------------------------------------------------------------- #
def _run_30_with_outline(tmp_path, monkeypatch):
    from runtime import registry_loader

    class _FakeReg:
        version = "v1"
        facts = {}
        def get(self, _eid):
            return None

    specs = [type("Spec", (), {"index": i, "task_id": f"TASK-{i:05d}",
                               "event_id": f"EVT-{i:05d}",
                               "seeds": ["CHR-00001"], "goal": f"g{i}"})()
             for i in range(1, 31)]

    monkeypatch.setattr(registry_loader, "load", lambda _p: _FakeReg())
    monkeypatch.setattr("runtime.serialize.loop.plan_chapters", lambda _reg: specs)
    pkg = lambda **kw: type("B", (), {"ok": True, "message": "ok", "stage": "ok",
        "package": {"provenance": {"derived_from": ["CHR-00001@v1"], "source_version": "v1"}}})()
    monkeypatch.setattr("runtime.pipeline.build_task_package", pkg)
    monkeypatch.setattr("runtime.serialize.loop.build_task_package", pkg)
    monkeypatch.setattr("runtime.serialize.loop.execute_package", lambda **kw: type("E", (), {
        "ok": True, "stage": "ok", "message": "ok",
        "artifact_path": "registry/derived/drafts/TASK-00001.json",
        "artifact": {
            "task_id": kw["package"]["provenance"]["derived_from"][0].split("@", 1)[0],
            "content_hash": "hash-draft", "body": "真实章节正文",
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
        prompt_version="1.0.0", max_chapters=30, outline=_outline(),
    )


def test_producer_writes_rolling_plan_at_each_checkpoint(tmp_path, monkeypatch):
    _run_30_with_outline(tmp_path, monkeypatch)
    rp_dir = tmp_path / "registry" / "derived" / ROLLING_PLAN_CATEGORY
    for idx in (index for index in CHECKPOINT_INDICES if index <= 30):
        assert (rp_dir / f"rolling-{idx:03d}.json").exists()


def test_reader_reads_rolling_plans_back(tmp_path, monkeypatch):
    _run_30_with_outline(tmp_path, monkeypatch)
    plans = load_rolling_plans(tmp_path)
    assert [p["current_chapter"] for p in plans] == [10, 20, 30]
    for p in plans:
        assert p["kind"] == "rolling_10_chapter_plan"
        # forward-only: no completed chapter appears in the plan
        for g in p["active_goals"] + p["preview_goals"]:
            assert g["chapter_no"] > p["current_chapter"]

    single = load_rolling_plan(tmp_path, 20)
    assert single is not None and single["current_chapter"] == 20


# --------------------------------------------------------------------------- #
# 4. reader degrades when the project never ran                               #
# --------------------------------------------------------------------------- #
def test_reader_degrades_when_no_run(tmp_path):
    assert load_rolling_plans(tmp_path) == []
    assert load_rolling_plan(tmp_path, 10) is None
