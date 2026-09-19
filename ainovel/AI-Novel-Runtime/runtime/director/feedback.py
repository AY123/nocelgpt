"""feedback.py — cross-chapter director feedback (Phase 7.3).

The step that makes the director LEARN across a serial: chapter N+1's objective
is shaped by chapter N's REALIZED signals, not planned in a vacuum. This is a
PURE DETERMINISTIC FOLD — the same previous-chapter signals always yield the same
adjustment — so it adds no nondeterminism and stays reproducible (ADR-001/005).

It is ADVISORY and NEVER gates (ADR-003): it nudges the next chapter's retention
focus / drop-risk target / payoff emphasis; it does not fail a chapter. And it
touches PROSE INTENT only — it never writes facts, so the state fold (ADR-008) is
unchanged whether or not feedback fires.

CRITICAL compatibility property: when the previous chapter shows NO adverse signal
(a plain deterministic run: verdict None, commercial None, pacing insufficient,
no dangling backlog), the feedback returns EXACTLY the defaults
build_chapter_objective already uses — so a plain serial run's objectives are
byte-identical with or without feedback. Feedback only diverges the objective when
a REAL adverse signal (a declining reviewer verdict, a regressed commercial loop,
a flat pacing curve, a growing setup backlog) appears.
"""
from __future__ import annotations

from typing import Any, Optional

# The neutral baseline — MUST match build_chapter_objective's own defaults so a
# no-signal run is byte-identical.
_DEFAULT_RETENTION = "next_chapter_pull"
_DEFAULT_PAYOFF = "partial_payoff"
_DEFAULT_DROP_RISK = "low"

# Setup backlog above this many open (unresolved) setups is treated as a signal
# that the next chapter should start paying threads off.
_BACKLOG_THRESHOLD = 3


def build_director_feedback(prev_run: Optional[dict]) -> Optional[dict]:
    """Fold the previous chapter's realized signals into an adjustment dict shaped
    for build_chapter_objective's `commercial=` parameter (retention_focus /
    payoff_type / drop_risk_target + a rationale trail). Returns None when there is
    no previous chapter (chapter 1) — so the opening chapter is unaffected.

    `prev_run` is a dict of the previous ChapterRun's signals:
      verdict            — the reviewer's quality verdict (regressed/degraded => adverse)
      commercial_verdict — the commercial loop's verdict (regressed => adverse)
      pacing             — the intra-chapter emotion-curve check (flat/front_loaded => adverse)
      open_setups        — count of unresolved setups (backlog pressure)
    """
    if not prev_run:
        return None

    retention = _DEFAULT_RETENTION
    payoff = _DEFAULT_PAYOFF
    drop_risk = _DEFAULT_DROP_RISK
    rationale: list[str] = []

    verdict = prev_run.get("verdict")
    commercial_verdict = prev_run.get("commercial_verdict")
    if verdict in ("regressed", "degraded"):
        retention = "strong_recovery_hook"
        drop_risk = "low"
        rationale.append(f"上一章质量判定为 {verdict}，本章强化留存与开篇钩子以挽回读者")
    if commercial_verdict == "regressed":
        retention = "strong_recovery_hook"
        rationale.append("上一章商业优化判定为 regressed，本章优先追读动力")

    # Pacing: a flat or front-loaded curve last chapter => push the payoff harder.
    pacing = prev_run.get("pacing") or {}
    findings = pacing.get("findings") or []
    shapes = " ".join(f.get("check", "") + " " + f.get("message", "") for f in findings)
    if any(k in shapes for k in ("flat", "monotone", "front", "平", "前置")):
        payoff = "clear_payoff"
        rationale.append("上一章情绪曲线偏平/前置，本章给出更明确的回报")

    # Setup backlog: too many open threads => the next chapter should resolve some.
    open_setups = prev_run.get("open_setups") or 0
    if isinstance(open_setups, int) and open_setups > _BACKLOG_THRESHOLD:
        payoff = "clear_payoff"
        rationale.append(f"未回收铺垫已达 {open_setups} 条，本章优先兑现部分线索")

    return {
        "retention_focus": retention,
        "payoff_type": payoff,
        "drop_risk_target": drop_risk,
        "rationale": rationale,
    }


def prev_run_signals(chapter_run: Any) -> dict:
    """Extract the signals feedback reads from a ChapterRun (dataclass or dict).
    Keeps the fold input explicit and small, so what feedback depends on is
    visible and testable."""
    def g(name, default=None):
        if isinstance(chapter_run, dict):
            return chapter_run.get(name, default)
        return getattr(chapter_run, name, default)
    return {
        "verdict": g("verdict"),
        "commercial_verdict": g("commercial_verdict"),
        "pacing": g("pacing"),
        "open_setups": g("open_setups", 0),
    }
