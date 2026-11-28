"""Finite offline extraction observations, never natural-prose certification.

The proposal regex and blind inventory scanner discover from raw UTF-8 and a
value-free identity/type catalogue. Inventory is sealed before proposal output
is read. Baseline values are used only afterwards to materialize/preview the
existing finite Delta. Retained observations are audit data, not authority or
freshness receipts; decoding them does not run either producer again.
"""

from __future__ import annotations

import json
import re
from base64 import b64decode, b64encode
from dataclasses import dataclass, field
from hashlib import sha256
from math import isfinite
from typing import cast

from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.contracts.models import CanonView
from anovel.domain.delta import (
    FactBaseline,
    FactPath,
    FactState,
    NarrativeDelta,
    NoChange,
    Operation,
    OperationMeta,
    Precondition,
    ProseEvidence,
    ScalarKind,
    SetFact,
    preview_delta,
)
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import EntityId
from anovel.domain.knowledge import Scalar
from anovel.genre.extensions.registration import registered_extensions

from .assembly import ChapterAssembly
from .models import WorkflowError

PROFILE = "FINITE_FACT_SENTENCES_V1"
QUIET_SENTENCE = "风掠过窗边。"
PROPOSAL_PRODUCER = "offline-finite-proposal/1.0"
INVENTORY_PRODUCER = "offline-blind-inventory/1.0"
_PREFIXES = {
    "听说": "RUMOR",
    "误信": "BELIEF",
    "并非": "NEGATED",
    "梦中": "DREAM",
    "计划": "PLANNED",
    "回忆": "RECOLLECTION",
}
_KINDS = frozenset(
    {"WHITESPACE", "QUIET", "ACTUAL", "QUOTATION", "UNSUPPORTED", *_PREFIXES.values()}
)
_CLAIM_KINDS = _KINDS - {"WHITESPACE", "QUIET", "UNSUPPORTED"}
_POLICY = {
    "profile": PROFILE,
    "quiet_sentence": QUIET_SENTENCE,
    "verbs": {"变为": "SET_FACT", "仍为": "NO_CHANGE"},
    "prefixes": _PREFIXES,
    "quotation": "引用：“<complete sentence>”",
    "coordinates": "ZERO_BASED_HALF_OPEN_UNICODE_AND_EXACT_UTF8",
    "inventory": INVENTORY_PRODUCER,
    "proposal": PROPOSAL_PRODUCER,
    "semantic_scope": "FINITE_ENGINEERING_PROFILE_NOT_Q0_Q3",
}
POLICY_HASH = sha256(canonical_bytes(_POLICY)).hexdigest()
_JSON_SCALAR = (
    r'"(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"'
    r"|true|false|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?"
)
_PROPOSAL_SENTENCE = re.compile(
    r"(?P<prefix>听说|误信|并非|梦中|计划|回忆)?"
    r"(?P<alias>[^。\r\n]+?)(?P<verb>变为|仍为)"
    r"(?P<value>" + _JSON_SCALAR + r")。"
)
_DISCOVERY_FIELDS = {
    "record_type",
    "schema_version",
    "profile",
    "producer",
    "prose_hash",
    "catalog_hash",
    "segments",
}
_FIXED: dict[str, object] = {
    "record_type": "offline_extraction_observation",
    "schema_version": "1.0",
    "profile": PROFILE,
    "policy_hash": POLICY_HASH,
    "evidence_scope": "FINITE_ENGINEERING_PROFILE_NOT_Q0_Q3",
    "semantic_status": "UNKNOWN",
    "observation_only": True,
    "can_commit": False,
    "can_issue_permit": False,
    "can_dispatch": False,
    "accepted": False,
    "published": False,
}
_OBSERVATION_FIELDS = set(_FIXED) | {
    "assembly",
    "assembly_hash",
    "prose_hash",
    "project",
    "branch",
    "run_id",
    "step_id",
    "source_id",
    "chapter_id",
    "parent_ref",
    "contract_hash",
    "pack_hash",
    "catalog",
    "catalog_hash",
    "proposal_raw_base64",
    "proposal_raw_hash",
    "inventory_raw_base64",
    "inventory_raw_hash",
    "coverage",
    "proposal_delta",
    "operation_count",
    "correspondence_status",
    "diagnostics",
}


