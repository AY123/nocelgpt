"""Finite raw genre discovery and actual local execution, never production authority.

The two producers see only raw UTF-8 and a value-free identity catalogue. Their
bounded grammar is not natural-prose understanding. Decode performs static audit
of retained bytes; it neither invokes a producer/checker nor grants publication.
"""

from __future__ import annotations

import re
from base64 import b64decode, b64encode
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import TYPE_CHECKING, Callable, cast
from uuid import uuid4

from anovel.canon.identity import canonical_bytes, decode_canonical, utc_timestamp
from anovel.domain.events import Occurrence
from anovel.domain.identity import EntityId
from anovel.genre.extensions.registration import registered_extensions
from anovel.genre.policy import (
    BUSINESS_POLICY_HASH,
    POLICY_HASH,
    PROGRESSION_POLICY_HASH,
    ClaimContext,
    EvidenceSpan,
    GenrePolicy,
    Mechanism,
    PolicyDiagnostic,
    PolicyResult,
    PolicyStatus,
    SemanticClaim,
    SourceDocument,
)
from anovel.genre.registry import ProjectGenreBinding

if TYPE_CHECKING:
    from anovel.workflow.extractor import ExactSpan, ExtractionObservation

PROFILE = "LOCAL_RAW_GENRE_V1"
INVENTORY_PRODUCER = "q2-independent-token-inventory/1.0"
PROPOSAL_PRODUCER = "q2-anchored-regex-proposal/1.0"
CHECK_IDS = (
    "Q2_RAW_INVENTORY_V1",
    "Q2_RAW_PROPOSAL_V1",
    "Q2_RAW_CORRESPONDENCE_V1",
    "Q2_GENRE_POLICY_V1",
)
_WRAPPERS = {
    "梦中": ClaimContext.DREAM,
    "引用": ClaimContext.QUOTATION,
    "比喻": ClaimContext.METAPHOR,
    "误信": ClaimContext.BELIEF,
    "假设": ClaimContext.HYPOTHESIS,
    "谎称": ClaimContext.LIE,
    "听说": ClaimContext.QUOTATION,
}
_TOKEN_RX = r"【([^【】\x00-\x1f\x7f]+)】"
_NUMBER_RX = r"([1-9][0-9]{0,17})"
_RX_RULES = (
    (Mechanism.ORDINARY_ACTION, _TOKEN_RX + "步行走到" + _TOKEN_RX + "身边。"),
    (
        Mechanism.LOCAL_TRADE,
        _TOKEN_RX
        + "向"
        + _TOKEN_RX
        + "支付"
        + _NUMBER_RX
        + "文钱，换取"
        + _TOKEN_RX
        + "。",
    ),
    (Mechanism.CULTIVATION, _TOKEN_RX + "修炼后以灵力隔空取来" + _TOKEN_RX + "。"),
    (Mechanism.MAGIC, _TOKEN_RX + "施展法术复制了" + _TOKEN_RX + "。"),
    (Mechanism.REBIRTH, _TOKEN_RX + "带着前世记忆重生回到" + _NUMBER_RX + "年。"),
    (Mechanism.SYSTEM, _TOKEN_RX + "从超现实系统获得" + _TOKEN_RX + "。"),
    (
        Mechanism.MODERN_CORPORATE_SCHEMA,
        _TOKEN_RX + "按现代公司股权会计规则取得" + _TOKEN_RX + "控制权。",
    ),
    (
        Mechanism.COST_FREE_CULTIVATION_ADVANCE,
        _TOKEN_RX + "未付任何资源或代价便跨越了全部境界。",
    ),
    (Mechanism.UNKNOWN, _TOKEN_RX + "仿佛凭空取得" + _TOKEN_RX + "。"),
)
METHOD_POLICY_HASH = sha256(
    canonical_bytes(
        {
            "profile": PROFILE,
            "version": "1.0",
            "taxonomy": [v.value for v in Mechanism],
            "cores": [{"mechanism": v.value, "regex": p} for v, p in _RX_RULES],
            "wrappers": {k: v.value for k, v in _WRAPPERS.items()},
            "default": ["WORLD", "OCCURRED"],
            "negation": "ONE_CORE_PREFIX_并非_NOT_OCCURRED",
            "nested_or_unknown": "WHOLE_SPAN_UNSUPPORTED",
            "aliases": "ACTUAL_ENTITY_DISPLAY_ALIASES_LOCAL_ID_UNIQUE_TOKEN_NO_VALUES",
            "producer": [INVENTORY_PRODUCER, PROPOSAL_PRODUCER],
            "coordinates": "EXACT_UTF8_AND_CODE_POINT_HALF_OPEN_NO_NORMALIZATION",
            "check_ids": list(CHECK_IDS),
            "dependencies": [[], [], [0, 1], [0]],
            "statuses": ["FINISHED", "ERROR", "NOT_EXECUTED"],
            "aggregation": "FAIL_ERROR_UNKNOWN_PASS_NONEMPTY_COMPLETE_REQUIRED",
            "no_claims": "ACTUAL_LOCAL_POLICY_GUARD_UNKNOWN_NOT_POLICYRESULT_PASS",
            "policies": [POLICY_HASH, BUSINESS_POLICY_HASH, PROGRESSION_POLICY_HASH],
            "natural_prose": "NOT_VERIFIED",
            "production": "BLOCKED",
        }
    )
).hexdigest()
_TOKEN = object()
_FALSE = {
    "can_commit": False,
    "can_issue_permit": False,
    "can_dispatch": False,
    "accepted": False,
    "published": False,
}


class Q2Error(ValueError):
    """Stable source-free diagnostics."""


