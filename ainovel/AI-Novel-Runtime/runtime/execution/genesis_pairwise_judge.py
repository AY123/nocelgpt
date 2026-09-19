"""Genesis-specific pairwise judge for comparing complete book proposals.

This judge is deliberately separate from ``pairwise_judge.py``.  The latter is
an instrument for comparing character rendering in two versions of one chapter;
Genesis needs a commercial book-opening rubric and complete proposal context.
Both instruments remain advisory, comparison-only, and never gate production.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Optional, Tuple

from .quality_center import _extract_json


GENESIS_DIMS: Tuple[str, ...] = (
    "logline_hook",
    "protagonist_appeal",
    "core_fantasy",
    "first_visible_payoff",
    "volume_one_promise",
    "thirty_chapter_expandability",
    "hundred_chapter_sustainability",
    "differentiation",
    "originality_risk",
)

GENESIS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "winners": {
            "type": "object",
            "properties": {
                dim: {"type": "string", "enum": ["A", "B", "tie"]}
                for dim in GENESIS_DIMS
            },
            "required": list(GENESIS_DIMS),
            "additionalProperties": False,
        },
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": len(GENESIS_DIMS),
            "maxItems": len(GENESIS_DIMS),
        },
    },
    "required": ["winners", "evidence"],
    "additionalProperties": False,
}

_DIMENSION_GUIDE = """
- logline_hook: 一句话卖点是否清晰、具体、能立即引发阅读欲
- protagonist_appeal: 主角的身份落差、欲望、缺陷与行动引擎是否有吸引力
- core_fantasy: 读者将持续代入和消费的核心幻想是否鲜明
- first_visible_payoff: 最早可见回报是否具体、及时且值得期待
- volume_one_promise: 第一卷的商业承诺、阶段目标与兑现路径是否成立
- thirty_chapter_expandability: 前30章是否能持续升级而非重复同一招
- hundred_chapter_sustainability: 力量、冲突、人物和世界规则能否支撑100章
- differentiation: 与常见同类相比是否有可辨识且可执行的差异
- originality_risk: 哪个方案的原创性风险更低、组合转化更充分（低风险者胜）
""".strip()

_GENESIS_PAIRWISE_TEMPLATE = """# 角色
你是负责新书立项的商业网文总编。你只对两个匿名开书方案做相对比较，不打绝对分。

# 评审规则
逐维判断方案甲或方案乙谁更强。必须使用完整方案材料，不能只根据标题或一句话内核。
若两者在某维确实无法区分才给 tie。originality_risk 维度由原创风险更低者获胜。
甲/乙只代表本次展示位置，不代表基线或优先级。先在心中按书名分别评价两个方案，
再做相对判断；不得因为先出现、篇幅更长或被标为甲而偏好某方案。若优势很小或换位后
可能改变判断，必须给 tie。evidence 使用书名或具体机制说明，不得用展示顺序本身作依据。
为固定推理顺序，无论下方甲乙如何交换，都必须先独立审阅「{review_first}」，
再独立审阅「{review_second}」，最后才映射回本次甲/乙位置输出 winner。

# 九个固定维度
{dimension_guide}

# 方案甲
<<<A>>>
{candidate_a}
<<<END A>>>

# 方案乙
<<<B>>>
{candidate_b}
<<<END B>>>

