"""run_manifest.py — persist one serial run as an audit record (roadmap 5.5).

`run_serial` returns a rich in-memory SerialResult that, before this module, was
printed and discarded. This folds that result + the persisted draft envelopes
into a ProductionRunManifest (contracts/production-run-manifest.schema.json) and
writes it under registry/derived/run-manifests/.

DISCIPLINE:
  - READS only; writes to registry/derived/, never facts (ADR-006, guard #10 —
    runtime/serialize/ is not a fact-writer). The manifest is an audit record.
  - NEVER gates (ADR-003): `gating` const false.
  - The cost/model-call data is FOLDED from each produced chapter's persisted
    `draft.produced_by.llm` block — no plumbing into run_serial. It exists only
    for LIVE-model chapters; a deterministic-stub run records cost null and
    live_calls 0 (the stub sets no token/cost metadata — costs are never faked).
  - NOT byte-reproducible by design (embeds timestamps + live cost), exactly like
    the build manifest. The DRAFTS it records are reproducible; this record is not.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .. import derived
from ..llm.cost_fold import CostFold

CATEGORY = "run-manifests"
MANIFEST_VERSION = "1.0"

def next_run_id(existing_ids: List[str]) -> str:
    """Next RUN-##### id given the ids already present. Deterministic."""
    nums = [int(i.split("-", 1)[1]) for i in existing_ids
            if i.startswith("RUN-") and i.split("-", 1)[1].isdigit()]
    return f"RUN-{(max(nums) + 1) if nums else 1:05d}"


def _existing_run_ids(project_path) -> List[str]:
    indexed = {
        entry["id"]
        for entry in derived._load_index(project_path).get("artifacts", [])
        if entry.get("category") == CATEGORY and entry.get("id")
    }
    on_disk = {path.stem for path in derived.derived_dir(project_path, CATEGORY).glob("RUN-*.json")}
    return sorted(indexed | on_disk)


def _load_envelope(project_path, task_id: str) -> Optional[dict]:
    """Load a produced chapter's persisted draft envelope by its task_id (the
    draft's derived-artifact id). Returns None if absent or unreadable — the
    manifest degrades to the SerialResult fields rather than failing."""
    for e in derived._load_index(project_path).get("artifacts", []):
        if e.get("category") == "drafts" and e.get("id") == task_id:
            p = Path(project_path) / e["path"]
            if not p.exists():
                return None
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                return None
    return None


def _load_chapter_final(project_path, task_id: str) -> Optional[dict]:
    """Load the chapter-final derived artifact for a chapter, if present."""
    for e in derived._load_index(project_path).get("artifacts", []):
        if e.get("category") == "chapter-final" and e.get("id") == f"final-{task_id}":
            p = Path(project_path) / e["path"]
            if not p.exists():
                return None
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                return None
    return None


def _fold_llm(envelope: Optional[dict]) -> Optional[dict]:
    """Fold a chapter's model-call record from its envelope's
    draft.produced_by.llm. None when the chapter was skipped, the envelope is
    missing, or a deterministic stub produced it (no llm block)."""
    if not envelope:
        return None
    llm = (envelope.get("draft", {}).get("produced_by", {}) or {}).get("llm")
    if not llm:
        return None
    return {
        "model": llm.get("model"),
        "provider": llm.get("provider"),
        "token_usage": llm.get("token_usage") or {},
        "cost": llm.get("cost"),
        "latency_ms": llm.get("latency_ms"),
        "response_hash": llm.get("response_hash"),
        "replay_ref": llm.get("replay_ref"),
    }


def _output_path(project_path, task_id: str) -> Optional[str]:
    for e in derived._load_index(project_path).get("artifacts", []):
        if e.get("category") == "drafts" and e.get("id") == task_id:
            return e.get("path")
    return None


