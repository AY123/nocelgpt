"""orchestrate.py — the `genesis` end-to-end book opening (ANES v2, M2 / Phase 8).

One call that turns reference sources + preference into a PRODUCIBLE project:

    outline bootstrap    -> final-outline.json + import-plan.json (existing)
    fold Novel Brain     -> sources/novel-brain.yaml            (G.6, deterministic)
    fold Market Position -> sources/market-position.yaml        (M2-B3, deterministic)
    run admission        -> registry/derived/market-admission/  (M2-B3, advisory)
    land the batch       -> events/characters/world via mint     (G.4, --confirm only)

DISCIPLINE:
  - Stitches EXISTING pieces; it invents no new write path. Facts are landed only
    through runtime/mint/genesis_apply (guard #16); the Brain is an authored source.
  - PREVIEW by default: without confirm it produces the outline + Brain draft and
    a preview of what WOULD be minted, writing no facts (ADR-009). `confirm=True`
    crosses the boundary and lands the candidates.
  - Brain never clobbers an author's hand-written one unless overwrite is set.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..outline.workflow import run_outline_bootstrap
from ..mint import preview_genesis, execute_genesis, MintRefused
from ..approval import (
    ApprovalDecision,
    ApprovalQueue,
    create_approval_request,
    load_approval_queue,
    record_approval_decision,
)
from .brain_gen import build_brain, write_brain
from ..long_arc.plan import build_long_arc_plan, write_long_arc_plan


@dataclass
class GenesisResult:
    ok: bool
    stage: str
    message: str = ""
    outline_id: Optional[str] = None
    brain_path: Optional[str] = None
    brain_written: bool = False
    reference_abstract_path: Optional[str] = None
    long_arc_path: Optional[str] = None
    position_path: Optional[str] = None
    position_written: bool = False
    admission_id: Optional[str] = None
    admission_recommendation: Optional[str] = None
    admission_rationale: Optional[str] = None
    events_planned: int = 0
    landed: bool = False
    receipt_id: Optional[str] = None
    minted_count: int = 0
    preview_count: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def _load_json(project: Path, rel: str) -> dict:
    return json.loads((project / rel).read_text(encoding="utf-8"))


def run_genesis(
    project_path: str | Path,
    *,
    schema_dir: str | Path,
    standard_root: Optional[str | Path] = None,
    confirm: bool = False,
    overwrite_brain: bool = False,
    run_id: Optional[str] = None,
    actor: Optional[str] = None,
    model=None,
) -> GenesisResult:
    """Open a book. Returns a GenesisResult; never raises for an expected refusal
    (a missing Brain slot, an unconfirmed run) — those are reported as stages.

    Deterministic through the outline + Brain fold; the only irreversible step is
    the mint, which runs only when confirm=True (ADR-009)."""
    project = Path(project_path)

    # --- 1. outline bootstrap (writes final-outline.json + import-plan.json) ---
    # A live model authors the original settings (candidates/characters/world);
    # None keeps the deterministic template path. The mint below is untouched
    # either way — the model touches outline authorship only, never the fact
    # writer (ADR-009 / fitness #23).
    boot = run_outline_bootstrap(project, run_id=run_id, model=model)
    if not boot.ok:
        return GenesisResult(ok=False, stage=f"outline:{boot.stage}",
                             message=boot.message, errors=boot.errors or [])
    outline = _load_json(project, boot.outline_json)
    import_plan = _load_json(project, boot.import_plan_json)
    reference_abstract = outline.get("provenance", {}).get("reference_abstract")
    if isinstance(reference_abstract, dict):
        result_reference_abstract_path = reference_abstract.get("path") or reference_abstract.get("id")
    else:
        result_reference_abstract_path = None
    events_planned = sum(1 for it in import_plan.get("items", [])
                         if it.get("target_type") == "Event")

    result = GenesisResult(
        ok=True, stage="outline-done", outline_id=outline.get("id"),
        events_planned=events_planned)
    result.reference_abstract_path = result_reference_abstract_path
    if isinstance(reference_abstract, dict):
        result.message = reference_abstract.get("id", "reference abstraction ready")

    # --- 2. fold a Novel Brain draft (deterministic; authored source) ----------
    try:
        brain = build_brain(outline)
        path = write_brain(project, brain, standard_root=standard_root,
                           overwrite=overwrite_brain)
        result.brain_path = str(path.relative_to(project))
        result.brain_written = True
    except FileExistsError:
        # an authored Brain already exists — respect it (the human's hand wins)
        from ..brain.loader import brain_path as _bp
        result.brain_path = str(_bp(project).relative_to(project))
        result.brain_written = False
    except ValueError as exc:
        # a folded Brain that fails schema is a real defect — surface it, but the
        # outline + import plan already succeeded, so genesis is not aborted.
        result.errors.append(f"brain: {exc}")

    # --- 2b. fold a Market Position + run the pre-book admission (M2-B3) --------
    # The positioning generator + admission fold already existed but nothing on
    # the open-book path invoked them (built≠live): project_admission always
    # degraded to 'hold — no positioning authored'. Genesis now folds a
    # deterministic Position from the same outline, then runs admission over
    # Position+Brain+Snapshot and pins the advisory verdict. Never gates
    # (ADR-003); the verdict rides into the approval context so the human opening
    # the book (ADR-009) sees admit/revise/hold. A hand-authored Position is
    # respected (no clobber). Failures are surfaced, never abort genesis.
    from ..positioning import (build_position, write_position, project_admission,
                               write_admission)
    try:
        position = build_position(outline)
        ppath = write_position(project, position, standard_root=standard_root,
                               overwrite=overwrite_brain)
        result.position_path = str(ppath.relative_to(project))
        result.position_written = True
    except FileExistsError:
        from ..positioning import position_path as _pp
        result.position_path = str(_pp(project).relative_to(project))
        result.position_written = False
    except ValueError as exc:
        result.errors.append(f"position: {exc}")
    try:
        admission = project_admission(project, standard_root=standard_root)
        write_admission(project, admission)
        result.admission_id = admission.get("id")
        result.admission_recommendation = admission.get("recommendation")
        result.admission_rationale = admission.get("rationale")
    except Exception as exc:  # admission is advisory — never abort genesis
        result.errors.append(f"admission: {exc}")

    # --- 2c. derive a long-arc plan (M3) --------------------------------------
    try:
        long_arc_plan = build_long_arc_plan(
            outline,
            brain=brain if "brain" in locals() else None,
            market_position=position if "position" in locals() else None,
            event_skeleton=import_plan,
        )
        lpath = write_long_arc_plan(project, long_arc_plan.to_dict())
        result.long_arc_path = str(lpath.relative_to(project))
    except Exception as exc:
        result.errors.append(f"long_arc: {exc}")

    # --- 3. land the batch (ADR-009: preview by default, mint on --confirm) -----
    approval_queue = load_approval_queue(project)
    approval_request = create_approval_request(
        request_id=f"APR-{outline.get('id', '00001')}",
        target_type="genesis",
        target_id=outline.get("id", "OUTLINE-00001"),
        action="confirm_genesis",
        reason="book opening requires human approval",
        requested_by={"module": "genesis.orchestrate", "run_id": run_id or ""},
        context={
            "outline_id": outline.get("id"),
            "events_planned": events_planned,
            # Surface the advisory admission verdict so the human deciding whether
            # to open the book (ADR-009) sees admit/revise/hold at the queue.
            "admission_recommendation": result.admission_recommendation,
            "admission_rationale": result.admission_rationale,
        },
    )
    approval_queue.enqueue(approval_request)
    if not confirm:
        try:
            id_map, _staged, report = preview_genesis(
                project_path=str(project), plan=import_plan, schema_dir=schema_dir)
            result.preview_count = len(id_map)
            result.stage = "preview"
            result.message = (f"would mint {len(id_map)} candidate(s); "
                              f"re-run with --confirm to land them")
            if not report.ok:
                result.errors.extend(
                    str(f) for f in report.findings if f.severity == "error")
        except MintRefused as exc:
            result.errors.append(f"preview: {exc}")
            result.stage = "preview-refused"
        return result

    try:
        record_approval_decision(
            approval_queue,
            request_id=approval_request.id,
            decision=ApprovalDecision.APPROVED,
            decided_by=actor or "human",
            notes="genesis confirmed",
        )
        receipt = execute_genesis(
            project_path=str(project), plan=import_plan, schema_dir=schema_dir,
            confirmed=True, actor=actor)
        result.landed = True
        result.receipt_id = receipt["id"]
        result.minted_count = len(receipt["landed"])
        result.stage = "landed"
        result.message = (f"opened book {outline.get('id')}: minted "
                          f"{result.minted_count} fact(s), {events_planned} events")
    except MintRefused as exc:
        result.ok = False
        result.stage = "mint-refused"
        result.errors.append(str(exc))
    return result
