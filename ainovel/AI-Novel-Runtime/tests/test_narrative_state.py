"""test_narrative_state.py — the unified narrative-state projection (M3-B5, ADR-008).

Pins that project_narrative_state folds StoryState + persisted mandate/ir/run
artifacts into ONE read-side projection (conflict phase / payoff debt / reader
questions / emotion curve), is deterministic (same inputs => same hash), never
mutates state, and surfaces live on the dashboard. Advisory, never gates.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from runtime import registry_loader
from runtime.serialize import run_serial
from runtime.narrative import project_narrative_state, narrative_state_artifact
from runtime.dashboard import build_dashboard

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


def _w(p: Path, o: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(o, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _scaffold(root: Path, n_events=4):
    facts = root / "registry" / "facts"
    meta = root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    _w(facts / "timelines" / "TML-00001.yaml", {
        "id": "TML-00001", "name": "主线", "status": "active", "fact_version": 1, "kind": "main"})
    _w(facts / "characters" / "CHR-00001.yaml", {
        "id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1})
    for i in range(1, n_events + 1):
        _w(facts / "events" / f"EVT-{i:05d}.yaml", {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active", "fact_version": 1,
            "timeline": "TML-00001", "sequence_index": i, "participants": ["CHR-00001"],
            "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []), "summary": f"第{i}章"})
    _w(root / "sources" / "novel-brain.yaml", {
        "id": "BRAIN-00001", "kind": "novel_brain", "version": "1.0", "mission": "追到天亮",
        "genre": {"primary": "玄幻", "channel": "男频"}, "target_reader": {"who": "男性"},
        "promise": "三章一高潮", "writing_style": {"voice": "冷峻", "pov": "第三人称"},
        "forbidden_style": ["注水"]})


def _write_outline(root: Path, n, cadence=2):
    out = root / "registry" / "derived" / "outline"
    out.mkdir(parents=True, exist_ok=True)
    outline = {"id": "OUTLINE-00001", "reward_loop": {"cadence_chapters": cadence},
               "first_30_chapters": [
                   {"chapter_no": i, "goal": f"目标{i}", "conflict": "冲突",
                    "escalation": "升级", "reward_if_any": "回报", "end_hook": "钩子"}
                   for i in range(1, n + 1)]}
    (out / "OUTLINE-00001.json").write_text(json.dumps(outline, ensure_ascii=False),
                                            encoding="utf-8")
    return outline


def _run(root, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "b", **kw)


def test_narrative_state_folds_all_sources(tmp_path):
    _scaffold(tmp_path, n_events=4)
    outline = _write_outline(tmp_path, 4)
    # v8 (--mandate) persists narrative-mandate + chapter-ir + chapter-run artifacts.
    _run(tmp_path, prompt_version="8.0.0", outline=outline)

    reg = registry_loader.load(tmp_path)
    ns = project_narrative_state(reg, tmp_path)

    # folded the produced chapters
    assert ns.chapters_folded == 4
    # main conflict phase derived from the escalation ladder (mandates present)
    assert ns.main_conflict["phase"] in {"inciting", "escalation", "reversal", "climax", "aftermath"}
    assert ns.main_conflict["ladder"], "escalation ladder folded from mandates"
    # setup/payoff folded from StoryState with a pressure band
    assert ns.setup_payoff["payoff_pressure"] in {"low", "medium", "high"}
    assert "open_count" in ns.setup_payoff
    # never gates (ADR-003)
    assert ns.gating is False


def test_narrative_state_is_deterministic(tmp_path):
    _scaffold(tmp_path, n_events=3)
    outline = _write_outline(tmp_path, 3)
    _run(tmp_path, prompt_version="8.0.0", outline=outline)

    reg = registry_loader.load(tmp_path)
    a = project_narrative_state(reg, tmp_path)
    b = project_narrative_state(reg, tmp_path)
    assert a.content_hash == b.content_hash
    assert a.to_dict() == b.to_dict()


def test_narrative_state_degrades_with_no_artifacts(tmp_path):
    # facts only, no serial run => a valid, sparse projection (no crash).
    _scaffold(tmp_path, n_events=2)
    reg = registry_loader.load(tmp_path)
    ns = project_narrative_state(reg, tmp_path)
    assert ns.chapters_folded == 0
    assert ns.main_conflict["phase"] == "unknown"
    assert ns.emotional_curve["fatigue_risk"] == "unknown"


def test_narrative_state_artifact_pins_facts(tmp_path):
    _scaffold(tmp_path, n_events=3)
    reg = registry_loader.load(tmp_path)
    ns = project_narrative_state(reg, tmp_path)
    art = narrative_state_artifact(reg, tmp_path, ns)
    assert art["kind"] == "narrative-state"
    assert art["content_hash"] == ns.content_hash
    # every fact is pinned at its version for staleness (ADR-008)
    assert any(p.startswith("EVT-00001@v") for p in art["provenance"]["derived_from"])


def test_dashboard_surfaces_narrative_state(tmp_path):
    _scaffold(tmp_path, n_events=4)
    outline = _write_outline(tmp_path, 4)
    _run(tmp_path, prompt_version="8.0.0", outline=outline)

    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d["gating"] is False
    section = d["narrative_state"]
    assert section is not None
    assert section["gating"] is False
    assert section["chapters_folded"] == 4
    assert "phase" in section["main_conflict"]
    assert "payoff_pressure" in section["setup_payoff"]


def test_dashboard_narrative_state_none_when_empty(tmp_path):
    # a project with meta but no facts and no run => nothing to surface.
    meta = tmp_path / "registry" / "_meta"
    meta.mkdir(parents=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d["narrative_state"] is None
