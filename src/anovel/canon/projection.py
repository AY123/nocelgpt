"""Pure replay of verified Canon history, never a second Canon writer.

Repository verifies the retained bytes, authorizations and receipts before the
service calls this module. A saved STATE_SNAPSHOT is a comparison target, never
the input to a reducer. A returned projection grants no commit authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from anovel.canon.chapter import StoredChapter
from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.canon.models import (
    CanonError,
    CanonIntegrityError,
    CommitReceipt,
    StoredRoot,
    identifier,
)
from anovel.domain.delta import FactBaseline, preview_delta
from anovel.domain.extensions import ExtensionRegistry


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """One scoped, immutable event and its fully verified retained evidence."""

    sequence: int
    parent_ref: str | None
    event_type: str
    reducer_version: str
    schema_version: str
    encoding: str
    content: StoredRoot | StoredChapter


@dataclass(frozen=True, slots=True)
class ProjectionCheckpoint:
    commit_id: str
    sequence: int
    event_type: str
    reducer_version: str
    schema_version: str
    encoding: str
    snapshot_sha256: str
    expected_snapshot_sha256: str | None


@dataclass(frozen=True, slots=True)
class RebuiltSnapshot:
    """A derived baseline anchored at the requested historical commit."""

    baseline: FactBaseline
    receipt: CommitReceipt
    checkpoints: tuple[ProjectionCheckpoint, ...]

    @property
    def baseline_sha256(self) -> str:
        return sha256(canonical_bytes(self.baseline.to_dict())).hexdigest()


class ProjectionError(CanonError):
    """Projection failed after verified history established an accepted target."""

    canon_committed = True

    def __init__(self, message: str, receipt: CommitReceipt) -> None:
        super().__init__(message)
        self.receipt = receipt


def _versions(entry: HistoryEntry, *, root: bool) -> None:
    if type(entry.sequence) is not int or entry.sequence < 0:
        raise CanonIntegrityError("invalid history sequence")
    try:
        for value in (
            entry.event_type,
            entry.reducer_version,
            entry.schema_version,
            entry.encoding,
        ):
            identifier(value)
    except CanonError as error:
        raise CanonIntegrityError("invalid historical version identity") from error
    pair = (
        ("ROOT_INITIALIZED", "ROOT-1")
        if root
        else ("CHAPTER_COMMITTED", "FACT_DELTA-1")
    )
    if (
        (entry.event_type, entry.reducer_version) != pair
        or entry.schema_version != "1.0"
        or entry.encoding != "ANOVELOS-CJSON-1"
    ):
        raise CanonIntegrityError("unsupported historical reducer, schema or encoding")


def _authorization_refs(stored: StoredChapter) -> frozenset[str]:
    """Consume the verified historical policy, not current issuance permission."""
    try:
        body = decode_canonical(stored.permit_bytes)
    except ValueError as error:
        raise CanonIntegrityError(
            "invalid historical projection Permit bytes"
        ) from error
    if (
        type(body) is not dict
        or body.get("kind") != "COMMIT_PERMIT"
        or body.get("schema_version") != "1.0"
    ):
        raise CanonIntegrityError("invalid historical projection Permit")
    policy = body.get("policy")
    if (
        type(policy) is not dict
        or policy.get("kind") != "CHAPTER_POLICY"
        or policy.get("schema_version") != "1.0"
        or policy.get("project") != stored.candidate.project
        or policy.get("branch") != stored.candidate.branch
    ):
        raise CanonIntegrityError("historical projection policy scope mismatch")
    refs = policy.get("authorization_refs")
    if type(refs) is not list or not refs:
        raise CanonIntegrityError("historical projection authorizations missing")
    try:
        for ref in refs:
            identifier(ref)
    except CanonError as error:
        raise CanonIntegrityError(
            "invalid historical projection authorization"
        ) from error
    if len(set(refs)) != len(refs):
        raise CanonIntegrityError("historical projection authorizations duplicated")
    return frozenset(refs)


def rebuild(
    history: tuple[HistoryEntry, ...],
    *,
    extension_registry: ExtensionRegistry | None = None,
) -> RebuiltSnapshot:
    """Replay every ancestor from its root; never bootstrap from a saved state.

    Version dispatch is deliberately limited to the actual retained v1 formats.
    Future formats must add their own historical reducer rather than silently
    reinterpret old events using the newest implementation.
    """
    if type(history) is not tuple or not history:
        raise CanonIntegrityError("a complete nonempty history is required")
    if any(type(entry) is not HistoryEntry for entry in history):
        raise CanonIntegrityError("invalid historical entry type")
    first = history[0]
    _versions(first, root=True)
    if (
        first.sequence != 0
        or first.parent_ref is not None
        or type(first.content) is not StoredRoot
    ):
        raise CanonIntegrityError("history must start at its unique root")
    root = first.content
    registry = ExtensionRegistry() if extension_registry is None else extension_registry
    if type(registry) is not ExtensionRegistry:
        raise CanonIntegrityError("invalid historical extension registry")
    project, branch = root.receipt.project, root.receipt.branch
    if root.seed.project != project:
        raise CanonIntegrityError("historical root crosses project scope")
    registry.validate_root(
        project,
        root.seed.extensions,
        root.seed.facts,
        tuple(item.id for item in root.seed.entities),
    )
    baseline = FactBaseline.from_world_facts(
        project,
        branch,
        root.receipt.commit_id,
        root.seed.facts,
        extensions=root.seed.extensions,
    )
    root_hash = sha256(canonical_bytes(baseline.to_dict())).hexdigest()
    checkpoints = [
        ProjectionCheckpoint(
            root.receipt.commit_id,
            0,
            first.event_type,
            first.reducer_version,
            first.schema_version,
            first.encoding,
            root_hash,
            None,  # Roots never had a persisted STATE_SNAPSHOT artifact.
        )
    ]
    seen = {root.receipt.commit_id}
    receipt = root.receipt
    for index, entry in enumerate(history[1:], start=1):
        _versions(entry, root=False)
        if type(entry.content) is not StoredChapter:
            raise CanonIntegrityError("a second root is not chapter history")
        chapter = entry.content
        pack_bytes = next(
            value.content
            for value in chapter.candidate.dependencies
            if value.kind == "PACK"
        )
        if chapter.state.extensions != baseline.extensions or any(
            binding.pack_bytes != pack_bytes for binding in baseline.extensions
        ):
            raise CanonIntegrityError(
                "historical chapter changed frozen Pack/extensions"
            )
        if (
            entry.sequence != index
            or entry.parent_ref != receipt.commit_id
            or chapter.candidate.parent_ref != entry.parent_ref
            or chapter.receipt.project != project
            or chapter.receipt.branch != branch
            or chapter.receipt.commit_id in seen
        ):
            raise CanonIntegrityError("historical ancestry or scope is inconsistent")
        preview = preview_delta(
            baseline,
            chapter.candidate.delta,
            source_id=chapter.candidate.id,
            authorization_refs=_authorization_refs(chapter),
            extension_registry=registry,
        )
        rebuilt_bytes = canonical_bytes(preview.candidate.to_dict())
        expected_bytes = canonical_bytes(chapter.state.to_dict())
        if rebuilt_bytes != expected_bytes:
            raise CanonIntegrityError(
                "replayed snapshot differs from accepted snapshot"
            )
        checkpoints.append(
            ProjectionCheckpoint(
                chapter.receipt.commit_id,
                entry.sequence,
                entry.event_type,
                entry.reducer_version,
                entry.schema_version,
                entry.encoding,
                sha256(rebuilt_bytes).hexdigest(),
                sha256(expected_bytes).hexdigest(),
            )
        )
        receipt = chapter.receipt
        seen.add(receipt.commit_id)
        # The stored comparison above belongs to the old parent. Only this
        # independently replayed state is re-anchored for the following event.
        baseline = FactBaseline(
            project,
            branch,
            receipt.commit_id,
            preview.candidate.facts,
            preview.candidate.extensions,
        )
    return RebuiltSnapshot(baseline, receipt, tuple(checkpoints))
