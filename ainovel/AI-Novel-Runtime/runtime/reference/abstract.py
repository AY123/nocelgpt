"""abstract.py — derive a machine-consumable reference LM abstraction from the
reference novels and their quality profile (M5).

This is the non-blocking Phase D enhancement: it turns 1-5 market-validated
reference novels into a structured abstraction layer that downstream planning
modules can consume. It is comparison-only, never gates, and writes only to
registry/derived/reference-abstract/.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..outline.sources import iter_source_texts, load_reference_sources
from .profile import PROFILE_ID, load_reference_profile
from .segment import segment_reference_novel

_SCHEMA_REL = ("AI-Novel-Standard", "contracts", "reference-lm-abstraction.schema.json")

SCHEMA_VERSION = "1.0"
ABSTRACT_ID = "REFABSTRACT-001"


@dataclass(frozen=True)
class ReferenceAbstractionResult:
    ok: bool
    stage: str
    message: str
    abstract_json: str | None = None
    sources: int | None = None
    chapters_seen: int | None = None
    evidence_spans: int | None = None
    errors: list[str] | None = None


def derived_reference_abstract_dir(project_path: str | Path) -> Path:
    return Path(project_path) / "registry" / "derived" / "reference-abstract"


def _first_nonempty(*values, default: str = "") -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def _collect_quote_spans(text: str, max_spans: int = 3) -> list[dict]:
    text = (text or "").strip()
    if not text:
        return []
    spans: list[dict] = []
    chapters = segment_reference_novel("REF", text)
    for chapter in chapters[:max_spans]:
        spans.append({
            "heading": chapter.heading,
            "excerpt": chapter.body[:240],
        })
    if not spans:
        spans.append({"heading": "", "excerpt": text[:240]})
    return spans


def _genre_from_sources(sources: list[tuple[str, str]]) -> str:
    for _, text in sources:
        sample = text[:3000]
        if any(token in sample for token in ("修仙", "仙侠", "玄幻", "灵气", "宗门")):
            return "玄幻/仙侠"
        if any(token in sample for token in ("星际", "机甲", "系统", "宇宙", "末世")):
            return "科幻/末世"
        if any(token in sample for token in ("豪门", "娱乐圈", "婚恋", "总裁", "重生")):
            return "都市/言情"
    return "泛类型商业网文"


def _build_patterns(profile: Optional[dict]) -> dict:
    bands = (profile or {}).get("bands", {}) if profile else {}
    patterns = {
        "opening": "强钩子开局、目标先行、身份或处境反差迅速建立",
        "conflict": "主目标牵引下的连续冲突升级",
        "payoff": "小周期兑现与章末悬念交替出现",
        "continuity": "事实与关系状态持续累积，不做重置式推进",
    }
    if bands:
        hook = bands.get("hook") or {}
        density = bands.get("density") or {}
        if hook.get("median") is not None:
            patterns["hook_anchor"] = f"参考集 hook 中位数约 {hook['median']}"
        if density.get("median") is not None:
            patterns["pacing_anchor"] = f"参考集 density 中位数约 {density['median']}"
    return patterns


def build_reference_abstraction(project_path: str | Path, *, max_spans_per_source: int = 2) -> dict:
    project = Path(project_path)
    check = load_reference_sources(project)
    if not check.ok:
        raise ValueError("reference source validation failed: " + "; ".join(check.errors))

    profile = load_reference_profile(project)
    pairs = [(src.id, text) for src, text in iter_source_texts(project, check.sources)]
    evidence_spans: list[dict] = []
    source_summaries: list[dict] = []
    chapters_seen = 0

    for source, text in pairs:
        chapters = segment_reference_novel(source, text)
        chapters_seen += len(chapters)
        evidence_spans.extend(_collect_quote_spans(text, max_spans=max_spans_per_source))
        source_summaries.append({
            "source_id": source,
            "chapters_estimated": len(chapters),
            "dominant_function": "开局/升级/兑现/关系推进",
        })

    genre = _genre_from_sources(pairs)
    core_promise = _first_nonempty(
        ((profile or {}).get("bands", {}).get("hook", {}) or {}).get("median")
        and "高抓力开篇与连续追读",
        "强商业钩子与稳定回报",
        default="强商业钩子与稳定回报",
    )
    if "".join(text for _, text in pairs).count("反转") > 3:
        core_promise = "以高频反转与局部兑现维持追读"

    abstraction = {
        "id": ABSTRACT_ID,
        "kind": "reference_lm_abstraction",
        "schema_version": SCHEMA_VERSION,
        "profile_id": PROFILE_ID if profile is not None else None,
        "source_ids": [src.id for src in check.sources],
        "market_positioning": {
            "genre": genre,
            "reader_target": "中文商业网文核心读者",
            "core_promise": core_promise,
            "commercial_thesis": "开篇强钩子 + 中段持续升级 + 章末钩子稳定兑现",
        },
        "structural_patterns": _build_patterns(profile),
        "character_patterns": {
            "protagonist": "目标驱动、行动前置、情绪与能力同步升级",
            "supporting": "功能型配角围绕主线压力与回报循环展开",
            "relationship": "关系张力与信息差共同驱动章节推进",
        },
        "world_patterns": {
            "rules": "设定先露边界，再逐步解释例外与代价",
            "progression": "成长/升级/解谜至少有一条稳定推进线",
            "constraints": "核心能力必须伴随成本、限制或条件触发",
        },
        "commercial_cadence": {
            "opening": "前几章迅速建立卖点与冲突",
            "mid_arc": "每个小周期均有显性回报",
            "chapter_end": "章末留钩子或未完成目标",
            "long_run": "百章尺度仍可维持升级空间与矛盾层次",
        },
        "transferable_abstractions": [
            "反差开局",
            "目标-阻力-回报循环",
            "连续升级阶梯",
            "关系张力驱动",
            "章末钩子",
        ],
        "prohibited_specifics": [
            "具体人物名",
            "专有世界观名词",
            "可唯一识别的情节细节",
        ],
        "source_summaries": source_summaries,
        "evidence_spans": evidence_spans,
        "notes": [
            "Observed information is separated from strategic abstraction.",
            "This artifact is comparison-only and advisory.",
        ],
    }
    return abstraction


def _validate_against_contract(abstraction: dict) -> None:
    schema_path = Path(__file__).resolve().parents[4] / _SCHEMA_REL[0] / _SCHEMA_REL[1] / _SCHEMA_REL[2]
    if not schema_path.exists():
        return
    try:
        import jsonschema
    except ImportError:
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(abstraction, schema)


def write_reference_abstraction(project_path: str | Path, abstraction: dict) -> str:
    _validate_against_contract(abstraction)
    out_dir = derived_reference_abstract_dir(project_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{abstraction['id']}.json"
    path.write_text(json.dumps(abstraction, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path.relative_to(Path(project_path)))


def load_reference_abstraction(project_path: str | Path) -> Optional[dict]:
    path = derived_reference_abstract_dir(project_path) / f"{ABSTRACT_ID}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
