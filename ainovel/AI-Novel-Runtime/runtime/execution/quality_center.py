"""quality_center.py — Novel Quality Center (ANES v2, ADR-003 evaluative axis).

The Quality Center scores a finished chapter draft on commercial + craft
dimensions and emits a per-issue revision plan. It is the EVALUATIVE counterpart
to draft_qa.py, and it plugs into the SAME DraftReviewer seam that
draft_review.py defines (run.py already accepts `reviewer=` and rides the report
on the envelope). So this is a drop-in: no control-flow change, no touch to the
frozen ChapterDraft schema.

Two structural invariants, enforced here AND by quality-report.schema.json:
  - axis is always "evaluative"
  - gating is always False

A quality report can therefore NEVER block a build, no matter what the model
returns. Predictive signals (subscription/retention) are kept OUT of the gating
path entirely and marked comparison-only — they are for choosing between two
revisions, not for asserting an absolute truth (the North Star discussion).

The judge depends only on the execution Model protocol (`generate(prompt) ->
.text`), so a real LLM (LLMExecutionModel) drops in unchanged, and a fake model
proves the parsing/degradation logic in CI without network.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from typing import List, Optional

AXIS_EVALUATIVE = "evaluative"   # structural invariant — never gates (ADR-003)

# v1 dimensions — REQUIRED by both quality-report v1 and v2 schemas. Never remove
# one: existing consumers (RevisionController, Review-Panel synthesis, Dashboard)
# hard-read them, and removing one breaks a mixed v1/v2 serial (Phase 4 invariant #1).
V1_DIMENSIONS = (
    "hook",
    "conflict",
    "reward_density",
    "character_consistency",
    "world_consistency",
    "emotion",
    "commercial",          # in v2 this is a ROLL-UP; the dims below decompose it
    "originality_risk",
)

# v2 commercial-decomposition dimensions (Phase 4.1). Optional in the schema, but
# quality_center always emits them (coerced to 0 when the judge omits one), so the
# emitted report is a full v2 report while still validating v1 readers via the tuple.
V2_DIMENSIONS = (
    "retention",
    "subscription",
    "payoff",
    "curiosity",
    "promise_delivery",
    "pacing",
    "character_growth",
    "serial_sustainability",
    "reader_drop_risk",
    "safety_risk",         # SUBJECTIVE edginess only; deterministic red-line is a separate gate
)

SCORE_DIMENSIONS = V1_DIMENSIONS + V2_DIMENSIONS


def quality_judge_output_schema() -> dict:
    """Provider-enforced minimum output contract for quality judges."""
    score_properties = {
        dimension: {"type": "integer", "minimum": 0, "maximum": 100}
        for dimension in SCORE_DIMENSIONS
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "scores": {
                "type": "object",
                "additionalProperties": False,
                "properties": score_properties,
                "required": list(SCORE_DIMENSIONS),
            },
            "dimensions": {"type": "array", "items": {"type": "object"}},
            "revision_plan": {"type": "array", "items": {"type": "object"}},
            "predictions": {"type": "object"},
        },
        "required": ["scores", "dimensions", "revision_plan", "predictions"],
    }

# Dimensions where LOWER is better (risk scores). Single source of truth — imported
# by revision.py so the "did it improve?" comparison agrees with the judge.
LOWER_IS_BETTER = frozenset({"originality_risk", "reader_drop_risk", "safety_risk"})

# A dimension scoring below this is expected to carry a revision_plan entry.
# Advisory only — never gates.
REVISION_THRESHOLD = 80


@dataclass(frozen=True)
class QualityReport:
    reviewer: str
    scores: dict                       # {dimension: 0-100}
    dimensions: List[dict] = field(default_factory=list)
    revision_plan: List[dict] = field(default_factory=list)
    predictions: Optional[dict] = None
    findings: List[dict] = field(default_factory=list)
    judge_provenance: Optional[dict] = None
    panel: Optional[dict] = None
    axis: str = AXIS_EVALUATIVE        # structural invariant
    gating: bool = False               # structural invariant — never blocks

    def to_dict(self) -> dict:
        out = {
            "reviewer": self.reviewer,
            "axis": self.axis,
            "gating": self.gating,
            "scores": self.scores,
            "dimensions": self.dimensions,
            "revision_plan": self.revision_plan,
            "findings": self.findings,
        }
        if self.predictions is not None:
            out["predictions"] = self.predictions
        if self.judge_provenance is not None:
            out["judge_provenance"] = self.judge_provenance
        if self.panel is not None:
            out["panel"] = self.panel
        return out

    # QualityReport satisfies the DraftReviewer.review() consumer in run.py:
    # envelope.wrap(qa_review=report.to_dict()) just needs a dict with these keys.


def _zero_scores() -> dict:
    return {dim: 0 for dim in SCORE_DIMENSIONS}


def degraded_report(reviewer: str, reason: str, *, model_id: str = "") -> QualityReport:
    """A structurally-valid EMPTY report used when the judge output cannot be
    trusted (unparseable / schema-invalid / model error). It records that the
    evaluative axis ran but was degraded, so audits distinguish 'judged, all
    zero because degraded' from 'never judged'. It NEVER gates."""
    return QualityReport(
        reviewer=reviewer,
        scores=_zero_scores(),
        dimensions=[],
        revision_plan=[],
        findings=[{
            "check": "judge-degraded",
            "severity": "warning",
            "message": f"quality judge output was not usable: {reason}; "
                       f"emitted a non-gating empty report (ADR-003)",
        }],
        judge_provenance={"model_id": model_id, "parse_ok": False, "degraded": True},
    )


