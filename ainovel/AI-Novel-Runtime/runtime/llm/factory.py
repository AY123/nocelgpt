from __future__ import annotations

import os
from pathlib import Path

from .adapters.claude import ClaudeAdapter
from .adapters.deepseek import DeepSeekAdapter
from .adapters.gemini import GeminiAdapter
from .adapters.local import LocalAdapter
from .adapters.mock import MockAdapter
from .adapters.openai_compatible import OpenAICompatibleAdapter
from .adapters.openai_responses import OpenAIResponsesAdapter
from .client import ManagedLLMClient
from .cost import CostCalculator
from .fallback import FallbackLLMClient
from .replay import ReplayStore


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
CC_VIBE_OPENAI_DEFAULT_BASE_URL = "https://claudecode.top/v1"
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
# Kimi (Moonshot AI) — OpenAI-compatible Chat Completions API.
# base_url per platform.kimi.com/docs/api/overview; auth is Bearer <key>.
KIMI_BASE_URL = "https://api.moonshot.cn/v1"
# 92code — codex-style relay exposing ONLY the OpenAI Responses API
# (/v1/responses works, /v1/chat/completions is 404). wire_api="responses".
CODE92_BASE_URL = "https://claudecode.top/v1"


DEFAULT_PRICING = {
    # Real DeepSeek pricing (CNY per million tokens), from the official pricing
    # page as of 2026-07. Keep unknown models cost=None instead of guessing.
    # The CostCalculator has no cache-hit tier, so input_per_million uses the
    # cache-MISS price (the conservative default). Cache-hit input is far cheaper
    # (v4-flash 0.02 / v4-pro 0.025 per million) — recorded here for reference:
    #   deepseek-v4-flash: input hit 0.02 / miss 1 / output 2  (CNY/M)
    #   deepseek-v4-pro  : input hit 0.025 / miss 3 / output 6  (CNY/M)
    "deepseek:deepseek-v4-flash": {
        "input_per_million": 1.0,
        "output_per_million": 2.0,
        "currency": "CNY",
        "version": "deepseek-official-2026-07",
    },
    "deepseek:deepseek-v4-pro": {
        "input_per_million": 3.0,
        "output_per_million": 6.0,
        "currency": "CNY",
        "version": "deepseek-official-2026-07",
    },
    # deepseek-chat is the standard chat alias used by the serial production runs.
    # Priced at the v4-pro tier (user-confirmed 2026-07). Without this entry the
    # CostCalculator returns None for every live chapter, so run-manifest folds
    # cost=null despite live_calls>0 (observed in RUN-00025/27). Aliased, not
    # guessed — same tier as v4-pro above.
    "deepseek:deepseek-chat": {
        "input_per_million": 3.0,
        "output_per_million": 6.0,
        "currency": "CNY",
        "version": "deepseek-official-2026-07",
    },
    # 92code relay 的 gpt-5.6-sol。**这不是官方价目表,是从真实账单反推的
    # 混合有效价** —— 用户确认 2026-08-01 的 v12-vs-v13 四臂 A/B 实际计费
    # 18.00 元,该轮实测用量:输入 1,169,310(其中 1,030,618 = 88% 是缓存命中)、
    # 输出 283,463。按下面两个价复现 18.04 元(误差 0.2%)。
    #
    # 为什么把缓存命中也按同一档计价:CostCalculator 没有缓存档
    # (cost.py:16 直接用 usage.input_tokens 全额乘 input_per_million),
    # 所以这里的 input_per_million 必须是**含缓存的混合有效价**,而不是
    # 官方的 cache-miss 价。这也意味着:若某轮的缓存命中率显著偏离 88%,
    # 折出的成本会有偏差 —— 缓存命中率越低则低估。真正的修法是给
    # CostCalculator 加缓存档,那要改 LLMResponse 的成本契约,单独做。
    #
    # 不加这个键的后果不是"成本未知"而更糟:loop.py:862 把 None 折成 0,
    # 于是 total_llm_cost 永远是 0,--budget-limit 永不触发 —— 熔断器对本
    # provider 完全失效。这一轮就是这样在无预算保护下跑掉 18 元的。
    "92code:gpt-5.6-sol": {
        "input_per_million": 5.25,
        "output_per_million": 42.0,
        "currency": "CNY",
        "version": "92code-derived-from-billing-2026-08-01",
    },
}


def _openai_sdk_client(*, api_key: str, base_url: str, trust_env: bool = True):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI-compatible providers require the OpenAI SDK. "
            "Install runtime dependencies with: pip install -r requirements.txt"
        ) from exc
    # When trust_env is disabled, force httpx to ignore ambient proxy vars.
    # This is useful for providers that must bypass local proxy interception.
    if not trust_env:
        import httpx

        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.Client(trust_env=False),
        )
    return OpenAI(api_key=api_key, base_url=base_url)


def _managed(adapter, *, replay_store=None):
    return ManagedLLMClient(
        adapter,
        replay_store=replay_store,
        cost_calculator=CostCalculator(DEFAULT_PRICING),
    )


