"""quality_rubric.py — B1 Chinese commercial web novel quality rubric artifact.

This module centralizes the rubric structure used by editors, reviewers, and
future evaluation pipelines. The rubric is intentionally data-first: the runtime
can serialize it, tests can validate it, and downstream tools can consume it
without hardcoding the scoring dimensions in multiple places.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import json

RUBRIC_ID = "QRL-00001"
RUBRIC_VERSION = "1.0"
RUBRIC_FILENAME = "quality-rubric.yaml"

RUBRIC_DIMENSIONS = (
    {
        "id": "opening_hook",
        "label": "开篇抓力",
        "weight": 0.12,
        "description": "开篇是否迅速建立吸引力、信息缺口和阅读动机。",
        "signals": ["开场是否立住", "前 300-800 字是否有钩子", "是否有明确阅读承诺"],
    },
    {
        "id": "chapter_goal",
        "label": "章节目标",
        "weight": 0.09,
        "description": "本章是否有明确可验证的目标，并在章节内持续推进。",
        "signals": ["目标是否具体", "是否有目标偏移", "是否有结果闭环"],
    },
    {
        "id": "conflict_progression",
        "label": "冲突推进",
        "weight": 0.11,
        "description": "冲突是否层层升级、是否推动情节发生变化。",
        "signals": ["冲突是否具体", "升级是否自然", "是否存在原地打转"],
    },
    {
        "id": "character_motivation",
        "label": "人物动机",
        "weight": 0.10,
        "description": "人物行为是否有内在动机支撑，是否可信。",
        "signals": ["动机是否清晰", "选择是否合乎性格", "行为后果是否一致"],
    },
    {
        "id": "emotion_flow",
        "label": "情绪推进",
        "weight": 0.08,
        "description": "情绪曲线是否连贯，是否能持续带动读者代入。",
        "signals": ["情绪是否有起伏", "情绪是否断层", "是否存在情绪空转"],
    },
    {
        "id": "information_density",
        "label": "信息密度",
        "weight": 0.08,
        "description": "章节信息是否有效，是否存在注水或重复说明。",
        "signals": ["有效信息量", "重复率", "叙述是否拖沓"],
    },
    {
        "id": "payoff_delivery",
        "label": "爽点兑现",
        "weight": 0.13,
        "description": "章节是否兑现前文承诺的爽点、反转或情绪回报。",
        "signals": ["承诺是否兑现", "爽点是否足量", "回报是否对等"],
    },
    {
        "id": "ending_hook",
        "label": "章末钩子",
        "weight": 0.10,
        "description": "章末是否形成强继续阅读动机。",
        "signals": ["是否有未完待续", "悬念是否自然", "是否推进下章目标"],
    },
    {
        "id": "continuity",
        "label": "连续性",
        "weight": 0.09,
        "description": "人物、设定、时间线和事件因果是否稳定一致。",
        "signals": ["是否自相矛盾", "是否吃设定", "是否破坏时间线"],
    },
    {
        "id": "ai_voice_risk",
        "label": "AI 腔风险",
        "weight": 0.05,
        "description": "是否存在模板味、空话、泛化句式和机械拼接感。",
        "signals": ["是否过度概括", "是否句式雷同", "是否缺少具体细节"],
    },
    {
        "id": "paying_intent",
        "label": "付费意愿",
        "weight": 0.03,
        "description": "章节是否强化读者愿意付费/追订的动机。",
        "signals": ["是否有付费预期", "是否强化下文价值", "是否形成继续付费理由"],
    },
    {
        "id": "continue_intent",
        "label": "追读意愿",
        "weight": 0.02,
        "description": "读者是否想立即点开下一章。",
        "signals": ["是否想继续读", "是否有情节惯性", "是否存在中断点"],
    },
)


@dataclass(frozen=True)
class RubricDimension:
    id: str
    label: str
    weight: float
    description: str
    signals: tuple[str, ...]


@dataclass(frozen=True)
class QualityRubric:
    id: str
    kind: str
    version: str
    title: str
    scope: str
    audience: str
    scoring_scale: str
    dimensions: tuple[RubricDimension, ...]
    review_policy: dict

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "version": self.version,
            "title": self.title,
            "scope": self.scope,
            "audience": self.audience,
            "scoring_scale": self.scoring_scale,
            "dimensions": [
                {
                    "id": d.id,
                    "label": d.label,
                    "weight": d.weight,
                    "description": d.description,
                    "signals": list(d.signals),
                }
                for d in self.dimensions
            ],
            "review_policy": self.review_policy,
        }


def _dimensions() -> tuple[RubricDimension, ...]:
    return tuple(
        RubricDimension(
            id=d["id"],
            label=d["label"],
            weight=d["weight"],
            description=d["description"],
            signals=tuple(d["signals"]),
        )
        for d in RUBRIC_DIMENSIONS
    )


def build_quality_rubric() -> QualityRubric:
    return QualityRubric(
        id=RUBRIC_ID,
        kind="quality_rubric",
        version=RUBRIC_VERSION,
        title="中文商业网文质量 Rubric",
        scope="chapter",
        audience="editorial_review",
        scoring_scale="0-100",
        dimensions=_dimensions(),
        review_policy={
            "authoritative": "human_editor",
            "llm_use": "advisory_only",
            "blocking": False,
            "rerun_required_on_prompt_change": True,
            "golden_set_required": True,
        },
    )


def render_quality_rubric_yaml() -> str:
    rubric = build_quality_rubric().to_dict()
    lines: list[str] = [
        f'id: "{rubric["id"]}"',
        f'kind: "{rubric["kind"]}"',
        f'version: "{rubric["version"]}"',
        f'title: "{rubric["title"]}"',
        f'scope: "{rubric["scope"]}"',
        f'audience: "{rubric["audience"]}"',
        f'scoring_scale: "{rubric["scoring_scale"]}"',
        "dimensions:",
    ]
    for dim in rubric["dimensions"]:
        lines.extend([
            "  - id: \"{}\"".format(dim["id"]),
            "    label: \"{}\"".format(dim["label"]),
            f"    weight: {dim['weight']}",
            "    description: \"{}\"".format(dim["description"]),
            "    signals:",
        ])
        for signal in dim["signals"]:
            lines.append(f"      - \"{signal}\"")
    lines.extend([
        "review_policy:",
        f"  authoritative: \"{rubric['review_policy']['authoritative']}\"",
        f"  llm_use: \"{rubric['review_policy']['llm_use']}\"",
        f"  blocking: {str(rubric['review_policy']['blocking']).lower()}",
        f"  rerun_required_on_prompt_change: {str(rubric['review_policy']['rerun_required_on_prompt_change']).lower()}",
        f"  golden_set_required: {str(rubric['review_policy']['golden_set_required']).lower()}",
    ])
    return "\n".join(lines) + "\n"


def write_quality_rubric_file(target_dir: str | Path) -> Path:
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / RUBRIC_FILENAME
    path.write_text(render_quality_rubric_yaml(), encoding="utf-8")
    return path


def rubric_dimension_ids() -> Iterable[str]:
    return (d["id"] for d in RUBRIC_DIMENSIONS)