def _record(value: object, keys: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise ValueError("closed record required")
    return cast(dict[str, object], value)


def _hash(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _scalar(value: object) -> Scalar:
    if type(value) not in (str, bool, int, float):
        raise ValueError("non-null finite JSON scalar required")
    if type(value) is float and not isfinite(value):
        raise ValueError("finite scalar required")
    canonical_bytes(value)
    return cast(Scalar, value)


def _kind(value: Scalar) -> ScalarKind:
    if type(value) is bool:
        return ScalarKind.BOOLEAN
    return ScalarKind.STRING if type(value) is str else ScalarKind.NUMBER


def _text(raw: bytes) -> str:
    if type(raw) is not bytes or not raw:
        raise ValueError("complete UTF-8 required")
    return raw.decode("utf-8")


def _encoded(raw: bytes) -> str:
    return b64encode(raw).decode("ascii")


def _decoded(value: object) -> bytes:
    if type(value) is not str:
        raise ValueError
    raw = b64decode(value, validate=True)
    if _encoded(raw) != value:
        raise ValueError
    return raw


@dataclass(frozen=True, slots=True)
class FactAlias:
    fact_id: EntityId
    alias: str
    value_kind: ScalarKind

    def __post_init__(self) -> None:
        if (
            type(self.fact_id) is not EntityId
            or type(self.alias) is not str
            or not self.alias.strip()
            or any(c in self.alias for c in '。\r\n\t“”"')
            or any(v in self.alias for v in ("变为", "仍为"))
            or any(self.alias.startswith(v) for v in (*_PREFIXES, "引用："))
            or type(self.value_kind) is not ScalarKind
        ):
            raise WorkflowError("INVALID_EXTRACTION_CATALOG")
        try:
            self.alias.encode("utf-8")
        except UnicodeError:
            raise WorkflowError("INVALID_EXTRACTION_CATALOG") from None

    def to_dict(self) -> dict[str, object]:
        return {
            "fact_id": self.fact_id.to_dict(),
            "alias": self.alias,
            "value_kind": self.value_kind.value,
        }

    @classmethod
    def from_dict(cls, value: object) -> FactAlias:
        row = _record(value, {"fact_id", "alias", "value_kind"})
        return cls(
            EntityId.from_dict(row["fact_id"]),
            cast(str, row["alias"]),
            ScalarKind(row["value_kind"]),
        )


def _catalog(catalog: tuple[FactAlias, ...]) -> tuple[FactAlias, ...]:
    if type(catalog) is not tuple or any(type(v) is not FactAlias for v in catalog):
        raise WorkflowError("INVALID_EXTRACTION_CATALOG")
    if (
        len({v.alias for v in catalog}) != len(catalog)
        or len({v.fact_id for v in catalog}) != len(catalog)
        or len({v.fact_id.project for v in catalog}) > 1
    ):
        raise WorkflowError("INVALID_EXTRACTION_CATALOG")
    return tuple(sorted(catalog, key=lambda v: (v.fact_id.project, v.fact_id.local_id)))


def _catalog_hash(catalog: tuple[FactAlias, ...]) -> str:
    return _hash(canonical_bytes([v.to_dict() for v in _catalog(catalog)]))


def _baseline(assembly: ChapterAssembly) -> FactBaseline:
    retained = next(
        v for v in assembly.child.source.contract.retained_inputs if v.name == "canon"
    )
    return CanonView.from_dict(decode_canonical(retained.content)).baseline


def make_catalog(
    assembly: ChapterAssembly, *, aliases: tuple[FactAlias, ...] | None = None
) -> tuple[FactAlias, ...]:
    """Copy only registered identities/types; no baseline values reach discovery."""
    if type(assembly) is not ChapterAssembly:
        raise WorkflowError("INVALID_EXTRACTION_SOURCE")
    baseline = _baseline(assembly)
    expected = {v.seed_fact.id: v.value_kind for v in baseline.facts}
    values = (
        _catalog(aliases)
        if aliases is not None
        else _catalog(
            tuple(
                FactAlias(fact_id, fact_id.local_id, kind)
                for fact_id, kind in expected.items()
            )
        )
    )
    if {v.fact_id: v.value_kind for v in values} != expected:
        raise WorkflowError("INVALID_EXTRACTION_CATALOG")
    return values


@dataclass(frozen=True, slots=True)
class ExactSpan:
    start: int
    end: int
    quote: str = field(repr=False)
    byte_start: int
    byte_end: int

    def __post_init__(self) -> None:
        if (
            any(
                type(v) is not int
                for v in (self.start, self.end, self.byte_start, self.byte_end)
            )
            or self.start < 0
            or self.end <= self.start
            or self.byte_start < 0
            or self.byte_end <= self.byte_start
            or type(self.quote) is not str
            or len(self.quote) != self.end - self.start
            or len(self.quote.encode("utf-8")) != self.byte_end - self.byte_start
        ):
            raise WorkflowError("INVALID_EXTRACTION_SPAN")

    @classmethod
    def from_source(cls, prose: bytes, start: int, end: int) -> ExactSpan:
        text = _text(prose)
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= len(text)
        ):
            raise WorkflowError("INVALID_EXTRACTION_SPAN")
        return cls(
            start,
            end,
            text[start:end],
            len(text[:start].encode("utf-8")),
            len(text[:end].encode("utf-8")),
        )

    def verify(self, prose: bytes) -> None:
        if self != self.from_source(prose, self.start, self.end):
            raise WorkflowError("INVALID_EXTRACTION_SPAN")

    def to_dict(self) -> dict[str, object]:
        return {
            "start": self.start,
            "end": self.end,
            "quote": self.quote,
            "byte_start": self.byte_start,
            "byte_end": self.byte_end,
        }

    @classmethod
    def from_dict(cls, value: object) -> ExactSpan:
        row = _record(value, {"start", "end", "quote", "byte_start", "byte_end"})
        return cls(
            cast(int, row["start"]),
            cast(int, row["end"]),
            cast(str, row["quote"]),
            cast(int, row["byte_start"]),
            cast(int, row["byte_end"]),
        )


@dataclass(frozen=True, slots=True)
class ExtractionSegment:
    kind: str
    span: ExactSpan
    fact_id: EntityId | None = None
    operation: str | None = None
    value_json: bytes | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not str
            or self.kind not in _KINDS
            or type(self.span) is not ExactSpan
        ):
            raise ValueError
        if self.kind in _CLAIM_KINDS:
            if (
                type(self.fact_id) is not EntityId
                or self.operation not in {"SET_FACT", "NO_CHANGE"}
                or type(self.value_json) is not bytes
            ):
                raise ValueError
            _scalar(decode_canonical(self.value_json))
        elif (
            self.fact_id is not None
            or self.operation is not None
            or self.value_json is not None
        ):
            raise ValueError

    @property
    def value(self) -> Scalar | None:
        return (
            None
            if self.value_json is None
            else _scalar(decode_canonical(self.value_json))
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "span": self.span.to_dict(),
            "fact_id": None if self.fact_id is None else self.fact_id.to_dict(),
            "operation": self.operation,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, value: object) -> ExtractionSegment:
        row = _record(value, {"kind", "span", "fact_id", "operation", "value"})
        return cls(
            cast(str, row["kind"]),
            ExactSpan.from_dict(row["span"]),
            None if row["fact_id"] is None else EntityId.from_dict(row["fact_id"]),
            cast(str | None, row["operation"]),
            None if row["value"] is None else canonical_bytes(_scalar(row["value"])),
        )


