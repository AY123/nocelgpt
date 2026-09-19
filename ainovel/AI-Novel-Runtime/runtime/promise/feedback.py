"""feedback.py — Promise feedback to generation (Stage B.3).

Closes the loop: detected promises flow back into chapter generation via
Director objectives. The Director sees which promises need to be delivered,
and the generation prompt includes them as constraints.

DISCIPLINE:
  - Read-only: never writes facts, never modifies the ledger
  - Advisory: suggestions for generation, never gates (ADR-003)
  - Deterministic: same ledger + chapter => same feedback
"""
from __future__ import annotations

from typing import List, Optional

from .ledger import PromiseLedger, PromiseEntry


def pending_promises_for_chapter(ledger: PromiseLedger, chapter: int,
                                 *, lookahead: int = 0) -> List[PromiseEntry]:
    """Return promises that should be considered for this chapter.

    Args:
        ledger: The promise ledger
        chapter: Current chapter number (1-based)
        lookahead: Include promises due in next N chapters (default 0)

    Returns:
        List of promises that should be delivered in this chapter or soon.
    """
    candidates = []

    for promise in ledger.promises:
        if promise.status != "open":
            continue

        # Promises with deadlines
        if promise.must_deliver_by is not None:
            # Due this chapter
            if promise.must_deliver_by == chapter:
                candidates.append(promise)
            # Due soon (within lookahead window)
            elif lookahead > 0 and chapter < promise.must_deliver_by <= chapter + lookahead:
                candidates.append(promise)

    return candidates


def overdue_promises_for_chapter(ledger: PromiseLedger, chapter: int) -> List[PromiseEntry]:
    """Return promises that are overdue at this chapter.

    These are high-priority items that should have been delivered already.
    """
    return ledger.overdue_promises(chapter)


def render_promise_brief(promises: List[PromiseEntry], *,
                         context: str = "delivery") -> str:
    """Render promises as a brief text block for prompts.

    Args:
        promises: List of promises to render
        context: "delivery" (for generation) or "reminder" (for review)

    Returns:
        Formatted text block, or empty string if no promises.
    """
    if not promises:
        return ""

    lines = []

    # Group by level
    critical = [p for p in promises if p.level == "critical"]
    important = [p for p in promises if p.level == "important"]
    optional = [p for p in promises if p.level == "optional"]

    if context == "delivery":
        if critical:
            lines.append("【必须兑现的承诺】（影响读者留存）")
            for p in critical:
                evidence = f"证据词: {', '.join(p.evidence_terms[:3])}" if p.evidence_terms else ""
                deadline = f"(截止第{p.must_deliver_by}章)" if p.must_deliver_by else ""
                lines.append(f"  • {p.statement} {evidence} {deadline}")

        if important:
            if critical:
                lines.append("")
            lines.append("【应兑现的伏笔】")
            for p in important:
                deadline = f"(第{p.created_at_chapter}章埋下)" if p.created_at_chapter else ""
                lines.append(f"  • {p.statement} {deadline}")

        if optional and len(promises) <= 5:  # Only show optional if list is short
            if critical or important:
                lines.append("")
            lines.append("【可选的线索】")
            for p in optional[:3]:  # Max 3 optional
                lines.append(f"  • {p.statement}")

    elif context == "reminder":
        for p in promises:
            level_mark = "⚠️" if p.level == "critical" else "•"
            lines.append(f"{level_mark} {p.statement} ({p.type}, 第{p.created_at_chapter}章)")

    return "\n".join(lines)


