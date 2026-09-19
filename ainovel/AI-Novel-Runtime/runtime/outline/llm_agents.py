"""llm_agents.py — real-LLM outline agents (ANES v2, Minimal Genesis / M2).

agents.py declares the multi-agent ROLES and ships a deterministic "template
engine" fallback (propose_candidates / review_candidate / _build_*). This module
is the LLM implementation of those roles behind the SAME return shapes, so the
outline workflow is unchanged: with a model it produces real, original설정; without
one (or on any failure) it degrades to the deterministic mock.

DISCIPLINE — same seam as scene/llm_planner.py & quality_center.LLMQualityJudge:
  - Depends only on the execution Model protocol (model.generate(prompt) -> obj
    with .text), so a fake model proves the parse/validate logic in CI without a
    network; a real provider drops in unchanged.
  - DEGRADE, never crash: a failed call, empty text, or unparseable/invalid JSON
    falls back to the deterministic producer. Genesis never breaks on the model
    (ADR-003 spirit extended to book creation).
  - Writes NOTHING to facts. It only produces outline-shaped dicts; characters and
    events reach the registry only later via candidates→mint (ADR-006/009).
"""
from __future__ import annotations

from typing import List, Optional

from ..execution.quality_center import _extract_json
from .agents import propose_candidates, review_candidate

_PROPOSE_TEMPLATE = """# 角色
你是 WorldBuilder + CharacterDesigner 双重身份的资深网文主编，为一本新书设计
原创方向。你必须产出**全新原创设定**，不得复刻任何参考作品的专有名词与设定。

# 参考分析（题材信号 / 读者爽点 / 结构信号 / 原创护栏）
{analysis}

# 题材约束
{genre_constraint}

# 任务
提出 {n} 个彼此不同的开书方向。每个方向必须是可长线连载的商业网文骨架，包含：
  - direction：一句话方向定位（如 商业强钩子升级线 / 群像博弈线）
  - title：原创书名
  - genre：题材数组
  - logline：一句话故事内核（含身份落差 + 金手指 + 即时冲突）
  - protagonist_engine：{{desire 深层渴望, flaw 缺陷, golden_finger 金手指, cost 使用代价}}
  - power_system：{{tiers 力量层级数组(5级), breakthrough_condition 突破条件, hard_limits 硬限制数组}}；对于都市/现实题材，力量层级指财富/权力/影响力等级，不是超自然能力
  - design_focus：设计侧重数组（如 fast-opening-hook / progression）
  - characters：3-4 个原创角色数组，每个 {{role 定位(protagonist/rival/mentor/ally 之一), name 原创人名, arc 成长弧, motivation 动机}}；至少一个 role 为 protagonist
  - world：{{summary 一句话原创世界观, rules 3 条可检验的世界硬规则数组}}；对于都市题材，世界观指现实社会规则（商业/职场/校园等）

原创人名与世界专名必须全新，不得复用参考作品或任何知名作品的专有名词。

# 输出
严格只输出一个 JSON 对象，不要解释、不要 markdown 代码块：
{{
  "candidates": [
    {{"id": "CANDIDATE-A", "direction": "...", "title": "...", "genre": ["..."],
      "logline": "...", "design_focus": ["..."],
      "protagonist_engine": {{"desire": "...", "flaw": "...", "golden_finger": "...", "cost": "..."}},
      "power_system": {{"tiers": ["..."], "breakthrough_condition": "...", "hard_limits": ["..."]}},
      "characters": [{{"role": "protagonist", "name": "...", "arc": "...", "motivation": "..."}}],
      "world": {{"summary": "...", "rules": ["...", "...", "..."]}}}}
  ]
}}

# 失败兜底
无法处理时输出 {{"candidates": []}}，系统会回退到确定性模板。"""


def _analysis_brief(merged_analysis: dict) -> str:
    """Compact the merged reference analysis into the prompt's analysis slot.
    Deterministic + bounded."""
    def _join(key, cap=8):
        vals = merged_analysis.get(key) or []
        return "、".join(str(v) for v in vals[:cap]) or "（无）"
    return (
        f"题材信号：{_join('genre_signals')}\n"
        f"读者爽点：{_join('reader_rewards')}\n"
        f"结构信号：{_join('structure_signals')}\n"
        f"原创护栏：{_join('originality_guardrails')}"
    )


_REQUIRED_CANDIDATE_KEYS = ("id", "direction", "title", "genre", "logline",
                            "protagonist_engine", "power_system")


def _valid_candidate(c: dict) -> bool:
    if not isinstance(c, dict) or not all(k in c for k in _REQUIRED_CANDIDATE_KEYS):
        return False
    eng = c.get("protagonist_engine")
    pw = c.get("power_system")
    if not isinstance(eng, dict) or not eng.get("golden_finger"):
        return False
    if not isinstance(pw, dict) or not isinstance(pw.get("tiers"), list) or not pw["tiers"]:
        return False
    return True


