"""mandate.py — Narrative Mandate projection (Phase 9, Narrative Intelligence).

The anti-流水账 layer. It sits ABOVE the chapter objective and answers the four
questions the original diagnosis named — why THIS chapter must happen NOW, how
far the conflict escalates vs the previous chapter, how the protagonist's inner
arc moves, and what irreversible main-line advance it commits (ROADMAP §13.2/§13.5).

It is a CROSS-CHAPTER FOLD, not a mutable state (ADR-008), the same discipline as
character_runtime / StoryState: mandate(N) folds from the outline's per-chapter
beat + mandate(N-1) + StoryState. `escalation.from_level` = the previous mandate's
`to_level`; `inner_shift.from` = the previous mandate's `to`. Same beat + same
prior mandate => same content_hash. The opening chapter degrades cleanly (no prior
mandate => base levels, from = an opening-situation seed).

It is ADVISORY and NEVER gates (ADR-003): the three staleness detectors (9.3) key
its fields to warn on 温水章 / 张力停滞 / 原地打转, but an unmet mandate never fails a
chapter. Authority is human (ADR-009): it stages a tension-arc recommendation, it
does not commit a book's direction.

A long-arc-plan (P10) does not exist yet; when it does it becomes an additional
fold input. Until then the fold is (beat, prev_mandate, StoryState, outline).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, List, Optional

from jsonschema import Draft202012Validator

_SCHEMA_PATH = (Path(__file__).resolve().parents[3] / "AI-Novel-Standard"
                / "contracts" / "narrative-mandate.schema.json")


def _hash(obj) -> str:
    """Pure content hash over a canonical JSON encoding. Inlined here (rather than
    reused from the execution/agent helper) so director/ never touches the model
    seam — guard #21 forbids director/ importing the agent/model/llm modules, and a
    mandate is a read-side projection, not a generated artifact."""
    canonical = json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

# The opening chapter's tension seed — no prior mandate to fold from.
_BASE_FROM_LEVEL = 2
_BASE_TO_LEVEL = 3
_MAX_LEVEL = 10


def _load_schema() -> dict:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _text(beat: dict) -> str:
    """All the beat's authored prose, joined, for keyword classification."""
    return " ".join(str(beat.get(k, "")) for k in
                    ("goal", "conflict", "escalation", "reward_if_any", "end_hook"))


# --- classification: deterministic keyword folds from the authored beat --------
# Each fold reads the beat's own words. Coarse and advisory (ADR-003); the point
# is to turn "did the conflict escalate / is there time pressure / did the hero
# change" into a computable field, not to be a semantic model.

# escalation.kind — the SHAPE of the escalation, keyed off the beat's conflict/
# escalation/hook prose. Order matters: the most specific wins.
_ESCALATION_KINDS = (
    ("betrayal",      ("背叛", "出卖", "叛", "betray")),
    ("new_antagonist",("新敌", "新的敌人", "新对手", "登场", "出现.*敌", "更强的")),
    ("reversal",      ("反转", "翻身", "打脸", "逆转", "反杀", "reversal")),
    ("power_reveal",  ("金手指", "觉醒", "突破", "异能", "力量", "梦蚀", "显性")),
    ("time_pressure", ("限时", "倒计时", "来不及", "期限", "今夜", "之前", "deadline")),
    ("stakes_raise",  ("升级", "更大", "更强", "危机", "威胁", "生死", "代价")),
)


def _escalation_kind(beat: dict) -> str:
    """Classify the escalation shape from the beat prose. Falls back to
    'stakes_raise' when escalation is authored but unshaped, and 'flat' only when
    the beat itself signals no escalation."""
    import re
    text = _text(beat)
    esc = str(beat.get("escalation", "")).strip()
    # A beat that explicitly says the conflict does NOT rise is flat.
    if esc and any(k in esc for k in ("未升级", "无升级", "持平", "平稳", "no escalation")):
        return "flat"
    for kind, pats in _ESCALATION_KINDS:
        if any(re.search(p, text) for p in pats):
            return kind
    # An escalation line is present (the scaffolder always writes "冲突较上一章升级")
    # => treat as a generic stakes raise; a truly empty beat is flat.
    return "stakes_raise" if esc else "flat"


# cost_of_delay — the anti-温水章 signal. High when the beat carries an explicit
# clock / threat; none when the beat is a quiet transition with no pressure word.
_HIGH_DELAY = ("今夜", "立刻", "马上", "来不及", "绝境", "生死", "威胁", "危机",
               "倒计时", "限时", "之前", "否则", "追兵", "逼")
_MED_DELAY = ("尽快", "很快", "逼近", "追", "压力", "紧迫", "不能等")


def _cost_of_delay(beat: dict) -> str:
    text = _text(beat)
    if any(k in text for k in _HIGH_DELAY):
        return "high"
    if any(k in text for k in _MED_DELAY):
        return "medium"
    # A beat with a concrete conflict still implies some cost; a pure transition
    # ("推进当前阶段目标") with no conflict specifics reads as none => 温水章 signal.
    conflict = str(beat.get("conflict", ""))
    if conflict and "具体冲突" not in conflict:
        return "low"
    return "none"


