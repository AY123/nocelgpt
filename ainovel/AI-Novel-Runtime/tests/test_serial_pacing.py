"""test_serial_pacing.py — cross-chapter pacing check (P23).

Where test_pacing checks one chapter's curve, this checks the RHYTHM OF CLIMAXES
across a serial: the per-chapter peak-valence sequence. Deterministic, evaluative,
never gates (ADR-003). Detects prolonged doldrums, no-climax runs, cadence
violation against the authored reward_loop.cadence_chapters, and clustering.
"""
from __future__ import annotations

from runtime.scene import check_serial_pacing, curve_summary


def _msgs(peaks, cadence=None):
    return check_serial_pacing(peaks, cadence=cadence).to_dict()["findings"]


def _warn(peaks, cadence=None):
    return [f["message"] for f in _msgs(peaks, cadence) if f["severity"] == "warning"]


# --------------------------------------------------------------------------- #
# Never gates, always evaluative                                              #
# --------------------------------------------------------------------------- #
def test_never_gates():
    r = check_serial_pacing([40, 75, 45, 80], cadence=2).to_dict()
    assert r["gating"] is False
    assert r["axis"] == "evaluative"


# --------------------------------------------------------------------------- #
# Symptoms                                                                     #
# --------------------------------------------------------------------------- #
def test_prolonged_doldrums_flagged():
    w = _warn([40, 45, 50, 42, 48])
    assert any("无高潮" in m for m in w)


def test_no_climax_flagged():
    w = _warn([30, 40, 50, 45])
    assert any("全程无一章达到高潮" in m for m in w)


def test_cadence_violation_flagged():
    # one early climax then a long dry stretch; author promised every 2 chapters
    w = _warn([85, 40, 45, 50, 55, 42], cadence=2)
    assert any("超出声明节奏" in m for m in w)


def test_cadence_respected_no_violation():
    # climaxes every ~2 chapters, matching cadence=2 -> no cadence warning
    msgs = _msgs([80, 45, 82, 48, 79, 50], cadence=2)
    assert not any("超出声明节奏" in f["message"] for f in msgs)


def test_healthy_rhythm_is_clean():
    r = check_serial_pacing([40, 75, 45, 80, 50, 72]).to_dict()
    assert all(f["severity"] != "warning" for f in r["findings"])
    assert any("健康" in f["message"] for f in r["findings"])


def test_clustering_noted():
    findings = _msgs([80, 85, 75, 40, 45, 42, 48, 44])
    assert any("扎堆" in f["message"] for f in findings)


# --------------------------------------------------------------------------- #
# Degrade + determinism                                                        #
# --------------------------------------------------------------------------- #
def test_too_few_chapters_degrades():
    r = check_serial_pacing([70]).to_dict()
    assert all(f["severity"] == "info" for f in r["findings"])
    assert r["gating"] is False


def test_deterministic():
    a = check_serial_pacing([40, 75, 45, 80], cadence=2).to_dict()
    b = check_serial_pacing([40, 75, 45, 80], cadence=2).to_dict()
    assert a == b


# --------------------------------------------------------------------------- #
# curve_summary feeds the per-chapter peak                                     #
# --------------------------------------------------------------------------- #
def test_curve_summary_exposes_peak():
    plan = {"scenes": [{"index": 1, "emotion": {"valence": 30}},
                       {"index": 2, "emotion": {"valence": 80}}]}
    s = curve_summary(plan)
    assert s["peak"] == 80
    assert s["amplitude"] == 50
    assert s["valences"] == [30, 80]


def test_curve_summary_none_without_emotion():
    assert curve_summary({"scenes": [{"index": 1, "beat": "setup", "purpose": "p"}]}) is None


# --------------------------------------------------------------------------- #
# Serial-loop integration: cross-chapter pacing surfaces in SerialResult       #
# --------------------------------------------------------------------------- #
import yaml
from pathlib import Path
from runtime.serialize import run_serial

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


class _Out:
    def __init__(self, t): self.text = t; self.model_id = "fake"


class _LowModel:
    """Enriches every scene with a low valence -> a doldrums serial."""
    model_id = "fake"
    def generate(self, prompt):
        import json
        return _Out(json.dumps({"scenes": [{"index": i, "emotion": {"valence": 45}}
                                           for i in range(1, 6)]}))


def _outline(n, cadence=2):
    return {"id": "OUTLINE-00001", "reward_loop": {"cadence_chapters": cadence},
            "first_30_chapters": [
                {"chapter_no": i, "goal": f"目标{i}", "conflict": "冲突",
                 "escalation": "升级", "reward_if_any": "回报", "end_hook": "钩子"}
                for i in range(1, n + 1)]}


def test_serial_pacing_surfaces_in_result(tmp_path):
    _scaffold(tmp_path, n_events=4)
    r = run_serial(project_path=tmp_path, standard_root=STANDARD, schema_dir=SCHEMA,
                   out_dir=tmp_path / "b", prompt_version="3.0.0",
                   outline=_outline(4), scene_planner_model=_LowModel()).to_dict()
    assert r["gating"] is False
    assert r["produced"] == 4
    # every produced chapter recorded its climax height
    assert [c["pacing_peak"] for c in r["chapters"]] == [45, 45, 45, 45]
    # the cross-chapter report is present and flags the doldrums, without gating
    sp = r["serial_pacing"]
    assert sp is not None and sp["gating"] is False
    assert any("无高潮" in f["message"] for f in sp["findings"])


def test_no_serial_pacing_without_enrichment(tmp_path):
    # v3 with an outline but NO scene planner model -> bare skeletons, no emotion,
    # so no cross-chapter pacing report (behavior unchanged from before P23).
    _scaffold(tmp_path, n_events=3)
    r = run_serial(project_path=tmp_path, standard_root=STANDARD, schema_dir=SCHEMA,
                   out_dir=tmp_path / "b", prompt_version="3.0.0",
                   outline=_outline(3)).to_dict()
    assert r["serial_pacing"] is None
    assert all(c["pacing_peak"] is None for c in r["chapters"])
