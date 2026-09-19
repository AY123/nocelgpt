"""revision.py — Revision Controller (ANES v2, evaluative optimization loop).

Closes the quality loop the North Star calls the highest-value step:

    draft --[QualityReport.revision_plan]--> targeted rewrite --> re-score
          --> verify the flagged dimensions actually improved

This is the machine-verifiable part that content_hash + replay make possible:
"did fixing the reward_density issue actually move reward_density up, and did it
regress anything else?" is answered with numbers, not a hunch.

Discipline:
  - The controller lives ENTIRELY in the evaluative/optimization lane. Its
    session record has `gating` const false; it never blocks a build. It selects
    a BETTER artifact; the deterministic gates still run on that artifact via the
    normal execute path.
  - The rewrite reuses the ChapterDraft hashing discipline (execution.agent), so
    a rewritten draft is a first-class, contract-shaped artifact with its own
    content_hash — that's what makes before/after comparison real.
  - Bounded: stops on all-flagged-dims-pass, no-improvement, max_rounds, or a
    degraded judge. Never loops forever, never bills forever.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Optional

from .agent import _count_words, ARTIFACT_FORMAT
from .quality_center import LLMQualityJudge, SCORE_DIMENSIONS, REVISION_THRESHOLD, LOWER_IS_BETTER

# Risk dims where LOWER is better. Single source of truth lives in quality_center
# (v2 added reader_drop_risk / safety_risk alongside originality_risk).
_LOWER_IS_BETTER = LOWER_IS_BETTER


def _canonical(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True)


def _hash(obj) -> str:
    return "sha256:" + hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _is_better(dim: str, new: int, old: int) -> bool:
    if dim in _LOWER_IS_BETTER:
        return new < old
    return new > old


def _passes(dim: str, score: int, threshold: int) -> bool:
    if dim in _LOWER_IS_BETTER:
        return score <= (100 - threshold)
    return score >= threshold


# --------------------------------------------------------------------------- #
# Contracted rewrite prompt. The rewriter is given the ORIGINAL prose and the  #
# per-issue revision plan, and must return ONLY revised prose — it may not     #
# introduce facts absent from the bound context (that stays a deterministic    #
# concern downstream).                                                          #
# --------------------------------------------------------------------------- #
_REWRITE_SYSTEM = (
    "你是一名资深网文作者兼修稿师。你根据编辑给出的逐条修改单修订正文，"
    "只输出修订后的完整正文，不解释、不加标题、不输出修改说明。"
)

_REWRITE_TEMPLATE = """# Role
网文修稿师。

# Goal
根据下面的逐条修改单，修订这一章正文。保留原有优点，只针对性地解决被指出的问题。

# 硬约束
- 只输出修订后的完整章节正文，不要输出任何解释、标题或 JSON。
- 不得引入下列设定事实之外的新专有名词、新世界规则。
- 不得改变人物既定目标与既有设定。
- 保持与原文相近的篇幅。

# 本章绑定设定(不得违反)
{context}

# 逐条修改单(按此修订)
{revision_list}

# 原正文
<<<CHAPTER>>>
{body}
<<<END>>>