# How far the overall quality mean may drop chapter-to-chapter before it reads as
# a REAL regression (not scoring jitter). Conservative — advisory, never gates.
_REGRESSION_MARGIN = 5.0


def _overall_quality(scores: dict) -> Optional[float]:
    """The mean quality across all scored dimensions, with risk dimensions
    (LOWER_IS_BETTER) inverted so higher always means better — the same
    orientation revision.py uses for its 'did it improve?' comparison. Returns
    None when no numeric scores are present."""
    vals = []
    for dim, v in (scores or {}).items():
        if not isinstance(v, (int, float)):
            continue
        vals.append((100 - v) if dim in LOWER_IS_BETTER else v)
    if not vals:
        return None
    return sum(vals) / len(vals)


def is_degraded_scores(qa_review: Optional[dict]) -> bool:
    """True when a QA review's scores cannot be trusted: judge_provenance flags it
    degraded, OR every numeric score is zero (the judge's 'cannot evaluate'
    sentinel — its prompt says output all-zero when it can't assess). Detected on
    the RAW scores, before any risk-dim inversion (an all-zero report inverts to
    overall≈16.7, so an inverted mean never reveals it). Any consumer that folds
    scores across chapters (verdict, retention curve) must exclude these so one
    un-evaluable chapter doesn't poison a baseline."""
    if not qa_review:
        return False
    scores = qa_review.get("scores")
    if not isinstance(scores, dict) or not scores:
        return False
    if (qa_review.get("judge_provenance") or {}).get("degraded"):
        return True
    raw_numeric = [v for v in scores.values() if isinstance(v, (int, float))]
    return bool(raw_numeric) and not any(raw_numeric)


def chapter_quality_verdict(qa_review: Optional[dict],
                            prev_scores: Optional[dict]) -> Optional[str]:
    """Derive a chapter's quality VERDICT from its QA review + the previous
    chapter's scores. This is the cross-chapter fold the director feedback
    (Phase 7.3) reads: it keys on 'regressed'/'degraded' to shape the next
    chapter's objective.

      - 'degraded' — the judge output was not trustworthy (judge_provenance
        marks degraded, or every score is zero): the axis ran but can't be read.
      - 'regressed' — the overall quality mean dropped vs the previous chapter by
        more than _REGRESSION_MARGIN (a real decline, not jitter).
      - None (clean) — no scores (a deterministic reviewer never produces them,
        so a default serial stays byte-identical), first chapter (no prior to
        compare), or a stable/rising chapter.

    Pure and deterministic (ADR-003): advisory only, never gates."""
    if not qa_review:
        return None
    scores = qa_review.get("scores")
    if not isinstance(scores, dict) or not scores:
        return None
    # An un-evaluable report (provenance-degraded or the all-zero sentinel) reads
    # as degraded, NOT regressed — even though its inverted mean (~16.7) looks like
    # a huge drop. is_degraded_scores checks the RAW scores before inversion.
    if is_degraded_scores(qa_review):
        return "degraded"
    overall = _overall_quality(scores)
    if overall is None:
        return "degraded"
    if prev_scores:
        prev_overall = _overall_quality(prev_scores)
        if prev_overall is not None and (prev_overall - overall) > _REGRESSION_MARGIN:
            return "regressed"
    return None


