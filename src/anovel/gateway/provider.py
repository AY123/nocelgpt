"""Bounded OpenAI Responses and Kimi Chat Completions HTTP adapters.

No SDK retries, redirects, tools, history sessions, or Canon capabilities.
The local loopback transport is explicitly test-only, never live evidence.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from queue import Empty, Queue
from threading import Thread
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from anovel.canon.identity import canonical_bytes
from anovel.context.models import ContextRole

from .ledger import DispatchPermit
from .models import (
    KIMI_CHAT_PATH,
    KIMI_PROBE_WINDOW,
    OPENAI_RESPONSES_ENDPOINT,
    OPENAI_SOL_CONTEXT_WINDOW,
    OPENAI_SOL_MODEL,
    GatewayError,
    GatewayRequest,
    ModelPolicy,
    ProviderReply,
    Usage,
    validate_output,
)

KIMI_FIRST_GENERATION_TEMPLATE = "gateway-kimi-first-generation-v1"
OPENAI_FIRST_GENERATION_TEMPLATE = "gateway-openai-first-generation-v1"
OPENAI_FIRST_GENERATION_TEXT = "ANovelOS OpenAI probe OK"
OPENAI_FIRST_GENERATION_INSTRUCTIONS = (
    'Return exactly this JSON object: {"text":"ANovelOS OpenAI probe OK"}.'
)
_PROBE_SCHEMA = canonical_bytes(
    {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
        "additionalProperties": False,
    }
)


def is_openai_first_generation_probe(
    request: GatewayRequest, policy: ModelPolicy
) -> bool:
    """Bind the uncounted request to the fixed, fiction-free Sol probe."""
    return (
        request.template_version == OPENAI_FIRST_GENERATION_TEMPLATE
        and request.instructions == OPENAI_FIRST_GENERATION_INSTRUCTIONS
        and request.schema_bytes == _PROBE_SCHEMA
        and request.policies == (policy,)
        and request.context.role is ContextRole.WRITER
        and not request.context.items
        and not request.context.selections
        and request.context.actor_id is None
        and request.context.scene_id is None
        and len(request.context.model_bytes) <= 1024
        and not policy.is_kimi
        and policy.model == OPENAI_SOL_MODEL
        and policy.accepted_models == (OPENAI_SOL_MODEL,)
        and policy.params == {"reasoning": {"effort": "low"}}
        and policy.max_output_tokens <= 1024
        and policy.timeout_seconds <= 30
        and (
            (policy.test_mode and policy.context_window <= KIMI_PROBE_WINDOW)
            or (
                not policy.test_mode
                and policy.endpoint == OPENAI_RESPONSES_ENDPOINT
                and policy.context_window == OPENAI_SOL_CONTEXT_WINDOW
                and policy.input_rate > 0
                and policy.output_rate > 0
            )
        )
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
    if policy.is_kimi:
        raise GatewayError("OpenAI Responses policy required")
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


class _BoundedHTTPAdapter:
    def __init__(
        self,
        api_key: str,
        *,
        allow_test_transport: bool = False,
        generation_only: bool = False,
    ) -> None:
        if type(generation_only) is not bool:
            raise GatewayError("Generation-only probe mode must be explicit")
        self._generation_only = generation_only
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

    def _consume_permit(
        self,
        request: GatewayRequest,
        policy: ModelPolicy,
        attempt_id: str,
        permit: DispatchPermit | None,
    ) -> DispatchPermit:
        if type(permit) is not DispatchPermit:
            raise GatewayError("Durable budget dispatch permit required")
        permit.consume(request, policy, attempt_id)
        if policy.test_mode and not self._allow_test_transport:
            raise GatewayError("Explicit loopback test transport required")
        return permit

    @staticmethod
    def _remaining_timeout(policy: ModelPolicy, permit: DispatchPermit) -> float:
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

    def _generate(
        self, policy: ModelPolicy, permit: DispatchPermit, payload: bytes
    ) -> ProviderReply:
        try:
            code, raw, request_id = self._post(
                policy.endpoint, payload, self._remaining_timeout(policy, permit)
            )
        except (URLError, TimeoutError, OSError, ValueError):
            return ProviderReply("UNKNOWN", error_code="GENERATION_TRANSPORT_UNPROVEN")
        return ProviderReply(
            "UNKNOWN" if code >= 500 else "FAILED",
            response_body=raw,
            provider_request_id=request_id,
            http_status=code,
            error_code=None if code == 200 else "HTTP_" + str(code),
        )

    def _count_and_generate(
        self,
        policy: ModelPolicy,
        permit: DispatchPermit,
        *,
        count_endpoint: str,
        count_payload: bytes,
        parse_count: Callable[[dict[str, object]], int | None],
        generation_payload: bytes,
        context_window: int,
    ) -> ProviderReply:
        count_raw = None
        count_id = None
        count = None
        try:
            code, count_raw, count_id = self._post(
                count_endpoint, count_payload, self._remaining_timeout(policy, permit)
            )
            if code != 200:
                return ProviderReply(
                    "FAILED",
                    error_code="COUNT_HTTP_" + str(code),
                    count_body=count_raw,
                    count_request_id=count_id,
                )
            count = parse_count(strict_json(count_raw))
            if count is None:
                return ProviderReply(
                    "FAILED",
                    error_code="INVALID_TOKEN_COUNT",
                    count_body=count_raw,
                    count_request_id=count_id,
                )
            if count + policy.max_output_tokens > context_window:
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
        return replace(
            self._generate(policy, permit, generation_payload),
            count_body=count_raw,
            count_request_id=count_id,
            input_token_count=count,
        )


def _openai_count(data: dict[str, object]) -> int | None:
    number = data.get("input_tokens")
    if (
        data.get("object") == "response.input_tokens"
        and type(number) is int
        and number >= 0
    ):
        return number
    return None


class OpenAIResponsesAdapter(_BoundedHTTPAdapter):
    def send(
        self,
        request: GatewayRequest,
        policy: ModelPolicy,
        attempt_id: str,
        permit: DispatchPermit | None = None,
    ) -> ProviderReply:
        if policy.is_kimi:
            raise GatewayError("OpenAI Responses policy required")
        dispatch = self._consume_permit(request, policy, attempt_id, permit)
        payload = response_payload(request, policy)
        if self._generation_only:
            if not is_openai_first_generation_probe(request, policy):
                raise GatewayError(
                    "Generation-only mode requires the fixed OpenAI probe"
                )
            base = self._generate(policy, dispatch, payload)
        else:
            count_payload = canonical_bytes(
                {
                    key: value
                    for key, value in strict_json(payload).items()
                    if key
                    in {
                        "model",
                        "instructions",
                        "input",
                        "text",
                        "reasoning",
                        "truncation",
                    }
                }
            )
            base = self._count_and_generate(
                policy,
                dispatch,
                count_endpoint=policy.endpoint + "/input_tokens",
                count_payload=count_payload,
                parse_count=_openai_count,
                generation_payload=payload,
                context_window=policy.context_window,
            )
        reply = parse_openai_response(request, policy, base)
        if (
            self._generation_only
            and reply.outcome == "SUCCESS"
            and reply.output_bytes
            != canonical_bytes({"text": OPENAI_FIRST_GENERATION_TEXT})
        ):
            return replace(
                reply,
                outcome="FAILED",
                output_bytes=None,
                error_code="PROBE_MARKER_MISMATCH",
            )
        return reply


def parse_openai_response(
    request: GatewayRequest, policy: ModelPolicy, base: ProviderReply
) -> ProviderReply:
    """Validate a Responses reply from wire bytes, also used for receipt readback."""
    if base.http_status != 200:
        return base
    assert base.response_body is not None
    try:
        data = strict_json(base.response_body)
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
        return replace(base, outcome="SUCCESS", output_bytes=canonical_bytes(output))
    except ValueError:
        return replace(base, error_code="OUTPUT_SCHEMA_INVALID")


def _kimi_count(data: dict[str, object]) -> int | None:
    estimate = data.get("data")
    if type(estimate) is dict:
        number = estimate.get("total_tokens")
        if type(number) is int and number > 0:
            return number
    return None


def _kimi_usage(data: object) -> Usage | None:
    if type(data) is not dict:
        return None
    prompt_tokens = data.get("prompt_tokens")
    completion_tokens = data.get("completion_tokens")
    total_tokens = data.get("total_tokens")
    if (
        type(prompt_tokens) is not int
        or prompt_tokens <= 0
        or type(completion_tokens) is not int
        or type(total_tokens) is not int
    ):
        return None
    prompt_details = data.get("prompt_tokens_details", {})
    completion_details = data.get("completion_tokens_details", {})
    if type(prompt_details) is not dict or type(completion_details) is not dict:
        return None
    legacy_cached = data.get("cached_tokens", 0)
    cached = prompt_details.get("cached_tokens", legacy_cached)
    cache_write = prompt_details.get("cache_write_tokens", 0)
    reasoning = completion_details.get("reasoning_tokens", 0)
    if (
        type(legacy_cached) is not int
        or legacy_cached < 0
        or type(cached) is not int
        or cached < 0
        or ("cached_tokens" in data and legacy_cached != cached)
        or type(cache_write) is not int
        or cache_write < 0
        or cached + cache_write > prompt_tokens
        or type(reasoning) is not int
        or not 0 <= reasoning <= completion_tokens
    ):
        return None
    try:
        # Kimi includes cache classes in prompt_tokens and reasoning in
        # completion_tokens. The frozen rate bounds every input class.
        return Usage(prompt_tokens, completion_tokens, total_tokens)
    except GatewayError:
        return None


class KimiChatCompletionsAdapter(_BoundedHTTPAdapter):
    def send(
        self,
        request: GatewayRequest,
        policy: ModelPolicy,
        attempt_id: str,
        permit: DispatchPermit | None = None,
    ) -> ProviderReply:
        if not policy.is_kimi:
            raise GatewayError("Kimi Chat Completions policy required")
        dispatch = self._consume_permit(request, policy, attempt_id, permit)
        if policy not in request.policies:
            raise GatewayError("Policy not frozen in logical request")
        inputs = {
            "model": policy.model,
            "messages": [
                {"role": "system", "content": request.instructions},
                {
                    "role": "user",
                    "content": request.context.model_bytes.decode("utf-8"),
                },
            ],
        }
        payload = canonical_bytes(
            {
                **inputs,
                "reasoning_effort": policy.params["reasoning_effort"],
                "max_completion_tokens": policy.max_output_tokens,
                "prompt_cache_options": {"mode": "implicit", "ttl": "5m"},
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "anovel_output",
                        "schema": request.schema,
                        "strict": True,
                    },
                },
                "stream": False,
            }
        )
        context_window = min(policy.context_window, KIMI_PROBE_WINDOW)
        if self._generation_only:
            if (
                request.template_version != KIMI_FIRST_GENERATION_TEMPLATE
                or len(payload) > KIMI_PROBE_WINDOW
            ):
                raise GatewayError(
                    "Generation-only mode requires a bounded first probe"
                )
            base = self._generate(policy, dispatch, payload)
        else:
            base = self._count_and_generate(
                policy,
                dispatch,
                count_endpoint=policy.endpoint.removesuffix(KIMI_CHAT_PATH)
                + "/v1/tokenizers/estimate-token-count",
                count_payload=canonical_bytes(inputs),
                parse_count=_kimi_count,
                generation_payload=payload,
                context_window=context_window,
            )
        if base.http_status != 200:
            return base
        assert base.response_body is not None
        try:
            data = strict_json(base.response_body)
        except ValueError:
            return replace(base, error_code="INVALID_RESPONSE_JSON")
        model = data.get("model")
        model = model if type(model) is str and model.strip() else None
        usage = _kimi_usage(data.get("usage"))
        base = replace(base, observed_model=model, usage=usage)
        if model not in policy.accepted_models:
            return replace(base, error_code="UNEXPECTED_MODEL")
        if usage is not None:
            if usage.output_tokens > policy.max_output_tokens:
                return replace(base, error_code="OUTPUT_TOKEN_LIMIT_EXCEEDED")
            if usage.total_tokens > context_window:
                return replace(base, error_code="INPUT_WINDOW_EXCEEDED")
        choices = data.get("choices")
        if (
            data.get("object") != "chat.completion"
            or type(choices) is not list
            or len(choices) != 1
        ):
            return replace(base, error_code="OUTPUT_SCHEMA_INVALID")
        choice = choices[0]
        if (
            type(choice) is not dict
            or type(choice.get("index")) is not int
            or choice["index"] != 0
        ):
            return replace(base, error_code="OUTPUT_SCHEMA_INVALID")
        message = choice.get("message")
        if type(message) is not dict or message.get("role") != "assistant":
            return replace(base, error_code="OUTPUT_SCHEMA_INVALID")
        if (
            choice.get("finish_reason") == "content_filter"
            or message.get("refusal") is not None
        ):
            return replace(base, error_code="MODEL_REFUSAL")
        if (
            choice.get("finish_reason") != "stop"
            or message.get("tool_calls")
            not in (
                None,
                [],
            )
            or message.get("function_call") is not None
        ):
            return replace(base, error_code="RESPONSE_NOT_COMPLETED")
        content = message.get("content")
        if type(content) is not str:
            return replace(base, error_code="OUTPUT_SCHEMA_INVALID")
        try:
            output = strict_json(content.encode("utf-8"))
            validate_output(request.schema, output)
        except ValueError:
            return replace(base, error_code="OUTPUT_SCHEMA_INVALID")
        if usage is not None and usage.output_tokens == 0:
            # A nonempty JSON answer cannot substantiate zero completion usage.
            base = replace(base, usage=None)
        return replace(base, outcome="SUCCESS", output_bytes=canonical_bytes(output))
