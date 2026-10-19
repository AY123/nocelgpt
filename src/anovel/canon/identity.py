"""ADR-005 byte identities; content identity never grants commit authority.

ANOVELOS-CJSON-1 preserves Unicode and array order. Its exact finite numeric
encoding is a project format, not a claim of JCS compatibility. PostgreSQL must
retain these bytes rather than regenerate them from a JSON projection.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from typing import cast

CANONICAL_ENCODING = "ANOVELOS-CJSON-1"
MAX_NESTING_DEPTH = 64
_INTEGER_BASE = 1_000_000_000
_ESCAPES = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


def _integer_text(value: int) -> str:
    """Do not depend on the interpreter's configurable integer string limit."""
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    remaining = abs(value)
    parts: list[int] = []
    while remaining:
        remaining, part = divmod(remaining, _INTEGER_BASE)
        parts.append(part)
    return (
        sign + str(parts[-1]) + "".join(f"{part:09d}" for part in reversed(parts[:-1]))
    )


def _parse_integer(text: str) -> int:
    negative = text.startswith("-")
    digits = text[1:] if negative else text
    value = 0
    for start in range(0, len(digits), 9):
        chunk = digits[start : start + 9]
        value = value * (10 ** len(chunk)) + int(chunk)
    return -value if negative else value


def _number_text(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("canonical numbers must be finite")
    numerator, denominator = value.as_integer_ratio()
    if numerator == 0:
        return "0"
    scale = denominator.bit_length() - 1
    sign = "-" if numerator < 0 else ""
    digits = _integer_text(abs(numerator) * 5**scale)
    if scale == 0:
        return sign + digits
    digits = digits.zfill(scale + 1)
    return sign + (digits[:-scale] + "." + digits[-scale:]).rstrip("0")


def _string_text(value: str) -> str:
    parts = ['"']
    for character in value:
        point = ord(character)
        if 0xD800 <= point <= 0xDFFF:
            raise ValueError("canonical strings cannot contain surrogates")
        if character in _ESCAPES:
            parts.append(_ESCAPES[character])
        elif point < 0x20:
            parts.append(f"\\u{point:04x}")
        else:
            parts.append(character)
    parts.append('"')
    return "".join(parts)


def _encode(value: object, depth: int, ancestors: set[int]) -> str:
    if depth > MAX_NESTING_DEPTH:
        raise ValueError("canonical value exceeds nesting depth limit")
    kind = type(value)
    if value is None:
        return "null"
    if kind is bool:
        return "true" if value else "false"
    if kind is int:
        return _integer_text(cast(int, value))
    if kind is float:
        return _number_text(cast(float, value))
    if kind is str:
        return _string_text(cast(str, value))
    if kind not in (dict, list):
        raise ValueError("canonical value must use exact JSON primitive types")
    identity = id(value)
    if identity in ancestors:
        raise ValueError("canonical value cannot contain a cycle")
    ancestors.add(identity)
    try:
        if kind is list:
            return (
                "["
                + ",".join(
                    _encode(item, depth + 1, ancestors)
                    for item in cast(list[object], value)
                )
                + "]"
            )
        record = cast(dict[object, object], value)
        if any(type(key) is not str for key in record):
            raise ValueError("canonical object keys must be exact strings")
        typed_record = cast(dict[str, object], record)
        return (
            "{"
            + ",".join(
                _string_text(key)
                + ":"
                + _encode(typed_record[key], depth + 1, ancestors)
                for key in sorted(typed_record)
            )
            + "}"
        )
    finally:
        ancestors.remove(identity)


def canonical_bytes(value: object) -> bytes:
    """Encode exact JSON types, with root depth zero and at most 64 edges."""
    return _encode(value, 0, set()).encode("utf-8")


def content_hash(value: object) -> str:
    """Hash the canonical bytes, returning a lowercase SHA-256 digest."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _utf8(value: bytes) -> str:
    if type(value) is not bytes:
        raise ValueError("content must be exact bytes")
    try:
        return value.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("content must contain valid UTF-8") from error


def raw_prose_hash(value: bytes) -> str:
    """Validate UTF-8 but hash the unchanged original bytes, including BOM."""
    _utf8(value)
    return hashlib.sha256(value).hexdigest()


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("canonical objects cannot contain duplicate keys")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError("canonical numbers must be finite")


def decode_canonical(value: bytes) -> object:
    """Reject syntactically valid JSON whose bytes are not ANOVELOS-CJSON-1."""
    text = _utf8(value)
    try:
        decoded: object = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_int=_parse_integer,
            parse_constant=_reject_constant,
        )
    except (ValueError, RecursionError) as error:
        raise ValueError("invalid canonical JSON") from error
    if canonical_bytes(decoded) != value:
        raise ValueError("JSON bytes are not canonical")
    return decoded


def utc_timestamp(value: datetime) -> str:
    """Normalize an aware system timestamp; fictional time is a domain type."""
    if type(value) is not datetime or value.utcoffset() is None:
        raise ValueError("system timestamp must be an aware datetime")
    try:
        normalized = value.astimezone(UTC)
    except (ValueError, OverflowError) as error:
        raise ValueError(
            "system timestamp is outside the UTC datetime range"
        ) from error
    return (
        f"{normalized.year:04d}-{normalized.month:02d}-{normalized.day:02d}"
        f"T{normalized.hour:02d}:{normalized.minute:02d}:{normalized.second:02d}"
        f".{normalized.microsecond:06d}Z"
    )