@dataclass(frozen=True, slots=True)
class ExtractionDiagnostic:
    code: str
    state: str
    span: ExactSpan | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "state": self.state,
            "span": None if self.span is None else self.span.to_dict(),
        }


def _segment(
    prose: bytes,
    start: int,
    end: int,
    kind: str,
    fact: FactAlias | None = None,
    verb: str | None = None,
    value: Scalar | None = None,
) -> ExtractionSegment:
    return ExtractionSegment(
        kind,
        ExactSpan.from_source(prose, start, end),
        None if fact is None else fact.fact_id,
        None if verb is None else {"变为": "SET_FACT", "仍为": "NO_CHANGE"}[verb],
        None if value is None else canonical_bytes(value),
    )


def _discovery(
    prose: bytes,
    catalog: tuple[FactAlias, ...],
    producer: str,
    segments: list[ExtractionSegment],
) -> bytes:
    return canonical_bytes(
        {
            "record_type": "finite_extraction_discovery",
            "schema_version": "1.0",
            "profile": PROFILE,
            "producer": producer,
            "prose_hash": _hash(prose),
            "catalog_hash": _catalog_hash(catalog),
            "segments": [v.to_dict() for v in segments],
        }
    )


def proposal_backend(prose: bytes, catalog: tuple[FactAlias, ...]) -> bytes:
    """Regex producer: no baseline, Contract, expected answer or inventory input."""
    text, catalog = _text(prose), _catalog(catalog)
    by_alias = {v.alias: v for v in catalog}
    segments: list[ExtractionSegment] = []
    cursor = 0
    while cursor < len(text):
        start = cursor
        if text[cursor].isspace() or (cursor == 0 and text[cursor] == "\ufeff"):
            cursor += 1
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
            segments.append(_segment(prose, start, cursor, "WHITESPACE"))
            continue
        if text.startswith(QUIET_SENTENCE, cursor):
            cursor += len(QUIET_SENTENCE)
            segments.append(_segment(prose, start, cursor, "QUIET"))
            continue
        quoted = text.startswith("引用：“", cursor)
        inner = cursor + len("引用：“") if quoted else cursor
        match = _PROPOSAL_SENTENCE.match(text, inner)
        if match is not None and (not quoted or text.startswith("”", match.end())):
            cursor = match.end() + int(quoted)
            alias = match["alias"]
            try:
                value = _scalar(json.loads(match["value"]))
            except (TypeError, ValueError):
                segments.append(_segment(prose, start, cursor, "UNSUPPORTED"))
                continue
            fact = by_alias.get(alias)
            # Nested wrappers and unknown identities are outside this profile.
            if (
                fact is None
                or (quoted and match["prefix"] is not None)
                or _kind(value) is not fact.value_kind
            ):
                segments.append(_segment(prose, start, cursor, "UNSUPPORTED"))
            else:
                kind = (
                    "QUOTATION" if quoted else _PREFIXES.get(match["prefix"], "ACTUAL")
                )
                segments.append(
                    _segment(prose, start, cursor, kind, fact, match["verb"], value)
                )
            continue
        # Keep an unknown sentence intact, including possible quoted content.
        ascii_quote, chinese_quote, escaped = False, False, False
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
                chinese_quote = True
            elif not ascii_quote and char == "”":
                chinese_quote = False
            elif char == "。" and not ascii_quote and not chinese_quote:
                break
        segments.append(_segment(prose, start, cursor, "UNSUPPORTED"))
    return _discovery(prose, catalog, PROPOSAL_PRODUCER, segments)


