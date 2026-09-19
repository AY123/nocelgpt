"""commercial.py — Commercial Optimization Loop (ANES v2, roadmap P16).

Closes the commercial lane the North Star describes:

    draft --> simulate readers --> targeted rewrite --> re-simulate
          --> compare (retention / satisfaction / who newly drops)
          --> keep the rewrite ONLY if readers relatively improved

This is deliberately DISTINCT from the Revision Controller (revision.py):
  - revise_until optimizes 8 CRAFT dimensions toward an ABSOLUTE threshold.
  - THIS loop optimizes SIMULATED READER reaction and is strictly
    COMPARISON-ONLY (compare_simulations before/after) — the North Star
    discipline that reader signals are never an absolute truth.

Discipline (enforced here AND by commercial-session.schema.json):
  - gating = False, comparison_only = True are structural invariants. This loop
    can NEVER block a build (ADR-003); the deterministic gates still run on the
    selected draft via the normal execute path.
  - It selects a BETTER draft (by reader reaction) and never returns one worse
    than the input. Bounded: stops on no-improvement, max_rounds, or a degraded
    simulation. Never loops forever, never bills forever.

It reuses existing seams — revision.rewrite_once (the rewriter) and
reader_sim.compare_simulations (the relative comparator) — so it adds no new
scorer and no control-flow change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .reader_sim import compare_simulations, _is_number
from .revision import rewrite_once


@dataclass
class CommercialSession:
    controller: str
    rounds: List[dict] = field(default_factory=list)
    terminate_reason: str = "max_rounds"
    verdict: str = "unchanged"
    selected_draft_hash: str = ""
    gating: bool = False            # structural invariant — never blocks
    comparison_only: bool = True    # structural invariant — relative use only

    def to_dict(self) -> dict:
        return {
            "controller": self.controller,
            "gating": self.gating,
            "comparison_only": self.comparison_only,
            "terminate_reason": self.terminate_reason,
            "verdict": self.verdict,
            "selected_draft_hash": self.selected_draft_hash,
            "rounds": self.rounds,
        }


@dataclass
class CommercialResult:
    session: CommercialSession
    final_artifact: dict
    final_simulation: dict


def _round_is_regression(r: dict) -> bool:
    """A round counts as a regression for the session verdict if a reader newly
    DROPPED, or a pay loss occurred that was NOT tolerated by the softened rule
    (i.e. net panel付费意愿 did not rise). A tip dip absorbed by an overall pay
    gain is not a regression — the loop rejected it as a non-improvement, not a
    net-worse draft."""
    if r.get("degraded"):
        return False
    if r.get("newly_dropped"):
        return True
    if r.get("newly_pay_lost"):
        pay_delta = r.get("mean_pay_probability_delta")
        return not (_is_number(pay_delta) and pay_delta > 0)
    return False


def _check_quality_maintained(original_artifact: dict, revised_artifact: dict,
                               tolerance: int = 5) -> tuple:
    """Phase 5: Check if quality scores are maintained (allowing tolerance).

    Returns (maintained: bool, reason: str, details: dict)
    """
    original_scores = (original_artifact.get("qa_review") or {}).get("scores")
    revised_scores = (revised_artifact.get("qa_review") or {}).get("scores")

    if not original_scores or not revised_scores:
        # No scores to compare, assume maintained
        return True, "", {}

    key_dimensions = ["character_consistency", "world_consistency", "prose_quality"]
    degraded_dims = []

    for dim in key_dimensions:
        if dim not in original_scores or dim not in revised_scores:
            continue

        original_val = original_scores[dim]
        revised_val = revised_scores[dim]
        delta = revised_val - original_val

        if delta < -tolerance:
            degraded_dims.append({
                "dimension": dim,
                "original": original_val,
                "revised": revised_val,
                "delta": delta
            })

    if degraded_dims:
        dims_str = ", ".join(d["dimension"] for d in degraded_dims)
        return False, f"Quality degraded: {dims_str}", {"degraded_dimensions": degraded_dims}

    return True, "", {}


def _check_contract_maintained(original_artifact: dict, revised_artifact: dict,
                                contract_gate) -> tuple:
    """Phase 5: Check if contract compliance is maintained.

    Returns (maintained: bool, reason: str, details: dict)
    """
    if not contract_gate:
        # No gate to check with, assume maintained
        return True, "", {}

    try:
        # Get contract check results from artifacts if available
        original_contract = original_artifact.get("contract_check")
        revised_contract = revised_artifact.get("contract_check")

        if not original_contract or not revised_contract:
            # No contract checks available, assume maintained
            return True, "", {}

        original_critical = original_contract.get("critical_count", 0)
        revised_critical = revised_contract.get("critical_count", 0)
        original_high = original_contract.get("high_count", 0)
        revised_high = revised_contract.get("high_count", 0)

        if revised_critical > original_critical:
            return False, f"Critical deviations increased: {original_critical} → {revised_critical}", {
                "original_critical": original_critical,
                "revised_critical": revised_critical
            }

        if revised_high > original_high:
            return False, f"High severity deviations increased: {original_high} → {revised_high}", {
                "original_high": original_high,
                "revised_high": revised_high
            }

        return True, "", {}

    except Exception as e:
        # If check fails, log warning but don't block (advisory)
        import logging
        logging.warning(f"Contract maintenance check failed: {e}")
        return True, "", {}


def _check_hygiene_maintained(original_artifact: dict, revised_artifact: dict) -> tuple:
    """Phase 5: Check if prose hygiene is maintained.

    Returns (maintained: bool, reason: str, details: dict)
    """
    original_hygiene = original_artifact.get("hygiene_check")
    revised_hygiene = revised_artifact.get("hygiene_check")

    if not original_hygiene or not revised_hygiene:
        # No hygiene checks available, assume maintained
        return True, "", {}

    original_issues = original_hygiene.get("issue_count", 0)
    revised_issues = revised_hygiene.get("issue_count", 0)

    if revised_issues > original_issues:
        return False, f"Hygiene issues increased: {original_issues} → {revised_issues}", {
            "original_issues": original_issues,
            "revised_issues": revised_issues
        }

    return True, "", {}


def _reader_plan(simulation: dict) -> List[dict]:
    """Turn a reader simulation into a light revision plan for the rewriter:
    the drop reasons + common expectations become the 'what to fix' list. The
    rewriter (revision.rewrite_once) accepts any [{dimension,issue,action}]."""
    plan: List[dict] = []
    for p in simulation.get("personas", []):
        if p.get("degraded"):
            continue
        if not p.get("would_continue", True) and p.get("drop_reason"):
            plan.append({
                "dimension": "reader_retention",
                "issue": f"{p['name']} 会弃书：{p['drop_reason']}",
                "action": "针对该读者类型的弃书点做加强，提升追读意愿",
                "priority": "high",
            })
        # v2: a commercial persona that keeps reading but won't pay is a money
        # leak — feed its reason to the rewriter as its own fix, separate from
        # the弃书 case above.
        elif _is_number(p.get("pay_probability")) \
                and p["pay_probability"] < 50 and p.get("drop_reason"):
            plan.append({
                "dimension": "reader_monetization",
                "issue": f"{p['name']} 追读但不愿付费：{p['drop_reason']}",
                "action": "在付费点前兑现足够爽感/价值，提升该读者类型的付费意愿",
                "priority": "high",
            })
    for exp in simulation.get("aggregate", {}).get("common_expectations", [])[:3]:
        plan.append({
            "dimension": "reader_expectation",
            "issue": f"读者期待未被满足：{exp}",
            "action": f"在不违反设定的前提下回应该期待：{exp}",
            "priority": "medium",
        })
    return plan


def optimize_commercial(
    simulator,
    rewrite_model,
    artifact: dict,
    package: dict,
    *,
    max_rounds: int = 2,
    controller_id: str = "commercial-loop-v1",
    initial_sim: Optional[dict] = None,
    quality_guard: bool = True,  # Phase 5: enable quality non-degradation checks
    contract_gate = None,  # Phase 5: optional ContractGate for contract checks
) -> CommercialResult:
    """Iteratively rewrite + re-simulate readers, keeping a rewrite only when the
    reader comparison says it improved. Always returns the BEST draft seen
    (never worse than the input by reader reaction). Purely advisory — never
    gates (ADR-003).

    Accept rule (v2, softened): a rewrite is kept when readers relatively improved
    AND no reader newly DROPS (a lost reader is gone — hard veto). A persona newly
    losing PAY intent (newly_pay_lost) is a softer signal: the reader still reads,
    so it only vetoes when the NET panel pay probability did not rise. A single
    tip-driven persona dipping below the bar is tolerated when overall付费意愿 still
    climbed — losing a reader and losing a tip are not equally catastrophic. Still
    comparison-only, still never gates.

    The soft pay bar is read from the simulator (simulator.pay_bar) so the crossing
    detection matches the aggregation bar; falls back to the module default."""
    session = CommercialSession(controller=controller_id)
    pay_bar = getattr(simulator, "pay_bar", None)

    current = artifact
    sim = initial_sim or simulator.review(artifact, package).to_dict()
    best_artifact, best_sim = current, sim

    # A degraded baseline simulation gives us nothing to compare against.
    if sim.get("judge_provenance", {}).get("degraded"):
        session.terminate_reason = "degraded"
        session.verdict = "degraded"
        session.selected_draft_hash = current.get("content_hash", "")
        return CommercialResult(session, best_artifact, best_sim)

    for rnd in range(1, max_rounds + 1):
        revised = rewrite_once(rewrite_model, current, package, _reader_plan(sim))
        if revised is None:
            session.rounds.append({
                "round": rnd,
                "draft_hash_before": current.get("content_hash", ""),
                "draft_hash_after": current.get("content_hash", ""),
                "reader_verdict": "unchanged",
                "accepted": False, "degraded": True,
                "note": "rewrite model produced no usable prose",
            })
            session.terminate_reason = "degraded"
            break

        new_sim = simulator.review(revised, package).to_dict()
        if new_sim.get("judge_provenance", {}).get("degraded"):
            session.rounds.append({
                "round": rnd,
                "draft_hash_before": current.get("content_hash", ""),
                "draft_hash_after": revised.get("content_hash", ""),
                "reader_verdict": "unchanged",
                "accepted": False, "degraded": True,
                "note": "re-simulation degraded; keeping prior draft",
            })
            session.terminate_reason = "degraded"
            break

        cmp = (compare_simulations(sim, new_sim, pay_bar=pay_bar)
               if pay_bar is not None else compare_simulations(sim, new_sim))
        # Accept a relative improvement with NO reader newly dropping (a lost
        # reader is gone — hard veto). A persona newly losing PAY intent is
        # softer: they still read, so it only vetoes when NET panel付费意愿 did
        # not rise. A single tip-driven persona dipping below the bar is tolerated
        # when overall pay still climbed (mean_pay_probability_delta > 0). When
        # the panel reported no pay signal at all, the pay clause is vacuous and
        # this reduces to the v1 (satisfaction/retention) rule.
        # Phase 5: Add quality guard checks (quality, contract, hygiene).
        pay_delta = cmp.get("mean_pay_probability_delta")
        pay_ok = (not cmp["newly_pay_lost"]
                  or (_is_number(pay_delta) and pay_delta > 0))

        # Phase 5: Quality guard checks
        quality_maintained = True
        contract_maintained = True
        hygiene_maintained = True
        quality_veto_reason = ""

        if quality_guard:
            quality_maintained, quality_reason, quality_details = _check_quality_maintained(
                current, revised)
            contract_maintained, contract_reason, contract_details = _check_contract_maintained(
                current, revised, contract_gate)
            hygiene_maintained, hygiene_reason, hygiene_details = _check_hygiene_maintained(
                current, revised)

            if not quality_maintained:
                quality_veto_reason = quality_reason
            elif not contract_maintained:
                quality_veto_reason = contract_reason
            elif not hygiene_maintained:
                quality_veto_reason = hygiene_reason

        accepted = (cmp["verdict"] == "improved"
                    and not cmp["newly_dropped"]
                    and pay_ok
                    and quality_maintained
                    and contract_maintained
                    and hygiene_maintained)

        record = {
            "round": rnd,
            "draft_hash_before": current.get("content_hash", ""),
            "draft_hash_after": revised.get("content_hash", ""),
            "reader_verdict": cmp["verdict"],
            "mean_satisfaction_delta": cmp["mean_satisfaction_delta"],
            "continue_rate_delta": cmp["continue_rate_delta"],
            "newly_dropped": cmp["newly_dropped"],
            "newly_retained": cmp["newly_retained"],
            "newly_pay_lost": cmp["newly_pay_lost"],
            "accepted": accepted,
            "degraded": False,
            "quality_maintained": quality_maintained,  # Phase 5
            "contract_maintained": contract_maintained,  # Phase 5
            "hygiene_maintained": hygiene_maintained,  # Phase 5
            "quality_veto_reason": quality_veto_reason if not accepted and quality_guard else "",  # Phase 5
        }
        # v2 probability deltas ride the round only when the panel reported them.
        if "mean_continue_probability_delta" in cmp:
            record["mean_continue_probability_delta"] = cmp["mean_continue_probability_delta"]
        if "mean_pay_probability_delta" in cmp:
            record["mean_pay_probability_delta"] = cmp["mean_pay_probability_delta"]
        session.rounds.append(record)

        if accepted:
            current, sim = revised, new_sim
            best_artifact, best_sim = revised, new_sim
        else:
            # No relative gain (or someone newly dropped) — stop rather than
            # burn budget or risk a regression.
            session.terminate_reason = "no_improvement"
            break
    else:
        session.terminate_reason = "max_rounds"

    # Verdict + terminate_reason from the rounds (relative, never absolute).
    accepted_any = any(r.get("accepted") for r in session.rounds)
    if session.terminate_reason == "degraded":
        session.verdict = "degraded"
    elif accepted_any:
        session.verdict = "improved"
        # an accepted rewrite that then hit the round cap still "converged"
        if session.terminate_reason == "max_rounds":
            session.terminate_reason = "improved_and_converged"
    elif any(_round_is_regression(r) for r in session.rounds):
        session.verdict = "regressed"
    else:
        session.verdict = "unchanged"

    session.selected_draft_hash = best_artifact.get("content_hash", "")
    return CommercialResult(session, best_artifact, best_sim)
