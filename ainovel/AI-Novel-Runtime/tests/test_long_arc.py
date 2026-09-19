from __future__ import annotations

from runtime.arc import project_long_arc, render_long_arc


def _outline():
    """A minimal outline with the long-arc raw material the fold reads."""
    return {
        "id": "OUTLINE-00001",
        "power_system": {"tiers": [
            "潜梦者（表层）", "织梦师（引导）", "梦墟行者（猎晶）",
            "梦域领主（造域）", "梦蚀尊者（改写）"]},
        "conflict_ladder": [
            {"level": "小敌人", "pressure_source": "生存威胁"},
            {"level": "阶段boss", "pressure_source": "势力封锁"},
            {"level": "世界级敌人", "pressure_source": "旧秩序顶层"}],
        "reward_loop": {"cadence_chapters": 3},
        "plot": {"volumes": [
            {"id": "VOL-01", "title": "起势", "goal": "突破潜梦者", "oppressor": "小敌人"},
            {"id": "VOL-02", "title": "破局", "goal": "突破梦墟行者", "oppressor": "阶段boss"},
            {"id": "VOL-03", "title": "问鼎", "goal": "突破梦蚀尊者", "oppressor": "世界级敌人"}]},
    }


# --- volume expansion ------------------------------------------------------

def test_volumes_partition_the_horizon_without_gaps():
    plan = project_long_arc(_outline(), chapter_limit=100)
    vols = plan.volumes
    assert len(vols) == 3
    # contiguous, no gaps, cover 1..100
    assert vols[0]["start_chapter"] == 1
    assert vols[-1]["end_chapter"] == 100
    for a, b in zip(vols, vols[1:]):
        assert b["start_chapter"] == a["end_chapter"] + 1
    # remainder (100/3 = 33 r1) goes to the earliest volume
    spans = [v["end_chapter"] - v["start_chapter"] + 1 for v in vols]
    assert spans == [34, 33, 33]


def test_climax_is_volume_end_and_paywall_opens_next_volume():
    plan = project_long_arc(_outline(), chapter_limit=100)
    v1 = plan.volumes[0]
    assert v1["climax_chapter"] == v1["end_chapter"] == 34
    assert v1["paywall_chapter"] == 35
    # the last volume has no paywall (nothing follows it in-horizon)
    assert plan.volumes[-1]["paywall_chapter"] is None
    assert plan.paywall_chapters == [35, 68]


# --- per-chapter coordinates ----------------------------------------------

def test_chapter_50_is_in_volume_2_with_right_coordinates():
    plan = project_long_arc(_outline(), chapter_limit=100)
    c = plan.chapter(50)
    assert c["volume_id"] == "VOL-02"
    assert c["position_in_volume"] == 50 - 35 + 1  # v2 starts at 35
    assert c["chapters_to_volume_climax"] == 67 - 50
    assert c["is_volume_climax"] is False
    assert c["conflict_level"] == "阶段boss"


def test_power_tier_climbs_with_progress():
    plan = project_long_arc(_outline(), chapter_limit=100)
    tiers = [plan.chapter(n)["power_tier"] for n in (1, 25, 50, 75, 100)]
    # ch1 approaches the first tier, ch100 the last; monotonic non-decreasing
    assert tiers[0] == "潜梦者"
    assert tiers[-1] == "梦蚀尊者"
    order = ["潜梦者", "织梦师", "梦墟行者", "梦域领主", "梦蚀尊者"]
    idxs = [order.index(t) for t in tiers]
    assert idxs == sorted(idxs)


def test_volume_climax_chapter_flagged():
    plan = project_long_arc(_outline(), chapter_limit=100)
    assert plan.chapter(34)["is_volume_climax"] is True
    assert plan.chapter(67)["is_volume_climax"] is True
    assert plan.chapter(100)["is_volume_climax"] is True


def test_deterministic():
    a = project_long_arc(_outline(), chapter_limit=100).to_dict()
    b = project_long_arc(_outline(), chapter_limit=100).to_dict()
    assert a == b


def test_never_gates():
    plan = project_long_arc(_outline(), chapter_limit=60)
    assert plan.to_dict()["gating"] is False


# --- degradation -----------------------------------------------------------

def test_empty_outline_degrades_to_single_implicit_volume():
    plan = project_long_arc(None, chapter_limit=20)
    assert len(plan.volumes) == 1
    assert plan.volumes[0]["start_chapter"] == 1
    assert plan.volumes[0]["end_chapter"] == 20
    c = plan.chapter(10)
    assert c["volume_id"] == "VOL-01"
    assert c["power_tier"] is None       # no tiers authored
    assert c["conflict_level"] is None


def test_chapter_out_of_range_returns_none():
    plan = project_long_arc(_outline(), chapter_limit=50)
    assert plan.chapter(51) is None
    assert plan.chapter(0) is None


# --- render ----------------------------------------------------------------

def test_render_names_volume_and_tier_and_marks_climax():
    plan = project_long_arc(_outline(), chapter_limit=100)
    block = render_long_arc(plan, 34)   # VOL-01 climax
    assert "VOL-01" in block
    assert "本卷高潮" in block
    assert "织梦师" in block or "潜梦者" in block   # a power tier appears
    # discipline line present
    assert "绝不覆盖事实" in block


def test_render_paywall_chapter_flags_hook():
    plan = project_long_arc(_outline(), chapter_limit=100)
    block = render_long_arc(plan, 35)   # first paywall
    assert "付费墙" in block or "新卷开篇" in block


def test_render_out_of_range_is_stable_sentinel():
    plan = project_long_arc(_outline(), chapter_limit=10)
    block = render_long_arc(plan, 11)
    assert block                         # non-empty so the v10 slot binds
    assert "超出长弧规划" in block