def build_run_manifest(
    *,
    project_path,
    result,
    run_id: str,
    params: Optional[dict] = None,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
) -> dict:
    """Fold a SerialResult + the persisted draft envelopes into a manifest dict.

    Pure aside from reading envelopes off disk (the drafts the run just wrote).
    Costs/tokens are summed from each produced chapter's produced_by.llm; a
    deterministic-stub run yields live_calls 0, token totals 0, cost null."""
    params = params or {}
    chapters = []
    live_calls = 0
    tok_in = tok_out = tok_total = 0
    # 成本折叠改由 CostFold 承担:它把"没调用模型"(确定性 stub,cost=null 正确)
    # 与"调用了但模型未定价"(真花了钱,cost 缺失是缺陷)分开计数。
    cost_fold = CostFold()

    for c in result.chapters:
        entry = {
            "index": c.spec.index,
            "task_id": c.spec.task_id,
            "event": c.spec.event_id,
            "ok": c.ok,
            "stage": c.stage,
            "message": c.message,
            "draft_hash": c.draft_hash,
            "state_hash": c.state_hash,
            "verdict": c.verdict,
            "commercial_verdict": c.commercial_verdict,
            "events_so_far": c.events_so_far,
            "open_setups": c.open_setups,
            "output_path": None,
            "llm": None,
            "publish_readiness": None,
        }
        if c.ok:
            envelope = _load_envelope(project_path, c.spec.task_id)
            chapter_final = _load_chapter_final(project_path, c.spec.task_id)
            entry["output_path"] = _output_path(project_path, c.spec.task_id)
            entry["publish_readiness"] = (envelope or {}).get("publish_readiness")
            entry["chapter_final"] = chapter_final
            # NOTE: prompt_provenance is deliberately NOT copied onto the chapter
            # entry. chapters.items is additionalProperties:false with no slot for
            # it (ADR-007). The provenance already lives on the draft envelope as a
            # sibling field, which is the authoritative route-evidence home; the
            # manifest pins the chapter by task_id, so it stays reachable there.
            llm = _fold_llm(envelope)
            if llm is not None:
                entry["llm"] = llm
                live_calls += 1
                tu = llm.get("token_usage") or {}
                tok_in += int(tu.get("input_tokens", tu.get("input", 0)) or 0)
                tok_out += int(tu.get("output_tokens", tu.get("output", 0)) or 0)
                tok_total += int(tu.get("total_tokens", tu.get("total", 0)) or 0)
                # 走 cost_fold:金额照加,但"有 token 用量却没成本"(模型未定价)
                # 会被数进 unpriced_calls。此前 `or 0` 把 None 静默折成 0,于是
                # 未定价模型的真实花费在 manifest 里也表现为 cost=null,与"确定性
                # stub 没花钱"完全无法区分。
                cost_fold.add(llm)
        chapters.append(entry)

    totals = {
        "planned": len(result.chapters),
        "produced": result.produced,
        "skipped": result.skipped,
        "final_state_hash": result.final_state_hash,
        "live_calls": live_calls,
        "token_usage": {"input": tok_in, "output": tok_out, "total": tok_total},
        # totals 与 totals.cost 都是 additionalProperties:false 的冻结契约,
        # 所以未定价计数不能塞进这里(ADR-007 / §1 Schema-First)。cost 的语义
        # 保持不变:折出过真实金额才给对象,否则 null。未定价告警走 rationale
        # 文案 + SerialResult.cost_warning(内存对象,不受校验)。
        "cost": ({"currency": cost_fold.currency or "USD",
                  "total_cost": round(cost_fold.total, 6)} if cost_fold.has_cost else None),
    }

    run_block = {
        "reviewer": result.reviewer,
        "prompt_version": params.get("prompt_version", "1.0.0"),
    }
    # NOTE: a params["selection_policy"] is deliberately NOT folded into run_block.
    # The run object is additionalProperties:false with no such slot (ADR-007). No
    # caller passes it today, so this was a latent violation that would have failed
    # schema validation the moment one did. The W9 policy is reachable via
    # build_w9_selection_policy(project_root) instead.
    for k in ("started_at", "finished_at", "commercial", "panel",
              "model_provider", "model_id", "max_chapters"):
        v = params.get(k)
        if k == "started_at":
            v = started_at if started_at is not None else v
        elif k == "finished_at":
            v = finished_at if finished_at is not None else v
        if v is not None:
            run_block[k] = v

    # "no live-model cost" 只在真的没调用模型时成立。有 live_calls 却折不出
    # 金额 = 模型未定价,钱是真花了的 —— 说成"无成本"会让熔断失效看不出来。
    if totals["cost"]:
        cost_note = f"cost {totals['cost']['total_cost']} {totals['cost']['currency']}"
    elif cost_fold.unpriced_calls:
        cost_note = (f"cost UNKNOWN: {cost_fold.unpriced_calls} unpriced live call(s) "
                     f"({', '.join(sorted(set(cost_fold.unpriced_models)))}) — not free")
    else:
        cost_note = "no live-model cost"
    return {
        "id": run_id,
        "kind": "production_run_manifest",
        "version": MANIFEST_VERSION,
        "gating": False,
        "run": run_block,
        "totals": totals,
        "chapters": chapters,
        "serial_pacing": result.serial_pacing,
        "rationale": (f"produced {result.produced}, skipped {result.skipped} "
                      f"of {len(result.chapters)}; {cost_note}"),
    }


