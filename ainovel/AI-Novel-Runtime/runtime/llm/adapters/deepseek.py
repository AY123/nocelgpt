from __future__ import annotations

from typing import Iterable, Optional

import json
import subprocess

from ..errors import PermanentLLMError, TransientLLMError
from ..types import (LLMRequest, LLMResponse, LLMStreamEvent, TokenUsage,
                     now_ms, sha256_obj)


ADAPTER_VERSION = "1.0.0"
DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"


def _classify(exc: Exception) -> Exception:
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and (status in {408, 409, 429} or 500 <= status < 600):
        return TransientLLMError(str(exc))
    name = exc.__class__.__name__.lower()
    if "timeout" in name or "connection" in name or "rate" in name:
        return TransientLLMError(str(exc))
    # A curl transport failure is wrapped as RuntimeError(stderr) with no
    # status_code, so the class name ("runtimeerror") carries no signal — the
    # transient nature is only in the MESSAGE. A --max-time timeout (curl exit
    # 28 "Operation timed out"), a DNS/connect failure ("could not resolve",
    # "connection refused/reset"), or "recv failure" is retryable, not permanent.
    # Without this a single network blip aborts the whole serial run (RUN-00023,
    # ch5 gen). Same class of bug as the openai 5xx misclassification.
    msg = str(exc).lower()
    _TRANSIENT_MARKERS = (
        "timed out", "timeout", "(28)", "operation too slow",
        "could not resolve", "couldn't resolve", "connection refused",
        "connection reset", "recv failure", "connection", "temporarily",
    )
    if any(marker in msg for marker in _TRANSIENT_MARKERS):
        return TransientLLMError(str(exc))
    return PermanentLLMError(str(exc))


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception as exc:
        raise PermanentLLMError(f"DeepSeek response was not valid JSON: {text[:200]!r}") from exc


class DeepSeekAdapter:
    adapter_version = ADAPTER_VERSION
    provider = "deepseek"

    def __init__(self, *, api_key: str, base_url: str = DEEPSEEK_CHAT_URL):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def _messages(request: LLMRequest):
        system = "\n\n".join(m.content for m in request.messages if m.role == "system")
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role != "system"
        ]
        if system:
            messages = [{"role": "system", "content": system}] + messages
        return messages

    def _endpoint(self) -> str:
        # factory hands us the API ROOT (https://api.deepseek.com); the chat
        # completions path must be appended or the POST 404s. Tolerate both a
        # root base_url and a full chat-completions URL (the class default) so
        # neither caller can silently POST to the wrong path.
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return self.base_url + "/chat/completions"

    def _build_curl_cmd(self, request: LLMRequest) -> list:
        """Assemble the curl argv for a chat-completions POST. Pure (no I/O) so
        the transport contract — direct connection, status trailer, timeout —
        is unit-testable without a network call."""
        payload = {
            "model": request.model_pin.model,
            "messages": self._messages(request),
            "temperature": request.temperature.temperature,
            "stream": False,
        }
        if request.temperature.top_p is not None:
            payload["top_p"] = request.temperature.top_p
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens
        # Trailer the HTTP status so an error response (which curl -sS still exits
        # 0 for) is DETECTED instead of parsed as an empty draft. --max-time caps a
        # hung connection at the request's own timeout.
        return [
            "curl", "-sS", "-w", "\n%{http_code}",
            # DeepSeek is a China-hosted API that must be reached DIRECTLY. curl
            # honors ambient http_proxy/https_proxy/all_proxy by default; a shell
            # proxy (e.g. Clash on 127.0.0.1:7897) would route the request through
            # it and the proxy rule rejects it (403). --noproxy '*' bypasses the
            # proxy for every host — the curl equivalent of httpx trust_env=False,
            # which the pre-curl SDK client used. Lost silently in the curl
            # migration (209b4d2); restored here. Regression: test_llm_factory_proxy.
            "--noproxy", "*",
            "--max-time", str(int(request.timeout_seconds) or 120),
            self._endpoint(),
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {self.api_key}",
            "-d", json.dumps(payload, ensure_ascii=False),
        ]

    def _post(self, request: LLMRequest) -> dict:
        cmd = self._build_curl_cmd(request)
        try:
            proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            # transport-level failure (DNS, connect, --max-time): body may be empty
            stderr = (exc.stderr or exc.stdout or str(exc)).strip()
            raise _classify(RuntimeError(stderr)) from exc
        except Exception as exc:
            raise _classify(exc) from exc
        body, _, status = proc.stdout.rpartition("\n")
        status = status.strip()
        if status and status != "200":
            err = RuntimeError(f"DeepSeek HTTP {status}: {body[:300]}")
            err.status_code = int(status) if status.isdigit() else None
            raise _classify(err)
        return _extract_json(body)

    def generate(self, request: LLMRequest) -> LLMResponse:
        started = now_ms()
        data = self._post(request)
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        text = (msg.get("content") or "").strip()
        usage = data.get("usage") or {}
        input_tokens = int(usage.get("prompt_tokens", 0) or 0)
        output_tokens = int(usage.get("completion_tokens", 0) or 0)
        total_tokens = int(usage.get("total_tokens", input_tokens + output_tokens) or (input_tokens + output_tokens))
        reason = choice.get("finish_reason") or "stop"
        if reason == "tool_calls":
            reason = "tool_call"
        return LLMResponse(
            request_id=request.request_id,
            provider=self.provider,
            model=request.model_pin.model,
            text=text,
            finish_reason=reason,
            token_usage=TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cached_input_tokens=int((usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0),
                reasoning_tokens=int((usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0),
            ),
            cost=None,
            latency_ms=now_ms() - started,
            response_hash=sha256_obj({"text": text}),
            provider_request_id=data.get("id"),
            replay_ref=None,
        )

    def stream(self, request: LLMRequest) -> Iterable[LLMStreamEvent]:
        # DeepSeek streaming is not needed for the baseline path; keep the
        # contract by returning a single terminal event.
        response = self.generate(request)
        yield LLMStreamEvent(
            request_id=request.request_id,
            kind="done",
            finish_reason=response.finish_reason,
            token_usage=response.token_usage,
            response=response,
        )
