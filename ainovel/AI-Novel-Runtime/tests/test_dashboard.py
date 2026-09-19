"""test_dashboard.py — Novel Dashboard (roadmap P18).

The dashboard is pure read-side aggregation over products the pipeline already
produces. These tests pin: it aggregates correct story/production counts,
reflects the Novel Brain and serialization schedule when present (and degrades
when absent), reads the latest draft's QA/commercial signals, never gates
(ADR-003), and produces a report even for an empty project.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from runtime.serialize import run_serial
from runtime.dashboard import build_dashboard

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _scaffold(root: Path, *, n_events: int = 3, with_brain: bool = False, with_plan: bool = False):
    facts = root / "registry" / "facts"
    meta = root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    _write(facts / "timelines" / "TML-00001.yaml", {"id": "TML-00001", "name": "主线", "status": "active", "fact_version": 1, "kind": "main"})
    _write(facts / "characters" / "CHR-00001.yaml", {"id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1})
    for i in range(1, n_events + 1):
        _write(facts / "events" / f"EVT-{i:05d}.yaml", {"id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active", "fact_version": 1, "timeline": "TML-00001", "sequence_index": i, "participants": ["CHR-00001"], "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []), "effects": ([f"EVT-{i+1:05d}"] if i < n_events else []), "summary": f"第{i}章"})
    if with_brain:
        _write(root / "sources" / "novel-brain.yaml", {"id": "BRAIN-00001", "kind": "novel_brain", "version": "1.0", "mission": "让读者追到天亮", "genre": {"primary": "玄幻", "channel": "男频"}, "target_reader": {"who": "读者"}, "promise": "每三章一个高潮", "writing_style": {"voice": "冷峻"}, "forbidden_style": ["注水"]})
    if with_plan:
        _write(root / "sources" / "serial-plan.yaml", {"id": "PLAN-00001", "kind": "serial_plan", "version": "1.0", "start_date": "2026-06-25", "daily_target": 1, "backlog_target": 5, "rest_days": [7]})


def _run(root: Path, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA, out_dir=root / "build-serial", **kw)


def test_dashboard_aggregates_story_and_production(tmp_path):
    _scaffold(tmp_path, n_events=3)
    _run(tmp_path)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d["gating"] is False
    assert d["story"]["events"] == 3
    assert d["story"]["characters"] == 1
    assert d["production"]["chapters_produced"] == 3
    assert d["production"]["latest_chapter"] == "TASK-00003"


def test_empty_project_still_produces_a_dashboard(tmp_path):
    _scaffold(tmp_path, n_events=2)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d["gating"] is False
    assert d["production"]["chapters_produced"] == 0
    assert d["production"]["latest_chapter"] is None
    assert d["brain"] == {"authored": False}
    assert d["schedule"] is None
    assert d["latest_signals"] == {}


def test_brain_section_reflects_authored_brain(tmp_path):
    _scaffold(tmp_path, n_events=2, with_brain=True)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d["brain"]["authored"] is True
    assert d["brain"]["valid"] is True
    assert d["brain"]["genre"] == "玄幻"


def test_schedule_section_appears_with_plan(tmp_path):
    _scaffold(tmp_path, n_events=3, with_plan=True)
    _run(tmp_path)
    d = build_dashboard(tmp_path, standard_root=STANDARD, today=date(2026, 7, 2)).to_dict()
    assert d["schedule"] is not None
    assert d["schedule"]["produced"] == 3
    assert d["schedule"]["gating"] is False
    assert d["schedule"]["break_risk"] in ("none", "low", "high")


class _ImprovingSim:
    reviewer_id = "improving-sim"

    def __init__(self):
        self.calls = 0

    def review(self, artifact, package):
        from runtime.execution.reader_sim import ReaderSimulation
        self.calls += 1
        sat = 90 if self.calls % 2 == 0 else 40
        return ReaderSimulation(reviewer=self.reviewer_id, personas=[{"name": "小白", "satisfaction": sat, "would_continue": True, "degraded": False}], aggregate={"mean_satisfaction": sat, "continue_rate": 100, "drop_personas": [], "common_expectations": []}, judge_provenance={"model_id": "improving-sim", "degraded": False})


class _Rewriter:
    model_id = "rw"
    model_kind = "llm"

    def generate(self, prompt):
        from runtime.execution.model import ModelOutput
        return ModelOutput(text="商业优化后的正文。" * 30, model_id="rw", model_kind="llm")


def test_latest_signals_reads_commercial_from_envelope(tmp_path):
    _scaffold(tmp_path, n_events=2)
    _run(tmp_path, simulator=_ImprovingSim(), rewrite_model=_Rewriter(), commercial_rounds=1)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    sig = d["latest_signals"]
    assert sig["chapter"] == "TASK-00002"
    assert sig.get("commercial", {}).get("verdict") == "improved"
    assert "pay_probability_delta" not in sig["commercial"]


class _PayImprovingSim:
    reviewer_id = "pay-sim"

    def __init__(self):
        self.calls = 0

    def review(self, artifact, package):
        from runtime.execution.reader_sim import ReaderSimulation
        self.calls += 1
        pay = 70 if self.calls % 2 == 0 else 40
        sat = 90 if self.calls % 2 == 0 else 50
        return ReaderSimulation(reviewer=self.reviewer_id, personas=[{"name": "追订党", "satisfaction": sat, "would_continue": True, "continue_probability": 85, "pay_probability": pay, "degraded": False}], aggregate={"mean_satisfaction": sat, "continue_rate": 100, "mean_continue_probability": 85, "mean_pay_probability": pay, "pay_personas": ["追订党"] if pay >= 50 else [], "drop_personas": [], "common_expectations": []}, judge_provenance={"model_id": "pay-sim", "degraded": False})


def test_latest_signals_surfaces_v2_pay_delta(tmp_path):
    _scaffold(tmp_path, n_events=2)
    _run(tmp_path, simulator=_PayImprovingSim(), rewrite_model=_Rewriter(), commercial_rounds=1)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    c = d["latest_signals"]["commercial"]
    assert c["verdict"] == "improved"
    assert c["pay_probability_delta"] == 30
    assert c["pay_leak_personas"] == []


def test_chapter_final_compare_view_reflects_written_finals(tmp_path):
    _scaffold(tmp_path, n_events=2, with_brain=True)
    _run(tmp_path)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    compare = d["chapter_final_compare"]
    assert compare is not None
    assert compare["chapters_compared"] == 2
    assert compare["chapters_changed"] >= 0
    assert compare["chapters_accepted"] >= 0
    assert compare["avg_delta_chars"] is not None
    assert len(compare["rows"]) == 2
    assert all("winner" in row for row in compare["rows"])
    assert all("recommendation" in row for row in compare["rows"])
    assert all("pipeline_action" in row for row in compare["rows"])


from runtime.execution.quality_center import QualityReport, V1_DIMENSIONS, SCORE_DIMENSIONS


class _VersionSwitchingReviewer:
    reviewer_id = "version-switching-reviewer"

    def __init__(self):
        self.calls = 0

    def review(self, artifact, package):
        self.calls += 1
        v1 = {d: 70 for d in V1_DIMENSIONS}
        v1["commercial"] = 60
        if self.calls % 2 == 1:
            return QualityReport(reviewer=self.reviewer_id, scores=v1)
        scores = dict(v1)
        scores.update({"retention": 80, "subscription": 55, "payoff": 75, "curiosity": 65, "promise_delivery": 60, "pacing": 70, "character_growth": 50, "serial_sustainability": 60, "reader_drop_risk": 30, "safety_risk": 10})
        return QualityReport(reviewer=self.reviewer_id, scores=scores)


def test_quality_trend_folds_all_chapters(tmp_path):
    _scaffold(tmp_path, n_events=4)
    _run(tmp_path, reviewer=_VersionSwitchingReviewer())
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    trend = d["quality_trend"]
    assert trend is not None
    assert trend["gating"] is False
    assert trend["chapters_scored"] == 4
    assert trend["chapters_total"] == 4
    assert len(trend["per_chapter"]) == 4
    assert trend["dimension_coverage"]["commercial"] == 4
    assert trend["dimension_coverage"]["retention"] == 2
    assert trend["dimension_averages"]["retention"] == 80.0
    assert "reader_drop_risk" in trend["risk_dimensions"]


def test_quality_trend_absent_without_reports(tmp_path):
    _scaffold(tmp_path, n_events=2)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d["quality_trend"] is None


def test_chapter_final_compare_rich_view(tmp_path):
    _scaffold(tmp_path, n_events=2)
    _run(tmp_path)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    compare = d["chapter_final_compare"]
    assert compare is not None
    assert compare["chapters_compared"] == 2
    assert compare["chapters_accepted"] >= 0
    assert compare["avg_delta_chars"] is not None
    assert len(compare["rows"]) == 2
    assert all("winner" in row for row in compare["rows"])
    assert all("recommendation" in row for row in compare["rows"])
    assert all("pipeline_action" in row for row in compare["rows"])


def test_dashboard_panels_are_split_for_editor_decision_ops(tmp_path):
    _scaffold(tmp_path, n_events=2, with_brain=True, with_plan=True)
    _run(tmp_path)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    compare = d["chapter_final_compare"]
    assert compare is not None
    assert compare["editor_panel"]["chapters_compared"] == compare["chapters_compared"]
    assert compare["decision_panel"]["recommended_action"] in {"advance", "revise", "review"}
    assert 0 <= compare["ops_panel"]["change_rate_avg"]
    assert compare["ops_panel"]["avg_delta_chars"] == compare["avg_delta_chars"]
    assert compare["editor_panel"]["headline_sample"]
    assert compare["decision_panel"]["accepted_count"] >= 0
    assert compare["ops_panel"]["risk_total"] >= 0


def test_m5_closeout_flags_present_in_dashboard(tmp_path):
    _scaffold(tmp_path, n_events=2)
    _run(tmp_path)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d.get("m5_closeout") is not None
    assert d["m5_closeout"]["status"] == "closed"
    assert d["m5_closeout"]["completed_items"] >= 4


def test_openings_section_present_and_never_gates(tmp_path):
    _scaffold(tmp_path, n_events=3)
    _run(tmp_path)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    openings = d.get("openings")
    assert openings is not None
    assert openings["gating"] is False
    assert openings["chapters_analyzed"] == 3
    # findings always present (either warnings or a clean info note)
    assert openings["findings"]


def test_openings_section_absent_without_chapters(tmp_path):
    _scaffold(tmp_path, n_events=2)   # facts only, no serial run => no drafts
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d.get("openings") is None


def test_openings_section_flags_repeated_openings(tmp_path):
    """A controlled repeated-opening set surfaces a warning in the dashboard."""
    from runtime import derived
    from runtime.execution.envelope import ENVELOPE_FORMAT
    _scaffold(tmp_path, n_events=1)   # registry meta the dashboard loader needs
    same = "周洛铭睁开眼，天花板的裂缝还在。梦墟在暗红天幕下绵延。他握紧了拳头。"
    for i in range(1, 4):
        env = {"envelope_format": ENVELOPE_FORMAT,
               "draft": {"artifact_format": "anes.v2", "kind": "prose",
                         "capability": "ChapterDraft", "task_id": f"TASK-{i:05d}",
                         "content_hash": f"sha256:{i}", "body": f"# 第{i}章\n\n{same}"}}
        derived.write_artifact(project_path=tmp_path, category="drafts",
                               artifact_id=f"TASK-{i:05d}", artifact=env,
                               serialized=__import__("json").dumps(env, ensure_ascii=False))
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    openings = d["openings"]
    assert openings["chapters_analyzed"] == 3
    assert openings["warnings"], "expected a repeated-opening warning"
    assert "周洛铭睁开眼" in openings["warnings"][0]


# --------------------------------------------------------------------------- #
# Pipeline stage section (M8-01) — the book-level governance view in the        #
# dashboard, plus its feed into book_health.                                    #
# --------------------------------------------------------------------------- #
def test_pipeline_section_folds_stage_counts(tmp_path):
    _scaffold(tmp_path, n_events=3)
    _run(tmp_path)
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    pipeline = d["pipeline"]
    assert pipeline is not None
    assert pipeline["total"] == 3
    assert pipeline["gating"] is False
    # a clean deterministic run has no governance backlog
    assert pipeline["blocked"] == 0
    assert pipeline["awaiting_approval"] == 0
    # every produced chapter is at least drafted; stage counts sum to the total
    assert sum(pipeline["by_stage"].values()) == 3


def test_pipeline_section_absent_without_chapters(tmp_path):
    _scaffold(tmp_path, n_events=2)   # facts only, no serial run => no drafts
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d.get("pipeline") is None


def test_blocked_chapter_raises_book_health_at_risk(tmp_path):
    """A chapter blocked by M7 (hard red-line / rejected review) must surface as an
    at_risk book_health signal — the governance backlog can't stay invisible."""
    from runtime import derived
    from runtime.execution.envelope import ENVELOPE_FORMAT
    _scaffold(tmp_path, n_events=1)
    # A draft whose envelope carries a 'block' publish_readiness (M7 rides the
    # envelope sibling; the pipeline projection reads recommendation=='block').
    env = {"envelope_format": ENVELOPE_FORMAT,
           "draft": {"artifact_format": "anes.v2", "kind": "prose",
                     "capability": "ChapterDraft", "task_id": "TASK-00001",
                     "content_hash": "sha256:1", "body": "正文"},
           "publish_readiness": {"recommendation": "block"},
           "m7": {"risk_level": "L3", "recommendation": "block", "redline_passed": False}}
    derived.write_artifact(project_path=tmp_path, category="drafts",
                           artifact_id="TASK-00001", artifact=env,
                           serialized=__import__("json").dumps(env, ensure_ascii=False))
    d = build_dashboard(tmp_path, standard_root=STANDARD).to_dict()
    assert d["pipeline"]["blocked"] == 1
    assert d["pipeline"]["blocked_chapters"] == ["TASK-00001"]
    assert d["book_health"]["health"] == "at_risk"
    assert any("publish-blocked" in r for r in d["book_health"]["reasons"])
    assert d["book_health"]["gating"] is False
