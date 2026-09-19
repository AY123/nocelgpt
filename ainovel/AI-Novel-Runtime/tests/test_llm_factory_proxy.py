"""Regression: the DeepSeek client must ignore ambient proxy env vars.

DeepSeek is a China-hosted API that must be reached directly. When a shell
proxy (http_proxy/https_proxy/all_proxy, e.g. Clash on 127.0.0.1:7897) is set,
the transport would otherwise route the request through it and the proxy rule
rejects it with a 403.

Two transports have carried this contract:
- the pre-curl OpenAI-SDK client used a trust_env=False httpx.Client;
- the current DeepSeekAdapter shells out to curl and must pass --noproxy '*'.
The curl migration (209b4d2) silently dropped the bypass; it is restored and
pinned here.
"""
from __future__ import annotations

from dataclasses import replace
import httpx
import json
import pytest
from types import SimpleNamespace

from runtime.llm.adapters.claude import ClaudeAdapter
from runtime.llm.adapters.openai_compatible import openai_model_pin
from runtime.llm.adapters.openai_responses import _response_text
from runtime.llm.errors import PermanentLLMError, TransientLLMError
from runtime.llm.factory import _openai_sdk_client, create_llm_client
from runtime.llm.types import (LLMRequest, PromptMessage, PromptProvenance,
                               TemperatureContract)


def _underlying_httpx_client(oai):
    # openai>=1.x exposes the transport as _client (an httpx.Client).
    return getattr(oai, "_client", None)


def test_deepseek_sdk_client_ignores_env_proxies():
    # The trust_env=False helper is still used for the SDK-based providers.
    oai = _openai_sdk_client(
        api_key="sk-test", base_url="https://api.deepseek.com", trust_env=False
    )
    hx = _underlying_httpx_client(oai)
    assert isinstance(hx, httpx.Client)
    assert hx.trust_env is False


def test_default_sdk_client_still_trusts_env():
    oai = _openai_sdk_client(api_key="sk-test", base_url="https://api.openai.com/v1")
    hx = _underlying_httpx_client(oai)
    # Default path keeps httpx's normal env-trusting behavior.
    assert hx is None or hx.trust_env is True


def _dummy_request() -> LLMRequest:
    return LLMRequest(
        request_id="R-proxy-test",
        capability="ChapterDraft",
        messages=[PromptMessage("user", "写一章")],
        model_pin=openai_model_pin(provider="deepseek", model="deepseek-v4-pro",
                                   api_base="https://api.deepseek.com"),
        temperature=TemperatureContract(temperature=0.7, top_p=None),
        timeout_seconds=120.0,
        max_output_tokens=4000,
        prompt_provenance=PromptProvenance(
            prompt_id="chapter-draft", prompt_hash="sha256:abc",
            template_id="chapter-draft", template_version="1.0.0",
            package_hash="sha256:pkg", derived_from=["CHR-00001@v1"],
            rendered_at="t1"),
        metadata={"bridge": "test"},
    )


def test_curl_adapter_bypasses_proxy_with_noproxy(monkeypatch):
    # The CURRENT transport is curl, not httpx. curl honors ambient proxy env
    # vars by default, so the adapter MUST pass --noproxy '*' to reach the
    # China-hosted API directly even under a shell proxy.
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:7897")
    monkeypatch.setenv("https_proxy", "http://127.0.0.1:7897")
    client = create_llm_client("deepseek")
    cmd = client.adapter._build_curl_cmd(_dummy_request())
    # --noproxy '*' present and paired
    assert "--noproxy" in cmd
    assert cmd[cmd.index("--noproxy") + 1] == "*"


def test_kimi_provider_uses_moonshot_base_url(monkeypatch):
    # Kimi (Moonshot) is OpenAI-compatible: it must dispatch through the shared
    # OpenAI-compatible adapter, labeled "kimi", pointed at the Moonshot base_url.
    from runtime.llm.factory import KIMI_BASE_URL
    assert KIMI_BASE_URL == "https://api.moonshot.cn/v1"
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    monkeypatch.setenv("MOONSHOT_API_KEY", "sk-test-kimi")
    client = create_llm_client("kimi")
    assert client.adapter.provider == "kimi"


def test_kimi_accepts_kimi_api_key_alias(monkeypatch):
    # Either MOONSHOT_API_KEY or KIMI_API_KEY works.
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.setenv("KIMI_API_KEY", "sk-test-alias")
    client = create_llm_client("kimi")
    assert client.adapter.provider == "kimi"


