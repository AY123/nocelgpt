"""Registered progression facts, before-state prerequisites and exact costs.

Only structured registered facts are interpreted. Builders propose the existing
finite Delta; they do not write Canon, evaluate prose or issue a Permit.
"""

from __future__ import annotations

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
from anovel.genre.extensions.progression_contracts import (
    PROGRESSION_NAMESPACE,
    PROGRESSION_PACK_IDENTITY,
    PROGRESSION_SCHEMA_BYTES,
    PROGRESSION_SCHEMA_HASH,
    PROGRESSION_SCHEMA_ID,
    PROGRESSION_VERSION,
)
from anovel.genre.registry import ProjectGenreBinding


class ProgressionError(ExtensionValidationError):
    """Malformed state, unsupported registration or illegal progression."""


def _text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise ProgressionError(f"{field} must be nonempty text")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise ProgressionError(f"{field} must be valid Unicode") from error
    return value


def _integer(value: object, field: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise ProgressionError(
            f"{field} must be a strict {'positive' if positive else 'nonnegative'} integer"
        )
    return value


def _id(value: object) -> EntityId:
    if type(value) is not EntityId:
        raise ProgressionError("an exact EntityId is required")
    return value


def _same_project(*values: EntityId) -> None:
    if len({_id(value).project for value in values}) != 1:
        raise ProgressionError("progression references cross project")


def _record(value: object, keys: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise ProgressionError("progression fields must be exact and closed")
    return cast(dict[str, object], value)


def _entity(value: object) -> EntityId:
    row = _record(value, {"project", "local_id"})
    return EntityId(
        _text(row["project"], "project"), _text(row["local_id"], "local ID")
    )


def _array(value: object) -> list[object]:
    if type(value) is not list:
        raise ProgressionError("progression members must be arrays")
    return cast(list[object], value)


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        raise ProgressionError("learned must be a strict boolean")
    return value


@dataclass(frozen=True, slots=True)
class RealmDefinition:
    id: EntityId
    rank: int
    resource: str
    unit: str
    breakthrough_cost: int

    def __post_init__(self) -> None:
        _id(self.id)
        _integer(self.rank, "rank")
        _text(self.resource, "resource")
        _text(self.unit, "unit")
        _integer(self.breakthrough_cost, "breakthrough_cost")
        if (self.rank == 0) != (self.breakthrough_cost == 0):
            raise ProgressionError(
                "rank zero costs zero; higher realms have positive cost"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id.to_dict(),
            "rank": self.rank,
            "resource": self.resource,
            "unit": self.unit,
            "breakthrough_cost": self.breakthrough_cost,
        }

    @classmethod
    def from_dict(cls, value: object) -> RealmDefinition:
        row = _record(value, {"id", "rank", "resource", "unit", "breakthrough_cost"})
        return cls(
            _entity(row["id"]),
            _integer(row["rank"], "rank"),
            _text(row["resource"], "resource"),
            _text(row["unit"], "unit"),
            _integer(row["breakthrough_cost"], "breakthrough_cost"),
        )


@dataclass(frozen=True, slots=True)
class Cultivator:
    id: EntityId
    realm: EntityId

    def __post_init__(self) -> None:
        _same_project(self.id, self.realm)

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id.to_dict(), "realm": self.realm.to_dict()}

    @classmethod
    def from_dict(cls, value: object) -> Cultivator:
        row = _record(value, {"id", "realm"})
        return cls(_entity(row["id"]), _entity(row["realm"]))


@dataclass(frozen=True, slots=True)
class AbilityDefinition:
    id: EntityId
    minimum_realm: EntityId
    resource: str
    unit: str
    learning_cost: int
    use_cost: int

    def __post_init__(self) -> None:
        _same_project(self.id, self.minimum_realm)
        _text(self.resource, "resource")
        _text(self.unit, "unit")
        _integer(self.learning_cost, "learning_cost", positive=True)
        _integer(self.use_cost, "use_cost", positive=True)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id.to_dict(),
            "minimum_realm": self.minimum_realm.to_dict(),
            "resource": self.resource,
            "unit": self.unit,
            "learning_cost": self.learning_cost,
            "use_cost": self.use_cost,
        }

    @classmethod
    def from_dict(cls, value: object) -> AbilityDefinition:
        row = _record(
            value,
            {"id", "minimum_realm", "resource", "unit", "learning_cost", "use_cost"},
        )
        return cls(
            _entity(row["id"]),
            _entity(row["minimum_realm"]),
            _text(row["resource"], "resource"),
            _text(row["unit"], "unit"),
            _integer(row["learning_cost"], "learning_cost", positive=True),
            _integer(row["use_cost"], "use_cost", positive=True),
        )


