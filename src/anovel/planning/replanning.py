"""Finite input-change diagnosis and unapplied future-plan proposals."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from anovel.canon.identity import canonical_bytes
from anovel.domain.identity import EntityId
from anovel.planning.models import (
    PlanningError,
    SeriesVision,
    _array,
    _data,
    _digest,
    _ids,
    _record,
    _scope,
    _text,
    _Value,
)
from anovel.planning.versions import PlanHistory, PlanVersion, _validate_revision


@dataclass(frozen=True, slots=True)
class InputIdentity(_Value):
    parent_ref: str
    canon_hash: str
    pack_hash: str
    knowledge_hash: str
    plan_hash: str
    continuity_hash: str

    def __post_init__(self) -> None:
        if type(self.parent_ref) is not str or not self.parent_ref.startswith(
            "sha256:"
        ):
            raise PlanningError("input identity requires a Canon parent")
        _digest(self.parent_ref[7:])
        for value in (
            self.canon_hash,
            self.pack_hash,
            self.knowledge_hash,
            self.plan_hash,
            self.continuity_hash,
        ):
            _digest(value)

    def to_dict(self) -> dict[str, object]:
        return _data(
            "PLANNING_INPUT_IDENTITY",
            {
                "parent_ref": self.parent_ref,
                "canon_hash": self.canon_hash,
                "pack_hash": self.pack_hash,
                "knowledge_hash": self.knowledge_hash,
                "plan_hash": self.plan_hash,
                "continuity_hash": self.continuity_hash,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> InputIdentity:
        row = _record(
            value,
            "PLANNING_INPUT_IDENTITY",
            {
                "parent_ref",
                "canon_hash",
                "pack_hash",
                "knowledge_hash",
                "plan_hash",
                "continuity_hash",
            },
        )
        return cls(
            *(
                _text(row[k], k)
                for k in (
                    "parent_ref",
                    "canon_hash",
                    "pack_hash",
                    "knowledge_hash",
                    "plan_hash",
                    "continuity_hash",
                )
            )
        )


@dataclass(frozen=True, slots=True)
class Invalidation(_Value):
    changed_inputs: tuple[str, ...]
    affected_chapter_ids: tuple[EntityId, ...]
    reusable_chapter_ids: tuple[EntityId, ...]
    requires_recompile: bool

    def __post_init__(self) -> None:
        if (
            type(self.changed_inputs) is not tuple
            or any(type(v) is not str for v in self.changed_inputs)
            or len(set(self.changed_inputs)) != len(self.changed_inputs)
            or any(
                v
                not in {
                    "parent_ref",
                    "canon_hash",
                    "pack_hash",
                    "knowledge_hash",
                    "plan_hash",
                    "continuity_hash",
                }
                for v in self.changed_inputs
            )
        ):
            raise PlanningError("unregistered input invalidation reason")
        _ids(self.affected_chapter_ids, "affected chapters")
        _ids(self.reusable_chapter_ids, "reusable chapters")
        if set(self.affected_chapter_ids) & set(self.reusable_chapter_ids):
            raise PlanningError("affected and reusable chapters overlap")
        if type(self.requires_recompile) is not bool or self.requires_recompile != bool(
            self.changed_inputs
        ):
            raise PlanningError("recompile flag differs from observed input changes")

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.changed_inputs

    def to_dict(self) -> dict[str, object]:
        return _data(
            "PLAN_INVALIDATION",
            {
                "changed_inputs": list(self.changed_inputs),
                "affected_chapter_ids": [
                    v.to_dict() for v in self.affected_chapter_ids
                ],
                "reusable_chapter_ids": [
                    v.to_dict() for v in self.reusable_chapter_ids
                ],
                "requires_recompile": self.requires_recompile,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> Invalidation:
        row = _record(
            value,
            "PLAN_INVALIDATION",
            {
                "changed_inputs",
                "affected_chapter_ids",
                "reusable_chapter_ids",
                "requires_recompile",
            },
        )
        if type(row["requires_recompile"]) is not bool:
            raise PlanningError("recompile flag must be a boolean")
        return cls(
            tuple(_text(v, "input reason") for v in _array(row["changed_inputs"])),
            tuple(EntityId.from_dict(v) for v in _array(row["affected_chapter_ids"])),
            tuple(EntityId.from_dict(v) for v in _array(row["reusable_chapter_ids"])),
            row["requires_recompile"],
        )


@dataclass(frozen=True, slots=True)
class PlanDiff(_Value):
    base_hash: str
    new_hash: str
    changed_chapter_ids: tuple[EntityId, ...]
    added_chapter_ids: tuple[EntityId, ...]
    removed_chapter_ids: tuple[EntityId, ...]
    reusable_chapter_ids: tuple[EntityId, ...]

    def __post_init__(self) -> None:
        _digest(self.base_hash)
        _digest(self.new_hash)
        ids: list[EntityId] = []
        for value in (
            self.changed_chapter_ids,
            self.added_chapter_ids,
            self.removed_chapter_ids,
            self.reusable_chapter_ids,
        ):
            ids += list(_ids(value, "chapter diff"))
        if len(set(ids)) != len(ids) or len({v.project for v in ids}) > 1:
            raise PlanningError("plan diff categories overlap or cross project")

    @property
    def affected_chapter_ids(self) -> tuple[EntityId, ...]:
        return tuple(
            sorted(
                (
                    *self.changed_chapter_ids,
                    *self.added_chapter_ids,
                    *self.removed_chapter_ids,
                ),
                key=str,
            )
        )

    def to_dict(self) -> dict[str, object]:
        return _data(
            "PLAN_DIFF",
            {
                "base_hash": self.base_hash,
                "new_hash": self.new_hash,
                "changed_chapter_ids": [v.to_dict() for v in self.changed_chapter_ids],
                "added_chapter_ids": [v.to_dict() for v in self.added_chapter_ids],
                "removed_chapter_ids": [v.to_dict() for v in self.removed_chapter_ids],
                "reusable_chapter_ids": [
                    v.to_dict() for v in self.reusable_chapter_ids
                ],
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> PlanDiff:
        row = _record(
            value,
            "PLAN_DIFF",
            {
                "base_hash",
                "new_hash",
                "changed_chapter_ids",
                "added_chapter_ids",
                "removed_chapter_ids",
                "reusable_chapter_ids",
            },
        )
        return cls(
            _digest(row["base_hash"]),
            _digest(row["new_hash"]),
            *(
                tuple(EntityId.from_dict(v) for v in _array(row[k]))
                for k in (
                    "changed_chapter_ids",
                    "added_chapter_ids",
                    "removed_chapter_ids",
                    "reusable_chapter_ids",
                )
            ),
        )


def diff_plans(before: PlanVersion, after: PlanVersion) -> PlanDiff:
    if (
        type(before) is not PlanVersion
        or type(after) is not PlanVersion
        or before.id != after.id
        or before.vision.id != after.vision.id
    ):
        raise PlanningError("plan diff requires the same plan and vision identity")

    def inputs(version: PlanVersion) -> dict[EntityId, str]:
        # Global and enclosing-arc intentions are inputs too. An unchanged
        # chapter body alone cannot prove reuse after its meaning has changed.
        return {
            chapter.id: sha256(
                canonical_bytes(
                    {
                        "vision_id": version.vision.id.to_dict(),
                        "premise": version.vision.premise,
                        "protagonist_goal": version.vision.protagonist_goal,
                        "arc_id": arc.id.to_dict(),
                        "arc_purpose": arc.purpose,
                        "chapter": chapter.to_dict(),
                    }
                )
            ).hexdigest()
            for arc in version.vision.arcs
            for chapter in arc.chapters
        }

    first, last = inputs(before), inputs(after)
    common = set(first) & set(last)
    return PlanDiff(
        before.content_hash,
        after.content_hash,
        tuple(sorted((v for v in common if first[v] != last[v]), key=str)),
        tuple(sorted(set(last) - set(first), key=str)),
        tuple(sorted(set(first) - set(last), key=str)),
        tuple(sorted((v for v in common if first[v] == last[v]), key=str)),
    )


@dataclass(frozen=True, slots=True)
class ReplanProposal(_Value):
    base_hash: str
    version: PlanVersion
    affected_chapter_ids: tuple[EntityId, ...]
    reason: str

    def __post_init__(self) -> None:
        _digest(self.base_hash)
        if (
            type(self.version) is not PlanVersion
            or self.version.parent_hash != self.base_hash
        ):
            raise PlanningError("proposal must extend its declared base version")
        _ids(self.affected_chapter_ids, "proposal chapters")
        _scope(self.version.project, self.affected_chapter_ids)
        _text(self.reason, "replan reason")

    def to_dict(self) -> dict[str, object]:
        return _data(
            "REPLAN_PROPOSAL",
            {
                "base_hash": self.base_hash,
                "version": self.version.to_dict(),
                "affected_chapter_ids": [
                    v.to_dict() for v in self.affected_chapter_ids
                ],
                "reason": self.reason,
            },
        )

    @classmethod
    def from_dict(cls, value: object) -> ReplanProposal:
        row = _record(
            value,
            "REPLAN_PROPOSAL",
            {"base_hash", "version", "affected_chapter_ids", "reason"},
        )
        return cls(
            _digest(row["base_hash"]),
            PlanVersion.from_dict(row["version"]),
            tuple(EntityId.from_dict(v) for v in _array(row["affected_chapter_ids"])),
            _text(row["reason"], "reason"),
        )


def propose_revision(
    history: PlanHistory,
    vision: SeriesVision,
    *,
    reason: str,
    fixture_hash: str | None = None,
) -> ReplanProposal:
    if type(history) is not PlanHistory or type(vision) is not SeriesVision:
        raise PlanningError("exact history and proposed vision are required")
    active = history.active
    version = PlanVersion(
        active.id,
        active.revision + 1,
        active.content_hash,
        vision,
        active.fixture_hash if fixture_hash is None else fixture_hash,
    )
    _validate_revision(history, version)
    return ReplanProposal(
        active.content_hash,
        version,
        diff_plans(active, version).affected_chapter_ids,
        _text(reason, "reason"),
    )


def assess_changes(
    before: InputIdentity,
    after: InputIdentity,
    *,
    chapter_ids: tuple[EntityId, ...],
    before_plan: PlanVersion | None = None,
    after_plan: PlanVersion | None = None,
) -> Invalidation:
    """Classify only declared dependencies; no model, writer or plan adoption."""
    if type(before) is not InputIdentity or type(after) is not InputIdentity:
        raise PlanningError("exact frozen input identities are required")
    ids = _ids(chapter_ids, "dependent chapters")
    if len({v.project for v in ids}) > 1:
        raise PlanningError("invalidation chapters cross project")
    names = (
        "parent_ref",
        "canon_hash",
        "pack_hash",
        "knowledge_hash",
        "plan_hash",
        "continuity_hash",
    )
    changed = tuple(
        name for name in names if getattr(before, name) != getattr(after, name)
    )
    if not changed:
        return Invalidation((), (), ids, False)
    affected = set(ids)
    if changed == ("plan_hash",) and before_plan is not None and after_plan is not None:
        if (
            before_plan.content_hash != before.plan_hash
            or after_plan.content_hash != after.plan_hash
        ):
            raise PlanningError("supplied plan payloads do not match input identities")
        diff = diff_plans(before_plan, after_plan)
        affected = set(ids) & set(diff.affected_chapter_ids)
    return Invalidation(
        changed,
        tuple(sorted(affected, key=str)),
        tuple(sorted(set(ids) - affected, key=str)),
        True,
    )
