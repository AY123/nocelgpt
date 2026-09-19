"""review_panel.py — multi-model review panel (ANES v2, evaluative axis).

The North Star's highest-value idea made concrete: instead of one judge, N
specialist judges score the SAME draft INDEPENDENTLY (no cross-reference — a
hard requirement), each with a role focus and its own model. A deterministic
Synthesizer then merges them into ONE consensus QualityReport, weighting each
panelist on the dimensions it is expert in, and SURFACING disagreement rather
than averaging it away.

Design:
  - Each panelist is just an LLMQualityJudge with a role_focus + its own model,
    so it reuses the whole quality_center pipeline (robust parse, degradation,
    invariants). A panel IS a DraftReviewer: it drops into execute_package and
    revise_until with no change, because its output is a plain QualityReport.
  - Synthesis is DETERMINISTIC given the panelists' reports (reproducible), even
    though each report came from a non-deterministic LLM (replay-stable). No
    synthesizer *model* is needed for v1; weighted merge is enough and auditable.
  - Invariants hold: the merged report is axis=evaluative, gating=false. A panel
    can never gate.
  - Resilience: if one panelist degrades, the panel continues on the rest. Only
    if ALL degrade does the consensus degrade.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .quality_center import (
    LLMQualityJudge,
    QualityReport,
    SCORE_DIMENSIONS,
    degraded_report,
)

# Each role is trusted MORE on the dimensions it specializes in. Weights are
# relative; the synthesizer normalizes per dimension across non-degraded
# panelists. A role not listed for a dimension still contributes at BASE_WEIGHT.
BASE_WEIGHT = 1.0
SPECIALIST_WEIGHT = 3.0

ROLE_FOCUS: Dict[str, str] = {
    "literary": (
        "你侧重文学性与情绪：语言质感、画面感、情绪调动与人物内心可信度。"
        "对 emotion 与 character_consistency 的判断最为权威。"
    ),
    "structural": (
        "你侧重叙事结构：钩子布置、冲突推进、节奏与场景衔接。"
        "对 hook、conflict、pacing 与 curiosity(下一章打开欲) 的判断最为权威。"
    ),
    "commercial": (
        "你侧重网文商业性：爽点密度、付费追读欲望、市场卖点、订阅转化。"
        "对 commercial、reward_density、retention、subscription、payoff、"
        "promise_delivery、reader_drop_risk 的判断最为权威。"
    ),
    "logic": (
        "你侧重设定与逻辑一致性：是否违反世界规则、是否套路化/抄袭风险。"
        "对 world_consistency、originality_risk 与 serial_sustainability 的判断最为权威。"
    ),
    "character": (
        "你侧重人物弧光：人物的目标、动机、压力与本章内的成长变化是否可信、可追踪。"
        "对 character_consistency 与 character_growth 的判断最为权威。"
    ),
    "safety": (
        "你侧重平台内容安全：擦边、敏感、违规风险的主观程度评估(非硬性红线，红线由确定性检查负责)。"
        "对 safety_risk 的判断最为权威。"
    ),
}

# Each v2 commercial-decomposition dimension is owned by the specialist best placed
# to judge it, so no single mega-judge carries all 18 (Phase 4 invariant #3). A role
# not listed for a dimension still contributes at BASE_WEIGHT.
ROLE_SPECIALTY: Dict[str, tuple] = {
    "literary": ("emotion", "character_consistency"),
    "structural": ("hook", "conflict", "pacing", "curiosity"),
    "commercial": ("commercial", "reward_density", "retention", "subscription",
                   "payoff", "promise_delivery", "reader_drop_risk"),
    "logic": ("world_consistency", "originality_risk", "serial_sustainability"),
    "character": ("character_consistency", "character_growth"),
    "safety": ("safety_risk",),
}


@dataclass
class Panelist:
    """A single specialist reviewer: a role + a judge (which wraps a model)."""
    role: str
    judge: LLMQualityJudge

    @classmethod
    def build(cls, role: str, model, *, threshold: int = 80) -> "Panelist":
        focus = ROLE_FOCUS.get(role, "")
        judge = LLMQualityJudge(
            model,
            reviewer_id=f"panelist-{role}",
            threshold=threshold,
            role_focus=focus,
        )
        return cls(role=role, judge=judge)


def _weight(role: str, dim: str) -> float:
    return SPECIALIST_WEIGHT if dim in ROLE_SPECIALTY.get(role, ()) else BASE_WEIGHT


def _synthesize(reports: List[tuple], *, reviewer_id: str) -> QualityReport:
    """Merge (role, QualityReport) pairs into one consensus report.

    - scores: per-dimension weighted mean over NON-degraded panelists, where a
      panelist's weight is higher on its specialty dimensions.
    - disagreement: per-dimension spread (max-min) over non-degraded panelists.
    - revision_plan: union of all panelists' plans (dedup by dimension+action),
      so no specialist's concern is lost in the merge.
    - findings surface high-disagreement dimensions for human attention.
    """
    live = [(role, rep) for role, rep in reports
            if not (rep.judge_provenance or {}).get("degraded")]

    panelists_block = [{
        "reviewer": rep.reviewer,
        "role": role,
        "model_id": (rep.judge_provenance or {}).get("model_id", ""),
        "degraded": bool((rep.judge_provenance or {}).get("degraded")),
        "scores": rep.scores,
    } for role, rep in reports]

    if not live:
        # Every panelist degraded — consensus degrades too (still non-gating).
        base = degraded_report(reviewer_id, "all panelists degraded")
        return QualityReport(
            reviewer=reviewer_id,
            scores=base.scores,
            dimensions=[],
            revision_plan=[],
            findings=base.findings,
            judge_provenance={"model_id": "panel", "parse_ok": False, "degraded": True},
            panel={"synthesis": "weighted", "panelists": panelists_block, "disagreement": {}},
        )

    scores: Dict[str, int] = {}
    disagreement: Dict[str, int] = {}
    for dim in SCORE_DIMENSIONS:
        weighted_sum = 0.0
        weight_total = 0.0
        vals = []
        for role, rep in live:
            v = rep.scores.get(dim, 0)
            w = _weight(role, dim)
            weighted_sum += v * w
            weight_total += w
            vals.append(v)
        scores[dim] = int(round(weighted_sum / weight_total)) if weight_total else 0
        disagreement[dim] = (max(vals) - min(vals)) if vals else 0

    # Union revision plans, dedup on (dimension, action).
    seen = set()
    revision_plan = []
    for role, rep in live:
        for item in rep.revision_plan:
            key = (item.get("dimension"), item.get("action"))
            if key in seen:
                continue
            seen.add(key)
            revision_plan.append(item)

    # Consensus dimensions carry the merged score + evidence of who flagged what.
    dimensions = [{"name": dim, "score": scores[dim]} for dim in SCORE_DIMENSIONS]

    findings = [{
        "check": "panel-synthesis",
        "severity": "info",
        "message": f"panel of {len(reports)} ({len(live)} live) synthesized by weighted merge",
    }]
    HIGH_SPREAD = 25
    for dim, spread in disagreement.items():
        if spread >= HIGH_SPREAD:
            findings.append({
                "check": "panel-disagreement",
                "severity": "warning",
                "message": f"panelists disagree on {dim} (spread {spread}); human review advised",
            })

    return QualityReport(
        reviewer=reviewer_id,
        scores=scores,
        dimensions=dimensions,
        revision_plan=revision_plan,
        findings=findings,
        judge_provenance={"model_id": "panel", "parse_ok": True, "degraded": False},
        panel={
            "synthesis": "weighted",
            "panelists": panelists_block,
            "disagreement": disagreement,
        },
    )


class ReviewPanel:
    """A DraftReviewer that fans out to specialist panelists (independently) and
    synthesizes one consensus QualityReport. Drops into execute_package and
    revise_until unchanged — its output is a plain QualityReport."""

    def __init__(self, panelists: List[Panelist], *, reviewer_id: str = "review-panel-v1"):
        if not panelists:
            raise ValueError("ReviewPanel requires at least one panelist")
        self.panelists = panelists
        self.reviewer_id = reviewer_id

    def review(self, artifact: dict, package: dict,
               grounding: dict | None = None) -> QualityReport:
        # INDEPENDENT scoring: each panelist sees only the raw draft + package,
        # never another panelist's scores (North Star: no cross-reference).
        # `grounding` (Phase 4.2 Chapter IR payoff_target) is forwarded to every
        # panelist so the commercial specialist (which owns promise_delivery)
        # scores it against the stated promise; panelists ignore it if absent.
        reports = []
        for p in self.panelists:
            try:
                rep = p.judge.review(artifact, package, grounding=grounding)
            except Exception as exc:
                rep = degraded_report(f"panelist-{p.role}", f"panel error: {exc}")
            reports.append((p.role, rep))
        return _synthesize(reports, reviewer_id=self.reviewer_id)


def build_review_panel(role_to_model: Dict[str, object], *, threshold: int = 80,
                       reviewer_id: str = "review-panel-v1") -> ReviewPanel:
    """Convenience: {role: model} -> ReviewPanel. Roles not in ROLE_FOCUS still
    work (they just contribute at base weight everywhere)."""
    panelists = [Panelist.build(role, model, threshold=threshold)
                 for role, model in role_to_model.items()]
    return ReviewPanel(panelists, reviewer_id=reviewer_id)
