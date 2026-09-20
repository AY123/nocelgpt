"""Read-only audit of source; all simulated project mutations use TemporaryDirectory."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent / "ainovel"
sys.path[:0] = [str(ROOT / "AI-Novel-Runtime"), str(ROOT)]

from tests.test_workflow_scheduler import _scaffold, STANDARD, SCHEMA
from tests.test_mint import _make_project, _stage_additive
from runtime.serialize.workflow_scheduler import WorkflowScheduler
from runtime.serialize.loop import ChapterSpec, ChapterRun, SerialResult, run_serial
from runtime.registry_loader import load
from runtime.memory.state import project_state
from runtime.mint.executor import execute_mint
from runtime.outline.analyzer import _detect_genres
from runtime.chapter.state_machine import create_blocked_decision


def chapter(n, ok):
    return ChapterRun(ChapterSpec(n, f"TASK-{n:05d}", f"EVT-{n:05d}", [], "audit"), ok, "done")


def scheduler(p):
    return WorkflowScheduler(project_path=p, standard_root=STANDARD, schema_dir=SCHEMA, out_dir=p / "build")


results = {}
with tempfile.TemporaryDirectory(prefix="ainovel-audit-") as temp:
    root = Path(temp)
    p = root / "scheduler"
    _scaffold(p, n_events=3)
    s = scheduler(p)
    mixed = SerialResult("audit", chapters=[chapter(1, True), chapter(2, False), chapter(3, True)], produced=2, skipped=1)
    s._checkpoint_from_result("RUN-GAP", mixed)
    m = s.store.load("RUN-GAP")
    assert m.cursor == 4 and m.failed_chapters[0]["chapter"] == 2
    results["resume_skips_failed_gap"] = {"completed": m.completed_chapters, "failed": [x["chapter"] for x in m.failed_chapters], "cursor": m.cursor}

    held = SerialResult("audit", chapters=[chapter(1, False)], produced=1, skipped=0)
    s._checkpoint_from_result("RUN-HELD", held)
    m = s.store.load("RUN-HELD")
    assert m.status == "completed" and not m.completed_chapters
    results["blocked_run_marked_completed"] = {"status": m.status, "completed": m.completed_chapters, "failed": [x["chapter"] for x in m.failed_chapters]}

    s._checkpoint_from_result("RUN-HISTORY", SerialResult("audit", chapters=[chapter(1, True)], produced=1))
    s._checkpoint_from_result("RUN-HISTORY", SerialResult("audit", chapters=[chapter(2, True)], produced=1))
    m = s.store.load("RUN-HISTORY")
    assert m.completed_chapters == [2]
    results["resume_replaces_completion_history"] = m.completed_chapters

    s._checkpoint_from_result("RUN-REPLAY", SerialResult("audit", chapters=[chapter(1, True)], produced=1))
    s.prompt_version = "2.0.0"
    with patch.object(importlib.import_module("runtime.serialize.workflow_scheduler"), "run_serial", return_value=SerialResult("audit")) as mock:
        s.resume("RUN-REPLAY")
    assert mock.call_count == 1
    results["completed_resume_reenters_serial_with_changed_input"] = {"calls": mock.call_count, "start_chapter": mock.call_args.kwargs["start_chapter"], "prompt_version": mock.call_args.kwargs["prompt_version"]}

    reg = load(p)
    state = project_state(reg, up_to_event="EVT-99999")
    assert len(state.event_order) == 3
    results["unknown_state_cursor_exposes_all_events"] = {"requested": state.up_to_event, "returned": state.event_order}

    p2 = root / "mint"
    _make_project(p2)
    plan = _stage_additive(p2)
    original_write = Path.write_text
    def fail_version_write(path, *args, **kwargs):
        if path == p2 / "registry/_meta/registry-version":
            raise OSError("simulated disk failure after fact write")
        return original_write(path, *args, **kwargs)
    with patch.object(Path, "write_text", fail_version_write):
        try:
            execute_mint(project_path=p2, plan=plan, accepted=["CAND-00001"], schema_dir=SCHEMA, confirmed=True, actor="audit")
        except OSError:
            pass
        else:
            raise AssertionError("failure injection did not fire")
    reg2 = load(p2)
    receipts = list((p2 / "registry/derived/mint-receipts").glob("*.json"))
    assert reg2.version == 1 and reg2.facts["CHR-00001"]["fact_version"] == 2 and not receipts
    results["mint_partial_commit_after_io_failure"] = {"registry_version": reg2.version, "fact_version": reg2.facts["CHR-00001"]["fact_version"], "receipt_count": len(receipts)}

    p3 = root / "blocked-serial"
    _scaffold(p3, n_events=2)
    with patch("runtime.decision_engine.ProductionDecisionEngine.decide_chapter_state", side_effect=lambda **kw: create_blocked_decision(reason="injected hard failure")):
        serial = run_serial(project_path=p3, standard_root=STANDARD, schema_dir=SCHEMA, out_dir=p3 / "build", max_chapters=2)
    assert len(serial.chapters) == 2 and all(not c.ok for c in serial.chapters)
    results["serial_continues_after_blocked_decision"] = {"produced": serial.produced, "skipped": serial.skipped, "chapter_ok": [c.ok for c in serial.chapters], "event_counts": [c.events_so_far for c in serial.chapters]}

    text = "他重生于仙门，修炼灵气，突破境界，掌握飞剑，踏上渡劫之路。"
    genres = _detect_genres(text)
    assert genres[:2] == ["都市", "都市重生"]
    results["rebirth_fantasy_misclassified_urban"] = {"input": text, "genres": genres}

print(json.dumps(results, ensure_ascii=False, indent=2))
