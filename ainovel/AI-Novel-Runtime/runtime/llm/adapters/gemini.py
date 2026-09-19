from __future__ import annotations

from ..errors import PermanentLLMError, TransientLLMError
from ..types import LLMRequest, LLMResponse, TokenUsage, now_ms, sha256_obj


class GeminiAdapter:
    adapter_version = "1.0.0"
    provider = "gemini"

    def __init__(self, *, api_key: str):
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError(
                "Gemini adapter requires google-genai. Install it to enable Gemini."
            ) from exc
        self.client = genai.Client(api_key=api_key)

    def generate(self, request: LLMRequest) -> LLMResponse:
        started = now_ms()
        prompt = "\n\n".join(f"{m.role}: {m.content}" for m in request.messages)
        try:
            response = self.client.models.generate_content(
                model=request.model_pin.model,
                contents=prompt,
            )
        except Exception as exc:
            name = exc.__class__.__name__.lower()
            if "rate" in name or "timeout" in name or "connection" in name:
                raise TransientLLMError(str(exc)) from exc
            raise PermanentLLMError(str(exc)) from exc
        text = getattr(response, "text", "") or ""
        usage = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "candidates_token_count", 0) or 0
        return LLMResponse(
            request_id=request.request_id,
            provider="gemini",
            model=request.model_pin.model,
            text=text.strip(),
            finish_reason="stop",
            token_usage=TokenUsage(input_tokens, output_tokens, input_tokens + output_tokens),
            cost=None,
            latency_ms=now_ms() - started,
            response_hash=sha256_obj({"text": text}),
            provider_request_id=None,
            replay_ref=None,
        )

    def stream(self, request):
        yield from ()
