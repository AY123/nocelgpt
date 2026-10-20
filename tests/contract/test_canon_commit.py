"""Strict candidate and receipt identities do not manufacture commit authority."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
from pathlib import Path

import jsonschema
import pytest

from anovel.canon.chapter import CandidateEvidence, ChapterCandidate, StoredChapter
from anovel.canon.identity import canonical_bytes, decode_canonical
from anovel.canon.models import CanonError, CommitReceipt
from anovel.domain.delta import (
    FactBaseline,
    FactPath,
    NarrativeDelta,
    OperationMeta,
    Precondition,
    ProseEvidence,
    SetFact,
    preview_delta,
)
from anovel.domain.events import NarrativePosition
from anovel.domain.identity import EntityId
from anovel.domain.knowledge import Proposition, WorldFact

PARENT = "sha256:" + "a" * 64
ROOT = Path(__file__).resolve().parents[2]


def eid(value):
    return EntityId("book_a", value)


def baseline():
    return FactBaseline.from_world_facts(
        "book_a",
        "main",
        PARENT,
        (WorldFact(eid("door"), Proposition(eid("room"), "status", "closed"), "seed"),),
    )


def candidate():
    base = baseline()
    source = eid("chapter_1")
    operation = SetFact(
        OperationMeta(
            eid("open_door"),
            eid("door"),
            FactPath.VALUE,
            Precondition.from_snapshot(base.facts[0]),
            ProseEvidence(source, NarrativePosition(1, 1), "paragraph:1"),
            "chapter:open",
        ),
        "open",
    )
    return ChapterCandidate(
        source,
        "main",
        PARENT,
        1,
        "他推开了门。\r\n".encode(),
        NarrativeDelta(eid("delta_1"), "main", PARENT, source, (operation,)),
        tuple(
            CandidateEvidence(
                kind,
                b"\x00\xfffixture:" + kind.encode(),
                "fixture:" + kind.lower(),
                "1.0",
                "isolated-test",
                "1.0",
            )
            for kind in ("MODEL", "PACK", "CONTRACT", "CONTEXT")
        ),
    )


def receipt(payload="c" * 64):
    return CommitReceipt(
        "book_a",
        "main",
        "request_1",
        "sha256:" + "b" * 64,
        payload,
        "2026-10-19T08:30:00.123456Z",
    )


def receipt_validator():
    schema = json.loads((ROOT / "specs/schemas/commit-receipt.schema.json").read_text())
    return jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )


def test_candidate_round_trip_preserves_full_binary_evidence_and_raw_prose():
    original = candidate()
    data = decode_canonical(original.payload_bytes())
    restored = ChapterCandidate.from_dict(data)
    assert restored == original
    assert restored.prose == "他推开了门。\r\n".encode()
    assert restored.dependencies[0].content == b"\x00\xfffixture:CONTEXT"
    assert restored.dependencies[1].content == b"\x00\xfffixture:CONTRACT"
    assert original.payload_hash == sha256(original.payload_bytes()).hexdigest()
    assert original.to_dict()["raw_prose_hash"] == sha256(original.prose).hexdigest()
    assert {item.kind for item in restored.dependencies} == {
        "CONTRACT",
        "PACK",
        "MODEL",
        "CONTEXT",
    }
    assert all(
        item.content_hash == sha256(item.content).hexdigest()
        for item in restored.dependencies
    )


def test_dependency_order_is_set_like_but_content_and_metadata_are_bound():
    original = candidate()
    assert (
        replace(original, dependencies=original.dependencies[::-1]).payload_hash
        == original.payload_hash
    )
    first = original.dependencies[0]
    for field, value in (
        ("content", first.content + b"changed"),
        ("schema_id", "other-schema"),
        ("schema_version", "2.0"),
        ("producer", "other-producer"),
        ("producer_version", "2.0"),
    ):
        changed = replace(first, **{field: value})
        amended = replace(original, dependencies=(changed,) + original.dependencies[1:])
        assert amended.payload_hash != original.payload_hash


def test_all_candidate_inputs_change_stable_payload_without_attempt_metadata():
    original = candidate()
    changed_delta = replace(
        original.delta,
        operations=(replace(original.delta.operations[0], value="ajar"),),
    )
    new_parent = "sha256:" + "d" * 64
    alternatives = (
        replace(original, version=2),
        replace(original, prose=original.prose.replace(b"\r\n", b"\n")),
        replace(original, delta=changed_delta),
        replace(
            original,
            parent_ref=new_parent,
            delta=replace(original.delta, parent_ref=new_parent),
        ),
        replace(
            original, branch="draft", delta=replace(original.delta, branch="draft")
        ),
    )
    assert (
        len({original.payload_hash, *(item.payload_hash for item in alternatives)}) == 6
    )
    assert "attempt" not in original.to_dict()
    assert "permit" not in original.to_dict()


def test_candidate_does_not_mutate_on_export_and_uses_real_delta_preview():
    original = candidate()
    exported = original.to_dict()
    exported["dependencies"][0]["content_base64"] = ""
    exported["delta"]["operations"][0]["value"] = "corrupted"
    assert ChapterCandidate.from_dict(original.to_dict()) == original
    before = baseline()
    result = preview_delta(
        before,
        original.delta,
        source_id=original.id,
        authorization_refs=frozenset({"chapter:open"}),
    )
    assert result.candidate.facts[0].state.value == "open"
    assert before.facts[0].state.value == "closed"
    assert result.candidate.parent_ref == original.parent_ref
    with pytest.raises(FrozenInstanceError):
        original.version = 2


@pytest.mark.parametrize("version", [0, -1, True, 1.0, "1", None])
def test_candidate_version_has_no_coercion(version):
    with pytest.raises(ValueError):
        replace(candidate(), version=version)


@pytest.mark.parametrize(
    "value", ["parent", "sha256:" + "A" * 64, "sha256:" + "a" * 63, PARENT + "\n", None]
)
def test_candidate_parent_requires_exact_canon_identity(value):
    with pytest.raises(ValueError):
        replace(candidate(), parent_ref=value)


@pytest.mark.parametrize("value", [b"", bytearray(b"text"), "text", b"\xff"])
def test_candidate_prose_rejects_empty_nonbytes_or_non_utf8(value):
    with pytest.raises(ValueError):
        replace(candidate(), prose=value)


@pytest.mark.parametrize("mode", ["missing", "duplicate", "list", "unknown_type"])
def test_candidate_requires_four_exact_immutable_dependencies(mode):
    original = candidate()
    dependencies = {
        "missing": original.dependencies[:-1],
        "duplicate": original.dependencies[:-1] + (original.dependencies[0],),
        "list": list(original.dependencies),
        "unknown_type": original.dependencies[:-1] + ({},),
    }[mode]
    with pytest.raises(CanonError):
        replace(original, dependencies=dependencies)


def test_candidate_binds_delta_source_project_branch_and_parent():
    original = candidate()
    for delta in (
        replace(
            original.delta,
            source_id=eid("other_source"),
            operations=(
                replace(
                    original.delta.operations[0],
                    meta=replace(
                        original.delta.operations[0].meta,
                        evidence=replace(
                            original.delta.operations[0].meta.evidence,
                            source_id=eid("other_source"),
                        ),
                    ),
                ),
            ),
        ),
        replace(original.delta, branch="other"),
        replace(original.delta, parent_ref="sha256:" + "e" * 64),
    ):
        with pytest.raises(CanonError):
            replace(original, delta=delta)
    with pytest.raises(CanonError):
        replace(original, id=EntityId("other_book", original.id.local_id))


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "ALLOW"),
        ("content", b""),
        ("content", bytearray(b"x")),
        ("schema_id", ""),
        ("schema_version", None),
        ("producer", "  "),
        ("producer_version", 1),
    ],
)
def test_evidence_rejects_unregistered_kind_or_invalid_metadata(field, value):
    with pytest.raises(CanonError):
        replace(candidate().dependencies[0], **{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("content_hash", "0" * 64),
        ("content_base64", "not base64"),
        ("content_base64", "AB=="),
        ("content_base64", "eA===="),
        ("content_base64", None),
        ("kind", "UNKNOWN"),
        ("extra", True),
    ],
)
def test_evidence_parser_is_closed_and_detects_corruption(field, value):
    data = candidate().dependencies[0].to_dict()
    data[field] = value
    with pytest.raises(ValueError):
        CandidateEvidence.from_dict(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "ROOT_INPUT"),
        ("schema_version", "2.0"),
        ("project", "other_book"),
        ("raw_prose_hash", "f" * 64),
        ("prose_base64", "eA===="),
        ("dependencies", {}),
        ("version", False),
        ("extra", "ALLOW"),
    ],
)
def test_candidate_parser_rejects_wrong_binding_version_or_shape(field, value):
    data = candidate().to_dict()
    data[field] = value
    with pytest.raises(ValueError):
        ChapterCandidate.from_dict(data)


def test_candidate_and_evidence_records_require_every_field():
    original = candidate().to_dict()
    for name in original:
        data = dict(original)
        del data[name]
        with pytest.raises(ValueError):
            ChapterCandidate.from_dict(data)
    evidence = candidate().dependencies[0].to_dict()
    for name in evidence:
        data = dict(evidence)
        del data[name]
        with pytest.raises(ValueError):
            CandidateEvidence.from_dict(data)


def test_root_compatible_receipt_strict_roundtrip_and_schema():
    original = receipt()
    assert CommitReceipt.from_dict(original.to_dict()) == original
    assert canonical_bytes(original.to_dict()) == canonical_bytes(
        CommitReceipt.from_dict(original.to_dict()).to_dict()
    )
    validator = receipt_validator()
    validator.check_schema(validator.schema)
    validator.validate(original.to_dict())


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "PERMIT"),
        ("schema_version", "2.0"),
        ("project", ""),
        ("project", "  \t"),
        ("branch", "x" * 201),
        ("request_id", "x\x00y"),
        ("commit_id", "b" * 64),
        ("commit_id", "sha256:" + "B" * 64),
        ("commit_id", "sha256:" + "b" * 64 + "\n"),
        ("payload_hash", "sha256:" + "c" * 64),
        ("payload_hash", "c" * 64 + "\n"),
        ("payload_hash", None),
        ("created_at", "2026-10-19T08:30:00Z"),
        ("created_at", "2026-10-19T08:30:00.123456+00:00"),
        ("created_at", "2026-10-19T08:30:60.123456Z"),
        ("created_at", "2026-10-19T08:30:00.123456Z\n"),
        ("extra", True),
    ],
)
def test_receipt_domain_and_schema_reject_the_same_invalid_records(field, value):
    data = receipt().to_dict()
    data[field] = value
    with pytest.raises(ValueError):
        CommitReceipt.from_dict(data)
    assert not receipt_validator().is_valid(data)


def test_receipt_missing_fields_and_nonobjects_are_rejected():
    original = receipt().to_dict()
    for name in original:
        data = dict(original)
        del data[name]
        with pytest.raises(ValueError):
            CommitReceipt.from_dict(data)
        assert not receipt_validator().is_valid(data)
    for value in (None, [], "ALLOW"):
        with pytest.raises(ValueError):
            CommitReceipt.from_dict(value)


@pytest.mark.parametrize(
    "date,valid",
    [
        ("0001-01-01", True),
        ("9999-12-31", True),
        ("2000-02-29", True),
        ("2024-02-29", True),
        ("2400-02-29", True),
        ("2026-04-30", True),
        ("2026-01-31", True),
        ("2026-12-31", True),
        ("0000-01-01", False),
        ("1900-02-29", False),
        ("2100-02-29", False),
        ("2026-02-29", False),
        ("2026-04-31", False),
        ("2026-00-01", False),
        ("2026-13-01", False),
        ("2026-01-00", False),
        ("2026-01-32", False),
    ],
)
def test_receipt_schema_validates_calendar_without_optional_format_dependency(
    date, valid
):
    data = receipt().to_dict()
    data["created_at"] = date + "T23:59:59.999999Z"
    validator = receipt_validator()
    # JSON Schema checks UTC shape. Complete calendar validation belongs
    # to the strict domain parser, regardless of optional format packages.
    bare = jsonschema.Draft202012Validator(validator.schema)
    assert bare.is_valid(data)
    if valid:
        assert CommitReceipt.from_dict(data).created_at == data["created_at"]
    else:
        with pytest.raises(ValueError):
            CommitReceipt.from_dict(data)


def test_candidate_rejects_unregistered_identity_and_delta_subclasses():
    class DerivedId(EntityId):
        pass

    class DerivedDelta(NarrativeDelta):
        pass

    original = candidate()
    with pytest.raises(CanonError):
        replace(original, id=DerivedId(original.id.project, original.id.local_id))
    with pytest.raises(CanonError):
        replace(
            original,
            delta=DerivedDelta(
                original.delta.id,
                original.delta.branch,
                original.delta.parent_ref,
                original.delta.source_id,
                original.delta.operations,
            ),
        )


def test_retained_chapter_evidence_preserves_derived_parent_and_complete_bytes():
    original = candidate()
    state = preview_delta(
        baseline(),
        original.delta,
        source_id=original.id,
        authorization_refs=frozenset({"chapter:open"}),
    ).candidate
    stored = StoredChapter(
        receipt(original.payload_hash), original, state, b"fixture-permit"
    )
    assert stored.candidate.prose == original.prose
    assert stored.state.parent_ref == PARENT
    assert stored.permit_bytes == b"fixture-permit"
    for field, value in (
        ("permit_bytes", b""),
        ("receipt", receipt()),
        ("state", replace(state, parent_ref=stored.receipt.commit_id)),
        ("state", replace(state, branch="other")),
    ):
        with pytest.raises(ValueError):
            replace(stored, **{field: value})
