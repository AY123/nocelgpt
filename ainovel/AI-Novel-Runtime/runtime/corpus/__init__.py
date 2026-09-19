"""Versioned external-corpus evidence for narrative mining."""

from .snapshot import (
    CorpusSnapshotError,
    build_snapshot,
    canonical_manifest_hash,
    load_snapshot,
    query_analysis_books,
    validate_corpus_files,
    write_snapshot,
)

__all__ = [
    "CorpusSnapshotError",
    "build_snapshot",
    "canonical_manifest_hash",
    "load_snapshot",
    "query_analysis_books",
    "validate_corpus_files",
    "write_snapshot",
]
