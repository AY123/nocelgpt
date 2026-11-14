"""Typed business facts and conserved transfers through the existing Delta.

This module validates supplied structured facts. It neither interprets prose
nor writes a database, issues a Permit or advances Canon.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import ClassVar, cast

from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.domain.delta import (
    FactBaseline,
    FactPath,
    FactSnapshot,
    FactStatus,
    NarrativeDelta,
    OperationMeta,
    Precondition,
    ProseEvidence,
    SetFact,
    preview_delta,
)
from anovel.domain.extensions import ExtensionBinding, ExtensionValidationError
from anovel.domain.identity import EntityId
from anovel.domain.knowledge import Proposition, Scalar, WorldFact
from anovel.genre.extensions.contracts import (
    BUSINESS_NAMESPACE,
    BUSINESS_PACK_IDENTITY,
    BUSINESS_SCHEMA_BYTES,
    BUSINESS_SCHEMA_HASH,
    BUSINESS_SCHEMA_ID,
    BUSINESS_VERSION,
    SHARE_PARTS,
)
from anovel.genre.registry import ProjectGenreBinding


class BusinessError(ExtensionValidationError):
    """Unsupported, malformed or inconsistent registered business state."""


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise BusinessError(f"{field} must be a nonempty string")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise BusinessError(f"{field} must be valid Unicode") from error
    return value


def _id(value: object) -> EntityId:
    if type(value) is not EntityId:
        raise BusinessError("business identity must be an exact EntityId")
    _text(value.project, "project")
    _text(value.local_id, "local ID")
    return value


def _integer(value: object, field: str) -> int:
    if type(value) is not int or value < 0:
        raise BusinessError(f"{field} must be a nonnegative strict integer")
    return value


def _record(value: object, keys: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise BusinessError("business record has missing or unknown fields")
    return cast(dict[str, object], value)


def _array(value: object) -> list[object]:
    if type(value) is not list:
        raise BusinessError("business members must be arrays")
    return cast(list[object], value)


def _entity(value: object) -> EntityId:
    row = _record(value, {"project", "local_id"})
    return EntityId(
        _text(row["project"], "project"), _text(row["local_id"], "local ID")
    )


def _same_project(*ids: EntityId) -> None:
    if len({_id(item).project for item in ids}) != 1:
        raise BusinessError("business references cross project scopes")


@dataclass(frozen=True, slots=True)
class Company:
    id: EntityId
    total_parts: int = SHARE_PARTS

    def __post_init__(self) -> None:
        _id(self.id)
        if _integer(self.total_parts, "total_parts") != SHARE_PARTS:
            raise BusinessError("issued company shares must be exactly1000000 parts")

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id.to_dict(), "total_parts": self.total_parts}

    @classmethod
    def from_dict(cls, value: object) -> Company:
        row = _record(value, {"id", "total_parts"})
        return cls(_entity(row["id"]), _integer(row["total_parts"], "total_parts"))


@dataclass(frozen=True, slots=True)
class CashAccount:
    id: EntityId
    owner: EntityId
    currency: str
    balance_minor: int

    def __post_init__(self) -> None:
        _same_project(self.id, self.owner)
        if re.fullmatch(r"[A-Z]{3}", _text(self.currency, "currency")) is None:
            raise BusinessError("currency must be an explicit three-letter code")
        _integer(self.balance_minor, "balance_minor")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id.to_dict(),
            "owner": self.owner.to_dict(),
            "currency": self.currency,
            "balance_minor": self.balance_minor,
        }

    @classmethod
    def from_dict(cls, value: object) -> CashAccount:
        row = _record(value, {"id", "owner", "currency", "balance_minor"})
        return cls(
            _entity(row["id"]),
            _entity(row["owner"]),
            _text(row["currency"], "currency"),
            _integer(row["balance_minor"], "balance_minor"),
        )


@dataclass(frozen=True, slots=True)
class ShareHolding:
    id: EntityId
    company: EntityId
    owner: EntityId
    parts: int

    def __post_init__(self) -> None:
        _same_project(self.id, self.company, self.owner)
        if _integer(self.parts, "parts") > SHARE_PARTS:
            raise BusinessError("holding exceeds all issued shares")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id.to_dict(),
            "company": self.company.to_dict(),
            "owner": self.owner.to_dict(),
            "parts": self.parts,
        }

    @classmethod
    def from_dict(cls, value: object) -> ShareHolding:
        row = _record(value, {"id", "company", "owner", "parts"})
        return cls(
            _entity(row["id"]),
            _entity(row["company"]),
            _entity(row["owner"]),
            _integer(row["parts"], "parts"),
        )


@dataclass(frozen=True, slots=True)
class ResourceHolding:
    id: EntityId
    owner: EntityId
    resource: str
    unit: str
    quantity: int

    def __post_init__(self) -> None:
        _same_project(self.id, self.owner)
        _text(self.resource, "resource")
        _text(self.unit, "unit")
        _integer(self.quantity, "quantity")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id.to_dict(),
            "owner": self.owner.to_dict(),
            "resource": self.resource,
            "unit": self.unit,
            "quantity": self.quantity,
        }

    @classmethod
    def from_dict(cls, value: object) -> ResourceHolding:
        row = _record(value, {"id", "owner", "resource", "unit", "quantity"})
        return cls(
            _entity(row["id"]),
            _entity(row["owner"]),
            _text(row["resource"], "resource"),
            _text(row["unit"], "unit"),
            _integer(row["quantity"], "quantity"),
        )


BusinessItem = Company | CashAccount | ShareHolding | ResourceHolding
_FIELDS = {
    "company": frozenset({"total_parts"}),
    "account": frozenset({"owner", "currency", "balance_minor"}),
    "share": frozenset({"company", "owner", "parts"}),
    "resource": frozenset({"owner", "resource", "unit", "quantity"}),
}
_MUTABLE = {"account": "balance_minor", "share": "parts", "resource": "quantity"}
_REFERENCES = frozenset({"owner", "company"})
_PREFIX = "ext:" + BUSINESS_NAMESPACE + ":"


def _predicate(kind: str, field: str) -> str:
    return _PREFIX + kind + "." + field


def _fact_id(subject: EntityId, predicate: str) -> EntityId:
    digest = sha256(
        canonical_bytes({"subject": subject.to_dict(), "predicate": predicate})
    ).hexdigest()
    return EntityId(subject.project, "business-fact:" + digest)


@dataclass(frozen=True, slots=True)
class BusinessState:
    companies: tuple[Company, ...]
    accounts: tuple[CashAccount, ...]
    holdings: tuple[ShareHolding, ...]
    resources: tuple[ResourceHolding, ...]

    def __post_init__(self) -> None:
        for members, kind in (
            (self.companies, Company),
            (self.accounts, CashAccount),
            (self.holdings, ShareHolding),
            (self.resources, ResourceHolding),
        ):
            if type(members) is not tuple or any(
                type(item) is not kind for item in members
            ):
                raise BusinessError(
                    "business state requires immutable exact typed members"
                )
        items = self._items()
        if len({item.id for item in items}) != len(items):
            raise BusinessError("business object identities repeat")
        refs = self.referenced_ids
        if len({item.project for item in refs}) > 1:
            raise BusinessError("business state crosses project")
        company_ids = {item.id for item in self.companies}
        if any(item.company not in company_ids for item in self.holdings):
            raise BusinessError("shareholding refers to an undeclared company")
        for company in self.companies:
            if (
                sum(item.parts for item in self.holdings if item.company == company.id)
                != company.total_parts
            ):
                raise BusinessError("holdings do not equal all issued company shares")

    def _items(self) -> tuple[BusinessItem, ...]:
        return (*self.companies, *self.accounts, *self.holdings, *self.resources)

    @property
    def referenced_ids(self) -> frozenset[EntityId]:
        refs = {item.id for item in self._items()}
        for item in self._items():
            if isinstance(item, (CashAccount, ShareHolding, ResourceHolding)):
                refs.add(item.owner)
            if isinstance(item, ShareHolding):
                refs.add(item.company)
        return frozenset(refs)

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "URBAN_BUSINESS_STATE",
            "schema_version": BUSINESS_VERSION,
            "companies": [
                item.to_dict()
                for item in sorted(self.companies, key=lambda v: str(v.id))
            ],
            "accounts": [
                item.to_dict()
                for item in sorted(self.accounts, key=lambda v: str(v.id))
            ],
            "holdings": [
                item.to_dict()
                for item in sorted(self.holdings, key=lambda v: str(v.id))
            ],
            "resources": [
                item.to_dict()
                for item in sorted(self.resources, key=lambda v: str(v.id))
            ],
        }

    @classmethod
    def from_dict(cls, value: object) -> BusinessState:
        row = _record(
            value,
            {
                "kind",
                "schema_version",
                "companies",
                "accounts",
                "holdings",
                "resources",
            },
        )
        if (
            row["kind"] != "URBAN_BUSINESS_STATE"
            or row["schema_version"] != BUSINESS_VERSION
        ):
            raise BusinessError("unregistered business state format")
        return cls(
            tuple(Company.from_dict(v) for v in _array(row["companies"])),
            tuple(CashAccount.from_dict(v) for v in _array(row["accounts"])),
            tuple(ShareHolding.from_dict(v) for v in _array(row["holdings"])),
            tuple(ResourceHolding.from_dict(v) for v in _array(row["resources"])),
        )

    def to_facts(self, evidence_ref: str) -> tuple[WorldFact, ...]:
        _text(evidence_ref, "evidence reference")
        result: list[WorldFact] = []
        for kind, items in (
            ("company", self.companies),
            ("account", self.accounts),
            ("share", self.holdings),
            ("resource", self.resources),
        ):
            for item in items:
                row = item.to_dict()
                for field in sorted(_FIELDS[kind]):
                    value = row[field]
                    if field in _REFERENCES:
                        value = cast(dict[str, str], value)["local_id"]
                    predicate = _predicate(kind, field)
                    result.append(
                        WorldFact(
                            _fact_id(item.id, predicate),
                            Proposition(item.id, predicate, cast(Scalar, value)),
                            evidence_ref,
                        )
                    )
        return tuple(sorted(result, key=lambda fact: str(fact.id)))

    @classmethod
    def from_baseline(cls, baseline: FactBaseline) -> BusinessState:
        from anovel.genre.extensions.registration import registered_extensions

        if type(baseline) is not FactBaseline:
            raise BusinessError("a frozen fact baseline is required")
        if not any(
            binding.namespace == BUSINESS_NAMESPACE for binding in baseline.extensions
        ):
            raise BusinessError("a frozen registered business binding is required")
        registered_extensions().validate_baseline(baseline)
        return _decode(baseline.facts)


def _decode(facts: tuple[FactSnapshot, ...]) -> BusinessState:
    if type(facts) is not tuple or any(type(v) is not FactSnapshot for v in facts):
        raise BusinessError("business input must be exact immutable fact snapshots")
    records: dict[EntityId, tuple[str, dict[str, object]]] = {}
    ids: set[EntityId] = set()
    for snapshot in facts:
        seed = snapshot.seed_fact
        predicate = seed.proposition.predicate
        if not predicate.startswith(_PREFIX):
            continue
        tail = predicate[len(_PREFIX) :]
        kind, separator, field = tail.partition(".")
        if not separator or kind not in _FIELDS or field not in _FIELDS[kind]:
            raise BusinessError("unregistered business predicate")
        subject = seed.proposition.subject
        if seed.id != _fact_id(subject, predicate) or seed.id in ids:
            raise BusinessError("business fact identity is not canonical or repeats")
        ids.add(seed.id)
        if snapshot.state.status is not FactStatus.KNOWN:
            raise BusinessError("business quantities and metadata must remain KNOWN")
        value = snapshot.state.value
        if field == _MUTABLE.get(kind) or (kind, field) == ("company", "total_parts"):
            _integer(seed.proposition.value, "business seed quantity")
        if field != _MUTABLE.get(kind) and (
            type(value) is not type(seed.proposition.value)
            or value != seed.proposition.value
        ):
            raise BusinessError("business metadata is immutable")
        record_kind, row = records.setdefault(subject, (kind, {}))
        if record_kind != kind or field in row:
            raise BusinessError("business subject repeats a kind or field")
        row[field] = (
            _entity({"project": subject.project, "local_id": value}).to_dict()
            if field in _REFERENCES
            else value
        )
    companies: list[Company] = []
    accounts: list[CashAccount] = []
    holdings: list[ShareHolding] = []
    resources: list[ResourceHolding] = []
    for subject, (kind, row) in sorted(records.items(), key=lambda v: str(v[0])):
        if set(row) != _FIELDS[kind]:
            raise BusinessError("business object is missing a required field")
        record_value = {"id": subject.to_dict(), **row}
        if kind == "company":
            companies.append(Company.from_dict(record_value))
        elif kind == "account":
            accounts.append(CashAccount.from_dict(record_value))
        elif kind == "share":
            holdings.append(ShareHolding.from_dict(record_value))
        else:
            resources.append(ResourceHolding.from_dict(record_value))
    return BusinessState(
        tuple(companies), tuple(accounts), tuple(holdings), tuple(resources)
    )


def create_business_binding(
    binding: ProjectGenreBinding, entity_ids: tuple[EntityId, ...]
) -> ExtensionBinding:
    if type(binding) is not ProjectGenreBinding:
        raise BusinessError("an exact project GenrePack binding is required")
    result = ExtensionBinding(
        BUSINESS_NAMESPACE,
        BUSINESS_VERSION,
        BUSINESS_SCHEMA_ID,
        BUSINESS_SCHEMA_HASH,
        binding.ref.id,
        binding.ref.version,
        binding.ref.content_hash,
        canonical_bytes(binding.to_dict()),
        BUSINESS_SCHEMA_BYTES,
        entity_ids,
    )
    BusinessValidator().validate_binding(result, binding.project)
    return result


@dataclass(frozen=True, slots=True)
class BusinessValidator:
    namespace: ClassVar[str] = BUSINESS_NAMESPACE
    version: ClassVar[str] = BUSINESS_VERSION
    schema_id: ClassVar[str] = BUSINESS_SCHEMA_ID
    schema_hash: ClassVar[str] = BUSINESS_SCHEMA_HASH

    def validate_binding(self, binding: ExtensionBinding, project: str) -> None:
        if type(binding) is not ExtensionBinding or (
            binding.namespace,
            binding.version,
            binding.schema_id,
            binding.schema_hash,
        ) != (self.namespace, self.version, self.schema_id, self.schema_hash):
            raise BusinessError("binding does not match the compiled business contract")
        if (
            binding.pack_id,
            binding.pack_version,
            binding.pack_hash,
        ) != BUSINESS_PACK_IDENTITY:
            raise BusinessError("business extension requires its exact registered Pack")
        if binding.schema_bytes != BUSINESS_SCHEMA_BYTES:
            raise BusinessError(
                "business Schema bytes differ from the compiled contract"
            )
        try:
            restored = ProjectGenreBinding.from_dict(
                decode_canonical(binding.pack_bytes)
            )
        except ValueError as error:
            raise BusinessError("retained project Pack binding is invalid") from error
        if (
            restored.project != project
            or canonical_bytes(restored.to_dict()) != binding.pack_bytes
        ):
            raise BusinessError("retained Pack crosses scope or canonical identity")
        if (
            restored.ref.id,
            restored.ref.version,
            restored.ref.content_hash,
        ) != BUSINESS_PACK_IDENTITY:
            raise BusinessError("retained Pack identity differs from its declaration")
        expected = {
            "namespace": self.namespace,
            "version": self.version,
            "schema_id": self.schema_id,
            "schema_hash": self.schema_hash,
        }
        if tuple(item.to_dict() for item in restored.pack.extensions) != (expected,):
            raise BusinessError("retained Pack does not declare this exact extension")
        if any(item.project != project for item in binding.entity_ids):
            raise BusinessError("business entity registry crosses project")

    def validate_state(
        self, binding: ExtensionBinding, facts: tuple[FactSnapshot, ...]
    ) -> None:
        self.validate_binding(binding, binding.entity_ids[0].project)
        state = _decode(facts)
        if not state.referenced_ids <= frozenset(binding.entity_ids):
            raise BusinessError(
                "business object or reference is not registered in root"
            )
        if not state._items():
            raise BusinessError(
                "business binding requires actual registered business facts"
            )

    def validate_transition(
        self,
        binding: ExtensionBinding,
        before: tuple[FactSnapshot, ...],
        after: tuple[FactSnapshot, ...],
    ) -> None:
        self.validate_state(binding, before)
        self.validate_state(binding, after)
        first, last = _decode(before), _decode(after)
        if {v.seed_fact.id: v.seed_fact for v in before} != {
            v.seed_fact.id: v.seed_fact for v in after
        }:
            raise BusinessError("business transition changes registered fact identity")
        if _totals(first) != _totals(last):
            raise BusinessError("cash, shares and resources must be conserved per unit")


def _totals(state: BusinessState) -> dict[tuple[str, ...], int]:
    totals: dict[tuple[str, ...], int] = {}
    key: tuple[str, ...]
    for account in state.accounts:
        key = ("cash", account.currency)
        totals[key] = totals.get(key, 0) + account.balance_minor
    for holding in state.holdings:
        key = ("shares", str(holding.company))
        totals[key] = totals.get(key, 0) + holding.parts
    for resource in state.resources:
        key = ("resource", resource.resource, resource.unit)
        totals[key] = totals.get(key, 0) + resource.quantity
    return totals


def _transfer(
    baseline: FactBaseline,
    source: EntityId,
    target: EntityId,
    amount: int,
    *,
    kind: str,
    delta_id: EntityId,
    evidence: ProseEvidence,
    authorization_ref: str,
) -> NarrativeDelta:
    from anovel.genre.extensions.registration import registered_extensions

    registry = registered_extensions()
    registry.validate_baseline(baseline)
    _same_project(_id(source), _id(target), _id(delta_id))
    if source.project != baseline.project or source == target:
        raise BusinessError("transfer needs distinct subjects in the bound project")
    if _integer(amount, "transfer amount") == 0:
        raise BusinessError("transfer amount must be strictly positive")
    state = BusinessState.from_baseline(baseline)
    field = _MUTABLE[kind]
    members: (
        tuple[CashAccount, ...] | tuple[ShareHolding, ...] | tuple[ResourceHolding, ...]
    )
    if kind == "account":
        members = state.accounts
    elif kind == "share":
        members = state.holdings
    else:
        members = state.resources
    first = next((item for item in members if item.id == source), None)
    last = next((item for item in members if item.id == target), None)
    if first is None or last is None:
        raise BusinessError("transfer targets must be registered holdings of one type")
    if isinstance(first, CashAccount) and isinstance(last, CashAccount):
        compatible = first.currency == last.currency
        first_amount, last_amount = first.balance_minor, last.balance_minor
    elif isinstance(first, ShareHolding) and isinstance(last, ShareHolding):
        compatible = first.company == last.company
        first_amount, last_amount = first.parts, last.parts
    elif isinstance(first, ResourceHolding) and isinstance(last, ResourceHolding):
        compatible = (first.resource, first.unit) == (last.resource, last.unit)
        first_amount, last_amount = first.quantity, last.quantity
    else:
        raise BusinessError("transfer target types differ")
    if not compatible or first_amount < amount:
        raise BusinessError(
            "transfer units differ or source has insufficient resources"
        )
    operations = []
    for index, subject, value in (
        (0, source, first_amount - amount),
        (1, target, last_amount + amount),
    ):
        snapshot = baseline.get(_fact_id(subject, _predicate(kind, field)))
        if snapshot is None:
            raise BusinessError("transfer quantity fact is not registered")
        op_id = EntityId(
            delta_id.project,
            "business-op:"
            + sha256(
                canonical_bytes({"delta": delta_id.to_dict(), "index": index})
            ).hexdigest(),
        )
        operations.append(
            SetFact(
                OperationMeta(
                    op_id,
                    snapshot.seed_fact.id,
                    FactPath.VALUE,
                    Precondition.from_snapshot(snapshot),
                    evidence,
                    authorization_ref,
                ),
                value,
            )
        )
    delta = NarrativeDelta(
        delta_id,
        baseline.branch,
        baseline.parent_ref,
        evidence.source_id,
        tuple(operations),
    )
    preview_delta(
        baseline,
        delta,
        source_id=evidence.source_id,
        authorization_refs=frozenset({authorization_ref}),
        extension_registry=registry,
    )
    return delta


def transfer_cash(
    baseline: FactBaseline,
    source: EntityId,
    target: EntityId,
    amount: int,
    *,
    delta_id: EntityId,
    evidence: ProseEvidence,
    authorization_ref: str,
) -> NarrativeDelta:
    return _transfer(
        baseline,
        source,
        target,
        amount,
        kind="account",
        delta_id=delta_id,
        evidence=evidence,
        authorization_ref=authorization_ref,
    )


def transfer_shares(
    baseline: FactBaseline,
    source: EntityId,
    target: EntityId,
    amount: int,
    *,
    delta_id: EntityId,
    evidence: ProseEvidence,
    authorization_ref: str,
) -> NarrativeDelta:
    return _transfer(
        baseline,
        source,
        target,
        amount,
        kind="share",
        delta_id=delta_id,
        evidence=evidence,
        authorization_ref=authorization_ref,
    )


def transfer_resource(
    baseline: FactBaseline,
    source: EntityId,
    target: EntityId,
    amount: int,
    *,
    delta_id: EntityId,
    evidence: ProseEvidence,
    authorization_ref: str,
) -> NarrativeDelta:
    return _transfer(
        baseline,
        source,
        target,
        amount,
        kind="resource",
        delta_id=delta_id,
        evidence=evidence,
        authorization_ref=authorization_ref,
    )
