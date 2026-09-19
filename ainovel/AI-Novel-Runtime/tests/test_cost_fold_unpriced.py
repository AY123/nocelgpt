"""test_cost_fold_unpriced.py — "没花钱" vs "花了钱但不知道多少"。

根因层的回归测试。此前所有成本折叠点都写 `float(cst.get("total_cost", 0) or 0)`,
`or 0` 把 None 静默变成 0。而 None 有两个来源:

  A. 确定性 stub 跑:没调模型,cost=null 正确且诚实(costs are never faked)
  B. 真实调用但模型未定价:CostCalculator 返回 None(cost.py:14-15),
     此时 live_calls 已 +1、token 用量齐全 —— 钱是真花了的

把 B 折成 0 的后果比报错更危险:total_llm_cost 永远是 0,--budget-limit 永不
触发,熔断器看起来在工作实则完全失效。已发生两次(deepseek-chat 缺键;
92code:gpt-5.6-sol 缺键导致 v12-vs-v13 四臂 A/B 在零预算保护下跑掉 18 元)。

这里钉住:A 行为不变(不伪造成本),B 变得可见(计数 + 告警 + 文案不再谎称免费)。
"""
from __future__ import annotations

from runtime.llm.cost_fold import CostFold, fold_cost

_LIVE_UNPRICED = {
    "provider": "92code",
    "model": "gpt-5.6-sol",
    "token_usage": {"input_tokens": 7964, "output_tokens": 1930, "total_tokens": 9894},
    "cost": None,                      # CostCalculator 对未定价模型的真实返回
}
_LIVE_PRICED = {
    "provider": "deepseek",
    "model": "deepseek-chat",
    "token_usage": {"input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500},
    "cost": {"total_cost": 0.25, "currency": "CNY", "pricing_version": "x"},
}


# --------------------------------------------------------------------------- #
# 情形 A:没有调用 => cost=null 正确,不告警                                    #
# --------------------------------------------------------------------------- #
def test_deterministic_stub_run_is_not_flagged():
    """确定性 stub 没有 llm 块,是真的没花钱 —— 不能误报为"未定价"。"""
    fold = fold_cost([None, {}, None])

    assert fold.total == 0.0
    assert fold.has_cost is False          # => manifest cost 仍为 null
    assert fold.is_understated is False
    assert fold.unpriced_calls == 0
    assert fold.warning() is None


def test_llm_block_without_token_usage_is_not_a_paid_call():
    """有 llm 块但零 token 用量,不算真实付费调用。"""
    fold = fold_cost([{"provider": "p", "model": "m",
                       "token_usage": {"total_tokens": 0}, "cost": None}])

    assert fold.unpriced_calls == 0
    assert fold.warning() is None


# --------------------------------------------------------------------------- #
# 情形 B:真实调用却没有定价 => 必须可见                                        #
# --------------------------------------------------------------------------- #
def test_unpriced_live_call_is_counted_not_silently_zeroed():
    """这就是跑掉 18 元的那个形状:token 用量齐全但 cost 为 None。"""
    fold = fold_cost([_LIVE_UNPRICED])

    assert fold.total == 0.0               # 无法折出金额(不伪造)
    assert fold.has_cost is False
    assert fold.is_understated is True     # 但明确标记"低于真实花费"
    assert fold.unpriced_calls == 1
    warning = fold.warning()
    assert warning is not None
    assert "92code:gpt-5.6-sol" in warning
    assert "熔断" in warning               # 告警必须点出预算保护失效


def test_mixed_priced_and_unpriced_is_understated():
    """最危险的情形:部分定价 => 总额非 0 看似正常,实则静默低估。"""
    fold = fold_cost([_LIVE_PRICED, _LIVE_UNPRICED, _LIVE_PRICED])

    assert fold.total == 0.5               # 只有两次已定价的被计入
    assert fold.has_cost is True           # cost 非 null,看起来正常
    assert fold.priced_calls == 2
    assert fold.unpriced_calls == 1
    assert fold.is_understated is True     # 但低估被标记出来了
    assert fold.warning() is not None


def test_priced_calls_carry_currency_and_version():
    fold = fold_cost([_LIVE_PRICED])

    assert fold.total == 0.25
    assert fold.currency == "CNY"
    assert fold.pricing_version == "x"
    assert fold.is_understated is False
    assert fold.warning() is None


def test_add_returns_the_amount_it_folded():
    """add() 的返回值直接进 chapter_cost,未定价必须返回 0 而不是抛错。"""
    fold = CostFold()

    assert fold.add(_LIVE_PRICED) == 0.25
    assert fold.add(_LIVE_UNPRICED) == 0.0
    assert fold.add(None) == 0.0


# --------------------------------------------------------------------------- #
# 与真实计价表的联动:补上键之后不该再告警                                       #
# --------------------------------------------------------------------------- #
def test_pricing_the_model_clears_the_warning():
    """补上 DEFAULT_PRICING 键后,同一次调用就折得出成本、不再告警。

    这条把"告警"与"修复动作"绑在一起:告警文案指向 DEFAULT_PRICING,
    而补键确实能消除它。
    """
    from runtime.llm.cost import CostCalculator
    from runtime.llm.factory import DEFAULT_PRICING
    from runtime.llm.types import TokenUsage

    usage = TokenUsage(input_tokens=7964, output_tokens=1930, total_tokens=9894)
    cost = CostCalculator(DEFAULT_PRICING).calculate("92code", "gpt-5.6-sol", usage)
    assert cost is not None, "92code:gpt-5.6-sol 应已在 DEFAULT_PRICING 中"

    priced = dict(_LIVE_UNPRICED, cost={"total_cost": cost.total_cost,
                                        "currency": cost.currency,
                                        "pricing_version": cost.pricing_version})
    fold = fold_cost([priced])

    assert fold.is_understated is False
    assert fold.warning() is None
    assert fold.total > 0
