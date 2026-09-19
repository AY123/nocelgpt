"""test_prose_hygiene.py — detection→correction loop (ANES v2, §14.5, ADR-003).

Pins the loop that turns the deterministic density + ai_taste WARNINGS into a
targeted rewrite: it reuses rewrite_once (no second rewrite engine), re-checks
DETERMINISTICALLY, accepts only a strict warning-count improvement, always keeps
the best (never-worse) draft, and never gates. Stub models keep it API-free.

Load-bearing properties:
  - an improving rewrite lowers the warning count → verdict=improved, hash changes
  - a no-op / worsening rewrite is rejected → original kept, never worse
  - a clean input never calls the rewriter (0 rounds)
  - a degraded rewrite (None) terminates cleanly, original kept
  - the serial loop is byte-identical when hygiene_model is absent
"""
from __future__ import annotations

from pathlib import Path

import yaml

from runtime.execution.model import ModelOutput
from runtime.execution.prose_hygiene import (
    improve_prose_hygiene, hygiene_findings, _warning_count,
    _warnings_to_revision_plan, HYGIENE_CONTROLLER_ID)
from runtime.serialize import run_serial

HERE = Path(__file__).resolve().parent
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


# A draft that trips both detectors: anaphora stacking + no dialogue + similes.
_DIRTY = (
    "He had not eaten. He had not slept. He had not stopped moving. "
    "The rain fell like glass. The wind cut like a blade. The night pressed "
    "like a shroud. The road stretched like a wound across the hills."
) * 3

# A clean, concrete, dialogue-rich rewrite target.
_CLEAN = (
    "「站住。」马伦举起铁锤挡在门口。埃德里克抬起头，低声报出名字。"
    "她皱眉，把一碗温水递过去，问他从哪儿来。他沉默良久，终于开口，说出那座被烧毁的城邦。"
)


def _artifact(body: str, tag: str = "a") -> dict:
    return {
        "task_id": "TASK-00001",
        "kind": "prose",
        "capability": "ChapterDraft",
        "body": body,
        "content_hash": "sha256:" + tag * 64,
        "provenance": {"derived_from": ["CHR-00001@v1"], "source_version": 1},
        "word_count": len(body),
    }


_PKG = {"task": {"task_id": "TASK-00001"}, "context": {}}


class _Stub:
    """A rewrite model that always returns a fixed body."""
    def __init__(self, text, model_id="hygiene-stub"):
        self._text = text
        self.model_id = model_id

    def generate(self, prompt):
        return ModelOutput(text=self._text, model_id=self.model_id, model_kind="llm")


class _DegradeStub:
    model_id = "degrade-stub"

    def generate(self, prompt):
        return ModelOutput(text="", model_id=self.model_id, model_kind="llm")


# --------------------------------------------------------------------------- #
# Adapter layer                                                               #
# --------------------------------------------------------------------------- #
def test_only_warnings_become_revision_plan():
    art = _artifact(_DIRTY)
    findings = hygiene_findings(art)
    assert findings and all(f.severity == "warning" for f in findings)
    plan = _warnings_to_revision_plan(findings)
    assert len(plan) == len(findings)
    dims = {item["dimension"] for item in plan}
    assert dims <= {"density", "ai-taste", "end-hook"}
    assert all(item["action"] for item in plan)  # every plan item carries a fix


def test_clean_draft_has_no_warnings():
    assert _warning_count(_artifact(_CLEAN)) == 0


# --------------------------------------------------------------------------- #
# end-hook is now a hygiene signal the loop can correct                        #
# --------------------------------------------------------------------------- #
_EMO_CLOSE = (
    "「站住。」马伦举起铁锤挡在门口。埃德里克抬头，低声报出名字。"
    "她皱眉，把一碗温水递过去，问他从哪儿来。他沉默良久，终于开口，说起那座被烧毁的城邦。"
    "两人在炉火边说了很久，话里话外都是过往。" * 2
    + "他终于松了口气，靠着墙沉沉睡去，一切都会好起来的。")
