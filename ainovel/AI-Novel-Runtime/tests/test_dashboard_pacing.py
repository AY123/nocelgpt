"""test_dashboard_pacing.py — the dashboard's pacing panorama (P22/P23 view).

The dashboard folds the persisted scene plans back into a pacing readout: it
recomputes per-chapter intra-chapter warnings and the cross-chapter climax
rhythm (against the authored cadence). Pure read-side, advisory, never gates.
None when no scene plans exist.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from runtime.serialize import run_serial
from runtime.dashboard import build_dashboard

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


def _w(p: Path, o: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(o, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _scaffold(root: Path, n_events=3):
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


class _Out:
    def __init__(self, t): self.text = t; self.model_id = "fake"


class _LowModel:
    """Flat, low valence across all scenes -> doldrums + flat-curve warnings."""
    model_id = "fake"
    def generate(self, prompt):
        return _Out(json.dumps({"scenes": [{"index": i, "emotion": {"valence": 45}}
                                           for i in range(1, 6)]}))


def _run(root, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "b", **kw)


def test_pacing_section_surfaces_with_enriched_plans(tmp_path):
    _scaffold(tmp_path, n_events=4)
    outline = _write_outline(tmp_path, 4)
    _run(tmp_path, prompt_version="3.0.0", outline=outline, scene_planner_model=_LowModel())

    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d["gating"] is False
    pacing = d["pacing"]
    assert pacing is not None
    assert pacing["chapters_analyzed"] == 4
    assert pacing["gating"] is False
    # flat low curves -> every chapter flagged intra-chapter
    assert pacing["chapters_with_pacing_warnings"] == 4
    # cross-chapter: 4 low peaks -> doldrums warning present
    assert pacing["serial"]["peaks"] == [45, 45, 45, 45]
    assert any("无高潮" in w for w in pacing["serial"]["warnings"])


def test_pacing_section_none_without_scene_plans(tmp_path):
    # v1 run -> no scene layer -> no persisted plans -> pacing section is None
    _scaffold(tmp_path, n_events=2)
    _run(tmp_path, prompt_version="1.0.0")
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d["pacing"] is None


def test_bare_skeleton_analyzed_but_no_serial_curve(tmp_path):
    # v3 without enrichment -> plans persisted but no emotion -> intra-chapter
    # analysis runs (clean, no warnings) and no serial curve (no peaks).
    _scaffold(tmp_path, n_events=3)
    outline = _write_outline(tmp_path, 3)
    _run(tmp_path, prompt_version="3.0.0", outline=outline)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    pacing = d["pacing"]
    assert pacing is not None
    assert pacing["chapters_analyzed"] == 3
    assert pacing["chapters_with_pacing_warnings"] == 0
    assert "serial" not in pacing        # no peaks -> no cross-chapter curve
