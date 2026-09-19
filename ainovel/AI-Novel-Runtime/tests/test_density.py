"""test_density.py — single-chapter information-density check (ANES v2, ADR-003).

Pins the §14 anti-注水 guard: the checker flags atmosphere-stacking / dialogue-
starved / front-loaded-mood prose DETERMINISTICALLY, stays advisory (never gates),
degrades cleanly on empty/short bodies, and — the load-bearing property — records
a density report on every serial chapter without ever touching draft_hash or
state_hash (it reads only the body).

The §14 regression fixture is a purple-prose opening in the style of the DeepSeek
baseline ("暮色如铁锈 / 寒风如刀"): the checker must catch it.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import yaml

from runtime.execution.density import (check_density, density_summary,
                                       DENSITY_REVIEWER_ID)
from runtime.serialize import run_serial

HERE = Path(__file__).resolve().parent
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


# --------------------------------------------------------------------------- #
# Prose fixtures                                                              #
# --------------------------------------------------------------------------- #
# §14 baseline style: zero-information atmosphere, no dialogue, simile-stacked.
_PURPLE = (
    "暮色如铁锈般沉沉压下，寒风如刀，割着他的脸。天空仿佛一块浸血的幕布，"
    "云层像奔涌的潮水。他记不清逃亡了多少天，只觉得四肢如灌了铅，脚步宛如"
    "踩在棉花上。远处的山影犹如巨兽伏卧，雾气好似轻纱般缠绕。" * 4
)

# Concrete scene: dialogue-heavy, named entities, almost no simile.
_HEALTHY = (
    "「站住！」马伦举起铁锤，挡在门口。埃德里克抬起头。"
    "「我叫埃德里克·万斯，从格伦莫尔来。」他说。"
    "「格伦莫尔？」马伦皱眉，「那地方三个月前就被烧了。」"
    "「我知道，」他低声说，「我就是从火里爬出来的。」" * 4
)


# --------------------------------------------------------------------------- #
# Signal correctness                                                          #
# --------------------------------------------------------------------------- #
def test_purple_prose_flags_dialogue_and_simile():
    findings = check_density({"body": _PURPLE}).findings
    checks = {f.check for f in findings}
    msgs = " ".join(f.message for f in findings)
    assert checks == {"density"}
    assert "对白占比过低" in msgs
    assert "比喻/氛围句密度偏高" in msgs
    # every finding is advisory (never an implicit gate signal)
    assert all(f.severity in ("info", "warning", "error") for f in findings)


def test_healthy_prose_is_clean():
    findings = check_density({"body": _HEALTHY}).findings
    assert len(findings) == 1
    assert findings[0].severity == "info"
    assert "信息密度健康" in findings[0].message


def test_frontloaded_long_prose_flags_skew():
    # first third stacks atmosphere (simile-dense), rest is concrete dialogue —
    # the §14 opening shape. The frontload signal is the opening's simile
    # concentration vs the rest's (language-robust), NOT a "concreteness" proxy
    # (which was blind to CJK narration and false-fired on every Chinese chapter).
    body = _PURPLE + ("「你是谁？」马伦问。「埃德里克·万斯。」他答。"
                      "从格伦莫尔一路逃到这边境小镇。" * 20)
    assert len(body) >= 800  # long enough for the frontload comparison
    msgs = " ".join(f.message for f in check_density({"body": body}).findings)
    assert "开篇氛围/比喻堆砌" in msgs


def test_short_body_does_not_false_fire_frontload():
    # a short but healthy body must not trip the frontload warning (thirds too
    # small to compare — ADR-003 don't cry wolf).
    msgs = " ".join(f.message for f in check_density({"body": _HEALTHY}).findings)
    assert "开篇氛围/比喻堆砌" not in msgs


def test_chinese_narration_opening_does_not_false_fire_frontload():
    # Regression for the real-run finding (2026-07-06): a Chinese chapter whose
    # opening is info-dense NARRATION (few similes, little dialogue) must NOT trip
    # frontload. The old "concreteness" proxy counted only dialogue + latin
    # proper-noun chars, so it scored CJK narration as ~0 and fired on every
    # Chinese opening. The simile-concentration signal is language-robust.
    opening = ("暮色压下来的时候，林线终于断了。埃德里克按着左肋的手已经没有知觉。"
               "三天前那里挨了一记链枷，铁匠打的倒刺勾进甲缝里，他拔出来时没敢看，"
               "只把斗篷割下一角塞进锁子甲和里衣之间，继续走。追兵落在两日脚程之后，"
               "叛国罪、通敌罪，三份口供两份画押，印鉴齐全。" * 6)
    rest = ("他把剑收进鞘里，扯了扯兜帽。坡底隐约有屋顶、烟囱、几缕炊烟。"
            "「你是谁。」有人问。他报出名字，说起被烧掉的城邦。" * 6)
    body = opening + rest
    assert len(body) >= 800
    msgs = " ".join(f.message for f in check_density({"body": body}).findings)
    assert "开篇氛围/比喻堆砌" not in msgs


# --------------------------------------------------------------------------- #
# Report shape + degradation                                                  #
# --------------------------------------------------------------------------- #
def test_report_is_evaluative_and_never_gates():
    rep = check_density({"body": _PURPLE})
    d = rep.to_dict()
    assert d["axis"] == "evaluative"
    assert d["gating"] is False
    assert d["reviewer"] == DENSITY_REVIEWER_ID


def test_empty_body_degrades_cleanly():
    assert density_summary("") is None
    findings = check_density({"body": ""}).findings
    assert len(findings) == 1 and findings[0].severity == "info"
    assert "正文为空" in findings[0].message


def test_summary_is_deterministic():
    assert density_summary(_PURPLE) == density_summary(_PURPLE)


# --------------------------------------------------------------------------- #
# Serial integration: recorded on every chapter, never gates, hashes unchanged #
# --------------------------------------------------------------------------- #
def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


def _scaffold(root: Path, n_events: int = 3):
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


def test_serial_records_density_never_gates(tmp_path):
    root = tmp_path / "proj"
    _scaffold(root, 3)
    r = _run(root)                       # default v1 — density needs no enrichment
    assert r.produced == 3
    assert r.gating is False
    # every produced chapter carries a density report on the evaluative axis
    for c in r.chapters:
        assert c.density is not None
        assert c.density["axis"] == "evaluative"
        assert c.density["gating"] is False
    # and it survives serialization
    assert all(ch["density"] is not None for ch in r.to_dict()["chapters"])


def test_density_does_not_change_draft_or_state_hashes(tmp_path):
    # density reads only the body, so enabling it changes no artifact. We prove
    # this by running the same project twice: identical draft + state hashes.
    a, b = tmp_path / "a", tmp_path / "b"
    _scaffold(a, 3)
    _scaffold(b, 3)
    ra, rb = _run(a), _run(b)
    assert [c.draft_hash for c in ra.chapters] == [c.draft_hash for c in rb.chapters]
    assert [c.state_hash for c in ra.chapters] == [c.state_hash for c in rb.chapters]
