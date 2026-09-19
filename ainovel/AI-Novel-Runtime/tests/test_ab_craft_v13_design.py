"""test_ab_craft_v13_design.py — v13 A/B runner structure and invariants.

This is a structural test for the new `tools/ab_craft_v13.py` experiment runner.
It does not require chapter exports to exist; it only pins the design-level
contract so the runner stays aligned with the v13 experiment framing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

ab_craft_v13 = pytest.importorskip("ab_craft_v13")


def test_v13_runner_uses_v12_as_baseline_and_v13_as_experiment():
    assert ab_craft_v13.DEFAULT_ARM_A.name == "AB-craft-v12"
    assert ab_craft_v13.DEFAULT_ARM_B.name == "AB-craft-v13"
    assert ab_craft_v13.DEFAULT_OUT.name == "craft-ab-v12-v13-report.json"


def test_craft_texture_features_are_controls_not_v13_targets():
    """破折号/比喻/对白是 v12 的约束,不是 v13 的定向指标。

    此测试原来断言这三项属于 TARGETED,那编码了一个**错误契约**:
    AI-Novel-Standard/contracts/prompts/chapter-draft.v13.prompt.yaml 相对 v12
    的 diff 只有 8 行,内容是"不得把章号/大纲/提示词等生产元信息写进故事世界"
    的防泄漏指令。v13 ⊃ v12,所以这三项工艺约束在两臂**同等施加** ——
    把它们当作 v13 的定向指标,等于给 v13 记 v12 的功劳。

    正确划分:v13 唯一新增的是元指代防泄漏(单独按章级二元 + 精确 McNemar
    检验),这三项未被新增触及 → 天然对照。若对照也发生显著系统性移动,
    说明两臂差异不能干净归因于防泄漏约束。
    """
    for feature in ("ai_taste.dash_aside_per_1000",
                    "density.simile_per_1000",
                    "density.dialogue_ratio"):
        assert feature in ab_craft_v13.CONTROL, feature
        assert feature not in ab_craft_v13.TARGETED, feature


def test_v13_meta_leak_is_tested_as_chapter_level_binary():
    """H2 必须用章级二元 + 精确 McNemar,不能用计数符号检验。

    计数是零膨胀的(多数章 0 次、少数章 2-6 次),签名秩在这种分布上失效。
    早先 runner 里 mc_nemar_p **定义了却从未被调用**,H2 实际跑的是
    sign_p(计数),这正是本仓库反复出现的 built≠live。
    """
    from ab_stats import exact_mcnemar

    # 一致配对不携带信息
    assert exact_mcnemar(0, 0) == 1.0
    # c=0 时需 b>=6 才可能显著,这是判据的现实约束
    assert exact_mcnemar(5, 0) > ab_craft_v13.ALPHA
    assert exact_mcnemar(6, 0) < ab_craft_v13.ALPHA

    from meta_leak import has_meta_leak

    # 真泄漏:句中把章号当世界内时间标记
    assert has_meta_leak("那股在第一章末吞进体内的曜能还没压住。") is True
    # 格式产物不算泄漏(标题行 / 章末标记)
    assert has_meta_leak("# 第二十一章\n\n曜压如山。") is False
    assert has_meta_leak("他的手停在门把上。\n\n（第一章 完）") is False


def test_v13_runner_preserves_natural_control_policy():
    assert "ai_taste.anaphora_run" in ab_craft_v13.CONTROL
    assert "ai_taste.sentence_length_cv" in ab_craft_v13.CONTROL
    assert ab_craft_v13.MIN_CARDINALITY >= 6
    assert ab_craft_v13.ALPHA == 0.05