@dataclass(frozen=True, slots=True)
class AbilityState:
    id: EntityId
    owner: EntityId
    ability: EntityId
    learned: bool
    uses: int

    def __post_init__(self) -> None:
        _same_project(self.id, self.owner, self.ability)
        _boolean(self.learned)
        _integer(self.uses, "uses")
        if not self.learned and self.uses:
            raise ProgressionError("an unlearned ability cannot have uses")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id.to_dict(),
            "owner": self.owner.to_dict(),
            "ability": self.ability.to_dict(),
            "learned": self.learned,
            "uses": self.uses,
        }

    @classmethod
    def from_dict(cls, value: object) -> AbilityState:
        row = _record(value, {"id", "owner", "ability", "learned", "uses"})
        return cls(
            _entity(row["id"]),
            _entity(row["owner"]),
            _entity(row["ability"]),
            _boolean(row["learned"]),
            _integer(row["uses"], "uses"),
        )


@dataclass(frozen=True, slots=True)
class ProgressionResource:
    id: EntityId
    owner: EntityId
    resource: str
    unit: str
    quantity: int
    spent: int

    def __post_init__(self) -> None:
        _same_project(self.id, self.owner)
        _text(self.resource, "resource")
        _text(self.unit, "unit")
        _integer(self.quantity, "quantity")
        _integer(self.spent, "spent")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id.to_dict(),
            "owner": self.owner.to_dict(),
            "resource": self.resource,
            "unit": self.unit,
            "quantity": self.quantity,
            "spent": self.spent,
        }

    @classmethod
    def from_dict(cls, value: object) -> ProgressionResource:
        row = _record(value, {"id", "owner", "resource", "unit", "quantity", "spent"})
        return cls(
            _entity(row["id"]),
            _entity(row["owner"]),
            _text(row["resource"], "resource"),
            _text(row["unit"], "unit"),
            _integer(row["quantity"], "quantity"),
            _integer(row["spent"], "spent"),
        )


ProgressionItem = (
    RealmDefinition
    | Cultivator
    | AbilityDefinition
    | AbilityState
    | ProgressionResource
)
_FIELDS = {
    "realm": {"rank", "resource", "unit", "breakthrough_cost"},
    "cultivator": {"realm"},
    "ability": {"minimum_realm", "resource", "unit", "learning_cost", "use_cost"},
    "ability_state": {"owner", "ability", "learned", "uses"},
    "resource": {"owner", "resource", "unit", "quantity", "spent"},
}
_MUTABLE = {
    ("cultivator", "realm"),
    ("ability_state", "learned"),
    ("ability_state", "uses"),
    ("resource", "quantity"),
    ("resource", "spent"),
}
_REFERENCES = {"realm", "minimum_realm", "owner", "ability"}
_PREFIX = "ext:" + PROGRESSION_NAMESPACE + ":"


def _predicate(kind: str, field: str) -> str:
    return _PREFIX + kind + "." + field


def _fact_id(subject: EntityId, predicate: str) -> EntityId:
    digest = sha256(
        canonical_bytes({"subject": subject.to_dict(), "predicate": predicate})
    ).hexdigest()
    return EntityId(subject.project, "progression-fact:" + digest)


