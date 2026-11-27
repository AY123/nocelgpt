"""Finite raw Contract checks, never natural-prose certification or authority.

Discovery sees only raw bytes and value-free identities. Inventory is sealed
before proposal discovery; Contract and author knowledge enter only comparison.
Decoding audits retained outputs without running a discovery producer. The local
publication token is cooperative process identity, not hostile-owner protection.
"""

from __future__ import annotations

import json
import re
from base64 import b64decode, b64encode
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from hashlib import sha256
from math import isfinite
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from anovel.canon.identity import canonical_bytes, decode_canonical, utc_timestamp
from anovel.contracts.models import (
    CanonView,
    CompiledContract,
    ContinuationEvidence,
    KnowledgeSnapshot,
)
from anovel.domain.delta import (
    FactState,
    FactStatus,
    Precondition,
    ScalarKind,
)
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import EntityId
from anovel.domain.knowledge import Scalar
from anovel.planning.models import StoryFixture

if TYPE_CHECKING:
    from anovel.workflow.extractor import ExactSpan, ExtractionObservation

PROFILE = "LOCAL_RAW_CONTRACT_V1"
METHOD_DOCUMENT_HASH = (
    "bf0550192a26a0d5c445535ac016affa8455d029bdb5fc3e08c816475adffac0"
)
INVENTORY_PRODUCER = "q3-independent-inventory/1.0"
PROPOSAL_PRODUCER = "q3-regex-proposal/1.0"
CHECK_IDS = (
    "Q3_RAW_INVENTORY_V1",
    "Q3_RAW_PROPOSAL_V1",
    "Q3_RAW_CORRESPONDENCE_V1",
    "Q3_TRANSITIONS_V1",
    "Q3_CONTINUATION_V1",
    "Q3_KNOWLEDGE_REVEAL_V1",
)
QUIET_SENTENCE = "风掠过窗边。"
_ACTIONS = {
    "关上": "CLOSE",
    "关闭": "CLOSE",
    "打开": "OPEN",
    "交付": "DELIVER",
    "接收": "RECEIVE",
}
_CONTEXTS = {
    "并非": "NEGATED",
    "听说": "RUMOR",
    "误信": "BELIEF",
    "梦中": "DREAM",
    "计划": "PLANNED",
    "回忆": "RECOLLECTION",
}
_JSON = r'"(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"|true|false|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?'
_FACT_RX = re.compile(r"(.+?)(变为|仍为)(" + _JSON + r")。")
_ACTION_RX = re.compile(
    r"(.+?)在(.+?)于(.+?)(关上|关闭|打开|交付|接收)(.+?)，(已经完成|尚未完成)。"
)
_KNOW_RX = re.compile(
    r"(.+?)根据已知事实“(.+?)为(" + _JSON + r")”选择(关上|关闭|打开|交付|接收)。"
)
_BELIEF_RX = re.compile(
    r"(.+?)根据自己的误信(.+?)“(.+?)为(" + _JSON + r")”选择(关上|关闭|打开|交付|接收)。"
)
_ACQUIRE_RX = re.compile(r"(.+?)获知：(.+?)为(" + _JSON + r")。")
_REVEAL_RX = re.compile(r"此处向读者揭示：(.+?)为(" + _JSON + r")。")
METHOD_POLICY_BYTES = canonical_bytes(
    {
        "profile": PROFILE,
        "document_hash": METHOD_DOCUMENT_HASH,
        "checks": list(CHECK_IDS),
        "actions": _ACTIONS,
        "contexts": _CONTEXTS,
        "grammar": [
            _FACT_RX.pattern,
            _ACTION_RX.pattern,
            _KNOW_RX.pattern,
            _BELIEF_RX.pattern,
            _ACQUIRE_RX.pattern,
            _REVEAL_RX.pattern,
        ],
        "quiet": QUIET_SENTENCE,
        "time": "EXACT_ISO8601_SECONDS_WITH_OFFSET",
        "coordinate": "EXACT_UTF8_AND_CODEPOINT_HALF_OPEN_SCENE_CONTAINMENT",
        "dependencies": [[], [], [0, 1], [0], [0], [0]],
        "scope": "SCENE_NOT_CHAPTER_UNION",
        "production": "UNKNOWN_BLOCKED",
        "multiple_transitions": "PRESERVE_PROCESS_UNKNOWN_ENCODING_FAIL_SURVIVES",
    }
)
METHOD_POLICY_HASH = sha256(METHOD_POLICY_BYTES).hexdigest()
_TOKEN = object()
_FALSE = {
    "can_commit": False,
    "can_issue_permit": False,
    "can_dispatch": False,
    "accepted": False,
    "published": False,
}


class Q3Error(ValueError):
    """Stable diagnostics do not interpolate private prose."""