# --------------------------------------------------------------------------- #
# Contracted judge prompt (Role/Goal/Inputs/Constraints/Evaluation/Output/     #
# FailurePolicy). Kept as a single template here for v1; it graduates to a     #
# versioned prompt-contract artifact once a 2nd judge exists (ROADMAP: no      #
# consumer = stub).                                                            #
# --------------------------------------------------------------------------- #
_JUDGE_SYSTEM = (
    "你是一名拥有百万字网文经验的商业小说总编，同时精通文学性与追读商业性。"
    "你只做评审，绝不改写正文。你的评审必须客观、可执行、引用正文证据。"
)

_JUDGE_TEMPLATE = """# Role
网文商业总编 + 质量评审官。
{role_focus}
# Goal
审查下面这一章是否具备持续追读价值，给出 0-100 的分项评分和逐条可执行修改单。
你不重写正文，只诊断。

# Inputs
- 章节任务目标: {goal}
- 本章绑定的设定事实(Registry facts，人物/世界规则，正文不得与之冲突):
{context}{grounding}
- 章节正文:
<<<CHAPTER>>>
{body}
<<<END>>>

# Evaluation Dimensions (每项 0-100)
## 基础维度 (v1)
- hook: 开篇与章末钩子能否勾住读者继续读
- conflict: 冲突是否具体、是否在推进
- reward_density: 本章是否兑现了让读者“值了”的爽点
- character_consistency: 人物是否符合设定、无 OOC
- world_consistency: 是否违反给定世界规则
- emotion: 情绪调动是否到位，有无情绪断层
- commercial: 商业追读潜力（总览分，下面的商业分项是它的分解）
- originality_risk: 抄袭/套路化风险(0=极安全, 100=高风险)
## 商业生产维度 (v2)
- retention: 本章是否让读者愿意继续读下一章
- subscription: 本章是否累积“愿意付费/订阅”的动机
- payoff: 爽点兑现的质量(是否真的兑现了此前埋下的承诺)
- curiosity: 打开“下一章”的动机强度(开章率驱动)
- promise_delivery: 是否兑现了本章立下的商业承诺
- pacing: 节奏密度是否恰当
- character_growth: 本章人物是否有可追踪的成长/变化
- serial_sustainability: 这条主线/爽点引擎能否支撑长篇连载
- reader_drop_risk: 弃书风险(0=几乎不弃, 100=极可能弃书) —— 越低越好
- safety_risk: 内容擦边/敏感风险的主观程度(0=安全, 100=高风险) —— 越低越好；仅主观判断，硬性违禁词红线由确定性检查另行负责

# Constraints (硬约束)
- 禁止改写或续写正文。
- 每个低于 {threshold} 分的维度，必须在 revision_plan 里给出至少一条可执行修改单(reader_drop_risk / safety_risk / originality_risk 这三项越低越好，高于 {inv_threshold} 才需要修改单)。
- 每条判断必须引用正文中的具体句子作为 evidence。
- 不讨论个人文风偏好。
- predictions 仅用于版本间相对比较，不是绝对真值。

# Output
严格只输出一个 JSON 对象，不要输出任何解释文字、不要用 markdown 代码块。结构:
{{
  "scores": {{"hook":0-100,"conflict":0-100,"reward_density":0-100,"character_consistency":0-100,"world_consistency":0-100,"emotion":0-100,"commercial":0-100,"originality_risk":0-100,"retention":0-100,"subscription":0-100,"payoff":0-100,"curiosity":0-100,"promise_delivery":0-100,"pacing":0-100,"character_growth":0-100,"serial_sustainability":0-100,"reader_drop_risk":0-100,"safety_risk":0-100}},
  "dimensions": [{{"name":"hook","score":0-100,"evidence":"正文引用","comment":"简短说明"}}],
  "revision_plan": [{{"dimension":"hook","issue":"问题","action":"具体怎么改","evidence":"正文引用","priority":"high|medium|low"}}],
  "predictions": {{"subscription":0-100,"retention":0-100,"reader_satisfaction":0-100,"next_chapter_open_rate":0-100,"pay_conversion":0-100}}
}}

# Failure Policy
如果你无法评估，也必须输出上述结构且 scores 各项给 0，revision_plan 为空。绝不输出 JSON 以外的内容。
"""