_HOOKED = (
    "「站住。」马伦举起铁锤挡在门口。埃德里克抬头，低声报出名字。"
    "她皱眉，把一碗温水递过去，问他从哪儿来。他沉默良久，终于开口，说起那座被烧毁的城邦。"
    "两人在炉火边说了很久，话里话外都是过往。" * 2
    + "就在这时，门外突然响起沉重的脚步声，一个陌生的声音低喝：他在里面吗？")


def test_emotional_close_is_a_correctable_hygiene_warning():
    # the §14 finding-3 tell: an emotional/settling close is now a hygiene warning
    # (end-hook), and the loop can correct it by rewriting to a hooked ending.
    art = _artifact(_EMO_CLOSE)
    findings = hygiene_findings(art)
    assert any(f.check == "end-hook" for f in findings)
    res = improve_prose_hygiene(_Stub(_HOOKED), art, _PKG)
    assert res.session.verdict == "improved"
    assert _warning_count(res.final_artifact) < _warning_count(art)


def test_objective_declared_hook_threads_into_hygiene():
    # objective cross-check flows through the loop: a neutral ending with a
    # declared cliffhanger counts as a warning the loop sees.
    neutral = _artifact(
        "马伦收拾好碗筷，往炉里添了块柴。埃德里克靠在墙边，慢慢活动着僵硬的肩膀。"
        "两人有一搭没一搭地聊着镇上的事，谁也没提更远的将来。窗外的雨小了些，"
        "檐下滴着水。" * 3
        + "他放下碗，望着窗外，心里想着明天该往哪里走。")
    assert len(neutral["body"]) >= 200      # long enough for the hook detector
    obj = {"cliffhanger_type": "threat"}
    n_without = _warning_count(neutral)
    n_with = _warning_count(neutral, objective=obj)
    assert n_with > n_without


# --------------------------------------------------------------------------- #
# keep-best correction loop                                                   #
# --------------------------------------------------------------------------- #
def test_improving_rewrite_is_accepted():
    art = _artifact(_DIRTY)
    before = _warning_count(art)
    assert before > 0
    res = improve_prose_hygiene(_Stub(_CLEAN), art, _PKG)
    assert res.session.verdict == "improved"
    assert _warning_count(res.final_artifact) < before
    assert res.final_artifact["content_hash"] != art["content_hash"]
    assert res.session.gating is False


def test_noop_rewrite_is_rejected_and_original_kept():
    # rewriter returns the same dirty prose → no improvement → keep original.
    art = _artifact(_DIRTY)
    res = improve_prose_hygiene(_Stub(_DIRTY), art, _PKG)
    assert res.session.verdict == "no_improvement"
    assert res.final_artifact["content_hash"] == art["content_hash"]
    # never worse than the input
    assert _warning_count(res.final_artifact) == _warning_count(art)


def test_clean_input_skips_rewrite():
    art = _artifact(_CLEAN)
    res = improve_prose_hygiene(_Stub(_DIRTY), art, _PKG)
    assert res.session.terminate_reason == "no_warnings"
    assert res.session.rounds == []            # rewriter never called
    assert res.final_artifact["content_hash"] == art["content_hash"]


def test_degraded_rewrite_terminates_cleanly():
    art = _artifact(_DIRTY)
    res = improve_prose_hygiene(_DegradeStub(), art, _PKG)
    assert res.session.terminate_reason == "degraded"
    assert res.session.verdict == "degraded"
    assert res.final_artifact["content_hash"] == art["content_hash"]


def test_controller_id_and_session_shape():
    res = improve_prose_hygiene(_Stub(_CLEAN), _artifact(_DIRTY), _PKG)
    d = res.session.to_dict()
    assert d["controller"] == HYGIENE_CONTROLLER_ID
    assert d["gating"] is False
    assert "selected_draft_hash" in d and "rounds" in d


# --------------------------------------------------------------------------- #
# Serial integration                                                          #
# --------------------------------------------------------------------------- #
def _write(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False),
                    encoding="utf-8")


