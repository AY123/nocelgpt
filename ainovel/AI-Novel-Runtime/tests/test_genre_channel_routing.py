"""test_genre_channel_routing.py — genre→channel routing has ONE home.

The 男频/女频 default used to be a literal set duplicated in
positioning/generate.py and genesis/brain_gen.py:

    _MALE_LEAN = {"玄幻", "仙侠", "科幻", "奇幻"}

Both copies stayed in sync and both were wrong the same way: they listed four
一级题材 only, so 武侠/都市/历史/游戏/诸天无限 and EVERY 起点 二级分类 name
(东方玄幻 高武世界 都市异能 商战职场 …) defaulted to 女频 whenever the outline
left `market_position.channel` blank. That is a deterministic misroute which
poisons the folded Brain's genre.channel, the Position's reader_segment/leans_on,
and the admission channel-consistency check downstream.

Pins:
  - every 一级题材 and 二级分类 this project targets routes to 男频;
  - an AUTHORED channel always wins over the genre default (the human wins);
  - a folded Brain and a folded Position never disagree on channel (they share
    the same leaf, so this can no longer drift);
  - 女频 names still route to 女频 (the fix is not "everything is 男频");
  - unknown/blank degrades deterministically, never raises.
"""
from __future__ import annotations

import pytest

from runtime.genre_taxonomy import (DEFAULT_CADENCE, DEFAULT_CHANNEL,
                                    FEMALE_CHANNEL, MALE_CHANNEL,
                                    cadence_for_genre, channel_for_genre,
                                    resolve_cadence, resolve_channel)
from runtime.genesis.brain_gen import build_brain
from runtime.positioning.generate import build_position

# The nine 一级题材 + the ten 二级分类 the standard docs cover.
PRIMARY_GENRES = ["玄幻", "奇幻", "武侠", "仙侠", "都市", "历史", "游戏",
                  "科幻", "诸天无限"]
XUANHUAN_SUBGENRES = ["东方玄幻", "异世大陆", "王朝争霸", "高武世界"]
URBAN_SUBGENRES = ["都市生活", "都市异能", "异术超能", "青春校园",
                   "娱乐明星", "商战职场"]


def _outline(genre: str, *, channel: str | None = None) -> dict:
    """Minimal outline shaped like the bootstrap's, with channel left blank so
    the genre default is what actually decides."""
    mp: dict = {"sub_genre": genre, "reader_promise": "持续成长"}
    if channel is not None:
        mp["channel"] = channel
    return {
        "genre": [genre],
        "core_hook": f"一个{genre}故事的核心钩子",
        "logline": f"{genre}测试用 logline",
        "market_position": mp,
        "reward_loop": {"reward_types": ["打脸", "升级"], "cadence_chapters": 3},
        "originality_delta": [{"our_variation": "金手指有代价"}],
    }


# --------------------------------------------------------------------------- #
# The leaf                                                                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("genre", PRIMARY_GENRES + XUANHUAN_SUBGENRES + URBAN_SUBGENRES)
def test_male_genres_and_subgenres_route_to_male_channel(genre):
    """The regression: every one of these used to fall through to 女频."""
    assert channel_for_genre(genre) == MALE_CHANNEL, (
        f"{genre} must default to {MALE_CHANNEL}")


@pytest.mark.parametrize("genre", ["现代言情", "古代言情", "宫廷侯爵", "宅斗",
                                   "甜宠", "疯批", "治愈"])
def test_female_genres_still_route_to_female_channel(genre):
    """The fix must not collapse into 'everything is 男频'."""
    assert channel_for_genre(genre) == FEMALE_CHANNEL


def test_compound_authored_names_route_by_containment():
    """Authors write compound names; they must still route."""
    assert channel_for_genre("东方玄幻·宗门流") == MALE_CHANNEL
    assert channel_for_genre("都市异能流") == MALE_CHANNEL
    # 都市异能 (male) must win over the bare 都市 substring, and a female
    # compound must not be captured by a male substring.
    assert channel_for_genre("现代言情·豪门") == FEMALE_CHANNEL


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_blank_genre_degrades_to_default(blank):
    assert channel_for_genre(blank) == DEFAULT_CHANNEL


def test_unknown_genre_degrades_and_never_raises():
    assert channel_for_genre("完全没听过的类型XYZ") == DEFAULT_CHANNEL


def test_authored_channel_always_wins():
    """The human's authored value beats the genre default in both directions."""
    assert resolve_channel("女频", "高武世界") == "女频"
    assert resolve_channel("男频", "现代言情") == "男频"
    # Blank/whitespace authored value falls through to the genre default.
    assert resolve_channel(None, "高武世界") == MALE_CHANNEL
    assert resolve_channel("   ", "高武世界") == MALE_CHANNEL


