import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from runtime.corpus import (
    CorpusSnapshotError,
    build_snapshot,
    canonical_manifest_hash,
    load_snapshot,
    query_analysis_books,
    validate_corpus_files,
    write_snapshot,
)


def _schema() -> dict:
    path = (
        Path(__file__).resolve().parents[2]
        / "AI-Novel-Standard"
        / "contracts"
        / "corpus-snapshot.schema.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _book(index: int, **overrides) -> dict:
    value = {
        "id": f"CBK-{index:08d}",
        "relative_path": f"books/book-{index}.txt",
        "content_sha256": f"{index:064x}",
        "size_bytes": 1000 + index,
        "genre": "玄幻",
        "performance_tier": "top",
        "completion_status": "completed",
        "authorization_status": "authorized",
        "cleaning_status": "ready",
        "duplicate_cluster_id": None,
        "analysis_status": "ready",
    }
    value.update(overrides)
    return value


def _snapshot(created_at: str = "2026-07-26T00:00:00Z", books=None) -> dict:
    return build_snapshot(
        snapshot_id="CORPUS-2026-001",
        created_at=created_at,
        corpus_policy={
            "authorization_scope": "internal-authorized",
            "allowed_uses": ["narrative_mining"],
            "prohibited_uses": ["source_prose_generation_context"],
        },
        books=books if books is not None else [_book(1), _book(2)],
        toolchain={
            "segmenter_version": "reference-segment-v1",
            "analyzer_version": "narrative-miner-v1",
            "prompt_version": "book-profile-v1",
            "model_policy_version": "corpus-model-policy-v1",
        },
    )


def test_snapshot_conforms_to_schema():
    Draft202012Validator(_schema()).validate(_snapshot())


def test_manifest_hash_excludes_created_at_and_book_order():
    a = _snapshot("2026-07-26T00:00:00Z", [_book(2), _book(1)])
    b = _snapshot("2026-07-27T00:00:00Z", [_book(1), _book(2)])
    assert a["manifest_hash"] == b["manifest_hash"]
    assert canonical_manifest_hash(a) == a["manifest_hash"]


def test_query_excludes_unauthorized_unready_and_duplicate_members():
    books = [
        _book(1, duplicate_cluster_id="DUP-ABC"),
        _book(2, duplicate_cluster_id="DUP-ABC"),
        _book(3, authorization_status="restricted"),
        _book(4, cleaning_status="pending"),
        _book(5, analysis_status="failed"),
        _book(6),
    ]
    snapshot = _snapshot(books=books)
    assert [b["id"] for b in query_analysis_books(snapshot)] == [
        "CBK-00000001",
        "CBK-00000006",
    ]
    assert snapshot["counts"]["authorized"] == 5
    assert snapshot["counts"]["ready_for_analysis"] == 2


@pytest.mark.parametrize("path", ["/tmp/book.txt", "../book.txt", "books/../book.txt"])
def test_rejects_paths_outside_corpus_root(path):
    with pytest.raises(CorpusSnapshotError, match="escapes corpus root"):
        _snapshot(books=[_book(1, relative_path=path)])


def test_duplicate_content_requires_cluster():
    with pytest.raises(CorpusSnapshotError, match="duplicate content"):
        _snapshot(books=[_book(1), _book(2, content_sha256=f"{1:064x}")])


def test_duplicate_content_must_share_the_same_cluster():
    with pytest.raises(CorpusSnapshotError, match="share duplicate_cluster_id"):
        _snapshot(
            books=[
                _book(1, duplicate_cluster_id="DUP-ONE"),
                _book(2, content_sha256=f"{1:064x}", duplicate_cluster_id="DUP-TWO"),
            ]
        )


def test_rejects_non_hex_content_hash():
    with pytest.raises(CorpusSnapshotError, match="invalid content_sha256"):
        _snapshot(books=[_book(1, content_sha256="z" * 64)])


def test_write_load_round_trip_and_tamper_detection(tmp_path):
    snapshot = _snapshot()
    rel = write_snapshot(tmp_path, snapshot)
    assert rel == "snapshots/CORPUS-2026-001.json"
    assert load_snapshot(tmp_path, "CORPUS-2026-001") == snapshot

    path = tmp_path / rel
    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["books"][0]["genre"] = "都市"
    path.write_text(json.dumps(tampered, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(CorpusSnapshotError, match="manifest_hash"):
        load_snapshot(tmp_path, "CORPUS-2026-001")


def test_schema_forbids_source_prose_and_external_identity_fields():
    properties = _schema()["$defs"]["book"]["properties"]
    assert "text" not in properties
    assert "excerpt" not in properties
    assert "title" not in properties
    assert "author" not in properties
    assert "external_id" not in properties
    assert _schema()["$defs"]["book"]["additionalProperties"] is False


def _fixture_snapshot():
    root = Path(__file__).parent / "fixtures" / "corpus-xuanhuan-10"
    payload = json.loads((root / "snapshot-input.json").read_text(encoding="utf-8"))
    return root, build_snapshot(**payload)


def test_xuanhuan_fixture_is_replayable_and_covers_fitness_classes():
    root, snapshot = _fixture_snapshot()
    Draft202012Validator(_schema()).validate(snapshot)
    assert snapshot["counts"] == {
        "total": 10,
        "by_performance_tier": {
            "top": 3,
            "control": 3,
            "high_open_low_finish": 2,
            "unknown": 2,
        },
        "authorized": 9,
        "ready_for_analysis": 7,
    }
    assert validate_corpus_files(root, snapshot) == []
    assert [book["id"] for book in query_analysis_books(snapshot)] == [
        "CBK-00000001",
        "CBK-00000002",
        "CBK-00000003",
        "CBK-00000004",
        "CBK-00000005",
        "CBK-00000006",
        "CBK-00000007",
    ]


def test_fixture_manifest_replays_independently_of_timestamp():
    _root, snapshot = _fixture_snapshot()
    payload = dict(snapshot)
    payload.pop("manifest_hash")
    payload.pop("counts")
    payload.pop("kind")
    payload.pop("schema_version")
    payload["snapshot_id"] = payload.pop("id")
    payload["created_at"] = "2026-07-27T00:00:00Z"
    replayed = build_snapshot(**payload)
    assert replayed["manifest_hash"] == snapshot["manifest_hash"]


def test_inventory_validation_reports_missing_and_tampered_files(tmp_path):
    root, snapshot = _fixture_snapshot()
    copied = tmp_path / "corpus"
    copied.mkdir()
    (copied / "books").mkdir()
    for book in snapshot["books"]:
        source = root / book["relative_path"]
        target = copied / book["relative_path"]
        target.write_bytes(source.read_bytes())
    (copied / "books" / "book-01.txt").unlink()
    (copied / "books" / "book-02.txt").write_text("tampered", encoding="utf-8")
    assert validate_corpus_files(copied, snapshot) == [
        {"book_id": "CBK-00000001", "code": "missing_file"},
        {"book_id": "CBK-00000002", "code": "size_mismatch"},
        {"book_id": "CBK-00000002", "code": "hash_mismatch"},
    ]