# 输出
直接输出修订后的完整正文。"""


def build_rewrite_prompt(artifact: dict, package: dict, revision_plan: List[dict]) -> str:
    context_lines = []
    for records in package.get("context", {}).values():
        for rec in records:
            name = rec.get("name", rec.get("id", "?"))
            note = rec.get("statement") or rec.get("summary") or rec.get("notes") or ""
            context_lines.append(f"- {rec.get('id','?')} {name}: {note}".rstrip())
    context = "\n".join(context_lines) or "(无绑定设定)"
    if revision_plan:
        revision_list = "\n".join(
            f"{i}. [{item.get('priority','-')}] {item.get('dimension')}: "
            f"{item.get('issue','')} → {item.get('action','')}"
            for i, item in enumerate(revision_plan, start=1)
        )
    else:
        revision_list = "(无具体修改单，整体提升追读性与爽点密度)"
    return _REWRITE_TEMPLATE.format(
        context=context, revision_list=revision_list, body=artifact.get("body", ""))


def rewrite_once(model, artifact: dict, package: dict, revision_plan: List[dict]) -> Optional[dict]:
    """Produce a rewritten ChapterDraft artifact. Reuses the agent hashing
    discipline so the result is a first-class artifact with its own content_hash.
    Returns None if the model errors or yields empty prose (caller degrades)."""
    prompt = build_rewrite_prompt(artifact, package, revision_plan)
    try:
        output = model.generate(prompt)
        text = getattr(output, "text", "") or ""
        model_id = getattr(output, "model_id", getattr(model, "model_id", ""))
        model_kind = getattr(output, "model_kind", "llm")
    except Exception:
        return None
    if not text.strip():
        return None

    core = {
        "artifact_format": ARTIFACT_FORMAT,
        "kind": "prose",
        "capability": "ChapterDraft",
        "task_id": artifact.get("task_id", package.get("task", {}).get("task_id", "")),
        "provenance": dict(artifact.get("provenance", {})),
        "body": text,
    }
    new_artifact = dict(core)
    new_artifact["content_hash"] = _hash(core)
    new_artifact["word_count"] = _count_words(text)
    new_artifact["produced_by"] = {"model_id": model_id, "model_kind": model_kind}
    return new_artifact


# --------------------------------------------------------------------------- #
# The controller loop.                                                         #
# --------------------------------------------------------------------------- #
@dataclass
class RevisionSession:
    controller: str
    threshold: int
    rounds: List[dict] = field(default_factory=list)
    terminate_reason: str = "max_rounds"
    verdict: str = "unchanged"
    selected_draft_hash: str = ""
    gating: bool = False   # structural invariant — never blocks

    def to_dict(self) -> dict:
        return {
            "controller": self.controller,
            "gating": self.gating,
            "threshold": self.threshold,
            "terminate_reason": self.terminate_reason,
            "verdict": self.verdict,
            "selected_draft_hash": self.selected_draft_hash,
            "rounds": self.rounds,
        }


def _targeted_dims(report: dict) -> List[str]:
    dims = []
    for item in report.get("revision_plan", []):
        d = item.get("dimension")
        if d in SCORE_DIMENSIONS and d not in dims:
            dims.append(d)
    return dims


def _compare(before: dict, after: dict, targeted: List[str]) -> dict:
    """Classify every scored dimension as improved / regressed / unchanged.
    Improvement direction respects originality_risk (lower is better)."""
    improved, regressed, unchanged = [], [], []
    for dim in SCORE_DIMENSIONS:
        b, a = before.get(dim, 0), after.get(dim, 0)
        if _is_better(dim, a, b):
            improved.append(dim)
        elif _is_better(dim, b, a):
            regressed.append(dim)
        else:
            unchanged.append(dim)
    return {"improved": improved, "regressed": regressed, "unchanged": unchanged}


@dataclass
class RevisionResult:
    session: RevisionSession
    final_artifact: dict
    final_report: dict


def _reference_gap(artifact: dict, reference_profile: Optional[dict]) -> Optional[dict]:
    """The M9.1 advisory signal for the revision loop: place this round's draft
    against the market-validated reference bands. Recorded per round for audit —
    it NEVER feeds the accept/reject decision (that stays the judge-score
    comparison, ADR-003). None when no profile is pinned."""
    if reference_profile is None:
        return None
    from ..reference import measure_reference_chapter, compare_to_profile
    measurement = measure_reference_chapter((artifact or {}).get("body", ""))
    return compare_to_profile(measurement, reference_profile)


def revise_until(
    judge: LLMQualityJudge,
    rewrite_model,
    artifact: dict,
    package: dict,
    *,
    max_rounds: int = 3,
    threshold: int = REVISION_THRESHOLD,
    controller_id: str = "revision-controller-v1",
    initial_report: Optional[dict] = None,
    reference_profile: Optional[dict] = None,
) -> RevisionResult:
    """Iteratively rewrite + re-score until flagged dims pass, improvement
    stalls, or max_rounds. Always returns the BEST draft seen (never worse than
    the input). Purely advisory — never gates.

    `reference_profile` (optional M9 anchor) adds a per-round `reference_gap`
    advisory reading to the session (distance from a market-validated chapter).
    RECORDED ONLY: the accept/reject decision stays the judge-score comparison,
    so the gap never gates or reorders selection (ADR-003)."""
    session = RevisionSession(controller=controller_id, threshold=threshold)

    current = artifact
    report = initial_report or judge.review(artifact, package).to_dict()
    best_artifact = current
    best_report = report

    def _all_pass(rep: dict) -> bool:
        scores = rep.get("scores", {})
        return all(_passes(d, scores.get(d, 0), threshold) for d in SCORE_DIMENSIONS)

    if best_report.get("judge_provenance", {}).get("degraded"):
        session.terminate_reason = "degraded"
        session.verdict = "degraded"
        session.selected_draft_hash = current.get("content_hash", "")
        return RevisionResult(session, best_artifact, best_report)

    if _all_pass(best_report):
        session.terminate_reason = "all_dimensions_pass"
        session.verdict = "unchanged"
        session.selected_draft_hash = current.get("content_hash", "")
        return RevisionResult(session, best_artifact, best_report)

    for rnd in range(1, max_rounds + 1):
        targeted = _targeted_dims(report)
        scores_before = dict(report.get("scores", {}))

        revised = rewrite_once(rewrite_model, current, package, report.get("revision_plan", []))
        if revised is None:
            session.rounds.append({
                "round": rnd,
                "draft_hash_before": current.get("content_hash", ""),
                "draft_hash_after": current.get("content_hash", ""),
                "targeted_dimensions": targeted,
                "scores_before": scores_before,
                "scores_after": scores_before,
                "improved": [], "regressed": [], "unchanged": list(SCORE_DIMENSIONS),
                "degraded": True,
                "note": "rewrite model produced no usable prose",
            })
            session.terminate_reason = "degraded"
            break

        new_report = judge.review(revised, package).to_dict()
        if new_report.get("judge_provenance", {}).get("degraded"):
            session.rounds.append({
                "round": rnd,
                "draft_hash_before": current.get("content_hash", ""),
                "draft_hash_after": revised.get("content_hash", ""),
                "targeted_dimensions": targeted,
                "scores_before": scores_before,
                "scores_after": scores_before,
                "improved": [], "regressed": [], "unchanged": list(SCORE_DIMENSIONS),
                "degraded": True,
                "note": "re-score degraded; keeping prior draft",
            })
            session.terminate_reason = "degraded"
            break

        scores_after = dict(new_report.get("scores", {}))
        cmp = _compare(scores_before, scores_after, targeted)
        round_record = {
            "round": rnd,
            "draft_hash_before": current.get("content_hash", ""),
            "draft_hash_after": revised.get("content_hash", ""),
            "targeted_dimensions": targeted,
            "scores_before": scores_before,
            "scores_after": scores_after,
            **cmp,
            "degraded": False,
        }
        # Advisory M9.1 reading — recorded, never part of the accept decision below.
        gap = _reference_gap(revised, reference_profile)
        if gap is not None:
            round_record["reference_gap"] = gap
        session.rounds.append(round_record)

        # Did the targeted dimensions improve on net? Accept the rewrite only if
        # at least one targeted dim improved and none of ANY dim regressed below.
        targeted_improved = [d for d in targeted if d in cmp["improved"]]
        accepted = bool(targeted_improved) and not cmp["regressed"]

        if accepted:
            current, report = revised, new_report
            best_artifact, best_report = revised, new_report
            if _all_pass(new_report):
                session.terminate_reason = "all_dimensions_pass"
                break
            # The judge proposed no further revisions — it has nothing left to
            # fix, so the draft has converged even if not every dim hit the bar.
            if not _targeted_dims(new_report):
                session.terminate_reason = "converged"
                break
        else:
            # No net gain this round — stop rather than burn budget or regress.
            session.terminate_reason = "no_improvement"
            break
    else:
        session.terminate_reason = "max_rounds"

    # Verdict from first-seen vs best-selected.
    first_scores = (initial_report or {}).get("scores") if initial_report else None
    baseline = first_scores or (session.rounds[0]["scores_before"] if session.rounds else {})
    final_scores = best_report.get("scores", {})
    final_cmp = _compare(baseline, final_scores, [])
    if session.terminate_reason == "degraded":
        session.verdict = "degraded"
    elif final_cmp["improved"] and not final_cmp["regressed"]:
        session.verdict = "improved"
    elif final_cmp["regressed"]:
        session.verdict = "regressed"
    else:
        session.verdict = "unchanged"

    session.selected_draft_hash = best_artifact.get("content_hash", "")
    return RevisionResult(session, best_artifact, best_report)
