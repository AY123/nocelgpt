import json
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.market.sources import load_market_observations
from runtime.market.analyzer import analyze_observations
from runtime.market.snapshot import build_market_snapshot, _compute_staleness
from runtime.market.writer import build_market_intelligence, load_market_snapshot
from runtime.outline.agents import derive_market_position


def make_project(tmp_path: Path) -> Path:
    project = tmp_path / "novel"
    (project / "sources" / "market-observations").mkdir(parents=True)
    (project / "registry" / "_meta").mkdir(parents=True)
    (project / "registry" / "_meta" / "project-id").write_text("novel\n", encoding="utf-8")
    return project


def write_obs(project: Path, name: str, text: str):
    (project / "sources" / "market-observations" / name).write_text(text, encoding="utf-8")


MALE_OBS = (
    "fetched_at: 2026-06-01\n"
    "起点月票榜：无限流依旧霸榜，副本+轮回设定让读者高度代入，爽点密集追读强。"
    "修仙类稳定，境界突破带来解压感。"
    "读者弃书集中在中期注水、副本节奏拖沓。\n"
)
FEMALE_OBS = (
    "fetched_at: 2026-05-20\n"
    "晋江榜单：治愈日常题材温暖治愈，读者共鸣强。疯批人设情绪拉满。"
    "掉订多因人设崩塌与断更。\n"
)


def market_schema() -> dict:
    path = (Path(__file__).resolve().parents[2]
            / "AI-Novel-Standard" / "contracts" / "market-snapshot.schema.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_observations_require_at_least_one(tmp_path):
    project = make_project(tmp_path)
    result = load_market_observations(project)
    assert not result.ok
    assert any("at least 1" in e for e in result.errors)


def test_observations_load_with_fetched_at_and_platform(tmp_path):
    project = make_project(tmp_path)
    write_obs(project, "qidian-male.txt", MALE_OBS)
    result = load_market_observations(project)
    assert result.ok
    obs = result.observations[0]
    assert obs.fetched_at == "2026-06-01"
    assert obs.platform == "qidian"
    assert obs.sha256


def test_analysis_is_deterministic_and_channel_routed(tmp_path):
    project = make_project(tmp_path)
    write_obs(project, "male.txt", MALE_OBS)
    write_obs(project, "female.txt", FEMALE_OBS)
    result = load_market_observations(project)
    a1 = analyze_observations(project, result.observations)
    a2 = analyze_observations(project, result.observations)
    assert a1 == a2   # reproducible
    male_genres = {s["genre"] for s in a1["male_signals"]}
    female_genres = {s["genre"] for s in a1["female_signals"]}
    assert "无限流" in male_genres
    assert "治愈" in female_genres
    assert a1["common_drop_points"]   # drop points extracted


def test_snapshot_validates_against_contract(tmp_path):
    project = make_project(tmp_path)
    write_obs(project, "male.txt", MALE_OBS)
    write_obs(project, "female.txt", FEMALE_OBS)
    obs = load_market_observations(project).observations
    analysis = analyze_observations(project, obs)
    snap = build_market_snapshot(analysis, obs, project_id="novel",
                                 today=date(2026, 6, 15))
    schema = market_schema()
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(snap))
    assert errors == [], [e.message for e in errors]
    assert snap["staleness"]["gating"] is False


def test_staleness_fresh_vs_stale():
    fresh = _compute_staleness("2026-06-01", freshness_days=90, today=date(2026, 6, 15))
    assert fresh["is_stale"] is False
    assert fresh["age_days"] == 14
    stale = _compute_staleness("2026-01-01", freshness_days=90, today=date(2026, 6, 15))
    assert stale["is_stale"] is True
    assert stale["gating"] is False    # stale NEVER gates (ADR-003)
    assert "note" in stale


def test_missing_fetched_at_marks_stale_but_never_gates():
    block = _compute_staleness(None, freshness_days=90)
    assert block["is_stale"] is True
    assert block["gating"] is False


def test_build_writes_snapshot_not_facts(tmp_path):
    project = make_project(tmp_path)
    write_obs(project, "male.txt", MALE_OBS)
    result = build_market_intelligence(project)
    assert result.ok
    assert result.snapshot_json == "registry/derived/market/MARKET-00001.json"
    assert (project / result.snapshot_json).exists()
    # never writes facts
    facts = project / "registry" / "facts"
    assert not any(facts.rglob("MARKET*")) if facts.exists() else True
    loaded = load_market_snapshot(project)
    assert loaded["kind"] == "market_snapshot"


def test_derive_market_position_without_snapshot_falls_back():
    # No snapshot => reference-derived positioning (existing behavior preserved).
    pos = derive_market_position({"genre_signals": ["玄幻"], "reader_rewards": []})
    assert pos["channel"] == "男频"
    assert pos["sub_genre"] == "玄幻"
    assert "market_snapshot_id" not in pos


def test_derive_market_position_with_snapshot_anchors_on_real_signals():
    snapshot = {
        "id": "MARKET-00001",
        "channels": [
            {"channel": "男频", "hot_genres": [
                {"genre": "无限流", "heat": 90, "why_hot": "副本轮回代入感强",
                 "drop_points": ["中期注水"]}]},
        ],
        "signals": {"trending_genres": ["无限流", "修仙"]},
        "staleness": {"is_stale": False},
    }
    pos = derive_market_position({"genre_signals": ["玄幻"], "reader_rewards": []}, snapshot)
    assert pos["sub_genre"] == "无限流"            # anchored on real market, not reference
    assert pos["reader_promise"] == "副本轮回代入感强"
    assert pos["known_drop_points"] == ["中期注水"]
    assert pos["market_snapshot_id"] == "MARKET-00001"
    assert pos["market_is_stale"] is False


def test_outline_uses_snapshot_when_present(tmp_path):
    # End-to-end: a market snapshot in the project steers the outline's position.
    from runtime.outline.workflow import run_outline_bootstrap
    project = tmp_path / "novel"
    (project / "sources" / "reference-novels").mkdir(parents=True)
    (project / "sources" / "market-observations").mkdir(parents=True)
    (project / "registry" / "_meta").mkdir(parents=True)
    (project / "registry" / "_meta" / "project-id").write_text("novel\n", encoding="utf-8")
    (project / "sources" / "reference-novels" / "ref.txt").write_text(
        "少年觉醒金手指，逃离追杀，突破境界赢得胜利。", encoding="utf-8")
    (project / "sources" / "market-observations" / "male.txt").write_text(
        MALE_OBS, encoding="utf-8")

    build_market_intelligence(project)
    result = run_outline_bootstrap(project, run_id="market-run")
    assert result.ok
    outline = json.loads((project / result.outline_json).read_text(encoding="utf-8"))
    assert outline["market_position"].get("market_snapshot_id") == "MARKET-00001"
