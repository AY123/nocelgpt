"""test_ab_power_design.py — 固化下一轮工艺 A/B 的实验判据（tools/ab_power.py）。

上一轮 v11-vs-v12 的结论只能是 DIRECTIONAL ONLY，两个设计缺陷记在
`ANOVEL_PLAN_CORRECTION.md` §11.3：功效不足、阴性对照无效。`tools/ab_power.py`
把"要多少章"和"谁有资格当对照"变成可计算的，因此它编码的是**实验判据**，
不是一次性脚本——判据必须被钉住，否则下一轮又会凭感觉选 n 和对照。

只测纯统计核心与资格规则：两臂正文导出在 gitignore 里，测试不得依赖它们存在。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

ab_power = pytest.importorskip("ab_power")


# --------------------------------------------------------------------------- #
# 符号检验：钉住"n=10 单特征需 9/10 才显著"这个被反复引用的事实              #
# --------------------------------------------------------------------------- #
def test_sign_test_needs_9_of_10_at_n10():
    """§11.2 的核心论断：n=10 时功效不足是**构造性**的，不是运气不好。"""
    assert ab_power.sign_p(9, 10) < 0.05
    assert ab_power.sign_p(8, 10) > 0.05
    # 上一轮实测的 7/10 与 6/10 远不可能显著——方向对不等于有效。
    assert ab_power.sign_p(7, 10) > 0.05
    assert ab_power.sign_p(6, 10) > 0.05


def test_sign_test_threshold_relaxes_as_n_grows():
    """章数越多，所需胜率越低——这正是加大 n 的收益。"""
    def needed(n):
        return next(k for k in range(n + 1) if ab_power.sign_p(k, n) < 0.05)

    assert needed(10) / 10 == pytest.approx(0.90)
    assert needed(30) / 30 == pytest.approx(0.70)
    assert needed(40) / 40 < needed(20) / 20


def test_sign_p_is_capped_and_symmetric():
    assert ab_power.sign_p(5, 10) == 1.0          # 双尾且封顶，不会 >1
    assert ab_power.sign_p(0, 0) == 1.0           # 全平局 => 不下结论


# --------------------------------------------------------------------------- #
# Wilcoxon：更高功效的来源，以及它拒绝下结论的边界                            #
# --------------------------------------------------------------------------- #
def test_wilcoxon_refuses_to_conclude_below_six_pairs():
    """n<6 时正态近似不可靠，必须返回 1.0 而不是假装算出了 p。"""
    assert ab_power.wilcoxon_p([1.0] * 5) == 1.0
    assert ab_power.wilcoxon_p([]) == 1.0
    assert ab_power.wilcoxon_p([0.0] * 20) == 1.0   # 全平局


def test_wilcoxon_beats_sign_test_on_mixed_data():
    """Wilcoxon 的优势出现在**混合**数据上：大幅改善 + 少数轻微变差。
    符号检验只数正负（7/10 => p=0.34，判不显著），Wilcoxon 看到"赢得多、输得少"
    因而给出 p<0.05。上一轮四个特征全是这个形状（胜 6-7/10 但中位改善明显），
    所以主检验选 Wilcoxon 是有据的，不是偏好。
    """
    deltas = [0.9, 0.8, -0.05, 0.7, 0.85, -0.03, 0.95, 0.75, 0.88, -0.04]
    wins = sum(1 for x in deltas if x > 0)
    assert wins == 7
    assert ab_power.sign_p(wins, len(deltas)) > 0.05      # 符号检验判不显著
    assert ab_power.wilcoxon_p(deltas) < 0.05             # Wilcoxon 抓到了


def test_sign_test_is_not_universally_weaker():
    """诚实标注反向情形：差值**一致同向**时符号检验已达其最小可能 p，
    而这里的 Wilcoxon 是正态近似（小样本偏保守），反而更大。
    所以设计里 Wilcoxon 为主、符号检验为稳健性附证——两者都报，不互相替代。"""
    unanimous = [0.5, 0.4, 0.6, 0.3, 0.7, 0.45, 0.55, 0.35]
    n = len(unanimous)
    assert ab_power.sign_p(n, n) < ab_power.wilcoxon_p(unanimous)


# --------------------------------------------------------------------------- #
# 自助法功效：单调性 + 确定性 + 无效应时不虚报                                #
# --------------------------------------------------------------------------- #
def test_power_rises_with_n_for_a_real_effect():
    deltas = [0.4, 0.5, -0.1, 0.6, 0.3, 0.45, -0.05, 0.7, 0.35, 0.55]
    p10 = ab_power.bootstrap_power(deltas, 10, "wilcoxon", reps=600)
    p50 = ab_power.bootstrap_power(deltas, 50, "wilcoxon", reps=600)
    assert p50 > p10


def test_power_stays_near_alpha_when_there_is_no_effect():
    """对称噪声（无真实效应）下检出率应贴近 alpha，否则功效估计本身是坏的。"""
    deltas = [0.5, -0.5, 0.3, -0.3, 0.4, -0.4, 0.2, -0.2, 0.6, -0.6]
    power = ab_power.bootstrap_power(deltas, 30, "wilcoxon", reps=1200)
    assert power < 0.20


def test_bootstrap_is_deterministic_given_the_seed():
    """同输入同结论——实验设计必须可复现，不能每次跑出不同的所需章数。"""
    deltas = [0.4, 0.5, -0.1, 0.6, 0.3, 0.45, -0.05, 0.7, 0.35, 0.55]
    a = ab_power.bootstrap_power(deltas, 25, "sign", reps=500)
    b = ab_power.bootstrap_power(deltas, 25, "sign", reps=500)
    assert a == b


# --------------------------------------------------------------------------- #
# McNemar：H2（元指代）必须用它，因为逐章计数是零膨胀的                        #
# --------------------------------------------------------------------------- #
def test_wilcoxon_collapses_on_the_real_zero_inflated_leak_counts():
    """这是 H2 换检验的**根因**，不是风格选择。

    实测 v11 逐章元指代 = [0,0,2,0,1,3,0,0,6,0]，v12 = [0,...,3,0]。配对差值里
    有 6 个 0-0 平局，签名秩把平局丢掉后只剩 4 对 < 6，wilcoxon_p 只能返回 1.0
    拒绝下结论。用逐章计数做 H2 等于自断功效。
    """
    v11 = [0, 0, 2, 0, 1, 3, 0, 0, 6, 0]
    v12 = [0, 0, 0, 0, 0, 0, 0, 0, 3, 0]
    diffs = [a - b for a, b in zip(v11, v12)]
    assert sum(1 for x in diffs if x != 0) < 6
    assert ab_power.wilcoxon_p(diffs) == 1.0


def test_mcnemar_uses_only_discordant_pairs():
    """一致对（两臂都有 / 都没有）不携带信息；全一致 => 不下结论。"""
    assert ab_power.mcnemar_p(0, 0) == 1.0
    # 完全一边倒的不一致对 => 显著
    assert ab_power.mcnemar_p(9, 0) < 0.05
    # 对称不一致 => 无证据
    assert ab_power.mcnemar_p(4, 4) == 1.0


def test_mcnemar_is_symmetric_in_its_two_directions():
    assert ab_power.mcnemar_p(7, 2) == ab_power.mcnemar_p(2, 7)


def test_h2_needs_more_chapters_than_h1():
    """本设计的关键结论：总章数由 H2 决定，不是 H1。

    H1 在 45 章/臂已够（dash 25 / simile 40 / dialogue 45），但 H2 在
    35%→10% 的乐观情形下 45 章只有 ~0.77 功效，需 60 章才到 ~0.87。
    按更严的那一项定 n，否则 H2 注定测不出来。

    注意（2026-08-01 实测更正）：本测试断言的是 `power_mcnemar` 的**单调性**，
    0.35 只是输入参数，这部分数学依然成立。但"n=60 即可"这个**设计结论已被
    真实 A/B 推翻**：35% 基线是被污染的正则算出来的（`第N章` 同时命中章节标题
    与章末标记 `（第一章 完）`），真实章级泄漏率只有 4.6%（3/65）。按真实基线
    达 80% 功效需 n≈200 章级配对。详见 docs/craft-ab-v12-v13-pooled.json。
    """
    p45 = ab_power.power_mcnemar(45, 0.35, 0.10, reps=1200)
    p60 = ab_power.power_mcnemar(60, 0.35, 0.10, reps=1200)
    assert p45 < ab_power.TARGET_POWER
    assert p60 >= ab_power.TARGET_POWER
    assert p60 > p45


def test_mcnemar_power_falls_as_the_effect_shrinks():
    """目标降幅越小越难测——这解释了为什么 35%→20% 在任何可行章数都不现实。"""
    strong = ab_power.power_mcnemar(60, 0.35, 0.10, reps=1000)
    weak = ab_power.power_mcnemar(60, 0.35, 0.20, reps=1000)
    assert strong > weak


def test_required_n_returns_none_when_no_n_suffices():
    """高方差特征（如 opening_simile）在任何可行章数都到不了 80%：必须如实返回
    None，好让它被降级为观察项，而不是给实验设一个必输条件。"""
    noise = [0.5, -0.5, 0.3, -0.3, 0.4, -0.4, 0.2, -0.2, 0.6, -0.6]
    assert ab_power.required_n(noise, "sign", cap=40) is None
    assert ab_power.required_n([], "sign", cap=40) is None


# --------------------------------------------------------------------------- #
# 对照资格规则：本轮最容易出错、也最值得钉住的一条                            #
# --------------------------------------------------------------------------- #
def test_rest_simile_is_excluded_as_a_constrained_sibling():
    """density.rest_simile_per_1000 基数高(20)又在带外，筛查会把它误判为合格对照。
    但 v12 的比喻约束原文是 "SPARSE: about one per 1000 characters ACROSS THE
    CHAPTER"，并点明 "what they never do is sustain that density through the whole
    chapter" —— 正文段同样受约束。拿受约束的特征当对照会伪造出"对照也动了"的
    结论，直接推翻整轮归因。"""
    assert "density.rest_simile_per_1000" in ab_power.CONSTRAINED_SIBLINGS
    assert "density.rest_simile_per_1000" not in ab_power.TARGETED


def test_size_derived_features_are_not_eligible_controls():
    """篇幅一动就同步拉动它们，所以不能独立当对照——下一轮恰好要改篇幅。"""
    for feature in ("ai_taste.total_chars", "density.total_chars",
                    "length.total_chars", "ai_taste.sentence_count"):
        assert feature in ab_power.SIZE_DERIVED


def test_control_eligibility_demands_both_cardinality_and_pressure():
    """§11.3 缺陷①的根因：上一轮只看了"未被约束"，没看"有没有移动空间"。
    两个条件都必须在规则里。"""
    assert ab_power.MIN_CARDINALITY >= 6
    assert ab_power.TARGET_POWER == 0.80
    assert ab_power.ALPHA == 0.05


def test_targeted_features_carry_an_explicit_defect_direction():
    """缺陷方向决定配对差值的符号；缺了它就无法判断"改善"是哪一侧。"""
    assert ab_power.TARGETED["density.dialogue_ratio"] == "below"
    for feature, side in ab_power.TARGETED.items():
        assert side in ("above", "below"), feature
