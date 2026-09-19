"""Narrative evidence pack retrieval for Genesis and outline planning."""
from __future__ import annotations

import hashlib
from typing import Mapping


def build_query_hash(query: Mapping, snapshot_id: str) -> str:
    payload = {"query": query, "snapshot_id": snapshot_id}
    raw = repr(sorted(payload.items())).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def build_narrative_evidence_pack(*, task: str, snapshot: Mapping, query: Mapping, baselines: list[dict], patterns: list[dict], anti_patterns: list[dict], constraints: list[str], originality: Mapping, profile_ids: list[str], retrieval_policy_version: str = "genesis-retrieval-v1") -> dict:
    query_hash = build_query_hash(query, snapshot["id"])
    return {
        "id": f"NEP-{snapshot['id'].removeprefix('CORPUS-')}-{task.upper()}",
        "kind": "narrative_evidence_pack",
        "schema_version": "1.0",
        "task": task,
        "corpus_snapshot_id": snapshot["id"],
        "query": dict(query),
        "baselines": baselines,
        "patterns": patterns,
        "anti_patterns": anti_patterns,
        "constraints": constraints,
        "originality": dict(originality),
        "provenance": {
            "snapshot_hash": snapshot["manifest_hash"],
            "query_hash": query_hash,
            "retrieval_policy_version": retrieval_policy_version,
            "profile_ids": sorted(set(profile_ids)),
        },
    }