class LLMCandidateProposer:
    """WorldBuilder + CharacterDesigner as a real-LLM agent. Produces original
    story directions in the SAME shape as agents.propose_candidates; degrades to
    that deterministic producer on any failure (empty/unparseable/invalid)."""

    def __init__(self, model, *, n: int = 3, agent_id: str = "llm-candidate-proposer-v1"):
        self.model = model
        self.n = n
        self.agent_id = agent_id

    def propose(self, merged_analysis: dict) -> List[dict]:
        fallback = propose_candidates(merged_analysis)
        try:
            # Build genre constraint based on primary genre signal
            genre_signals = merged_analysis.get("genre_signals", [])
            primary_genre = genre_signals[0] if genre_signals else "待判定"

            # 选择题材专用模板
            if primary_genre == "都市" or primary_genre == "都市重生" or "重生" in str(genre_signals):
                from .prompts.urban import URBAN_PROPOSE_TEMPLATE
                template = URBAN_PROPOSE_TEMPLATE
                prompt = template.format(
                    analysis=_analysis_brief(merged_analysis),
                    n=self.n)
            else:
                # 使用默认通用模板，传入 genre_constraint
                genre_constraint_map = {
                    "都市": """**强制要求：纯都市现实题材**
- 主角必须生活在现代真实城市（如北京/上海/深圳等）
- 场景必须是现实的：公司办公室、学校教室、商场、咖啡厅、住宅小区等
- 冲突必须是现实的：商业竞争、职场斗争、校园社交、感情纠葛、家庭矛盾等
- 可以有重生/系统/预知未来等金手指，但金手指只提供信息/机会，不能违反物理规律
- **严格禁止**：魔法、修仙、异能、超自然力量、灾变、废土、预言、旧神、继承者等奇幻/玄幻元素
- logline 必须包含现实城市场景关键词（如"公司"、"校园"、"创业"、"职场"等）""",
                    "玄幻": "必须是玄幻题材。可以有修炼/灵气/宗门/境界等设定。",
                    "仙侠": "必须是仙侠题材。可以有飞剑/渡劫/元婴等设定。",
                    "科幻": "必须是科幻题材。可以有星际/AI/未来科技等设定。",
                    "奇幻": "必须是奇幻题材。可以有魔法/骑士/龙等设定。",
                }
                genre_constraint = genre_constraint_map.get(primary_genre, f"题材为：{primary_genre}")
                template = _PROPOSE_TEMPLATE
                prompt = template.format(
                    analysis=_analysis_brief(merged_analysis),
                    n=self.n,
                    genre_constraint=genre_constraint)

            text = getattr(self.model.generate(prompt), "text", "") or ""
        except Exception:
            return fallback
        obj = _extract_json(text)
        if not obj:
            return fallback
        cands = obj.get("candidates")
        if not isinstance(cands, list):
            return fallback
        valid = [c for c in cands if _valid_candidate(c)]
        # A partial degrade would leave the reviewer/synthesizer with a thin set;
        # require at least one usable candidate, else fall back wholesale so the
        # deterministic skeleton stays complete (scene/llm_planner discipline).
        return valid if valid else fallback


_REVIEW_TEMPLATE = """# 角色
你是 Critic + OriginalityGuard 双重身份的网文审稿人。评审一个开书方向的商业潜力
与原创性风险。

# 待评方向
标题：{title}
方向：{direction}
内核：{logline}
金手指：{golden_finger}（代价：{cost}）

# 原创护栏（必须规避的复刻风险）
{guardrails}

# 任务
给出评审。score 为 1-10 的商业+原创综合分；risk_level 为 low/medium/high 的原创
风险（越像参考作品越高）。

# 输出
严格只输出一个 JSON 对象，不要解释、不要 markdown：
{{"score": 1-10, "risk_level": "low|medium|high",
  "strengths": ["..."], "concerns": ["..."]}}

# 失败兜底
无法处理时输出 {{"score": 0}}，系统会回退到确定性评审。"""


class LLMCandidateReviewer:
    """Critic + OriginalityGuard as a real-LLM agent. Scores a candidate's
    commercial + originality risk in the SAME shape as agents.review_candidate;
    degrades to that deterministic reviewer on any failure."""

    def __init__(self, model, *, agent_id: str = "llm-candidate-reviewer-v1"):
        self.model = model
        self.agent_id = agent_id

    def review(self, candidate: dict, merged_analysis: dict) -> dict:
        fallback = review_candidate(candidate, merged_analysis)
        try:
            eng = candidate.get("protagonist_engine", {}) or {}
            prompt = _REVIEW_TEMPLATE.format(
                title=candidate.get("title", ""),
                direction=candidate.get("direction", ""),
                logline=candidate.get("logline", ""),
                golden_finger=eng.get("golden_finger", ""),
                cost=eng.get("cost", ""),
                guardrails="、".join(str(g) for g in (
                    merged_analysis.get("originality_guardrails") or [])) or "（无）")
            text = getattr(self.model.generate(prompt), "text", "") or ""
        except Exception:
            return fallback
        obj = _extract_json(text)
        if not obj:
            return fallback
        score = obj.get("score")
        risk = obj.get("risk_level")
        if not isinstance(score, (int, float)) or score < 1 or risk not in ("low", "medium", "high"):
            return fallback
        # Keep the deterministic reviewer's structural keys; overlay the LLM's
        # judgment so downstream synthesize_final_outline reads the same shape.
        return {
            **fallback,
            "score": int(score),
            "risk_level": risk,
            "strengths": obj.get("strengths") or fallback["strengths"],
            "concerns": obj.get("concerns") or fallback["concerns"],
            "reviewed_by": self.agent_id,
        }