def _grounding_block(grounding: Optional[dict]) -> str:
    """Render the Chapter IR's payoff_target into a judge-prompt block that GROUNDS
    the promise_delivery score (Phase 4.2). Before this, promise_delivery was a
    best-effort guess at 'the promise this chapter立下'; with the IR the promise is
    STATED, so the judge grades delivery against a concrete target. Empty when no
    payoff_target was supplied (the ungrounded fallback — a pure setup chapter)."""
    if not isinstance(grounding, dict):
        return ""
    promise = str(grounding.get("promise", "")).strip()
    if not promise:
        return ""
    kind = grounding.get("kind")
    kind_str = f"（承诺类型：{kind}）" if kind else ""
    return (f"\n- 本章的叙事 IR 已声明本章必须兑现的承诺(payoff_target){kind_str}:"
            f"\n  «{promise}»"
            f"\n  评审 promise_delivery 时，请以此声明的承诺为准绳判断正文是否真正兑现，"
            f"而不是自行猜测本章承诺；未兑现或偏离该承诺应显著扣分。")


def build_judge_prompt(artifact: dict, package: dict, *, threshold: int = REVISION_THRESHOLD,
                       role_focus: str = "", grounding: Optional[dict] = None) -> str:
    goal = package.get("task", {}).get("goal", "(未提供目标)")
    context_lines = []
    for records in package.get("context", {}).values():
        for rec in records:
            name = rec.get("name", rec.get("id", "?"))
            note = rec.get("statement") or rec.get("summary") or rec.get("notes") or ""
            context_lines.append(f"- {rec.get('id', '?')} {name}: {note}".rstrip())
    context = "\n".join(context_lines) or "(无绑定设定)"
    body = artifact.get("body", "")
    focus_block = f"\n# 你的评审侧重\n{role_focus}\n" if role_focus else ""
    return _JUDGE_TEMPLATE.format(
        role_focus=focus_block, goal=goal, context=context, body=body,
        grounding=_grounding_block(grounding),
        threshold=threshold, inv_threshold=100 - threshold)


# --------------------------------------------------------------------------- #
# Robust response parsing. An LLM judge's output is not trustworthy input: it  #
# may wrap JSON in prose or a code fence, omit fields, or return junk. We      #
# extract, coerce, and clamp — and on any failure fall back to a non-gating    #
# degraded report. The parser NEVER raises.                                    #
# --------------------------------------------------------------------------- #
_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_json(text: str) -> Optional[dict]:
    if not text or not text.strip():
        return None
    # 1) fenced ```json { ... } ```
    m = _FENCE_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 2) whole string is JSON
    try:
        obj = json.loads(text.strip())
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    # 3) first balanced {...} span
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


_SCORES_KEY_RE = re.compile(r'"scores"\s*:\s*\{')


