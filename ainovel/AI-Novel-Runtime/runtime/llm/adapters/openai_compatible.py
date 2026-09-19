from __future__ import annotations

from typing import Iterable, Optional

from ..errors import PermanentLLMError, TransientLLMError
from ..types import (LLMRequest, LLMResponse, LLMStreamEvent, ModelVersionPin,
                     TokenUsage, now_ms, sha256_obj)


ADAPTER_VERSION = "1.0.0"


# HTTP statuses worth retrying: request timeout, conflict, rate limit, and ALL
# 5xx server errors (503 "service too busy", 500, 502, 504). A server-side 5xx is
# the canonical transient failure — classifying it as permanent (as the old
# name-only check did) makes a provider-overload run degrade with no retry.
_RETRYABLE_STATUS = {408, 409, 429}
_TRANSIENT_NAMES = {
    "APIConnectionError", "APITimeoutError", "RateLimitError",
    "InternalServerError", "APIError",
}


def _classify_openai_error(exc: Exception):
    """Map an OpenAI-SDK exception to Transient (retryable) vs Permanent. Prefers
    the HTTP status_code when present (5xx / 408 / 409 / 429 => transient), then
    falls back to the exception class name."""
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and (status in _RETRYABLE_STATUS or 500 <= status < 600):
        return TransientLLMError(str(exc))
    if exc.__class__.__name__ in _TRANSIENT_NAMES:
        return TransientLLMError(str(exc))
    return PermanentLLMError(str(exc))


def _usage_from_openai(usage) -> TokenUsage:
    if usage is None:
        return TokenUsage(0, 0, 0, usage_estimated=True)
    prompt_details = getattr(usage, "prompt_tokens_details", None)
    completion_details = getattr(usage, "completion_tokens_details", None)
    return TokenUsage(
        input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        total_tokens=getattr(usage, "total_tokens", 0) or 0,
        cached_input_tokens=getattr(prompt_details, "cached_tokens", 0) or 0,
        reasoning_tokens=getattr(completion_details, "reasoning_tokens", 0) or 0,
    )


def _map_finish_reason(value: Optional[str]):
    if value in ("stop", "length", "tool_call", "content_filter"):
        return value
    if value == "tool_calls":
        return "tool_call"
    return "stop"


def openai_model_pin(*, provider, model, api_base) -> ModelVersionPin:
    return ModelVersionPin(
        provider=provider,
        model=model,
        adapter_version=ADAPTER_VERSION,
        api_base=api_base,
    )


class OpenAICompatibleAdapter:
    adapter_version = ADAPTER_VERSION

    def __init__(self, *, provider, client):
        self.provider = provider
        self.client = client

    def generate(self, request: LLMRequest) -> LLMResponse:
        started = now_ms()
        kwargs = {
            "model": request.model_pin.model,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in request.messages
            ],
            "stream": False,
            "temperature": request.temperature.temperature,
            "timeout": request.timeout_seconds,
        }
        if request.temperature.top_p is not None:
            kwargs["top_p"] = request.temperature.top_p
        if request.max_output_tokens is not None:
            kwargs["max_tokens"] = request.max_output_tokens
        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            raise _classify_openai_error(exc) from exc

        text = response.choices[0].message.content or ""
        return LLMResponse(
            request_id=request.request_id,
            provider=self.provider,
            model=request.model_pin.model,
            text=text.strip(),
            finish_reason=_map_finish_reason(response.choices[0].finish_reason),
            token_usage=_usage_from_openai(getattr(response, "usage", None)),
            cost=None,
            latency_ms=now_ms() - started,
            response_hash=sha256_obj({"text": text}),
            provider_request_id=getattr(response, "id", None),
            replay_ref=None,
        )

    def stream(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        kwargs = {
            "model": request.model_pin.model,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in request.messages
            ],
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": request.temperature.temperature,
            "timeout": request.timeout_seconds,
        }
        if request.max_output_tokens is not None:
            kwargs["max_tokens"] = request.max_output_tokens
        try:
            for chunk in self.client.chat.completions.create(**kwargs):
                usage = getattr(chunk, "usage", None)
                if usage is not None:
                    yield LLMStreamEvent(
                        request_id=request.request_id,
                        kind="usage",
                        token_usage=_usage_from_openai(usage),
                    )
                    continue
                if not getattr(chunk, "choices", None):
                    continue
                delta = getattr(chunk.choices[0].delta, "content", None)
                if delta:
                    yield LLMStreamEvent(
                        request_id=request.request_id,
                        kind="delta",
                        text_delta=delta,
                    )
            yield LLMStreamEvent(request_id=request.request_id, kind="done")
        except Exception as exc:
            yield LLMStreamEvent(request_id=request.request_id, kind="error", error=str(exc))