def _inventory_sentence(
    body: str, catalog: tuple[FactAlias, ...]
) -> tuple[str, FactAlias | None, str | None, Scalar | None]:
    """A separate, anchored inventory grammar; never reads proposal AST/output."""
    if body == QUIET_SENTENCE:
        return "QUIET", None, None, None
    if body and all(
        c.isspace() or (i == 0 and c == "\ufeff") for i, c in enumerate(body)
    ):
        return "WHITESPACE", None, None, None
    kind = "ACTUAL"
    if body.startswith("引用：“") and body.endswith("”"):
        kind, body = "QUOTATION", body[len("引用：“") : -1]
    else:
        for prefix, category in _PREFIXES.items():
            if body.startswith(prefix):
                kind, body = category, body[len(prefix) :]
                break
    if not body.endswith("。"):
        return "UNSUPPORTED", None, None, None
    inner = body[:-1]
    for fact in catalog:
        if not inner.startswith(fact.alias):
            continue
        tail = inner[len(fact.alias) :]
        verb = (
            "变为"
            if tail.startswith("变为")
            else "仍为"
            if tail.startswith("仍为")
            else None
        )
        if verb is None:
            continue
        raw_value = tail[len(verb) :]
        try:
            # Complete JSON decoding, independent of the producer regex.
            value, end = json.JSONDecoder().raw_decode(raw_value)
            scalar = _scalar(value)
            if end != len(raw_value) or _kind(scalar) is not fact.value_kind:
                continue
            return kind, fact, verb, scalar
        except (ValueError, TypeError):
            continue
    return "UNSUPPORTED", None, None, None


def _inventory_ranges(text: str) -> tuple[tuple[int, int], ...]:
    """Raw coordinate boundaries only, with no claim or proposal classification."""
    ranges: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(text):
        start = cursor
        if text[cursor].isspace() or (cursor == 0 and text[cursor] == "\ufeff"):
            cursor += 1
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
        else:
            string, escaped, quotation = False, False, False
            while cursor < len(text):
                char = text[cursor]
                cursor += 1
                if string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == '"':
                        string = False
                    continue
                if char == '"':
                    string = True
                elif char == "“":
                    quotation = True
                elif char == "”":
                    quotation = False
                    if text.startswith("引用：“", start):
                        break
                elif char == "。" and not quotation:
                    break
        ranges.append((start, cursor))
    return tuple(ranges)