def _balanced_span(text: str, start: int) -> Optional[str]:
    """The balanced {...} span beginning at text[start] == '{', or None.

    String-aware: braces inside JSON string literals do not affect depth, so a
    comment containing '{' cannot end the span early.
    """
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _salvage_scores(text: str) -> Optional[dict]:
    """Recover the top-level `scores` object from judge output whose OUTER JSON
    is malformed.

    Observed live (claude-opus-5 through a relay that silently DROPS the forced
    tool call, so the model hand-writes JSON): `scores` is emitted correctly and
    completely, then a broken entry appears deeper in the ADVISORY `dimensions`
    array — `{"name":"retention":81,"score":81,...}`, a stray `:81`. json.loads
    fails on the whole payload, _extract_json's balanced-span fallback returns
    the inner `scores` object (which has no "scores" key), and the guard in
    parse_judge_response degrades the report — discarding 18 real dimension
    scores because a prose comment was malformed.

    This recovers ONLY a complete, parseable object located at an explicit
    `"scores":` key. If the payload is genuinely truncated mid-scores the span
    never balances and this returns None, so the truncation guard still holds:
    a salvage can never forge scores the judge did not emit.
    """
    if not text:
        return None
    for match in _SCORES_KEY_RE.finditer(text):
        span = _balanced_span(text, match.end() - 1)
        if not span:
            continue
        try:
            obj = json.loads(span)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj:
            return obj
    return None


def _clamp_score(value) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, n))


def _coerce_scores(raw) -> dict:
    raw = raw if isinstance(raw, dict) else {}
    return {dim: _clamp_score(raw.get(dim, 0)) for dim in SCORE_DIMENSIONS}


def _coerce_predictions(raw) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    out = {"gating": False, "comparison_only": True}
    for key in ("subscription", "retention", "reader_satisfaction",
                "next_chapter_open_rate", "pay_conversion"):
        if key in raw:
            out[key] = _clamp_score(raw[key])
    return out


def parse_judge_response(text: str, *, reviewer: str, model_id: str = "") -> QualityReport:
    """Parse a judge's raw text into a validated QualityReport, degrading to a
    non-gating empty report on any problem. Never raises."""
    obj = _extract_json(text)
    if obj is None:
        return degraded_report(reviewer, "no JSON object found in judge output", model_id=model_id)

    # A TRUNCATED judge response has no closing brace for the outer object, so
    # _extract_json's balanced-span fallback returns the first COMPLETE inner
    # object it finds — typically the `scores` object itself, which has no
    # "scores" key. Coercing that to all-zero would forge a non-degraded all-zero
    # report (indistinguishable downstream from the legitimate "cannot evaluate"
    # sentinel, but silently wrong). A response with no "scores" key at all is a
    # parse failure, not a verdict — degrade it. (A real all-zero sentinel DOES
    # carry a "scores" key with zero values, so this preserves that path.)
    salvaged = False
    if "scores" not in obj:
        # Before degrading, try to recover a COMPLETE top-level `scores` object
        # from the raw text: a malformed entry in the advisory `dimensions`
        # array must not cost us 18 real scores. Truncated-mid-scores payloads
        # never balance, so they still fall through to the guard below.
        rescued = _salvage_scores(text)
        if rescued is None:
            return degraded_report(
                reviewer, "judge output had no 'scores' object (likely truncated)",
                model_id=model_id)
        obj = {"scores": rescued}
        salvaged = True

    scores = _coerce_scores(obj.get("scores"))

    dimensions = []
    for d in obj.get("dimensions", []) if isinstance(obj.get("dimensions"), list) else []:
        if not isinstance(d, dict) or "name" not in d:
            continue
        entry = {"name": str(d["name"]), "score": _clamp_score(d.get("score", 0))}
        if d.get("evidence"):
            entry["evidence"] = str(d["evidence"])
        if d.get("comment"):
            entry["comment"] = str(d["comment"])
        dimensions.append(entry)

    revision_plan = []
    for r in obj.get("revision_plan", []) if isinstance(obj.get("revision_plan"), list) else []:
        if not isinstance(r, dict):
            continue
        if not (r.get("dimension") and r.get("issue") and r.get("action")):
            continue
        entry = {
            "dimension": str(r["dimension"]),
            "issue": str(r["issue"]),
            "action": str(r["action"]),
        }
        if r.get("evidence"):
            entry["evidence"] = str(r["evidence"])
        if r.get("priority") in ("high", "medium", "low"):
            entry["priority"] = r["priority"]
        revision_plan.append(entry)

    predictions = _coerce_predictions(obj.get("predictions"))

    findings = [{
        "check": "quality-judge",
        "severity": "info",
        "message": "evaluative quality report produced (advisory, non-gating)",
    }]
    if salvaged:
        findings.append({
            "check": "quality-judge-salvaged",
            "severity": "warning",
            "message": "judge JSON was malformed; recovered the top-level scores "
                       "object only — dimensions/revision_plan/predictions were "
                       "dropped (advisory, non-gating)",
        })

    provenance = {"model_id": model_id, "parse_ok": True, "degraded": False}
    if salvaged:
        # NOT degraded: the scores are the judge's real numbers, so they must stay
        # in cross-chapter baselines. `salvaged` records that the prose detail was
        # lost, which is what an audit needs to distinguish it from a clean parse.
        provenance["salvaged"] = True

    return QualityReport(
        reviewer=reviewer,
        scores=scores,
        dimensions=dimensions,
        revision_plan=revision_plan,
        predictions=predictions,
        findings=findings,
        judge_provenance=provenance,
    )


