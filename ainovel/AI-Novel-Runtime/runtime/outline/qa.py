"""qa.py — two-axis QA for a novel outline (ANES v2, ADR-003).

Mirrors the runtime's draft_qa/draft_review split so the same discipline that
governs chapter drafts governs outlines:

  - DETERMINISTIC checks (check_outline): objective, pass/fail, reproducible.
    They MAY gate the workflow. A skeleton missing its commercial engine, its
    opening hooks, or its per-volume escalation is structurally incomplete and
    must not become a final outline.
  - EVALUATIVE checks (review_outline / review_outline_with_model): judgments
    about hook strength, reward density, commercial viability. ADVISORY ONLY —
    they ride the trend axis and NEVER gate (ADR-003).  The heuristic and model
    reports remain separate so model output cannot masquerade as a hard check.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, List

from ..execution.quality_center import _extract_json


# --------------------------------------------------------------------------- #
# Deterministic axis — MAY gate                                               #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class OutlineFinding:
    check: str
    message: str

    def __str__(self) -> str:
        return f"[error] outline-qa/{self.check}: {self.message}"


def check_outline(outline: dict, *, min_opening_hooks: int = 3) -> List[OutlineFinding]:
    """Deterministic structural completeness checks on an outline skeleton.

    Every check is an objective presence/shape test — no taste judgments — so it
    is reproducible and may block the workflow from emitting a final outline.
    """
    out: List[OutlineFinding] = []

    # Commercial engine must exist and the golden finger must carry a cost,
    # otherwise reward is not sustainable (the core failure mode of the v0.2
    # hardcoded synthesizer).
    engine = outline.get("protagonist_engine") or {}
    if not engine.get("golden_finger", "").strip():
        out.append(OutlineFinding("protagonist-engine",
                                  "protagonist_engine.golden_finger is empty"))
    if not engine.get("cost", "").strip():
        out.append(OutlineFinding("golden-finger-cost",
                                  "golden_finger has no cost; reward is not sustainable"))

    # Progression system (or power_system) tiers back the conflict ladder.
    # Support both old "power_system" and new "progression_system"
    progression = outline.get("progression_system") or outline.get("power_system") or {}
    tiers = progression.get("tiers") or []
    if not tiers:
        out.append(OutlineFinding("power-system",
                                  "progression_system/power_system.tiers is empty"))

    ladder = outline.get("conflict_ladder") or []
    if len(ladder) < 2:
        out.append(OutlineFinding("conflict-ladder",
                                  "conflict_ladder needs at least 2 escalating levels"))

    # Reward loop cadence must be a short, concrete promise to the reader.
    loop = outline.get("reward_loop") or {}
    cadence = loop.get("cadence_chapters")
    if not isinstance(cadence, int) or cadence < 1:
        out.append(OutlineFinding("reward-loop",
                                  "reward_loop.cadence_chapters must be a positive integer"))

    # Opening hooks: the retention battlefield. Require the first N chapters and
    # a non-empty end_hook on each.
    opening = outline.get("first_30_chapters") or []
    if len(opening) < min_opening_hooks:
        out.append(OutlineFinding("opening-hooks",
                                  f"first_30_chapters has {len(opening)} entries; "
                                  f"need at least {min_opening_hooks}"))
    for ch in opening[:min_opening_hooks]:
        if not str(ch.get("end_hook", "")).strip():
            out.append(OutlineFinding("chapter-end-hook",
                                      f"chapter {ch.get('chapter_no', '?')} has no end_hook"))

    # Every volume must carry escalation scaffolding, not just a purpose blurb.
    for vol in outline.get("plot", {}).get("volumes", []):
        vid = vol.get("id", "?")
        for field_name in ("oppressor", "twist"):
            if not str(vol.get(field_name, "")).strip():
                out.append(OutlineFinding("volume-escalation",
                                          f"volume {vid} missing {field_name}"))

    return out


# --------------------------------------------------------------------------- #
# Evaluative axis — ADVISORY, never gates                                     #
# --------------------------------------------------------------------------- #
AXIS_EVALUATIVE = "evaluative"
SEVERITIES = ("info", "warning", "error")

OUTLINE_REVIEW_CHECKS = (
    "opening_hook",
    "protagonist_engine",
    "core_fantasy",
    "reward_progression",
    "volume_one_promise",
    "thirty_chapter_progression",
    "long_run_sustainability",
    "character_world_leverage",
    "originality_risk",
)

OUTLINE_REVIEW_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "assessments": {
            "type": "object",
            "properties": {
                check: {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": list(SEVERITIES)},
                        "message": {
                            "type": "string", "minLength": 1, "maxLength": 160,
                        },
                    },
                    "required": ["severity", "message"],
                    "additionalProperties": False,
                }
                for check in OUTLINE_REVIEW_CHECKS
            },
            "required": list(OUTLINE_REVIEW_CHECKS),
            "additionalProperties": False,
        },
        "summary": {
            "type": "string", "minLength": 1, "maxLength": 240,
        },
    },
    "required": ["assessments", "summary"],
    "additionalProperties": False,
}

_OUTLINE_REVIEW_GUIDE = """
- opening_hook: 开篇冲突、悬念与前三章留存力
- protagonist_engine: 主角欲望、缺陷、行动能力与金手指代价
- core_fantasy: 读者持续代入的核心幻想是否鲜明且可兑现
- reward_progression: 回报密度、类型变化与升级节奏
- volume_one_promise: 第一卷阶段目标、对手、转折与兑现路径
- thirty_chapter_progression: 前30章是否逐步升级而非重复同一机制
- long_run_sustainability: 冲突、力量、关系和世界规则能否支撑100章以上
- character_world_leverage: 配角关系和世界规则是否真正制造选择与冲突
- originality_risk: 是否只是表层拼贴，差异化机制能否转化为具体剧情
""".strip()

_OUTLINE_REVIEW_PROMPT = """# 角色
你是负责新书立项与长篇连载诊断的商业网文总编。