@dataclass(frozen=True, slots=True)
class ProgressionState:
    realms: tuple[RealmDefinition, ...]
    cultivators: tuple[Cultivator, ...]
    abilities: tuple[AbilityDefinition, ...]
    ability_states: tuple[AbilityState, ...]
    resources: tuple[ProgressionResource, ...]

    def __post_init__(self) -> None:
        for values, kind in (
            (self.realms, RealmDefinition),
            (self.cultivators, Cultivator),
            (self.abilities, AbilityDefinition),
            (self.ability_states, AbilityState),
            (self.resources, ProgressionResource),
        ):
            if type(values) is not tuple or any(
                type(value) is not kind for value in values
            ):
                raise ProgressionError(
                    "state requires exact immutable registered members"
                )
        if not self.realms or not self.cultivators or not self.resources:
            raise ProgressionError(
                "state requires realms, cultivators and resource pools"
            )
        if len({v.id for v in self._items()}) != len(self._items()):
            raise ProgressionError("progression object identities repeat")
        if len({v.project for v in self.referenced_ids}) != 1:
            raise ProgressionError("progression state crosses project")
        if sorted(v.rank for v in self.realms) != list(range(len(self.realms))):
            raise ProgressionError(
                "realm ranks must be unique and consecutive from zero"
            )
        realms = {v.id: v for v in self.realms}
        cultivators = {v.id: v for v in self.cultivators}
        abilities = {v.id: v for v in self.abilities}
        if any(v.realm not in realms for v in self.cultivators) or any(
            v.minimum_realm not in realms for v in self.abilities
        ):
            raise ProgressionError("realm reference has no registered definition")
        for ability in self.ability_states:
            if ability.owner not in cultivators or ability.ability not in abilities:
                raise ProgressionError(
                    "ability needs a registered cultivator and definition"
                )
            if (
                ability.learned
                and realms[cultivators[ability.owner].realm].rank
                < realms[abilities[ability.ability].minimum_realm].rank
            ):
                raise ProgressionError("learned ability requires its minimum realm")
        if len({(v.owner, v.ability) for v in self.ability_states}) != len(
            self.ability_states
        ):
            raise ProgressionError("an actor can have only one state per ability")
        if len({(v.owner, v.resource, v.unit) for v in self.resources}) != len(
            self.resources
        ):
            raise ProgressionError(
                "an owner can have only one pool per resource and unit"
            )

    def _groups(self) -> tuple[tuple[str, tuple[ProgressionItem, ...]], ...]:
        return (
            ("realm", self.realms),
            ("cultivator", self.cultivators),
            ("ability", self.abilities),
            ("ability_state", self.ability_states),
            ("resource", self.resources),
        )

    def _items(self) -> tuple[ProgressionItem, ...]:
        return (
            *self.realms,
            *self.cultivators,
            *self.abilities,
            *self.ability_states,
            *self.resources,
        )

    @property
    def referenced_ids(self) -> frozenset[EntityId]:
        result = {v.id for v in self._items()}
        result.update(v.realm for v in self.cultivators)
        result.update(v.minimum_realm for v in self.abilities)
        result.update(v.owner for v in self.ability_states)
        result.update(v.owner for v in self.resources)
        result.update(v.ability for v in self.ability_states)
        return frozenset(result)

    def to_dict(self) -> dict[str, object]:
        names = {
            "realm": "realms",
            "cultivator": "cultivators",
            "ability": "abilities",
            "ability_state": "ability_states",
            "resource": "resources",
        }
        return {
            "kind": "EASTERN_PROGRESSION_STATE",
            "schema_version": PROGRESSION_VERSION,
            **{
                names[kind]: [
                    v.to_dict() for v in sorted(values, key=lambda v: str(v.id))
                ]
                for kind, values in self._groups()
            },
        }

    @classmethod
    def from_dict(cls, value: object) -> ProgressionState:
        row = _record(
            value,
            {
                "kind",
                "schema_version",
                "realms",
                "cultivators",
                "abilities",
                "ability_states",
                "resources",
            },
        )
        if (
            row["kind"] != "EASTERN_PROGRESSION_STATE"
            or row["schema_version"] != PROGRESSION_VERSION
        ):
            raise ProgressionError("unsupported progression state format")
        return cls(
            tuple(RealmDefinition.from_dict(v) for v in _array(row["realms"])),
            tuple(Cultivator.from_dict(v) for v in _array(row["cultivators"])),
            tuple(AbilityDefinition.from_dict(v) for v in _array(row["abilities"])),
            tuple(AbilityState.from_dict(v) for v in _array(row["ability_states"])),
            tuple(ProgressionResource.from_dict(v) for v in _array(row["resources"])),
        )

    def to_facts(self, evidence_ref: str) -> tuple[WorldFact, ...]:
        _text(evidence_ref, "evidence reference")
        result = []
        for kind, values in self._groups():
            for item in values:
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
        return tuple(sorted(result, key=lambda v: str(v.id)))

    @classmethod
    def from_baseline(cls, baseline: FactBaseline) -> ProgressionState:
        from anovel.genre.extensions.registration import registered_extensions

        if type(baseline) is not FactBaseline or not any(
            v.namespace == PROGRESSION_NAMESPACE for v in baseline.extensions
        ):
            raise ProgressionError(
                "a frozen registered progression baseline is required"
            )
        registered_extensions().validate_baseline(baseline)
        return _decode(baseline.facts)