# --------------------------------------------------------------------------- #
# The two consumers                                                            #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("genre", ["武侠", "都市", "历史", "游戏", "诸天无限",
                                    "高武世界", "都市异能", "商战职场"])
def test_folded_brain_and_position_agree_on_channel(genre):
    """Sharing the leaf makes Brain/Position channel disagreement impossible —
    a disagreement surfaces downstream as a false admission conflict."""
    outline = _outline(genre)
    brain = build_brain(outline)
    position = build_position(outline)
    assert brain["genre"]["channel"] == MALE_CHANNEL
    assert position["channel"] == MALE_CHANNEL
    assert brain["genre"]["channel"] == position["channel"]


def test_folded_position_reader_segment_carries_correct_channel():
    """The misroute's real damage: channel is interpolated into reader_segment
    and leans_on, so a wrong channel silently mislabels the audience."""
    position = build_position(_outline("高武世界"))
    assert MALE_CHANNEL in position["reader_segment"]["primary"]
    assert FEMALE_CHANNEL not in position["reader_segment"]["primary"]


def test_authored_channel_respected_by_both_consumers():
    outline = _outline("高武世界", channel="女频")
    assert build_brain(outline)["genre"]["channel"] == "女频"
    assert build_position(outline)["channel"] == "女频"


def test_male_lean_literal_sets_are_gone():
    """Guard: the duplicated hand-synced sets must not come back."""
    from runtime.genesis import brain_gen
    from runtime.positioning import generate
    assert not hasattr(brain_gen, "_MALE_LEAN")
    assert not hasattr(generate, "_MALE_LEAN")


# --------------------------------------------------------------------------- #
# Pacing defaults (cadence)                                                    #
# --------------------------------------------------------------------------- #
def test_cadence_is_genre_differentiated():
    """The regression: cadence was hardcoded 3 for every genre, so a faction-scale
    payoff (王朝争霸) and a personal-scale one (都市) shared one rhythm."""
    assert cadence_for_genre("王朝争霸") > cadence_for_genre("都市")
    assert cadence_for_genre("历史") > cadence_for_genre("游戏")
    # Coarse by design — the data behind these is C-grade, not measured.
    for genre in PRIMARY_GENRES + XUANHUAN_SUBGENRES + URBAN_SUBGENRES:
        assert 3 <= cadence_for_genre(genre) <= 6


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_blank_genre_cadence_degrades_to_old_hardcoded_value(blank):
    assert cadence_for_genre(blank) == DEFAULT_CADENCE == 3


def test_unknown_genre_cadence_preserves_old_behavior():
    """Any genre absent from the table must behave exactly as before this module
    existed — the old code returned a literal 3 for everything."""
    assert cadence_for_genre("完全没听过的类型XYZ") == 3


def test_subgenre_cadence_wins_over_primary_substring():
    """都市异能 must not be routed by the bare 都市 substring if they differ."""
    assert cadence_for_genre("都市异能流") == cadence_for_genre("都市异能")
    assert cadence_for_genre("异术超能") == 4


def test_authored_cadence_always_wins():
    assert resolve_cadence(7, "都市") == 7
    assert resolve_cadence(None, "王朝争霸") == cadence_for_genre("王朝争霸")


@pytest.mark.parametrize("bad", [0, -1, None, "3", 3.5, True, False])
def test_invalid_authored_cadence_falls_back_to_genre_default(bad):
    """outline/qa.py requires a positive int; passing a bad value through would
    only move the failure downstream. bool is rejected despite being an int."""
    assert resolve_cadence(bad, "王朝争霸") == cadence_for_genre("王朝争霸")


def test_outline_builder_emits_genre_keyed_cadence():
    """The consumer: _build_reward_loop used to return a literal 3."""
    from runtime.outline.agents import _build_reward_loop
    assert _build_reward_loop({"genre_signals": ["王朝争霸"]})["cadence_chapters"] == 6
    assert _build_reward_loop({"genre_signals": ["都市"]})["cadence_chapters"] == 3
    # No genre signal => the analyzer's "原创类型" fallback => old behavior.
    assert _build_reward_loop({"genre_signals": []})["cadence_chapters"] == 3


def test_outline_builder_cadence_stays_schema_valid():
    """qa.py requires a positive integer; every table value must satisfy it."""
    from runtime.outline.agents import _build_reward_loop
    for genre in PRIMARY_GENRES + XUANHUAN_SUBGENRES + URBAN_SUBGENRES:
        c = _build_reward_loop({"genre_signals": [genre]})["cadence_chapters"]
        assert isinstance(c, int) and not isinstance(c, bool) and c > 0