def blind_inventory(prose: bytes, catalog: tuple[FactAlias, ...]) -> bytes:
    """Scan the entire raw source before reading any proposal result."""
    text, catalog = _text(prose), _catalog(catalog)
    segments: list[ExtractionSegment] = []
    for start, end in _inventory_ranges(text):
        kind, fact, verb, value = _inventory_sentence(text[start:end], catalog)
        segments.append(_segment(prose, start, end, kind, fact, verb, value))
    return _discovery(prose, catalog, INVENTORY_PRODUCER, segments)


def _complete(segments: tuple[ExtractionSegment, ...], prose: bytes) -> bool:
    cursor = 0
    for segment in segments:
        if segment.span.start != cursor:
            return False
        cursor = segment.span.end
    return cursor == len(_text(prose))


def _read_discovery(
    raw: bytes,
    prose: bytes,
    catalog: tuple[FactAlias, ...],
    producer: str,
    *,
    inventory: bool,
) -> tuple[ExtractionSegment, ...]:
    row = _record(decode_canonical(raw), _DISCOVERY_FIELDS)
    if (
        any(
            row[k] != v or type(row[k]) is not str
            for k, v in {
                "record_type": "finite_extraction_discovery",
                "schema_version": "1.0",
                "profile": PROFILE,
                "producer": producer,
                "prose_hash": _hash(prose),
                "catalog_hash": _catalog_hash(catalog),
            }.items()
        )
        or type(row["segments"]) is not list
    ):
        raise ValueError
    segments = tuple(ExtractionSegment.from_dict(v) for v in row["segments"])
    if inventory and tuple(
        (v.span.start, v.span.end) for v in segments
    ) != _inventory_ranges(_text(prose)):
        # A caller cannot split off a qualifier, or merge sentences to conceal
        # a supported transition inside a declared unsupported segment.
        raise ValueError
    by_id = {v.fact_id: v for v in catalog}
    previous = 0
    for segment in segments:
        segment.span.verify(prose)
        if segment.span.start < previous:
            raise ValueError
        previous = segment.span.end
        if segment.fact_id is not None and (
            segment.fact_id not in by_id
            or segment.value is None
            or _kind(segment.value) is not by_id[segment.fact_id].value_kind
        ):
            raise ValueError
        if inventory:
            # Audit the sealed declaration against its exact source sentence;
            # this is validation, not a new inventory/producer attempt.
            kind, fact, verb, value = _inventory_sentence(segment.span.quote, catalog)
            expected = _segment(
                prose, segment.span.start, segment.span.end, kind, fact, verb, value
            )
            if canonical_bytes(expected.to_dict()) != canonical_bytes(
                segment.to_dict()
            ):
                raise ValueError
    if inventory and not _complete(segments, prose):
        raise ValueError
    return segments


def _candidate_id(assembly: ChapterAssembly) -> EntityId:
    return EntityId(assembly.project, "extraction-candidate-" + assembly.record_hash)


