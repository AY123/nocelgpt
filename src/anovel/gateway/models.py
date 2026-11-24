"""Closed Provider data contracts; no credentials, transport or budget mutation.

Money is integer micro-USD. Usage costs are undiscounted estimates, not verified
bills. Received raw body identities and token-count evidence remain distinct.
"""

from __future__ import annotations

import ipaddress
import math
import re
from abc import ABC, abstractmethod
from base64 import b64decode, b64encode
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from importlib import import_module
from typing import Protocol, cast
from urllib.parse import urlsplit

from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.context.models import ContextArtifact

OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
KIMI_CHAT_PATH = "/v1/chat/completions"
KIMI_CHAT_ENDPOINT = "https://api.moonshot.cn" + KIMI_CHAT_PATH
KIMI_MODEL = "kimi-k3.1-pro"
KIMI_CONTEXT_WINDOW = 1_048_576
KIMI_PROBE_WINDOW = 16_384


class GatewayError(ValueError):
    """Malformed, inconsistent or unsupported Gateway input."""


class BudgetBlocked(GatewayError):
    """The original durable budget does not admit another attempt."""


class IdentityConflict(GatewayError):
    """A scoped stable logical request identity changed its semantics."""


class UnknownRetryRequired(GatewayError):
    """Retry would risk duplicate charges and needs an explicit decision."""


class _SchemaValidator(Protocol):
    def validate(self, instance: object) -> None: ...


class _SchemaFactory(Protocol):
    def __call__(self, schema: dict[str, object]) -> _SchemaValidator: ...

    def check_schema(self, schema: object) -> None: ...


# Describe only public methods of the one locked library without new stubs.
# This literal import is fixed application composition, never a plugin path.
_JSONSCHEMA = import_module("jsonschema")
_SCHEMA_FACTORY = cast(_SchemaFactory, _JSONSCHEMA.Draft202012Validator)
_SCHEMA_ERROR = cast(type[Exception], _JSONSCHEMA.exceptions.SchemaError)
_VALIDATION_ERROR = cast(type[Exception], _JSONSCHEMA.exceptions.ValidationError)


def _local_schema(schema: dict[str, object]) -> None:
    """Avoid implicit external retrieval during offline output validation."""
    pending: list[object] = [schema]
    while pending:
        current = pending.pop()
        if type(current) is dict:
            row = cast(dict[str, object], current)
            for key in ("$ref", "$dynamicRef", "$recursiveRef"):
                if key not in row:
                    continue
                value = row[key]
                if key in {"$ref", "$dynamicRef", "$recursiveRef"} and (
                    type(value) is not str or not value.startswith("#")
                ):
                    raise GatewayError(
                        "response Schema cannot retrieve external references"
                    )
            # Traverse Schema positions, not instance literals such as const /
            # enum or property names that happen to be named "$ref".
            for key in (
                "properties",
                "patternProperties",
                "$defs",
                "definitions",
                "dependentSchemas",
            ):
                mapping = row.get(key)
                if type(mapping) is dict:
                    pending.extend(cast(dict[str, object], mapping).values())
            for key in (
                "additionalProperties",
                "unevaluatedProperties",
                "unevaluatedItems",
                "items",
                "contains",
                "propertyNames",
                "not",
                "if",
                "then",
                "else",
                "contentSchema",
            ):
                if key in row:
                    pending.append(row[key])
            for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
                members = row.get(key)
                if type(members) is list:
                    pending.extend(cast(list[object], members))


def validate_output(schema: dict[str, object], output: object) -> None:
    """Check JSON locally without exposing Schema or generated instance values.

    This is not model-specific Provider subset validation, literary evaluation,
    truth checking, or Canon acceptance.
    """
    if type(schema) is not dict:
        raise GatewayError("response Schema must be an object")
    try:
        canonical_bytes(schema)
        canonical_bytes(output)
        _local_schema(schema)
        _SCHEMA_FACTORY.check_schema(schema)
    except (_SCHEMA_ERROR, _VALIDATION_ERROR, ValueError, TypeError, RecursionError):
        # jsonschema exception text can contain the entire instance and Schema.
        raise GatewayError(
            "structured output does not satisfy the frozen response Schema"
        ) from None
    try:
        _SCHEMA_FACTORY(schema).validate(output)
    except Exception:
        # The library can also raise local-reference resolution errors. Keep
        # that third-party boundary fail-closed without echoing raw instances.
        raise GatewayError(
            "structured output validation could not establish conformity"
        ) from None