def write_run_manifest(*, project_path, result, params=None,
                       started_at=None, finished_at=None) -> tuple:
    """Build + write the manifest as a derived artifact. Returns (manifest, rel_path)."""
    run_id = next_run_id(_existing_run_ids(project_path))
    manifest = build_run_manifest(
        project_path=project_path, result=result, run_id=run_id, params=params,
        started_at=started_at, finished_at=finished_at)
    rel = derived.write_artifact(
        project_path=project_path,
        category=CATEGORY,
        artifact_id=run_id,
        artifact=manifest,
        serialized=json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2),
    )
    return manifest, rel


def rebuild_segment_manifest(*, project_path, package_dir, start_chapter: int,
                             end_chapter: int, run_id: str, params=None,
                             started_at=None, finished_at=None) -> tuple:
    """Rebuild one immutable segment manifest from persisted chapter evidence."""
    from .loop import ChapterRun, ChapterSpec, SerialResult

    project = Path(project_path)
    packages = Path(package_dir)
    result = SerialResult(reviewer="serial-v1")
    for index in range(start_chapter, end_chapter + 1):
        task_id = f"TASK-{index:05d}"
        run_path = project / "registry" / "derived" / "chapter-run" / f"run-{task_id}.json"
        package_path = packages / f"{task_id}.package.json"
        chapter = json.loads(run_path.read_text(encoding="utf-8"))
        package = json.loads(package_path.read_text(encoding="utf-8"))
        task = package.get("task") or {}
        spec = ChapterSpec(
            index=index, task_id=task_id,
            event_id=str(chapter.get("event") or ""),
            seeds=list(task.get("seeds") or []), goal=str(task.get("goal") or ""),
            planning_source=(task.get("extra") or {}).get("planning_source"),
        )
        item = ChapterRun(
            spec=spec, ok=bool(chapter.get("ok")),
            stage=str(chapter.get("stage") or ""),
            message=str(chapter.get("message") or ""),
            draft_hash=chapter.get("draft_hash"), state_hash=chapter.get("state_hash"),
            open_setups=int(chapter.get("open_setups") or 0),
            events_so_far=int(chapter.get("events_so_far") or 0),
            verdict=chapter.get("verdict"),
            commercial_verdict=chapter.get("commercial_verdict"),
        )
        result.chapters.append(item)
        result.produced += int(item.ok)
        result.skipped += int(not item.ok)
        if item.state_hash:
            result.final_state_hash = item.state_hash
    manifest = build_run_manifest(
        project_path=project, result=result, run_id=run_id, params=params,
        started_at=started_at, finished_at=finished_at)
    rel = derived.write_artifact(
        project_path=project, category=CATEGORY, artifact_id=run_id,
        artifact=manifest,
        serialized=json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2))
    return manifest, rel