def _materialize(
    assembly: ChapterAssembly, claims: tuple[ExtractionSegment, ...]
) -> tuple[NarrativeDelta | None, tuple[ExtractionDiagnostic, ...]]:
    actual = tuple(v for v in claims if v.kind == "ACTUAL")
    if not actual:
        return None, ()
    counts = {v.fact_id: sum(w.fact_id == v.fact_id for w in actual) for v in actual}
    if any(v > 1 for v in counts.values()):
        return None, tuple(
            ExtractionDiagnostic("MULTIPLE_TRANSITIONS_UNSUPPORTED", "UNKNOWN", v.span)
            for v in actual
            if counts[v.fact_id] > 1
        )
    baseline, contract = _baseline(assembly), assembly.child.source.contract
    authorization = "offline-extraction:" + POLICY_HASH
    operations: list[Operation] = []
    for index, claim in enumerate(actual, 1):
        assert claim.fact_id is not None and claim.value is not None
        snapshot = baseline.get(claim.fact_id)
        if snapshot is None:
            raise ValueError
        if claim.operation == "NO_CHANGE" and snapshot.state != FactState.known(
            claim.value
        ):
            return None, (
                ExtractionDiagnostic("NO_CHANGE_VALUE_CONFLICT", "FAIL", claim.span),
            )
        if claim.operation == "SET_FACT" and snapshot.state == FactState.known(
            claim.value
        ):
            return None, (
                ExtractionDiagnostic(
                    "SAME_VALUE_SET_REQUIRES_EXPLICIT_NO_CHANGE", "FAIL", claim.span
                ),
            )
        identity = _hash(
            canonical_bytes(
                {"assembly": assembly.record_hash, "claim": claim.to_dict()}
            )
        )
        meta = OperationMeta(
            EntityId(assembly.project, "extraction-op-" + identity),
            claim.fact_id,
            FactPath.VALUE,
            Precondition.from_snapshot(snapshot),
            ProseEvidence(
                _candidate_id(assembly),
                NarrativePosition(contract.chapter_number, index),
                "draft-extraction-evidence:sha256:" + identity,
            ),
            authorization,
        )
        operations.append(
            NoChange(meta)
            if claim.operation == "NO_CHANGE"
            else SetFact(meta, claim.value)
        )
    delta = NarrativeDelta(
        EntityId(
            assembly.project,
            "extraction-"
            + _hash(
                canonical_bytes(
                    {
                        "assembly": assembly.record_hash,
                        "claims": [v.to_dict() for v in actual],
                        "policy": POLICY_HASH,
                    }
                )
            ),
        ),
        assembly.branch,
        contract.parent_ref,
        _candidate_id(assembly),
        tuple(operations),
    )
    try:
        preview_delta(
            baseline,
            delta,
            source_id=_candidate_id(assembly),
            authorization_refs=frozenset({authorization}),
            extension_registry=registered_extensions(),
        )
    except (TypeError, ValueError):
        return None, (ExtractionDiagnostic("FINITE_DELTA_PREVIEW_REJECTED", "FAIL"),)
    return delta, ()


def audit_extraction_evidence(
    prose: bytes,
    catalog: tuple[FactAlias, ...],
    proposal_raw: bytes,
    inventory_raw: bytes,
) -> tuple[tuple[ExtractionSegment, ...], tuple[ExtractionDiagnostic, ...]]:
    """Compare independent discovery with the proposal on the same raw text."""
    # An invalid inventory is not retained as a fabricated zero observation.
    inventory = _read_discovery(
        inventory_raw, prose, catalog, INVENTORY_PRODUCER, inventory=True
    )
    diagnostics: list[ExtractionDiagnostic] = []
    try:
        proposed = _read_discovery(
            proposal_raw, prose, catalog, PROPOSAL_PRODUCER, inventory=False
        )
    except (TypeError, ValueError, KeyError, UnicodeError):
        return inventory, (ExtractionDiagnostic("PROPOSAL_RESULT_INVALID", "ERROR"),)
    if not _complete(proposed, prose):
        diagnostics.append(ExtractionDiagnostic("PROPOSAL_COVERAGE_GAP", "FAIL"))
    proposed_by_span = {(v.span.start, v.span.end): v for v in proposed}
    inventory_by_span = {(v.span.start, v.span.end): v for v in inventory}
    for expected in inventory:
        key = expected.span.start, expected.span.end
        found = proposed_by_span.get(key)
        if expected.kind == "UNSUPPORTED":
            diagnostics.append(
                ExtractionDiagnostic(
                    "UNSUPPORTED_SOURCE_SPAN", "UNKNOWN", expected.span
                )
            )
        elif found is None:
            diagnostics.append(
                ExtractionDiagnostic("MISSING_PROPOSITION", "FAIL", expected.span)
            )
        elif canonical_bytes(found.to_dict()) != canonical_bytes(expected.to_dict()):
            diagnostics.append(
                ExtractionDiagnostic("PROPOSITION_MISMATCH", "FAIL", expected.span)
            )
    for found in proposed:
        if (
            found.kind in _CLAIM_KINDS
            and (found.span.start, found.span.end) not in inventory_by_span
        ):
            diagnostics.append(
                ExtractionDiagnostic("UNGROUNDED_PROPOSITION", "FAIL", found.span)
            )
    return inventory, tuple(diagnostics)