def _hash(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _row(value: object, keys: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise Q3Error("INVALID_Q3_RECORD")
    return cast(dict[str, object], value)


def _encode(raw: bytes) -> str:
    return b64encode(raw).decode("ascii")


def _decode(value: object) -> bytes:
    if type(value) is not str:
        raise Q3Error("INVALID_Q3_BYTES")
    raw = b64decode(value, validate=True)
    if _encode(raw) != value:
        raise Q3Error("INVALID_Q3_BYTES")
    return raw


def _text(raw: bytes) -> str:
    if type(raw) is not bytes or not raw:
        raise Q3Error("INVALID_Q3_PROSE")
    return raw.decode("utf-8")


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise Q3Error("INVALID_Q3_HASH")
    return value


def _scalar(raw: str) -> Scalar:
    value = json.loads(raw)
    if type(value) not in (str, bool, int, float) or (
        type(value) is float and not isfinite(value)
    ):
        raise ValueError
    return cast(Scalar, value)


def _kind(value: Scalar) -> str:
    return (
        ScalarKind.BOOLEAN.value
        if type(value) is bool
        else ScalarKind.STRING.value
        if type(value) is str
        else ScalarKind.NUMBER.value
    )


def _instant(raw: str) -> str:
    if re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:Z|[+-]\d\d:\d\d)", raw) is None:
        raise ValueError
    return utc_timestamp(datetime.fromisoformat(raw).astimezone(UTC))


@dataclass(frozen=True, slots=True)
class Q3Alias:
    identity: EntityId
    alias: str
    kind: str
    value_kind: str | None = None

    def __post_init__(self) -> None:
        if (
            type(self.identity) is not EntityId
            or type(self.alias) is not str
            or not self.alias
            or any(c in self.alias for c in "\r\n。：“”")
            or self.kind not in {"ENTITY", "FACT", "BELIEF"}
        ):
            raise Q3Error("INVALID_Q3_ALIAS")
        if (
            self.kind == "FACT" and self.value_kind not in {v.value for v in ScalarKind}
        ) or (self.kind != "FACT" and self.value_kind is not None):
            raise Q3Error("INVALID_Q3_ALIAS")

    def to_dict(self) -> dict[str, object]:
        return {
            "identity": self.identity.to_dict(),
            "alias": self.alias,
            "kind": self.kind,
            "value_kind": self.value_kind,
        }

    @classmethod
    def from_dict(cls, value: object) -> Q3Alias:
        row = _row(value, {"identity", "alias", "kind", "value_kind"})
        return cls(
            EntityId.from_dict(row["identity"]),
            cast(str, row["alias"]),
            cast(str, row["kind"]),
            cast(str | None, row["value_kind"]),
        )


def _catalog(catalog: tuple[Q3Alias, ...]) -> tuple[Q3Alias, ...]:
    if type(catalog) is not tuple or any(type(v) is not Q3Alias for v in catalog):
        raise Q3Error("INVALID_Q3_CATALOG")
    ordered = tuple(
        sorted(
            catalog,
            key=lambda v: (v.kind, v.alias, v.identity.project, v.identity.local_id),
        )
    )
    if len({canonical_bytes(v.to_dict()) for v in ordered}) != len(ordered):
        raise Q3Error("INVALID_Q3_CATALOG")
    return ordered


def _resolve(catalog: tuple[Q3Alias, ...], alias: str, kind: str) -> Q3Alias:
    found = tuple(v for v in catalog if v.alias == alias and v.kind == kind)
    if len(found) != 1:
        raise ValueError
    return found[0]


def _ranges(text: str) -> tuple[tuple[int, int], ...]:
    """Raw coordinate scanning only; no shared classified AST."""
    ranges: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(text):
        start = cursor
        if text[cursor].isspace() or (cursor == 0 and text[cursor] == "\ufeff"):
            cursor += 1
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
        else:
            chinese, ascii_quote, escaped = 0, False, False
            while cursor < len(text):
                char = text[cursor]
                cursor += 1
                if escaped:
                    escaped = False
                elif ascii_quote and char == "\\":
                    escaped = True
                elif char == '"':
                    ascii_quote = not ascii_quote
                elif not ascii_quote and char == "“":
                    chinese += 1
                elif not ascii_quote and char == "”":
                    chinese = max(0, chinese - 1)
                    if (
                        chinese == 0
                        and cursor > start
                        and text[start:].startswith(("引用：“", "梦境：“"))
                    ):
                        break
                elif not ascii_quote and chinese == 0 and char == "。":
                    break
        ranges.append((start, cursor))
    return tuple(ranges)


def _proposal_parse(
    body: str, catalog: tuple[Q3Alias, ...]
) -> tuple[str, dict[str, object]]:
    """Anchored regex discovery; no inventory or frozen values."""
    if match := _BELIEF_RX.fullmatch(body):
        holder, belief, fact = (
            _resolve(catalog, match[1], "ENTITY"),
            _resolve(catalog, match[2], "BELIEF"),
            _resolve(catalog, match[3], "FACT"),
        )
        value = _scalar(match[4])
        return "BELIEF_CHOICE", {
            "holder": holder.identity.to_dict(),
            "belief_id": belief.identity.to_dict(),
            "fact_id": fact.identity.to_dict(),
            "value": value,
            "action": _ACTIONS[match[5]],
        }
    if match := _KNOW_RX.fullmatch(body):
        holder, fact = (
            _resolve(catalog, match[1], "ENTITY"),
            _resolve(catalog, match[2], "FACT"),
        )
        value = _scalar(match[3])
        return "KNOWLEDGE_USE", {
            "holder": holder.identity.to_dict(),
            "fact_id": fact.identity.to_dict(),
            "value": value,
            "action": _ACTIONS[match[4]],
        }
    if match := _ACQUIRE_RX.fullmatch(body):
        holder, fact = (
            _resolve(catalog, match[1], "ENTITY"),
            _resolve(catalog, match[2], "FACT"),
        )
        value = _scalar(match[3])
        return "ACQUISITION", {
            "holder": holder.identity.to_dict(),
            "fact_id": fact.identity.to_dict(),
            "value": value,
        }
    if match := _REVEAL_RX.fullmatch(body):
        fact = _resolve(catalog, match[1], "FACT")
        value = _scalar(match[2])
        return "READER_REVEAL", {"fact_id": fact.identity.to_dict(), "value": value}
    entities = (
        "(?:"
        + "|".join(re.escape(v.alias) for v in catalog if v.kind == "ENTITY")
        + ")"
    )
    action_rx = re.compile(
        "("
        + entities
        + r")在(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:Z|[+-]\d\d:\d\d))于("
        + entities
        + r")(关上|关闭|打开|交付|接收)("
        + entities
        + r")，(已经完成|尚未完成)。"
    )
    if match := action_rx.fullmatch(body):
        actor, place, target = (
            _resolve(catalog, match[1], "ENTITY"),
            _resolve(catalog, match[3], "ENTITY"),
            _resolve(catalog, match[5], "ENTITY"),
        )
        return "ACTION", {
            "actor": actor.identity.to_dict(),
            "place": place.identity.to_dict(),
            "object": target.identity.to_dict(),
            "at": _instant(match[2]),
            "action": _ACTIONS[match[4]],
            "completed": match[6] == "已经完成",
        }
    if match := _FACT_RX.fullmatch(body):
        fact, value = _resolve(catalog, match[1], "FACT"), _scalar(match[3])
        return "FACT", {
            "fact_id": fact.identity.to_dict(),
            "operation": "SET_FACT" if match[2] == "变为" else "NO_CHANGE",
            "value": value,
            "path": "proposition.value",
            "operation_version": "1.0",
        }
    raise ValueError


def _syntax_mask(text: str) -> str:
    """Hide JSON string contents while locating grammar delimiters."""
    chars = list(text)
    quoted, escaped = False, False
    for index, char in enumerate(text):
        if escaped:
            chars[index] = "\0"
            escaped = False
        elif quoted and char == "\\":
            chars[index] = "\0"
            escaped = True
        elif char == '"':
            quoted = not quoted
            chars[index] = "\0"
        elif quoted:
            chars[index] = "\0"
    return "".join(chars)


def _inventory_proposition(
    text: str, catalog: tuple[Q3Alias, ...]
) -> tuple[Q3Alias, Scalar]:
    candidates: list[tuple[Q3Alias, Scalar]] = []
    for entry in catalog:
        prefix = entry.alias + "为"
        if entry.kind == "FACT" and text.startswith(prefix):
            try:
                candidates.append((entry, _scalar(text[len(prefix) :])))
            except (ValueError, TypeError):
                pass
    if len(candidates) != 1:
        raise ValueError
    return candidates[0]


def _inventory_parse(
    body: str, catalog: tuple[Q3Alias, ...]
) -> tuple[str, dict[str, object]]:
    """Independent delimiter scanner; never calls proposal regex/classifier."""
    if not body.endswith("。"):
        raise ValueError
    content = body[:-1]
    syntax = _syntax_mask(content)
    if "根据自己的误信" in syntax:
        actor, rest = content.split("根据自己的误信", 1)
        belief_name, quoted = rest.split("“", 1)
        proposition, action = quoted.rsplit("”选择", 1)
        fact, value = _inventory_proposition(proposition, catalog)
        holder, belief = (
            _resolve(catalog, actor, "ENTITY"),
            _resolve(catalog, belief_name, "BELIEF"),
        )
        if action not in _ACTIONS:
            raise ValueError
        return "BELIEF_CHOICE", {
            "holder": holder.identity.to_dict(),
            "belief_id": belief.identity.to_dict(),
            "fact_id": fact.identity.to_dict(),
            "value": value,
            "action": _ACTIONS[action],
        }
    if "根据已知事实“" in syntax:
        actor, quoted = content.split("根据已知事实“", 1)
        proposition, action = quoted.rsplit("”选择", 1)
        fact, value = _inventory_proposition(proposition, catalog)
        holder = _resolve(catalog, actor, "ENTITY")
        if action not in _ACTIONS:
            raise ValueError
        return "KNOWLEDGE_USE", {
            "holder": holder.identity.to_dict(),
            "fact_id": fact.identity.to_dict(),
            "value": value,
            "action": _ACTIONS[action],
        }
    if "获知：" in syntax:
        actor, proposition = content.split("获知：", 1)
        fact, value = _inventory_proposition(proposition, catalog)
        holder = _resolve(catalog, actor, "ENTITY")
        return "ACQUISITION", {
            "holder": holder.identity.to_dict(),
            "fact_id": fact.identity.to_dict(),
            "value": value,
        }
    if content.startswith("此处向读者揭示："):
        fact, value = _inventory_proposition(
            content.removeprefix("此处向读者揭示："), catalog
        )
        return "READER_REVEAL", {"fact_id": fact.identity.to_dict(), "value": value}
    if content.endswith(("，已经完成", "，尚未完成")):
        core, completion = content.rsplit("，", 1)
        entities = [v for v in catalog if v.kind == "ENTITY"]
        actions: list[dict[str, object]] = []
        for actor_entry in entities:
            prefix = actor_entry.alias + "在"
            if not core.startswith(prefix):
                continue
            temporal, marker, located = core[len(prefix) :].partition("于")
            if not marker:
                continue
            try:
                at = _instant(temporal)
            except (ValueError, OverflowError):
                continue
            for place in entities:
                for verb, action in _ACTIONS.items():
                    for target in entities:
                        if located == place.alias + verb + target.alias:
                            actions.append(
                                {
                                    "actor": actor_entry.identity.to_dict(),
                                    "place": place.identity.to_dict(),
                                    "object": target.identity.to_dict(),
                                    "at": at,
                                    "action": action,
                                    "completed": completion == "已经完成",
                                }
                            )
        unique = {canonical_bytes(v): v for v in actions}
        if len(unique) != 1:
            raise ValueError
        return "ACTION", next(iter(unique.values()))
    matches: list[tuple[Q3Alias, str, Scalar]] = []
    for entry in catalog:
        if entry.kind != "FACT":
            continue
        for verb in ("变为", "仍为"):
            prefix = entry.alias + verb
            if content.startswith(prefix):
                try:
                    matches.append((entry, verb, _scalar(content[len(prefix) :])))
                except (ValueError, TypeError):
                    pass
    if len(matches) != 1:
        raise ValueError
    fact, verb, value = matches[0]
    return "FACT", {
        "fact_id": fact.identity.to_dict(),
        "operation": "SET_FACT" if verb == "变为" else "NO_CHANGE",
        "value": value,
        "path": "proposition.value",
        "operation_version": "1.0",
    }


@dataclass(frozen=True, slots=True)
class Q3Segment:
    kind: str
    span: ExactSpan
    context: str = "WORLD"
    claim_type: str | None = None
    data: bytes | None = field(default=None, repr=False)
    pov: EntityId | None = None

    def __post_init__(self) -> None:
        from anovel.workflow.extractor import ExactSpan

        if (
            type(self.span) is not ExactSpan
            or self.kind not in {"CLAIM", "QUIET", "WHITESPACE", "UNSUPPORTED"}
            or self.context
            not in {"WORLD", "QUOTATION", "ALTERNATE_VIEWPOINT", *_CONTEXTS.values()}
        ):
            raise Q3Error("INVALID_Q3_SEGMENT")
        if self.kind == "CLAIM":
            keys = {
                "FACT": {"fact_id", "operation", "value", "path", "operation_version"},
                "ACTION": {"actor", "place", "object", "at", "action", "completed"},
                "KNOWLEDGE_USE": {"holder", "fact_id", "value", "action"},
                "ACQUISITION": {"holder", "fact_id", "value"},
                "BELIEF_CHOICE": {"holder", "belief_id", "fact_id", "value", "action"},
                "READER_REVEAL": {"fact_id", "value"},
            }
            if self.claim_type not in keys or type(self.data) is not bytes:
                raise Q3Error("INVALID_Q3_SEGMENT")
            payload = _row(decode_canonical(self.data), keys[self.claim_type])
            for key in set(payload) & {
                "actor",
                "place",
                "object",
                "holder",
                "fact_id",
                "belief_id",
            }:
                EntityId.from_dict(payload[key])
            if "value" in payload:
                _scalar(json.dumps(payload["value"]))
            if "action" in payload and payload["action"] not in _ACTIONS.values():
                raise Q3Error("INVALID_Q3_SEGMENT")
            if self.claim_type == "FACT" and (
                payload["operation"] not in {"SET_FACT", "NO_CHANGE"}
                or payload["operation_version"] != "1.0"
                or payload["path"] != "proposition.value"
            ):
                raise Q3Error("INVALID_Q3_SEGMENT")
            if self.claim_type == "ACTION" and (
                type(payload["completed"]) is not bool
                or _instant(cast(str, payload["at"]).replace(".000000Z", "Z"))
                != payload["at"]
            ):
                raise Q3Error("INVALID_Q3_SEGMENT")
        elif (
            self.claim_type is not None
            or self.data is not None
            or self.context != "WORLD"
            or self.pov is not None
        ):
            raise Q3Error("INVALID_Q3_SEGMENT")
        if (self.context == "ALTERNATE_VIEWPOINT") != (self.pov is not None):
            raise Q3Error("INVALID_Q3_SEGMENT")

    @property
    def values(self) -> dict[str, object]:
        return (
            {}
            if self.data is None
            else cast(dict[str, object], decode_canonical(self.data))
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "span": self.span.to_dict(),
            "context": self.context,
            "claim_type": self.claim_type,
            "data": None if self.data is None else self.values,
            "pov": None if self.pov is None else self.pov.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> Q3Segment:
        from anovel.workflow.extractor import ExactSpan

        row = _row(value, {"kind", "span", "context", "claim_type", "data", "pov"})
        return cls(
            cast(str, row["kind"]),
            ExactSpan.from_dict(row["span"]),
            cast(str, row["context"]),
            cast(str | None, row["claim_type"]),
            None if row["data"] is None else canonical_bytes(row["data"]),
            None if row["pov"] is None else EntityId.from_dict(row["pov"]),
        )


def _inventory_segment(
    prose: bytes, catalog: tuple[Q3Alias, ...], span: ExactSpan
) -> Q3Segment:
    body, context, pov = span.quote, "WORLD", None
    if not body.strip("\ufeff \t\r\n"):
        return Q3Segment("WHITESPACE", span)
    if body == QUIET_SENTENCE:
        return Q3Segment("QUIET", span)
    try:
        if body.startswith("从") and "看过去：" in body:
            alias, body = body[1:].split("看过去：", 1)
            pov, context = (
                _resolve(catalog, alias, "ENTITY").identity,
                "ALTERNATE_VIEWPOINT",
            )
        elif body.startswith(("引用：“", "梦境：“")) and body.endswith("”"):
            marker, body = body.split("：“", 1)
            body, context = (
                body[:-1],
                "QUOTATION" if marker == "引用" else "DREAM",
            )
        elif body.startswith("回忆："):
            body, context = body[len("回忆：") :], "RECOLLECTION"
        else:
            for prefix, label in _CONTEXTS.items():
                if body.startswith(prefix):
                    body, context = body[len(prefix) :], label
                    break
        claim_type, data = _inventory_parse(body, catalog)
        return Q3Segment("CLAIM", span, context, claim_type, canonical_bytes(data), pov)
    except (ValueError, TypeError, KeyError, OverflowError):
        return Q3Segment("UNSUPPORTED", span)


def _discover(prose: bytes, catalog: tuple[Q3Alias, ...], *, inventory: bool) -> bytes:
    from anovel.workflow.extractor import ExactSpan

    text, catalog = _text(prose), _catalog(catalog)
    segments: list[Q3Segment] = []
    for start, end in _ranges(text):
        body, context, pov = text[start:end], "WORLD", None
        span = ExactSpan.from_source(prose, start, end)
        if inventory:
            segments.append(_inventory_segment(prose, catalog, span))
            continue
        if not body.strip("\ufeff \t\r\n"):
            segments.append(Q3Segment("WHITESPACE", span))
            continue
        if body == QUIET_SENTENCE:
            segments.append(Q3Segment("QUIET", span))
            continue
        try:
            # Wrapper recognition is separately implemented for the two paths.
            if match := re.fullmatch(r"从(.+?)看过去：(.+)", body, re.DOTALL):
                pov, context, body = (
                    _resolve(catalog, match[1], "ENTITY").identity,
                    "ALTERNATE_VIEWPOINT",
                    match[2],
                )
            elif match := re.fullmatch(r"(引用|梦境)：“(.+)”", body, re.DOTALL):
                context, body = (
                    "QUOTATION" if match[1] == "引用" else "DREAM",
                    match[2],
                )
            elif body.startswith("回忆："):
                context, body = "RECOLLECTION", body[3:]
            elif match := re.fullmatch(
                r"(并非|听说|误信|梦中|计划|回忆)(.+)", body, re.DOTALL
            ):
                context, body = _CONTEXTS[match[1]], match[2]
            claim_type, data = _proposal_parse(body, catalog)
            segments.append(
                Q3Segment(
                    "CLAIM", span, context, claim_type, canonical_bytes(data), pov
                )
            )
        except (ValueError, TypeError, KeyError, OverflowError):
            segments.append(Q3Segment("UNSUPPORTED", span))
    return canonical_bytes(
        {
            "record_type": "q3_raw_discovery",
            "schema_version": "1.0",
            "profile": PROFILE,
            "producer": INVENTORY_PRODUCER if inventory else PROPOSAL_PRODUCER,
            "prose_hash": _hash(prose),
            "catalog_hash": _hash(canonical_bytes([v.to_dict() for v in catalog])),
            "segments": [v.to_dict() for v in segments],
        }
    )


def blind_inventory(prose: bytes, catalog: tuple[Q3Alias, ...]) -> bytes:
    return _discover(prose, catalog, inventory=True)


def proposal_backend(prose: bytes, catalog: tuple[Q3Alias, ...]) -> bytes:
    return _discover(prose, catalog, inventory=False)


def _read_discovery(
    raw: bytes, prose: bytes, catalog: tuple[Q3Alias, ...], *, inventory: bool
) -> tuple[Q3Segment, ...]:
    row = _row(
        decode_canonical(raw),
        {
            "record_type",
            "schema_version",
            "profile",
            "producer",
            "prose_hash",
            "catalog_hash",
            "segments",
        },
    )
    if (
        row["record_type"] != "q3_raw_discovery"
        or row["schema_version"] != "1.0"
        or row["profile"] != PROFILE
        or row["producer"] != (INVENTORY_PRODUCER if inventory else PROPOSAL_PRODUCER)
        or row["prose_hash"] != _hash(prose)
        or row["catalog_hash"]
        != _hash(canonical_bytes([v.to_dict() for v in _catalog(catalog)]))
        or type(row["segments"]) is not list
    ):
        raise Q3Error("INVALID_Q3_DISCOVERY")
    segments = tuple(
        Q3Segment.from_dict(v) for v in cast(list[object], row["segments"])
    )
    if inventory and tuple((v.span.start, v.span.end) for v in segments) != _ranges(
        _text(prose)
    ):
        raise Q3Error("INVALID_Q3_DISCOVERY_PARTITION")
    previous = 0
    for item in segments:
        item.span.verify(prose)
        if inventory and item != _inventory_segment(prose, catalog, item.span):
            raise Q3Error("INVALID_Q3_INVENTORY_SEMANTICS")
        if item.span.start < previous or (inventory and item.span.start != previous):
            raise Q3Error("INVALID_Q3_DISCOVERY_COVERAGE")
        previous = item.span.end
        for key in set(item.values) & {
            "actor",
            "place",
            "object",
            "holder",
            "fact_id",
            "belief_id",
        }:
            identity = EntityId.from_dict(item.values[key])
            if identity not in {v.identity for v in catalog}:
                raise Q3Error("INVALID_Q3_DISCOVERY_IDENTITY")
    if inventory and previous != len(_text(prose)):
        raise Q3Error("INVALID_Q3_DISCOVERY_COVERAGE")
    if canonical_bytes(row) != raw:
        raise Q3Error("INVALID_Q3_DISCOVERY")
    return segments


@dataclass(frozen=True, slots=True)
class Q3SceneRange:
    scene_id: EntityId
    order: int
    start: int
    end: int

    def __post_init__(self) -> None:
        if (
            type(self.scene_id) is not EntityId
            or any(type(v) is not int for v in (self.order, self.start, self.end))
            or self.order < 1
            or not 0 <= self.start < self.end
        ):
            raise Q3Error("INVALID_Q3_SCENE_RANGE")

    def to_dict(self) -> dict[str, object]:
        return {
            "scene_id": self.scene_id.to_dict(),
            "order": self.order,
            "start": self.start,
            "end": self.end,
        }

    @classmethod
    def from_dict(cls, value: object) -> Q3SceneRange:
        row = _row(value, {"scene_id", "order", "start", "end"})
        return cls(
            EntityId.from_dict(row["scene_id"]),
            cast(int, row["order"]),
            cast(int, row["start"]),
            cast(int, row["end"]),
        )


@dataclass(frozen=True, slots=True)
class Q3Finding:
    code: str
    verdict: str
    span: ExactSpan | None = None
    document: str = "CURRENT"

    def __post_init__(self) -> None:
        if (
            type(self.code) is not str
            or re.fullmatch(r"[A-Z0-9_]+", self.code) is None
            or self.verdict not in {"FAIL", "UNKNOWN", "ERROR"}
            or self.document not in {"CURRENT", "PREVIOUS"}
        ):
            raise Q3Error("INVALID_Q3_FINDING")

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "verdict": self.verdict,
            "span": None if self.span is None else self.span.to_dict(),
            "document": self.document,
        }


@dataclass(frozen=True, slots=True)
class Q3RequiredTransitionDiagnostic:
    """Writer-facing context for a required transition in audited evidence."""

    code: str
    scene: Q3SceneRange
    fact_id: EntityId
    expected_operation: str
    expected_value: Scalar | None
    actual: Q3Segment | None = field(repr=False)

    def to_dict(self) -> dict[str, object]:
        actual = self.actual.values if self.actual is not None else None
        span = self.actual.span if self.actual is not None else None
        return {
            "code": self.code,
            "scene_id": self.scene.scene_id.to_dict(),
            "scene_order": self.scene.order,
            "fact_id": self.fact_id.to_dict(),
            "expected": {
                "operation": self.expected_operation,
                "value": self.expected_value,
            },
            "actual": None
            if actual is None
            else {"operation": actual["operation"], "value": actual["value"]},
            "location_status": "UNRESOLVED" if span is None else "LOCATED",
            "span": None
            if span is None
            else {
                "start": span.start,
                "end": span.end,
                "byte_start": span.byte_start,
                "byte_end": span.byte_end,
            },
        }


def _verdict(findings: list[Q3Finding] | tuple[Q3Finding, ...]) -> str:
    return next(
        (
            v
            for v in ("FAIL", "ERROR", "UNKNOWN")
            if any(f.verdict == v for f in findings)
        ),
        "PASS",
    )


def _output(findings: list[Q3Finding], *, applicability: str = "APPLICABLE") -> bytes:
    return canonical_bytes(
        {
            "verdict": _verdict(findings),
            "applicability": applicability,
            "diagnostics": [v.to_dict() for v in findings],
        }
    )


def _correspondence(
    prose: bytes,
    inventory: tuple[Q3Segment, ...],
    proposal: tuple[Q3Segment, ...],
    *,
    document: str,
) -> list[Q3Finding]:
    findings: list[Q3Finding] = []
    found = {(v.span.start, v.span.end): v for v in proposal}
    for item in inventory:
        if item.kind == "UNSUPPORTED":
            continue
        other = found.get((item.span.start, item.span.end))
        if other is None:
            findings.append(
                Q3Finding("MISSING_PROPOSITION", "FAIL", item.span, document)
            )
        elif canonical_bytes(item.to_dict()) != canonical_bytes(other.to_dict()):
            findings.append(
                Q3Finding("PROPOSITION_MISMATCH", "FAIL", item.span, document)
            )
    expected = {(v.span.start, v.span.end) for v in inventory}
    for item in proposal:
        if (item.span.start, item.span.end) not in expected:
            findings.append(
                Q3Finding("UNGROUNDED_PROPOSITION", "FAIL", item.span, document)
            )
    if sum(v.span.end - v.span.start for v in proposal) != len(_text(prose)):
        findings.append(Q3Finding("PROPOSAL_COVERAGE_GAP", "FAIL", document=document))
    return findings


def _parts(
    contract: CompiledContract,
) -> tuple[CanonView, KnowledgeSnapshot, StoryFixture, ContinuationEvidence | None]:
    retained = {v.name: decode_canonical(v.content) for v in contract.retained_inputs}
    return (
        CanonView.from_dict(retained["canon"]),
        KnowledgeSnapshot.from_dict(retained["knowledge"]),
        StoryFixture.from_dict(retained["fixture"]),
        None
        if retained["continuity"] is None
        else ContinuationEvidence.from_dict(retained["continuity"]),
    )


def _make_catalog(contract: CompiledContract) -> tuple[Q3Alias, ...]:
    view, snapshot, _fixture, _continuity = _parts(contract)
    values: set[tuple[EntityId, str, str, str | None]] = set()
    for entity in view.root.seed.entities:
        for alias in (entity.id.local_id, entity.display_name, *entity.aliases):
            try:
                Q3Alias(entity.id, alias, "ENTITY")
            except Q3Error:
                continue
            values.add((entity.id, alias, "ENTITY", None))
    for fact in view.baseline.facts:
        values.add(
            (
                fact.seed_fact.id,
                fact.seed_fact.id.local_id,
                "FACT",
                fact.value_kind.value,
            )
        )
    for belief in snapshot.knowledge.beliefs:
        values.add((belief.id, belief.id.local_id, "BELIEF", None))
    return _catalog(tuple(Q3Alias(*value) for value in values))


def _scene(item: Q3Segment, ranges: tuple[Q3SceneRange, ...]) -> Q3SceneRange | None:
    found = tuple(
        v for v in ranges if v.start <= item.span.start < item.span.end <= v.end
    )
    return found[0] if len(found) == 1 else None


def _transitions(
    contract: CompiledContract,
    ranges: tuple[Q3SceneRange, ...],
    inventory: tuple[Q3Segment, ...],
    *,
    diagnostics: list[Q3RequiredTransitionDiagnostic] | None = None,
) -> bytes:
    view, _snapshot, _fixture, _continuity = _parts(contract)
    states = {v.seed_fact.id: v for v in view.baseline.facts}
    findings: list[Q3Finding] = []
    actual = [v for v in inventory if v.claim_type == "FACT" and v.context == "WORLD"]
    counts = {
        EntityId.from_dict(v.values["fact_id"]): sum(
            w.values["fact_id"] == v.values["fact_id"] for w in actual
        )
        for v in actual
    }
    for item in actual:
        if counts[EntityId.from_dict(item.values["fact_id"])] > 1:
            findings.append(
                Q3Finding("MULTIPLE_TRANSITIONS_UNSUPPORTED", "UNKNOWN", item.span)
            )
    satisfied: set[tuple[EntityId, EntityId]] = set()
    candidates: dict[tuple[EntityId, EntityId], list[tuple[bool, Q3Segment]]] = {}
    for item in inventory:
        if item.kind not in {"CLAIM", "UNSUPPORTED"}:
            continue
        located = _scene(item, ranges)
        if located is None:
            findings.append(Q3Finding("CROSS_SCENE_PROPOSITION", "UNKNOWN", item.span))
            continue
        scene = next(v for v in contract.scenes if v.id == located.scene_id)
        if item.kind == "UNSUPPORTED":
            findings.append(Q3Finding("UNSUPPORTED_SOURCE_SPAN", "UNKNOWN", item.span))
            continue
        if item not in actual:
            continue
        data = item.values
        target, value = EntityId.from_dict(data["fact_id"]), cast(Scalar, data["value"])
        before = states[target]
        state = FactState.known(value)
        valid = True
        if _kind(value) != before.value_kind.value:
            findings.append(Q3Finding("FACT_VALUE_TYPE_MISMATCH", "FAIL", item.span))
            valid = False
        elif data["operation"] == "NO_CHANGE" and before.state != state:
            findings.append(Q3Finding("NO_CHANGE_VALUE_CONFLICT", "FAIL", item.span))
            valid = False
        elif data["operation"] == "SET_FACT" and before.state == state:
            findings.append(
                Q3Finding("SAME_VALUE_SET_REQUIRES_NO_CHANGE", "FAIL", item.span)
            )
            valid = False
        elif (
            data["operation"] == "SET_FACT"
            and before.state.status is FactStatus.RETRACTED
        ):
            findings.append(Q3Finding("RETRACTED_FACT_CHANGED", "FAIL", item.span))
            valid = False
        if (
            data["operation"] == "SET_FACT"
            and before.state != state
            and target in scene.plan.protected_fact_ids
        ):
            findings.append(Q3Finding("PROTECTED_FACT_CHANGED", "FAIL", item.span))
        for forbidden in scene.plan.forbidden:
            if (
                target == forbidden.target_id
                and data["operation"] == forbidden.operation.value
                and (
                    forbidden.operation.value != "SET_FACT"
                    or FactState.known(cast(Scalar, forbidden.value)) == state
                )
            ):
                findings.append(Q3Finding("FORBIDDEN_TRANSITION", "FAIL", item.span))
        for required in scene.required:
            if target != required.target_id:
                continue
            key = (scene.id, target)
            same_transition = data["operation"] == required.spec.operation.value and (
                data["operation"] != "SET_FACT"
                or state == FactState.known(cast(Scalar, required.spec.value))
            )
            candidates.setdefault(key, []).append((same_transition, item))
            if (
                valid
                and same_transition
                and required.expected == Precondition.from_snapshot(before)
            ):
                satisfied.add(key)
        if valid and data["operation"] == "SET_FACT":
            from anovel.domain.delta import FactSnapshot

            states[target] = FactSnapshot(
                before.seed_fact, before.revision + 1, state=state
            )
    for scene in contract.scenes:
        region = next(v for v in ranges if v.scene_id == scene.id)
        complete = not any(
            v.kind == "UNSUPPORTED"
            and v.span.start < region.end
            and v.span.end > region.start
            or v.kind == "CLAIM"
            and _scene(v, ranges) is None
            for v in inventory
        )
        for required in scene.required:
            key = (scene.id, required.target_id)
            if key in satisfied:
                continue
            supported = required.spec.operation.value in {"SET_FACT", "NO_CHANGE"}
            observed = candidates.get(key, [])
            if not complete or not supported:
                finding = Q3Finding("REQUIRED_TRANSITION_UNPROVEN", "UNKNOWN")
            elif not observed:
                finding = Q3Finding("REQUIRED_TRANSITION_MISSING", "FAIL")
            else:
                finding = Q3Finding(
                    "REQUIRED_PRECONDITION_MISMATCH"
                    if any(matches for matches, _ in observed)
                    else "REQUIRED_TRANSITION_MISMATCH",
                    "FAIL",
                )
            findings.append(finding)
            if diagnostics is not None:
                unique = (
                    observed[0][1]
                    if finding.code == "REQUIRED_TRANSITION_MISMATCH"
                    and len(observed) == 1
                    and counts[required.target_id] == 1
                    else None
                )
                diagnostics.append(
                    Q3RequiredTransitionDiagnostic(
                        finding.code,
                        region,
                        required.target_id,
                        required.spec.operation.value,
                        required.spec.value,
                        unique,
                    )
                )
    return _output(findings)


def _continuation(
    contract: CompiledContract,
    current: tuple[Q3Segment, ...],
    previous: tuple[Q3Segment, ...] | None,
) -> bytes:
    view, _snapshot, _fixture, continuity = _parts(contract)
    if contract.chapter_number == 1 and view.previous is None and continuity is None:
        return _output([], applicability="FIRST_CHAPTER_NO_PREDECESSOR")
    findings: list[Q3Finding] = []
    if view.previous is None or continuity is None or previous is None:
        return _output([Q3Finding("PREDECESSOR_EVIDENCE_UNAVAILABLE", "UNKNOWN")])
    text = view.previous.prose.decode("utf-8")
    if (
        continuity.previous_commit_id != contract.parent_ref
        or continuity.prose_hash != _hash(view.previous.prose)
        or continuity.candidate_id != view.previous.candidate_id
        or continuity.end != len(text)
        or text[continuity.start : continuity.end] != continuity.quote
    ):
        findings.append(Q3Finding("PREDECESSOR_BINDING_MISMATCH", "FAIL"))
    for document, items in (("CURRENT", current), ("PREVIOUS", previous)):
        findings.extend(
            Q3Finding("CONTINUATION_UNSUPPORTED_SPAN", "UNKNOWN", item.span, document)
            for item in items
            if item.kind == "UNSUPPORTED"
        )
    completed = [
        v.values
        for v in previous
        if v.claim_type == "ACTION"
        and v.context == "WORLD"
        and v.values["completed"] is True
    ]
    for item in current:
        if item.claim_type != "ACTION" or item.context != "WORLD":
            continue
        data = item.values
        if any(
            all(data[k] == old[k] for k in ("actor", "action", "object", "at", "place"))
            for old in completed
        ):
            findings.append(Q3Finding("PREDECESSOR_ACTION_REPEATED", "FAIL", item.span))
    return _output(findings)


def _knowledge(
    contract: CompiledContract,
    ranges: tuple[Q3SceneRange, ...],
    inventory: tuple[Q3Segment, ...],
) -> bytes:
    from anovel.domain.delta import FactSnapshot

    view, snapshot, fixture, _continuity = _parts(contract)
    knowledge = snapshot.knowledge
    beliefs = {v.id: v for v in knowledge.beliefs}
    reveals = {v.fact_id: v.not_before for v in fixture.reader_boundaries}
    states = {v.seed_fact.id: v for v in view.baseline.facts}
    findings: list[Q3Finding] = []
    uncertain_trace = False
    checked_scenes: set[EntityId] = set()
    for item in inventory:
        location = _scene(item, ranges)
        if location is not None and location.scene_id not in checked_scenes:
            checked_scenes.add(location.scene_id)
            scene_start = next(v for v in contract.scenes if v.id == location.scene_id)
            for boundary in scene_start.plan.knowledge_boundaries:
                for required_fact in boundary.must_know:
                    try:
                        acquired = knowledge.require_known(
                            boundary.actor_id, required_fact
                        )
                        if (
                            FactState.known(acquired.proposition.value)
                            != states[required_fact].state
                        ):
                            raise ValueError
                    except ValueError:
                        findings.append(
                            Q3Finding(
                                "REQUIRED_CURRENT_KNOWLEDGE_UNPROVEN",
                                "UNKNOWN",
                                item.span,
                            )
                        )
        if item.kind == "UNSUPPORTED":
            findings.append(
                Q3Finding("KNOWLEDGE_UNSUPPORTED_SPAN", "UNKNOWN", item.span)
            )
            uncertain_trace = True
        if item.context != "WORLD":
            continue
        data = item.values
        if item.claim_type == "FACT":
            target = EntityId.from_dict(data["fact_id"])
            located_fact = _scene(item, ranges)
            if located_fact is None:
                uncertain_trace = True
                continue
            if (
                target in reveals
                and located_fact is not None
                and NarrativePosition(contract.chapter_number, located_fact.order)
                < reveals[target]
            ):
                findings.append(Q3Finding("EARLY_READER_REVEAL", "FAIL", item.span))
            before = states[target]
            value = cast(Scalar, data["value"])
            if (
                data["operation"] == "SET_FACT"
                and _kind(value) == before.value_kind.value
                and before.state.status is not FactStatus.RETRACTED
                and before.state != FactState.known(value)
            ):
                states[target] = FactSnapshot(
                    before.seed_fact, before.revision + 1, state=FactState.known(value)
                )
            continue
        if item.claim_type not in {
            "ACQUISITION",
            "KNOWLEDGE_USE",
            "BELIEF_CHOICE",
            "READER_REVEAL",
        }:
            continue
        located = _scene(item, ranges)
        if located is None:
            findings.append(Q3Finding("KNOWLEDGE_SCENE_UNPROVEN", "UNKNOWN", item.span))
            continue
        scene = next(v for v in contract.scenes if v.id == located.scene_id)
        fact_id, value = (
            EntityId.from_dict(data["fact_id"]),
            cast(Scalar, data["value"]),
        )
        actual = states[fact_id]
        if item.claim_type == "READER_REVEAL":
            if actual.state != FactState.known(value):
                findings.append(
                    Q3Finding(
                        "REVEAL_PROPOSITION_UNPROVEN"
                        if uncertain_trace
                        else "REVEAL_PROPOSITION_MISMATCH",
                        "UNKNOWN" if uncertain_trace else "FAIL",
                        item.span,
                    )
                )
            if (
                fact_id in reveals
                and NarrativePosition(contract.chapter_number, located.order)
                < reveals[fact_id]
            ):
                findings.append(Q3Finding("EARLY_READER_REVEAL", "FAIL", item.span))
            continue
        if (
            item.claim_type in {"KNOWLEDGE_USE", "ACQUISITION"}
            and fact_id in reveals
            and NarrativePosition(contract.chapter_number, located.order)
            < reveals[fact_id]
        ):
            findings.append(
                Q3Finding("READER_REVEAL_CONTEXT_UNPROVEN", "UNKNOWN", item.span)
            )
        holder = EntityId.from_dict(data["holder"])
        if holder not in {v.id for v in knowledge.characters}:
            findings.append(
                Q3Finding("KNOWLEDGE_HOLDER_UNAVAILABLE", "UNKNOWN", item.span)
            )
            continue
        if item.claim_type == "BELIEF_CHOICE":
            belief = beliefs.get(EntityId.from_dict(data["belief_id"]))
            if belief is None:
                findings.append(
                    Q3Finding("BELIEF_SOURCE_UNAVAILABLE", "UNKNOWN", item.span)
                )
            elif (
                belief.holder != holder
                or belief.proposition.subject != actual.seed_fact.proposition.subject
                or belief.proposition.predicate
                != actual.seed_fact.proposition.predicate
                or FactState.known(belief.proposition.value) != FactState.known(value)
            ):
                findings.append(
                    Q3Finding(
                        "BELIEF_HOLDER_OR_PROPOSITION_MISMATCH", "FAIL", item.span
                    )
                )
            continue
        if any(
            v.actor_id == holder and fact_id in v.must_not_know
            for v in scene.plan.knowledge_boundaries
        ):
            findings.append(Q3Finding("FORBIDDEN_KNOWLEDGE_USED", "FAIL", item.span))
        if actual.state != FactState.known(value):
            findings.append(
                Q3Finding(
                    "KNOWLEDGE_PROPOSITION_UNPROVEN"
                    if uncertain_trace
                    else "KNOWLEDGE_PROPOSITION_MISMATCH",
                    "UNKNOWN" if uncertain_trace else "FAIL",
                    item.span,
                )
            )
        try:
            known = knowledge.require_known(holder, fact_id)
            if FactState.known(known.proposition.value) != actual.state:
                raise ValueError
        except ValueError:
            findings.append(
                Q3Finding("ACQUISITION_OR_USE_SOURCE_UNPROVEN", "UNKNOWN", item.span)
            )
    return _output(findings, applicability="EXPLICIT_FROZEN_KNOWLEDGE_AND_RAW_CLAIMS")


_EXEC_FIELDS = {
    "reason",
    "attempt_id",
    "finished_at",
    "request_id",
    "record_type",
    "input_hash",
    "started_at",
    "result_hash",
    "check_id",
    "method_policy_hash",
    "execution_status",
    "schema_version",
    "error_code",
    "result_base64",
}


def _timestamp(value: object) -> datetime:
    if type(value) is not str:
        raise Q3Error("INVALID_Q3_TIMESTAMP")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or utc_timestamp(result) != value:
        raise Q3Error("INVALID_Q3_TIMESTAMP")
    return result


def _code(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[A-Z0-9_]+", value) is None:
        raise Q3Error("INVALID_Q3_CODE")
    return value


def _request(check_id: str, input_hash: str) -> str:
    return _hash(
        canonical_bytes(
            {
                "check_id": check_id,
                "input_hash": input_hash,
                "method_policy_hash": METHOD_POLICY_HASH,
            }
        )
    )


@dataclass(frozen=True, slots=True)
class Q3Execution:
    payload: bytes = field(repr=False)

    def __post_init__(self) -> None:
        try:
            row = _row(decode_canonical(self.payload), _EXEC_FIELDS)
            if (
                row["record_type"] != "q3_execution"
                or row["schema_version"] != "1.0"
                or row["method_policy_hash"] != METHOD_POLICY_HASH
                or type(row["check_id"]) is not str
                or row["check_id"] not in CHECK_IDS
            ):
                raise ValueError
            if row["request_id"] != _request(
                row["check_id"], _digest(row["input_hash"])
            ):
                raise ValueError
            status = row["execution_status"]
            if status == "NOT_EXECUTED":
                if row["reason"] != "PREREQUISITE_NOT_AVAILABLE" or any(
                    row[v] is not None
                    for v in (
                        "attempt_id",
                        "started_at",
                        "finished_at",
                        "result_base64",
                        "result_hash",
                        "error_code",
                    )
                ):
                    raise ValueError
            elif status in {"FINISHED", "ERROR"}:
                if (
                    type(row["attempt_id"]) is not str
                    or re.fullmatch(r"[0-9a-f]{32}", row["attempt_id"]) is None
                    or _timestamp(row["finished_at"]) < _timestamp(row["started_at"])
                ):
                    raise ValueError
                if _hash(_decode(row["result_base64"])) != row["result_hash"]:
                    raise ValueError
                if status == "FINISHED":
                    if row["reason"] != "EXECUTED" or row["error_code"] is not None:
                        raise ValueError
                elif row["reason"] != "EXECUTION_ERROR" or _code(
                    row["error_code"]
                ) not in {"NATIVE_EXECUTION_ERROR", "INVALID_STAGE_RESULT"}:
                    raise ValueError
            else:
                raise ValueError
            if canonical_bytes(row) != self.payload:
                raise ValueError
        except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
            raise Q3Error("INVALID_Q3_EXECUTION") from None

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    def payload_bytes(self) -> bytes:
        return self.payload

    @classmethod
    def from_dict(cls, value: object) -> Q3Execution:
        return cls(canonical_bytes(value))

    @classmethod
    def from_bytes(cls, raw: bytes) -> Q3Execution:
        return cls(raw)

    @property
    def record_hash(self) -> str:
        return _hash(self.payload)

    @property
    def check_id(self) -> str:
        return cast(str, self.to_dict()["check_id"])

    @property
    def execution_status(self) -> str:
        return cast(str, self.to_dict()["execution_status"])

    @property
    def input_hash(self) -> str:
        return cast(str, self.to_dict()["input_hash"])

    @property
    def result_bytes(self) -> bytes | None:
        value = self.to_dict()["result_base64"]
        return None if value is None else _decode(value)

    @property
    def result_hash(self) -> str | None:
        return cast(str | None, self.to_dict()["result_hash"])


def _stage(
    check_id: str,
    input_hash: str,
    method: Callable[[], bytes],
    audit: Callable[[bytes], object],
) -> Q3Execution:
    started = utc_timestamp(datetime.now(UTC))
    status, error = "FINISHED", None
    try:
        raw = method()
        if type(raw) is not bytes:
            raise ValueError
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        RuntimeError,
        OSError,
        OverflowError,
        RecursionError,
    ):
        status, error = "ERROR", "NATIVE_EXECUTION_ERROR"
        raw = canonical_bytes(
            {"record_type": "q3_execution_error", "check_id": check_id, "code": error}
        )
    if status == "FINISHED":
        try:
            audit(raw)
        except (
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            RuntimeError,
            OSError,
            OverflowError,
            RecursionError,
        ):
            status, error = "ERROR", "INVALID_STAGE_RESULT"
    return Q3Execution.from_dict(
        {
            "record_type": "q3_execution",
            "schema_version": "1.0",
            "check_id": check_id,
            "input_hash": input_hash,
            "method_policy_hash": METHOD_POLICY_HASH,
            "request_id": _request(check_id, input_hash),
            "attempt_id": uuid4().hex,
            "execution_status": status,
            "started_at": started,
            "finished_at": utc_timestamp(datetime.now(UTC)),
            "result_base64": _encode(raw),
            "result_hash": _hash(raw),
            "error_code": error,
            "reason": "EXECUTED" if status == "FINISHED" else "EXECUTION_ERROR",
        }
    )


def _not_executed(check_id: str, input_hash: str) -> Q3Execution:
    return Q3Execution.from_dict(
        {
            "record_type": "q3_execution",
            "schema_version": "1.0",
            "check_id": check_id,
            "input_hash": input_hash,
            "method_policy_hash": METHOD_POLICY_HASH,
            "request_id": _request(check_id, input_hash),
            "attempt_id": None,
            "execution_status": "NOT_EXECUTED",
            "started_at": None,
            "finished_at": None,
            "result_base64": None,
            "result_hash": None,
            "error_code": None,
            "reason": "PREREQUISITE_NOT_AVAILABLE",
        }
    )


def _input_record(
    prose: bytes,
    source_id: EntityId,
    contract: CompiledContract,
    ranges: tuple[Q3SceneRange, ...],
) -> dict[str, object]:
    text = _text(prose)
    if (
        type(source_id) is not EntityId
        or type(contract) is not CompiledContract
        or source_id.project != contract.project
        or type(ranges) is not tuple
        or any(type(v) is not Q3SceneRange for v in ranges)
    ):
        raise Q3Error("Q3_SOURCE_SCOPE_MISMATCH")
    if tuple((v.scene_id, v.order) for v in ranges) != tuple(
        (v.id, v.plan.order) for v in contract.scenes
    ):
        raise Q3Error("Q3_SCENE_INVENTORY_MISMATCH")
    cursor = 0
    for region in ranges:
        if (
            region.start < cursor
            or region.end > len(text)
            or text[cursor : region.start].strip()
        ):
            raise Q3Error("Q3_SCENE_RANGE_MISMATCH")
        cursor = region.end
    if text[cursor:].strip():
        raise Q3Error("Q3_SCENE_RANGE_MISMATCH")
    view, _snapshot, _fixture, continuity = _parts(contract)
    previous = (
        None
        if view.previous is None or continuity is None
        else continuity.quote.encode("utf-8")
    )
    return {
        "prose_base64": _encode(prose),
        "prose_hash": _hash(prose),
        "source_id": source_id.to_dict(),
        "contract_base64": _encode(contract.content_bytes),
        "contract_hash": contract.content_hash,
        "scene_ranges": [v.to_dict() for v in ranges],
        "catalog": [v.to_dict() for v in _make_catalog(contract)],
        "previous_base64": None if previous is None else _encode(previous),
        "method_policy_hash": METHOD_POLICY_HASH,
        "method_document_hash": METHOD_DOCUMENT_HASH,
        "method_policy": decode_canonical(METHOD_POLICY_BYTES),
    }


def _documents(source: dict[str, object]) -> tuple[tuple[str, bytes], ...]:
    result = [("CURRENT", _decode(source["prose_base64"]))]
    if source["previous_base64"] is not None:
        result.append(("PREVIOUS", _decode(source["previous_base64"])))
    return tuple(result)


def _discover_documents(
    source: dict[str, object], catalog: tuple[Q3Alias, ...], *, inventory: bool
) -> bytes:
    backend = blind_inventory if inventory else proposal_backend
    # Every document's inventory is sealed before any proposal is exposed.
    return canonical_bytes(
        {name: _encode(backend(prose, catalog)) for name, prose in _documents(source)}
    )


def _read_documents(
    raw: bytes,
    source: dict[str, object],
    catalog: tuple[Q3Alias, ...],
    *,
    inventory: bool,
) -> dict[str, tuple[Q3Segment, ...]]:
    docs = _documents(source)
    row = _row(decode_canonical(raw), {name for name, _ in docs})
    return {
        name: _read_discovery(_decode(row[name]), prose, catalog, inventory=inventory)
        for name, prose in docs
    }


def _result_audit(raw: bytes, expected: bytes) -> dict[str, object]:
    if raw != expected:
        raise Q3Error("INVALID_Q3_STAGE_RESULT")
    return cast(dict[str, object], decode_canonical(raw))


def _audit_stage(
    execution: Q3Execution, audit: Callable[[bytes], object]
) -> object | None:
    raw = execution.result_bytes
    if raw is None:
        return None
    row = execution.to_dict()
    if execution.execution_status == "ERROR":
        if row["error_code"] == "NATIVE_EXECUTION_ERROR":
            if raw != canonical_bytes(
                {
                    "record_type": "q3_execution_error",
                    "check_id": execution.check_id,
                    "code": "NATIVE_EXECUTION_ERROR",
                }
            ):
                raise Q3Error("INVALID_Q3_ERROR_RESULT")
        else:
            try:
                audit(raw)
            except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
                pass
            else:
                raise Q3Error("INVALID_Q3_ERROR_RESULT")
        return None
    return audit(raw)


def _correspondence_output(
    source: dict[str, object],
    inventory: dict[str, tuple[Q3Segment, ...]],
    proposal: dict[str, tuple[Q3Segment, ...]],
) -> bytes:
    findings: list[Q3Finding] = []
    for document, prose in _documents(source):
        findings.extend(
            _correspondence(
                prose, inventory[document], proposal[document], document=document
            )
        )
    return _output(findings)


def _comparison_methods(
    source: dict[str, object],
    contract: CompiledContract,
    ranges: tuple[Q3SceneRange, ...],
    inventory: dict[str, tuple[Q3Segment, ...]] | None,
    proposal: dict[str, tuple[Q3Segment, ...]] | None,
    *,
    transition_diagnostics: list[Q3RequiredTransitionDiagnostic] | None = None,
) -> tuple[Callable[[], bytes] | None, ...]:
    if inventory is None:
        return (None,) * 4
    return (
        None
        if proposal is None
        else partial(_correspondence_output, source, inventory, proposal),
        partial(
            _transitions,
            contract,
            ranges,
            inventory["CURRENT"],
            diagnostics=transition_diagnostics,
        ),
        partial(
            _continuation, contract, inventory["CURRENT"], inventory.get("PREVIOUS")
        ),
        partial(_knowledge, contract, ranges, inventory["CURRENT"]),
    )


def _shape_audit(raw: bytes) -> dict[str, object]:
    row = _row(decode_canonical(raw), {"verdict", "applicability", "diagnostics"})
    if (
        row["verdict"] not in {"PASS", "FAIL", "UNKNOWN", "ERROR"}
        or type(row["applicability"]) is not str
        or type(row["diagnostics"]) is not list
    ):
        raise Q3Error("INVALID_Q3_STAGE_RESULT")
    return row


def _comparison_audit(method: Callable[[], bytes], raw: bytes) -> dict[str, object]:
    _shape_audit(raw)
    return _result_audit(raw, method())


def _audit_evidence(
    source: dict[str, object],
    contract: CompiledContract,
    ranges: tuple[Q3SceneRange, ...],
    executions: tuple[Q3Execution, ...],
    *,
    transition_diagnostics: list[Q3RequiredTransitionDiagnostic] | None = None,
) -> dict[str, object]:
    from anovel.workflow.extractor import ExactSpan

    input_hash = _hash(canonical_bytes(source))
    if (
        tuple(v.check_id for v in executions) != CHECK_IDS
        or any(v.input_hash != input_hash for v in executions)
        or any(v.execution_status == "NOT_EXECUTED" for v in executions[:2])
    ):
        raise Q3Error("Q3_EXECUTION_CLOSURE_MISMATCH")
    catalog = _make_catalog(contract)
    inventory = cast(
        dict[str, tuple[Q3Segment, ...]] | None,
        _audit_stage(
            executions[0],
            lambda raw: _read_documents(raw, source, catalog, inventory=True),
        ),
    )
    proposal = cast(
        dict[str, tuple[Q3Segment, ...]] | None,
        _audit_stage(
            executions[1],
            lambda raw: _read_documents(raw, source, catalog, inventory=False),
        ),
    )
    methods = _comparison_methods(
        source,
        contract,
        ranges,
        inventory,
        proposal,
        transition_diagnostics=(
            transition_diagnostics
            if executions[3].execution_status == "FINISHED"
            else None
        ),
    )
    findings = [
        Q3Finding(v.check_id + "_ERROR", "ERROR")
        for v in executions
        if v.execution_status == "ERROR"
    ]
    results: list[dict[str, object] | None] = []
    for execution, method in zip(executions[2:], methods, strict=True):
        if (execution.execution_status != "NOT_EXECUTED") != (method is not None):
            raise Q3Error("Q3_EXECUTION_DEPENDENCY_MISMATCH")
        result = (
            None
            if method is None
            else cast(
                dict[str, object] | None,
                _audit_stage(execution, partial(_comparison_audit, method)),
            )
        )
        results.append(result)
        if result is not None:
            if type(result["diagnostics"]) is not list:
                raise Q3Error("INVALID_Q3_FINDINGS")
            for value in cast(list[object], result["diagnostics"]):
                row = _row(value, {"code", "verdict", "span", "document"})
                findings.append(
                    Q3Finding(
                        cast(str, row["code"]),
                        cast(str, row["verdict"]),
                        None
                        if row["span"] is None
                        else ExactSpan.from_dict(row["span"]),
                        cast(str, row["document"]),
                    )
                )
    if inventory is not None:
        for document, segments in inventory.items():
            findings.extend(
                Q3Finding("UNSUPPORTED_SOURCE_SPAN", "UNKNOWN", item.span, document)
                for item in segments
                if item.kind == "UNSUPPORTED"
            )
    unique = tuple({canonical_bytes(v.to_dict()): v for v in findings}.values())
    statuses = [
        "ERROR"
        if execution.execution_status == "ERROR"
        else "NOT_EXECUTED"
        if result is None
        else result["verdict"]
        for execution, result in zip(executions[2:], results, strict=True)
    ]
    return {
        "input_hash": input_hash,
        "q3_status": _verdict(unique),
        "correspondence_status": statuses[0],
        "transition_status": statuses[1],
        "continuation_status": statuses[2],
        "knowledge_status": statuses[3],
        "finite_coverage_status": "UNKNOWN"
        if inventory is None
        else "INCOMPLETE"
        if any(
            item.kind == "UNSUPPORTED"
            for segments in inventory.values()
            for item in segments
        )
        else "COMPLETE",
        "diagnostics": [v.to_dict() for v in unique],
    }


def _evidence_record(
    source: dict[str, object],
    contract: CompiledContract,
    ranges: tuple[Q3SceneRange, ...],
    executions: tuple[Q3Execution, ...],
    *,
    transition_diagnostics: list[Q3RequiredTransitionDiagnostic] | None = None,
) -> dict[str, object]:
    return {
        "record_type": "q3_evidence",
        "schema_version": "1.0",
        "profile": PROFILE,
        **source,
        "executions": [v.to_dict() for v in executions],
        **_audit_evidence(
            source,
            contract,
            ranges,
            executions,
            transition_diagnostics=transition_diagnostics,
        ),
        "coverage_status": "NOT_VERIFIED",
        "production_status": "UNKNOWN",
        "semantic_status": "UNKNOWN",
        "aggregate_status": "BLOCKED",
        **_FALSE,
    }


@dataclass(frozen=True, slots=True)
class Q3Evidence:
    payload: bytes = field(repr=False)
    _executions: tuple[Q3Execution, ...] = field(init=False, repr=False, compare=False)
    _row: dict[str, object] = field(init=False, repr=False, compare=False)
    required_transition_diagnostics: tuple[Q3RequiredTransitionDiagnostic, ...] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        try:
            row = cast(dict[str, object], decode_canonical(self.payload))
            contract = CompiledContract.from_dict(
                decode_canonical(_decode(row["contract_base64"]))
            )
            ranges = tuple(
                Q3SceneRange.from_dict(v)
                for v in cast(list[object], row["scene_ranges"])
            )
            source = _input_record(
                _decode(row["prose_base64"]),
                EntityId.from_dict(row["source_id"]),
                contract,
                ranges,
            )
            executions = tuple(
                Q3Execution.from_dict(v) for v in cast(list[object], row["executions"])
            )
            diagnostics: list[Q3RequiredTransitionDiagnostic] = []
            if (
                canonical_bytes(
                    _evidence_record(
                        source,
                        contract,
                        ranges,
                        executions,
                        transition_diagnostics=diagnostics,
                    )
                )
                != self.payload
            ):
                raise ValueError
            object.__setattr__(self, "_row", row)
            object.__setattr__(self, "_executions", executions)
            object.__setattr__(
                self, "required_transition_diagnostics", tuple(diagnostics)
            )
        except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
            raise Q3Error("INVALID_Q3_EVIDENCE") from None

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    def payload_bytes(self) -> bytes:
        return self.payload

    @classmethod
    def from_dict(cls, value: object) -> Q3Evidence:
        return cls(canonical_bytes(value))

    @classmethod
    def from_bytes(cls, raw: bytes) -> Q3Evidence:
        return cls(raw)

    @property
    def record_hash(self) -> str:
        return _hash(self.payload)

    @property
    def content_hash(self) -> str:
        return self.record_hash

    @property
    def executions(self) -> tuple[Q3Execution, ...]:
        return self._executions

    @property
    def prose(self) -> bytes:
        return _decode(self._row["prose_base64"])

    @property
    def prose_hash(self) -> str:
        return cast(str, self._row["prose_hash"])

    @property
    def inventory_raw(self) -> bytes | None:
        return self.executions[0].result_bytes

    @property
    def proposal_raw(self) -> bytes | None:
        return self.executions[1].result_bytes

    @property
    def diagnostics(self) -> tuple[Q3Finding, ...]:
        from anovel.workflow.extractor import ExactSpan

        return tuple(
            Q3Finding(
                cast(str, row["code"]),
                cast(str, row["verdict"]),
                None if row["span"] is None else ExactSpan.from_dict(row["span"]),
                cast(str, row["document"]),
            )
            for row in cast(list[dict[str, object]], self._row["diagnostics"])
        )

    @property
    def q3_status(self) -> str:
        return cast(str, self._row["q3_status"])

    @property
    def correspondence_status(self) -> str:
        return cast(str, self._row["correspondence_status"])

    @property
    def transition_status(self) -> str:
        return cast(str, self._row["transition_status"])

    @property
    def continuation_status(self) -> str:
        return cast(str, self._row["continuation_status"])

    @property
    def knowledge_status(self) -> str:
        return cast(str, self._row["knowledge_status"])

    @property
    def finite_coverage_status(self) -> str:
        return cast(str, self._row["finite_coverage_status"])


def execute_raw_q3(
    prose: bytes,
    *,
    source_id: EntityId,
    contract: CompiledContract,
    scene_ranges: tuple[Q3SceneRange, ...],
) -> Q3Evidence:
    """Run actual finite checks; this small-input entry has no publication token."""
    source = _input_record(prose, source_id, contract, scene_ranges)
    input_hash, catalog = _hash(canonical_bytes(source)), _make_catalog(contract)
    inventory_execution = _stage(
        CHECK_IDS[0],
        input_hash,
        lambda: _discover_documents(source, catalog, inventory=True),
        lambda raw: _read_documents(raw, source, catalog, inventory=True),
    )
    proposal_execution = _stage(
        CHECK_IDS[1],
        input_hash,
        lambda: _discover_documents(source, catalog, inventory=False),
        lambda raw: _read_documents(raw, source, catalog, inventory=False),
    )
    inventory = (
        None
        if inventory_execution.execution_status != "FINISHED"
        else _read_documents(
            cast(bytes, inventory_execution.result_bytes),
            source,
            catalog,
            inventory=True,
        )
    )
    proposal = (
        None
        if proposal_execution.execution_status != "FINISHED"
        else _read_documents(
            cast(bytes, proposal_execution.result_bytes),
            source,
            catalog,
            inventory=False,
        )
    )
    executions = [inventory_execution, proposal_execution]
    for check_id, method in zip(
        CHECK_IDS[2:],
        _comparison_methods(source, contract, scene_ranges, inventory, proposal),
        strict=True,
    ):
        executions.append(
            _not_executed(check_id, input_hash)
            if method is None
            else _stage(check_id, input_hash, method, _shape_audit)
        )
    return Q3Evidence(
        canonical_bytes(
            _evidence_record(source, contract, scene_ranges, tuple(executions))
        )
    )


def _bound_source(
    observation: ExtractionObservation,
) -> tuple[bytes, EntityId, CompiledContract, tuple[Q3SceneRange, ...]]:
    from anovel.workflow.extractor import ExtractionObservation

    if type(observation) is not ExtractionObservation:
        raise Q3Error("Q3_OBSERVATION_REQUIRED")
    assembly = observation.assembly
    regions = tuple(
        Q3SceneRange(
            EntityId.from_dict(v["scene_id"]),
            cast(int, v["scene_order"]),
            cast(int, v["unicode_start"]),
            cast(int, v["unicode_end"]),
        )
        for v in cast(list[dict[str, object]], assembly.to_dict()["segments"])
        if v["kind"] != "SEPARATOR"
    )
    return (
        assembly.prose,
        observation.source_id,
        assembly.child.source.contract,
        regions,
    )


def _run_record(
    observation: ExtractionObservation, evidence: Q3Evidence
) -> dict[str, object]:
    prose, source_id, contract, ranges = _bound_source(observation)
    source = _input_record(prose, source_id, contract, ranges)
    row = evidence.to_dict()
    if any(row[k] != value for k, value in source.items()):
        raise Q3Error("Q3_EVIDENCE_SOURCE_CHANGED")
    return {
        "record_type": "local_q3_run",
        "schema_version": "1.0",
        "profile": PROFILE,
        "observation_base64": _encode(observation.payload_bytes()),
        "observation_hash": observation.record_hash,
        "evidence_base64": _encode(evidence.payload_bytes()),
        "evidence_hash": evidence.record_hash,
        "project": observation.project,
        "branch": observation.branch,
        "run_id": observation.run_id,
        "step_id": observation.step_id,
        "assembly_hash": observation.assembly_hash,
        "prose_hash": evidence.prose_hash,
        "method_policy_hash": METHOD_POLICY_HASH,
        "method_document_hash": METHOD_DOCUMENT_HASH,
        "method_policy": decode_canonical(METHOD_POLICY_BYTES),
        "q3_status": evidence.q3_status,
        "finite_coverage_status": evidence.finite_coverage_status,
        "observation_correspondence_status": observation.correspondence_status,
        "coverage_status": "NOT_VERIFIED",
        "source_qualification": "FINITE_LOCAL_RAW_METHOD_NOT_PRODUCTION_QUALIFIED",
        "production_status": "UNKNOWN",
        "semantic_status": "UNKNOWN",
        "aggregate_status": "BLOCKED",
        **_FALSE,
    }


@dataclass(frozen=True, slots=True)
class Q3Run:
    payload: bytes = field(repr=False)
    _observation: ExtractionObservation = field(init=False, repr=False, compare=False)
    _evidence: Q3Evidence = field(init=False, repr=False, compare=False)
    _token: object | None = field(init=False, default=None, repr=False, compare=False)
    _token_hash: str | None = field(init=False, default=None, repr=False, compare=False)
    _token_owner: int | None = field(
        init=False, default=None, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        from anovel.workflow.extractor import ExtractionObservation

        try:
            row = cast(dict[str, object], decode_canonical(self.payload))
            observation = ExtractionObservation.from_bytes(
                _decode(row["observation_base64"])
            )
            evidence = Q3Evidence.from_bytes(_decode(row["evidence_base64"]))
            if canonical_bytes(_run_record(observation, evidence)) != self.payload:
                raise ValueError
            object.__setattr__(self, "_observation", observation)
            object.__setattr__(self, "_evidence", evidence)
        except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
            raise Q3Error("INVALID_Q3_RUN") from None

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    def payload_bytes(self) -> bytes:
        return self.payload

    @classmethod
    def from_dict(cls, value: object) -> Q3Run:
        return cls(canonical_bytes(value))

    @classmethod
    def from_bytes(cls, raw: bytes) -> Q3Run:
        return cls(raw)

    @property
    def record_hash(self) -> str:
        return _hash(self.payload)

    @property
    def content_hash(self) -> str:
        return self.record_hash

    @property
    def observation(self) -> ExtractionObservation:
        return self._observation

    @property
    def evidence(self) -> Q3Evidence:
        return self._evidence

    @property
    def executions(self) -> tuple[Q3Execution, ...]:
        return self.evidence.executions

    @property
    def project(self) -> str:
        return self.observation.project

    @property
    def branch(self) -> str:
        return self.observation.branch

    @property
    def run_id(self) -> str:
        return self.observation.run_id

    @property
    def step_id(self) -> str:
        return self.observation.step_id

    @property
    def observation_hash(self) -> str:
        return self.observation.record_hash

    @property
    def assembly_hash(self) -> str:
        return self.observation.assembly_hash

    @property
    def prose_hash(self) -> str:
        return self.evidence.prose_hash

    @property
    def method_policy_hash(self) -> str:
        return cast(str, self.to_dict()["method_policy_hash"])

    @property
    def q3_status(self) -> str:
        return self.evidence.q3_status

    @property
    def correspondence_status(self) -> str:
        return self.evidence.correspondence_status

    @property
    def transition_status(self) -> str:
        return self.evidence.transition_status

    @property
    def continuation_status(self) -> str:
        return self.evidence.continuation_status

    @property
    def knowledge_status(self) -> str:
        return self.evidence.knowledge_status

    @property
    def finite_coverage_status(self) -> str:
        return self.evidence.finite_coverage_status

    @property
    def diagnostics(self) -> tuple[Q3Finding, ...]:
        return self.evidence.diagnostics

    @property
    def coverage_status(self) -> str:
        return "NOT_VERIFIED"

    @property
    def source_qualification(self) -> str:
        return "FINITE_LOCAL_RAW_METHOD_NOT_PRODUCTION_QUALIFIED"

    @property
    def production_status(self) -> str:
        return "UNKNOWN"

    @property
    def semantic_status(self) -> str:
        return "UNKNOWN"

    @property
    def aggregate_status(self) -> str:
        return "BLOCKED"

    @property
    def can_commit(self) -> bool:
        return False

    @property
    def can_issue_permit(self) -> bool:
        return False

    @property
    def can_dispatch(self) -> bool:
        return False

    @property
    def accepted(self) -> bool:
        return False

    @property
    def published(self) -> bool:
        return False


def require_local_execution_q3(run: Q3Run) -> None:
    if (
        type(run) is not Q3Run
        or run._token is not _TOKEN
        or run._token_hash != run.record_hash
        or run._token_owner != id(run)
    ):
        raise Q3Error("Q3_NATIVE_EXECUTION_REQUIRED")


def execute_local_q3(observation: ExtractionObservation) -> Q3Run:
    prose, source_id, contract, ranges = _bound_source(observation)
    evidence = execute_raw_q3(
        prose, source_id=source_id, contract=contract, scene_ranges=ranges
    )
    result = Q3Run(canonical_bytes(_run_record(observation, evidence)))
    object.__setattr__(result, "_token", _TOKEN)
    object.__setattr__(result, "_token_hash", result.record_hash)
    object.__setattr__(result, "_token_owner", id(result))
    return result
