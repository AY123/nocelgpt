from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Literal, Optional, Protocol


Provider = Literal["openai", "deepseek", "claude", "gemini", "kimi", "92code", "local", "mock"]
FinishReason = Literal["stop", "length", "tool_call", "content_filter", "error"]


def now_ms() -> int:
    return int(time.time() * 1000)


def new_request_id() -> str:
    return "LLM-" + uuid.uuid4().hex


def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_obj(obj) -> str:
    import hashlib
    return "sha256:" + hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def to_dict(obj):
    return asdict(obj)


def response_from_dict(data: dict) -> "LLMResponse":
    usage = data["token_usage"]
    cost = data.get("cost")
    return LLMResponse(
        request_id=data["request_id"],
        provider=data["provider"],
        model=data["model"],
        text=data["text"],
        finish_reason=data["finish_reason"],
        token_usage=TokenUsage(**usage),
        cost=CostMetrics(**cost) if cost else None,
        latency_ms=data["latency_ms"],
        response_hash=data["response_hash"],
        provider_request_id=data.get("provider_request_id"),
        replay_ref=data.get("replay_ref"),
        attempts=list(data.get("attempts", [])),
    )


@dataclass(frozen=True)
class ModelVersionPin:
    provider: Provider
    model: str
    adapter_version: str
    api_base: Optional[str] = None
    api_version: Optional[str] = None


@dataclass(frozen=True)
class TemperatureContract:
    temperature: float
    top_p: Optional[float] = None
    seed: Optional[int] = None

    def validate(self) -> None:
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if self.top_p is not None and not 0 <= self.top_p <= 1:
            raise ValueError("top_p must be between 0 and 1")


@dataclass(frozen=True)
class PromptMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class PromptProvenance:
    prompt_id: str
    prompt_hash: str
    template_id: Optional[str]
    template_version: Optional[str]
    package_hash: str
    derived_from: List[str]
    rendered_at: str


@dataclass(frozen=True)
class LLMRequest:
    request_id: str
    capability: str
    messages: List[PromptMessage]
    model_pin: ModelVersionPin
    temperature: TemperatureContract
    timeout_seconds: float
    max_output_tokens: Optional[int]
    prompt_provenance: PromptProvenance
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    usage_estimated: bool = False


@dataclass(frozen=True)
class CostMetrics:
    currency: str
    input_cost: float
    output_cost: float
    total_cost: float
    pricing_version: str


@dataclass(frozen=True)
class LLMResponse:
    request_id: str
    provider: Provider
    model: str
    text: str
    finish_reason: FinishReason
    token_usage: TokenUsage
    cost: Optional[CostMetrics]
    latency_ms: int
    response_hash: str
    provider_request_id: Optional[str]
    replay_ref: Optional[str]
    attempts: List[Dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class LLMStreamEvent:
    request_id: str
    kind: Literal["delta", "usage", "done", "error"]
    text_delta: str = ""
    token_usage: Optional[TokenUsage] = None
    error: Optional[str] = None
    finish_reason: Optional[str] = None
    # On a terminal "done" event the managed client may attach the fully
    # reconstructed response (always so in replay mode, where there is no live
    # token stream). The bridge prefers this over its own delta accumulation.
    response: Optional["LLMResponse"] = None


class LLMClient(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...

    def stream(self, request: LLMRequest) -> Iterable[LLMStreamEvent]: ...
