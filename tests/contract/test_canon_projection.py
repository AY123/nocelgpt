"""Pure historical version/reducer contracts, without database or Permit issuance."""

from dataclasses import replace
from hashlib import sha256

import pytest
from test_canon_commit import PARENT, baseline, candidate, eid, receipt

from anovel.canon.chapter import StoredChapter
from anovel.canon.identity import CANONICAL_ENCODING, canonical_bytes
from anovel.canon.models import CanonError, RootSeed, StoredRoot
from anovel.canon.projection import HistoryEntry, rebuild
from anovel.domain.delta import FactState, preview_delta
from anovel.domain.identity import Entity


def history():
    base = baseline()
    proposal = candidate()
    root_receipt = replace(
        receipt(), request_id="root", commit_id=PARENT, payload_hash="d" * 64
    )
    root = StoredRoot(
        root_receipt,
        RootSeed((Entity(eid("room"), "room"),), (), (base.facts[0].seed_fact,)),
        b"manual root",
        b"{}",
    )
    state = preview_delta(
        base,
        proposal.delta,
        source_id=proposal.id,
        authorization_refs=frozenset(["chapter:open"]),
    ).candidate
    permit = canonical_bytes(
        {
            "kind": "COMMIT_PERMIT",
            "schema_version": "1.0",
            "policy": {
                "kind": "CHAPTER_POLICY",
                "schema_version": "1.0",
                "project": proposal.project,
                "branch": proposal.branch,
                "authorization_refs": ["chapter:open"],
            },
        }
    )
    chapter = StoredChapter(receipt(proposal.payload_hash), proposal, state, permit)
    return (
        HistoryEntry(
            0, None, "ROOT_INITIALIZED", "ROOT-1", "1.0", CANONICAL_ENCODING, root
        ),
        HistoryEntry(
            1,
            PARENT,
            "CHAPTER_COMMITTED",
            "FACT_DELTA-1",
            "1.0",
            CANONICAL_ENCODING,
            chapter,
        ),
    )


def test_registered_old_versions_replay_exact_original_snapshot_before_reanchoring():
    original = history()
    result = rebuild(original)
    assert result.receipt == original[-1].content.receipt
    assert result.baseline.parent_ref == result.receipt.commit_id
    assert result.baseline.facts[0].state == FactState.known("open")
    assert result.baseline.facts[0].revision == 1
    assert (
        result.baseline_sha256
        == sha256(canonical_bytes(result.baseline.to_dict())).hexdigest()
    )
    step = result.checkpoints[-1]
    original_digest = sha256(
        canonical_bytes(original[-1].content.state.to_dict())
    ).hexdigest()
    assert step.snapshot_sha256 == step.expected_snapshot_sha256 == original_digest
    assert [step.reducer_version for step in result.checkpoints] == [
        "ROOT-1",
        "FACT_DELTA-1",
    ]
    assert rebuild(original) == result


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "2.0"),
        ("encoding", "UNSUPPORTED"),
        ("event_type", "UNREGISTERED"),
        ("reducer_version", "UNSUPPORTED-999"),
    ],
)
def test_unknown_historical_version_never_falls_back_to_current(index, field, value):
    source = list(history())
    source[index] = replace(source[index], **{field: value})
    with pytest.raises(CanonError):
        rebuild(tuple(source))


@pytest.mark.parametrize(
    "change",
    [
        "no-root",
        "reverse",
        "duplicate",
        "sequence-gap",
        "wrong-parent",
        "duplicate-root",
        "wrong-root-content",
    ],
)
def test_incomplete_or_contradictory_event_chain_is_rejected(change):
    source = history()
    if change == "no-root":
        changed = source[1:]
    elif change == "reverse":
        changed = source[::-1]
    elif change == "duplicate":
        changed = source + (source[-1],)
    elif change == "sequence-gap":
        changed = (source[0], replace(source[1], sequence=3))
    elif change == "wrong-parent":
        changed = (source[0], replace(source[1], parent_ref="sha256:" + "e" * 64))
    elif change == "duplicate-root":
        changed = source + (
            replace(
                source[0], sequence=2, parent_ref=source[-1].content.receipt.commit_id
            ),
        )
    else:
        changed = (replace(source[0], content=source[-1].content), source[-1])
    with pytest.raises(CanonError):
        rebuild(changed)


@pytest.mark.parametrize("change", ["state", "revision", "seed"])
def test_saved_snapshot_cannot_replace_independently_recomputed_state(change):
    root, chapter = history()
    state = chapter.content.state
    snapshot = state.facts[0]
    if change == "state":
        altered = replace(snapshot, state=FactState.known("closed"))
    elif change == "revision":
        altered = replace(snapshot, revision=2)
    else:
        seed = replace(snapshot.seed_fact, evidence_ref="different-history-source")
        altered = replace(snapshot, seed_fact=seed)
    changed_state = replace(state, facts=(altered,))
    changed = replace(chapter, content=replace(chapter.content, state=changed_state))
    with pytest.raises(CanonError):
        rebuild((root, changed))


@pytest.mark.parametrize("value", [None, (), []])
def test_empty_or_untyped_history_has_no_successful_projection(value):
    with pytest.raises(CanonError):
        rebuild(value)


@pytest.mark.parametrize("value", [False, -1])
def test_invalid_sequence_identity_is_not_accepted_as_integer_alias(value):
    source = history()
    with pytest.raises(CanonError):
        rebuild((replace(source[0], sequence=value), source[-1]))


def test_same_known_reducer_in_wrong_event_position_is_rejected():
    root, chapter = history()
    with pytest.raises(CanonError):
        rebuild((replace(root, reducer_version="FACT_DELTA-1"), chapter))
    with pytest.raises(CanonError):
        rebuild((root, replace(chapter, reducer_version="ROOT-1")))