def _text(value: object, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise GatewayError(f"{name} must be nonempty text")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise GatewayError(f"{name} must be valid Unicode") from error
    return value


def _int(value: object, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise GatewayError(f"{name} must be an exact integer >= {minimum}")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise GatewayError(f"{name} must be an exact boolean")
    return value


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise GatewayError("expected a complete lowercase SHA256")
    return value


def _utc(value: object, name: str) -> str:
    text = _text(value, name)
    if "T" not in text:
        raise GatewayError(f"{name} requires an aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("timezone missing")
        return (
            parsed.astimezone(UTC)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
    except (ValueError, OverflowError) as error:
        raise GatewayError(f"{name} requires an aware ISO timestamp") from error


def _record(value: object, kind: str, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != {"kind", "schema_version"} | fields:
        raise GatewayError("Gateway fields must be exact and closed")
    row = cast(dict[str, object], value)
    if (row["kind"], row["schema_version"]) != (kind, "1.0"):
        raise GatewayError("unsupported Gateway record kind/version")
    return row


def _array(value: object) -> list[object]:
    if type(value) is not list:
        raise GatewayError("expected a JSON array")
    return cast(list[object], value)


def _members[T](value: object, cls: type[T], name: str) -> tuple[T, ...]:
    if type(value) is not tuple or any(type(v) is not cls for v in value):
        raise GatewayError(f"{name} requires an immutable tuple of exact values")
    return cast(tuple[T, ...], value)


def _bytes(value: object, name: str) -> bytes:
    if type(value) is not bytes or not value:
        raise GatewayError(
            f"{name} must be complete nonempty bytes; use None for no body"
        )
    return value


def _canonical(value: object, name: str) -> bytes:
    raw = _bytes(value, name)
    try:
        if canonical_bytes(decode_canonical(raw)) != raw:
            raise ValueError("noncanonical bytes")
    except ValueError as error:
        raise GatewayError(f"{name} requires canonical JSON bytes") from error
    return raw


def _object(raw: bytes, name: str) -> dict[str, object]:
    value = decode_canonical(raw)
    if type(value) is not dict:
        raise GatewayError(f"{name} must be an object")
    return cast(dict[str, object], value)


def _encoded(value: bytes | None) -> str | None:
    return None if value is None else b64encode(value).decode("ascii")


def _decoded(value: object) -> bytes | None:
    if value is None:
        return None
    if type(value) is not str:
        raise GatewayError("Gateway bytes require base64 strings or null")
    try:
        result = b64decode(value, validate=True)
    except ValueError as error:
        raise GatewayError("invalid base64") from error
    if _encoded(result) != value:
        raise GatewayError("noncanonical base64")
    return result


def _required_decoded(value: object, name: str) -> bytes:
    result = _decoded(value)
    return _bytes(result, name)


def _data(kind: str, fields: dict[str, object]) -> dict[str, object]:
    return {"kind": kind, "schema_version": "1.0", **fields}


def _cost(tokens: int, rate: int) -> int:
    return (tokens * rate + 999_999) // 1_000_000


class _Value(ABC):
    __slots__ = ()

    @abstractmethod
    def to_dict(self) -> dict[str, object]: ...

    def to_bytes(self) -> bytes:
        return canonical_bytes(self.to_dict())

    @property
    def content_hash(self) -> str:
        return sha256(self.to_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class ModelPolicy(_Value):
    id: str
    model: str
    endpoint: str
    context_window: int
    max_output_tokens: int
    input_rate: int
    output_rate: int
    price_ref: str
    price_expires_at: str
    timeout_seconds: int = 30
    params_bytes: bytes = field(default=b"{}", repr=False)
    accepted_models: tuple[str, ...] = ()
    margin_microusd: int = 0
    test_mode: bool = False

    def __post_init__(self) -> None:
        for name in ("id", "model", "endpoint", "price_ref"):
            _text(getattr(self, name), name)
        for name in ("context_window", "max_output_tokens", "timeout_seconds"):
            _int(getattr(self, name), name, 1)
        if self.max_output_tokens > self.context_window:
            raise GatewayError("maximum output exceeds the configured model window")
        for name in ("input_rate", "output_rate", "margin_microusd"):
            _int(getattr(self, name), name)
        _bool(self.test_mode, "test mode")
        try:
            url = urlsplit(self.endpoint)
            port = url.port
        except ValueError as error:
            raise GatewayError("invalid Provider endpoint") from error
        if (
            url.username is not None
            or url.password is not None
            or url.query
            or url.fragment
            or url.path not in {"/v1/responses", KIMI_CHAT_PATH}
        ):
            raise GatewayError(
                "Provider endpoint cannot carry credentials, query or another path"
            )
        if self.test_mode:
            try:
                loopback = url.hostname == "localhost" or (
                    url.hostname is not None
                    and ipaddress.ip_address(url.hostname).is_loopback
                )
            except ValueError:
                loopback = False
            if (
                url.scheme != "http"
                or not loopback
                or (port is not None and not 1 <= port <= 65535)
            ):
                raise GatewayError(
                    "test transport accepts only HTTP loopback endpoints"
                )
        elif self.endpoint not in {OPENAI_RESPONSES_ENDPOINT, KIMI_CHAT_ENDPOINT}:
            raise GatewayError(
                "only the exact configured OpenAI and Kimi endpoints are supported"
            )
        _canonical(self.params_bytes, "model parameters")
        _members(self.accepted_models, str, "accepted models")
        for model in self.accepted_models:
            _text(model, "accepted model")
        if len(set(self.accepted_models)) != len(self.accepted_models):
            raise GatewayError("accepted model identities repeat")
        if not self.accepted_models:
            object.__setattr__(self, "accepted_models", (self.model,))
        if self.is_kimi:
            if self.model != KIMI_MODEL or self.accepted_models != (KIMI_MODEL,):
                raise GatewayError("Kimi policy requires the selected model identity")
            if self.params != {"reasoning_effort": "high"}:
                raise GatewayError("Kimi policy requires frozen high reasoning effort")
            if not self.test_mode and self.context_window != KIMI_CONTEXT_WINDOW:
                raise GatewayError(
                    "Kimi live policy must reserve the full model window"
                )
        else:
            self._validate_openai_parameters()
        object.__setattr__(
            self, "price_expires_at", _utc(self.price_expires_at, "price expiry")
        )

    def _validate_openai_parameters(self) -> None:
        params = self.params
        if not set(params) <= {"temperature", "top_p", "reasoning"}:
            raise GatewayError(
                "parameters cannot override request structure or transport"
            )
        for name in ("temperature", "top_p"):
            if name in params:
                number = params[name]
                if type(number) not in (int, float) or not math.isfinite(
                    cast(int | float, number)
                ):
                    raise GatewayError(f"{name} must be a finite number, not bool")
        if "reasoning" in params and type(params["reasoning"]) is not dict:
            raise GatewayError("reasoning parameters must be an explicit object")

    @property
    def is_kimi(self) -> bool:
        return urlsplit(self.endpoint).path == KIMI_CHAT_PATH

    @property
    def params(self) -> dict[str, object]:
        return _object(self.params_bytes, "model parameters")

    @property
    def reserve_microusd(self) -> int:
        return (
            _cost(self.context_window, self.input_rate)
            + _cost(self.max_output_tokens, self.output_rate)
            + self.margin_microusd
        )

    def to_dict(self) -> dict[str, object]:
        return _data(
            "MODEL_POLICY",
            {
                "id": self.id,
                "model": self.model,
                "endpoint": self.endpoint,
                "context_window": self.context_window,
                "max_output_tokens": self.max_output_tokens,
                "input_rate": self.input_rate,
                "output_rate": self.output_rate,
                "price_ref": self.price_ref,
                "price_expires_at": self.price_expires_at,
                "timeout_seconds": self.timeout_seconds,
                "params_base64": _encoded(self.params_bytes),
                "accepted_models": list(self.accepted_models),
                "margin_microusd": self.margin_microusd,
                "test_mode": self.test_mode,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> ModelPolicy:
        row = _record(
            value,
            "MODEL_POLICY",
            {
                "id",
                "model",
                "endpoint",
                "context_window",
                "max_output_tokens",
                "input_rate",
                "output_rate",
                "price_ref",
                "price_expires_at",
                "timeout_seconds",
                "params_base64",
                "accepted_models",
                "margin_microusd",
                "test_mode",
            },
        )
        return cls(
            _text(row["id"], "id"),
            _text(row["model"], "model"),
            _text(row["endpoint"], "endpoint"),
            _int(row["context_window"], "context window", 1),
            _int(row["max_output_tokens"], "max output", 1),
            _int(row["input_rate"], "input rate"),
            _int(row["output_rate"], "output rate"),
            _text(row["price_ref"], "price ref"),
            _text(row["price_expires_at"], "price expiry"),
            _int(row["timeout_seconds"], "timeout", 1),
            _required_decoded(row["params_base64"], "parameters"),
            tuple(_text(v, "accepted model") for v in _array(row["accepted_models"])),
            _int(row["margin_microusd"], "margin"),
            _bool(row["test_mode"], "test mode"),
        )


@dataclass(frozen=True, slots=True)
class GatewayRequest(_Value):
    project: str
    branch: str
    run_id: str
    logical_id: str
    context: ContextArtifact = field(repr=False)
    instructions: str = field(repr=False)
    template_version: str
    schema_bytes: bytes = field(repr=False)
    policies: tuple[ModelPolicy, ...]

    def __post_init__(self) -> None:
        for name in (
            "project",
            "branch",
            "run_id",
            "logical_id",
            "instructions",
            "template_version",
        ):
            _text(getattr(self, name), name)
        if type(self.context) is not ContextArtifact or (
            self.context.project,
            self.context.branch,
        ) != (self.project, self.branch):
            raise GatewayError(
                "request requires a same-scope role-safe ContextArtifact"
            )
        _canonical(self.schema_bytes, "response Schema")
        schema = self.schema
        try:
            _local_schema(schema)
            _SCHEMA_FACTORY.check_schema(schema)
        except (_SCHEMA_ERROR, ValueError, RecursionError):
            raise GatewayError(
                "response Schema is not valid local Draft2020-12"
            ) from None
        properties = schema.get("properties")
        required = schema.get("required")
        if (
            schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
            or type(properties) is not dict
            or type(required) is not list
            or any(type(v) is not str for v in required)
            or len(required) != len(set(required))
            or set(required) != set(properties)
        ):
            raise GatewayError(
                "structured output needs a closed object with every property required"
            )
        _members(self.policies, ModelPolicy, "allowed policies")
        if not self.policies or len({v.id for v in self.policies}) != len(
            self.policies
        ):
            raise GatewayError(
                "request needs unique, explicitly allowed model policies"
            )

    @property
    def schema(self) -> dict[str, object]:
        return _object(self.schema_bytes, "response Schema")

    @property
    def semantic_hash(self) -> str:
        return self.content_hash

    def to_dict(self) -> dict[str, object]:
        return _data(
            "GATEWAY_REQUEST",
            {
                "project": self.project,
                "branch": self.branch,
                "run_id": self.run_id,
                "logical_id": self.logical_id,
                "context": self.context.to_dict(),
                "instructions": self.instructions,
                "template_version": self.template_version,
                "schema_base64": _encoded(self.schema_bytes),
                "policies": [v.to_dict() for v in self.policies],
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> GatewayRequest:
        row = _record(
            value,
            "GATEWAY_REQUEST",
            {
                "project",
                "branch",
                "run_id",
                "logical_id",
                "context",
                "instructions",
                "template_version",
                "schema_base64",
                "policies",
            },
        )
        return cls(
            _text(row["project"], "project"),
            _text(row["branch"], "branch"),
            _text(row["run_id"], "run ID"),
            _text(row["logical_id"], "logical ID"),
            ContextArtifact.from_dict(row["context"]),
            _text(row["instructions"], "instructions"),
            _text(row["template_version"], "template version"),
            _required_decoded(row["schema_base64"], "Schema"),
            tuple(ModelPolicy.from_dict(v) for v in _array(row["policies"])),
        )


@dataclass(frozen=True, slots=True)
class EstimateFeeBound(_Value):
    """A positive bound for a single estimate, backed by frozen tariff evidence."""

    maximum_microusd: int
    evidence_sha256: str
    expires_at: str

    def __post_init__(self) -> None:
        _int(self.maximum_microusd, "estimate fee upper bound", 1)
        _digest(self.evidence_sha256)
        object.__setattr__(
            self, "expires_at", _utc(self.expires_at, "estimate fee expiry")
        )

    def to_dict(self) -> dict[str, object]:
        return _data(
            "ESTIMATE_FEE_BOUND",
            {
                "maximum_microusd": self.maximum_microusd,
                "evidence_sha256": self.evidence_sha256,
                "expires_at": self.expires_at,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> EstimateFeeBound:
        row = _record(
            value,
            "ESTIMATE_FEE_BOUND",
            {"maximum_microusd", "evidence_sha256", "expires_at"},
        )
        return cls(
            _int(row["maximum_microusd"], "estimate fee upper bound", 1),
            _digest(row["evidence_sha256"]),
            _text(row["expires_at"], "estimate fee expiry"),
        )


@dataclass(frozen=True, slots=True)
class BudgetLimit(_Value):
    project: str
    branch: str
    run_id: str
    total_microusd: int
    max_attempts: int
    deadline_at: str
    max_inflight: int = 1
    max_unknown: int = 1

    def __post_init__(self) -> None:
        for name in ("project", "branch", "run_id"):
            _text(getattr(self, name), name)
        for name in ("total_microusd", "max_attempts", "max_inflight", "max_unknown"):
            _int(getattr(self, name), name, 1)
        object.__setattr__(
            self, "deadline_at", _utc(self.deadline_at, "budget deadline")
        )

    def to_dict(self) -> dict[str, object]:
        return _data(
            "BUDGET_LIMIT",
            {
                "project": self.project,
                "branch": self.branch,
                "run_id": self.run_id,
                "total_microusd": self.total_microusd,
                "max_attempts": self.max_attempts,
                "deadline_at": self.deadline_at,
                "max_inflight": self.max_inflight,
                "max_unknown": self.max_unknown,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> BudgetLimit:
        row = _record(
            value,
            "BUDGET_LIMIT",
            {
                "project",
                "branch",
                "run_id",
                "total_microusd",
                "max_attempts",
                "deadline_at",
                "max_inflight",
                "max_unknown",
            },
        )
        return cls(
            _text(row["project"], "project"),
            _text(row["branch"], "branch"),
            _text(row["run_id"], "run ID"),
            _int(row["total_microusd"], "total microUSD", 1),
            _int(row["max_attempts"], "max attempts", 1),
            _text(row["deadline_at"], "deadline"),
            _int(row["max_inflight"], "max inflight", 1),
            _int(row["max_unknown"], "max unknown", 1),
        )


@dataclass(frozen=True, slots=True)
class Usage(_Value):
    input_tokens: int
    output_tokens: int
    total_tokens: int

    def __post_init__(self) -> None:
        _int(self.input_tokens, "input tokens")
        _int(self.output_tokens, "output tokens")
        _int(self.total_tokens, "total tokens")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise GatewayError("usage total does not equal input plus output")

    def cost(self, policy: ModelPolicy) -> int:
        if type(policy) is not ModelPolicy:
            raise GatewayError("cost estimation requires an exact frozen policy")
        return _cost(self.input_tokens, policy.input_rate) + _cost(
            self.output_tokens, policy.output_rate
        )

    def to_dict(self) -> dict[str, object]:
        return _data(
            "PROVIDER_USAGE",
            {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> Usage:
        row = _record(
            value, "PROVIDER_USAGE", {"input_tokens", "output_tokens", "total_tokens"}
        )
        return cls(
            _int(row["input_tokens"], "input tokens"),
            _int(row["output_tokens"], "output tokens"),
            _int(row["total_tokens"], "total tokens"),
        )


@dataclass(frozen=True, slots=True)
class RetryDecision(_Value):
    authority_ref: str
    reason: str
    accept_unknown: bool = False

    def __post_init__(self) -> None:
        _text(self.authority_ref, "retry authority")
        _text(self.reason, "retry reason")
        _bool(self.accept_unknown, "accept unknown")

    def to_dict(self) -> dict[str, object]:
        return _data(
            "RETRY_DECISION",
            {
                "authority_ref": self.authority_ref,
                "reason": self.reason,
                "accept_unknown": self.accept_unknown,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> RetryDecision:
        row = _record(
            value, "RETRY_DECISION", {"authority_ref", "reason", "accept_unknown"}
        )
        return cls(
            _text(row["authority_ref"], "authority"),
            _text(row["reason"], "reason"),
            _bool(row["accept_unknown"], "accept unknown"),
        )


@dataclass(frozen=True, slots=True)
class ProviderReply(_Value):
    outcome: str
    response_body: bytes | None = field(default=None, repr=False)
    provider_request_id: str | None = None
    observed_model: str | None = None
    usage: Usage | None = None
    output_bytes: bytes | None = field(default=None, repr=False)
    error_code: str | None = None
    http_status: int | None = None
    count_body: bytes | None = field(default=None, repr=False)
    count_request_id: str | None = None
    input_token_count: int | None = None

    def __post_init__(self) -> None:
        if type(self.outcome) is not str or self.outcome not in {
            "SUCCESS",
            "FAILED",
            "UNKNOWN",
        }:
            raise GatewayError("unregistered Provider outcome")
        for name in (
            "provider_request_id",
            "observed_model",
            "error_code",
            "count_request_id",
        ):
            value = getattr(self, name)
            if value is not None:
                _text(value, name)
        for name in ("response_body", "count_body"):
            body = getattr(self, name)
            if body is not None and type(body) is not bytes:
                raise GatewayError(f"{name} must retain actual bytes or None")
        if self.usage is not None and type(self.usage) is not Usage:
            raise GatewayError("usage requires its exact registered type")
        if self.output_bytes is not None:
            _canonical(self.output_bytes, "structured output")
        if self.outcome == "SUCCESS":
            if (
                self.response_body is None
                or self.output_bytes is None
                or self.observed_model is None
            ):
                raise GatewayError(
                    "successful reply requires actual response, output and model"
                )
        elif self.output_bytes is not None:
            raise GatewayError(
                "failed or unknown replies cannot carry successful output"
            )
        if (
            self.http_status is not None
            and not 100 <= _int(self.http_status, "HTTP status", 100) <= 599
        ):
            raise GatewayError("invalid HTTP status")
        if self.input_token_count is not None:
            _int(self.input_token_count, "input token count")
            if self.count_body is None:
                raise GatewayError(
                    "input count must retain its actual counting response body"
                )

    @property
    def response_hash(self) -> str | None:
        return (
            None
            if self.response_body is None
            else sha256(self.response_body).hexdigest()
        )

    @property
    def count_hash(self) -> str | None:
        return None if self.count_body is None else sha256(self.count_body).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return _data(
            "PROVIDER_REPLY",
            {
                "outcome": self.outcome,
                "response_base64": _encoded(self.response_body),
                "response_hash": self.response_hash,
                "provider_request_id": self.provider_request_id,
                "observed_model": self.observed_model,
                "usage": None if self.usage is None else self.usage.to_dict(),
                "output_base64": _encoded(self.output_bytes),
                "error_code": self.error_code,
                "http_status": self.http_status,
                "count_base64": _encoded(self.count_body),
                "count_hash": self.count_hash,
                "count_request_id": self.count_request_id,
                "input_token_count": self.input_token_count,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> ProviderReply:
        row = _record(
            value,
            "PROVIDER_REPLY",
            {
                "outcome",
                "response_base64",
                "response_hash",
                "provider_request_id",
                "observed_model",
                "usage",
                "output_base64",
                "error_code",
                "http_status",
                "count_base64",
                "count_hash",
                "count_request_id",
                "input_token_count",
            },
        )
        result = cls(
            _text(row["outcome"], "outcome"),
            _decoded(row["response_base64"]),
            None
            if row["provider_request_id"] is None
            else _text(row["provider_request_id"], "Provider request ID"),
            None
            if row["observed_model"] is None
            else _text(row["observed_model"], "model"),
            None if row["usage"] is None else Usage.from_dict(row["usage"]),
            _decoded(row["output_base64"]),
            None
            if row["error_code"] is None
            else _text(row["error_code"], "error code"),
            None
            if row["http_status"] is None
            else _int(row["http_status"], "HTTP status", 100),
            _decoded(row["count_base64"]),
            None
            if row["count_request_id"] is None
            else _text(row["count_request_id"], "count request ID"),
            None
            if row["input_token_count"] is None
            else _int(row["input_token_count"], "input token count"),
        )
        if (
            row["response_hash"] != result.response_hash
            or row["count_hash"] != result.count_hash
        ):
            raise GatewayError("retained Provider response/count hash mismatch")
        return result


@dataclass(frozen=True, slots=True)
class GatewayResult(_Value):
    project: str
    branch: str
    run_id: str
    logical_id: str
    attempt_id: str
    request_hash: str
    policy_hash: str
    started_at: str
    finished_at: str
    reply: ProviderReply
    charge_status: str
    charge_microusd: int | None
    reserved_microusd: int
    replayed: bool = False

    def __post_init__(self) -> None:
        for name in ("project", "branch", "run_id", "logical_id", "attempt_id"):
            _text(getattr(self, name), name)
        _digest(self.request_hash)
        _digest(self.policy_hash)
        object.__setattr__(self, "started_at", _utc(self.started_at, "started at"))
        object.__setattr__(self, "finished_at", _utc(self.finished_at, "finished at"))
        if self.finished_at < self.started_at:
            raise GatewayError("result cannot finish before it started")
        if type(self.reply) is not ProviderReply:
            raise GatewayError("result requires an actual Provider reply")
        if type(self.charge_status) is not str or self.charge_status not in {
            "ESTIMATED",
            "PENDING",
            "VERIFIED",
        }:
            raise GatewayError("unregistered charge status")
        if self.charge_status == "PENDING":
            if self.charge_microusd is not None:
                raise GatewayError("pending charge must not pretend a settled amount")
        elif self.charge_microusd is None:
            raise GatewayError(
                "estimated or verified charge requires an explicit amount"
            )
        if self.charge_microusd is not None:
            _int(self.charge_microusd, "charge microUSD")
        _int(self.reserved_microusd, "reserved microUSD")
        _bool(self.replayed, "replayed")

    @property
    def status(self) -> str:
        return self.reply.outcome

    def to_dict(self) -> dict[str, object]:
        return _data(
            "GATEWAY_RESULT",
            {
                "project": self.project,
                "branch": self.branch,
                "run_id": self.run_id,
                "logical_id": self.logical_id,
                "attempt_id": self.attempt_id,
                "request_hash": self.request_hash,
                "policy_hash": self.policy_hash,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "reply": self.reply.to_dict(),
                "charge_status": self.charge_status,
                "charge_microusd": self.charge_microusd,
                "reserved_microusd": self.reserved_microusd,
                "replayed": self.replayed,
                "status": self.status,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> GatewayResult:
        row = _record(
            value,
            "GATEWAY_RESULT",
            {
                "project",
                "branch",
                "run_id",
                "logical_id",
                "attempt_id",
                "request_hash",
                "policy_hash",
                "started_at",
                "finished_at",
                "reply",
                "charge_status",
                "charge_microusd",
                "reserved_microusd",
                "replayed",
                "status",
            },
        )
        result = cls(
            _text(row["project"], "project"),
            _text(row["branch"], "branch"),
            _text(row["run_id"], "run ID"),
            _text(row["logical_id"], "logical ID"),
            _text(row["attempt_id"], "attempt ID"),
            _digest(row["request_hash"]),
            _digest(row["policy_hash"]),
            _text(row["started_at"], "started at"),
            _text(row["finished_at"], "finished at"),
            ProviderReply.from_dict(row["reply"]),
            _text(row["charge_status"], "charge status"),
            None
            if row["charge_microusd"] is None
            else _int(row["charge_microusd"], "charge microUSD"),
            _int(row["reserved_microusd"], "reserve microUSD"),
            _bool(row["replayed"], "replayed"),
        )
        if row["status"] != result.status:
            raise GatewayError("result status differs from its Provider reply")
        return result