def _audit(
    assembly: ChapterAssembly,
    catalog: tuple[FactAlias, ...],
    proposal_raw: bytes,
    inventory_raw: bytes,
) -> tuple[
    tuple[ExtractionSegment, ...],
    NarrativeDelta | None,
    tuple[ExtractionDiagnostic, ...],
    str,
]:
    inventory, diagnostics = audit_extraction_evidence(
        assembly.prose,
        make_catalog(assembly, aliases=catalog),
        proposal_raw,
        inventory_raw,
    )
    delta = None
    if not any(v.state in {"FAIL", "ERROR"} for v in diagnostics):
        delta, materialization = _materialize(assembly, inventory)
        diagnostics += materialization
    status = (
        "ERROR"
        if any(v.state == "ERROR" for v in diagnostics)
        else "FAIL"
        if any(v.state == "FAIL" for v in diagnostics)
        else "UNKNOWN"
        if diagnostics
        else "PASS"
    )
    return inventory, delta, diagnostics, status


def _observation_record(
    assembly: ChapterAssembly,
    catalog: tuple[FactAlias, ...],
    proposal_raw: bytes,
    inventory_raw: bytes,
    *,
    audit: tuple[
        tuple[ExtractionSegment, ...],
        NarrativeDelta | None,
        tuple[ExtractionDiagnostic, ...],
        str,
    ]
    | None = None,
) -> dict[str, object]:
    coverage, delta, diagnostics, status = (
        _audit(assembly, catalog, proposal_raw, inventory_raw)
        if audit is None
        else audit
    )
    contract = assembly.child.source.contract
    return {
        **_FIXED,
        "assembly": assembly.to_dict(),
        "assembly_hash": assembly.record_hash,
        "prose_hash": assembly.prose_hash,
        "project": assembly.project,
        "branch": assembly.branch,
        "run_id": assembly.run_id,
        "step_id": assembly.step_id,
        "source_id": _candidate_id(assembly).to_dict(),
        "chapter_id": contract.chapter_id.to_dict(),
        "parent_ref": contract.parent_ref,
        "contract_hash": contract.content_hash,
        "pack_hash": contract.pack_hash,
        "catalog": [v.to_dict() for v in catalog],
        "catalog_hash": _catalog_hash(catalog),
        "proposal_raw_base64": _encoded(proposal_raw),
        "proposal_raw_hash": _hash(proposal_raw),
        "inventory_raw_base64": _encoded(inventory_raw),
        "inventory_raw_hash": _hash(inventory_raw),
        "coverage": [v.to_dict() for v in coverage],
        "proposal_delta": None if delta is None else delta.to_dict(),
        "operation_count": 0 if delta is None else len(delta.operations),
        "correspondence_status": status,
        "diagnostics": [v.to_dict() for v in diagnostics],
    }


