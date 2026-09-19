from __future__ import annotations

import json

from ..errors import PermanentLLMError, TransientLLMError
from ..types import (LLMRequest, LLMResponse, LLMStreamEvent, TokenUsage,
                     now_ms, sha256_obj)


class ClaudeAdapter:
    adapter_version = "1.0.0"
    provider = "claude"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        auth_token: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        trust_env: bool = False,
    ):
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "Claude adapter requires anthropic. Install it to enable Claude."
            ) from exc
        client_kwargs = {}
        if api_key:
            client_kwargs["api_key"] = api_key
        if auth_token:
            client_kwargs["auth_token"] = auth_token
        if base_url:
            client_kwargs["base_url"] = base_url
        if not trust_env:
            # The judge must not inherit a local system or shell proxy. The
            # Anthropic SDK uses httpx underneath, so this is its equivalent
            # of DeepSeek's curl --noproxy '*'.
            import httpx

            client_kwargs["http_client"] = httpx.Client(trust_env=False)
        self.client = anthropic.Anthropic(**client_kwargs)
        self.default_model = model

    def _model_for(self, request: LLMRequest) -> str:
        model = request.model_pin.model or self.default_model
        if not model:
            raise PermanentLLMError(
                "Claude model is required in the request model pin or ANTHROPIC_MODEL"
            )
        return model

    @staticmethod
    def _split(request: LLMRequest):
        system = "\n\n".join(m.content for m in request.messages if m.role == "system")
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role != "system"
        ]
        return system, messages

    @staticmethod
    def _classify(exc: Exception) -> Exception:
        name = exc.__class__.__name__.lower()
        status = getattr(exc, "status_code", None)
        # P1-3: Include 408 (request timeout) and 409 (conflict) as transient
        if (status in {408, 409, 429} or (isinstance(status, int) and status >= 500)
                or "rate" in name or "timeout" in name or "connection" in name):
            return TransientLLMError(str(exc))
        return PermanentLLMError(str(exc))

    def generate(self, request: LLMRequest) -> LLMResponse:
        started = now_ms()
        system, messages = self._split(request)
        model = self._model_for(request)
        kwargs = {
            "model": model,
            "max_tokens": request.max_output_tokens or 1024,
            "temperature": request.temperature.temperature,
            "system": system or None,
            "messages": messages,
            "timeout": request.timeout_seconds,
        }
        # Only include top_p if explicitly set (some APIs reject None)
        if request.temperature.top_p is not None:
            kwargs["top_p"] = request.temperature.top_p
        structured_schema = request.metadata.get("structured_output_schema")
        tool_name = request.metadata.get(
            "structured_output_tool_name", "submit_structured_result")
        if structured_schema:
            try:
                schema = json.loads(structured_schema)
            except json.JSONDecodeError as exc:
                raise PermanentLLMError("invalid structured_output_schema metadata") from exc
            kwargs["tools"] = [{
                "name": tool_name,
                "description": "Submit the complete structured result.",
                "input_schema": schema,
            }]
            kwargs["tool_choice"] = {"type": "tool", "name": tool_name}
        try:
            response = self.client.messages.create(**kwargs)
        except Exception as exc:
            raise self._classify(exc) from exc
        tool_inputs = [
            getattr(block, "input", None)
            for block in response.content
            if getattr(block, "type", "") == "tool_use"
            and getattr(block, "name", None) == tool_name
        ]
        if structured_schema and tool_inputs:
            text = json.dumps(
                tool_inputs[0], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        else:
            text = "\n".join(
                getattr(block, "text", "") for block in response.content
                if getattr(block, "type", "") == "text")
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        return LLMResponse(
            request_id=request.request_id,
            provider="claude",
            model=model,
            text=text.strip(),
            finish_reason=_map_stop_reason(getattr(response, "stop_reason", None)),
            token_usage=TokenUsage(input_tokens, output_tokens, input_tokens + output_tokens),
            cost=None,
            latency_ms=now_ms() - started,
            response_hash=sha256_obj({"text": text}),
            provider_request_id=getattr(response, "id", None),
            replay_ref=None,
        )

    def stream(self, request: LLMRequest):
        """Live token streaming via the Anthropic SDK. Yields `delta` events as
        text arrives, then a terminal `done` event carrying token usage so the
        managed client can price and record it. Errors are classified into the
        transient/permanent hierarchy so retry + fallback behave as in generate."""
        system, messages = self._split(request)
        model = self._model_for(request)
        stream_kwargs = {
            "model": model,
            "max_tokens": request.max_output_tokens or 1024,
            "temperature": request.temperature.temperature,
            "system": system or None,
            "messages": messages,
        }
        # Only include top_p if explicitly set (some APIs reject None)
        if request.temperature.top_p is not None:
            stream_kwargs["top_p"] = request.temperature.top_p
        try:
            with self.client.messages.stream(**stream_kwargs) as stream:
                for text_delta in stream.text_stream:
                    yield LLMStreamEvent(
                        request_id=request.request_id,
                        kind="delta",
                        text_delta=text_delta,
                    )
                final = stream.get_final_message()
        except Exception as exc:
            raise self._classify(exc) from exc
        usage = getattr(final, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        finish_reason = _map_stop_reason(getattr(final, "stop_reason", None))
        yield LLMStreamEvent(
            request_id=request.request_id,
            kind="done",
            finish_reason=finish_reason,
            token_usage=TokenUsage(
                input_tokens, output_tokens, input_tokens + output_tokens),
        )


def _map_stop_reason(reason) -> str:
    return {
        "end_turn": "stop",
        "max_tokens": "length",
        "stop_sequence": "stop",
        "tool_use": "tool_call",
    }.get(reason or "end_turn", "stop")