# inner_shift.dimension — which axis of the protagonist moves this chapter, keyed
# off the beat + the protagonist engine (desire/flaw/cost).
def _inner_dimension(beat: dict) -> str:
    text = _text(beat)
    if any(k in text for k in ("信念", "觉悟", "醒悟", "决心", "belief")):
        return "belief"
    if any(k in text for k in ("恐惧", "害怕", "惧", "fear")):
        return "fear"
    if any(k in text for k in ("关系", "背叛", "信任", "羁绊", "同伴")):
        return "relationship"
    if any(k in text for k in ("价值", "原则", "底线", "value")):
        return "value"
    if any(k in text for k in ("目标", "野心", "goal")):
        return "goal"
    return "resolve"


def _beat_for(outline: Optional[dict], chapter_no: int) -> dict:
    """The authored per-chapter beat for this chapter, or an empty beat when the
    outline doesn't reach this far (the fold then degrades to base levels)."""
    beats = (outline or {}).get("first_30_chapters") or []
    for b in beats:
        if isinstance(b, dict) and b.get("chapter_no") == chapter_no:
            return b
    # positional fallback (1-indexed) if chapter_no isn't stamped
    if 1 <= chapter_no <= len(beats) and isinstance(beats[chapter_no - 1], dict):
        return beats[chapter_no - 1]
    return {}


def _inner_from_seed(outline: Optional[dict]) -> str:
    """The opening chapter's inner starting point — the protagonist's authored
    flaw/desire, so inner_shift.from isn't invented from nothing."""
    pe = (outline or {}).get("protagonist_engine") or {}
    return (pe.get("flaw") or pe.get("desire") or "初始心境").strip() or "初始心境"


def project_narrative_mandate(*, chapter_no: int, task_id: str,
                              outline: Optional[dict] = None,
                              long_arc_plan: Optional[dict] = None,
                              prev_mandate: Optional[dict] = None,
                              state: Optional[Any] = None,
                              derived_from: Optional[List[str]] = None,
                              source_version: Optional[int] = None) -> dict:
    """Fold the authored per-chapter beat + the previous mandate + StoryState into
    a NarrativeMandate (conforms to narrative-mandate.schema.json). Pure and
    deterministic (ADR-008): same beat + same prev_mandate => same content_hash.

    Cross-chapter fold discipline (mirrors character_runtime):
      - escalation.from_level = prev_mandate.escalation.to_level (base on ch1)
      - inner_shift.from       = prev_mandate.inner_shift.to     (seed on ch1)
    `state` is an optional StoryState (or dict) whose open_setups/events_so_far
    could shape net_advance; it is read defensively so a None state degrades
    cleanly. `long_arc_plan` is an optional higher-order band plan whose chapter
    band goals can tighten why_now / net_advance, but the fold still works
    without it so existing runs stay byte-identical.
    """
    beat = _beat_for(outline, chapter_no)
    prev_esc = ((prev_mandate or {}).get("escalation") or {})
    prev_inner = ((prev_mandate or {}).get("inner_shift") or {})
    arc_band = None
    if isinstance(long_arc_plan, dict):
        bands = long_arc_plan.get("bands") or long_arc_plan.get("chapter_bands") or []
        for b in bands:
            if isinstance(b, dict) and chapter_no >= int(b.get("start", chapter_no)) and chapter_no <= int(b.get("end", chapter_no)):
                arc_band = b
                break

    # ① why_now
    cost = _cost_of_delay(beat)
    trigger = (str(beat.get("conflict", "")).strip()
               or str(beat.get("goal", "")).strip()
               or "本章冲突推进")
    why_now: dict[str, Any] = {"trigger": trigger, "cost_of_delay": cost}
    if arc_band:
        why_now["arc_band"] = {
            "id": arc_band.get("id"),
            "goal": arc_band.get("goal") or arc_band.get("stage_goal") or arc_band.get("purpose"),
        }
    hook = str(beat.get("end_hook", "")).strip()
    if hook:
        why_now["clock"] = hook

    # ② escalation — from_level folds from the prior mandate's to_level
    from_level = prev_esc.get("to_level")
    if not isinstance(from_level, int):
        from_level = _BASE_FROM_LEVEL
    kind = _escalation_kind(beat)
    # flat => no rise; any other kind => +1 rung, clamped at MAX.
    to_level = from_level if kind == "flat" else min(from_level + 1, _MAX_LEVEL)
    # If the ladder didn't actually rise (an authored flat, OR a kind that hit the
    # MAX ceiling so the level is pinned), the escalation IS flat regardless of the
    # keyword — otherwise a run stuck at level 10 would read as endless "升级" and
    # the tension-stall detector (9.3) would never fire. Honesty over the label.
    if to_level <= from_level:
        kind = "flat"
    escalation: dict[str, Any] = {
        "from_level": from_level, "to_level": to_level, "kind": kind,
    }
    esc_line = str(beat.get("escalation", "")).strip()
    if esc_line:
        escalation["vs_previous"] = esc_line

    # ③ inner_shift — `from` folds from the prior mandate's `to`
    inner_from = prev_inner.get("to") or _inner_from_seed(outline)
    dimension = _inner_dimension(beat)
    reward = str(beat.get("reward_if_any", "")).strip()
    goal_txt = str(beat.get("goal", "")).strip()
    inner_to = reward or goal_txt or inner_from
    inner_shift: dict[str, Any] = {
        "dimension": dimension, "from": inner_from, "to": inner_to,
    }
    if goal_txt and goal_txt != inner_to:
        inner_shift["cause"] = goal_txt

    # ④ net_advance
    main_line = goal_txt or trigger
    # irreversible when the chapter delivers a reward/reveal or escalates the
    # stakes structurally; a pure flat transition is reversible (原地打转 signal).
    irreversible = bool(reward) or kind in (
        "reversal", "betrayal", "power_reveal", "new_antagonist")
    net_advance: dict[str, Any] = {
        "main_line": main_line, "irreversible": irreversible,
    }
    if arc_band:
        net_advance["arc_goal"] = arc_band.get("goal") or arc_band.get("stage_goal") or arc_band.get("purpose")
    thread = (outline or {}).get("id")
    if thread:
        net_advance["advances_thread"] = thread

    mandate: dict[str, Any] = {
        "id": f"MND-{chapter_no:05d}",
        "kind": "narrative_mandate",
        "authority": "human",
        "gating": False,
        "schema_version": "1.0",
        "chapter_no": chapter_no,
        "task_id": task_id,
        "why_now": why_now,
        "escalation": escalation,
        "inner_shift": inner_shift,
        "net_advance": net_advance,
    }
    prov: dict[str, Any] = {}
    if derived_from is not None:
        prov["derived_from"] = list(derived_from)
    if source_version is not None:
        prov["source_version"] = source_version
    if prev_mandate and prev_mandate.get("id"):
        prov["prev_mandate_id"] = prev_mandate["id"]
    if prov:
        mandate["provenance"] = prov

    # content_hash over the semantic core (excludes provenance/id, like peers)
    core = {k: mandate[k] for k in
            ("chapter_no", "why_now", "escalation", "inner_shift", "net_advance")}
    mandate["content_hash"] = _hash(core)
    return mandate