@dataclass(frozen=True, slots=True)
class ExtractionObservation:
    payload: bytes = field(repr=False)
    _assembly: ChapterAssembly = field(init=False, repr=False, compare=False)
    _catalog: tuple[FactAlias, ...] = field(init=False, repr=False, compare=False)
    _coverage: tuple[ExtractionSegment, ...] = field(
        init=False, repr=False, compare=False
    )
    _delta: NarrativeDelta | None = field(init=False, repr=False, compare=False)
    _diagnostics: tuple[ExtractionDiagnostic, ...] = field(
        init=False, repr=False, compare=False
    )
    _status: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        try:
            row = _record(decode_canonical(self.payload), _OBSERVATION_FIELDS)
            assembly = ChapterAssembly.from_bytes(canonical_bytes(row["assembly"]))
            if type(row["catalog"]) is not list:
                raise ValueError
            catalog = make_catalog(
                assembly, aliases=tuple(FactAlias.from_dict(v) for v in row["catalog"])
            )
            proposal_raw = _decoded(row["proposal_raw_base64"])
            inventory_raw = _decoded(row["inventory_raw_base64"])
            audit = _audit(assembly, catalog, proposal_raw, inventory_raw)
            expected = _observation_record(
                assembly, catalog, proposal_raw, inventory_raw, audit=audit
            )
            if canonical_bytes(expected) != self.payload:
                raise ValueError
            coverage, delta, diagnostics, status = audit
            object.__setattr__(self, "_assembly", assembly)
            object.__setattr__(self, "_catalog", catalog)
            object.__setattr__(self, "_coverage", coverage)
            object.__setattr__(self, "_delta", delta)
            object.__setattr__(self, "_diagnostics", diagnostics)
            object.__setattr__(self, "_status", status)
        except (
            TypeError,
            ValueError,
            KeyError,
            AttributeError,
            StopIteration,
            RecursionError,
        ):
            raise WorkflowError("INVALID_EXTRACTION_OBSERVATION") from None

    @property
    def assembly(self) -> ChapterAssembly:
        return self._assembly

    @property
    def catalog(self) -> tuple[FactAlias, ...]:
        return self._catalog

    @property
    def coverage(self) -> tuple[ExtractionSegment, ...]:
        return self._coverage

    @property
    def proposal_delta(self) -> NarrativeDelta | None:
        return self._delta

    @property
    def operation_count(self) -> int:
        return 0 if self._delta is None else len(self._delta.operations)

    @property
    def diagnostics(self) -> tuple[ExtractionDiagnostic, ...]:
        return self._diagnostics

    @property
    def correspondence_status(self) -> str:
        return self._status

    @property
    def semantic_status(self) -> str:
        return "UNKNOWN"

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

    @property
    def project(self) -> str:
        return self.assembly.project

    @property
    def branch(self) -> str:
        return self.assembly.branch

    @property
    def run_id(self) -> str:
        return self.assembly.run_id

    @property
    def step_id(self) -> str:
        return self.assembly.step_id

    @property
    def source_id(self) -> EntityId:
        return _candidate_id(self.assembly)

    @property
    def chapter_id(self) -> EntityId:
        return self.assembly.child.source.contract.chapter_id

    @property
    def prose_hash(self) -> str:
        return self.assembly.prose_hash

    @property
    def assembly_hash(self) -> str:
        return self.assembly.record_hash

    @property
    def policy_hash(self) -> str:
        return POLICY_HASH

    @property
    def proposal_raw(self) -> bytes:
        return _decoded(self.to_dict()["proposal_raw_base64"])

    @property
    def inventory_raw(self) -> bytes:
        return _decoded(self.to_dict()["inventory_raw_base64"])

    def to_dict(self) -> dict[str, object]:
        return cast(dict[str, object], decode_canonical(self.payload))

    def payload_bytes(self) -> bytes:
        return self.payload

    @classmethod
    def from_dict(cls, value: object) -> ExtractionObservation:
        try:
            return cls(canonical_bytes(value))
        except (TypeError, ValueError, RecursionError):
            raise WorkflowError("INVALID_EXTRACTION_OBSERVATION") from None

    @classmethod
    def from_bytes(cls, raw: bytes) -> ExtractionObservation:
        return cls(raw)

    @property
    def record_hash(self) -> str:
        return _hash(self.payload)

    @property
    def content_hash(self) -> str:
        return self.record_hash


def reconcile(
    assembly: ChapterAssembly,
    catalog: tuple[FactAlias, ...],
    proposal_raw: bytes,
    inventory_raw: bytes,
) -> ExtractionObservation:
    """Validate sealed audit inputs; never run either discovery producer here."""
    try:
        catalog = make_catalog(assembly, aliases=catalog)
        return ExtractionObservation(
            canonical_bytes(
                _observation_record(assembly, catalog, proposal_raw, inventory_raw)
            )
        )
    except (TypeError, ValueError, KeyError, AttributeError, StopIteration):
        raise WorkflowError("INVALID_EXTRACTION_OBSERVATION") from None


def discover_extraction_evidence(
    prose: bytes, catalog: tuple[FactAlias, ...]
) -> tuple[bytes, bytes]:
    # Seal independent discovery before exposing proposal output to comparison.
    inventory_raw = blind_inventory(prose, catalog)
    try:
        proposal_raw = proposal_backend(prose, catalog)
    except (TypeError, ValueError, RuntimeError, OSError):
        proposal_raw = canonical_bytes(
            {"record_type": "finite_proposal_execution_error", "code": "PRODUCER_ERROR"}
        )
    return proposal_raw, inventory_raw


def extract_assembly(
    assembly: ChapterAssembly, *, aliases: tuple[FactAlias, ...] | None = None
) -> ExtractionObservation:
    catalog = make_catalog(assembly, aliases=aliases)
    return reconcile(
        assembly, catalog, *discover_extraction_evidence(assembly.prose, catalog)
    )
