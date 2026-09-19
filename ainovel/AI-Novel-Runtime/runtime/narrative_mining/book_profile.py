"""Evidence-linked book profiles derived from versioned corpus snapshots."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Protocol

from ..reference.segment import segment_reference_novel

SCHEMA_VERSION = "1.0"
KIND = "book_narrative_profile"
ANALYZER_VERSION = "deterministic-book-profile-v1"


class BookProfileError(ValueError):
    """The profile input or snapshot binding is invalid."""


class BookProfileAnalyzer(Protocol):
    def analyze(self, book: Mapping, text: str, *, snapshot: Mapping) -> dict: ...


def _profile_id(book_id: str) -> str:
    return f"BNP-{book_id.removeprefix('CBK-')}"


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


class DeterministicBookProfileAnalyzer:
    """Low-cost fixture/baseline analyzer; conclusions remain explicitly low confidence."""

    def analyze(self, book: Mapping, text: str, *, snapshot: Mapping) -> dict:
        if book.get("id") not in {item.get("id") for item in snapshot.get("books", [])}:
            raise BookProfileError("book is not a member of the bound corpus snapshot")
        chapters = segment_reference_novel(str(book["id"]), text)
        # Tiny synthetic fixtures can fall below the production segmenter's
        # 200-character chapter floor. Keep the deterministic baseline useful
        # without weakening the shared production segmentation contract.
        joined = "\n".join(chapter.body for chapter in chapters) if chapters else text
        chapter_indexes = [chapter.index for chapter in chapters[:3]] or [1]

        has_limit = _contains(joined, ("限制", "代价", "只能", "只有", "只赢得", "消耗", "失去"))
        has_choice = _contains(joined, ("选择", "决定", "主动", "拒绝", "承担"))
        has_power = _contains(joined, ("能力", "修炼", "血脉", "戒指", "传承", "力量"))
        has_faction = _contains(joined, ("宗门", "势力", "帝国", "学院", "山门"))
        has_map = _contains(joined, ("大陆", "地图", "帝国之外", "新区域"))
        has_payoff = _contains(joined, ("击败", "取回", "证明", "突破", "救下", "胜利"))

        growth_axes = ["personal_capability"] if has_power else ["task_competence"]
        if has_faction:
            growth_axes.append("faction_status")
        if has_map:
            growth_axes.append("world_expansion")
        limitations = ["ability_has_explicit_cost_or_limit"] if has_limit else []
        risks = []
        if has_power and not has_limit:
            risks.append("unbounded_power_growth")
        if not has_choice:
            risks.append("low_protagonist_agency")
        if len(growth_axes) == 1:
            risks.append("single_growth_axis")

        payoff_chapter = None
        for chapter in chapters:
            if _contains(chapter.body, ("击败", "取回", "证明", "突破", "救下", "胜利")):
                payoff_chapter = chapter.index
                break

        feature_codes = [
            code
            for condition, code in (
                (has_limit, "explicit_limit"),
                (has_choice, "protagonist_choice"),
                (has_power, "capability_signal"),
                (has_faction, "faction_signal"),
                (has_map, "map_expansion_signal"),
                (has_payoff, "visible_payoff_signal"),
            )
            if condition
        ] or ["insufficient_deterministic_signal"]
        confidence = 0.35 if chapters else 0.2
        return {
            "id": _profile_id(str(book["id"])),
            "kind": KIND,
            "schema_version": SCHEMA_VERSION,
            "book_id": book["id"],
            "corpus_snapshot_id": snapshot["id"],
            "corpus_manifest_hash": snapshot["manifest_hash"],
            "analysis": {
                "method": "deterministic",
                "analyzer_version": ANALYZER_VERSION,
                "prompt_version": snapshot["toolchain"]["prompt_version"],
                "model_policy_version": snapshot["toolchain"]["model_policy_version"],
            },
            "positioning": {
                "genre": book["genre"],
                "subgenres": [],
                "core_fantasy": "能力与处境持续改善" if has_power else "通过行动改善处境",
                "target_reader": [f"{book['genre']}类型读者"],
                "one_line_selling_point": "受限能力推动主动破局" if has_limit and has_choice else "主角在连续任务中改变处境",
            },
            "protagonist": {
                "initial_deficit": "初始资源或地位不足",
                "long_term_desire": "扩大行动能力并改变当前处境",
                "agency_level": "high" if has_choice else "low",
            },
            "progression": {
                "core_ability": "文本存在明确能力机制" if has_power else "经验与任务能力",
                "limitations": limitations,
                "growth_axes": growth_axes,
            },
            "commercial": {
                "first_visible_payoff_chapter": payoff_chapter,
                "first_volume_promise": "完成初始破局并打开更高层冲突" if has_payoff else "证明主角能够改变当前处境",
            },
            "sustainability": {
                "sources_30_100": growth_axes,
                "mid_stage_risks": risks,
            },
            "evidence": [{
                "field": "deterministic_profile_signals",
                "chapter_indexes": chapter_indexes,
                "feature_codes": feature_codes,
            }],
            "confidence": {
                "level": "low",
                "score": confidence,
                "limitations": ["deterministic keyword baseline; requires LLM and consensus analysis"],
            },
        }


def profile_dir(corpus_root: str | Path, snapshot_id: str) -> Path:
    return Path(corpus_root) / "profiles" / snapshot_id


def write_profile(corpus_root: str | Path, profile: Mapping) -> str:
    path = profile_dir(corpus_root, str(profile["corpus_snapshot_id"])) / f"{profile['id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(profile), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path.relative_to(Path(corpus_root)))


def load_profile(corpus_root: str | Path, snapshot_id: str, profile_id: str) -> dict:
    path = profile_dir(corpus_root, snapshot_id) / f"{profile_id}.json"
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BookProfileError(f"unable to load book narrative profile: {path}") from exc
    if profile.get("corpus_snapshot_id") != snapshot_id:
        raise BookProfileError("profile corpus snapshot binding is invalid")
    return profile