# 任务
完整审阅下方已经合成的新书大纲。逐项指出可执行的优势或风险，不改写大纲，
不做发布决定。severity 仅表示建议优先级：info=成立或轻微建议，
warning=会影响留存或展开，error=严重商业/叙事风险。所有结论均为咨询意见，不能作为构建门禁。

# 九项固定量尺
{guide}

# 完整大纲
<<<OUTLINE>>>
{outline}
<<<END OUTLINE>>>

# 输出契约
严格只输出一个 JSON 对象，不要解释、不要 markdown。assessments 必须恰好包含上述九个键；
每项必须包含 severity 和非空 message。每项 message 不超过80个汉字，summary 不超过120个汉字；
只写最关键的具体依据，不展开成长段分析：
{{
  "assessments": {{
    "opening_hook": {{"severity": "info|warning|error", "message": "具体依据"}},
    "protagonist_engine": {{"severity": "info|warning|error", "message": "具体依据"}},
    "core_fantasy": {{"severity": "info|warning|error", "message": "具体依据"}},
    "reward_progression": {{"severity": "info|warning|error", "message": "具体依据"}},
    "volume_one_promise": {{"severity": "info|warning|error", "message": "具体依据"}},
    "thirty_chapter_progression": {{"severity": "info|warning|error", "message": "具体依据"}},
    "long_run_sustainability": {{"severity": "info|warning|error", "message": "具体依据"}},
    "character_world_leverage": {{"severity": "info|warning|error", "message": "具体依据"}},
    "originality_risk": {{"severity": "info|warning|error", "message": "具体依据"}}
  }},
  "summary": "总体判断"
}}
"""


@dataclass(frozen=True)
class OutlineReviewFinding:
    check: str
    severity: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] outline-review/{self.check}: {self.message}"


@dataclass(frozen=True)
class OutlineReviewReport:
    reviewer: str
    axis: str = AXIS_EVALUATIVE   # structural invariant
    gating: bool = False          # structural invariant — never blocks
    findings: List[OutlineReviewFinding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "axis": self.axis,
            "gating": self.gating,
            "findings": [
                {"check": f.check, "severity": f.severity, "message": f.message}
                for f in self.findings
            ],
        }


@dataclass(frozen=True)
class LLMOutlineReviewReport:
    reviewer: str
    status: str
    findings: List[OutlineReviewFinding]
    summary: str | None
    provenance: dict[str, Any]
    axis: str = AXIS_EVALUATIVE
    gating: bool = False

    def to_dict(self) -> dict:
        return {
            "reviewer": self.reviewer,
            "axis": self.axis,
            "gating": self.gating,
            "status": self.status,
            "findings": [
                {"check": f.check, "severity": f.severity, "message": f.message}
                for f in self.findings
            ],
            "summary": self.summary,
            "provenance": self.provenance,
        }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_outline_review_prompt(outline: dict) -> str:
    return _OUTLINE_REVIEW_PROMPT.format(
        guide=_OUTLINE_REVIEW_GUIDE,
        outline=json.dumps(outline, ensure_ascii=False, sort_keys=True, indent=2),
    )


def parse_outline_review_response(
        text: str) -> tuple[list[OutlineReviewFinding] | None, str | None, str | None]:
    """Parse the complete fixed-axis model contract without silent defaults."""
    if not (text or "").strip():
        return None, None, "empty response"
    obj = _extract_json(text)
    if not isinstance(obj, dict):
        return None, None, "no JSON object found"
    extra_top = [key for key in obj if key not in ("assessments", "summary")]
    if extra_top:
        return None, None, f"unexpected field: {extra_top[0]}"
    assessments = obj.get("assessments")
    if not isinstance(assessments, dict):
        return None, None, "assessments must be an object"
    missing = [check for check in OUTLINE_REVIEW_CHECKS if check not in assessments]
    if missing:
        return None, None, f"missing assessment: {missing[0]}"
    extra = [check for check in assessments if check not in OUTLINE_REVIEW_CHECKS]
    if extra:
        return None, None, f"unexpected assessment: {extra[0]}"
    summary = obj.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return None, None, "summary must be a non-empty string"

    findings = []
    for check in OUTLINE_REVIEW_CHECKS:
        cell = assessments[check]
        if not isinstance(cell, dict):
            return None, None, f"assessment {check} must be an object"
        extra_cell = [key for key in cell if key not in ("severity", "message")]
        if extra_cell:
            return None, None, f"unexpected field for {check}: {extra_cell[0]}"
        severity = cell.get("severity")
        if severity not in SEVERITIES:
            return None, None, f"invalid severity for {check}: {severity!r}"
        message = cell.get("message")
        if not isinstance(message, str) or not message.strip():
            return None, None, f"message for {check} must be a non-empty string"
        findings.append(OutlineReviewFinding(check, severity, message.strip()))
    return findings, summary.strip(), None


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


def _request_hash(model, provider: str, model_id: str, prompt: str) -> str:
    request = getattr(model, "last_request", None)
    if request is not None:
        from ..llm.replay import stable_request_hash
        return stable_request_hash(request)
    return _sha256_text(_canonical_json({
        "provider": provider, "model": model_id, "prompt": prompt,
    }))


def review_outline_with_model(
        outline: dict, model, *, reviewer_id: str = "outline-llm-reviewer-v1",
) -> LLMOutlineReviewReport:
    """Run the advisory LM review. Every failure degrades; none can gate."""
    prompt = build_outline_review_prompt(outline)
    outline_hash = _sha256_text(_canonical_json(outline))
    try:
        if (getattr(model, "supports_structured_output", False)
                and hasattr(model, "generate_structured")):
            output = model.generate_structured(
                prompt, OUTLINE_REVIEW_RESPONSE_SCHEMA,
                tool_name="submit_outline_review")
        else:
            output = model.generate(prompt)
        text = str(getattr(output, "text", "") or "")
    except Exception as exc:
        provider, model_id = _provider_model(model)
        provenance = {
            "provider": provider,
            "model": model_id,
            "outline_hash": outline_hash,
            "request_hash": _request_hash(model, provider, model_id, prompt),
            "prompt_hash": _sha256_text(prompt),
            "response_hash": None,
            "token_usage": None,
            "cost": None,
            "cost_status": "unpriced",
            "provider_request_id": None,
            "finish_reason": None,
            "response_char_count": 0,
            "parse_ok": False,
            "error": f"provider error: {exc.__class__.__name__}: {exc}",
            "raw_response_summary": "",
        }
        return LLMOutlineReviewReport(
            reviewer=f"{reviewer_id}:{provider}:{model_id}",
            status="degraded", findings=[], summary=None, provenance=provenance)

    provider, model_id = _provider_model(model, output)
    response = getattr(model, "last_response", None)
    usage = getattr(response, "token_usage", None)
    cost = getattr(response, "cost", None)
    findings, summary, error = parse_outline_review_response(text)
    provenance = {
        "provider": provider,
        "model": model_id,
        "outline_hash": outline_hash,
        "request_hash": _request_hash(model, provider, model_id, prompt),
        "prompt_hash": _sha256_text(prompt),
        "response_hash": (getattr(response, "response_hash", None)
                          or _sha256_text(text)),
        "token_usage": asdict(usage) if usage is not None else None,
        "cost": asdict(cost) if cost is not None else None,
        "cost_status": "priced" if cost is not None else "unpriced",
        "provider_request_id": getattr(response, "provider_request_id", None),
        "finish_reason": (getattr(response, "finish_reason", None)
                          or getattr(output, "finish_reason", None)),
        "response_char_count": len(text),
        "parse_ok": findings is not None,
        "error": f"parse error: {error}" if error else None,
        "raw_response_summary": text[:500] if error else None,
    }
    return LLMOutlineReviewReport(
        reviewer=f"{reviewer_id}:{provider}:{model_id}",
        status="completed" if findings is not None else "degraded",
        findings=findings or [], summary=summary, provenance=provenance)


def review_outline(outline: dict, *, reviewer_id: str = "heuristic-outline-reviewer-v1") -> OutlineReviewReport:
    """Cheap deterministic heuristics on the advisory axis; never a gate."""
    findings: List[OutlineReviewFinding] = []

    opening = outline.get("first_30_chapters") or []
    rewarded = [ch for ch in opening[:3] if str(ch.get("reward_if_any", "")).strip()]
    if opening and not rewarded:
        findings.append(OutlineReviewFinding(
            "reward-density", "warning",
            "no reward is cashed in the first 3 chapters; early drop risk"))

    loop = outline.get("reward_loop") or {}
    cadence = loop.get("cadence_chapters")
    if isinstance(cadence, int) and cadence > 5:
        findings.append(OutlineReviewFinding(
            "reward-cadence", "warning",
            f"reward cadence of {cadence} chapters may feel slow for web serials"))

    if not findings:
        findings.append(OutlineReviewFinding(
            "heuristic-clear", "info",
            "heuristic outline review found no configured commercial warnings"))

    return OutlineReviewReport(reviewer=reviewer_id, findings=findings)
