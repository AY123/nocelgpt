"""cost_fold.py — 折叠 LLM 成本时区分"没花钱"与"花了钱但不知道多少"。

这是两起同类事故的根因层。此前所有折叠点都写成:

    cost_total += float(cst.get("total_cost", 0) or 0)

`or 0` 把 `None` 静默变成 `0`。而 `None` 有两个完全不同的来源:

  A. **确定性 stub 跑**:根本没调模型,没有成本元数据。
     cost=null 是正确且诚实的("costs are never faked")。
  B. **真实调用但模型未定价**:`CostCalculator.calculate` 对
     pricing_table 里没有的 `provider:model` 返回 None(cost.py:14-15),
     此时 live_calls 已 +1、token 用量齐全 —— 钱是真花了的。

在 B 情形下把 None 折成 0,后果比报错更危险:`total_llm_cost` 永远停在 0,
`--budget-limit` 永不触发,熔断器看起来在工作实则完全失效。已发生两次:
  * deepseek-chat 缺键 → RUN-00025/27 全程 cost=null
  * 92code:gpt-5.6-sol 缺键 → v12-vs-v13 四臂 A/B 在零预算保护下跑掉 18 元

本模块不改变 A 的行为(仍然 cost=null,不伪造),只让 B 变得**可见**:
折叠时同时数出"有真实调用却没有成本"的次数,让上层能告警。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass
class CostFold:
    """一次成本折叠的累计结果 + 未定价调用的计数。"""

    total: float = 0.0
    currency: Optional[str] = None
    pricing_version: Optional[str] = None
    priced_calls: int = 0
    #: 有真实 LLM 调用(token 用量非空)但成本缺失的次数 —— 情形 B。
    unpriced_calls: int = 0
    #: 未定价的 provider:model,用于告警文案。
    unpriced_models: list[str] = field(default_factory=list)

    @property
    def has_cost(self) -> bool:
        """是否折出过任何真实成本(决定 manifest 的 cost 是否为 null)。"""
        return self.priced_calls > 0

    @property
    def is_understated(self) -> bool:
        """累计值是否低于真实花费 —— 即存在未定价的真实调用。"""
        return self.unpriced_calls > 0

    def warning(self) -> Optional[str]:
        """给人看的告警;无未定价调用时返回 None。"""
        if not self.unpriced_calls:
            return None
        models = ", ".join(sorted(set(self.unpriced_models))) or "unknown model"
        return (
            f"{self.unpriced_calls} 次真实 LLM 调用没有定价({models})"
            f" —— 累计成本 {self.total:.6f} 低于真实花费,预算熔断在这些调用上无效。"
            f" 请在 runtime/llm/factory.py 的 DEFAULT_PRICING 补上对应键。"
        )

    def add(self, llm: Optional[Mapping[str, Any]]) -> float:
        """折入一次调用的 llm 元数据块,返回本次计入的金额。

        `llm` 是产物 `produced_by.llm`(或 manifest 的 chapters[].llm)。
        None / 空 => 情形 A(没有调用),不计数、不告警。
        """
        if not llm:
            return 0.0
        usage = llm.get("token_usage") or {}
        called = any(
            int(usage.get(k, 0) or 0) > 0
            for k in ("total_tokens", "total", "input_tokens", "input",
                      "output_tokens", "output")
        )
        cost = llm.get("cost") or {}
        raw = cost.get("total_cost")

        if raw is None:
            # 有 token 用量却没有成本 => 情形 B,真花了钱但不知道多少。
            if called:
                self.unpriced_calls += 1
                model = f"{llm.get('provider') or '?'}:{llm.get('model') or '?'}"
                self.unpriced_models.append(model)
            return 0.0

        amount = float(raw)
        self.total += amount
        self.priced_calls += 1
        if cost.get("currency"):
            self.currency = cost["currency"]
        if cost.get("pricing_version"):
            self.pricing_version = cost["pricing_version"]
        return amount


def fold_cost(llm_blocks) -> CostFold:
    """便捷入口:折叠一串 llm 元数据块。"""
    fold = CostFold()
    for block in llm_blocks:
        fold.add(block)
    return fold