def validate_narrative_mandate(mandate: dict) -> list[str]:
    validator = Draft202012Validator(_load_schema())
    errs = []
    for e in sorted(validator.iter_errors(mandate), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in e.path) or "(root)"
        errs.append(f"{loc}: {e.message}")
    return errs


_KIND_LABELS = {
    "stakes_raise": "赌注升级", "new_antagonist": "新敌登场", "reversal": "反转",
    "betrayal": "背叛", "time_pressure": "时间压迫", "power_reveal": "力量揭示",
    "flat": "无升级（预警）",
}
_DIM_LABELS = {
    "belief": "信念", "goal": "目标", "fear": "恐惧", "value": "价值观",
    "relationship": "关系", "resolve": "决心",
}


def render_narrative_mandate(mandate: dict) -> str:
    """Compress a NarrativeMandate into a compact string for the v8 prompt's
    `narrative_mandate` variable. Deterministic + bounded, mirroring
    render_chapter_objective. This is the TOP intent above the objective: it tells
    the drafter WHY this chapter must happen now, how far the conflict rises, how
    the protagonist changes inside, and what irreversible advance it commits —
    directly attacking 流水账."""
    wn = mandate.get("why_now") or {}
    esc = mandate.get("escalation") or {}
    ins = mandate.get("inner_shift") or {}
    na = mandate.get("net_advance") or {}
    lines: list[str] = []

    trigger = wn.get("trigger")
    if trigger:
        cod = wn.get("cost_of_delay")
        cod_note = "（无时间压力，警惕温水章）" if cod == "none" else f"（拖延代价：{cod}）"
        lines.append(f"为何是现在：{trigger}{cod_note}")
    if wn.get("clock"):
        lines.append(f"时间锚/钩子：{wn['clock']}")

    kind = esc.get("kind")
    kind_label = _KIND_LABELS.get(kind, kind or "")
    lines.append(
        f"冲突阶梯：{esc.get('from_level')} → {esc.get('to_level')}（{kind_label}）")
    if esc.get("vs_previous"):
        lines.append(f"较上一章：{esc['vs_previous']}")

    dim = _DIM_LABELS.get(ins.get("dimension"), ins.get("dimension") or "")
    if ins.get("from") and ins.get("to"):
        line = f"主角内在移动（{dim}）：{ins['from']} → {ins['to']}"
        if ins.get("cause"):
            line += f"（因：{ins['cause']}）"
        lines.append(line)

    if na.get("main_line"):
        irr = "不可逆" if na.get("irreversible") else "可逆（警惕原地打转）"
        lines.append(f"净推进主线：{na['main_line']}（{irr}）")

    return "\n".join(lines)