def _decode(facts: tuple[FactSnapshot, ...]) -> ProgressionState:
    if type(facts) is not tuple or any(type(v) is not FactSnapshot for v in facts):
        raise ProgressionError("progression needs exact immutable fact snapshots")
    rows: dict[EntityId, tuple[str, dict[str, object]]] = {}
    ids: set[EntityId] = set()
    for snapshot in facts:
        seed = snapshot.seed_fact
        predicate = seed.proposition.predicate
        if not predicate.startswith(_PREFIX):
            continue
        kind, separator, field = predicate[len(_PREFIX) :].partition(".")
        if not separator or kind not in _FIELDS or field not in _FIELDS[kind]:
            raise ProgressionError("unregistered progression predicate")
        subject = seed.proposition.subject
        if seed.id != _fact_id(subject, predicate) or seed.id in ids:
            raise ProgressionError(
                "progression fact identity is not canonical or repeats"
            )
        ids.add(seed.id)
        if snapshot.state.status is not FactStatus.KNOWN:
            raise ProgressionError("progression fields must remain KNOWN")
        value = snapshot.state.value
        if (kind, field) not in _MUTABLE and (
            type(value) is not type(seed.proposition.value)
            or value != seed.proposition.value
        ):
            raise ProgressionError("progression definitions and metadata are immutable")
        original_kind, row = rows.setdefault(subject, (kind, {}))
        if original_kind != kind or field in row:
            raise ProgressionError("progression subject repeats a kind or field")
        row[field] = (
            _entity({"project": subject.project, "local_id": value}).to_dict()
            if field in _REFERENCES
            else value
        )
    state: dict[str, object] = {
        "kind": "EASTERN_PROGRESSION_STATE",
        "schema_version": PROGRESSION_VERSION,
        "realms": [],
        "cultivators": [],
        "abilities": [],
        "ability_states": [],
        "resources": [],
    }
    names = {
        "realm": "realms",
        "cultivator": "cultivators",
        "ability": "abilities",
        "ability_state": "ability_states",
        "resource": "resources",
    }
    for subject, (kind, row) in sorted(rows.items(), key=lambda v: str(v[0])):
        if set(row) != _FIELDS[kind]:
            raise ProgressionError("progression object is missing required fields")
        cast(list[object], state[names[kind]]).append({"id": subject.to_dict(), **row})
    return ProgressionState.from_dict(state)


