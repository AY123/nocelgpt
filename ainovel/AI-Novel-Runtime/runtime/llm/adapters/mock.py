from __future__ import annotations

from typing import Iterable

from ..types import (LLMRequest, LLMResponse, LLMStreamEvent, TokenUsage,
                     now_ms, sha256_obj)


class MockAdapter:
    adapter_version = "1.0.0"
    provider = "mock"

    def __init__(self, text: str = "Mock draft generated for CI."):
        self.text = text

    def generate(self, request: LLMRequest) -> LLMResponse:
        started = now_ms()
        input_tokens = sum(len(m.content.split()) for m in request.messages)
        output_tokens = len(self.text.split())
        return LLMResponse(
            request_id=request.request_id,
            provider="mock",
            model=request.model_pin.model,
            text=self.text,
            finish_reason="stop",
            token_usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                usage_estimated=True,
            ),
            cost=None,
            latency_ms=now_ms() - started,
            response_hash=sha256_obj({"text": self.text}),
            provider_request_id=None,
            replay_ref=None,
        )

    def stream(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        for token in self.text.split():
            yield LLMStreamEvent(
                request_id=request.request_id,
                kind="delta",
                text_delta=token + " ",
            )
        yield LLMStreamEvent(request_id=request.request_id, kind="done")