# --------------------------------------------------------------------------- #
# The reviewer. Implements the DraftReviewer seam (execution.draft_review):    #
# `.reviewer_id` + `.review(artifact, package) -> report`. run.py calls it and #
# rides `report.to_dict()` on the envelope, exactly like the existing          #
# placeholder/unanchored reviewers.                                            #
# --------------------------------------------------------------------------- #
class LLMQualityJudge:
    """Novel Quality Center reviewer backed by any execution Model. Advisory
    only — its report can never gate (axis/gating are invariants)."""

    def __init__(self, model, *, reviewer_id: str = "llm-quality-judge-v1",
                 threshold: int = REVISION_THRESHOLD, role_focus: str = ""):
        self.model = model
        self.reviewer_id = reviewer_id
        self.threshold = threshold
        self.role_focus = role_focus

    def review(self, artifact: dict, package: dict,
               grounding: Optional[dict] = None) -> QualityReport:
        """`grounding` (Phase 4.2) optionally carries the Chapter IR's
        payoff_target so promise_delivery is scored against the chapter's STATED
        promise. Absent => the ungrounded judgment (byte-identical prompt to
        before 4.2, so existing v1/v2/v3 behavior is unchanged)."""
        model_id = getattr(self.model, "model_id", "")
        prompt = build_judge_prompt(artifact, package, threshold=self.threshold,
                                    role_focus=self.role_focus, grounding=grounding)
        try:
            if (getattr(self.model, "supports_structured_output", False)
                    and hasattr(self.model, "generate_structured")):
                output = self.model.generate_structured(
                    prompt, quality_judge_output_schema(),
                    tool_name="submit_quality_review")
            else:
                output = self.model.generate(prompt)
            text = getattr(output, "text", "")
            model_id = getattr(output, "model_id", model_id)
        except Exception as exc:  # a judge failure must never break the loop
            return degraded_report(self.reviewer_id, f"model error: {exc}", model_id=model_id)
        report = parse_judge_response(
            text, reviewer=self.reviewer_id, model_id=model_id)
        response = getattr(self.model, "last_response", None)
        request = getattr(self.model, "last_request", None)
        if response is None:
            return report
        provenance = {
            **(report.judge_provenance or {}),
            "provider": getattr(response, "provider", None),
            "request_id": getattr(response, "request_id", None),
            "request_hash": (
                getattr(getattr(request, "prompt_provenance", None), "prompt_hash", None)),
            "response_hash": getattr(response, "response_hash", None),
            "finish_reason": getattr(response, "finish_reason", None),
            "token_usage": (
                response.token_usage.to_dict()
                if hasattr(response.token_usage, "to_dict")
                else {
                    "input_tokens": response.token_usage.input_tokens,
                    "output_tokens": response.token_usage.output_tokens,
                    "total_tokens": response.token_usage.total_tokens,
                }),
            "cost_status": "priced" if response.cost is not None else "unpriced",
            "structured_output": bool(
                getattr(self.model, "supports_structured_output", False)),
        }
        return replace(report, judge_provenance=provenance)


def llm_quality_judge(model, **kwargs) -> LLMQualityJudge:
    return LLMQualityJudge(model, **kwargs)
