"""Deterministic provenance for approved-state consumption by the next chapter."""
from __future__ import annotations

import hashlib
import json
from typing import Mapping


def build_consumption_evidence(*, chapter_id: str, approved_candidates: list[Mapping] | None = None, mint_records: list[Mapping] | None = None, recompute: Mapping | None = None, state_before: Mapping | None = None, state_after: Mapping | None = None, objective_id: str | None = None, prompt_manifest_id: str | None = None, draft_ref: str | None = None) -> dict:
    approved = [str(item.get("id")) for item in approved_candidates or [] if item.get("id")]
    mints = [str(item.get("id")) for item in mint_records or [] if item.get("id")]
    # Carry the SEMANTIC content of each minted fact (name/field/value), not just
    # its id — the next chapter's prompt must be able to READ what the fact IS to
    # write it into prose. Id+hash alone (the audit shell) leaves the model unable
    # to consume the fact (CI-M2-04 finding). Sorted for deterministic hashing.
    approved_facts = sorted(
        ({"id": str(m.get("id")),
          "name": (str(m.get("name")) if m.get("name") is not None else None),
          "field": (str(m.get("field")) if m.get("field") is not None else None),
          "value": m.get("value")}
         for m in mint_records or [] if m.get("id")),
        key=lambda f: f["id"])
    payload = {
        "chapter_id": chapter_id,
        "approved_candidate_ids": sorted(set(approved)),
        "mint_ids": sorted(set(mints)),
        "approved_facts": approved_facts,
        "recompute_ref": (recompute or {}).get("id") or (recompute or {}).get("content_hash"),
        "state_before_hash": (state_before or {}).get("state_hash"),
        "state_after_hash": (state_after or {}).get("state_hash"),
        "objective_id": objective_id,
        "prompt_manifest_id": prompt_manifest_id,
        "draft_ref": draft_ref,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["consumption_hash"] = "sha256:" + hashlib.sha256(raw).hexdigest()
    return payload


def approved_state_constraints(evidence: Mapping | None, state_after: Mapping | None) -> list[str]:
    if not evidence or not evidence.get("mint_ids"):
        return []
    constraints = ["已批准并 Mint 的事实必须与重算后的 StoryState 保持一致"]
    if (state_after or {}).get("state_hash"):
        constraints.append(f"本章须遵守重算状态：{state_after['state_hash']}")
    for fact in evidence.get("approved_facts") or []:
        name = str(fact.get("name") or fact.get("value") or fact.get("id") or "").strip()
        if not name:
            continue
        field = str(fact.get("field") or "fact")
        value = fact.get("value")
        detail = f"{field}={value}" if value is not None else field
        constraints.append(
            f"已批准事实必须在正文行动或描写中自然体现：{name}（{detail}）")
    return constraints
