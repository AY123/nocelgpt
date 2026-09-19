"""Advisory originality risk reads for narrative evidence and candidates."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Mapping


def assess_evidence_originality(evidence_pack: Mapping) -> dict:
    originality = evidence_pack.get("originality") or {}
    clusters = int(originality.get("source_cluster_count") or 0)
    share = float(originality.get("max_single_source_share") or 0.0)
    declared = originality.get("risk_level") or "medium"
    reasons = []
    if clusters < 2:
        reasons.append("insufficient_source_clusters")
    if share > 0.6:
        reasons.append("single_source_concentration")
    computed = "high" if reasons else "medium" if clusters < 3 or share > 0.45 else "low"
    risk = max((declared, computed), key={"low": 0, "medium": 1, "high": 2}.get)
    payload = {
        "evidence_pack_id": evidence_pack.get("id"),
        "corpus_snapshot_id": evidence_pack.get("corpus_snapshot_id"),
        "snapshot_hash": (evidence_pack.get("provenance") or {}).get("snapshot_hash"),
        "query_hash": (evidence_pack.get("provenance") or {}).get("query_hash"),
        "source_cluster_count": clusters,
        "max_single_source_share": share,
        "risk_level": risk,
        "reasons": reasons,
        "comparison_only": True,
        "legal_conclusion": False,
    }
    payload["report_hash"] = _hash(payload)
    return payload


def assess_candidate_originality(candidate: Mapping, evidence_pack: Mapping) -> dict:
    evidence = assess_evidence_originality(evidence_pack)
    evidence_types = [
        str(item.get("pattern_type"))
        for item in evidence_pack.get("patterns", [])
        if isinstance(item, Mapping) and item.get("pattern_type")
    ]
    focus = [str(item) for item in candidate.get("design_focus", [])]
    overlap = sum((Counter(evidence_types) & Counter(focus)).values())
    ratio = overlap / len(evidence_types) if evidence_types else 0.0
    reasons = list(evidence["reasons"])
    if ratio > 0.75 and evidence["source_cluster_count"] < 3:
        reasons.append("candidate_overfits_low_diversity_patterns")
    risk = "high" if "candidate_overfits_low_diversity_patterns" in reasons or evidence["risk_level"] == "high" else evidence["risk_level"]
    return {
        "candidate_id": candidate.get("id"),
        "risk_level": risk,
        "functional_pattern_overlap": round(ratio, 3),
        "reasons": sorted(set(reasons)),
        "report_hash": evidence["report_hash"],
        "comparison_only": True,
        "legal_conclusion": False,
    }


def _hash(value: Mapping) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()
