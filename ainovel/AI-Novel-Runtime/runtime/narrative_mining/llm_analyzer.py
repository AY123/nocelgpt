"""Independent top-down and bottom-up LLM passes for book profiling."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping

from ..reference.segment import segment_reference_novel

SCHEMA_VERSION = "1.0"
KIND = "book_profile_analysis_pass"
ANALYZER_VERSION = "llm-book-profile-two-pass-v1"
_ALLOWED_FINDINGS = (
    "core_fantasy", "target_reader", "selling_point", "protagonist_deficit",
    "long_term_desire", "core_ability", "limitations", "growth_axes",
    "first_visible_payoff_chapter", "first_volume_promise",
    "sustainability_sources", "mid_stage_risks",
)

_PROMPT = """你是中文商业网文语料分析器。执行{pass_name}分析，只抽象叙事机制。
作品内部ID：{book_id}；题材：{genre}；章节材料：
{material}
只输出JSON对象，字段必须为：findings、evidence、confidence。
findings 必须含 core_fantasy,target_reader,selling_point,protagonist_deficit,long_term_desire,
core_ability,limitations,growth_axes,first_visible_payoff_chapter,first_volume_promise,
sustainability_sources,mid_stage_risks。
evidence 每项只允许 field、chapter_indexes、feature_codes，禁止原文、摘录、角色名、作品名。
confidence 必须含 level(low/medium/high)、score(0-1)、limitations。
无法可靠判断时使用空字符串/空数组/null并降低置信度。"""


def _extract_json(text: str):
    match = re.search(r"\{[\s\S]*\}", text or "")
    if not match:
        raise ValueError("no JSON object found in model response")
    return json.loads(match.group(0))


class LLMBookProfileAnalyzer:
    def __init__(self, model):
        self.model = model

    def analyze_pass(self, book: Mapping, text: str, *, snapshot: Mapping, pass_type: str) -> dict:
        if pass_type not in {"top_down", "bottom_up"}:
            raise ValueError(f"unsupported book profile pass: {pass_type}")
        chapters = segment_reference_novel(str(book["id"]), text)
        material = _material(chapters, text, pass_type)
        prompt = _PROMPT.format(
            pass_name="自上而下" if pass_type == "top_down" else "自下而上",
            book_id=book["id"], genre=book["genre"], material=material,
        )
        try:
            response = self.model.generate(prompt)
            payload = _extract_json(getattr(response, "text", ""))
            findings = _normalize_findings(payload.get("findings") if isinstance(payload, dict) else None)
            evidence = _normalize_evidence(payload.get("evidence") if isinstance(payload, dict) else None)
            confidence = _normalize_confidence(payload.get("confidence") if isinstance(payload, dict) else None)
            status = "completed" if findings is not None and evidence is not None and confidence is not None else "degraded"
        except Exception:
            findings = evidence = confidence = None
            status = "degraded"
        return _envelope(book, snapshot, pass_type, status, findings, evidence, confidence)


def _material(chapters, text: str, pass_type: str) -> str:
    bodies = [chapter.body for chapter in chapters]
    if not bodies:
        bodies = [text]
    indexes = range(len(bodies)) if pass_type == "top_down" else range(len(bodies))
    lines = []
    for i in list(indexes)[:12]:
        compact = " ".join(bodies[i].split())[:600]
        lines.append(f"[chapter_index={i + 1}] {compact}")
    return "\n".join(lines)


def _normalize_findings(value):
    if not isinstance(value, dict) or any(key not in value for key in _ALLOWED_FINDINGS):
        return None
    out = {key: value[key] for key in _ALLOWED_FINDINGS}
    list_fields = {"target_reader", "limitations", "growth_axes", "sustainability_sources", "mid_stage_risks"}
    if any(not isinstance(out[key], list) for key in list_fields):
        return None
    if out["first_visible_payoff_chapter"] is not None and not isinstance(out["first_visible_payoff_chapter"], int):
        return None
    for key in set(_ALLOWED_FINDINGS) - list_fields - {"first_visible_payoff_chapter"}:
        if not isinstance(out[key], str):
            return None
    return out


def _normalize_evidence(value):
    if not isinstance(value, list):
        return None
    out = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"field", "chapter_indexes", "feature_codes"}:
            return None
        if not isinstance(item["chapter_indexes"], list) or not isinstance(item["feature_codes"], list):
            return None
        out.append({"field": str(item["field"]), "chapter_indexes": item["chapter_indexes"], "feature_codes": item["feature_codes"]})
    return out


def _normalize_confidence(value):
    if not isinstance(value, dict) or set(value) != {"level", "score", "limitations"}:
        return None
    if value["level"] not in {"low", "medium", "high"} or not isinstance(value["score"], (int, float)) or not isinstance(value["limitations"], list):
        return None
    return {"level": value["level"], "score": max(0.0, min(1.0, float(value["score"]))), "limitations": value["limitations"]}


def _envelope(book, snapshot, pass_type, status, findings, evidence, confidence):
    empty = {
        "core_fantasy": "", "target_reader": [], "selling_point": "",
        "protagonist_deficit": "", "long_term_desire": "", "core_ability": "",
        "limitations": [], "growth_axes": [], "first_visible_payoff_chapter": None,
        "first_volume_promise": "", "sustainability_sources": [], "mid_stage_risks": [],
    }
    suffix = "TOPDOWN" if pass_type == "top_down" else "BOTTOMUP"
    return {
        "id": f"BPA-{str(book['id']).removeprefix('CBK-')}-{suffix}",
        "kind": KIND, "schema_version": SCHEMA_VERSION, "book_id": book["id"],
        "corpus_snapshot_id": snapshot["id"], "corpus_manifest_hash": snapshot["manifest_hash"],
        "pass_type": pass_type, "status": status,
        "analysis": {"analyzer_version": ANALYZER_VERSION, "prompt_version": snapshot["toolchain"]["prompt_version"], "model_policy_version": snapshot["toolchain"]["model_policy_version"]},
        "findings": findings or empty,
        "evidence": evidence or [],
        "confidence": confidence or {"level": "low", "score": 0.0, "limitations": ["model pass failed or returned invalid structured output"]},
    }


def write_analysis_pass(corpus_root: str | Path, result: Mapping) -> str:
    root = Path(corpus_root)
    path = root / "analysis-passes" / str(result["corpus_snapshot_id"]) / str(result["book_id"]) / f"{result['pass_type']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path.relative_to(root))
