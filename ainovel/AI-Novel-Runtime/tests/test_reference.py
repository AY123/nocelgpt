"""test_reference.py — Reference Quality Anchor (roadmap M9).

Proves the anchor's discipline end-to-end: segmentation, that a reference chapter
is measured with the SAME instruments as a generated one, deterministic profile
aggregation, schema conformance of the pinned artifact, the gap read, the CLI,
and the dashboard section that makes it LIVE (a real production-path consumer).
"""
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.reference import (
    segment_reference_novel, measure_reference_chapter, DETERMINISTIC_FEATURES,
    build_reference_profile, build_reference_intelligence, load_reference_profile,
    compare_to_profile, PROFILE_ID)
from runtime.reference.measure import measure_reference_chapter as _measure


def _schema() -> dict:
    path = (Path(__file__).resolve().parents[2]
            / "AI-Novel-Standard" / "contracts"
            / "reference-quality-profile.schema.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _novel(n_chapters: int = 4) -> str:
    parts = []
    for i in range(1, n_chapters + 1):
        body = ("他握紧了拳头，低声说：“走吧。”" * 25
                + "风像刀，夜像墨，心却像铁一样冷硬。" * 15)
        parts.append(f"第{i}章 章节{i}\n{body}")
    return "\n\n".join(parts)


def make_project(tmp_path: Path) -> Path:
    project = tmp_path / "novel"
    (project / "sources" / "reference-novels").mkdir(parents=True)
    return project


def write_ref(project: Path, name: str, text: str):
    (project / "sources" / "reference-novels" / name).write_text(text, encoding="utf-8")


# --- segmentation ---------------------------------------------------------

def test_segments_on_chapter_headings():
    chapters = segment_reference_novel("REF-00001", _novel(4))
    assert len(chapters) == 4
    assert chapters[0].index == 1
    assert chapters[0].heading.startswith("第1章")


def test_segmentation_is_deterministic():
    text = _novel(3)
    a = [c.to_dict() for c in segment_reference_novel("REF-00001", text)]
    b = [c.to_dict() for c in segment_reference_novel("REF-00001", text)]
    assert a == b


def test_headingless_text_degrades_to_chunks():
    blob = "这是一段没有任何章节标题的长文本。" * 500
    chapters = segment_reference_novel("REF-00001", blob)
    assert len(chapters) >= 1
    assert all(c.heading == "" for c in chapters)


# --- measurement (same instruments) --------------------------------------

def test_measures_with_same_deterministic_features():
    feats = _measure("他说：“走。”" * 40)
    assert feats  # non-empty
    # every declared comparable feature is measurable from a chapter body
    for f in DETERMINISTIC_FEATURES:
        assert f in feats, f

def test_empty_body_measures_to_empty():
    assert _measure("   ") == {}


# --- profile aggregation --------------------------------------------------

def test_profile_is_deterministic():
    src = [("REF-00001", _novel(4))]
    a = build_reference_profile(src).to_dict()
    b = build_reference_profile(src).to_dict()
    assert a == b


def test_profile_bands_only_declared_features():
    profile = build_reference_profile([("REF-00001", _novel(4))])
    d = profile.to_dict()
    assert d["chapters_measured"] == 4
    assert set(d["bands"]).issubset(set(DETERMINISTIC_FEATURES))
    assert d["judge_bands"] == {}          # no reviewer => empty judge arm
    assert d["gating"] is False            # ADR-003


def test_empty_corpus_yields_null_bands():
    d = build_reference_profile([]).to_dict()
    assert d["chapters_measured"] == 0
    assert d["bands"] == {}


# --- schema conformance (Schema-First) ------------------------------------

def test_profile_conforms_to_frozen_schema():
    validator = Draft202012Validator(_schema())
    validator.validate(build_reference_profile([("REF-00001", _novel(4))]).to_dict())
    validator.validate(build_reference_profile([]).to_dict())   # null-band path


def test_schema_pins_gating_false_and_kind():
    schema = _schema()
    assert schema["properties"]["gating"]["const"] is False
    assert schema["properties"]["kind"]["const"] == "reference_quality_profile"
    assert schema["additionalProperties"] is False


# --- gap read -------------------------------------------------------------

def test_gap_flags_in_and_out_of_band():
    profile = build_reference_profile([("REF-00001", _novel(4))]).to_dict()
    # a chapter identical in style to the reference should land mostly in-band
    same = measure_reference_chapter(
        "他握紧了拳头，低声说：“走吧。”" * 25 + "风像刀，夜像墨，心却像铁一样冷硬。" * 15)
    gap = compare_to_profile(same, profile)
    assert gap["gating"] is False
    assert gap["comparison_only"] is True
    assert gap["features_compared"] >= 1
    assert gap["in_band"] + gap["out_of_band"] == gap["features_compared"]


def test_gap_empty_profile_compares_nothing():
    gap = compare_to_profile({"density.dialogue_ratio": 0.5}, {"bands": {}})
    assert gap["features_compared"] == 0


# --- writer + pinned artifact ---------------------------------------------

def test_build_reference_intelligence_pins_conforming_profile(tmp_path):
    project = make_project(tmp_path)
    write_ref(project, "ref1.txt", _novel(4))
    result = build_reference_intelligence(project)
    assert result.ok, result.errors
    assert result.chapters_measured == 4
    loaded = load_reference_profile(project)
    assert loaded is not None and loaded["id"] == PROFILE_ID
    Draft202012Validator(_schema()).validate(loaded)


def test_build_fails_without_sources(tmp_path):
    project = make_project(tmp_path)   # dir exists but empty
    result = build_reference_intelligence(project)
    assert not result.ok
    assert result.stage == "sources"


# --- dashboard section (LIVE consumer) ------------------------------------

def test_dashboard_reference_anchor_section(tmp_path):
    from runtime.dashboard.report import _reference_anchor_section
    project = make_project(tmp_path)
    write_ref(project, "ref1.txt", _novel(4))
    assert build_reference_intelligence(project).ok

    # fake a generated draft envelope + index (mirrors the serial write shape)
    dd = project / "registry" / "derived" / "drafts"
    dd.mkdir(parents=True)
    env = {"draft": {"text": "第九章\n" + ("测试正文，重复。" * 200)}, "content_hash": "x"}
    (dd / "CH-0009.json").write_text(json.dumps(env, ensure_ascii=False), encoding="utf-8")
    (project / "registry" / "derived" / "_index.yaml").write_text(
        "artifacts:\n  - id: CH-0009\n    category: drafts\n"
        "    path: registry/derived/drafts/CH-0009.json\n", encoding="utf-8")

    sec = _reference_anchor_section(project, {"chapter_ids": ["CH-0009"]})
    assert sec is not None
    assert sec["gating"] is False
    assert sec["chapters_compared"] == 1
    assert sec["profile_id"] == PROFILE_ID
    assert sec["per_chapter"][0]["chapter"] == "CH-0009"


def test_dashboard_section_none_without_profile(tmp_path):
    from runtime.dashboard.report import _reference_anchor_section
    project = make_project(tmp_path)
    assert _reference_anchor_section(project, {"chapter_ids": ["CH-0001"]}) is None


# --- judge-bias divergence (reverse-utilize the proven judge bias) --------

def _draft_env(cid: str, body: str, hook: int) -> dict:
    return {"draft": {"text": body}, "content_hash": cid,
            "qa_review": {"scores": {"hook": hook, "conflict": hook, "emotion": hook,
                          "reader_drop_risk": 100 - hook,
                          "originality_risk": 100 - hook, "safety_risk": 0}}}


def _pin_drafts(project: Path, drafts: dict):
    dd = project / "registry" / "derived" / "drafts"
    dd.mkdir(parents=True, exist_ok=True)
    for cid, env in drafts.items():
        (dd / f"{cid}.json").write_text(json.dumps(env, ensure_ascii=False), encoding="utf-8")
    (project / "registry" / "derived" / "_index.yaml").write_text(
        "artifacts:\n" + "".join(
            f"  - id: {cid}\n    category: drafts\n"
            f"    path: registry/derived/drafts/{cid}.json\n" for cid in drafts),
        encoding="utf-8")


def test_judge_bias_divergence_flags_approved_but_divergent(tmp_path):
    from runtime.dashboard.report import _judge_bias_divergence_section
    project = make_project(tmp_path)
    write_ref(project, "ref1.txt", _novel(4))
    assert build_reference_intelligence(project).ok
    # CH-0001: anaphora-heavy prose (ai_taste out of band) + high judge score →
    # the danger zone. CH-0002: clean dialogue + low judge score → not flagged.
    aitasty = "风像刀。风像火。风像潮。" * 60
    clean = "「站住。」马伦举锤挡门。埃德里克抬头报名。她递水问他来历。" * 30
    _pin_drafts(project, {
        "CH-0001": _draft_env("CH-0001", aitasty, 95),
        "CH-0002": _draft_env("CH-0002", clean, 60)})
    sec = _judge_bias_divergence_section(project, {"chapter_ids": ["CH-0001", "CH-0002"]})
    assert sec is not None
    assert sec["gating"] is False and sec["comparison_only"] is True
    assert sec["chapters_analyzed"] == 2
    labels = [s["chapter"] for s in sec["suspects"]]
    assert "CH-0001" in labels            # judge-approved + market-divergent
    assert "CH-0002" not in labels        # low judge score → not in the danger zone
    assert sec["suspects"][0]["ai_taste_out_of_band"] >= 1


def test_judge_bias_divergence_none_without_profile(tmp_path):
    from runtime.dashboard.report import _judge_bias_divergence_section
    project = make_project(tmp_path)
    _pin_drafts(project, {"CH-0001": _draft_env("CH-0001", "正文。" * 200, 90)})
    # no reference profile pinned → nothing to diverge from
    assert _judge_bias_divergence_section(project, {"chapter_ids": ["CH-0001"]}) is None


def test_judge_bias_divergence_skips_degraded_scores(tmp_path):
    from runtime.dashboard.report import _judge_bias_divergence_section
    project = make_project(tmp_path)
    write_ref(project, "ref1.txt", _novel(4))
    assert build_reference_intelligence(project).ok
    # an all-zero (degraded sentinel) score must be excluded, not treated as a
    # low-quality chapter — is_degraded_scores guards the fold.
    env = _draft_env("CH-0001", "风像刀。风像火。风像潮。" * 60, 0)
    env["qa_review"]["scores"] = {k: 0 for k in env["qa_review"]["scores"]}
    _pin_drafts(project, {"CH-0001": env})
    sec = _judge_bias_divergence_section(project, {"chapter_ids": ["CH-0001"]})
    # the only chapter is degraded → no analyzable rows → section is None
    assert sec is None
