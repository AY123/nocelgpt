import json
from types import SimpleNamespace

from runtime.execution.llm_model import LLMExecutionModel
from runtime.cli import _apply_model_defaults
from runtime.llm.types import LLMResponse, TokenUsage


def test_92code_model_default_can_be_constructed(monkeypatch):
    monkeypatch.setenv("CODE92_MODEL", "gpt-5.6-sol")
    monkeypatch.setattr(
        "runtime.execution.llm_model.create_llm_client", lambda *args, **kwargs: object())

    model = LLMExecutionModel(provider="92code", model_id="deepseek-v4-pro")

    assert model.model_id == "gpt-5.6-sol"


def test_cli_model_default_does_not_override_deepseek(monkeypatch):
    monkeypatch.setenv("CODE92_MODEL", "gpt-5.6-sol")
    args = SimpleNamespace(
        model_provider="deepseek", model_id="deepseek-v4-pro")

    _apply_model_defaults(args)

    assert args.model_id == "deepseek-v4-pro"


def test_cli_model_default_still_applies_to_92code(monkeypatch):
    monkeypatch.setenv("CODE92_MODEL", "gpt-5.6-sol")
    args = SimpleNamespace(
        model_provider="92code", model_id="deepseek-v4-pro")

    _apply_model_defaults(args)

    assert args.model_id == "gpt-5.6-sol"


def test_execution_model_carries_structured_schema_in_semantic_request(monkeypatch):
    captured = {}

    class Client:
        def generate(self, request):
            captured["request"] = request
            return LLMResponse(
                request_id=request.request_id,
                provider="claude",
                model=request.model_pin.model,
                text='{"ok":true}',
                finish_reason="tool_call",
                token_usage=TokenUsage(1, 1, 2),
                cost=None,
                latency_ms=1,
                response_hash="sha256:response",
                provider_request_id="msg-1",
                replay_ref=None,
            )

    monkeypatch.setattr(
        "runtime.execution.llm_model.create_llm_client",
        lambda provider, replay_dir=None: Client())
    model = LLMExecutionModel(provider="claude", model_id="claude-test")
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}

    output = model.generate_structured(
        "return ok", schema, tool_name="submit_result")

    request = captured["request"]
    assert model.supports_structured_output is True
    assert json.loads(request.metadata["structured_output_schema"]) == schema
    assert request.metadata["structured_output_tool_name"] == "submit_result"
    assert model.last_request is request
    assert output.text == '{"ok":true}'
