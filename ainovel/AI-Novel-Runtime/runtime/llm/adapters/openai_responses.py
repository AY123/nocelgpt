"""openai_responses.py — adapter for the OpenAI *Responses* API (/v1/responses).

Distinct from OpenAICompatibleAdapter, which speaks Chat Completions
(/v1/chat/completions). Some relays/providers only expose the Responses wire
protocol (e.g. codex-style gateways with wire_api="responses"): their
/v1/chat/completions returns 404 while /v1/responses works. This adapter maps
our LLMRequest onto responses.create(input, instructions, reasoning, ...) and
reads the aggregated output text back.
"""
from __future__ import annotations

from typing import Iterable, Optional

from ..errors import PermanentLLMError, TransientLLMError
from ..types import (LLMRequest, LLMResponse, LLMStreamEvent, ModelVersionPin,
                     TokenUsage, now_ms, sha256_obj)
from .openai_compatible import (_classify_openai_error, _map_finish_reason,
                                ADAPTER_VERSION)

def _usage_from_responses(usage) -> TokenUsage:
    """Responses API usage uses input_tokens/output_tokens/total_tokens (not the
    Chat Completions prompt_/completion_ names). reasoning_tokens lives under
    output_tokens_details."""
    if usage is None:
        return TokenUsage(0, 0, 0, usage_estimated=True)
    out_details = getattr(usage, "output_tokens_details", None)
    in_details = getattr(usage, "input_tokens_details", None)
    return TokenUsage(
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        total_tokens=getattr(usage, "total_tokens", 0) or 0,
        cached_input_tokens=getattr(in_details, "cached_tokens", 0) or 0,
        reasoning_tokens=getattr(out_details, "reasoning_tokens", 0) or 0,
    )


def responses_model_pin(*, provider, model, api_base) -> ModelVersionPin:
    return ModelVersionPin(
        provider=provider,
        model=model,
        adapter_version=ADAPTER_VERSION,
        api_base=api_base,
    )


def _split_instructions(request: LLMRequest):
    """Responses API takes a single `instructions` (system) + `input` (the turns).
    Fold all system messages into instructions; join the rest as the input."""
    system = "\n\n".join(m.content for m in request.messages if m.role == "system")
    turns = "\n\n".join(m.content for m in request.messages if m.role != "system")
    return (system or None), turns


def _response_text(response) -> str:
    """Read text from both SDK-native and relay-shaped Responses payloads."""
    aggregated = getattr(response, "output_text", None)
    if aggregated:
        return str(aggregated).strip()

    chunks = []
    for item in getattr(response, "output", None) or []:
        content = (
            item.get("content", []) if isinstance(item, dict)
            else getattr(item, "content", [])
        )
        for part in content or []:
            if isinstance(part, dict):
                text = part.get("text") or part.get("output_text")
            else:
                text = getattr(part, "text", None) or getattr(part, "output_text", None)
            if text:
                chunks.append(str(text))
    return "\n".join(chunks).strip()


class OpenAIResponsesAdapter:
    adapter_version = ADAPTER_VERSION

    def __init__(self, *, provider, client, reasoning_effort: Optional[str] = None,
                 store: bool = True):
        self.provider = provider
        self.client = client
        self.reasoning_effort = reasoning_effort
        self.store = store

    def generate(self, request: LLMRequest) -> LLMResponse:
        started = now_ms()
        instructions, user_input = _split_instructions(request)
        kwargs = {
            "model": request.model_pin.model,
            "input": user_input,
            "temperature": request.temperature.temperature,
            "timeout": request.timeout_seconds,
            "store": self.store,
        }
        if instructions:
            kwargs["instructions"] = instructions
        if request.max_output_tokens is not None:
            kwargs["max_output_tokens"] = request.max_output_tokens
        if self.reasoning_effort:
            kwargs["reasoning"] = {"effort": self.reasoning_effort}
        try:
            response = self.client.responses.create(**kwargs)
        except Exception as exc:
            raise _classify_openai_error(exc) from exc

        text = _response_text(response)
        status = getattr(response, "status", None)
        finish = "length" if status == "incomplete" else "stop"
        return LLMResponse(
            request_id=request.request_id,
            provider=self.provider,
            model=request.model_pin.model,
            text=text,
            finish_reason=_map_finish_reason(finish),
            token_usage=_usage_from_responses(getattr(response, "usage", None)),
            cost=None,
            latency_ms=now_ms() - started,
            response_hash=sha256_obj({"text": text}),
            provider_request_id=getattr(response, "id", None),
            replay_ref=None,
        )

    def stream(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        # Responses API supports streaming, but the serial path only needs
        # non-streaming generate(). Fall back to a single generate() emitted as
        # one delta + done so the model still works under a streaming caller.
        try:
            resp = self.generate(request)
        except Exception as exc:
            yield LLMStreamEvent(request_id=request.request_id, kind="error", error=str(exc))
            return
        yield LLMStreamEvent(request_id=request.request_id, kind="delta", text_delta=resp.text)
        yield LLMStreamEvent(request_id=request.request_id, kind="usage",
                             token_usage=resp.token_usage)
        yield LLMStreamEvent(request_id=request.request_id, kind="done")
