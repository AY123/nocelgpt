"""test_92code_pricing.py — 92code:gpt-5.6-sol 的计价键与熔断恢复。

这个键缺失时的后果不是"成本未知"而更糟:CostCalculator 对未知模型返回 None
(cost.py:14-15),而 loop.py 的 `float(cst.get("total_cost", 0) or 0)` 把 None
折成 0,于是 total_llm_cost 永远停在 0,--budget-limit 永不触发 ——
分层熔断器对该 provider 完全失效。2026-08-01 的 v12-vs-v13 四臂 A/B 就是
这样在无预算保护下跑掉 18 元的。

这里钉住三件事:
  1. 键存在,且按该轮真实用量能复现实际账单(18.00 元,容差 2%)
  2. 计价后熔断器恢复作用(费用能累加、能触发)
  3. 反推价的已知局限:CostCalculator 没有缓存档
"""
from __future__ import annotations

from runtime.llm.cost import CostCalculator
from runtime.llm.factory import DEFAULT_PRICING
from runtime.llm.types import TokenUsage
from runtime.serialize.cost_breaker import check_budget

KEY = "92code:gpt-5.6-sol"

# 2026-08-01 v12-vs-v13 四臂 A/B(132 章)的实测总用量。
AB_INPUT_TOKENS = 1_169_310      # 含缓存命中
AB_CACHED_TOKENS = 1_030_618     # 其中 88% 是缓存命中
AB_OUTPUT_TOKENS = 283_463
AB_ACTUAL_BILL_CNY = 18.00       # 用户确认的实际计费
AB_CHAPTERS = 132


def test_92code_pricing_key_exists():
    """缺键 => 成本折 None => 熔断失效。这个键是预算保护的前提。"""
    assert KEY in DEFAULT_PRICING, (
        "缺少 92code:gpt-5.6-sol 计价键 => cost=None => loop.py 折成 0 "
        "=> --budget-limit 永不触发"
    )
    price = DEFAULT_PRICING[KEY]
    assert price["currency"] == "CNY"
    assert price["input_per_million"] > 0
    assert price["output_per_million"] > 0


def test_pricing_reproduces_the_real_ab_bill():
    """按真实用量折出的成本必须复现实际账单(容差 2%)。

    这是这个键唯一的校准依据 —— 它不是官方价目表,而是从账单反推的
    混合有效价,所以必须钉住"能复现那张账单"。
    """
    calc = CostCalculator(DEFAULT_PRICING)
    usage = TokenUsage(
        input_tokens=AB_INPUT_TOKENS,
        output_tokens=AB_OUTPUT_TOKENS,
        total_tokens=AB_INPUT_TOKENS + AB_OUTPUT_TOKENS,
    )
    cost = calc.calculate("92code", "gpt-5.6-sol", usage)

    assert cost is not None, "已加键却折出 None"
    assert cost.currency == "CNY"
    rel_err = abs(cost.total_cost - AB_ACTUAL_BILL_CNY) / AB_ACTUAL_BILL_CNY
    assert rel_err < 0.02, (
        f"折出 {cost.total_cost:.2f} 元,实际 {AB_ACTUAL_BILL_CNY} 元,"
        f"相对误差 {rel_err:.1%} 超过 2%"
    )


def test_per_chapter_cost_is_the_planning_number():
    """每章成本是唯一零假设的运营数字(总额/章数),用于预算下一轮。"""
    calc = CostCalculator(DEFAULT_PRICING)
    usage = TokenUsage(
        input_tokens=AB_INPUT_TOKENS,
        output_tokens=AB_OUTPUT_TOKENS,
        total_tokens=AB_INPUT_TOKENS + AB_OUTPUT_TOKENS,
    )
    per_chapter = calc.calculate("92code", "gpt-5.6-sol", usage).total_cost / AB_CHAPTERS

    # 实测 ~0.1364 元/章;比 deepseek-v4-pro(~0.0305)贵约 4.5 倍
    assert 0.12 < per_chapter < 0.16, f"每章 {per_chapter:.4f} 元,偏离实测区间"


def test_breaker_actually_trips_once_cost_is_priced():
    """计价恢复后,熔断器必须能真的拦住 —— 这是补键的实际目的。

    模拟 loop.py 的累加:逐章把折出的成本加进 total,一旦触及预算就停。
    """
    calc = CostCalculator(DEFAULT_PRICING)
    # 单章平均用量
    per_ch = TokenUsage(
        input_tokens=AB_INPUT_TOKENS // AB_CHAPTERS,
        output_tokens=AB_OUTPUT_TOKENS // AB_CHAPTERS,
        total_tokens=(AB_INPUT_TOKENS + AB_OUTPUT_TOKENS) // AB_CHAPTERS,
    )
    chapter_cost = calc.calculate("92code", "gpt-5.6-sol", per_ch).total_cost
    assert chapter_cost > 0, "单章成本为 0 => 熔断仍然失效"

    budget = 1.0
    total = 0.0
    produced = 0
    for _ in range(AB_CHAPTERS):
        if check_budget(project_limit=budget, project_spent=total).any_tripped:
            break
        total += chapter_cost
        produced += 1

    assert produced < AB_CHAPTERS, "跑满全部章节 => 预算未生效"
    assert total >= budget, "停下时未达预算 => 触发逻辑异常"
    # 1 元预算下约能跑 7-8 章
    assert 5 <= produced <= 10, f"1 元预算跑了 {produced} 章,偏离预期"


def test_pricing_has_no_cache_tier_documented_limitation():
    """如实记录局限:CostCalculator 没有缓存档。

    cost.py:16 用全部 input_tokens 乘 input_per_million,所以这里的
    input_per_million 是**含 88% 缓存命中的混合有效价**。若某轮缓存命中率
    显著低于 88%,折出的成本会低估。这条测试的作用是让该假设可见 ——
    若将来给 CostCalculator 加了缓存档,这里会红,提醒同时重算该键。
    """
    calc = CostCalculator(DEFAULT_PRICING)
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=0, total_tokens=1_000_000)
    cost = calc.calculate("92code", "gpt-5.6-sol", usage)

    # 全部输入按同一档计价,不区分是否缓存命中
    assert cost.input_cost == DEFAULT_PRICING[KEY]["input_per_million"]
    assert AB_CACHED_TOKENS / AB_INPUT_TOKENS > 0.85, "校准依据的缓存命中率约 88%"
    assert "derived-from-billing" in DEFAULT_PRICING[KEY]["version"], (
        "version 必须标明这是反推价,而非官方价目表"
    )
