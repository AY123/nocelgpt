"""test_hook_check.py — single-chapter end-hook detection (ANES v2, §14 finding-3, ADR-003).

Pins the guard that verifies the chapter END leaves a 追读 hook instead of trusting
the model to: it flags a settling/emotional close with no hook (the §14 tell),
cross-checks an objective's declared cliffhanger_type against delivery, stays
advisory (never gates), is bilingual, degrades on empty/short bodies, and records
an end_hook report on every serial chapter without touching draft_hash/state_hash.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from runtime.execution.hook_check import (check_end_hook, hook_summary,
                                          HOOK_REVIEWER_ID)
from runtime.serialize import run_serial

HERE = Path(__file__).resolve().parent
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"

# Neutral padding so the body clears MIN_BODY_CHARS and the ending window is real.
_PAD = ("马伦把粥端到床边，炉火噼啪响着。埃德里克靠在墙上，慢慢喝完那碗粥。"
        "窗外的雨还在下，夜色深沉。他闭目养神，听着锤声。" * 4)


def _art(ending: str) -> dict:
    return {"task_id": "T", "body": _PAD + ending}


# --------------------------------------------------------------------------- #
# Signal correctness — the four ending shapes                                 #
# --------------------------------------------------------------------------- #
def test_question_ending_is_a_hook():
    s = hook_summary(_PAD + "可他真的能信任这个陌生女人吗？")
    assert s["has_question"] and not s["has_closure"]
    rep = check_end_hook(_art("可他真的能信任这个陌生女人吗？"))
    assert rep.findings[0].severity == "info"
    assert "钩子" in rep.findings[0].message


def test_suspension_ending_is_a_hook():
    s = hook_summary(_PAD + "门外传来一阵沉重的脚步声——")
    assert s["has_suspension"]
    assert check_end_hook(_art("门外传来一阵沉重的脚步声——")).findings[0].severity == "info"


def test_turn_ending_is_a_hook():
    s = hook_summary(_PAD + "就在这时，身后忽然响起一个陌生的声音。")
    assert s["has_turn"]
    assert check_end_hook(_art("就在这时，身后忽然响起一个陌生的声音。")).findings[0].severity == "info"


def test_emotional_close_with_no_hook_is_flagged():
    # the §14 tell: "closed on emotion", no pull.
    body = _PAD + "他终于松了口气，沉沉睡去，一切都会好起来的。"
    s = hook_summary(body)
    assert s["has_closure"] and not (s["has_question"] or s["has_suspension"] or s["has_turn"])
    rep = check_end_hook({"body": body})
    assert rep.findings[0].severity == "warning"
    assert "缺乏追读钩子" in rep.findings[0].message


def test_english_closure_is_flagged_bilingual():
    body = ("Maren set the bowl down. The fire crackled. He leaned back against "
            "the wall and ate slowly. The rain kept falling outside. " * 4
            + "At last he breathed easy and fell asleep, safe now.")
    assert check_end_hook({"body": body}).findings[0].severity == "warning"


# --------------------------------------------------------------------------- #
# Objective cross-check                                                       #
# --------------------------------------------------------------------------- #
def test_declared_hook_not_delivered_is_flagged():
    # a neutral (non-closing) ending that delivers no hook, but the objective
    # declared one → declared-vs-delivered mismatch warning.
    body = _PAD + "他放下碗，望着窗外，心里想着明天该往哪里走。"
    s = hook_summary(body)
    assert not (s["has_question"] or s["has_suspension"] or s["has_turn"])
    assert not s["has_closure"]           # neutral, not a settling close
    rep = check_end_hook({"body": body}, objective={"cliffhanger_type": "threat"})
    assert rep.findings[0].severity == "warning"
    assert "声明" in rep.findings[0].message


def test_cliffhanger_none_does_not_force_a_hook():
    # objective explicitly wants no cliffhanger → a neutral ending is fine.
    body = _PAD + "他放下碗，望着窗外，心里想着明天该往哪里走。"
    rep = check_end_hook({"body": body}, objective={"cliffhanger_type": "none"})
    assert rep.findings[0].severity == "info"


# --------------------------------------------------------------------------- #
# Report shape + degradation                                                  #
# --------------------------------------------------------------------------- #
def test_report_is_evaluative_and_never_gates():
    d = check_end_hook(_art("门外传来脚步声——")).to_dict()
    assert d["axis"] == "evaluative" and d["gating"] is False
    assert d["reviewer"] == HOOK_REVIEWER_ID


def test_empty_and_short_bodies_degrade_cleanly():
    assert hook_summary("") is None
    assert check_end_hook({"body": ""}).findings[0].severity == "info"
    short = check_end_hook({"body": "太短了。"}).findings[0]
    assert short.severity == "info" and "过短" in short.message


def test_summary_is_deterministic():
    b = _PAD + "他真的能信任她吗？"
    assert hook_summary(b) == hook_summary(b)


# --------------------------------------------------------------------------- #
# Serial integration                                                          #
# --------------------------------------------------------------------------- #
def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


def _scaffold(root: Path, n_events: int = 2):
    facts, meta = root / "registry" / "facts", root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    _write(facts / "timelines" / "TML-00001.yaml", {
        "id": "TML-00001", "name": "主线", "status": "active",
        "fact_version": 1, "kind": "main"})
    _write(facts / "characters" / "CHR-00001.yaml", {
        "id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1})
    for i in range(1, n_events + 1):
        _write(facts / "events" / f"EVT-{i:05d}.yaml", {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active",
            "fact_version": 1, "timeline": "TML-00001", "sequence_index": i,
            "participants": ["CHR-00001"],
            "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []),
            "effects": ([f"EVT-{i+1:05d}"] if i < n_events else []),
            "summary": f"第{i}章"})


def _run(root, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "build-serial", **kw)


def test_serial_records_end_hook_never_gates(tmp_path):
    root = tmp_path / "proj"
    _scaffold(root, 2)
    r = _run(root)
    assert r.produced == 2 and r.gating is False
    for c in r.chapters:
        assert c.end_hook is not None
        assert c.end_hook["axis"] == "evaluative" and c.end_hook["gating"] is False
    assert all(ch["end_hook"] is not None for ch in r.to_dict()["chapters"])


def test_end_hook_does_not_change_hashes(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _scaffold(a, 2)
    _scaffold(b, 2)
    ra, rb = _run(a), _run(b)
    assert [c.draft_hash for c in ra.chapters] == [c.draft_hash for c in rb.chapters]
    assert [c.state_hash for c in ra.chapters] == [c.state_hash for c in rb.chapters]
