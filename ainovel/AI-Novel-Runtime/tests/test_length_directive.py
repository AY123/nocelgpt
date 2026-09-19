"""test_length_directive.py — P0-3 篇幅失控的上游修正。

实测：市场中位 3166 / p75 3287 字，我们 RUN-00001 中位 5238（1.56x），v12 5427（1.65x）。

两条路先被证据排除，再落这一条：
  1. hygiene 重写 —— 需缩减 36%，低于 deletion-cheat floor（0.8x），每轮都会被判
     gutting 而否决（已由 test_length_cannot_be_hygiene_fixed 固化）。
  2. 单纯加强 prompt 措辞 —— 已失败两次（"严禁超过3900" 仍产出 231-242%）。

所以修在上游：plan 交给生成侧的 directive。相对旧措辞改两处：
  a) 旧的"约 N 字（可上下浮动）"**没有上界** → 给出明确上限。
  b) 旧的只给全章一个总数，而模型逐分镜写 → 给出**每分镜配额**。
     依据：4-beat 章 5128 字 vs 5-beat 5305 字，仅差 176，而超标近 1900 ——
     超长来自每分镜写太长，不是分镜太多。

这些测试锁住行为与非破坏不变量。
"""
from __future__ import annotations

from runtime.chapter_length import (
    LENGTH_CEILING_RATIO,
    length_directive,
    role_length,
)


# --------------------------------------------------------------------------- #
# 非破坏性：无 target 必须完全静默（byte-identical 草稿依赖这一点）              #
# --------------------------------------------------------------------------- #
def test_absent_target_yields_empty_directive():
    for target in (None, 0):
        assert length_directive(target) == ""
        assert length_directive(target, role="advance", beats=4) == ""


# --------------------------------------------------------------------------- #
# a) 必须有明确上界 —— 旧措辞最大的缺陷                                         #
# --------------------------------------------------------------------------- #
def test_directive_states_an_explicit_ceiling():
    d = length_directive(3333)
    assert "上限" in d and str(int(3333 * LENGTH_CEILING_RATIO)) in d
    assert "不得超过" in d


def test_directive_no_longer_invites_drift():
    """旧措辞的『可上下浮动』正是超长的邀请函，不得再出现。"""
    assert "可上下浮动" not in length_directive(3333, role="advance", beats=4)


def test_ceiling_cuts_into_the_measured_overshoot():
    """上限必须真的比实测中位低，否则等于没约束。"""
    ceiling = int(3333 * LENGTH_CEILING_RATIO)
    assert ceiling < 5238, "上限高于 RUN-00001 实测中位，约束无效"
    assert ceiling < 5427, "上限高于 v12 实测中位，约束无效"
    # 但不能紧到低于市场 p75，否则会逼出草草收尾
    assert ceiling > 3287, "上限低于市场 p75，会逼模型砍情节"


# --------------------------------------------------------------------------- #
# b) 每分镜配额 —— 实测指出的真正杠杆                                           #
# --------------------------------------------------------------------------- #
def test_per_beat_budget_appears_when_plan_known():
    d = length_directive(3333, role="advance", beats=4)
    assert "4 个分镜" in d
    assert str(3333 // 4) in d          # 833


def test_per_beat_budget_scales_with_beat_count():
    four = length_directive(3333, role="advance", beats=4)
    five = length_directive(3333, role="advance", beats=5)
    assert str(3333 // 4) in four and str(3333 // 5) in five
    assert four != five


def test_no_plan_degrades_to_whole_chapter_form():
    """没有分镜计划时退化为整章形式，仍带上限——不得因缺计划而丢掉约束。"""
    d = length_directive(3333, role="advance")
    assert "分镜" not in d
    assert "上限" in d


def test_zero_or_negative_beats_degrade_cleanly():
    for beats in (0, -1):
        d = length_directive(3333, role="advance", beats=beats)
        assert "分镜" not in d and "上限" in d


# --------------------------------------------------------------------------- #
# 上限与 role 的关系：实测不支持按 role 放宽                                     #
# --------------------------------------------------------------------------- #
def test_ceiling_is_the_tighter_of_role_band_and_global_ratio():
    """所有 role 的 band_high 都 >1.25，故当前一律落在 1.25。

    实测依据：市场开篇窗口只比全书宽 1.6%（golden3 p75 3409 vs first30 3354），
    没有证据支持按 role 放宽上限。min() 保留，使未来更紧的 role band 仍能生效。"""
    expected = int(3333 * LENGTH_CEILING_RATIO)
    for role in ("opening", "advance", "turn", "hook", None):
        assert role_length(role)["band_high"] >= LENGTH_CEILING_RATIO
        assert str(expected) in length_directive(3333, role=role)


def test_min_chars_floors_are_untouched():
    """min_chars 是 reviewer 的裁决地板，本改动不得移动它（清单 item 2 不破坏硬门）。"""
    assert role_length("opening")["min_chars"] == 900
    assert role_length("advance")["min_chars"] == 700
    assert role_length("turn")["min_chars"] == 800
    assert role_length("hook")["min_chars"] == 600


# --------------------------------------------------------------------------- #
# 确定性 + 接线                                                                #
# --------------------------------------------------------------------------- #
def test_deterministic():
    a = length_directive(3333, role="advance", beats=4)
    b = length_directive(3333, role="advance", beats=4)
    assert a == b


def test_scene_beats_helper_folds_the_plan():
    from runtime.serialize.loop import _scene_beats
    assert _scene_beats({"scenes": [{}, {}, {}, {}]}) == 4
    # 缺计划/空计划 => None => directive 退化为整章形式（保持旧路径）
    assert _scene_beats(None) is None
    assert _scene_beats({}) is None
    assert _scene_beats({"scenes": []}) is None
    assert _scene_beats("not-a-dict") is None


def test_execute_package_accepts_scene_beats():
    """接线自检：参数必须真的存在于生产入口签名上，否则 per-beat 配额永不生效。"""
    import inspect
    from runtime.execution.run import execute_package
    assert "scene_beats" in inspect.signature(execute_package).parameters
