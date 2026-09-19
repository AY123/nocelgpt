"""test_replay_reprices_cost.py — a replayed response is priced against the
CURRENT pricing table, not frozen at whatever the table held when it was cached.

Real bug (RUN-00028): the run-manifest folded cost=null even after deepseek-chat
was added to DEFAULT_PRICING, because ManagedLLMClient.generate returned the
cached response BEFORE the cost step. The 33ch replay cache stored cost=null
(cached when the model had no pricing entry), so every replayed chapter re-read
that stale null. Cost is a pure function of cached tokens times the live pricing
table — not part of the replay key or the draft content_hash — so a cache hit
must re-price. This locks the live and replay paths to the same pricing behavior.
"""
from __future__ import annotations

from dataclasses import replace

from runtime.llm.client import ManagedLLMClient
from runtime.llm.cost import CostCalculator
from runtime.llm.replay import ReplayStore
from runtime.llm.types import (LLMRequest, PromptMessage, PromptProvenance,
                               LLMResponse, TokenUsage, TemperatureContract)
from runtime.llm.adapters.openai_compatible import openai_model_pin

_PRICING = {
    "deepseek:deepseek-chat": {
        "input_per_million": 3.0,
        "output_per_million": 6.0,
        "currency": "CNY",
        "version": "test-2026-07",
    },
}


def _request():
    return LLMRequest(
        request_id="R-1",
        capability="ChapterDraft",
        messages=[PromptMessage("system", "sys"), PromptMessage("user", "写一章")],
        model_pin=openai_model_pin(provider="deepseek", model="deepseek-chat",
                                   api_base="https://api.deepseek.com"),
        temperature=TemperatureContract(temperature=0.7, top_p=None),
        timeout_seconds=120.0,
        max_output_tokens=4000,
        prompt_provenance=PromptProvenance(
            prompt_id="chapter-draft", prompt_hash="sha256:abc",
            template_id="chapter-draft", template_version="1.0.0",
            package_hash="sha256:pkg", derived_from=["CHR-00001@v1"],
            rendered_at="t1"),
        metadata={},
    )


def _null_cost_response(request):
    """A response as it was cached BEFORE the model had a pricing entry."""
    return LLMResponse(
        request_id=request.request_id,
        provider="deepseek",
        model="deepseek-chat",
        text="正文……",
        finish_reason="stop",
        token_usage=TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000,
                               total_tokens=2_000_000),
        cost=None,                       # stale: cached when pricing was absent
        latency_ms=100,
        response_hash="sha256:body",
        provider_request_id=None,
        replay_ref=None,
    )


class _NeverCalledAdapter:
    provider = "deepseek"

    def generate(self, request):  # pragma: no cover - must not run on a cache hit
        raise AssertionError("adapter.generate must not be called on a replay hit")


def test_replay_hit_reprices_a_stale_null_cost(tmp_path):
    store = ReplayStore(tmp_path)
    req = _request()
    # Seed the cache with a response that recorded cost=null.
    store.put(req, _null_cost_response(req))

    client = ManagedLLMClient(_NeverCalledAdapter(), replay_store=store,
                              cost_calculator=CostCalculator(_PRICING))
    response = client.generate(req)

    # Served from cache (adapter never called), yet cost is recomputed against
    # the current table: 1M input * 3 + 1M output * 6 = 9.0 CNY.
    assert response.cost is not None, "replayed response must be re-priced"
    assert response.cost.currency == "CNY"
    assert response.cost.total_cost == 9.0
    assert response.replay_ref is not None


def test_replay_hit_without_calculator_leaves_cost_untouched(tmp_path):
    store = ReplayStore(tmp_path)
    req = _request()
    store.put(req, _null_cost_response(req))
    client = ManagedLLMClient(_NeverCalledAdapter(), replay_store=store,
                              cost_calculator=None)
    response = client.generate(req)
    assert response.cost is None