def _hash(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _row(value: object, keys: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise Q2Error("INVALID_Q2_RECORD")
    return cast(dict[str, object], value)


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise Q2Error("INVALID_Q2_HASH")
    return value


def _encode(raw: bytes) -> str:
    return b64encode(raw).decode("ascii")


def _decode(value: object) -> bytes:
    if type(value) is not str:
        raise Q2Error("INVALID_Q2_BYTES")
    raw = b64decode(value, validate=True)
    if _encode(raw) != value:
        raise Q2Error("INVALID_Q2_BYTES")
    return raw


def _text(raw: bytes) -> str:
    if type(raw) is not bytes or not raw:
        raise Q2Error("INVALID_Q2_PROSE")
    try:
        return raw.decode("utf-8")
    except UnicodeError:
        raise Q2Error("INVALID_Q2_PROSE") from None


def _timestamp(value: object) -> datetime:
    if type(value) is not str:
        raise Q2Error("INVALID_Q2_TIME")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if utc_timestamp(parsed) != value:
        raise Q2Error("INVALID_Q2_TIME")
    return parsed


def _code(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", value) is None:
        raise Q2Error("INVALID_Q2_CODE")
    return value


@dataclass(frozen=True, slots=True)
class GenreAlias:
    entity_id: EntityId
    alias: str

    def __post_init__(self) -> None:
        if (
            type(self.entity_id) is not EntityId
            or type(self.alias) is not str
            or not self.alias.strip()
            or any(
                c in "【】" or ord(c) < 32 or 127 <= ord(c) <= 159 for c in self.alias
            )
        ):
            raise Q2Error("INVALID_Q2_CATALOG")
        try:
            self.alias.encode("utf-8")
        except UnicodeError:
            raise Q2Error("INVALID_Q2_CATALOG") from None

    def to_dict(self) -> dict[str, object]:
        return {"entity_id": self.entity_id.to_dict(), "alias": self.alias}

    @classmethod
    def from_dict(cls, value: object) -> GenreAlias:
        row = _row(value, {"entity_id", "alias"})
        return cls(EntityId.from_dict(row["entity_id"]), cast(str, row["alias"]))


def _catalog(values: tuple[GenreAlias, ...]) -> tuple[GenreAlias, ...]:
    if (
        type(values) is not tuple
        or any(type(v) is not GenreAlias for v in values)
        or len({(v.entity_id, v.alias) for v in values}) != len(values)
        or len({v.entity_id.project for v in values}) > 1
    ):
        raise Q2Error("INVALID_Q2_CATALOG")
    return tuple(sorted(values, key=lambda v: (str(v.entity_id), v.alias)))


def _catalog_hash(values: tuple[GenreAlias, ...]) -> str:
    return _hash(canonical_bytes([v.to_dict() for v in _catalog(values)]))


def _ranges(text: str) -> tuple[tuple[int, int], ...]:
    """Coordinates only: no mechanism, semantic labels or producer output."""
    ranges: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(text):
        start = cursor
        if text[cursor].isspace() or (cursor == 0 and text[cursor] == "\ufeff"):
            cursor += 1
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
        else:
            quotes, token = 0, False
            while cursor < len(text):
                character = text[cursor]
                cursor += 1
                if character == "【":
                    token = True
                elif token:
                    if character == "】":
                        token = False
                elif character == "“":
                    quotes += 1
                elif character == "”":
                    quotes = max(0, quotes - 1)
                    if quotes == 0:
                        break
                elif character == "。" and quotes == 0:
                    break
        ranges.append((start, cursor))
    return tuple(ranges)


type _Classification = tuple[Mechanism, ClaimContext, Occurrence, tuple[EntityId, ...]]


def _resolve(
    names: tuple[str, ...], catalog: tuple[GenreAlias, ...]
) -> tuple[EntityId, ...] | None:
    ids: list[EntityId] = []
    for name in names:
        matches = {v.entity_id for v in catalog if v.alias == name}
        if len(matches) != 1:
            return None
        ids.append(next(iter(matches)))
    return tuple(ids)


def _proposal_classify(
    body: str, catalog: tuple[GenreAlias, ...]
) -> _Classification | None:
    """Anchored regex producer; no inventory parser or classified AST."""
    context, occurrence = ClaimContext.WORLD, Occurrence.OCCURRED
    wrapper = re.fullmatch(r"(梦中|引用|比喻|误信|假设|谎称|听说)：“([\s\S]+)”", body)
    if wrapper is not None:
        context, body = _WRAPPERS[wrapper[1]], wrapper[2]
    elif body.startswith("并非"):
        occurrence, body = Occurrence.NOT_OCCURRED, body[2:]
    for mechanism, pattern in _RX_RULES:
        match = re.fullmatch(pattern, body)
        if match is None:
            continue
        # Token matches, not a guess from the action's subject or a gold label.
        names = tuple(re.findall(_TOKEN_RX, body))
        ids = _resolve(names, catalog)
        if ids is not None:
            return mechanism, context, occurrence, ids
    return None


def _take_token(body: str) -> tuple[str, str] | None:
    if not body.startswith("【"):
        return None
    end = body.find("】", 1)
    if end < 2 or "【" in body[1:end]:
        return None
    return body[1:end], body[end + 1 :]


def _inventory_classify(
    body: str, catalog: tuple[GenreAlias, ...]
) -> _Classification | None:
    """Independent token/literal consumer; does not call regex classification."""
    context, occurrence = ClaimContext.WORLD, Occurrence.OCCURRED
    for label, category in _WRAPPERS.items():
        prefix = label + "：“"
        if body.startswith(prefix) and body.endswith("”"):
            context, body = category, body[len(prefix) : -1]
            break
    else:
        if body.startswith("并非"):
            occurrence, body = Occurrence.NOT_OCCURRED, body[2:]
    first = _take_token(body)
    if first is None:
        return None
    actor, tail = first
    names = [actor]
    mechanism: Mechanism | None = None
    if tail == "未付任何资源或代价便跨越了全部境界。":
        mechanism = Mechanism.COST_FREE_CULTIVATION_ADVANCE
    elif tail.startswith("带着前世记忆重生回到") and tail.endswith("年。"):
        number = tail[len("带着前世记忆重生回到") : -2]
        if (
            1 <= len(number) <= 18
            and number[0] in "123456789"
            and all(c in "0123456789" for c in number)
        ):
            mechanism = Mechanism.REBIRTH
    elif tail.startswith("向"):
        second = _take_token(tail[1:])
        if second is not None:
            partner, remainder = second
            if remainder.startswith("支付") and "文钱，换取" in remainder:
                number, after = remainder[2:].split("文钱，换取", 1)
                third = _take_token(after)
                if (
                    third is not None
                    and third[1] == "。"
                    and 1 <= len(number) <= 18
                    and number[0] in "123456789"
                    and all(c in "0123456789" for c in number)
                ):
                    names.extend((partner, third[0]))
                    mechanism = Mechanism.LOCAL_TRADE
    else:
        # Literal token parsing, independently from the regex rule table.
        for prefix, suffix, core_mechanism in (
            ("步行走到", "身边。", Mechanism.ORDINARY_ACTION),
            ("修炼后以灵力隔空取来", "。", Mechanism.CULTIVATION),
            ("施展法术复制了", "。", Mechanism.MAGIC),
            ("从超现实系统获得", "。", Mechanism.SYSTEM),
            (
                "按现代公司股权会计规则取得",
                "控制权。",
                Mechanism.MODERN_CORPORATE_SCHEMA,
            ),
            ("仿佛凭空取得", "。", Mechanism.UNKNOWN),
        ):
            if tail.startswith(prefix):
                second = _take_token(tail[len(prefix) :])
                if second is not None and second[1] == suffix:
                    names.append(second[0])
                    mechanism = core_mechanism
                    break
    if mechanism is None:
        return None
    ids = _resolve(tuple(names), catalog)
    return None if ids is None else (mechanism, context, occurrence, ids)


@dataclass(frozen=True, slots=True)
class Q2Segment:
    span: ExactSpan
    kind: str
    mechanism: Mechanism | None = None
    context: ClaimContext | None = None
    occurrence: Occurrence | None = None
    entities: tuple[EntityId, ...] = ()
    reason: str = "CLASSIFIED"

    def __post_init__(self) -> None:
        from anovel.workflow.extractor import ExactSpan

        if (
            type(self.span) is not ExactSpan
            or type(self.entities) is not tuple
            or any(type(v) is not EntityId for v in self.entities)
        ):
            raise Q2Error("INVALID_Q2_SEGMENT")
        if self.kind == "CLAIM":
            if (
                type(self.mechanism) is not Mechanism
                or type(self.context) is not ClaimContext
                or type(self.occurrence) is not Occurrence
                or not self.entities
                or self.reason != "CLASSIFIED"
            ):
                raise Q2Error("INVALID_Q2_SEGMENT")
        elif (
            self.kind not in {"WHITESPACE", "UNSUPPORTED"}
            or any(
                v is not None for v in (self.mechanism, self.context, self.occurrence)
            )
            or self.entities
            or self.reason
            not in {"WHITESPACE", "UNSUPPORTED_SOURCE_SPAN", "AMBIGUOUS_ALIAS"}
        ):
            raise Q2Error("INVALID_Q2_SEGMENT")

    def to_dict(self) -> dict[str, object]:
        return {
            "span": self.span.to_dict(),
            "kind": self.kind,
            "mechanism": None if self.mechanism is None else self.mechanism.value,
            "context": None if self.context is None else self.context.value,
            "occurrence": None if self.occurrence is None else self.occurrence.value,
            "entities": [v.to_dict() for v in self.entities],
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, value: object) -> Q2Segment:
        from anovel.workflow.extractor import ExactSpan

        row = _row(
            value,
            {
                "span",
                "kind",
                "mechanism",
                "context",
                "occurrence",
                "entities",
                "reason",
            },
        )
        if type(row["entities"]) is not list:
            raise Q2Error("INVALID_Q2_SEGMENT")
        return cls(
            ExactSpan.from_dict(row["span"]),
            cast(str, row["kind"]),
            None if row["mechanism"] is None else Mechanism(row["mechanism"]),
            None if row["context"] is None else ClaimContext(row["context"]),
            None if row["occurrence"] is None else Occurrence(row["occurrence"]),
            tuple(EntityId.from_dict(v) for v in row["entities"]),
            cast(str, row["reason"]),
        )


def _segment(
    prose: bytes, start: int, end: int, classification: _Classification | None
) -> Q2Segment:
    from anovel.workflow.extractor import ExactSpan

    span = ExactSpan.from_source(prose, start, end)
    if all(
        c.isspace() or (start == 0 and i == 0 and c == "\ufeff")
        for i, c in enumerate(span.quote)
    ):
        return Q2Segment(span, "WHITESPACE", reason="WHITESPACE")
    if classification is None:
        return Q2Segment(span, "UNSUPPORTED", reason="UNSUPPORTED_SOURCE_SPAN")
    mechanism, context, occurrence, ids = classification
    return Q2Segment(span, "CLAIM", mechanism, context, occurrence, ids)


def _discovery(
    prose: bytes,
    catalog: tuple[GenreAlias, ...],
    producer: str,
    segments: tuple[Q2Segment, ...],
) -> bytes:
    return canonical_bytes(
        {
            "record_type": "q2_raw_discovery",
            "schema_version": "1.0",
            "profile": PROFILE,
            "producer": producer,
            "method_policy_hash": METHOD_POLICY_HASH,
            "prose_hash": _hash(prose),
            "catalog_hash": _catalog_hash(catalog),
            "segments": [v.to_dict() for v in segments],
        }
    )


def proposal_backend(prose: bytes, catalog: tuple[GenreAlias, ...]) -> bytes:
    """First responsibility: regex proposals, without inventory or Pack input."""
    text, catalog = _text(prose), _catalog(catalog)
    segments = tuple(
        _segment(prose, start, end, _proposal_classify(text[start:end], catalog))
        for start, end in _ranges(text)
    )
    return _discovery(prose, catalog, PROPOSAL_PRODUCER, segments)


def blind_inventory(prose: bytes, catalog: tuple[GenreAlias, ...]) -> bytes:
    """Independently enumerate full raw source before any proposal is available."""
    text, catalog = _text(prose), _catalog(catalog)
    segments = tuple(
        _segment(prose, start, end, _inventory_classify(text[start:end], catalog))
        for start, end in _ranges(text)
    )
    return _discovery(prose, catalog, INVENTORY_PRODUCER, segments)


def _read_discovery(
    raw: bytes, prose: bytes, catalog: tuple[GenreAlias, ...], *, inventory: bool
) -> tuple[Q2Segment, ...]:
    row = _row(
        decode_canonical(raw),
        {
            "record_type",
            "schema_version",
            "profile",
            "producer",
            "method_policy_hash",
            "prose_hash",
            "catalog_hash",
            "segments",
        },
    )
    if (
        row["record_type"] != "q2_raw_discovery"
        or row["schema_version"] != "1.0"
        or row["profile"] != PROFILE
        or row["producer"] != (INVENTORY_PRODUCER if inventory else PROPOSAL_PRODUCER)
        or row["method_policy_hash"] != METHOD_POLICY_HASH
        or row["prose_hash"] != _hash(prose)
        or row["catalog_hash"] != _catalog_hash(catalog)
        or type(row["segments"]) is not list
    ):
        raise Q2Error("INVALID_Q2_DISCOVERY")
    segments = tuple(Q2Segment.from_dict(v) for v in row["segments"])
    previous = 0
    for segment in segments:
        segment.span.verify(prose)
        if segment.span.start < previous:
            raise Q2Error("INVALID_Q2_DISCOVERY")
        if any(v not in {a.entity_id for a in catalog} for v in segment.entities):
            raise Q2Error("INVALID_Q2_DISCOVERY")
        previous = segment.span.end
    if inventory:
        ranges = _ranges(_text(prose))
        if tuple((v.span.start, v.span.end) for v in segments) != ranges:
            raise Q2Error("INVALID_Q2_INVENTORY")
        # Audit only the declared spans. Do not call the discovery producer.
        if any(
            v
            != _segment(
                prose,
                v.span.start,
                v.span.end,
                _inventory_classify(v.span.quote, catalog),
            )
            for v in segments
        ):
            raise Q2Error("INVALID_Q2_INVENTORY")
    if (
        _discovery(
            prose,
            catalog,
            INVENTORY_PRODUCER if inventory else PROPOSAL_PRODUCER,
            segments,
        )
        != raw
    ):
        raise Q2Error("INVALID_Q2_DISCOVERY")
    return segments


@dataclass(frozen=True, slots=True)
class Q2Finding:
    code: str
    verdict: str
    span: ExactSpan | None = None

    def __post_init__(self) -> None:
        from anovel.workflow.extractor import ExactSpan

        _code(self.code)
        if (
            type(self.verdict) is not str
            or self.verdict not in {"FAIL", "UNKNOWN", "ERROR"}
            or (self.span is not None and type(self.span) is not ExactSpan)
        ):
            raise Q2Error("INVALID_Q2_FINDING")

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "verdict": self.verdict,
            "span": None if self.span is None else self.span.to_dict(),
        }


def _verdict(findings: tuple[Q2Finding, ...]) -> str:
    return next(
        (
            v
            for v in ("FAIL", "ERROR", "UNKNOWN")
            if any(f.verdict == v for f in findings)
        ),
        "PASS",
    )


def _correspondence(
    prose: bytes, inventory: tuple[Q2Segment, ...], proposed: tuple[Q2Segment, ...]
) -> dict[str, object]:
    findings: list[Q2Finding] = []
    cursor = 0
    for segment in proposed:
        if segment.span.start != cursor:
            findings.append(Q2Finding("PROPOSAL_COVERAGE_GAP", "FAIL", segment.span))
        cursor = segment.span.end
    if cursor != len(_text(prose)):
        findings.append(Q2Finding("PROPOSAL_COVERAGE_GAP", "FAIL"))
    by_span = {(v.span.start, v.span.end): v for v in proposed}
    known_spans = {(v.span.start, v.span.end) for v in inventory}
    for segment in inventory:
        if segment.kind == "UNSUPPORTED":
            findings.append(
                Q2Finding("UNSUPPORTED_SOURCE_SPAN", "UNKNOWN", segment.span)
            )
        else:
            found = by_span.get((segment.span.start, segment.span.end))
            if found is None:
                findings.append(
                    Q2Finding("MISSING_MECHANISM_PROPOSITION", "FAIL", segment.span)
                )
            elif found != segment:
                findings.append(
                    Q2Finding("RAW_PROPOSITION_MISMATCH", "FAIL", segment.span)
                )
    for segment in proposed:
        if (
            segment.kind == "CLAIM"
            and (segment.span.start, segment.span.end) not in known_spans
        ):
            findings.append(
                Q2Finding("UNGROUNDED_MECHANISM_PROPOSITION", "FAIL", segment.span)
            )
    if not any(v.kind == "CLAIM" for v in inventory):
        findings.append(Q2Finding("NO_MECHANISM_CLAIMS", "UNKNOWN"))
    return {
        "record_type": "q2_correspondence",
        "verdict": _verdict(tuple(findings)),
        "diagnostics": [v.to_dict() for v in findings],
    }


def _claims(
    prose: bytes, source_id: EntityId, inventory: tuple[Q2Segment, ...]
) -> tuple[SemanticClaim, ...]:
    return tuple(
        SemanticClaim(
            f"raw-{v.span.start}-{v.span.end}",
            cast(Mechanism, v.mechanism),
            cast(ClaimContext, v.context),
            cast(Occurrence, v.occurrence),
            EvidenceSpan(
                source_id, _hash(prose), v.span.start, v.span.end, v.span.quote
            ),
            f"{PROFILE}:{METHOD_POLICY_HASH}:sealed-inventory",
        )
        for v in inventory
        if v.kind == "CLAIM"
    )


def _no_claims_record(
    prose: bytes, source_id: EntityId, binding: ProjectGenreBinding
) -> dict[str, object]:
    return {
        "record_type": "q2_policy_no_claims",
        "profile": PROFILE,
        "method_policy_hash": METHOD_POLICY_HASH,
        "prose_hash": _hash(prose),
        "source_id": source_id.to_dict(),
        "binding": binding.to_dict(),
        "verdict": "UNKNOWN",
        "reason": "NO_MECHANISM_CLAIMS",
    }


def _policy_output(
    prose: bytes,
    source_id: EntityId,
    binding: ProjectGenreBinding,
    inventory: tuple[Q2Segment, ...],
) -> bytes:
    claims = _claims(prose, source_id, inventory)
    if not claims:
        # The old SourceDocument deliberately rejects blank text. A real local
        # no-proposition guard is UNKNOWN, not a fabricated old PolicyResult.
        return canonical_bytes(_no_claims_record(prose, source_id, binding))
    return canonical_bytes(
        GenrePolicy(binding)
        .check(SourceDocument(source_id, _text(prose)), claims)
        .to_dict()
    )


def _policy_audit(
    raw: bytes,
    prose: bytes,
    source_id: EntityId,
    binding: ProjectGenreBinding,
    inventory: tuple[Q2Segment, ...],
) -> PolicyResult | str:
    """Rebuild static PolicyResult invariants without invoking GenrePolicy.check."""
    claims = _claims(prose, source_id, inventory)
    if not claims:
        if raw != canonical_bytes(_no_claims_record(prose, source_id, binding)):
            raise Q2Error("INVALID_Q2_POLICY_RESULT")
        return "UNKNOWN"
    row = _row(
        decode_canonical(raw),
        {
            "binding",
            "document",
            "diagnostics",
            "policy_hash",
            "policy_version",
            "scope",
            "prose_coverage",
            "status",
            "selection",
        },
    )
    if type(row["diagnostics"]) is not list or len(row["diagnostics"]) != max(
        1, len(claims)
    ):
        raise Q2Error("INVALID_Q2_POLICY_RESULT")
    diagnostics: list[PolicyDiagnostic] = []
    for index, value in enumerate(row["diagnostics"]):
        entry = _row(value, {"claim", "status", "code", "rule_id"})
        claim = claims[index] if claims else None
        if entry["claim"] != (None if claim is None else claim.to_dict()):
            raise Q2Error("INVALID_Q2_POLICY_RESULT")
        diagnostics.append(
            PolicyDiagnostic(
                claim,
                PolicyStatus(entry["status"]),
                cast(str, entry["code"]),
                cast(str, entry["rule_id"]),
            )
        )
    result = PolicyResult(
        binding,
        SourceDocument(source_id, _text(prose)),
        tuple(diagnostics),
        cast(str, row["policy_hash"]),
        cast(str, row["policy_version"]),
        cast(str, row["scope"]),
        cast(str, row["prose_coverage"]),
    )
    if canonical_bytes(result.to_dict()) != raw:
        raise Q2Error("INVALID_Q2_POLICY_RESULT")
    return result


_EXEC_FIELDS = {
    "record_type",
    "schema_version",
    "check_id",
    "input_hash",
    "method_policy_hash",
    "request_id",
    "attempt_id",
    "execution_status",
    "started_at",
    "finished_at",
    "result_base64",
    "result_hash",
    "error_code",
    "reason",
}


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
class Q2Execution:
    payload: bytes = field(repr=False)

    def __post_init__(self) -> None:
        try:
            row = _row(decode_canonical(self.payload), _EXEC_FIELDS)
            if (
                row["record_type"] != "q2_execution"
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
            raise Q2Error("INVALID_Q2_EXECUTION") from None

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    def payload_bytes(self) -> bytes:
        return self.payload

    @classmethod
    def from_dict(cls, value: object) -> Q2Execution:
        return cls(canonical_bytes(value))

    @classmethod
    def from_bytes(cls, raw: bytes) -> Q2Execution:
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
) -> Q2Execution:
    started = utc_timestamp(datetime.now(UTC))
    status, error = "FINISHED", None
    try:
        raw = method()
        if type(raw) is not bytes:
            raise ValueError
    except Exception:
        status, error = "ERROR", "NATIVE_EXECUTION_ERROR"
        raw = canonical_bytes(
            {"record_type": "q2_execution_error", "check_id": check_id, "code": error}
        )
    if status == "FINISHED":
        try:
            audit(raw)
        except Exception:
            status, error = "ERROR", "INVALID_STAGE_RESULT"
    return Q2Execution.from_dict(
        {
            "record_type": "q2_execution",
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


def _not_executed(check_id: str, input_hash: str) -> Q2Execution:
    return Q2Execution.from_dict(
        {
            "record_type": "q2_execution",
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
    binding: ProjectGenreBinding,
    catalog: tuple[GenreAlias, ...],
) -> dict[str, object]:
    _text(prose)
    if (
        type(source_id) is not EntityId
        or type(binding) is not ProjectGenreBinding
        or source_id.project != binding.project
        or any(v.entity_id.project != source_id.project for v in _catalog(catalog))
    ):
        raise Q2Error("Q2_SOURCE_SCOPE_MISMATCH")
    # Validate that this exact frozen Pack is supported before any dispatch.
    GenrePolicy(binding)
    return {
        "prose_base64": _encode(prose),
        "prose_hash": _hash(prose),
        "source_id": source_id.to_dict(),
        "binding": binding.to_dict(),
        "catalog": [v.to_dict() for v in _catalog(catalog)],
        "method_policy_hash": METHOD_POLICY_HASH,
    }


def _audit_stage(
    execution: Q2Execution, audit: Callable[[bytes], object]
) -> object | None:
    raw = execution.result_bytes
    if raw is None:
        return None
    row = execution.to_dict()
    if execution.execution_status == "ERROR":
        if row["error_code"] == "NATIVE_EXECUTION_ERROR":
            if raw != canonical_bytes(
                {
                    "record_type": "q2_execution_error",
                    "check_id": execution.check_id,
                    "code": "NATIVE_EXECUTION_ERROR",
                }
            ):
                raise Q2Error("INVALID_Q2_ERROR_RESULT")
        else:
            try:
                audit(raw)
            except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
                pass
            else:
                raise Q2Error("INVALID_Q2_ERROR_RESULT")
        return None
    return audit(raw)


def _read_correspondence(raw: bytes, expected: dict[str, object]) -> dict[str, object]:
    if raw != canonical_bytes(expected):
        raise Q2Error("INVALID_Q2_CORRESPONDENCE")
    return expected


def _findings(value: dict[str, object], prose: bytes) -> tuple[Q2Finding, ...]:
    from anovel.workflow.extractor import ExactSpan

    entries = value["diagnostics"]
    if type(entries) is not list:
        raise Q2Error("INVALID_Q2_DIAGNOSTICS")
    findings: list[Q2Finding] = []
    for entry in entries:
        row = _row(entry, {"code", "verdict", "span"})
        span = None if row["span"] is None else ExactSpan.from_dict(row["span"])
        if span is not None:
            span.verify(prose)
        findings.append(
            Q2Finding(cast(str, row["code"]), cast(str, row["verdict"]), span)
        )
    return tuple(findings)


def _evidence_audit(
    prose: bytes,
    source_id: EntityId,
    binding: ProjectGenreBinding,
    catalog: tuple[GenreAlias, ...],
    executions: tuple[Q2Execution, ...],
) -> dict[str, object]:
    from anovel.workflow.extractor import ExactSpan

    source = _input_record(prose, source_id, binding, catalog)
    input_hash = _hash(canonical_bytes(source))
    if tuple(v.check_id for v in executions) != CHECK_IDS or any(
        v.input_hash != input_hash for v in executions
    ):
        raise Q2Error("Q2_EXECUTION_CLOSURE_MISMATCH")
    if any(v.execution_status == "NOT_EXECUTED" for v in executions[:2]):
        raise Q2Error("Q2_EXECUTION_CLOSURE_MISMATCH")
    inventory = cast(
        tuple[Q2Segment, ...] | None,
        _audit_stage(
            executions[0],
            lambda raw: _read_discovery(raw, prose, catalog, inventory=True),
        ),
    )
    proposal = cast(
        tuple[Q2Segment, ...] | None,
        _audit_stage(
            executions[1],
            lambda raw: _read_discovery(raw, prose, catalog, inventory=False),
        ),
    )
    for index, ready in (
        (2, inventory is not None and proposal is not None),
        (3, inventory is not None),
    ):
        if (executions[index].execution_status != "NOT_EXECUTED") != ready:
            raise Q2Error("Q2_EXECUTION_DEPENDENCY_MISMATCH")
    findings: list[Q2Finding] = []
    for execution in executions:
        if execution.execution_status == "ERROR":
            findings.append(Q2Finding(execution.check_id + "_ERROR", "ERROR"))
    correspondence = None
    if inventory is not None and proposal is not None:
        expected = _correspondence(prose, inventory, proposal)
        correspondence = cast(
            dict[str, object] | None,
            _audit_stage(
                executions[2], lambda raw: _read_correspondence(raw, expected)
            ),
        )
        if correspondence is not None:
            findings.extend(_findings(correspondence, prose))
    # Inventory diagnoses survive proposal/correspondence errors.
    if inventory is not None:
        findings.extend(
            Q2Finding("UNSUPPORTED_SOURCE_SPAN", "UNKNOWN", v.span)
            for v in inventory
            if v.kind == "UNSUPPORTED"
        )
        if not any(v.kind == "CLAIM" for v in inventory):
            findings.append(Q2Finding("NO_MECHANISM_CLAIMS", "UNKNOWN"))
    policy = None
    if inventory is not None:
        policy = cast(
            PolicyResult | str | None,
            _audit_stage(
                executions[3],
                lambda raw: _policy_audit(raw, prose, source_id, binding, inventory),
            ),
        )
        if isinstance(policy, PolicyResult):
            for diagnosis in policy.diagnostics:
                if diagnosis.status is not PolicyStatus.PASS:
                    span = (
                        None
                        if diagnosis.claim is None
                        else ExactSpan.from_source(
                            prose,
                            diagnosis.claim.evidence.start,
                            diagnosis.claim.evidence.end,
                        )
                    )
                    findings.append(
                        Q2Finding(diagnosis.code, diagnosis.status.value, span)
                    )
    unique = {canonical_bytes(v.to_dict()): v for v in findings}
    findings = list(unique.values())
    status = _verdict(tuple(findings))
    if status == "PASS" and (
        inventory is None
        or not any(v.kind == "CLAIM" for v in inventory)
        or any(v.execution_status != "FINISHED" for v in executions)
    ):
        raise Q2Error("Q2_EXECUTION_CLOSURE_MISMATCH")
    return {
        "input_hash": input_hash,
        "q2_status": status,
        "correspondence_status": "ERROR"
        if executions[2].execution_status == "ERROR"
        else "NOT_EXECUTED"
        if correspondence is None
        else correspondence["verdict"],
        "genre_status": "ERROR"
        if executions[3].execution_status == "ERROR"
        else "NOT_EXECUTED"
        if policy is None
        else policy.status.value
        if isinstance(policy, PolicyResult)
        else policy,
        "finite_coverage_status": "UNKNOWN"
        if inventory is None
        else "INCOMPLETE"
        if any(v.kind == "UNSUPPORTED" for v in inventory)
        else "COMPLETE",
        "diagnostics": [v.to_dict() for v in findings],
    }


def _evidence_record(
    prose: bytes,
    source_id: EntityId,
    binding: ProjectGenreBinding,
    catalog: tuple[GenreAlias, ...],
    executions: tuple[Q2Execution, ...],
) -> dict[str, object]:
    return {
        "record_type": "q2_evidence",
        "schema_version": "1.0",
        "profile": PROFILE,
        **_input_record(prose, source_id, binding, catalog),
        "executions": [v.to_dict() for v in executions],
        **_evidence_audit(prose, source_id, binding, catalog, executions),
        "coverage_status": "NOT_VERIFIED",
        "production_status": "UNKNOWN",
        "semantic_status": "UNKNOWN",
        "aggregate_status": "BLOCKED",
        **_FALSE,
    }


_EVIDENCE_FIELDS = {
    "record_type",
    "schema_version",
    "profile",
    "prose_base64",
    "prose_hash",
    "source_id",
    "binding",
    "catalog",
    "method_policy_hash",
    "executions",
    "input_hash",
    "q2_status",
    "correspondence_status",
    "genre_status",
    "finite_coverage_status",
    "diagnostics",
    "coverage_status",
    "production_status",
    "semantic_status",
    "aggregate_status",
    *_FALSE,
}


@dataclass(frozen=True, slots=True)
class Q2Evidence:
    payload: bytes = field(repr=False)
    _executions: tuple[Q2Execution, ...] = field(init=False, repr=False, compare=False)
    _findings: tuple[Q2Finding, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        try:
            row = _row(decode_canonical(self.payload), _EVIDENCE_FIELDS)
            prose = _decode(row["prose_base64"])
            source_id = EntityId.from_dict(row["source_id"])
            binding = ProjectGenreBinding.from_dict(row["binding"])
            if type(row["catalog"]) is not list or type(row["executions"]) is not list:
                raise ValueError
            catalog = tuple(GenreAlias.from_dict(v) for v in row["catalog"])
            executions = tuple(Q2Execution.from_dict(v) for v in row["executions"])
            if (
                canonical_bytes(
                    _evidence_record(prose, source_id, binding, catalog, executions)
                )
                != self.payload
            ):
                raise ValueError
            object.__setattr__(self, "_executions", executions)
            object.__setattr__(self, "_findings", _findings(row, prose))
        except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
            raise Q2Error("INVALID_Q2_EVIDENCE") from None

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    def payload_bytes(self) -> bytes:
        return self.payload

    @classmethod
    def from_dict(cls, value: object) -> Q2Evidence:
        return cls(canonical_bytes(value))

    @classmethod
    def from_bytes(cls, raw: bytes) -> Q2Evidence:
        return cls(raw)

    @property
    def record_hash(self) -> str:
        return _hash(self.payload)

    @property
    def content_hash(self) -> str:
        return self.record_hash

    @property
    def executions(self) -> tuple[Q2Execution, ...]:
        return self._executions

    @property
    def diagnostics(self) -> tuple[Q2Finding, ...]:
        return self._findings

    @property
    def prose(self) -> bytes:
        return _decode(self.to_dict()["prose_base64"])

    @property
    def prose_hash(self) -> str:
        return _hash(self.prose)

    @property
    def inventory_raw(self) -> bytes:
        return cast(bytes, self.executions[0].result_bytes)

    @property
    def proposal_raw(self) -> bytes:
        return cast(bytes, self.executions[1].result_bytes)

    @property
    def q2_status(self) -> str:
        return cast(str, self.to_dict()["q2_status"])

    @property
    def correspondence_status(self) -> str:
        return cast(str, self.to_dict()["correspondence_status"])

    @property
    def genre_status(self) -> str:
        return cast(str, self.to_dict()["genre_status"])

    @property
    def finite_coverage_status(self) -> str:
        return cast(str, self.to_dict()["finite_coverage_status"])

    @property
    def method_policy_hash(self) -> str:
        return METHOD_POLICY_HASH


def execute_raw_q2(
    prose: bytes,
    *,
    source_id: EntityId,
    binding: ProjectGenreBinding,
    catalog: tuple[GenreAlias, ...],
) -> Q2Evidence:
    """Actual fixed local runner over small data, without Workflow publication."""
    catalog = _catalog(catalog)
    source = _input_record(prose, source_id, binding, catalog)
    input_hash = _hash(canonical_bytes(source))
    inventory_execution = _stage(
        CHECK_IDS[0],
        input_hash,
        lambda: blind_inventory(prose, catalog),
        lambda raw: _read_discovery(raw, prose, catalog, inventory=True),
    )
    proposal_execution = _stage(
        CHECK_IDS[1],
        input_hash,
        lambda: proposal_backend(prose, catalog),
        lambda raw: _read_discovery(raw, prose, catalog, inventory=False),
    )
    inventory = (
        None
        if inventory_execution.execution_status != "FINISHED"
        else _read_discovery(
            cast(bytes, inventory_execution.result_bytes),
            prose,
            catalog,
            inventory=True,
        )
    )
    proposal = (
        None
        if proposal_execution.execution_status != "FINISHED"
        else _read_discovery(
            cast(bytes, proposal_execution.result_bytes),
            prose,
            catalog,
            inventory=False,
        )
    )
    if inventory is not None and proposal is not None:
        expected = _correspondence(prose, inventory, proposal)
        correspondence = _stage(
            CHECK_IDS[2],
            input_hash,
            lambda: canonical_bytes(expected),
            lambda raw: _read_correspondence(raw, expected),
        )
    else:
        correspondence = _not_executed(CHECK_IDS[2], input_hash)
    if inventory is not None:
        policy = _stage(
            CHECK_IDS[3],
            input_hash,
            lambda: _policy_output(prose, source_id, binding, inventory),
            lambda raw: _policy_audit(raw, prose, source_id, binding, inventory),
        )
    else:
        policy = _not_executed(CHECK_IDS[3], input_hash)
    executions = (inventory_execution, proposal_execution, correspondence, policy)
    return Q2Evidence(
        canonical_bytes(
            _evidence_record(prose, source_id, binding, catalog, executions)
        )
    )


def _bound_source(
    observation: ExtractionObservation,
) -> tuple[bytes, EntityId, ProjectGenreBinding, tuple[GenreAlias, ...]]:
    from anovel.contracts.models import CanonView
    from anovel.workflow.extractor import ExtractionObservation

    if type(observation) is not ExtractionObservation:
        raise Q2Error("Q2_OBSERVATION_REQUIRED")
    contract = observation.assembly.child.source.contract
    retained = {v.name: v.content for v in contract.retained_inputs}
    binding = ProjectGenreBinding.from_dict(decode_canonical(retained["pack"]))
    view = CanonView.from_dict(decode_canonical(retained["canon"]))
    if (
        binding.project != observation.project
        or binding.ref.content_hash != contract.pack_hash
    ):
        raise Q2Error("Q2_PACK_SOURCE_CHANGED")
    registered_extensions().validate_baseline(view.baseline)
    entries: set[tuple[EntityId, str]] = set()
    for entity in view.root.seed.entities:
        for alias in (entity.display_name, *entity.aliases, entity.id.local_id):
            # Unsafe names remain unrepresentable, never guessed or normalized.
            try:
                GenreAlias(entity.id, alias)
            except Q2Error:
                continue
            entries.add((entity.id, alias))
    catalog = _catalog(
        tuple(GenreAlias(identity, alias) for identity, alias in entries)
    )
    return observation.assembly.prose, observation.source_id, binding, catalog


def _run_record(
    observation: ExtractionObservation, evidence: Q2Evidence
) -> dict[str, object]:
    prose, source_id, binding, catalog = _bound_source(observation)
    expected = _input_record(prose, source_id, binding, catalog)
    if any(evidence.to_dict()[k] != v for k, v in expected.items()):
        raise Q2Error("Q2_EVIDENCE_SOURCE_CHANGED")
    return {
        "record_type": "local_q2_run",
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
        "q2_status": evidence.q2_status,
        "finite_coverage_status": evidence.finite_coverage_status,
        "coverage_status": "NOT_VERIFIED",
        "source_qualification": "FINITE_LOCAL_RAW_METHOD_NOT_PRODUCTION_QUALIFIED",
        "production_status": "UNKNOWN",
        "semantic_status": "UNKNOWN",
        "aggregate_status": "BLOCKED",
        **_FALSE,
    }


_RUN_FIELDS = {
    "record_type",
    "schema_version",
    "profile",
    "observation_base64",
    "observation_hash",
    "evidence_base64",
    "evidence_hash",
    "project",
    "branch",
    "run_id",
    "step_id",
    "assembly_hash",
    "prose_hash",
    "method_policy_hash",
    "q2_status",
    "finite_coverage_status",
    "coverage_status",
    "source_qualification",
    "production_status",
    "semantic_status",
    "aggregate_status",
    *_FALSE,
}


@dataclass(frozen=True, slots=True)
class Q2Run:
    payload: bytes = field(repr=False)
    _observation: ExtractionObservation = field(init=False, repr=False, compare=False)
    _evidence: Q2Evidence = field(init=False, repr=False, compare=False)
    _token: object | None = field(init=False, default=None, repr=False, compare=False)
    _token_hash: str | None = field(init=False, default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        from anovel.workflow.extractor import ExtractionObservation

        try:
            row = _row(decode_canonical(self.payload), _RUN_FIELDS)
            observation = ExtractionObservation.from_bytes(
                _decode(row["observation_base64"])
            )
            evidence = Q2Evidence.from_bytes(_decode(row["evidence_base64"]))
            if canonical_bytes(_run_record(observation, evidence)) != self.payload:
                raise ValueError
            object.__setattr__(self, "_observation", observation)
            object.__setattr__(self, "_evidence", evidence)
        except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
            raise Q2Error("INVALID_Q2_RUN") from None

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    def payload_bytes(self) -> bytes:
        return self.payload

    @classmethod
    def from_dict(cls, value: object) -> Q2Run:
        return cls(canonical_bytes(value))

    @classmethod
    def from_bytes(cls, raw: bytes) -> Q2Run:
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
    def evidence(self) -> Q2Evidence:
        return self._evidence

    @property
    def executions(self) -> tuple[Q2Execution, ...]:
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
        return METHOD_POLICY_HASH

    @property
    def q2_status(self) -> str:
        return self.evidence.q2_status

    @property
    def correspondence_status(self) -> str:
        return self.evidence.correspondence_status

    @property
    def genre_status(self) -> str:
        return self.evidence.genre_status

    @property
    def finite_coverage_status(self) -> str:
        return self.evidence.finite_coverage_status

    @property
    def diagnostics(self) -> tuple[Q2Finding, ...]:
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


def require_local_execution_q2(run: Q2Run) -> None:
    """Cooperative local publication guard, not hostile same-owner protection."""
    if (
        type(run) is not Q2Run
        or run._token is not _TOKEN
        or run._token_hash != run.record_hash
    ):
        raise Q2Error("Q2_NATIVE_EXECUTION_REQUIRED")


def execute_local_q2(observation: ExtractionObservation) -> Q2Run:
    prose, source_id, binding, catalog = _bound_source(observation)
    evidence = execute_raw_q2(
        prose, source_id=source_id, binding=binding, catalog=catalog
    )
    result = Q2Run(canonical_bytes(_run_record(observation, evidence)))
    object.__setattr__(result, "_token", _TOKEN)
    object.__setattr__(result, "_token_hash", result.record_hash)
    return result
