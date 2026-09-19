"""test_humanization.py — single-chapter AI-tell detection (ANES v2, ADR-003).

Pins the §14 anti-AI-味 guard: the detector flags anaphora stacking / em-dash
asides / monotone sentence rhythm DETERMINISTICALLY, stays advisory (never
gates), is bilingual (CJK + English), degrades cleanly on empty/short bodies, and
— the load-bearing property — records an ai_taste report on every serial chapter
without ever touching draft_hash or state_hash (it reads only the body).

The §14 regression fixture is a parallel-structure opening in the style of the
DeepSeek baseline ("He had not eaten... He had not slept..."): it must be caught.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from runtime.execution.humanization import (check_ai_taste, ai_taste_summary,
                                            locate_anaphora_run,
                                            AI_TASTE_REVIEWER_ID)
from runtime.serialize import run_serial

HERE = Path(__file__).resolve().parent
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


# --------------------------------------------------------------------------- #
# Prose fixtures                                                              #
# --------------------------------------------------------------------------- #
# §14 baseline style: same-opening parallel sentences + an em-dash aside.
_ANAPHORA_EN = (
    "He had not eaten in four days. He had not slept in five. "
    "He had ridden his horse until it foundered. He had walked until his boots "
    "wore through. The rain was falling. The wind was rising. The night was "
    "closing in around him."
)

_DASH_HEAVY = (
    "他抬起头——那双眼睛琥珀色的——看着她。"
    "她递过水——一碗温的井水——放在床边。"
    "男人沉默了——那种计算的沉默——很久。"
    "炉火噼啪响着——像某种心跳——在雨夜里。"
    "她没有说话——什么也没有——只是等着。"
)

# Natural human rhythm: varied openings, varied lengths, no dash asides.
_HEALTHY = (
    "马伦扔下废铁，跑了过去。那是个比她高出一头的男人，脸色白得像褪了血，"
    "斗篷底下露出一截磨损的皮甲。「喂，」她拍他的脸，「别在这儿睡，夜里能冻死牛。」"
    "男人的嘴唇动了动，吐出一句几乎听不清的、带着外乡口音的话。随后他就昏了过去。"
    "她愣了一下，到底还是蹲下身，把他的手臂架到肩上。"
)


# --------------------------------------------------------------------------- #
# Signal correctness                                                          #
# --------------------------------------------------------------------------- #
def test_anaphora_stacking_is_flagged():
    findings = check_ai_taste({"body": _ANAPHORA_EN}).findings
    msgs = " ".join(f.message for f in findings)
    assert "同头排比" in msgs
    s = ai_taste_summary(_ANAPHORA_EN)
    assert s["anaphora_run"] >= 3


def test_dash_aside_density_is_flagged():
    findings = check_ai_taste({"body": _DASH_HEAVY}).findings
    msgs = " ".join(f.message for f in findings)
    assert "破折号插入语密度偏高" in msgs


def test_healthy_prose_is_clean():
    findings = check_ai_taste({"body": _HEALTHY}).findings
    assert len(findings) == 1
    assert findings[0].severity == "info"
    assert "未见明显 AI 味" in findings[0].message


def test_bilingual_anaphora_cjk():
    # anaphora detection must work in CJK too (first-char head unit: 他…他…他).
    cjk = ("他站起来，走向门口。他停下来，回过头。他看着她，没有说话。"
           "他转过身，推开门。")
    s = ai_taste_summary(cjk)
    assert s["anaphora_run"] >= 3


def test_system_panel_lines_are_not_false_anaphora():
    # Regression (G.8 real-run finding): a run of 系统/金手指 panel lines all begin
    # with 【, so keying on the raw first char counted them as a 5-run of anaphora.
    # They are a UI device, not parallel prose — the bracket must be stripped so
    # each line keys on its real first word and the run does not trip the detector.
    panel = ("【刻痕·主动扫描已启动】\n【目标物成分分析中……】\n"
             "【警告：检测到未知化合物】\n【与数据库匹配度：0%】\n【建议：不要服用】")
    s = ai_taste_summary(panel)
    assert s["anaphora_run"] < 3
    findings = check_ai_taste({"body": panel}).findings
    assert not any("同头排比" in f.message for f in findings)


def test_locate_anaphora_run_returns_the_offending_sentences():
    # The LOCATION behind the count: the actual sentences forming the longest run.
    body = ("他站起来，走向门口。他停下来，回过头。他看着她，没有说话。"
            "外面的风停了。")
    run = locate_anaphora_run(body)
    assert len(run) >= 3
    assert all(s.startswith("他") for s in run)
    # the located run is exactly what the counter counted (no drift)
    assert ai_taste_summary(body)["anaphora_run"] == len(locate_anaphora_run(body, max_sentences=99))


def test_locate_anaphora_run_empty_when_no_stacking():
    # A clean body (no 3-run) locates nothing — degrades to the plain message.
    body = "他站起来。她皱眉。风停了。门开了。"
    assert locate_anaphora_run(body) == []


def test_enumeration_ordinals_are_not_false_anaphora():
    # RUN-00001 finding: 第一道/第二道/第三道 (action list) and 第一个/第二个/第三个
    # (info list) are a LIST device, not the monotone subject-drop tell — keying on
    # the bare 第 collided them into a false run. Ordinal-aware keying fixes it.
    enum_dao = "第一道力量撞偏，擦着发顶飞过。第二道被拆散，碎成光线。第三道被他完整吞下。"
    enum_ge = "第一个：大曜士封锁矿道。第二个：审计提前。第三个：荧惑带回口信。"
    assert ai_taste_summary(enum_dao)["anaphora_run"] < 3
    assert ai_taste_summary(enum_ge)["anaphora_run"] < 3
    # a GENUINE same-ordinal repeat (第一…第一…第一) still keys the same => caught
    same = "第一次失败了。第一次的教训。第一次让他明白。"
    assert ai_taste_summary(same)["anaphora_run"] >= 3
    # and real pro-drop anaphora is untouched
    real = "他站起来，走向门口。他停下来，回过头。他看着她，没有说话。"
    assert ai_taste_summary(real)["anaphora_run"] >= 3


def test_fixed_threshold_anaphora_warning_quotes_the_offending_sentences():
    # N100-071: the fixed-threshold path (check_ai_taste, no reference_profile)
    # must ALSO name the exact offending sentences, mirroring the market-anchored
    # path — a count-only instruction let borderline runs survive the rewrite.
    body = ("他站起来，走向门口。他停下来，回过头。他看着她，没有说话。"
            "外面的风停了。")
    findings = check_ai_taste({"body": body}).findings
    ana = [f for f in findings if "同头排比" in f.message]
    assert ana, "anaphora run should be flagged"
    msg = ana[0].message
    assert "具体需改写这几句同头" in msg
    # the quoted sentences are exactly the located run
    for s in locate_anaphora_run(body):
        assert f"「{s}」" in msg


# --------------------------------------------------------------------------- #
# Report shape + degradation                                                  #
# --------------------------------------------------------------------------- #
def test_report_is_evaluative_and_never_gates():
    d = check_ai_taste({"body": _ANAPHORA_EN}).to_dict()
    assert d["axis"] == "evaluative"
    assert d["gating"] is False
    assert d["reviewer"] == AI_TASTE_REVIEWER_ID


def test_empty_body_degrades_cleanly():
    assert ai_taste_summary("") is None
    findings = check_ai_taste({"body": ""}).findings
    assert len(findings) == 1 and findings[0].severity == "info"
    assert "正文为空" in findings[0].message


def test_short_body_does_not_false_fire_cv():
    # a short healthy body has too few sentences for the CV signal — must not warn.
    msgs = " ".join(f.message for f in check_ai_taste({"body": _HEALTHY}).findings)
    assert "句长变异过低" not in msgs


def test_summary_is_deterministic():
    assert ai_taste_summary(_ANAPHORA_EN) == ai_taste_summary(_ANAPHORA_EN)


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


def test_serial_records_ai_taste_never_gates(tmp_path):
    root = tmp_path / "proj"
    _scaffold(root, 3)
    r = _run(root)
    assert r.produced == 3
    assert r.gating is False
    for c in r.chapters:
        assert c.ai_taste is not None
        assert c.ai_taste["axis"] == "evaluative"
        assert c.ai_taste["gating"] is False
    assert all(ch["ai_taste"] is not None for ch in r.to_dict()["chapters"])


def test_ai_taste_does_not_change_draft_or_state_hashes(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _scaffold(a, 3)
    _scaffold(b, 3)
    ra, rb = _run(a), _run(b)
    assert [c.draft_hash for c in ra.chapters] == [c.draft_hash for c in rb.chapters]
    assert [c.state_hash for c in ra.chapters] == [c.state_hash for c in rb.chapters]
