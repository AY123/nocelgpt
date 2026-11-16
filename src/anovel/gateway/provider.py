"""OpenAI Responses HTTP adapter; exactly one count and one generation at most.

No SDK retries, redirects, tools, history sessions, or Canon capabilities.
The local loopback transport is explicitly test-only, never live evidence.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import UTC, datetime
from queue import Empty, Queue
from threading import Thread
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from anovel.canon.identity import canonical_bytes

from .ledger import DispatchPermit
from .models import (
    GatewayError,
    GatewayRequest,
    ModelPolicy,
    ProviderReply,
    Usage,
    validate_output,
)


class ProviderAdapter(Protocol):
    def send(
        self,
        request: GatewayRequest,
        policy: ModelPolicy,
        attempt_id: str,
        permit: DispatchPermit | None = None,
    ) -> ProviderReply: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None


def strict_json(raw: bytes) -> dict[str, object]:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def constant(_value: str) -> object:
        raise ValueError("nonfinite JSON number")

    result = json.loads(
        raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
    )
    if type(result) is not dict:
        raise ValueError("JSON response must be an object")
    canonical_bytes(result)
    return cast(dict[str, object], result)


def response_payload(request: GatewayRequest, policy: ModelPolicy) -> bytes:
    if policy not in request.policies:
        raise GatewayError("Policy not frozen in logical request")
    params = strict_json(policy.params_bytes)
    return canonical_bytes(
        {
            "model": policy.model,
            "instructions": request.instructions,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": request.context.model_bytes.decode("utf-8"),
                        }
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "anovel_output",
                    "schema": request.schema,
                    "strict": True,
                }
            },
            "max_output_tokens": policy.max_output_tokens,
            "store": False,
            "stream": False,
            "truncation": "disabled",
            "service_tier": "default",
            **params,
        }
    )


class OpenAIResponsesAdapter:
    def __init__(self, api_key: str, *, allow_test_transport: bool = False) -> None:
        if type(api_key) is not str or not api_key.strip():
            raise GatewayError("Credential entry missing")
        self._credential = api_key
        self._allow_test_transport = allow_test_transport
        self._opener = build_opener(_NoRedirect())

    def _post(
        self, url: str, payload: bytes, timeout: float
    ) -> tuple[int, bytes, str | None]:
        # urllib's timeout alone is an idle socket timeout: a dripping response
        # can exceed it indefinitely. Bound what the caller waits for as well.
        # A timed-out remote request may still execute; its reserved liability
        # stays UNKNOWN. The worker performs this one POST only, never retries,
        # persists a result, or chains a generation after a late token count.
        results: Queue[tuple[int, bytes, str | None] | None] = Queue(maxsize=1)

        def exchange() -> None:
            try:
                results.put(self._post_wire(url, payload, timeout))
            except Exception:
                results.put(None)

        if timeout <= 0:
            raise TimeoutError("Frozen request deadline elapsed")
        Thread(target=exchange, daemon=True).start()
        try:
            result = results.get(timeout=timeout)
        except Empty:
            raise TimeoutError("Provider response deadline elapsed") from None
        if result is None:
            raise ValueError("Provider exchange could not establish a response")
        return result

    def _post_wire(
        self, url: str, payload: bytes, timeout: float
    ) -> tuple[int, bytes, str | None]:
        request = Request(
            url,
            data=payload,
            headers={
                "Authorization": "Bearer " + self._credential,
                "Content-Type": "application/json",
                "User-Agent": "ANovelOS-Gateway/1.0",
            },
            method="POST",
        )
        try:
            response = self._opener.open(request, timeout=timeout)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise ValueError("RESPONSE_BODY_LIMIT")
            if self._credential.encode() in raw or re.search(
                rb"sk-[A-Za-z0-9_-]{8,}", raw
            ):
                raise ValueError("CREDENTIAL_MATERIAL_WITHHELD")
            request_id = response.headers.get("x-request-id")
            if request_id is not None and (
                self._credential in request_id
                or re.search(r"sk-[A-Za-z0-9_-]{8,}", request_id)
                or len(request_id) > 512
                or any(ord(c) < 32 or ord(c) > 126 for c in request_id)
            ):
                request_id = None
            return response.code, raw, request_id

    def send(
        self,
        request: GatewayRequest,
        policy: ModelPolicy,
        attempt_id: str,
        permit: DispatchPermit | None = None,
    ) -> ProviderReply:
        if type(permit) is not DispatchPermit:
            raise GatewayError("Durable budget dispatch permit required")
        permit.consume(request, policy, attempt_id)

        def timeout() -> float:
            remaining = (
                min(
                    datetime.fromisoformat(permit.deadline_at),
                    datetime.fromisoformat(policy.price_expires_at),
                )
                - datetime.now(UTC)
            ).total_seconds()
            if remaining <= 0:
                raise TimeoutError("Frozen run deadline elapsed")
            return min(float(policy.timeout_seconds), remaining)

        if policy.test_mode and not self._allow_test_transport:
            raise GatewayError("Explicit loopback test transport required")
        payload = response_payload(request, policy)
        count_payload = canonical_bytes(
            {
                k: v
                for k, v in strict_json(payload).items()
                if k
                in {"model", "instructions", "input", "text", "reasoning", "truncation"}
            }
        )
        count_raw = None
        count_id = None
        count = None
        try:
            code, count_raw, count_id = self._post(
                policy.endpoint + "/input_tokens", count_payload, timeout()
            )
            if code != 200:
                return ProviderReply(
                    "FAILED",
                    error_code="COUNT_HTTP_" + str(code),
                    count_body=count_raw,
                    count_request_id=count_id,
                )
            data = strict_json(count_raw)
            number = data.get("input_tokens")
            if (
                data.get("object") != "response.input_tokens"
                or type(number) is not int
                or number < 0
            ):
                return ProviderReply(
                    "FAILED",
                    error_code="INVALID_TOKEN_COUNT",
                    count_body=count_raw,
                    count_request_id=count_id,
                )
            count = number
            if count + policy.max_output_tokens > policy.context_window:
                return ProviderReply(
                    "FAILED",
                    error_code="INPUT_WINDOW_EXCEEDED",
                    count_body=count_raw,
                    count_request_id=count_id,
                    input_token_count=count,
                )
        except (URLError, TimeoutError, OSError, ValueError):
            return ProviderReply(
                "FAILED" if count_raw is not None else "UNKNOWN",
                error_code="INVALID_TOKEN_COUNT_BODY"
                if count_raw is not None
                else "TOKEN_COUNT_UNPROVEN",
                count_body=count_raw,
                count_request_id=count_id,
                input_token_count=count,
            )
        try:
            code, raw, request_id = self._post(policy.endpoint, payload, timeout())
        except (URLError, TimeoutError, OSError, ValueError):
            return ProviderReply(
                "UNKNOWN",
                error_code="GENERATION_TRANSPORT_UNPROVEN",
                count_body=count_raw,
                count_request_id=count_id,
                input_token_count=count,
            )
        base = ProviderReply(
            "FAILED",
            response_body=raw,
            provider_request_id=request_id,
            http_status=code,
            count_body=count_raw,
            count_request_id=count_id,
            input_token_count=count,
        )
        if code != 200:
            return replace(
                base,
                outcome="UNKNOWN" if code >= 500 else "FAILED",
                error_code="HTTP_" + str(code),
            )
        try:
            data = strict_json(raw)
        except ValueError:
            return replace(base, error_code="INVALID_RESPONSE_JSON")
        model = data.get("model")
        model = model if type(model) is str and model else None
        usage = None
        usage_data = data.get("usage")
        if type(usage_data) is dict:
            try:
                i = usage_data.get("input_tokens")
                o = usage_data.get("output_tokens")
                t = usage_data.get("total_tokens")
                if type(i) is not int or type(o) is not int or type(t) is not int:
                    raise ValueError()
                usage = Usage(i, o, t)
            except ValueError:
                pass
        base = replace(base, observed_model=model, usage=usage)
        if data.get("service_tier") not in (None, "default"):
            return replace(base, usage=None, error_code="UNEXPECTED_SERVICE_TIER")
        if data.get("status") != "completed":
            return replace(base, error_code="RESPONSE_NOT_COMPLETED")
        if model not in policy.accepted_models:
            return replace(base, error_code="UNEXPECTED_MODEL")
        try:
            outputs = data.get("output")
            if type(outputs) is not list:
                raise ValueError()
            texts = []
            for item in outputs:
                if type(item) is not dict:
                    raise ValueError()
                if item.get("type") == "reasoning":
                    continue
                if item.get("type") != "message" or item.get("role") != "assistant":
                    raise ValueError()
                content = item.get("content")
                if type(content) is not list:
                    raise ValueError()
                for part in content:
                    if type(part) is not dict:
                        raise ValueError()
                    if part.get("type") == "refusal":
                        return replace(base, error_code="MODEL_REFUSAL")
                    if (
                        part.get("type") != "output_text"
                        or type(part.get("text")) is not str
                    ):
                        raise ValueError()
                    texts.append(part["text"])
            output = strict_json("".join(texts).encode("utf-8"))
            validate_output(request.schema, output)
            return replace(
                base, outcome="SUCCESS", output_bytes=canonical_bytes(output)
            )
        except ValueError:
            return replace(base, error_code="OUTPUT_SCHEMA_INVALID")
