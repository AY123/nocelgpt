"""D90-03: auto-revision blind evaluation scaffold.

Runs a three-arm blind comparison (original / auto-revised / human-revised)
and reports win-rate, fact-damage count, and a net-benefit verdict.
Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class BlindArm:
    arm_id: str
    label: str
    text_hash: str
    score: float | None = None
    fact_damage_count: int = 0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BlindEvaluationReport:
    kind: str
    version: str
    chapter_id: str
    arms: list[BlindArm]
    winner: str | None
    auto_revised_wins: int
    auto_revised_losses: int
    net_benefit: str  # "positive" | "neutral" | "negative"
    fact_damage_total: int
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "chapter_id": self.chapter_id,
            "arms": [a.to_dict() for a in self.arms],
            "winner": self.winner,
            "auto_revised_wins": self.auto_revised_wins,
            "auto_revised_losses": self.auto_revised_losses,
            "net_benefit": self.net_benefit,
            "fact_damage_total": self.fact_damage_total,
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def build_blind_evaluation(
    *,
    chapter_id: str,
    arms: Sequence[Mapping[str, Any]],
) -> BlindEvaluationReport:
    parsed = []
    for a in arms:
        parsed.append(BlindArm(
            arm_id=str(a.get("arm_id") or ""),
            label=str(a.get("label") or ""),
            text_hash=str(a.get("text_hash") or ""),
            score=float(a["score"]) if a.get("score") is not None else None,
            fact_damage_count=int(a.get("fact_damage_count") or 0),
            notes=str(a.get("notes") or ""),
        ))

    auto = next((a for a in parsed if a.label == "auto_revised"), None)
    original = next((a for a in parsed if a.label == "original"), None)
    human = next((a for a in parsed if a.label == "human_revised"), None)

    winner = None
    auto_wins = 0
    auto_losses = 0
    if auto and auto.score is not None:
        if original and original.score is not None:
            if auto.score > original.score:
                auto_wins += 1
            elif auto.score < original.score:
                auto_losses += 1
        if human and human.score is not None:
            if auto.score > human.score:
                auto_wins += 1
            elif auto.score < human.score:
                auto_losses += 1
    scored = [a for a in parsed if a.score is not None]
    if scored:
        winner = max(scored, key=lambda a: a.score).label

    fact_damage = sum(a.fact_damage_count for a in parsed)

    if auto_wins > auto_losses and fact_damage == 0:
        net = "positive"
    elif auto_wins == auto_losses:
        net = "neutral"
    else:
        net = "negative"

    return BlindEvaluationReport(
        kind="blind_evaluation_report",
        version="1.0",
        chapter_id=chapter_id,
        arms=parsed,
        winner=winner,
        auto_revised_wins=auto_wins,
        auto_revised_losses=auto_losses,
        net_benefit=net,
        fact_damage_total=fact_damage,
        metadata={"arm_count": len(parsed)},
    )
