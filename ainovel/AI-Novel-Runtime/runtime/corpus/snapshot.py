"""Immutable Corpus Snapshot construction, persistence, and fitness queries."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping

SCHEMA_VERSION = "1.0"
KIND = "corpus_snapshot"
PERFORMANCE_TIERS = ("top", "control", "high_open_low_finish", "unknown")
_CONTENT_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


class CorpusSnapshotError(ValueError):
    """The snapshot violates deterministic inventory or access constraints."""


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _manifest_payload(snapshot: Mapping) -> dict:
    return {
        "id": snapshot.get("id"),
        "kind": snapshot.get("kind"),
        "schema_version": snapshot.get("schema_version"),
        "corpus_policy": snapshot.get("corpus_policy"),
        "books": snapshot.get("books"),
        "counts": snapshot.get("counts"),
        "toolchain": snapshot.get("toolchain"),
    }


def canonical_manifest_hash(snapshot: Mapping) -> str:
    """Hash reproducibility inputs while deliberately excluding created_at."""
    digest = hashlib.sha256(_canonical_json(_manifest_payload(snapshot))).hexdigest()
    return f"sha256:{digest}"


def _validate_relative_path(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise CorpusSnapshotError("book relative_path must be a non-empty string")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise CorpusSnapshotError(f"book relative_path escapes corpus root: {raw}")
    return path.as_posix()


def _validate_books(books: Iterable[Mapping]) -> list[dict]:
    normalized: list[dict] = []
    ids: set[str] = set()
    paths: set[str] = set()
    hashes: set[str] = set()
    for source in books:
        book = dict(source)
        book_id = book.get("id")
        if not isinstance(book_id, str) or book_id in ids:
            raise CorpusSnapshotError(f"duplicate or invalid corpus book id: {book_id}")
        book["relative_path"] = _validate_relative_path(book.get("relative_path"))
        if book["relative_path"] in paths:
            raise CorpusSnapshotError(f"duplicate corpus relative_path: {book['relative_path']}")
        content_hash = book.get("content_sha256")
        if not isinstance(content_hash, str) or not _CONTENT_HASH_RE.fullmatch(content_hash):
            raise CorpusSnapshotError(f"invalid content_sha256 for {book_id}")
        if content_hash in hashes:
            cluster = book.get("duplicate_cluster_id")
            prior_clusters = {
                item.get("duplicate_cluster_id")
                for item in normalized
                if item.get("content_sha256") == content_hash
            }
            if not cluster or prior_clusters != {cluster}:
                raise CorpusSnapshotError(
                    f"duplicate content must share duplicate_cluster_id: {book_id}"
                )
        ids.add(book_id)
        paths.add(book["relative_path"])
        hashes.add(content_hash)
        normalized.append(book)
    return sorted(normalized, key=lambda item: item["id"])


def _counts(books: list[dict]) -> dict:
    tiers = {tier: 0 for tier in PERFORMANCE_TIERS}
    for book in books:
        tier = book.get("performance_tier")
        if tier not in tiers:
            raise CorpusSnapshotError(f"unsupported performance_tier: {tier}")
        tiers[tier] += 1
    authorized = sum(b.get("authorization_status") == "authorized" for b in books)
    ready = len(query_analysis_books({"books": books}))
    return {
        "total": len(books),
        "by_performance_tier": tiers,
        "authorized": authorized,
        "ready_for_analysis": ready,
    }


def build_snapshot(
    *,
    snapshot_id: str,
    created_at: str,
    corpus_policy: Mapping,
    books: Iterable[Mapping],
    toolchain: Mapping,
) -> dict:
    """Build a canonical snapshot; callers persist it only through write_snapshot."""
    normalized_books = _validate_books(books)
    snapshot = {
        "id": snapshot_id,
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "corpus_policy": dict(corpus_policy),
        "books": normalized_books,
        "counts": _counts(normalized_books),
        "toolchain": dict(toolchain),
    }
    snapshot["manifest_hash"] = canonical_manifest_hash(snapshot)
    return snapshot


def query_analysis_books(snapshot: Mapping) -> list[dict]:
    """Return authorized, clean, analyzable canonical members only."""
    seen_clusters: set[str] = set()
    selected: list[dict] = []
    for source in sorted(snapshot.get("books") or [], key=lambda item: item.get("id", "")):
        book = dict(source)
        if book.get("authorization_status") != "authorized":
            continue
        if book.get("cleaning_status") != "ready":
            continue
        if book.get("analysis_status") not in {"ready", "completed"}:
            continue
        cluster = book.get("duplicate_cluster_id")
        if cluster and cluster in seen_clusters:
            continue
        if cluster:
            seen_clusters.add(cluster)
        selected.append(book)
    return selected


def validate_corpus_files(corpus_root: str | Path, snapshot: Mapping) -> list[dict]:
    """Return deterministic inventory findings without reading source prose out."""
    root = Path(corpus_root).resolve()
    findings: list[dict] = []
    for book in sorted(snapshot.get("books") or [], key=lambda item: item.get("id", "")):
        relative_path = _validate_relative_path(book.get("relative_path"))
        path = (root / relative_path).resolve()
        if root not in path.parents:
            findings.append({"book_id": book.get("id"), "code": "path_escape"})
            continue
        if not path.is_file():
            findings.append({"book_id": book.get("id"), "code": "missing_file"})
            continue
        raw = path.read_bytes()
        if len(raw) != book.get("size_bytes"):
            findings.append({"book_id": book.get("id"), "code": "size_mismatch"})
        if hashlib.sha256(raw).hexdigest() != book.get("content_sha256"):
            findings.append({"book_id": book.get("id"), "code": "hash_mismatch"})
    return findings


def write_snapshot(corpus_root: str | Path, snapshot: Mapping) -> str:
    """Persist beneath the corpus root; never writes a project facts directory."""
    root = Path(corpus_root)
    expected = canonical_manifest_hash(snapshot)
    if snapshot.get("manifest_hash") != expected:
        raise CorpusSnapshotError("manifest_hash does not match canonical snapshot content")
    out_dir = root / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{snapshot['id']}.json"
    path.write_text(
        json.dumps(dict(snapshot), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return str(path.relative_to(root))


def load_snapshot(corpus_root: str | Path, snapshot_id: str) -> dict:
    path = Path(corpus_root) / "snapshots" / f"{snapshot_id}.json"
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorpusSnapshotError(f"unable to load corpus snapshot: {path}") from exc
    _validate_books(snapshot.get("books") or [])
    if snapshot.get("manifest_hash") != canonical_manifest_hash(snapshot):
        raise CorpusSnapshotError("loaded snapshot manifest_hash is invalid")
    if snapshot.get("counts") != _counts(snapshot["books"]):
        raise CorpusSnapshotError("loaded snapshot counts are inconsistent")
    return snapshot