def inject_promises_into_objective(objective: dict, ledger: PromiseLedger,
                                   chapter: int) -> dict:
    """Inject promise information into a ChapterObjective.

    Modifies the objective dict in-place by adding promise-related fields.
    This is called during objective construction.

    Args:
        objective: The chapter objective dict (being built)
        ledger: The promise ledger
        chapter: Current chapter number

    Returns:
        The modified objective dict (for chaining)
    """
    # Find relevant promises
    pending = pending_promises_for_chapter(ledger, chapter, lookahead=2)
    overdue = overdue_promises_for_chapter(ledger, chapter)

    # Add promise_to_deliver field (for backward compatibility)
    # This is the existing field that Director already has
    if pending or overdue:
        all_relevant = overdue + pending
        # Keep existing promise_to_deliver format (list of strings)
        objective["promise_to_deliver"] = [p.statement for p in all_relevant[:5]]
    else:
        objective["promise_to_deliver"] = []

    # Add structured promise references (new field, optional)
    # This allows Director to access full promise details if needed
    if pending or overdue:
        objective["promise_refs"] = [
            {
                "id": p.id,
                "type": p.type,
                "statement": p.statement,
                "level": p.level,
                "deadline": p.must_deliver_by,
                "overdue": p in overdue,
            }
            for p in (overdue + pending)[:5]
        ]
    else:
        objective["promise_refs"] = []

    # Add to constraints if there are critical promises
    critical_promises = [p for p in (overdue + pending) if p.level == "critical"]
    if critical_promises and "constraints" in objective:
        constraints = list(objective.get("constraints", []))
        promise_constraint = f"本章必须兑现 {len(critical_promises)} 个包装承诺"
        if promise_constraint not in constraints:
            constraints.append(promise_constraint)
        objective["constraints"] = constraints

    return objective


def render_promise_brief_for_prompt(ledger: PromiseLedger, chapter: int) -> str:
    """Render a promise brief suitable for inclusion in generation prompts.

    This is what gets injected into the chapter prompt to guide generation.
    """
    pending = pending_promises_for_chapter(ledger, chapter, lookahead=2)
    overdue = overdue_promises_for_chapter(ledger, chapter)

    if not pending and not overdue:
        return ""

    # Prioritize overdue
    if overdue:
        brief_lines = ["# 逾期未兑的承诺（高优先级）", ""]
        brief_lines.append(render_promise_brief(overdue, context="delivery"))
        brief_lines.append("")

    if pending:
        if not overdue:
            brief_lines = ["# 本章应兑现的承诺", ""]
        else:
            brief_lines.append("# 本章应兑现的承诺")
            brief_lines.append("")
        brief_lines.append(render_promise_brief(pending, context="delivery"))

    return "\n".join(brief_lines)


def verify_promise_delivery(draft_body: str, promise: PromiseEntry) -> dict:
    """Verify if a promise was delivered in the draft.

    This is a simple evidence-term based check. Returns a dict with:
    - delivered: bool
    - evidence_found: list of terms found
    - confidence: str (high/medium/low)

    Note: This is deterministic but simplistic. A future enhancement could
    use an LLM to verify semantic delivery.
    """
    if not promise.evidence_terms:
        # No evidence terms means we can't verify automatically
        return {
            "delivered": None,
            "evidence_found": [],
            "confidence": "unknown",
            "note": "No evidence terms specified",
        }

    body_lower = draft_body.lower()
    found_terms = [
        term for term in promise.evidence_terms
        if term.lower() in body_lower
    ]

    delivered = len(found_terms) > 0
    total_terms = len(promise.evidence_terms)
    found_count = len(found_terms)

    if found_count == 0:
        confidence = "low"
    elif found_count >= total_terms * 0.5:
        confidence = "high"
    else:
        confidence = "medium"

    return {
        "delivered": delivered,
        "evidence_found": found_terms,
        "evidence_total": total_terms,
        "confidence": confidence,
    }


def promise_delivery_report(ledger: PromiseLedger, chapter: int,
                           draft_body: str) -> dict:
    """Generate a report on promise delivery for this chapter.

    Checks all relevant promises against the draft and returns a summary.
    """
    pending = pending_promises_for_chapter(ledger, chapter)
    overdue = overdue_promises_for_chapter(ledger, chapter)
    all_relevant = overdue + pending

    results = []
    for promise in all_relevant:
        verification = verify_promise_delivery(draft_body, promise)
        results.append({
            "promise": promise.to_dict(),
            "verification": verification,
        })

    delivered_count = sum(1 for r in results if r["verification"]["delivered"])
    high_confidence = sum(
        1 for r in results
        if r["verification"]["delivered"] and r["verification"]["confidence"] == "high"
    )

    return {
        "chapter": chapter,
        "total_relevant": len(all_relevant),
        "delivered": delivered_count,
        "high_confidence": high_confidence,
        "overdue_count": len(overdue),
        "results": results,
        "summary": (
            f"{delivered_count}/{len(all_relevant)} 承诺已兑现 "
            f"({high_confidence} 高置信度)"
            if all_relevant else "无待兑承诺"
        ),
    }