def create_progression_binding(
    binding: ProjectGenreBinding, entity_ids: tuple[EntityId, ...]
) -> ExtensionBinding:
    if type(binding) is not ProjectGenreBinding:
        raise ProgressionError("an exact project GenrePack binding is required")
    result = ExtensionBinding(
        PROGRESSION_NAMESPACE,
        PROGRESSION_VERSION,
        PROGRESSION_SCHEMA_ID,
        PROGRESSION_SCHEMA_HASH,
        binding.ref.id,
        binding.ref.version,
        binding.ref.content_hash,
        canonical_bytes(binding.to_dict()),
        PROGRESSION_SCHEMA_BYTES,
        entity_ids,
    )
    ProgressionValidator().validate_binding(result, binding.project)
    return result


def _pool_key(resource: ProgressionResource) -> tuple[EntityId, str, str]:
    return resource.owner, resource.resource, resource.unit


def _totals(state: ProgressionState) -> dict[tuple[str, str], int]:
    totals: dict[tuple[str, str], int] = {}
    for resource in state.resources:
        key = resource.resource, resource.unit
        totals[key] = totals.get(key, 0) + resource.quantity + resource.spent
    return totals


def _costs(
    before: ProgressionState, after: ProgressionState
) -> dict[tuple[EntityId, str, str], int]:
    costs: dict[tuple[EntityId, str, str], int] = {}
    realms = {v.id: v for v in before.realms}
    actors = {v.id: v for v in before.cultivators}
    abilities = {v.id: v for v in before.abilities}
    states = {v.id: v for v in before.ability_states}

    def charge(owner: EntityId, resource: str, unit: str, amount: int) -> None:
        key = owner, resource, unit
        costs[key] = costs.get(key, 0) + amount

    for actor in after.cultivators:
        prior_actor = actors[actor.id]
        if actor.realm == prior_actor.realm:
            continue
        target = realms[actor.realm]
        if target.rank != realms[prior_actor.realm].rank + 1:
            raise ProgressionError("realm change must be exactly one forward rank")
        charge(actor.id, target.resource, target.unit, target.breakthrough_cost)
    for last in after.ability_states:
        first = states[last.id]
        definition = abilities[first.ability]
        rank = realms[actors[first.owner].realm].rank
        minimum = realms[definition.minimum_realm].rank
        if first.learned and not last.learned:
            raise ProgressionError("learning cannot be undone or refunded")
        if not first.learned and last.learned:
            if rank < minimum:
                raise ProgressionError(
                    "learning requires the minimum before-state realm"
                )
            charge(
                first.owner,
                definition.resource,
                definition.unit,
                definition.learning_cost,
            )
        if last.uses < first.uses:
            raise ProgressionError("ability uses cannot decrease")
        if last.uses != first.uses:
            if not first.learned or rank < minimum:
                raise ProgressionError(
                    "use requires before-state learned ability and realm"
                )
            charge(
                first.owner,
                definition.resource,
                definition.unit,
                (last.uses - first.uses) * definition.use_cost,
            )
    return costs