# 输出契约
严格只输出一个 JSON 对象，不要解释、不要 markdown。必须包含全部九个键；
每个 winner 只能是 "A"、"B" 或 "tie"。为降低结构错误，winners 使用固定九键对象，
evidence 使用与下方九键完全相同顺序的九项字符串数组，每项不超过60个汉字。
输出前自检：winners 必须恰好包含九个键，evidence 必须恰好有九项，所有花括号必须闭合：
{{
  "winners": {{
    "logline_hook": "A|B|tie",
    "protagonist_appeal": "A|B|tie",
    "core_fantasy": "A|B|tie",
    "first_visible_payoff": "A|B|tie",
    "volume_one_promise": "A|B|tie",
    "thirty_chapter_expandability": "A|B|tie",
    "hundred_chapter_sustainability": "A|B|tie",
    "differentiation": "A|B|tie",
    "originality_risk": "A|B|tie"
  }},
  "evidence": ["卖点依据", "主角依据", "幻想依据", "回报依据", "首卷依据", "30章依据", "100章依据", "差异依据", "原创风险依据"]
}}
"""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _review_key(candidate: Mapping[str, Any]) -> str:
    title = str(candidate.get("title") or "未命名方案")
    return f"{title} [{_sha256_text(_canonical_json(candidate))[7:15]}]"


def build_genesis_pairwise_prompt(
        candidate_a: Mapping[str, Any], candidate_b: Mapping[str, Any], *,
        review_order: tuple[str, str] | None = None) -> str:
    order = review_order or tuple(sorted(
        (_review_key(candidate_a), _review_key(candidate_b))))
    return _GENESIS_PAIRWISE_TEMPLATE.format(
        dimension_guide=_DIMENSION_GUIDE,
        review_first=order[0],
        review_second=order[1],
        candidate_a=json.dumps(candidate_a, ensure_ascii=False, sort_keys=True, indent=2),
        candidate_b=json.dumps(candidate_b, ensure_ascii=False, sort_keys=True, indent=2),
    )


def parse_genesis_judge_response(text: str) -> tuple[Optional[dict], Optional[str]]:
    """Strictly parse all nine dimensions from one ordering.

    Markdown-fenced JSON is accepted by the shared extractor.  Missing fields or
    invalid winners are errors, not ordinary ties, because silently converting
    malformed output would overstate judge agreement.
    """
    if not (text or "").strip():
        return None, "empty response"
    obj = _extract_json(text)
    if not isinstance(obj, dict):
        return None, "no JSON object found"
    winners = obj.get("winners")
    evidence = obj.get("evidence")
    if isinstance(winners, dict) or isinstance(evidence, list):
        if not isinstance(winners, dict):
            return None, "compact response requires winners object"
        missing = [dim for dim in GENESIS_DIMS if dim not in winners]
        if missing:
            return None, f"missing dimension: {missing[0]}"
        extra = [key for key in winners if key not in GENESIS_DIMS]
        if extra:
            return None, f"unexpected dimension: {extra[0]}"
        if not isinstance(evidence, list) or len(evidence) != len(GENESIS_DIMS):
            return None, f"evidence must contain exactly {len(GENESIS_DIMS)} items"
        parsed = {}
        for index, dim in enumerate(GENESIS_DIMS):
            winner = str(winners.get(dim) or "").strip().lower()
            if winner not in ("a", "b", "tie"):
                return None, f"invalid winner for {dim}: {winners.get(dim)!r}"
            parsed[dim] = {"slot": winner, "evidence": str(evidence[index] or "")}
        return parsed, None
    parsed = {}
    for dim in GENESIS_DIMS:
        if dim not in obj:
            return None, f"missing dimension: {dim}"
        cell = obj[dim]
        if not isinstance(cell, dict):
            return None, f"dimension {dim} must be an object"
        if "winner" not in cell or "evidence" not in cell:
            return None, f"dimension {dim} requires winner and evidence"
        winner = str(cell.get("winner") or "").strip().lower()
        if winner not in ("a", "b", "tie"):
            return None, f"invalid winner for {dim}: {cell.get('winner')!r}"
        parsed[dim] = {
            "slot": winner,
            "evidence": str(cell.get("evidence") or ""),
        }
    return parsed, None


def _provider_model(model, output=None) -> tuple[str, str]:
    provider = str(
        getattr(model, "primary_provider", None)
        or getattr(model, "provider", None)
        or "unknown"
    )
    model_id = str(
        getattr(output, "model_id", None)
        or getattr(model, "model_id", None)
        or "unknown"
    )
    return provider, model_id


def _call_provenance(model, output, prompt: str, text: str) -> dict:
    provider, model_id = _provider_model(model, output)
    response = getattr(model, "last_response", None)
    usage = getattr(response, "token_usage", None)
    cost = getattr(response, "cost", None)
    request = getattr(model, "last_request", None)
    if request is not None:
        from ..llm.replay import stable_request_hash
        request_hash = stable_request_hash(request)
    else:
        request_hash = _sha256_text(_canonical_json({
            "provider": provider, "model": model_id, "prompt": prompt,
        }))
    return {
        "provider": provider,
        "model": model_id,
        "request_hash": request_hash,
        "prompt_hash": _sha256_text(prompt),
        "response_hash": (getattr(response, "response_hash", None)
                          or _sha256_text(text)),
        "token_usage": asdict(usage) if usage is not None else None,
        "cost": asdict(cost) if cost is not None else None,
        "cost_status": "priced" if cost is not None else "unpriced",
        "provider_request_id": getattr(response, "provider_request_id", None),
    }


@dataclass(frozen=True)
class GenesisPairwiseComparison:
    reviewer: str
    label_a: str
    label_b: str
    dimensions: dict[str, dict[str, Any]]
    winner: str
    judge_provenance: dict[str, Any]
    axis: str = "evaluative"
    gating: bool = False
    comparison_only: bool = True
    calibrates: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer": self.reviewer,
            "axis": self.axis,
            "gating": self.gating,
            "comparison_only": self.comparison_only,
            "calibrates": self.calibrates,
            "label_a": self.label_a,
            "label_b": self.label_b,
            "dimensions": self.dimensions,
            "winner": self.winner,
            "judge_provenance": self.judge_provenance,
        }


def _empty_dimensions() -> dict[str, dict[str, Any]]:
    return {
        dim: {
            "verdict": "tie",
            "order_ab": None,
            "order_ba": None,
            "position_consistent": None,
            "evidence": "",
        }
        for dim in GENESIS_DIMS
    }


def _combine(order_ab: dict, order_ba: dict) -> tuple[dict, int]:
    dimensions = {}
    consistent = 0
    for dim in GENESIS_DIMS:
        ab = order_ab[dim]["slot"]
        ba_raw = order_ba[dim]["slot"]
        ba = {"a": "b", "b": "a", "tie": "tie"}[ba_raw]
        agrees = ab == ba
        if agrees:
            consistent += 1
        verdict = ab if agrees and ab in ("a", "b") else "tie"
        dimensions[dim] = {
            "verdict": verdict,
            "order_ab": ab,
            "order_ba": ba,
            "position_consistent": agrees,
            "evidence": order_ab[dim]["evidence"] or order_ba[dim]["evidence"],
        }
    return dimensions, consistent


def _winner(dimensions: Mapping[str, Mapping[str, Any]]) -> str:
    a_wins = sum(1 for item in dimensions.values() if item["verdict"] == "a")
    b_wins = sum(1 for item in dimensions.values() if item["verdict"] == "b")
    if a_wins > b_wins:
        return "a"
    if b_wins > a_wins:
        return "b"
    return "tie"


def compare_genesis_candidates(
    candidate_a: Mapping[str, Any],
    candidate_b: Mapping[str, Any],
    model,
    *,
    label_a: str,
    label_b: str,
    reviewer_id: str = "genesis-pairwise-judge-v1",
) -> GenesisPairwiseComparison:
    calls = {}
    review_order = tuple(sorted(
        (_review_key(candidate_a), _review_key(candidate_b))))

    def call(order: str, first: Mapping[str, Any], second: Mapping[str, Any]):
        prompt = build_genesis_pairwise_prompt(
            first, second, review_order=review_order)
        try:
            if (getattr(model, "supports_structured_output", False)
                    and hasattr(model, "generate_structured")):
                output = model.generate_structured(
                    prompt, GENESIS_RESPONSE_SCHEMA,
                    tool_name="submit_genesis_verdict")
            else:
                output = model.generate(prompt)
            text = str(getattr(output, "text", "") or "")
            record = _call_provenance(model, output, prompt, text)
        except Exception as exc:
            provider, model_id = _provider_model(model)
            request = getattr(model, "last_request", None)
            if request is not None:
                from ..llm.replay import stable_request_hash
                request_hash = stable_request_hash(request)
            else:
                request_hash = _sha256_text(_canonical_json({
                    "provider": provider, "model": model_id, "prompt": prompt,
                }))
            record = {
                "provider": provider,
                "model": model_id,
                "request_hash": request_hash,
                "prompt_hash": _sha256_text(prompt),
                "response_hash": None,
                "token_usage": None,
                "cost": None,
                "cost_status": "unpriced",
                "provider_request_id": None,
                "parse_ok": False,
                "error": f"provider error: {exc.__class__.__name__}: {exc}",
                "raw_response_summary": "",
            }
            calls[order] = record
            return None
        parsed, error = parse_genesis_judge_response(text)
        record["parse_ok"] = parsed is not None
        record["error"] = f"parse error: {error}" if error else None
        record["raw_response_summary"] = text[:500] if error else None
        calls[order] = record
        return parsed

    order_ab = call("order_ab", candidate_a, candidate_b)
    order_ba = call("order_ba", candidate_b, candidate_a)
    degraded = order_ab is None or order_ba is None
    if degraded:
        dimensions = _empty_dimensions()
        consistent = 0
        winner = "tie"
    else:
        dimensions, consistent = _combine(order_ab, order_ba)
        winner = _winner(dimensions)

    provider, model_id = _provider_model(model)
    provenance = {
        "provider": provider,
        "model": model_id,
        "degraded": degraded,
        "reason": "one or both pairwise calls failed" if degraded else None,
        "call_errors": {
            order: record.get("error")
            for order, record in calls.items()
            if record.get("error")
        },
        "calls": calls,
        "position_consistent_dimensions": consistent if not degraded else None,
        "position_total_dimensions": len(GENESIS_DIMS) if not degraded else None,
        "position_consistency_rate": (
            round(consistent / len(GENESIS_DIMS), 4) if not degraded else None
        ),
    }
    return GenesisPairwiseComparison(
        reviewer=reviewer_id,
        label_a=label_a,
        label_b=label_b,
        dimensions=dimensions,
        winner=winner,
        judge_provenance=provenance,
    )
