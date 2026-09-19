from __future__ import annotations

from typing import Iterable

import httpx

from ..errors import PermanentLLMError, TransientLLMError
from ..types import (LLMRequest, LLMResponse, LLMStreamEvent, TokenUsage,
                     now_ms, sha256_obj)


class LocalAdapter:
    adapter_version = "1.0.0"
    provider = "local"

    def __init__(self, *, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url.rstrip("/")

    def generate(self, request: LLMRequest) -> LLMResponse:
        started = now_ms()
        prompt = "\n\n".join(f"{m.role}: {m.content}" for m in request.messages)
        payload = {
            "model": request.model_pin.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature.temperature,
                **({"top_p": request.temperature.top_p}
                   if request.temperature.top_p is not None else {}),
            },
        }
        try:
            r = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=request.timeout_seconds,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            raise TransientLLMError(str(exc)) from exc
        text = data.get("response", "")
        input_tokens = int(data.get("prompt_eval_count", 0) or 0)
        output_tokens = int(data.get("eval_count", 0) or 0)
        if input_tokens == 0 and output_tokens == 0:
            input_tokens = len(prompt.split())
            output_tokens = len(text.split())
            estimated = True
        else:
            estimated = False
        return LLMResponse(
            request_id=request.request_id,
            provider="local",
            model=request.model_pin.model,
            text=text.strip(),
            finish_reason="stop",
            token_usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                usage_estimated=estimated,
            ),
            cost=None,
            latency_ms=now_ms() - started,
            response_hash=sha256_obj({"text": text}),
            provider_request_id=None,
            replay_ref=None,
        )

    def stream(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        yield from ()
