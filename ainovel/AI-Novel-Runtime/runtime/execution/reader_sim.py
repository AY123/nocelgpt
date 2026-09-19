"""reader_sim.py — Reader Simulator (ANES v2, roadmap P11, the LAST piece).

Several reader PERSONAS each simulate reading a chapter and report how satisfied
they are, whether they would keep reading, and where they would drop. This is
DELIBERATELY the last stage of the pipeline: reader reaction is unfalsifiable
prediction, so it is strictly ADVISORY and COMPARISON-ONLY.

Discipline (enforced here AND by reader-simulation.schema.json):
  - axis = evaluative, gating = false  -> can NEVER block a build (ADR-003).
  - comparison_only = true             -> the numbers are meaningful only as a
    RELATIVE comparison between two revisions (compare_simulations), never as an
    absolute "this chapter scores 73" truth (the North Star discipline).

It reuses the DraftReviewer seam (like LLMQualityJudge / ReviewPanel), so it can
ride execute/refine/revise unchanged — but because it is comparison-only, the
intended use is compare_simulations(before, after), not gating on one number.
The simulator depends only on the execution Model protocol; a fake model proves
the parsing/aggregation logic in CI without network.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .quality_center import _extract_json, _clamp_score

# Preset personas. Each reads with a different appetite; a chapter that thrills
# 爽文党 may bore 剧情党 — surfacing that split is the point.
PERSONAS: dict[str, str] = {
    "老白": "资深老读者，看过海量套路，容易审美疲劳。你最在意新意、逻辑硬伤和套路化。",
    "小白": "入门新读者，容易被强爽点和强钩子打动，不在意套路，讨厌节奏慢和信息量大。",
    "男频党": "偏好升级、战斗、逆袭、爽感与金手指兑现；对感情戏和细腻情绪耐心低。",
    "女频党": "偏好情绪张力、人物关系、细腻内心与人设魅力；对纯打斗流水账耐心低。",
    "爽文党": "只为爽感追读：打脸、翻身、装逼、即时回报。节奏一慢或憋屈就想弃书。",
    "剧情党": "为剧情与伏笔追读：在意悬念、结构、动机可信度；讨厌无意义爽点与降智。",
}

DEFAULT_PERSONAS = ("老白", "小白", "男频党", "女频党", "爽文党", "剧情党")

# v2 (roadmap 4.4) — a second FIXED panel of six COMMERCIAL personas. Where the
# v1 set reads by APPETITE (what they enjoy), this set reads by PAY BEHAVIOR
# (what makes them订阅/打赏/投月票 vs 白嫖/养肥/弃书). They carry the same soft
# discipline: their pay_probability is a comparison-only signal, never absolute
# truth and never a gate. Surfacing WHERE money leaks (who stops paying, why) is
# the point — the same way the v1 panel surfaces where readers drop.
COMMERCIAL_PERSONAS: dict[str, str] = {
    "首订党": "会不会为这一章掏首订，取决于开篇钩子与付费点前的爽感兑现。信息价值不足就只看免费章。",
    "追订党": "已入坑、按章追订的核心付费读者。最怕断更感、注水和爽点稀释；一旦'不值这几分钱'就转养肥。",
    "白嫖党": "默认不付费，只有被强钩子/强情绪逼到'等不及'才可能破例订阅。是付费转化的临界样本。",
    "打赏党": "情绪上头才打赏：高光名场面、人设魅力爆发、燃/虐/爽的峰值。平淡章节零打赏。",
    "月票党": "月底为'投给谁'比较各书。在意长期追读价值、稳定输出与作者存在感；单章崩坏会改投他书。",
    "养肥党": "宁可攒够几十章一次性看。要把他拉回即时追订，必须制造强断章悬念与'现在不看会亏'的紧迫感。",
}

DEFAULT_COMMERCIAL_PERSONAS = ("首订党", "追订党", "白嫖党", "打赏党", "月票党", "养肥党")

# Combined description lookup — build_persona_prompt resolves either panel.
_PERSONA_DESC: dict[str, str] = {**PERSONAS, **COMMERCIAL_PERSONAS}

# A persona is treated as "likely to pay" above this soft bar. Used only to
# derive comparison-only aggregates (pay_personas / newly_pay_lost); it is NOT a
# threshold that gates anything.
PAY_INTEREST_BAR = 50


@dataclass(frozen=True)
class ReaderSimulation:
    reviewer: str
    personas: List[dict]
    aggregate: dict
    findings: List[dict] = field(default_factory=list)
    judge_provenance: Optional[dict] = None
    axis: str = "evaluative"       # structural invariant
    gating: bool = False           # structural invariant — never blocks
    comparison_only: bool = True   # structural invariant — relative use only

    def to_dict(self) -> dict:
        out = {
            "reviewer": self.reviewer,
            "axis": self.axis,
            "gating": self.gating,
            "comparison_only": self.comparison_only,
            "personas": self.personas,
            "aggregate": self.aggregate,
            "findings": self.findings,
        }
        if self.judge_provenance is not None:
            out["judge_provenance"] = self.judge_provenance
        return out


# --------------------------------------------------------------------------- #
# Persona prompt (contracted). Asks the model to ROLE-PLAY one reader and report #
# a structured verdict — not to critique like an editor.                        #
# --------------------------------------------------------------------------- #
_SIM_TEMPLATE = """# Role
你现在是一名网文读者，人设：{persona_name} —— {persona_desc}