@dataclass(frozen=True, slots=True)
class ProgressionValidator:
    namespace: ClassVar[str] = PROGRESSION_NAMESPACE
    version: ClassVar[str] = PROGRESSION_VERSION
    schema_id: ClassVar[str] = PROGRESSION_SCHEMA_ID
    schema_hash: ClassVar[str] = PROGRESSION_SCHEMA_HASH

    def validate_binding(self, binding: ExtensionBinding, project: str) -> None:
        if type(binding) is not ExtensionBinding or (
            binding.namespace,
            binding.version,
            binding.schema_id,
            binding.schema_hash,
        ) != (self.namespace, self.version, self.schema_id, self.schema_hash):
            raise ProgressionError(
                "binding differs from the compiled progression contract"
            )
        if (
            (binding.pack_id, binding.pack_version, binding.pack_hash)
            != PROGRESSION_PACK_IDENTITY
            or binding.schema_bytes != PROGRESSION_SCHEMA_BYTES
        ):
            raise ProgressionError(
                "progression requires the exact registered Pack and Schema"
            )
        try:
            restored = ProjectGenreBinding.from_dict(
                decode_canonical(binding.pack_bytes)
            )
        except ValueError as error:
            raise ProgressionError(
                "retained project Pack binding is invalid"
            ) from error
        if (
            restored.project != project
            or canonical_bytes(restored.to_dict()) != binding.pack_bytes
            or (restored.ref.id, restored.ref.version, restored.ref.content_hash)
            != PROGRESSION_PACK_IDENTITY
        ):
            raise ProgressionError(
                "retained Pack differs from frozen scope or identity"
            )
        expected = {
            "namespace": self.namespace,
            "version": self.version,
            "schema_id": self.schema_id,
            "schema_hash": self.schema_hash,
        }
        if tuple(v.to_dict() for v in restored.pack.extensions) != (expected,):
            raise ProgressionError("retained Pack must declare exactly this extension")
        if any(v.project != project for v in binding.entity_ids):
            raise ProgressionError("progression entity registry crosses project")

    def validate_state(
        self, binding: ExtensionBinding, facts: tuple[FactSnapshot, ...]
    ) -> None:
        self.validate_binding(binding, binding.entity_ids[0].project)
        state = _decode(facts)
        seed = _decode(tuple(FactSnapshot(v.seed_fact) for v in facts))
        if not state.referenced_ids <= frozenset(
            binding.entity_ids
        ) or not seed.referenced_ids <= frozenset(binding.entity_ids):
            raise ProgressionError(
                "progression references must belong to root registry"
            )

    def validate_transition(
        self,
        binding: ExtensionBinding,
        before: tuple[FactSnapshot, ...],
        after: tuple[FactSnapshot, ...],
    ) -> None:
        self.validate_state(binding, before)
        self.validate_state(binding, after)
        if {v.seed_fact.id: v.seed_fact for v in before} != {
            v.seed_fact.id: v.seed_fact for v in after
        }:
            raise ProgressionError(
                "progression transition changed registered fact identity"
            )
        first, last = _decode(before), _decode(after)
        costs = _costs(first, last)
        pools = {_pool_key(v): v for v in first.resources}
        if any(
            key not in pools or pools[key].quantity < amount
            for key, amount in costs.items()
        ):
            raise ProgressionError(
                "action requires sufficient resources in its owner's before-state pool"
            )
        for resource in last.resources:
            key = _pool_key(resource)
            if resource.spent - pools[key].spent != costs.get(key, 0):
                raise ProgressionError(
                    "spent increment must equal this owner's exact registered action costs"
                )
        if _totals(first) != _totals(last):
            raise ProgressionError(
                "resource quantity plus spent must be conserved per explicit unit"
            )


