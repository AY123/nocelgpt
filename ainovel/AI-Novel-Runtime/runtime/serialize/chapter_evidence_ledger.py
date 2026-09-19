"""chapter_evidence_ledger.py — N100-003 chapter-level product evidence table.

One homogeneous row per chapter, folded from an existing ProductionRunManifest
(+ optional serial checkpoints). Does NOT invent a parallel fact store; it is a
derived read-side ledger for product audit (ADR-006).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .serialization_utils import content_hash, dump_pretty_json

LEDGER_KIND = "chapter_evidence_ledger"
LEDGER_VERSION = "1.0"


def _load_json(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _chapter_row(ch: dict, *, checkpoints_by_index: Dict[int, dict]) -> dict:
    index = int(ch.get("index") or 0)
    task_id = ch.get("task_id") or ""
    llm = ch.get("llm") or {}
    token_usage = llm.get("token_usage") or {}
    cf = ch.get("chapter_final") or {}
    final_review = cf.get("final_review") or {}
    publish = ch.get("publish_readiness") or {}
    m7 = None
    cp = checkpoints_by_index.get(index)
    if isinstance(cp, dict):
        m7 = cp.get("m7")
    elif isinstance(cf.get("m7"), dict):
        m7 = cf.get("m7")

    scores = final_review.get("scores") if isinstance(final_review, dict) else None
    final_hash = None
    if isinstance(cf, dict):
        final_hash = cf.get("final_hash") or (cf.get("final_review") or {}).get("final_hash")
    if not final_hash and isinstance(cp, dict):
        final_hash = cp.get("final_hash")

    return {
        "chapter_index": index,
        "task_id": task_id,
        "event_id": ch.get("event"),
        "ok": bool(ch.get("ok")),
        "stage": ch.get("stage"),
        "draft_hash": ch.get("draft_hash"),
        "state_hash": ch.get("state_hash"),
        "final_hash": final_hash,
        "output_path": ch.get("output_path"),
        "cost": {
            "provider": llm.get("provider"),
            "model": llm.get("model"),
            "latency_ms": llm.get("latency_ms"),
            "token_usage": {
                "input_tokens": token_usage.get("input_tokens"),
                "output_tokens": token_usage.get("output_tokens"),
                "total_tokens": token_usage.get("total_tokens"),
                "cached_input_tokens": token_usage.get("cached_input_tokens"),
            },
            "cost": llm.get("cost"),
            "response_hash": llm.get("response_hash"),
            "replay_ref": llm.get("replay_ref"),
        },
        "quality": {
            "verdict": ch.get("verdict") or final_review.get("overall_verdict"),
            "commercial_verdict": ch.get("commercial_verdict"),
            "scores": scores,
            "publish_recommendation": publish.get("recommendation") if isinstance(publish, dict) else None,
            "gating_recommendation": final_review.get("gating_recommendation") if isinstance(final_review, dict) else None,
        },
        "checkpoint": {
            "present": cp is not None,
            "path": f"registry/derived/serial-checkpoints/cp-{index:03d}.json" if cp is not None else None,
            "m7_risk_level": (m7 or {}).get("risk_level") if isinstance(m7, dict) else None,
            "m7_recommendation": (m7 or {}).get("recommendation") if isinstance(m7, dict) else None,
        },
        "human": {
            "review_notes": None,
            "edit_minutes": None,
            "labels": [],
            "accidents": [],
        },
        "facts": {
            "w12_candidates": None,
            "approval_status": None,
            "minted": None,
            "consumed_next_chapter": None,
        },
        "message": ch.get("message"),
    }


def load_checkpoints(project_path: str | Path) -> Dict[int, dict]:
    root = Path(project_path) / "registry" / "derived" / "serial-checkpoints"
    out: Dict[int, dict] = {}
    if not root.is_dir():
        return out
    for path in sorted(root.glob("cp-*.json")):
        data = _load_json(path)
        if not data:
            continue
        idx = data.get("chapter_index")
        if idx is None:
            # cp-010.json -> 10
            try:
                idx = int(path.stem.split("-", 1)[1])
            except (IndexError, ValueError):
                continue
        out[int(idx)] = data
    return out


def build_chapter_evidence_ledger(
    *,
    project_path: str | Path,
    run_manifest: dict | None = None,
    run_manifest_path: str | Path | None = None,
    protocol: dict | None = None,
) -> dict:
    """Fold one run into a homogeneous chapter evidence ledger."""
    project_path = Path(project_path)
    if run_manifest is None:
        if run_manifest_path is None:
            raise ValueError("run_manifest or run_manifest_path is required")
        run_manifest = _load_json(Path(run_manifest_path))
        if run_manifest is None:
            raise FileNotFoundError(f"run manifest not found: {run_manifest_path}")

    checkpoints = load_checkpoints(project_path)
    chapters = run_manifest.get("chapters") or []
    rows = [_chapter_row(ch, checkpoints_by_index=checkpoints)
            for ch in chapters if isinstance(ch, dict)]
    rows = sorted(rows, key=lambda r: r.get("chapter_index") or 0)

    totals = run_manifest.get("totals") or {}
    ledger = {
        "kind": LEDGER_KIND,
        "version": LEDGER_VERSION,
        "run_id": run_manifest.get("id") or run_manifest.get("run"),
        "project_path": str(project_path),
        "gating": run_manifest.get("gating", False),
        "protocol_id": (protocol or {}).get("protocol_id"),
        "protocol_content_hash": (protocol or {}).get("content_hash"),
        "run_totals": {
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
        "field_consumers": {
            "quality": "human review + selection diagnostics (never sole gate)",
            "cost": "budget / resume billing audit",
            "human": "manual labels filled at checkpoint reviews",
            "facts": "W12 stage → approval → mint → next-chapter consumption",
            "hashes": "winner / draft / state provenance integrity",
        },
    }
    body = {k: v for k, v in ledger.items() if k != "content_hash"}
    # Repo-wide convention is a "sha256:"-prefixed digest (chapter-ir, scene-plan,
    # character-runtime, release-package all pin it). serialization_utils
    # .content_hash returns a BARE hexdigest and is shared by 10+ modules, so the
    # prefix is applied here rather than changing every other artifact's hash.
    ledger["content_hash"] = "sha256:" + content_hash(body)
    return ledger


def write_chapter_evidence_ledger(path: str | Path, ledger: dict) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(dump_pretty_json(ledger) + "\n", encoding="utf-8")
    return out


def build_and_write_from_project(
    *,
    project_path: str | Path,
    run_id: str = "RUN-00025",
    out_path: str | Path | None = None,
    protocol: dict | None = None,
) -> dict:
    project_path = Path(project_path)
    manifest_path = project_path / "registry" / "derived" / "run-manifests" / f"{run_id}.json"
    ledger = build_chapter_evidence_ledger(
        project_path=project_path,
        run_manifest_path=manifest_path,
        protocol=protocol,
    )
    if out_path is None:
        out_path = project_path / "analysis" / f"{run_id.lower()}-chapter-evidence-ledger.json"
    write_chapter_evidence_ledger(out_path, ledger)
    return ledger
