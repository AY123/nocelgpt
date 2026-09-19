"""engine.py — the Derived Recompute Engine (ANES v2, roadmap Phase 5.3).

Analyzes which indexed derived artifacts a mint made stale, auto-rebuilds the
pure fact-folds, and stages the generative ones for human regeneration. Emits a
recompute-report. Not a fact-writer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .. import derived
from ..registry_loader import Registry, load as load_registry

REPORT_CATEGORY = "recompute-reports"
REPORT_VERSION = "1.0"


# --- rebuilder registry ------------------------------------------------------
# A category with a registered rebuilder is DETERMINISTIC: the rebuilder is a
# pure fold (reg -> artifact dict) that can be recomputed with no model and no
# cost. A category with NO rebuilder is treated as GENERATIVE: it is staged for
# a human, never auto-rebuilt. This registry is the whole deterministic/
# generative partition, in one auditable place.

# rebuilder: (reg, prev_artifact) -> new_artifact_dict (must carry provenance +
# content_hash, like every derived artifact).
Rebuilder = Callable[[Registry, dict], dict]
_REBUILDERS: Dict[str, Rebuilder] = {}

# The human command that regenerates a stale GENERATIVE artifact, by category.
# Descriptive only — the engine never runs it (ADR-009).
_REGEN_COMMAND: Dict[str, str] = {
    "drafts": "runtime execute --task <task> --capability ChapterDraft … (re-author the chapter, then re-review)",
    "quality": "runtime execute … / runtime refine …  (re-score the regenerated draft)",
    "quality-replay": "regenerated as a side effect of re-running the quality judge on a fresh draft",
    "reader-sim-replay": "runtime commercial … / runtime execute --reviewer panel  (re-simulate on a fresh draft)",
    "commercial-panel-replay": "runtime commercial …  (re-run the commercial panel on a fresh draft)",
    "commercial-loop-sim-replay": "runtime commercial …  (re-run the commercial loop on a fresh draft)",
    "commercial-loop-rewrite-replay": "runtime commercial …  (re-run the commercial rewrite on a fresh draft)",
    "panel-replay-commercial": "runtime execute --reviewer panel …",
    "panel-replay-literary": "runtime execute --reviewer panel …",
    "panel-replay-logic": "runtime execute --reviewer panel …",
    "panel-replay-structural": "runtime execute --reviewer panel …",
    "refine-replay-gen": "runtime refine …  (re-run the refine generation on current facts)",
    "refine-replay-rewrite": "runtime refine …  (re-run the refine rewrite)",
    "prompt-manifests": "regenerated as a side effect of re-running execute/refine",
    "prompt-cache": "regenerated as a side effect of re-running the prompt",
    "llm-replay": "regenerated as a side effect of re-running the model call",
}
_DEFAULT_REGEN = "regenerate via the capability that produced it (a model-backed step; a human authorizes it)"


def register_rebuilder(category: str, fn: Rebuilder) -> None:
    """Register a pure-fold rebuilder for a derived category. Presence in this
    registry is what makes a category DETERMINISTIC (auto-rebuildable)."""
    _REBUILDERS[category] = fn


def is_deterministic(category: str) -> bool:
    return category in _REBUILDERS


@dataclass
class ImpactItem:
    artifact_id: str
    category: str
    kind: str          # "deterministic" | "generative"
    staleness: str     # "direct" | "transitive"
    reason: str
    action: str = "staged"   # "rebuilt" | "staged"; set during execute

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "category": self.category,
            "kind": self.kind,
            "staleness": self.staleness,
            "action": self.action,
            "reason": self.reason,
        }


def analyze_impact(reg: Registry, project_path) -> List[ImpactItem]:
    """Walk the derived index and return one ImpactItem per STALE artifact.

    An artifact is stale (direct) when a fact it pins has advanced or vanished
    (derived.check_staleness). Its kind is deterministic iff its category has a
    registered rebuilder. PURE analysis: reads only, writes nothing."""
    index = derived._load_index(project_path)
    items: List[ImpactItem] = []
    for entry in index.get("artifacts", []):
        reasons = derived.check_staleness(reg, entry.get("derived_from", []))
        if not reasons:
            continue
        category = entry.get("category", "")
        items.append(ImpactItem(
            artifact_id=entry["id"],
            category=category,
            kind="deterministic" if is_deterministic(category) else "generative",
            staleness="direct",
            reason="; ".join(reasons),
        ))
    return items


def _index_entry(project_path, artifact_id: str) -> Optional[dict]:
    for e in derived._load_index(project_path).get("artifacts", []):
        if e.get("id") == artifact_id:
            return e
    return None


def _load_prev(project_path, entry: dict) -> dict:
    import json
    return json.loads((Path(project_path) / entry["path"]).read_text(encoding="utf-8"))


def _next_report_id(project_path) -> str:
    ids = []
    for e in derived._load_index(project_path).get("artifacts", []):
        if e.get("category") == REPORT_CATEGORY and e.get("id", "").startswith("RCP-"):
            tail = e["id"].split("-", 1)[1]
            if tail.isdigit():
                ids.append(int(tail))
    return f"RCP-{(max(ids) + 1) if ids else 1:05d}"


def _trigger_block(mint_receipt: Optional[dict]) -> dict:
    if mint_receipt is None:
        return {"kind": "scan"}
    advanced = [f"{m['entity_id']}@v{m['fact_version']['after']}"
                for m in mint_receipt.get("minted", [])]
    return {
        "kind": "mint",
        "mint_receipt_id": mint_receipt.get("id", ""),
        "advanced_entities": advanced,
    }


def recompute_plan(reg: Registry, project_path, *,
                   mint_receipt: Optional[dict] = None) -> dict:
    """Impact analysis WITHOUT writing anything — the preview. Returns a report
    dict whose `impacted` is populated and whose `rebuilt`/`staged` describe what
    execute WOULD do (action set, but nothing written)."""
    impact = analyze_impact(reg, project_path)
    rebuilt, staged = [], []
    for it in impact:
        if it.kind == "deterministic":
            it.action = "rebuilt"
            rebuilt.append({"artifact_id": it.artifact_id, "category": it.category})
        else:
            it.action = "staged"
            staged.append({
                "artifact_id": it.artifact_id, "category": it.category,
                "reason": it.reason,
                "regenerate_with": _REGEN_COMMAND.get(it.category, _DEFAULT_REGEN),
            })
    return _assemble_report("RCP-PREVIEW", impact, rebuilt, staged, mint_receipt,
                            previewed=True)


def execute_recompute(reg: Registry, project_path, *,
                      mint_receipt: Optional[dict] = None) -> dict:
    """Auto-rebuild every stale DETERMINISTIC fold (write back + fresh pin) and
    STAGE every stale GENERATIVE artifact. Emits + returns a recompute-report.
    Never writes facts; never regenerates a generative artifact."""
    impact = analyze_impact(reg, project_path)
    rebuilt: List[dict] = []
    staged: List[dict] = []

    for it in impact:
        if it.kind == "deterministic":
            entry = _index_entry(project_path, it.artifact_id)
            prev = _load_prev(project_path, entry) if entry else {}
            new_artifact = _REBUILDERS[it.category](reg, prev)
            serialized = _canonical(new_artifact)
            path = derived.write_artifact(
                project_path=project_path, category=it.category,
                artifact_id=it.artifact_id, artifact=new_artifact,
                serialized=serialized)
            it.action = "rebuilt"
            rebuilt.append({
                "artifact_id": it.artifact_id,
                "category": it.category,
                "content_hash": new_artifact.get("content_hash", ""),
                "content_hash_changed": new_artifact.get("content_hash")
                                        != (prev.get("content_hash") if prev else None),
                "path": path,
            })
        else:
            it.action = "staged"
            staged.append({
                "artifact_id": it.artifact_id, "category": it.category,
                "reason": it.reason,
                "regenerate_with": _REGEN_COMMAND.get(it.category, _DEFAULT_REGEN),
            })

    report_id = _next_report_id(project_path)
    report = _assemble_report(report_id, impact, rebuilt, staged, mint_receipt,
                              previewed=False)
    from ..serialize.serialization_utils import dump_pretty_json
    derived.write_artifact(
        project_path=project_path, category=REPORT_CATEGORY,
        artifact_id=report_id, artifact=report,
        serialized=dump_pretty_json(report))
    return report


def _assemble_report(report_id, impact, rebuilt, staged, mint_receipt, *,
                     previewed: bool) -> dict:
    n_rebuilt, n_staged = len(rebuilt), len(staged)
    rationale = (f"{'preview: would rebuild' if previewed else 'rebuilt'} "
                 f"{n_rebuilt} deterministic fold(s), "
                 f"{'would stage' if previewed else 'staged'} {n_staged} "
                 f"generative artifact(s) for human regeneration")
    return {
        "id": report_id,
        "kind": "recompute_report",
        "version": REPORT_VERSION,
        "authority": "human",
        "gating": False,
        "trigger": _trigger_block(mint_receipt),
        "impacted": [it.to_dict() for it in impact],
        "rebuilt": rebuilt,
        "staged": staged,
        "rationale": rationale,
    }


def _canonical(artifact: dict) -> str:
    from ..serialize.serialization_utils import dump_pretty_json
    return dump_pretty_json(artifact)


# --- registered rebuilders ---------------------------------------------------
# StoryState is the canonical pure fold: project_state(reg) folds facts+events
# into a projection, state_artifact pins every fact at its current version. A
# fact advance => stale => this rebuild writes it back fresh. No model, no cost.

def _rebuild_story_state(reg: Registry, prev: dict) -> dict:
    from ..memory.state import project_state, state_artifact
    up_to = None
    if prev:
        tid = prev.get("task_id", "")
        if tid.startswith("story-state-") and tid != "story-state-full":
            up_to = tid[len("story-state-"):]
    state = project_state(reg, up_to_event=up_to)
    return state_artifact(reg, state)


register_rebuilder("story-state", _rebuild_story_state)
