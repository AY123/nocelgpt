from __future__ import annotations

from typing import Optional

from .types import CostMetrics, TokenUsage


class CostCalculator:
    def __init__(self, pricing_table: dict):
        self.pricing_table = pricing_table

    def calculate(self, provider: str, model: str, usage: TokenUsage) -> Optional[CostMetrics]:
        price = self.pricing_table.get(f"{provider}:{model}")
        if not price:
            return None
        input_cost = usage.input_tokens / 1_000_000 * price["input_per_million"]
        output_cost = usage.output_tokens / 1_000_000 * price["output_per_million"]
        return CostMetrics(
            currency=price.get("currency", "USD"),
            input_cost=round(input_cost, 8),
            output_cost=round(output_cost, 8),
            total_cost=round(input_cost + output_cost, 8),
            pricing_version=price["version"],
        )

