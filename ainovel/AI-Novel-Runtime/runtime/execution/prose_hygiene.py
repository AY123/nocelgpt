"""prose_hygiene.py — detection→correction loop for single-chapter prose (ANES v2, ADR-003).

The §14.5 verdict made executable: a production SYSTEM makes ANY model produce a
commercially-acceptable draft via constraints, not by swapping in a stronger model.
The three single-chapter detectors (density = 注水, ai_taste = AI 味) already
MEASURE the tells; this loop CORRECTS them: it turns their warnings into a targeted
rewrite, re-checks DETERMINISTICALLY, and keeps the best draft.

ARCHITECTURE — a thin adapter over the existing rewrite atom, NOT a second rewrite
engine (same discipline as Phase 7's compare/select). It reuses
revision.rewrite_once (which owns the rewrite prompt + hash discipline). It differs
from revise_until in ONE deliberate way: the re-check is the DETERMINISTIC detector
set, not an LLM judge — cheaper (only the rewrite spends API; the check is free) and
reproducible (same draft => same warning count, so "better" is objective).

Scope is body-level prose HYGIENE: density + ai_taste, both of which read the body
text. Pacing is excluded — it reads the scene plan's emotion curve (a structural
layer needing LLM enrichment), not something a prose rewrite fixes.

DISCIPLINE:
  - never gates (ADR-003): HygieneSession.gating is a structural-false invariant.
  - keep-best: the returned draft is never worse (by warning count) than the input.
  - writes no facts; reuses rewrite_once (imports no new model path).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .draft_review import ReviewFinding
from .density import check_density
from .humanization import check_ai_taste
from .hook_check import check_end_hook
from .revision import rewrite_once

# Deterministic rewrite guidance per detector. The check name (density / ai-taste)
# is the revision_plan `dimension`; the action is the targeted fix the rewriter is
# told to apply. Kept here so the adapter layer is the single place that maps a
# detector's finding to a rewrite instruction.
_ACTION_BY_CHECK = {
    "density": "删减无信息量的氛围铺陈，增加对白与具体动作，提高单位篇幅的信息密度",
    "ai-taste": "打散连续同头排比、拆解破折号套嵌同位语、让句子长短交错，去除机器腔",
    "end-hook": "重写章节结尾：不要收于平息或情绪落地，改以未决疑问/悬置动作/转折威胁收束，留下追读钩子",
}

HYGIENE_CONTROLLER_ID = "prose-hygiene-v1"

# Deletion-cheat guard. A rewrite can lower an ai_taste/density defect distance by
# DELETING content instead of rewriting it — real A/B saw the biggest defect drops
# land on the biggest length losses (len×0.6, len×0.75). A rewrite whose body
# falls below this fraction of the ORIGINAL chapter length is rejected as a
# gutting, however much it "converges", so convergence can't be won by cutting the
# chapter. Measured against the ORIGINAL (not the previous round) so multi-round
# incremental trimming can't creep past the floor. Legitimate hygiene rewrites are
# length-preserving (A/B clean cases were 0.92-1.0×), so 0.8 clears them.
_LENGTH_FLOOR_FRACTION = 0.8


def _body_len(artifact: dict) -> int:
    return len((artifact or {}).get("body", "") or "")


# Unified market-anchored feature spec. Every body-level prose feature the
# reference anchor measures maps to: the DEFECT side of the band (which side reads
# as a flaw — the opposite side is BETTER than the market and must never trigger a
# rewrite), the hygiene `check` lane it belongs to, and a QUANTIFIED per-feature
# fix template (current value → market target). This ONE table drives both the
# market-anchored findings and the defect-distance keep-best tie-breaker, so the
# ai_taste (AI-味) and density (注水) families share the EXACT same discipline —
# each anchored to what a market winner (盘龙) actually looks like, not an
# arbitrary fixed constant. Real-data: for BOTH families the market band is a
# strict superset of the fixed thresholds (fixed-only=0, ~12 chapters band-out but
# fixed-clean), so anchoring only ADDS the missed chapters. end-hook is a boolean
# structural check (no band), so it stays on its fixed detector.
_MARKET_FEATURE_SPEC = {
    # ai_taste — the AI-tell family (§14 anti-AI-味)
    "ai_taste.anaphora_run": {
        "defect": "above", "check": "ai-taste",
        "fix": "连续同头排比过多（当前最长 {value} 句同头，畅销参考章通常 ≤{target}）："
               "打散重复的句首，改变起句方式，不要连续多句用同一个词/结构开头"},
    "ai_taste.dash_aside_per_1000": {
        "defect": "above", "check": "ai-taste",
        "fix": "破折号插入语过密（当前每千字 {value}，畅销参考章 ≈{target}）："
               "删除破折号套嵌的同位语/补充说明，改写为独立短句，避免 —…— 夹注"},
    "ai_taste.sentence_length_cv": {
        "defect": "below", "check": "ai-taste",
        "fix": "句长过于均匀（当前长度变异 CV {value}，畅销参考章 ≈{target}）："
               "让句子长短交错，穿插更短的动作句和更长的描写句，制造节奏起伏"},
    # density — the 注水 family (§14 anti-注水)
    "density.dialogue_ratio": {
        "defect": "below", "check": "density",
        "fix": "对白占比过低（当前 {value}，畅销参考章 ≈{target}）："
               "增加人物对话与交锋，用对白推进情节，减少大段纯叙述铺陈"},
    "density.simile_per_1000": {
        "defect": "above", "check": "density",
        "fix": "比喻/氛围句过密（当前每千字 {value}，畅销参考章 ≈{target}）："
               "删减堆砌的比喻和氛围描写，只留最有力的一两处，代之以具体动作与细节"},
    "density.opening_simile_per_1000": {
        "defect": "above", "check": "density",
        "fix": "开篇比喻堆砌（开篇每千字 {value}，畅销参考章 ≈{target}）："
               "开篇少用氛围铺陈，尽快进入事件与冲突，把比喻分散到全章"},
}

# Backward-compat view: the ai_taste defect directions, derived from the unified
# spec (some call sites / tests reference this family explicitly).
_AI_TASTE_DEFECT_DIRECTION = {
    f: s["defect"] for f, s in _MARKET_FEATURE_SPEC.items() if f.startswith("ai_taste.")
}


def _market_findings(artifact: dict, reference_profile: dict) -> List[ReviewFinding]:
    """Market-anchored replacement for the fixed-threshold ai_taste AND density
    warnings: any band-measured feature sitting OUT of the reference band ON ITS
    DEFECT SIDE is a flaw measured against a market winner, not an arbitrary
    constant. Each message is a SELF-CONTAINED, QUANTIFIED per-feature instruction
    (current value → market target) so the rewriter fixes the specific issue that
    fired, not a generic lump. Defect direction only — never rewrites prose that
    is already cleaner than the market. Emits each feature under its own `check`
    lane (ai-taste / density) so plan/keep-best treat them consistently. Real-data
    (genesis-pilot vs 盘龙): the market band is a strict superset of the fixed
    thresholds for both families (fixed-only=0), so this only ADDS the ~12 chapters
    per family that pass the loose fixed floor yet read nothing like the market."""
    from ..reference import measure_reference_chapter, compare_to_profile
    body = artifact.get("body", "")
    gap = compare_to_profile(measure_reference_chapter(body), reference_profile)
    findings: List[ReviewFinding] = []
    for feature, spec in _MARKET_FEATURE_SPEC.items():
        g = gap.get("features", {}).get(feature)
        if not g or g["in_band"] or g["direction"] != spec["defect"]:
            continue
        band = g["band"]
        # the market target is the band edge the draft must move back toward:
        # for an above-band defect that's q3 (upper edge), for below-band q1.
        target = band[1] if spec["defect"] == "above" else band[0]
        message = spec["fix"].format(value=g["value"], target=target)
        # anaphora: quote the offending sentences (量化→定位). The count-only
        # instruction let borderline 3-runs survive (tighten0716 ch3); naming the
        # exact sentences removes the "can't find them" skip. Location only — the
        # metric/target text is unchanged, so the 畅销参考章 marker and 同头 substring
        # (asserted by tests) still hold, and a feature we can't locate degrades to
        # the plain quantified message.
        #
        # Phase 1 Task 1.2.2: Enhanced with span locations for quantified instructions
        if feature == "ai_taste.anaphora_run":
            from .humanization import locate_anaphora_spans
            spans = locate_anaphora_spans(body)
            if spans:
                # Build quantified instruction with exact locations
                sentence_indices = [s["sentence_index"] + 1 for s in spans]  # 1-indexed for human
                start_idx = sentence_indices[0]
                end_idx = sentence_indices[-1]

                # Calculate approximate word position (char_offset / 2 for CJK, /5 for English)
                start_offset = spans[0]["char_offset"]
                end_offset = spans[-1]["char_offset"] + spans[-1]["length"]
                approx_word_start = start_offset // 2 if any('一' <= c <= '鿿' for c in body) else start_offset // 5
                approx_word_end = end_offset // 2 if any('一' <= c <= '鿿' for c in body) else end_offset // 5

                # Quote the sentences
                quoted = "；".join(f"「{s['text']}」" for s in spans)

                # Quantified instruction with locations
                message += (
                    f"。具体位置：第{start_idx}-{end_idx}句"
                    f"（约第{approx_word_start}-{approx_word_end}字），"
                    f"需改写这几句同头：{quoted}"
                )
        findings.append(ReviewFinding(spec["check"], "warning", message))
    return findings


# Backward-compat alias — the ai_taste-only entry point some tests still call.
def _market_ai_taste_findings(artifact: dict, reference_profile: dict) -> List[ReviewFinding]:
    return [f for f in _market_findings(artifact, reference_profile) if f.check == "ai-taste"]


def _defect_distance(artifact: dict, reference_profile: Optional[dict]) -> float:
    """Total ai_taste defect-side distance from the market band — the CONTINUOUS
    companion to the binary warning count. Zero-tolerance bands (dash [0,0]) make
    the warning count too coarse: a rewrite that cuts dash density 1.25 -> 0.3
    clearly converges toward the market but leaves the warning ON (still >0), so a
    count-only keep-best discards it. This scalar lets the loop keep such partial
    progress as a tie-breaker. 0.0 when no profile (no band to converge to)."""
    if reference_profile is None:
        return 0.0
    from ..reference import measure_reference_chapter, compare_to_profile
    gap = compare_to_profile(measure_reference_chapter(artifact.get("body", "")),
                             reference_profile)
    total = 0.0
    for feature, spec in _MARKET_FEATURE_SPEC.items():
        g = gap.get("features", {}).get(feature)
        if g and not g["in_band"] and g["direction"] == spec["defect"]:
            total += g["edge_gap"]
    return round(total, 4)


def hygiene_findings(artifact: dict, *, objective: Optional[dict] = None,
                     reference_profile: Optional[dict] = None) -> List[ReviewFinding]:
    """Run the body-level prose detectors and return only the WARNING findings
    (info notes never trigger a rewrite). Deterministic: same body => same list.
    `objective` (optional ChapterObjective) lets the end-hook detector cross-check
    the declared cliffhanger_type against delivery.

    `reference_profile` (optional M9 anchor): when supplied, BOTH the ai_taste
    (AI-味) and density (注水) arms are measured against the MARKET BAND (defect
    direction only, quantified per-feature) instead of the fixed thresholds — a
    strict superset that catches chapters passing the loose floor yet diverging
    from a market winner. Absent => fixed thresholds => byte-identical to before.
    end-hook is a boolean structural check (no band), so it always stays fixed.

    Phase 1 Task 1.2.4: Template detector integrated — detects high-frequency
    AI template phrases (e.g., "他知道", "沉默了片刻") that the LLM judge misses."""
    findings: List[ReviewFinding] = []
    if reference_profile is not None:
        # market-anchored density + ai_taste, both quantified per-feature
        findings.extend(_market_findings(artifact, reference_profile))
    else:
        findings.extend(f for f in check_density(artifact).findings if f.severity == "warning")
        findings.extend(f for f in check_ai_taste(artifact).findings if f.severity == "warning")
    findings.extend(f for f in check_end_hook(artifact, objective=objective).findings
                    if f.severity == "warning")

    # Phase 1 Task 1.2.4: Template overuse detection
    # Detect high-frequency AI template phrases that evade the LLM judge but
    # accumulate across chapters (e.g., "他知道" × 268 in RUN-00001).
    # Only warnings trigger rewrites (severity == "warning").
    from .template_detector import detect_template_phrases, format_template_finding
    body = artifact.get("body", "")
    if body:
        template_issues = detect_template_phrases(body)
        for issue in template_issues:
            if issue["severity"] == "warning":
                message = format_template_finding(issue)
                findings.append(ReviewFinding("ai-taste", "warning", message))

    return findings


def _warning_count(artifact: dict, *, objective: Optional[dict] = None,
                   reference_profile: Optional[dict] = None) -> int:
    """The deterministic scalar the keep-best comparison uses: how many prose-
    hygiene warnings the draft trips. Lower is better."""
    return len(hygiene_findings(artifact, objective=objective,
                                reference_profile=reference_profile))


# Marker present only in market-anchored ai_taste messages (they are already a
# self-contained quantified instruction). Used to avoid re-appending the generic
# lump action, which would re-mix all three tells and dilute a single-tell fix —
# the exact reason dash-only chapters stayed stuck in the A/B.
_MARKET_FINDING_MARKER = "畅销参考章"


def _warnings_to_revision_plan(findings: List[ReviewFinding]) -> List[dict]:
    """Adapt deterministic ReviewFindings into the revision_plan shape rewrite_once
    expects. This is the whole ReviewReport→revision_plan bridge: each warning's
    message is the issue, and its check maps to a targeted rewrite action. A
    market-anchored ai_taste message is ALREADY a quantified, self-contained
    instruction, so it keeps a terse 'follow the target above' action instead of
    the generic lump — otherwise the generic action would re-introduce the three
    mixed tells the quantified message deliberately isolated."""
    plan: List[dict] = []
    for f in findings:
        if _MARKET_FINDING_MARKER in f.message:
            action = "按上述量化目标修订该项，不要改动未被指出的其他方面"
        else:
            action = _ACTION_BY_CHECK.get(f.check, "针对性修订上述问题")
        plan.append({
            "dimension": f.check,
            "priority": "P1",
            "issue": f.message,
            "action": action,
        })
    return plan


@dataclass
class HygieneSession:
    """Audit record of a hygiene correction, riding the envelope like
    RevisionSession / commercial_session. Never gates (structural invariant)."""
    controller: str
    rounds: List[dict] = field(default_factory=list)
    terminate_reason: str = "max_rounds"
    verdict: str = "unchanged"          # unchanged | improved | no_improvement | degraded
    selected_draft_hash: str = ""
    gating: bool = False                # structural invariant — never blocks

    def to_dict(self) -> dict:
        return {
            "controller": self.controller,
            "gating": self.gating,
            "terminate_reason": self.terminate_reason,
            "verdict": self.verdict,
            "selected_draft_hash": self.selected_draft_hash,
            "rounds": self.rounds,
        }


@dataclass
class HygieneResult:
    session: HygieneSession
    final_artifact: dict


def _reference_gap(artifact: dict, reference_profile: Optional[dict],
                   *, target_wordcount: Optional[int] = None) -> Optional[dict]:
    """The M9.1 advisory signal: place this draft's body against the market-
    validated reference bands. Recorded per round for audit — it NEVER feeds the
    keep-best decision (that stays warning-count only, ADR-003). None when no
    profile is pinned. Imported lazily so hygiene keeps importing no model path."""
    if reference_profile is None:
        return None
    from ..reference import measure_reference_chapter, compare_to_profile
    measurement = measure_reference_chapter((artifact or {}).get("body", ""),
                                            target_wordcount=target_wordcount)
    return compare_to_profile(measurement, reference_profile)


def improve_prose_hygiene(
    rewrite_model,
    artifact: dict,
    package: dict,
    *,
    max_rounds: int = 2,
    controller_id: str = HYGIENE_CONTROLLER_ID,
    objective: Optional[dict] = None,
    reference_profile: Optional[dict] = None,
) -> HygieneResult:
    """Iteratively rewrite to clear body-level prose-hygiene warnings, re-checking
    DETERMINISTICALLY each round. Accepts a rewrite only when it strictly lowers
    the warning count; always returns the BEST (fewest-warning) draft seen, never
    worse than the input. Purely advisory — never gates.

    Only the rewrite spends API; the re-check (density + ai_taste + end_hook) is
    free and reproducible, so "better" is an objective, replayable judgment.
    `objective` (optional ChapterObjective) is passed to the end-hook detector for
    the declared/delivered cliffhanger cross-check.

    `reference_profile` (optional M9 anchor) adds a per-round `reference_gap`
    advisory reading to the session — how far each round's draft sits from a
    market-validated chapter. It is RECORDED ONLY: the keep-best decision remains
    warning-count-only, so the gap never gates or reorders selection (ADR-003)."""
    session = HygieneSession(controller=controller_id)

    current = artifact
    current_warnings = _warning_count(current, objective=objective,
                                      reference_profile=reference_profile)
    # keep-best key is LEXICOGRAPHIC (warning_count, defect_distance), both
    # lower-is-better. Distance is 0.0 without a profile, so the key collapses to
    # the count and behavior is byte-identical to the count-only loop. With a
    # profile it breaks ties the binary count can't: a rewrite that shrinks a
    # zero-tolerance-band defect (e.g. dash 1.25->0.3) but doesn't clear it keeps
    # the same warning count yet strictly lowers the distance — real convergence
    # the count-only keep-best discarded (A/B: 1/5 -> more).
    best_artifact = current
    best_count = current_warnings
    best_distance = _defect_distance(current, reference_profile)
    # Deletion-cheat floor: measured against the ORIGINAL body so multi-round
    # trimming can't creep past it. A rewrite shorter than this is rejected below
    # no matter how much its defect distance dropped. ONLY active on the market-
    # anchored path (a profile is present) — that is where the cheat was observed,
    # and it preserves the load-bearing "no profile => byte-identical" invariant.
    # 0 disables the floor (no profile).
    length_floor = (int(_body_len(artifact) * _LENGTH_FLOOR_FRACTION)
                    if reference_profile is not None else 0)

    if current_warnings == 0:
        session.terminate_reason = "no_warnings"
        session.verdict = "unchanged"
        session.selected_draft_hash = current.get("content_hash", "")
        return HygieneResult(session, best_artifact)

    for rnd in range(1, max_rounds + 1):
        findings = hygiene_findings(current, objective=objective,
                                    reference_profile=reference_profile)
        plan = _warnings_to_revision_plan(findings)
        revised = rewrite_once(rewrite_model, current, package, plan)

        if revised is None:
            session.rounds.append({
                "round": rnd,
                "draft_hash_before": current.get("content_hash", ""),
                "draft_hash_after": current.get("content_hash", ""),
                "warnings_before": best_count,
                "warnings_after": best_count,
                "degraded": True,
                "note": "rewrite model produced no usable prose",
            })
            session.terminate_reason = "degraded"
            break

        revised_count = _warning_count(revised, objective=objective,
                                       reference_profile=reference_profile)
        revised_distance = _defect_distance(revised, reference_profile)
        revised_len = _body_len(revised)
        too_short = revised_len < length_floor
        round_record = {
            "round": rnd,
            "draft_hash_before": current.get("content_hash", ""),
            "draft_hash_after": revised.get("content_hash", ""),
            "warnings_before": _warning_count(current, objective=objective,
                                              reference_profile=reference_profile),
            "warnings_after": revised_count,
            "defect_distance_before": best_distance,
            "defect_distance_after": revised_distance,
            "length_before": _body_len(artifact),
            "length_after": revised_len,
            "length_floor": length_floor,
            "rejected_as_gutting": too_short,
            "targeted_dimensions": [item["dimension"] for item in plan],
            "degraded": False,
        }
        # Advisory M9.1 reading — recorded, never part of the accept decision below.
        gap = _reference_gap(revised, reference_profile)
        if gap is not None:
            round_record["reference_gap"] = gap
        session.rounds.append(round_record)

        # Deletion-cheat guard FIRST: a rewrite that gutted the chapter below the
        # length floor is rejected outright, however much its defect distance
        # dropped — convergence must come from rewriting, not cutting. Stop the
        # loop (further rounds would rewrite the same too-short draft).
        if too_short:
            session.terminate_reason = "rejected_gutting"
            break

        # Accept a STRICT improvement on the LEXICOGRAPHIC key (fewer warnings, or
        # equal warnings but a strictly smaller defect distance). The distance
        # tie-breaker keeps partial convergence toward a zero-tolerance band that
        # the binary count throws away. Never accepts a worse draft (monotone), so
        # keep-best still never gates (ADR-003). Otherwise stop — don't burn budget.
        if (revised_count, revised_distance) < (best_count, best_distance):
            current, current_warnings = revised, revised_count
            best_artifact, best_count, best_distance = revised, revised_count, revised_distance
            if revised_count == 0:
                session.terminate_reason = "clean"
                break
        else:
            session.terminate_reason = "no_improvement"
            break
    else:
        session.terminate_reason = "max_rounds"

    orig_count = _warning_count(artifact, objective=objective,
                                reference_profile=reference_profile)
    orig_distance = _defect_distance(artifact, reference_profile)
    if session.terminate_reason == "degraded":
        session.verdict = "degraded"
    elif (best_count, best_distance) < (orig_count, orig_distance):
        # improved on the lexicographic key: fewer warnings, OR equal warnings but
        # a strictly smaller defect distance (partial convergence toward the band).
        # This is checked BEFORE rejected_gutting so a legit earlier round is still
        # credited even if a later round was rejected for gutting.
        session.verdict = "improved"
    elif session.terminate_reason == "rejected_gutting":
        # every rewrite that converged did so by gutting the chapter; kept the
        # original rather than a hollowed-out draft.
        session.verdict = "rejected_gutting"
    elif session.terminate_reason == "no_improvement":
        session.verdict = "no_improvement"
    else:
        session.verdict = "unchanged"

    session.selected_draft_hash = best_artifact.get("content_hash", "")
    return HygieneResult(session, best_artifact)