def _normalize_openai_compatible_base_url(base_url: str | None, default: str) -> str:
    value = (base_url or default).rstrip("/")
    if not value.endswith("/v1"):
        value = f"{value}/v1"
    return value


def create_llm_client(provider: str, *, replay_dir: str | Path | None = None):
    if "," in provider:
        return FallbackLLMClient([
            (p.strip(), create_llm_client(p.strip(), replay_dir=replay_dir))
            for p in provider.split(",")
            if p.strip()
        ])
    replay_store = ReplayStore(replay_dir) if replay_dir else None
    if provider == "mock":
        adapter = MockAdapter(os.environ.get("ANES_MOCK_LLM_TEXT", "Mock draft generated for CI."))
        return _managed(adapter, replay_store=replay_store)
    if provider == "deepseek":
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required for --model-provider deepseek")
        adapter = DeepSeekAdapter(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        return _managed(adapter, replay_store=replay_store)
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for --model-provider openai")
        adapter = OpenAICompatibleAdapter(
            provider="openai",
            client=_openai_sdk_client(api_key=api_key, base_url=OPENAI_BASE_URL),
        )
        return _managed(adapter, replay_store=replay_store)
    if provider == "cc-vibe-openai":
        api_key = os.environ.get("CC_VIBE_OPENAI_AUTH_TOKEN")
        if not api_key:
            raise RuntimeError(
                "CC_VIBE_OPENAI_AUTH_TOKEN is required for --model-provider cc-vibe-openai"
            )
        base_url = _normalize_openai_compatible_base_url(
            os.environ.get("CC_VIBE_OPENAI_BASE_URL"),
            CC_VIBE_OPENAI_DEFAULT_BASE_URL,
        )
        adapter = OpenAICompatibleAdapter(
            provider="cc-vibe-openai",
            client=_openai_sdk_client(api_key=api_key, base_url=base_url),
        )
        return _managed(adapter, replay_store=replay_store)
    if provider == "kimi":
        # Kimi (Moonshot AI): OpenAI-compatible, so reuse the same adapter as
        # openai with the Moonshot base_url. Key from MOONSHOT_API_KEY (the doc's
        # name) or KIMI_API_KEY. The model id (e.g. kimi-k3) is passed at call
        # time via --model-id; unknown models fold cost=None (no guessed pricing).
        api_key = os.environ.get("MOONSHOT_API_KEY") or os.environ.get("KIMI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "MOONSHOT_API_KEY (or KIMI_API_KEY) is required for --model-provider kimi")
        adapter = OpenAICompatibleAdapter(
            provider="kimi",
            client=_openai_sdk_client(api_key=api_key, base_url=KIMI_BASE_URL),
        )
        return _managed(adapter, replay_store=replay_store)
    if provider == "92code":
        # codex-style relay exposing ONLY the Responses API. Uses the Responses
        # adapter (not chat.completions, which 404s here). Key from CODE92_API_KEY.
        # reasoning effort + store map from the codex config (model_reasoning_effort
        # / disable_response_storage). Model defaults to CODE92_MODEL
        # (gpt-5.6-sol) when the CLI --model-id is omitted.
        api_key = os.environ.get("CODE92_API_KEY")
        if not api_key:
            raise RuntimeError("CODE92_API_KEY is required for --model-provider 92code")
        adapter = OpenAIResponsesAdapter(
            provider="92code",
            client=_openai_sdk_client(api_key=api_key, base_url=CODE92_BASE_URL),
            reasoning_effort=os.environ.get("CODE92_REASONING_EFFORT", "xhigh"),
            store=os.environ.get("CODE92_STORE", "false").lower() == "true",
        )
        return _managed(adapter, replay_store=replay_store)
    if provider == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
        if not api_key and not auth_token:
            raise RuntimeError(
                "ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN) is required for --model-provider claude"
            )
        base_url = os.environ.get("ANTHROPIC_BASE_URL")
        model = os.environ.get("ANTHROPIC_MODEL")
        # Direct transport is the reliable default for judge calls. Set this
        # to true only when the Anthropic endpoint explicitly requires a proxy.
        trust_env = os.environ.get("ANTHROPIC_TRUST_ENV", "false").lower() in {
            "1", "true", "yes", "on"
        }
        adapter = ClaudeAdapter(
            api_key=api_key,
            auth_token=None if api_key else auth_token,
            base_url=base_url,
            model=model,
            trust_env=trust_env,
        )
        return _managed(adapter, replay_store=replay_store)
    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is required for --model-provider gemini")
        return _managed(GeminiAdapter(api_key=api_key), replay_store=replay_store)
    if provider == "local":
        base_url = os.environ.get("OLLAMA_BASE_URL", OLLAMA_BASE_URL)
        return _managed(LocalAdapter(base_url=base_url), replay_store=replay_store)
    raise RuntimeError(f"unsupported LLM provider {provider!r}")
