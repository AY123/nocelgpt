"""Bounded genre decisions over supplied, source-bound semantic annotations.

This module does not extract or verify annotations, establish world facts,
check whole-prose coverage, issue a Permit, or write Canon. An annotation's
interpretation reference identifies its supplier's evidence, not its truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256

from anovel.canon.identity import canonical_bytes
from anovel.domain.events import Occurrence
from anovel.domain.identity import EntityId
from anovel.genre.extensions.contracts import BUSINESS_PACK_IDENTITY
from anovel.genre.extensions.progression_contracts import PROGRESSION_PACK_IDENTITY
from anovel.genre.registry import (
    GenreError,
    PackRef,
    ProjectGenreBinding,
    Selection,
    StrategySelection,
)


class PolicyError(GenreError):
    """Malformed, mismatched, cross-project or unsupported policy inputs."""


class Mechanism(str, Enum):
    ORDINARY_ACTION = "ORDINARY_ACTION"
    LOCAL_TRADE = "LOCAL_TRADE"
    CULTIVATION = "CULTIVATION"
    MAGIC = "MAGIC"
    REBIRTH = "REBIRTH"
    SYSTEM = "SYSTEM"
    MODERN_CORPORATE_SCHEMA = "MODERN_CORPORATE_SCHEMA"
    COST_FREE_CULTIVATION_ADVANCE = "COST_FREE_CULTIVATION_ADVANCE"
    UNKNOWN = "UNKNOWN"


class ClaimContext(str, Enum):
    WORLD = "WORLD"
    QUOTATION = "QUOTATION"
    DREAM = "DREAM"
    METAPHOR = "METAPHOR"
    BELIEF = "BELIEF"
    HYPOTHESIS = "HYPOTHESIS"
    LIE = "LIE"
    UNKNOWN = "UNKNOWN"


class PolicyStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


POLICY_VERSION = "1.0.0"
SUPPORTED_PACK_REFS = (
    PackRef(
        "urban.business.realistic",
        "1.0.0",
        "8cdcad278b40f570487ac31f2ef6340e68329943098863776f6048ebd1cda061",
    ),
    PackRef(
        "fantasy.eastern.progression",
        "1.0.0",
        "820499c61491affb367b13a3b7e200911e9c0e586df1b55e15eb82c24cf56968",
    ),
)

# Exact, immutable rules, not natural-language matching or a plugin registry.
# Each row binds one Pack to the decisions for WORLD/OCCURRED mechanisms only.
_RULES = (
    (
        SUPPORTED_PACK_REFS[0],
        (
            (Mechanism.ORDINARY_ACTION, PolicyStatus.PASS),
            (Mechanism.LOCAL_TRADE, PolicyStatus.PASS),
            (Mechanism.MODERN_CORPORATE_SCHEMA, PolicyStatus.PASS),
            (Mechanism.CULTIVATION, PolicyStatus.FAIL),
            (Mechanism.MAGIC, PolicyStatus.FAIL),
            (Mechanism.REBIRTH, PolicyStatus.FAIL),
            (Mechanism.SYSTEM, PolicyStatus.FAIL),
            (Mechanism.COST_FREE_CULTIVATION_ADVANCE, PolicyStatus.FAIL),
        ),
    ),
    (
        SUPPORTED_PACK_REFS[1],
        (
            (Mechanism.ORDINARY_ACTION, PolicyStatus.PASS),
            (Mechanism.LOCAL_TRADE, PolicyStatus.PASS),
            (Mechanism.CULTIVATION, PolicyStatus.PASS),
            (Mechanism.MODERN_CORPORATE_SCHEMA, PolicyStatus.FAIL),
            (Mechanism.COST_FREE_CULTIVATION_ADVANCE, PolicyStatus.FAIL),
            (Mechanism.MAGIC, PolicyStatus.UNKNOWN),
            (Mechanism.REBIRTH, PolicyStatus.UNKNOWN),
            (Mechanism.SYSTEM, PolicyStatus.UNKNOWN),
        ),
    ),
)
POLICY_HASH = sha256(
    canonical_bytes(
        {
            "version": POLICY_VERSION,
            "supported_packs": [ref.to_dict() for ref in SUPPORTED_PACK_REFS],
            "world_occurred_rules": [
                {
                    "pack_ref": ref.to_dict(),
                    "mechanisms": [
                        {"mechanism": mechanism.value, "status": status.value}
                        for mechanism, status in rules
                    ],
                }
                for ref, rules in _RULES
            ],
            "decision_order": [
                "contradictory same source/span/mechanism annotation => UNKNOWN",
                "unknown context/mechanism/occurrence => UNKNOWN",
                "explicit non-WORLD context => PASS/NOT_WORLD_FACT",
                "explicit NOT_OCCURRED => PASS/NOT_OCCURRED",
                "WORLD/OCCURRED => exact Pack mechanism rule",
            ],
            "aggregation": "FAIL before UNKNOWN before PASS; retain every diagnosis",
            "empty_claims": "UNKNOWN",
            "no_strategy_match": "no proposal/claims; applicability PASS only",
            "span_encoding": "Unicode character half-open interval; full UTF-8 SHA256",
            "interpretation": "supplied annotations, not verified semantics",
            "prose_coverage": "NOT_VERIFIED",
        }
    )
).hexdigest()

# Keep the accepted 1.0 policy fingerprint reproducible for existing books.
# A registered business Pack has an explicit new policy, never an implicit
# widening of the old supported-Pack set or its historical fingerprint.
BUSINESS_PACK_REF = PackRef(*BUSINESS_PACK_IDENTITY)
BUSINESS_POLICY_VERSION = "1.1.0"
BUSINESS_POLICY_HASH = sha256(
    canonical_bytes(
        {
            "version": BUSINESS_POLICY_VERSION,
            "base_policy_hash": POLICY_HASH,
            "pack_ref": BUSINESS_PACK_REF.to_dict(),
            "world_occurred_rules": [
                {"mechanism": mechanism.value, "status": status.value}
                for mechanism, status in _RULES[0][1]
            ],
            "scope": "Same bounded reality policy; typed business invariants checked separately",
        }
    )
).hexdigest()


PROGRESSION_PACK_REF = PackRef(*PROGRESSION_PACK_IDENTITY)
PROGRESSION_POLICY_VERSION = "1.1.0"
PROGRESSION_POLICY_HASH = sha256(
    canonical_bytes(
        {
            "version": PROGRESSION_POLICY_VERSION,
            "base_policy_hash": POLICY_HASH,
            "pack_ref": PROGRESSION_PACK_REF.to_dict(),
            "world_occurred_rules": [
                {"mechanism": mechanism.value, "status": status.value}
                for mechanism, status in _RULES[1][1]
            ],
            "scope": "Same bounded fantasy policy; typed progression invariants checked separately",
        }
    )
).hexdigest()


def _policy_identity(ref: PackRef) -> tuple[str, str]:
    if ref == BUSINESS_PACK_REF:
        return BUSINESS_POLICY_VERSION, BUSINESS_POLICY_HASH
    if ref == PROGRESSION_PACK_REF:
        return PROGRESSION_POLICY_VERSION, PROGRESSION_POLICY_HASH
    return POLICY_VERSION, POLICY_HASH


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise PolicyError(f"{field} must be a nonempty string")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise PolicyError(f"{field} must be valid Unicode") from error
    return value


def _id(value: object, field: str) -> EntityId:
    if type(value) is not EntityId:
        raise PolicyError(f"{field} must be an exact EntityId")
    return value


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise PolicyError("source identity requires a lowercase SHA256 digest")
    return value


def _binding(value: object) -> ProjectGenreBinding:
    if type(value) is not ProjectGenreBinding:
        raise PolicyError("policy needs an exact project GenrePack binding")
    if value.ref not in (*SUPPORTED_PACK_REFS, BUSINESS_PACK_REF, PROGRESSION_PACK_REF):
        raise PolicyError("no policy is bound to this exact Pack ID/version/hash")
    return value


@dataclass(frozen=True, slots=True)
class SourceDocument:
    id: EntityId
    text: str

    def __post_init__(self) -> None:
        _id(self.id, "source ID")
        _text(self.text, "source text")

    @property
    def content_hash(self) -> str:
        return sha256(self.text.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id.to_dict(),
            "text": self.text,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class EvidenceSpan:
    source_id: EntityId
    source_sha256: str
    start: int
    end: int
    quote: str

    def __post_init__(self) -> None:
        _id(self.source_id, "evidence source ID")
        _digest(self.source_sha256)
        if (
            type(self.start) is not int
            or type(self.end) is not int
            or self.start < 0
            or self.end <= self.start
        ):
            raise PolicyError("span needs strict increasing nonnegative integers")
        _text(self.quote, "evidence quote")

    def to_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id.to_dict(),
            "source_sha256": self.source_sha256,
            "start": self.start,
            "end": self.end,
            "quote": self.quote,
        }


@dataclass(frozen=True, slots=True)
class SemanticClaim:
    id: str
    mechanism: Mechanism
    context: ClaimContext
    occurrence: Occurrence
    evidence: EvidenceSpan
    interpretation_ref: str

    def __post_init__(self) -> None:
        _text(self.id, "claim ID")
        if (
            type(self.mechanism) is not Mechanism
            or type(self.context) is not ClaimContext
            or type(self.occurrence) is not Occurrence
            or type(self.evidence) is not EvidenceSpan
        ):
            raise PolicyError("claim needs exact mechanism/context/occurrence/span")
        _text(self.interpretation_ref, "interpretation reference")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "mechanism": self.mechanism.value,
            "context": self.context.value,
            "occurrence": self.occurrence.value,
            "evidence": self.evidence.to_dict(),
            "interpretation_ref": self.interpretation_ref,
        }


@dataclass(frozen=True, slots=True)
class PolicyDiagnostic:
    claim: SemanticClaim | None
    status: PolicyStatus
    code: str
    rule_id: str

    def __post_init__(self) -> None:
        if self.claim is not None and type(self.claim) is not SemanticClaim:
            raise PolicyError("diagnostic claim must be an exact semantic claim")
        if type(self.status) is not PolicyStatus:
            raise PolicyError("diagnostic status must be a PolicyStatus")
        _text(self.code, "diagnostic code")
        _text(self.rule_id, "rule ID")

    def to_dict(self) -> dict[str, object]:
        return {
            "claim": None if self.claim is None else self.claim.to_dict(),
            "status": self.status.value,
            "code": self.code,
            "rule_id": self.rule_id,
        }


def _claims(value: tuple[SemanticClaim, ...]) -> tuple[SemanticClaim, ...]:
    if type(value) is not tuple or any(type(c) is not SemanticClaim for c in value):
        raise PolicyError("claims must be an immutable tuple of semantic claims")
    if len({c.id for c in value}) != len(value):
        raise PolicyError("claim IDs must be unique within a check")
    return value


def _source(
    binding: ProjectGenreBinding,
    document: SourceDocument,
    claims: tuple[SemanticClaim, ...],
) -> None:
    if type(document) is not SourceDocument or document.id.project != binding.project:
        raise PolicyError("source document must belong to the bound project")
    for claim in claims:
        span = claim.evidence
        if (
            span.source_id != document.id
            or span.source_sha256 != document.content_hash
            or span.end > len(document.text)
            or document.text[span.start : span.end] != span.quote
        ):
            raise PolicyError("claim evidence does not match this exact source span")


@dataclass(frozen=True, slots=True)
class PolicyResult:
    binding: ProjectGenreBinding
    document: SourceDocument | None
    diagnostics: tuple[PolicyDiagnostic, ...]
    policy_hash: str
    policy_version: str
    scope: str
    prose_coverage: str = "NOT_VERIFIED"
    selection: StrategySelection | None = None

    def __post_init__(self) -> None:
        _binding(self.binding)
        version, digest = _policy_identity(self.binding.ref)
        if (
            type(self.diagnostics) is not tuple
            or not self.diagnostics
            or any(type(d) is not PolicyDiagnostic for d in self.diagnostics)
        ):
            raise PolicyError("results require immutable nonempty diagnostics")
        if (
            type(self.policy_hash) is not str
            or self.policy_hash != digest
            or type(self.policy_version) is not str
            or self.policy_version != version
            or type(self.scope) is not str
            or self.scope not in {"STRUCTURED_CLAIMS_ONLY", "OPTIONAL_STRATEGY"}
            or type(self.prose_coverage) is not str
            or self.prose_coverage != "NOT_VERIFIED"
        ):
            raise PolicyError("result policy identity or scope is invalid")
        claims = _claims(
            tuple(d.claim for d in self.diagnostics if d.claim is not None)
        )
        if self.document is not None:
            _source(self.binding, self.document, claims)
        elif claims or self.scope == "STRUCTURED_CLAIMS_ONLY":
            raise PolicyError("structured claim results require their source document")
        if self.scope == "STRUCTURED_CLAIMS_ONLY":
            if self.selection is not None:
                raise PolicyError(
                    "structured claims must not carry a strategy selection"
                )
            expected = _evaluate(self.binding.ref, claims)
        else:
            expected = _strategy_diagnostics(
                self.binding, self.selection, self.document, claims
            )
        if self.diagnostics != expected:
            raise PolicyError(
                "result diagnostics do not match the actual policy decision"
            )

    @property
    def status(self) -> PolicyStatus:
        if any(d.status is PolicyStatus.FAIL for d in self.diagnostics):
            return PolicyStatus.FAIL
        if any(d.status is PolicyStatus.UNKNOWN for d in self.diagnostics):
            return PolicyStatus.UNKNOWN
        return PolicyStatus.PASS

    def to_dict(self) -> dict[str, object]:
        return {
            "binding": self.binding.to_dict(),
            "document": None if self.document is None else self.document.to_dict(),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "policy_hash": self.policy_hash,
            "policy_version": self.policy_version,
            "scope": self.scope,
            "prose_coverage": self.prose_coverage,
            "status": self.status.value,
            "selection": None
            if self.selection is None
            else {
                "status": self.selection.status.value,
                "binding": self.selection.binding.to_dict(),
                "strategy": None
                if self.selection.strategy is None
                else self.selection.strategy.to_dict(),
            },
        }


def _claim_decision(
    ref: PackRef, claim: SemanticClaim, contradictory: bool
) -> PolicyDiagnostic:
    if contradictory:
        return PolicyDiagnostic(
            claim,
            PolicyStatus.UNKNOWN,
            "CONTRADICTORY_ANNOTATION",
            "GENRE-ANNOTATION-1",
        )
    for unknown, code in (
        (claim.context is ClaimContext.UNKNOWN, "UNKNOWN_CONTEXT"),
        (claim.mechanism is Mechanism.UNKNOWN, "UNKNOWN_MECHANISM"),
        (claim.occurrence is Occurrence.UNKNOWN, "UNKNOWN_OCCURRENCE"),
    ):
        if unknown:
            return PolicyDiagnostic(
                claim, PolicyStatus.UNKNOWN, code, "GENRE-UNKNOWN-1"
            )
    if claim.context is not ClaimContext.WORLD:
        return PolicyDiagnostic(
            claim, PolicyStatus.PASS, "NOT_WORLD_FACT", "GENRE-NONWORLD-1"
        )
    if claim.occurrence is Occurrence.NOT_OCCURRED:
        return PolicyDiagnostic(
            claim, PolicyStatus.PASS, "NOT_OCCURRED", "GENRE-NONOCCURRENCE-1"
        )
    for supported, rules in _RULES:
        if (
            supported == ref
            or (ref == BUSINESS_PACK_REF and supported == SUPPORTED_PACK_REFS[0])
            or (ref == PROGRESSION_PACK_REF and supported == SUPPORTED_PACK_REFS[1])
        ):
            for mechanism, status in rules:
                if mechanism is claim.mechanism:
                    code = {
                        PolicyStatus.PASS: "MECHANISM_ALLOWED",
                        PolicyStatus.FAIL: "WORLD_MECHANISM_CONFLICT",
                        PolicyStatus.UNKNOWN: "MECHANISM_NOT_ESTABLISHED",
                    }[status]
                    return PolicyDiagnostic(
                        claim, status, code, f"{ref.id}:{mechanism.value}:1"
                    )
    # An incomplete future rule table must not turn an omitted decision into PASS.
    return PolicyDiagnostic(
        claim, PolicyStatus.UNKNOWN, "NO_MECHANISM_RULE", "GENRE-UNKNOWN-1"
    )


def _evaluate(
    ref: PackRef, claims: tuple[SemanticClaim, ...]
) -> tuple[PolicyDiagnostic, ...]:
    if not claims:
        return (
            PolicyDiagnostic(None, PolicyStatus.UNKNOWN, "NO_CLAIMS", "GENRE-EMPTY-1"),
        )
    annotations: dict[
        tuple[EntityId, str, int, int, Mechanism], set[tuple[ClaimContext, Occurrence]]
    ] = {}
    keys = []
    for claim in claims:
        span = claim.evidence
        key = (
            span.source_id,
            span.source_sha256,
            span.start,
            span.end,
            claim.mechanism,
        )
        keys.append(key)
        annotations.setdefault(key, set()).add((claim.context, claim.occurrence))
    return tuple(
        _claim_decision(ref, claim, len(annotations[key]) > 1)
        for claim, key in zip(claims, keys, strict=True)
    )


def _strategy_diagnostics(
    binding: ProjectGenreBinding,
    selection: StrategySelection | None,
    proposal: SourceDocument | None,
    claims: tuple[SemanticClaim, ...],
) -> tuple[PolicyDiagnostic, ...]:
    if type(selection) is not StrategySelection or selection.binding != binding:
        raise PolicyError("strategy selection must retain the exact policy binding")
    if selection.status is Selection.NO_MATCH:
        if proposal is not None or claims:
            raise PolicyError("NO_MATCH cannot inject a proposal or semantic claims")
        return (
            PolicyDiagnostic(
                None, PolicyStatus.PASS, "NO_OPTIONAL_STRATEGY", "GENRE-NOMATCH-1"
            ),
        )
    if proposal is None:
        if claims:
            raise PolicyError("strategy claims require their proposal document")
        return (
            PolicyDiagnostic(
                None,
                PolicyStatus.UNKNOWN,
                "MISSING_STRATEGY_PROPOSAL",
                "GENRE-STRATEGY-1",
            ),
        )
    _source(binding, proposal, claims)
    return _evaluate(binding.ref, claims)


@dataclass(frozen=True, slots=True)
class GenrePolicy:
    binding: ProjectGenreBinding

    def __post_init__(self) -> None:
        _binding(self.binding)

    def check(
        self, document: SourceDocument, claims: tuple[SemanticClaim, ...]
    ) -> PolicyResult:
        checked = _claims(claims)
        _source(self.binding, document, checked)
        version, digest = _policy_identity(self.binding.ref)
        return PolicyResult(
            self.binding,
            document,
            _evaluate(self.binding.ref, checked),
            digest,
            version,
            "STRUCTURED_CLAIMS_ONLY",
        )

    def check_strategy(
        self,
        selection: StrategySelection,
        proposal: SourceDocument | None = None,
        claims: tuple[SemanticClaim, ...] = (),
    ) -> PolicyResult:
        checked = _claims(claims)
        diagnoses = _strategy_diagnostics(self.binding, selection, proposal, checked)
        version, digest = _policy_identity(self.binding.ref)
        return PolicyResult(
            self.binding,
            proposal,
            diagnoses,
            digest,
            version,
            "OPTIONAL_STRATEGY",
            selection=selection,
        )