def test_92code_uses_responses_adapter(monkeypatch):
    # 92code relay exposes ONLY the Responses API (/v1/chat/completions 404s), so
    # it must dispatch through OpenAIResponsesAdapter, not the chat-completions one.
    from runtime.llm.factory import CODE92_BASE_URL
    from runtime.llm.adapters.openai_responses import OpenAIResponsesAdapter
    assert CODE92_BASE_URL == "https://claudecode.top/v1"
    monkeypatch.setenv("CODE92_API_KEY", "sk-test-92code")
    monkeypatch.delenv("CODE92_STORE", raising=False)
    monkeypatch.delenv("CODE92_REASONING_EFFORT", raising=False)
    client = create_llm_client("92code")
    assert isinstance(client.adapter, OpenAIResponsesAdapter)
    assert client.adapter.provider == "92code"
    # codex config defaults: reasoning xhigh, store off (disable_response_storage)
    assert client.adapter.reasoning_effort == "xhigh"
    assert client.adapter.store is False


def test_92code_missing_key_errors_clearly(monkeypatch):
    monkeypatch.delenv("CODE92_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="CODE92_API_KEY"):
        create_llm_client("92code")


def test_kimi_missing_key_errors_clearly(monkeypatch):
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="MOONSHOT_API_KEY"):
        create_llm_client("kimi")


def test_claude_forced_tool_schema_returns_canonical_json():
    captured = {}

    class Messages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                content=[SimpleNamespace(
                    type="tool_use", name="submit_result",
                    input={"ok": True})],
                usage=SimpleNamespace(input_tokens=4, output_tokens=2),
                id="msg-test", stop_reason="tool_use",
            )

    adapter = ClaudeAdapter.__new__(ClaudeAdapter)
    adapter.client = SimpleNamespace(messages=Messages())
    adapter.default_model = None
    schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }
    request = replace(_dummy_request(), metadata={
        "structured_output_schema": json.dumps(schema),
        "structured_output_tool_name": "submit_result",
    })

    response = adapter.generate(request)

    assert captured["tools"][0]["input_schema"] == schema
    assert captured["tool_choice"] == {"type": "tool", "name": "submit_result"}
    assert json.loads(response.text) == {"ok": True}
    assert response.finish_reason == "tool_call"


def test_claude_factory_accepts_auth_token_and_proxy_config(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-test-claude")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://relay.example/v1")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test")
    monkeypatch.delenv("ANTHROPIC_TRUST_ENV", raising=False)

    client = create_llm_client("claude")

    assert isinstance(client.adapter, ClaudeAdapter)
    assert client.adapter.default_model == "claude-test"
    assert client.adapter.client.auth_token == "sk-test-claude"
    assert client.adapter.client.api_key is None
    assert client.adapter.client._client.trust_env is False


def test_claude_can_opt_in_to_ambient_proxy(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-claude")
    monkeypatch.setenv("ANTHROPIC_TRUST_ENV", "true")

    client = create_llm_client("claude")

    assert isinstance(client.adapter, ClaudeAdapter)
    assert client.adapter.client._client.trust_env is True


def test_claude_requires_a_resolved_model(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-claude")
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    client = create_llm_client("claude")
    request = _dummy_request()
    request = LLMRequest(
        **{
            **request.__dict__,
            "model_pin": openai_model_pin(
                provider="claude", model="", api_base="https://api.anthropic.com"
            ),
        }
    )

    with pytest.raises(PermanentLLMError, match="Claude model is required"):
        client.adapter.generate(request)


def test_claude_classifies_rate_limits_and_server_errors_as_transient():
    class StatusError(Exception):
        def __init__(self, status_code):
            self.status_code = status_code

    for status in (429, 500, 502, 503):
        assert isinstance(ClaudeAdapter._classify(StatusError(status)),
                          TransientLLMError)
    assert isinstance(ClaudeAdapter._classify(StatusError(400)),
                      PermanentLLMError)


def test_responses_text_falls_back_to_nested_output_content():
    class Part:
        text = '{"character_consistency":{"winner":"A","evidence":"证据"}}'

    class Item:
        content = [Part()]

    class RelayResponse:
        output_text = ""
        output = [Item()]

    assert _response_text(RelayResponse()).startswith('{"character_consistency"')


def test_responses_text_supports_dict_shaped_relay_output():
    response = type(
        "RelayResponse",
        (),
        {
            "output_text": None,
            "output": [
                {"content": [{"type": "output_text", "text": '{"winner":"A"}'}]}
            ],
        },
    )()

    assert _response_text(response) == '{"winner":"A"}'
