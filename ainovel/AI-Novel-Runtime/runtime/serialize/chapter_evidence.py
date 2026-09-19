"""chapter_evidence.py — N100-003 chapter-level product evidence ledger.

Builds a same-shape per-chapter record from an existing run manifest (+ optional
serial checkpoints). Does NOT invent a parallel run system; it folds product
evidence already present in RUN manifests into one queryable ledger.

Fields are consumer-facing (quality / cost / facts / accidents / resume):
human review slots stay empty until filled by real editors.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Optional

from .serialization_utils import content_hash, dump_pretty_json

LEDGER_KIND = "chapter_evidence_ledger"
LEDGER_VERSION = "1.0"
ROW_KIND = "chapter_evidence_row"


def _safe_get(d: Any, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def _chapter_length(ch: dict) -> dict:
    final = ch.get("chapter_final") or {}
    text = final.get("final_text") or ""
    if not text and isinstance(final.get("text_summary"), dict):
        # no full text in some manifests
        pass
    # Prefer structured length from comparison when present
    versions = _safe_get(final, "comparison_report", "versions", default=[]) or []
    for v in versions:
        if v.get("version_id") in ("draft", "winner", None):
            after = _safe_get(v, "text_summary", "after") or _safe_get(v, "diff_summary", "after_length")
            if isinstance(after, dict) and after:
                return {
                    "chars": after.get("chars"),
                    "words": after.get("words"),
                    "lines": after.get("lines"),
                }
    if text:
        return {
            "chars": len(text),
            "words": len(text.split()),
            "lines": text.count("\n") + 1 if text else 0,
        }
    return {"chars": None, "words": None, "lines": None}


def _scores(ch: dict) -> dict:
    final = ch.get("chapter_final") or {}
    review = final.get("final_review") or {}
    scores = review.get("scores") or {}
    return dict(scores) if isinstance(scores, dict) else {}


def _publish(ch: dict) -> dict:
    pr = ch.get("publish_readiness") or {}
    if not isinstance(pr, dict):
        return {}
    return {
        "recommendation": pr.get("recommendation"),
        "gates_build": pr.get("gates_build"),
        "rationale": pr.get("rationale"),
    }


def _llm(ch: dict) -> dict:
    llm = ch.get("llm") or {}
    if not isinstance(llm, dict):
        return {}
    usage = llm.get("token_usage") or {}
    return {
        "provider": llm.get("provider"),
        "model": llm.get("model"),
        "latency_ms": llm.get("latency_ms"),
        "response_hash": llm.get("response_hash"),
        "replay_ref": llm.get("replay_ref"),
        "cost": llm.get("cost"),
        "token_usage": {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "cached_input_tokens": usage.get("cached_input_tokens"),
            "usage_estimated": usage.get("usage_estimated"),
        },
    }


def _hashes(ch: dict) -> dict:
    final = ch.get("chapter_final") or {}
    return {
        "draft_hash": ch.get("draft_hash"),
        "state_hash": ch.get("state_hash"),
        "final_hash": final.get("final_hash"),
        "winner_id": _safe_get(final, "comparison_report", "winner"),
    }


def _accidents(ch: dict) -> list:
    out = []
    if ch.get("ok") is False:
        out.append({"type": "chapter_not_ok", "message": ch.get("message") or ch.get("stage")})
    final = ch.get("chapter_final") or {}
    notes = final.get("continuity_notes") or []
    for n in notes:
        out.append({"type": "continuity", "message": n})
    pr = ch.get("publish_readiness") or {}
    basis = pr.get("basis") or {}
    redline = basis.get("redline") or {}
    if redline.get("passed") is False:
        out.append({"type": "redline", "hits": redline.get("hits") or []})
    return out


def _human_slots() -> dict:
    """Empty until real human review is recorded — never AI-filled."""
    return {
        "reviewer_ids": [],
        "accept": None,
        "edit_minutes": None,
        "labels": [],
        "notes": "",
        "adjudication": None,
    }


def _fact_slots() -> dict:
    """W12 / mint consumption slots — filled when run or side artifacts provide them."""
    return {
        "candidates_staged": None,
        "candidates_mintable": None,
        "mint_receipt_ids": [],
        "approval_request_ids": [],
        "next_chapter_consumed": None,
    }


def build_chapter_row(ch: dict, *, checkpoint: Optional[dict] = None) -> dict:
    final = ch.get("chapter_final") or {}
    row = {
        "kind": ROW_KIND,
        "version": LEDGER_VERSION,
        "chapter_index": ch.get("index"),
        "task_id": ch.get("task_id"),
        "event_id": ch.get("event"),
        "stage": ch.get("stage"),
        "ok": ch.get("ok"),
        "output_path": ch.get("output_path"),
        "hashes": _hashes(ch),
        "length": _chapter_length(ch),
        "quality": {
            "scores": _scores(ch),
            "overall_verdict": _safe_get(final, "final_review", "overall_verdict"),
            "publish_readiness": _publish(ch),
            "commercial_verdict": ch.get("commercial_verdict"),
            "verdict": ch.get("verdict"),
        },
        "llm": _llm(ch),
        "prompt_provenance": ch.get("prompt_provenance") or {},
        "facts": _fact_slots(),
        "human": _human_slots(),
        "accidents": _accidents(ch),
        "checkpoint": None,
    }
    if checkpoint:
        m7 = checkpoint.get("m7") or {}
        row["checkpoint"] = {
            "chapter_index": checkpoint.get("chapter_index"),
            "draft_hash": checkpoint.get("draft_hash"),
            "state_hash": checkpoint.get("state_hash"),
            "final_hash": checkpoint.get("final_hash"),
            "m7_recommendation": m7.get("recommendation"),
            "m7_risk_level": m7.get("risk_level"),
            "redline_passed": m7.get("redline_passed"),
            "similarity": _safe_get(m7, "similarity", "overall_similarity"),
        }
    row["content_hash"] = content_hash({k: v for k, v in row.items() if k != "content_hash"})
    return row


def load_run_manifest(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_checkpoints(project_path: str | Path) -> dict[int, dict]:
    root = Path(project_path) / "registry" / "derived" / "serial-checkpoints"
    out: dict[int, dict] = {}
    if not root.is_dir():
        return out
    for p in sorted(root.glob("cp-*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        idx = obj.get("chapter_index")
        if isinstance(idx, int):
            out[idx] = obj
    return out


def build_chapter_evidence_ledger(
    *,
    run_manifest: dict,
    project_path: str | Path | None = None,
    protocol_id: str = "",
    protocol_config_hash: str = "",
    notes: str = "",
) -> dict:
    chapters = list(run_manifest.get("chapters") or [])
    cps = load_checkpoints(project_path) if project_path else {}
    rows = []
    for ch in chapters:
        if not isinstance(ch, dict):
            continue
        idx = ch.get("index")
        rows.append(build_chapter_row(ch, checkpoint=cps.get(idx)))
    rows.sort(key=lambda r: (r.get("chapter_index") is None, r.get("chapter_index") or 0))

    totals = run_manifest.get("totals") or {}
    ledger = {
        "kind": LEDGER_KIND,
        "version": LEDGER_VERSION,
        "run_id": run_manifest.get("id") or _safe_get(run_manifest, "run", "id"),
        "run_ref": {
            "kind": run_manifest.get("kind"),
            "version": run_manifest.get("version"),
            "gating": run_manifest.get("gating"),
        },
        "protocol_id": protocol_id,
        "protocol_config_hash": protocol_config_hash,
        "totals": {
            "planned": totals.get("planned"),
            "produced": totals.get("produced"),
            "skipped": totals.get("skipped"),
            "live_calls": totals.get("live_calls"),
            "final_state_hash": totals.get("final_state_hash"),
            "token_usage": totals.get("token_usage"),
            "cost": totals.get("cost"),
        },
        "chapter_count": len(rows),
        "chapters": rows,
        "notes": notes,
    }
    ledger["content_hash"] = content_hash({k: v for k, v in ledger.items() if k != "content_hash"})
    return ledger


def write_chapter_evidence_ledger(path: str | Path, ledger: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_pretty_json(ledger) + "\n", encoding="utf-8")
    return path


def build_ledger_from_project(
    project_path: str | Path,
    *,
    run_manifest_id: str = "RUN-00025",
    protocol_id: str = "",
    protocol_config_hash: str = "",
    notes: str = "",
) -> dict:
    project_path = Path(project_path)
    manifest_path = project_path / "registry" / "derived" / "run-manifests" / f"{run_manifest_id}.json"
    manifest = load_run_manifest(manifest_path)
    return build_chapter_evidence_ledger(
        run_manifest=manifest,
        project_path=project_path,
        protocol_id=protocol_id,
        protocol_config_hash=protocol_config_hash,
        notes=notes,
    )