def _scaffold(root: Path, n_events: int = 2):
    facts, meta = root / "registry" / "facts", root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    _write(facts / "timelines" / "TML-00001.yaml", {
        "id": "TML-00001", "name": "主线", "status": "active",
        "fact_version": 1, "kind": "main"})
    _write(facts / "characters" / "CHR-00001.yaml", {
        "id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1})
    for i in range(1, n_events + 1):
        _write(facts / "events" / f"EVT-{i:05d}.yaml", {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active",
            "fact_version": 1, "timeline": "TML-00001", "sequence_index": i,
            "participants": ["CHR-00001"],
            "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []),
            "effects": ([f"EVT-{i+1:05d}"] if i < n_events else []),
            "summary": f"第{i}章"})


def _run(root, **kw):
    return run_serial(project_path=root, standard_root=STANDARD, schema_dir=SCHEMA,
                      out_dir=root / "build-serial", **kw)


def test_serial_without_hygiene_model_is_byte_identical(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _scaffold(a, 2)
    _scaffold(b, 2)
    r_plain = _run(a)
    r_hyg = _run(b, hygiene_model=None)   # explicit None → same path
    assert [c.draft_hash for c in r_plain.chapters] == [c.draft_hash for c in r_hyg.chapters]
    # hygiene field is absent (None) when the loop did not run
    assert all(c.hygiene is None for c in r_plain.chapters)


def test_serial_records_hygiene_never_gates_state_unchanged(tmp_path):
    base, hyg = tmp_path / "base", tmp_path / "hyg"
    _scaffold(base, 2)
    _scaffold(hyg, 2)
    r_base = _run(base)
    # a stub that returns clean prose — the deterministic draft is likely already
    # clean, so this mainly proves the loop runs, records, and never gates.
    r_hyg = _run(hyg, hygiene_model=_Stub(_CLEAN))
    assert r_hyg.produced == r_base.produced
    assert r_hyg.gating is False
    for c in r_hyg.chapters:
        assert c.hygiene is not None
        assert c.hygiene["gating"] is False
    # state is a fold of the SAME facts → per-chapter state hashes unchanged
    assert [c.state_hash for c in r_base.chapters] == [c.state_hash for c in r_hyg.chapters]
    assert all(ch["hygiene"] is not None for ch in r_hyg.to_dict()["chapters"])


# --------------------------------------------------------------------------- #
# M9.1 — reference gap rides the session as advisory, never gates keep-best    #
# --------------------------------------------------------------------------- #
def _ref_profile():
    from runtime.reference import build_reference_profile
    novel = "\n\n".join(
        f"第{i}章 章节{i}\n" + (_CLEAN * 4) for i in range(1, 4))
    return build_reference_profile([("REF-00001", novel)]).to_dict()


def test_hygiene_records_reference_gap_as_advisory():
    # The M9.1 invariant that still holds: the reference_gap DICT recorded per
    # round is purely advisory — gating=False, comparison_only=True — and is never
    # read by the accept logic. (Note: the market-band WARNINGS and defect DISTANCE
    # do drive selection since commits 14e510b/6eeeb53 — that is deliberate; only
    # the reference_gap dict itself stays advisory. An earlier version of this test
    # asserted "profile does not change selection", which became false at 14e510b.)
    art = _artifact(_DIRTY)
    profile = _ref_profile()
    r_gap = improve_prose_hygiene(_Stub(_CLEAN), art, _PKG, max_rounds=2,
                                  reference_profile=profile)
    r_plain = improve_prose_hygiene(_Stub(_CLEAN), art, _PKG, max_rounds=2)
    # the gap IS recorded, advisory, per non-degraded round
    assert r_gap.session.rounds, "expected at least one round"
    for rd in r_gap.session.rounds:
        if rd.get("degraded"):
            continue
        assert "reference_gap" in rd
        assert rd["reference_gap"]["gating"] is False
        assert rd["reference_gap"]["comparison_only"] is True
    # without a profile there is no reference_gap key at all (clean degrade)
    for rd in r_plain.session.rounds:
        assert "reference_gap" not in rd


def test_revision_records_reference_gap_without_changing_keepbest():
    from runtime.execution.revision import revise_until
    from runtime.execution.quality_center import llm_quality_judge
    from runtime.execution.model import ModelOutput

    # A judge stub that scores the rewrite strictly higher so a round is accepted,
    # and a rewrite stub that returns clean prose. The accept decision is the
    # judge-score comparison; the reference gap must not participate.
    class _JudgeModel:
        model_id = "judge-stub"
        def __init__(self):
            self.n = 0
        def generate(self, prompt):
            # first call (initial review) low; subsequent (re-score) high
            self.n += 1
            score = 40 if self.n == 1 else 95
            dims = ("hook_strength", "reward_density", "clarity", "pacing",
                    "character_consistency", "setting_consistency",
                    "promise_delivery", "emotional_impact", "originality_risk",
                    "reader_drop_risk", "safety_risk", "voice_distinction",
                    "scene_purpose", "dialogue_quality", "continuity",
                    "commercial_fit", "prose_control", "payoff_setup")
            body = "{" + ", ".join(f'"{d}": {score}' for d in dims) + \
                   ', "revision_plan": [{"dimension": "hook_strength", ' \
                   '"priority": "P1", "issue": "x", "action": "y"}]}'
            return ModelOutput(text=body, model_id=self.model_id, model_kind="llm")

    judge = llm_quality_judge(_JudgeModel())
    art = _artifact(_DIRTY)
    profile = _ref_profile()
    r_plain = revise_until(judge, _Stub(_CLEAN), art, _PKG, max_rounds=1)
    judge2 = llm_quality_judge(_JudgeModel())
    r_gap = revise_until(judge2, _Stub(_CLEAN), art, _PKG, max_rounds=1,
                         reference_profile=profile)
    assert r_gap.session.selected_draft_hash == r_plain.session.selected_draft_hash
    assert r_gap.session.verdict == r_plain.session.verdict
    for rd in r_gap.session.rounds:
        if rd.get("degraded"):
            continue
        assert "reference_gap" in rd
        assert rd["reference_gap"]["gating"] is False
    for rd in r_plain.session.rounds:
        assert "reference_gap" not in rd


def test_serial_chapter_run_carries_reference_gap(tmp_path):
    from runtime.reference import write_reference_profile, build_reference_profile
    root = tmp_path / "refgap"
    _scaffold(root, 2)
    # pin a reference profile so the serial loop folds a per-chapter gap
    novel = "\n\n".join(f"第{i}章 甲\n" + (_CLEAN * 4) for i in range(1, 4))
    write_reference_profile(root, build_reference_profile([("REF-00001", novel)]))
    r = _run(root)
    assert r.gating is False
    produced = [c for c in r.chapters if c.ok]
    assert produced, "expected at least one produced chapter"
    for c in produced:
        assert c.reference_gap is not None
        assert c.reference_gap["gating"] is False
        assert c.reference_gap["comparison_only"] is True
    # persisted to disk on the ChapterRun artifact
    assert all(ch["reference_gap"] is not None
               for ch in r.to_dict()["chapters"] if ch["ok"])


def test_serial_without_profile_has_no_reference_gap(tmp_path):
    root = tmp_path / "noref"
    _scaffold(root, 2)
    r = _run(root)   # no profile pinned
    assert all(c.reference_gap is None for c in r.chapters)


# --------------------------------------------------------------------------- #
# Market-anchored ai_taste warnings (defect-direction only, superset of fixed) #
# --------------------------------------------------------------------------- #
def _varied_market_profile():
    # A market anchor built from dialogue-rich, varied-length, dash-free prose:
    # high sentence-CV band, anaphora/dash bands at their floor. Mirrors 盘龙's
    # shape so a monotone generated chapter reads as below-band on CV.
    from runtime.reference import build_reference_profile
    ref = "\n\n".join(
        f"第{i}章 章节{i}\n" + (
            "「走吧。」他说。她皱眉，把一碗温水递过去，问他究竟从哪里来，"
            "声音压得很低，带着几分难以掩饰的试探。他沉默不语。良久，才缓缓开口。" * 12)
        for i in range(1, 4))
    return build_reference_profile([("REF-00001", ref)]).to_dict()


def test_no_profile_uses_fixed_thresholds_bytewise():
    # Without a profile, hygiene_findings must be byte-identical to the fixed
    # detector path (density + fixed ai_taste + end-hook).
    from runtime.execution.humanization import check_ai_taste
    art = _artifact(_DIRTY)
    got = [f.message for f in hygiene_findings(art)]
    fixed_ai = [f.message for f in check_ai_taste(art).findings if f.severity == "warning"]
    # every fixed ai-taste warning is present in the no-profile findings
    assert set(fixed_ai) <= set(got)


def test_market_band_catches_chapter_passing_fixed_floor():
    # The load-bearing case: a chapter whose CV clears the loose fixed floor
    # (0.35) — so the fixed detector is SILENT — but sits BELOW a market winner's
    # band, so the market path warns. This is the ~13 real chapters the fixed
    # threshold missed. Fixture CV ≈ 0.83: above 0.35, below the market band.
    from runtime.execution.humanization import check_ai_taste, ai_taste_summary
    mono = _artifact(
        "风停了。整片森林在午后的阳光下安静得没有一丝声响，连鸟鸣都消失了。他握紧了手中的剑。" * 15)
    cv = ai_taste_summary(mono["body"])["sentence_length_cv"]
    assert cv >= 0.35, f"fixture must clear the fixed floor (cv={cv})"
    fixed_warns = [f for f in check_ai_taste(mono).findings if f.severity == "warning"]
    assert not fixed_warns, "fixed detector must be silent on this fixture"
    market_warns = [f for f in hygiene_findings(mono, reference_profile=_varied_market_profile())
                    if f.check == "ai-taste"]
    assert market_warns, f"market band should flag a below-band CV (cv={cv})"


def test_market_band_does_not_flag_prose_cleaner_than_market():
    # A chapter CLEANER than the market on the defect side (higher CV, no dashes,
    # no anaphora stacking) must NOT be warned — defect-direction-only guarantees
    # we never rewrite prose that already beats the market.
    from runtime.execution.prose_hygiene import _market_ai_taste_findings
    profile = _varied_market_profile()
    clean = _artifact(
        "「站住！」马伦怒吼。埃德里克缓缓抬头，用一种近乎耳语、几乎听不见的声音，"
        "报出那个早被烧成灰烬的城邦的名字，随即闭口不言。她默默递过水。" * 10)
    warns = _market_ai_taste_findings(clean, profile)
    # no defect-side ai_taste warning (it may be above-band on CV = better, which
    # is explicitly not a defect)
    assert warns == [] or all("方向 above" not in w.message for w in warns
                              if "cv" in w.message)


def test_market_ai_taste_defect_direction_is_single_sided():
    # Direct unit check of the load-bearing invariant: only the defect side fires.
    from runtime.execution.prose_hygiene import (
        _market_ai_taste_findings, _AI_TASTE_DEFECT_DIRECTION)
    assert _AI_TASTE_DEFECT_DIRECTION["ai_taste.anaphora_run"] == "above"
    assert _AI_TASTE_DEFECT_DIRECTION["ai_taste.dash_aside_per_1000"] == "above"
    assert _AI_TASTE_DEFECT_DIRECTION["ai_taste.sentence_length_cv"] == "below"


def test_market_anaphora_instruction_quotes_the_offending_sentences():
    # 量化→定位: the anaphora market instruction must name the specific 同头 sentences
    # (the tighten0716 ch3 fix — a count-only instruction let a borderline 3-run
    # survive). Location is APPENDED; the quantified metric + 畅销参考章 marker stay.
    from runtime.execution.prose_hygiene import _market_ai_taste_findings
    profile = _varied_market_profile()
    dirty = _artifact(
        "他站起来，走向窗边。他停下脚步，回过头。他看着她，久久没有说话。"
        "「你到底想说什么。」她终于开口，声音里带着压不住的疲惫和一丝试探。" * 6)
    warns = _market_ai_taste_findings(dirty, profile)
    ana = [w for w in warns if "同头" in w.message]
    assert ana, "a stacked 3-run should fire the market anaphora warning"
    msg = ana[0].message
    assert "畅销参考章" in msg          # quantified metric preserved
    # Phase 1 Task 1.2.2: Enhanced with quantified locations
    assert "具体位置：第" in msg and "需改写这几句同头" in msg  # location appended with quantification
    assert "他站起来" in msg or "他停下脚步" in msg  # one of the sentences quoted
    assert "「他" in msg                # an offending sentence is quoted back


# --------------------------------------------------------------------------- #
# Lexicographic keep-best: partial convergence toward a zero-tolerance band     #
# (the A/B fix — count-only keep-best discarded these rewrites)                 #
# --------------------------------------------------------------------------- #
# A dialogue-rich, dash-free market anchor → dash band is [0,0] (zero-tolerance).
_DASH_FREE_MARKET = "\n\n".join(
    f"第{i}章 x\n" + ("「走吧。」他说。她皱眉，把碗递过去，问他从哪来，声音很轻。他沉默。良久，才开口。" * 15)
    for i in range(1, 4))
# Both bodies trip the SAME warning count (dash out of the [0,0] band), but LOW
# has far fewer dashes → a strictly smaller defect distance.
_HIGH_DASH = "他停下——那种迟疑——像是在等什么。她转身——头也不回——走了。" * 20
_LOW_DASH = "他停下，那种迟疑，像是在等什么。她转身——头也不回，走了。也许吧。" * 20


def _dash_market_profile():
    from runtime.reference import build_reference_profile
    return build_reference_profile([("REF-00001", _DASH_FREE_MARKET)]).to_dict()


def test_defect_distance_zero_without_profile():
    from runtime.execution.prose_hygiene import _defect_distance
    assert _defect_distance(_artifact(_HIGH_DASH), None) == 0.0


def test_keepbest_accepts_equal_count_lower_distance():
    # The A/B finding made executable: HIGH_DASH and LOW_DASH trip the same
    # warning count, so count-only keep-best would reject the rewrite. The
    # lexicographic (count, distance) key must ACCEPT it — LOW has a strictly
    # smaller defect distance (real convergence toward the [0,0] dash band).
    from runtime.execution.prose_hygiene import _warning_count, _defect_distance
    profile = _dash_market_profile()
    high, low = _artifact(_HIGH_DASH), _artifact(_LOW_DASH)
    # precondition: equal warning count, strictly lower distance
    assert _warning_count(high, reference_profile=profile) == \
           _warning_count(low, reference_profile=profile)
    assert _defect_distance(low, profile) < _defect_distance(high, profile)
    # the rewrite model returns the lower-dash body → must be accepted + selected
    res = improve_prose_hygiene(_Stub(_LOW_DASH), high, _PKG, max_rounds=1,
                                reference_profile=profile)
    assert res.final_artifact["body"] == _LOW_DASH
    assert res.session.verdict == "improved"


def test_keepbest_still_rejects_equal_count_equal_distance():
    # Guard the monotone invariant: a rewrite that changes nothing measurable
    # (same count, same distance) is NOT accepted — no spurious churn.
    profile = _dash_market_profile()
    high = _artifact(_HIGH_DASH)
    res = improve_prose_hygiene(_Stub(_HIGH_DASH), high, _PKG, max_rounds=1,
                                reference_profile=profile)
    assert res.session.verdict in ("no_improvement", "unchanged")


# --------------------------------------------------------------------------- #
# Quantified per-feature rewrite instructions (A/B follow-up: dash-only chapters
# stayed stuck under the generic lump action even with a strong model)          #
# --------------------------------------------------------------------------- #
def test_market_finding_message_is_quantified_per_feature():
    # A dash-heavy chapter against a dash-free market band must yield a message
    # that names the dash feature AND carries a concrete current-value → target.
    from runtime.execution.prose_hygiene import _market_ai_taste_findings
    profile = _dash_market_profile()
    findings = _market_ai_taste_findings(_artifact(_HIGH_DASH), profile)
    dash = [f for f in findings if "破折号" in f.message]
    assert dash, "expected a dash-aside finding"
    msg = dash[0].message
    assert "每千字" in msg and "≈0" in msg   # current density + market target 0


def test_market_plan_drops_generic_lump_action():
    # The revision plan for a market finding must NOT re-append the generic
    # three-tell lump action (that dilution left dash-only chapters stuck).
    from runtime.execution.prose_hygiene import (
        _market_ai_taste_findings, _warnings_to_revision_plan, _ACTION_BY_CHECK)
    profile = _dash_market_profile()
    plan = _warnings_to_revision_plan(_market_ai_taste_findings(_artifact(_HIGH_DASH), profile))
    assert plan, "expected at least one plan item"
    for item in plan:
        # the quantified issue rides; the generic lump action is replaced
        assert item["action"] != _ACTION_BY_CHECK["ai-taste"]
        assert "上述量化目标" in item["action"]


def test_fixed_path_still_uses_generic_action():
    # Without a profile (fixed-threshold path), the generic ai-taste action is
    # unchanged — byte-identical behavior preserved.
    from runtime.execution.prose_hygiene import (
        hygiene_findings, _warnings_to_revision_plan, _ACTION_BY_CHECK)
    plan = _warnings_to_revision_plan(hygiene_findings(_artifact(_DIRTY)))
    ai = [item for item in plan if item["dimension"] == "ai-taste"]
    if ai:  # _DIRTY trips the fixed ai-taste detector
        assert any(item["action"] == _ACTION_BY_CHECK["ai-taste"] for item in ai)


# --------------------------------------------------------------------------- #
# Market anchor generalized to the density (注水) family, not just ai_taste     #
# --------------------------------------------------------------------------- #
# A dialogue-rich, simile-free market anchor → high dialogue_ratio band, simile
# band near zero. A narration-only, simile-heavy chapter diverges on the DENSITY
# defect sides (dialogue below band, simile above band).
_DIALOGUE_MARKET = "\n\n".join(
    f"第{i}章 x\n" + ("「走吧。」他说。「等等，」她拉住他，「你还没说原因。」他回头，「因为危险。」" * 15)
    for i in range(1, 4))
_NARRATION_HEAVY = "夜色如墨，风声如泣，寒意如刀。他独自走在长街上，思绪如潮翻涌，往事如烟浮现。" * 20


def _dialogue_market_profile():
    from runtime.reference import build_reference_profile
    return build_reference_profile([("REF-00001", _DIALOGUE_MARKET)]).to_dict()


def test_market_anchor_covers_density_family():
    # The generalization: a low-dialogue chapter must now yield a market-anchored
    # DENSITY finding (quantified), not only ai_taste. Proves the anchor drives
    # the 注水 family the same way it drives AI-味.
    from runtime.execution.prose_hygiene import _market_findings
    findings = _market_findings(_artifact(_NARRATION_HEAVY), _dialogue_market_profile())
    density = [f for f in findings if f.check == "density"]
    assert density, "expected a market-anchored density finding"
    assert any("对白占比过低" in f.message and "≈" in f.message for f in density)


def test_defect_distance_includes_density():
    # The keep-best defect distance must fold density defects too, so a rewrite
    # that raises the dialogue ratio toward the band is kept even before it clears.
    from runtime.execution.prose_hygiene import _defect_distance
    profile = _dialogue_market_profile()
    d = _defect_distance(_artifact(_NARRATION_HEAVY), profile)
    assert d > 0, "narration-heavy chapter should carry a positive density defect distance"


def test_density_defect_direction_single_sided():
    # Load-bearing invariant carried over to density: dialogue defect is BELOW the
    # band (too little dialogue), simile defects ABOVE (too much atmosphere). A
    # dialogue-RICH chapter (above the band) is better than market → not flagged.
    from runtime.execution.prose_hygiene import _MARKET_FEATURE_SPEC, _market_findings
    assert _MARKET_FEATURE_SPEC["density.dialogue_ratio"]["defect"] == "below"
    assert _MARKET_FEATURE_SPEC["density.simile_per_1000"]["defect"] == "above"
    # a chapter MORE dialogue-rich than the market anchor is not a density defect.
    # Long quotes + minimal attribution push the ratio above the anchor's ~0.68.
    dialogue_rich = _artifact(
        "「我们必须现在就走，外面的人随时会冲进来，一刻都不能再等了。」他说。" * 30)
    from runtime.execution.density import density_summary
    profile = _dialogue_market_profile()
    ratio = density_summary(dialogue_rich["body"])["dialogue_ratio"]
    band = profile["bands"]["density.dialogue_ratio"]
    assert ratio >= band["q1"], f"fixture must be above the band (ratio={ratio}, band={band})"
    density = [f for f in _market_findings(dialogue_rich, profile)
               if f.check == "density" and "对白占比" in f.message]
    assert not density, "a dialogue-richer-than-market chapter must not be flagged"


# --------------------------------------------------------------------------- #
# Deletion-cheat guard: a rewrite can't win convergence by gutting the chapter  #
# (real A/B saw the biggest defect drops on the biggest length losses)          #
# --------------------------------------------------------------------------- #
# A long, dash-heavy original vs a dash-free market band → defect drops if the
# dashes go, but a rewrite that ALSO cuts the chapter to a stub is a cheat.
_DASH_HEAVY_LONG = "他停下——迟疑——像等什么。她转身——不回头——走了。" * 40
_GUTTED = "他走了。" * 5   # dash-clean but ~2% of the original length


def test_gutting_rewrite_is_rejected_under_market_anchor():
    profile = _dash_market_profile()
    art = _artifact(_DASH_HEAVY_LONG)
    res = improve_prose_hygiene(_Stub(_GUTTED), art, _PKG, max_rounds=1,
                                reference_profile=profile)
    # the gutted rewrite converges on defect but is rejected for length
    assert res.session.verdict == "rejected_gutting"
    assert res.final_artifact["body"] == _DASH_HEAVY_LONG   # original kept
    assert res.session.rounds[0]["rejected_as_gutting"] is True
    assert res.session.rounds[0]["length_after"] < res.session.rounds[0]["length_floor"]


def test_length_preserving_rewrite_still_accepted_under_market_anchor():
    # A rewrite that removes the dashes WITHOUT cutting length must still be
    # accepted — the guard only blocks gutting, never a genuine length-preserving
    # convergence (A/B clean cases were 0.92-1.0×).
    profile = _dash_market_profile()
    art = _artifact(_DASH_HEAVY_LONG)
    # same content, dashes replaced by commas → length ~preserved, defect drops
    clean_same_len = "他停下，迟疑，像等什么。她转身，不回头，走了。" * 40
    res = improve_prose_hygiene(_Stub(clean_same_len), art, _PKG, max_rounds=1,
                                reference_profile=profile)
    assert res.session.verdict == "improved"
    assert res.final_artifact["body"] == clean_same_len
    assert res.session.rounds[0]["rejected_as_gutting"] is False


def test_length_floor_disabled_without_profile():
    # The guard is market-anchored-only: without a profile the floor is 0, so the
    # legacy fixed path is byte-identical (a short clean rewrite is still accepted).
    art = _artifact(_DIRTY)
    res = improve_prose_hygiene(_Stub(_CLEAN), art, _PKG, max_rounds=1)
    # _CLEAN is far shorter than _DIRTY, but with no profile the floor is inert
    assert res.session.rounds[0]["length_floor"] == 0
    assert res.session.rounds[0]["rejected_as_gutting"] is False