def _propose(
    baseline: FactBaseline,
    updates: tuple[tuple[EntityId, str, str, Scalar], ...],
    *,
    delta_id: EntityId,
    evidence: ProseEvidence,
    authorization_ref: str,
) -> NarrativeDelta:
    from anovel.genre.extensions.registration import registered_extensions

    registry = registered_extensions()
    registry.validate_baseline(baseline)
    if _id(delta_id).project != baseline.project:
        raise ProgressionError("delta identity crosses project")
    operations = []
    for index, (subject, kind, field, value) in enumerate(updates):
        if _id(subject).project != baseline.project:
            raise ProgressionError("target crosses project")
        snapshot = baseline.get(_fact_id(subject, _predicate(kind, field)))
        if snapshot is None:
            raise ProgressionError("target fact is not registered in baseline")
        op_id = EntityId(
            delta_id.project,
            "progression-op:"
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


def _payment(
    state: ProgressionState, owner: EntityId, resource: str, unit: str, cost: int
) -> tuple[tuple[EntityId, str, str, Scalar], ...]:
    pool = next(
        (v for v in state.resources if _pool_key(v) == (owner, resource, unit)), None
    )
    if pool is None or pool.quantity < cost:
        raise ProgressionError("owner has no sufficient registered resource pool")
    return (
        (pool.id, "resource", "quantity", pool.quantity - cost),
        (pool.id, "resource", "spent", pool.spent + cost),
    )


def advance_realm(
    baseline: FactBaseline,
    actor: EntityId,
    *,
    delta_id: EntityId,
    evidence: ProseEvidence,
    authorization_ref: str,
) -> NarrativeDelta:
    state = ProgressionState.from_baseline(baseline)
    cultivator = next((v for v in state.cultivators if v.id == _id(actor)), None)
    if cultivator is None:
        raise ProgressionError("actor is not a registered cultivator")
    current = next(v for v in state.realms if v.id == cultivator.realm)
    target = next((v for v in state.realms if v.rank == current.rank + 1), None)
    if target is None:
        raise ProgressionError("no next registered realm")
    updates = (
        (actor, "cultivator", "realm", target.id.local_id),
        *_payment(state, actor, target.resource, target.unit, target.breakthrough_cost),
    )
    return _propose(
        baseline,
        updates,
        delta_id=delta_id,
        evidence=evidence,
        authorization_ref=authorization_ref,
    )


def _ability_action(
    baseline: FactBaseline,
    ability_state_id: EntityId,
    *,
    learning: bool,
    delta_id: EntityId,
    evidence: ProseEvidence,
    authorization_ref: str,
) -> NarrativeDelta:
    state = ProgressionState.from_baseline(baseline)
    member = next(
        (v for v in state.ability_states if v.id == _id(ability_state_id)), None
    )
    if member is None:
        raise ProgressionError("ability state is not registered")
    if (learning and member.learned) or (not learning and not member.learned):
        raise ProgressionError(
            "ability must be unlearned for learning and learned for use"
        )
    definition = next(v for v in state.abilities if v.id == member.ability)
    field, value, cost = (
        ("learned", True, definition.learning_cost)
        if learning
        else ("uses", member.uses + 1, definition.use_cost)
    )
    updates = (
        (member.id, "ability_state", field, value),
        *_payment(state, member.owner, definition.resource, definition.unit, cost),
    )
    return _propose(
        baseline,
        updates,
        delta_id=delta_id,
        evidence=evidence,
        authorization_ref=authorization_ref,
    )


def learn_ability(
    baseline: FactBaseline,
    ability_state_id: EntityId,
    *,
    delta_id: EntityId,
    evidence: ProseEvidence,
    authorization_ref: str,
) -> NarrativeDelta:
    return _ability_action(
        baseline,
        ability_state_id,
        learning=True,
        delta_id=delta_id,
        evidence=evidence,
        authorization_ref=authorization_ref,
    )


def use_ability(
    baseline: FactBaseline,
    ability_state_id: EntityId,
    *,
    delta_id: EntityId,
    evidence: ProseEvidence,
    authorization_ref: str,
) -> NarrativeDelta:
    return _ability_action(
        baseline,
        ability_state_id,
        learning=False,
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
    state = ProgressionState.from_baseline(baseline)
    _same_project(source, target)
    _integer(amount, "transfer amount", positive=True)
    first = next((v for v in state.resources if v.id == source), None)
    last = next((v for v in state.resources if v.id == target), None)
    if (
        first is None
        or last is None
        or source == target
        or (first.resource, first.unit) != (last.resource, last.unit)
        or first.quantity < amount
    ):
        raise ProgressionError(
            "transfer needs distinct compatible pools and sufficient source quantity"
        )
    return _propose(
        baseline,
        (
            (source, "resource", "quantity", first.quantity - amount),
            (target, "resource", "quantity", last.quantity + amount),
        ),
        delta_id=delta_id,
        evidence=evidence,
        authorization_ref=authorization_ref,
    )
