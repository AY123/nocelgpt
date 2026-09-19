"""state.py — the unified Narrative State projection (ANES v2, M3-B5, ADR-008).

NarrativeState@N = fold(StoryState, persisted mandate/ir/chapter-run artifacts)

A pure read-side fold that consolidates the four fragmented narrative projections
into one advisory read surface. Never mutable, never a fact, never gates. Same
inputs => same projection (deterministic, byte-reproducible via content hash).

Exposes (each field is READ from an existing projection, never re-derived):
  main_conflict     — phase + pressure_level + latest escalation kind (from mandates)
  protagonist_arc   — dimension / from / to / cause (from the latest mandate)
  setup_payoff      — open + resolved setups, payoff_pressure (from StoryState)
  reader_questions  — the active open questions (from chapter-ir beats)
  emotional_curve   — recent peaks, temperature, fatigue_risk (from chapter-run pacing)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from ..execution.agent import _hash


def _load_category(project_path: str | Path, category: str) -> List[dict]:
    """Load all persisted derived artifacts of a category in stable id order.

    Reads the derived index (the same read pattern the dashboard sections use).
    Missing index / unreadable files degrade to an empty list — the projection
    simply folds fewer inputs, never raises."""
    from .. import derived
    try:
        entries = sorted(
            (e for e in derived._load_index(project_path).get("artifacts", [])
             if e.get("category") == category),
            key=lambda e: e.get("id", ""))
    except Exception:
        return []
    out: List[dict] = []
    for e in entries:
        path = Path(project_path) / e.get("path", "")
        if not path.exists():
            continue
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return out


# Escalation to_level (0-10, from the narrative mandate) maps to a coarse conflict
# PHASE. Deterministic bands; the phase is advisory narrative context, not a gate.
def _conflict_phase(to_level: Optional[int]) -> str:
    if to_level is None:
        return "unknown"
    if to_level <= 2:
        return "inciting"
    if to_level <= 5:
        return "escalation"
    if to_level <= 7:
        return "reversal"
    if to_level <= 9:
        return "climax"
    return "aftermath"


# Emotional temperature from the most recent pacing peak valence (0-100, from the
# chapter-run pacing check). Coarse bands, deterministic.
def _temperature(peak: Optional[int]) -> str:
    if peak is None:
        return "unknown"
    if peak >= 70:
        return "high"
    if peak >= 45:
        return "medium"
    return "low"


def _fatigue_risk(peaks: List[int]) -> str:
    """Emotional-curve fatigue from the recent peak sequence (deterministic).

    - too FLAT for a stretch (no peak reaches a climax) => reader boredom risk.
    - too HOT for a stretch (every recent chapter peaks high) => exhaustion risk.
    - otherwise low. Empty/short history => unknown (nothing to judge)."""
    recent = [p for p in peaks[-5:] if p is not None]
    if len(recent) < 3:
        return "unknown"
    if max(recent) < 55:
        return "high"          # a flat run of low-energy chapters
    if min(recent) >= 75:
        return "high"          # relentless high — no breathing room
    return "low"


# payoff_pressure from the open-setup backlog (from StoryState). The director's
# feedback fold already treats >3 open setups as a clear_payoff pressure signal
# (director/plan.py); keep the SAME threshold so the two agree.
def _payoff_pressure(open_count: int) -> str:
    if open_count <= 3:
        return "low"
    if open_count <= 7:
        return "medium"
    return "high"


@dataclass(frozen=True)
class NarrativeState:
    """A point-in-time unified narrative projection, folded from StoryState + the
    persisted per-chapter mandate/ir/run artifacts. `chapters_folded` is how many
    chapter-run artifacts were seen (the narrative "cursor")."""
    reviewer: str
    chapters_folded: int
    main_conflict: dict = field(default_factory=dict)
    protagonist_arc: dict = field(default_factory=dict)
    setup_payoff: dict = field(default_factory=dict)
    reader_questions: dict = field(default_factory=dict)
    emotional_curve: dict = field(default_factory=dict)
    reference_anchor: dict = field(default_factory=dict)
    gating: bool = False   # ADR-003 — advisory, never blocks

    def core(self) -> dict:
        """The hashed, replay-stable body (no reviewer label). Same inputs =>
        same core => same content hash."""
        return {
            "chapters_folded": self.chapters_folded,
            "main_conflict": self.main_conflict,
            "protagonist_arc": self.protagonist_arc,
            "setup_payoff": self.setup_payoff,
            "reader_questions": self.reader_questions,
            "emotional_curve": self.emotional_curve,
            "reference_anchor": self.reference_anchor,
        }

    @property
    def content_hash(self) -> str:
        return _hash(self.core())

    def to_dict(self) -> dict:
        d = {"reviewer": self.reviewer, "gating": self.gating,
             "content_hash": self.content_hash}
        d.update(self.core())
        return d


def _reader_questions_from_irs(irs: List[dict]) -> List[dict]:
    """Fold the per-chapter IR beats into the reader questions opened across the
    run, in chapter order, de-duplicated by question text (the first chapter that
    opens a question wins its opened_at). A question is 'active' until answered;
    we have no explicit answer signal in the IR, so we treat a later chapter's
    payoff_target promise that names/echoes the question as tentatively resolving
    it — otherwise it stays open. Deterministic, order-stable."""
    opened: Dict[str, dict] = {}
    for ir in irs:
        ch = ir.get("chapter_no")
        for beat in ir.get("beats", []) or []:
            q = (beat.get("reader_question") or "").strip()
            if q and q not in opened:
                opened[q] = {"question": q, "opened_at": ch}
    return list(opened.values())


def project_narrative_state(
    reg, project_path: str | Path, *,
    up_to_event: Optional[str] = None,
    reviewer_id: str = "narrative-state-v1",
) -> NarrativeState:
    """Fold StoryState + the persisted per-chapter narrative artifacts into one
    unified NarrativeState (ADR-008). Pure + deterministic: no model, no
    randomness; the only I/O is reading already-persisted derived artifacts.

    Each source degrades independently: a run with no mandates/irs/runs still
    yields a valid (sparser) projection — mirrors how the dashboard sections
    return None-safe blocks. Never mutates state, never writes facts."""
    from ..memory.state import project_state

    story = project_state(reg, up_to_event=up_to_event)
    mandates = _load_category(project_path, "narrative-mandate")
    irs = _load_category(project_path, "chapter-ir")
    runs = _load_category(project_path, "chapter-run")

    # --- main_conflict (from the escalation ladder in the mandates) ----------
    latest_mandate = mandates[-1] if mandates else {}
    esc = latest_mandate.get("escalation") or {}
    to_level = esc.get("to_level")
    main_conflict = {
        "phase": _conflict_phase(to_level),
        "pressure_level": to_level,          # 0-10 or None
        "latest_escalation_kind": esc.get("kind"),
        "ladder": [(m.get("escalation") or {}).get("to_level") for m in mandates],
    }

    # --- protagonist_arc (from the latest mandate's inner shift) --------------
    inner = latest_mandate.get("inner_shift") or {}
    protagonist_arc = {
        "dimension": inner.get("dimension"),
        "from": inner.get("from"),
        "to": inner.get("to"),
        "cause": inner.get("cause"),
    }

    # --- setup_payoff (from StoryState) + payoff_pressure --------------------
    open_count = len(story.open_setups)
    setup_payoff = {
        "open_setups": story.open_setups,
        "resolved_setups": story.resolved_setups,
        "open_count": open_count,
        "resolved_count": len(story.resolved_setups),
        "payoff_pressure": _payoff_pressure(open_count),
    }

    # --- reader_questions (from chapter-ir beats) -----------------------------
    active_questions = _reader_questions_from_irs(irs)
    reader_questions = {
        "active": active_questions,
        "active_count": len(active_questions),
    }

    # --- emotional_curve (from chapter-run pacing peaks) ----------------------
    peaks = [r.get("pacing_peak") for r in runs
             if r.get("pacing_peak") is not None]
    recent_peak = peaks[-1] if peaks else None
    recent_peak_chapter = None
    for r in runs:
        if r.get("pacing_peak") is not None:
            recent_peak_chapter = (r.get("spec") or {}).get("index")
    emotional_curve = {
        "peaks": peaks,
        "current_temperature": _temperature(recent_peak),
        "recent_peak_chapter": recent_peak_chapter,
        "fatigue_risk": _fatigue_risk(peaks),
    }

    from ..reference.abstract import load_reference_abstraction
    reference_anchor = load_reference_abstraction(project_path) or {}
    if reference_anchor:
        reference_anchor = {
            "id": reference_anchor.get("id"),
            "kind": reference_anchor.get("kind"),
            "market_positioning": reference_anchor.get("market_positioning", {}),
            "structural_patterns": reference_anchor.get("structural_patterns", {}),
            "commercial_cadence": reference_anchor.get("commercial_cadence", {}),
            "transferable_abstractions": reference_anchor.get("transferable_abstractions", []),
        }

    return NarrativeState(
        reviewer=reviewer_id,
        chapters_folded=len(runs),
        main_conflict=main_conflict,
        protagonist_arc=protagonist_arc,
        setup_payoff=setup_payoff,
        reader_questions=reader_questions,
        emotional_curve=emotional_curve,
        reference_anchor=reference_anchor,
    )


def narrative_state_artifact(reg, project_path: str | Path,
                             state: NarrativeState) -> dict:
    """Wrap a NarrativeState as a Derived Artifact (ADR-006/ADR-008). Pins the
    fact sources at their current fact_version so the stored projection inherits
    staleness for free (same discipline as state_artifact). `content_hash` is the
    projection's own hash, so the derived index keys on it like any artifact.

    Note the derived_from pins FACT sources; the narrative artifacts it also folds
    are themselves derived projections of those same facts, so pinning the facts
    is the correct staleness root (recomputing the fold re-reads them)."""
    derived_from = [f"{rid}@v{int(rec.get('fact_version', 0))}"
                    for rid, rec in sorted(reg.facts.items())]
    return {
        "artifact_format": "1.0",
        "kind": "narrative-state",
        "capability": "NarrativeState",
        "task_id": f"narrative-state-{state.chapters_folded}ch",
        "content_hash": state.content_hash,
        "provenance": {
            "derived_from": derived_from,
            "source_version": reg.version,
        },
        "state": state.core(),
    }