# 任务
以这名读者的口味，真实地"读"下面这一章，然后给出你的反应。你不是编辑，不做写作建议，
只表达作为这类读者的真实感受。

# 章节正文
<<<CHAPTER>>>
{body}
<<<END>>>

# 输出
严格只输出一个 JSON 对象，不要解释、不要 markdown 代码块：
{{
  "satisfaction": 0-100,             // 作为这类读者，这一章让你多满意
  "would_continue": true/false,      // 你会不会继续追下一章
  "continue_probability": 0-100,     // 你继续追下一章的概率（比 would_continue 更细）
  "pay_probability": 0-100,          // 作为这类读者，此刻你为追读付费（订阅/打赏/月票）的概率
  "drop_point": "若会弃书，指出正文中让你想弃的位置/句子；不弃留空",
  "drop_reason": "弃书、不满、或不愿付费的具体原因；没有留空",
  "expectations": ["你希望下一章出现什么，1-3条"]
}}

# 失败兜底
无法评估时也必须输出上述结构：satisfaction=0, would_continue=false,
continue_probability=0, pay_probability=0, 其余留空/空数组。"""


def build_persona_prompt(persona_name: str, artifact: dict) -> str:
    return _SIM_TEMPLATE.format(
        persona_name=persona_name,
        persona_desc=_PERSONA_DESC.get(persona_name, "普通网文读者"),
        body=artifact.get("body", ""),
    )


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _parse_persona(text: str, persona_name: str) -> dict:
    """Parse one persona's raw output into a validated verdict; degrade to a
    non-blocking neutral verdict on any problem. Never raises."""
    obj = _extract_json(text)
    if obj is None:
        return {"name": persona_name, "satisfaction": 0, "would_continue": False,
                "degraded": True}
    would_continue = bool(obj.get("would_continue", False))
    verdict = {
        "name": persona_name,
        "satisfaction": _clamp_score(obj.get("satisfaction", 0)),
        "would_continue": would_continue,
        "degraded": False,
    }
    # v2: probabilities are the finer, comparison-only signals. If the model
    # omits them (v1-style output), backfill from the coarse signals so a mixed
    # panel still aggregates — a continuing reader defaults to a high追读概率,
    # and付费概率 tracks satisfaction. Explicit model values always win.
    cont_p = obj.get("continue_probability")
    verdict["continue_probability"] = (
        _clamp_score(cont_p) if _is_number(cont_p)
        else (80 if would_continue else 20))
    pay_p = obj.get("pay_probability")
    if _is_number(pay_p):
        verdict["pay_probability"] = _clamp_score(pay_p)
    elif "pay_probability" in obj:
        verdict["pay_probability"] = 0
    # else: leave pay_probability ABSENT — an appetite persona that never
    # reports it should not be counted as a 0-pay reader in the aggregate.
    if obj.get("drop_point"):
        verdict["drop_point"] = str(obj["drop_point"])
    if obj.get("drop_reason"):
        verdict["drop_reason"] = str(obj["drop_reason"])
    exp = obj.get("expectations")
    if isinstance(exp, list):
        verdict["expectations"] = [str(e) for e in exp][:3]
    return verdict


def _aggregate(personas: List[dict], *, pay_bar: int = PAY_INTEREST_BAR) -> dict:
    live = [p for p in personas if not p.get("degraded")]
    if not live:
        return {"mean_satisfaction": 0, "continue_rate": 0,
                "drop_personas": [], "common_expectations": []}
    mean = int(round(sum(p["satisfaction"] for p in live) / len(live)))
    cont = int(round(100 * sum(1 for p in live if p["would_continue"]) / len(live)))
    drop = [p["name"] for p in live if not p["would_continue"]]
    seen: list[str] = []
    for p in live:
        for e in p.get("expectations", []):
            if e not in seen:
                seen.append(e)
    agg = {"mean_satisfaction": mean, "continue_rate": cont,
           "drop_personas": drop, "common_expectations": seen[:6]}

    # v2: comparison-only continue/pay aggregates. Each is averaged ONLY over the
    # personas that reported it, so an appetite-only panel (no pay_probability)
    # simply omits the pay aggregate rather than reporting a misleading 0.
    cont_ps = [p["continue_probability"] for p in live if "continue_probability" in p]
    if cont_ps:
        agg["mean_continue_probability"] = int(round(sum(cont_ps) / len(cont_ps)))
    pay_reporters = [p for p in live if "pay_probability" in p]
    if pay_reporters:
        agg["mean_pay_probability"] = int(round(
            sum(p["pay_probability"] for p in pay_reporters) / len(pay_reporters)))
        agg["pay_personas"] = [p["name"] for p in pay_reporters
                               if p["pay_probability"] >= pay_bar]
    return agg


# --------------------------------------------------------------------------- #
# The simulator. Implements the DraftReviewer seam (.reviewer_id + .review),    #
# so it can ride execute/refine — but its report is comparison-only, so the     #
# intended use is compare_simulations(before, after).                           #
# --------------------------------------------------------------------------- #
class LLMReaderSimulator:
    def __init__(self, model, *, personas=DEFAULT_PERSONAS,
                 reviewer_id: str = "reader-simulator-v1",
                 pay_bar: int = PAY_INTEREST_BAR):
        self.model = model
        self.personas = tuple(personas)
        self.reviewer_id = reviewer_id
        self.pay_bar = pay_bar

    def review(self, artifact: dict, package: dict | None = None) -> ReaderSimulation:
        model_id = getattr(self.model, "model_id", "")
        verdicts: List[dict] = []
        for name in self.personas:
            prompt = build_persona_prompt(name, artifact)
            try:
                output = self.model.generate(prompt)
                text = getattr(output, "text", "")
                model_id = getattr(output, "model_id", model_id)
                verdicts.append(_parse_persona(text, name))
            except Exception:
                verdicts.append({"name": name, "satisfaction": 0,
                                 "would_continue": False, "degraded": True})

        # aggregate + findings
        aggregate = _aggregate(verdicts, pay_bar=self.pay_bar)
        all_degraded = all(v.get("degraded") for v in verdicts)
        findings = []
        if all_degraded:
            findings.append({"check": "reader-sim-degraded", "severity": "warning",
                             "message": "all personas degraded; non-gating empty simulation"})
        else:
            findings.append({"check": "reader-sim", "severity": "info",
                             "message": f"{len(verdicts)} personas simulated (advisory, comparison-only)"})
            if aggregate["drop_personas"]:
                findings.append({"check": "reader-drop", "severity": "warning",
                                 "message": f"personas that would drop: {', '.join(aggregate['drop_personas'])}"})
        return ReaderSimulation(
            reviewer=self.reviewer_id,
            personas=verdicts,
            aggregate=aggregate,
            findings=findings,
            judge_provenance={"model_id": model_id, "degraded": all_degraded},
        )


def llm_reader_simulator(model, **kwargs) -> LLMReaderSimulator:
    return LLMReaderSimulator(model, **kwargs)


def commercial_reader_simulator(model, **kwargs) -> LLMReaderSimulator:
    """v2 (roadmap 4.4): a simulator over the six COMMERCIAL personas
    (首订党/追订党/白嫖党/打赏党/月票党/养肥党). Identical machinery to the
    appetite simulator — same seam, same comparison-only discipline — but its
    panel reads by pay behavior, so its pay_probability aggregate is the one the
    Commercial Loop compares. Pass personas=... to blend both panels."""
    kwargs.setdefault("personas", DEFAULT_COMMERCIAL_PERSONAS)
    kwargs.setdefault("reviewer_id", "commercial-reader-simulator-v2")
    return LLMReaderSimulator(model, **kwargs)


def compare_simulations(before: dict, after: dict, *,
                        pay_bar: int = PAY_INTEREST_BAR) -> dict:
    """RELATIVE comparison of two reader simulations (the intended use — reader
    signals are comparison-only, never absolute). Returns per-persona satisfaction
    deltas + who newly drops/recovers + an overall verdict. Never gates.

    `pay_bar` is the soft付费意愿 threshold used to detect a persona crossing from
    likely-to-pay to unlikely-to-pay (newly_pay_lost); it must match the bar the
    simulations were aggregated with, or the crossing detection disagrees with the
    pay_personas list. Defaults to PAY_INTEREST_BAR (the simulator default)."""
    b_personas = {p["name"]: p for p in before.get("personas", [])}
    a_personas = {p["name"]: p for p in after.get("personas", [])}
    names = [n for n in a_personas if n in b_personas]

    deltas = {}
    newly_dropped, newly_retained, newly_pay_lost = [], [], []
    for n in names:
        bp, ap = b_personas[n], a_personas[n]
        if bp.get("degraded") or ap.get("degraded"):
            continue
        deltas[n] = ap["satisfaction"] - bp["satisfaction"]
        if bp["would_continue"] and not ap["would_continue"]:
            newly_dropped.append(n)
        elif not bp["would_continue"] and ap["would_continue"]:
            newly_retained.append(n)
        # v2: a persona crossing from likely-to-pay to unlikely-to-pay is a
        # commercial regression even if they'd still keep reading for free.
        bpay, apay = bp.get("pay_probability"), ap.get("pay_probability")
        if _is_number(bpay) and _is_number(apay) \
                and bpay >= pay_bar and apay < pay_bar:
            newly_pay_lost.append(n)

    b_agg = before.get("aggregate", {})
    a_agg = after.get("aggregate", {})
    b_mean = b_agg.get("mean_satisfaction", 0)
    a_mean = a_agg.get("mean_satisfaction", 0)
    b_cont = b_agg.get("continue_rate", 0)
    a_cont = a_agg.get("continue_rate", 0)

    if newly_dropped and not newly_retained:
        verdict = "regressed"
    elif a_mean > b_mean and not newly_dropped:
        verdict = "improved"
    elif a_mean < b_mean or newly_dropped:
        verdict = "mixed"
    else:
        verdict = "unchanged"

    out = {
        "comparison_only": True,
        "gating": False,
        "verdict": verdict,
        "mean_satisfaction_delta": a_mean - b_mean,
        "continue_rate_delta": a_cont - b_cont,
        "per_persona_delta": deltas,
        "newly_dropped": newly_dropped,
        "newly_retained": newly_retained,
        "newly_pay_lost": newly_pay_lost,
    }
    # v2 pay/continue-probability deltas — only when BOTH sides reported them,
    # so an appetite-only comparison stays byte-identical to v1 (minus the
    # always-empty newly_pay_lost list).
    if "mean_continue_probability" in b_agg and "mean_continue_probability" in a_agg:
        out["mean_continue_probability_delta"] = (
            a_agg["mean_continue_probability"] - b_agg["mean_continue_probability"])
    if "mean_pay_probability" in b_agg and "mean_pay_probability" in a_agg:
        out["mean_pay_probability_delta"] = (
            a_agg["mean_pay_probability"] - b_agg["mean_pay_probability"])
    return out
