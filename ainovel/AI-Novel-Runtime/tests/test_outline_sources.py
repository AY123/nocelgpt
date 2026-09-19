import json
from pathlib import Path

from runtime.catalog import Catalog
from runtime.outline.sources import load_reference_sources
from runtime.outline.workflow import run_outline_bootstrap
from runtime.outline.qa import check_outline, review_outline
from runtime.validator import SchemaSet
from jsonschema import Draft202012Validator


def make_project(tmp_path: Path) -> Path:
    project = tmp_path / "novel"
    (project / "sources" / "reference-novels").mkdir(parents=True)
    (project / "registry" / "_meta").mkdir(parents=True)
    (project / "registry" / "_meta" / "project-id").write_text("novel\n", encoding="utf-8")
    return project


def schema_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "AI-Novel-Standard" / "phase-1" / "generated" / "json-schema"


def test_sources_requires_at_least_one_reference(tmp_path):
    project = make_project(tmp_path)

    result = load_reference_sources(project)

    assert not result.ok
    assert "at least 1 reference novel is required" in result.errors


def test_sources_accepts_one_to_five_references(tmp_path):
    project = make_project(tmp_path)
    for index in range(5):
        (project / "sources" / "reference-novels" / f"novel-{index}.txt").write_text(
            f"正文 {index}", encoding="utf-8"
        )

    result = load_reference_sources(project)

    assert result.ok
    assert [source.id for source in result.sources] == [
        "REF-00001",
        "REF-00002",
        "REF-00003",
        "REF-00004",
        "REF-00005",
    ]


def test_sources_rejects_more_than_five_references(tmp_path):
    project = make_project(tmp_path)
    for index in range(6):
        (project / "sources" / "reference-novels" / f"novel-{index}.txt").write_text(
            f"正文 {index}", encoding="utf-8"
        )

    result = load_reference_sources(project)

    assert not result.ok
    assert "at most 5 reference novels are allowed" in result.errors


def test_sources_rejects_unsupported_formats(tmp_path):
    project = make_project(tmp_path)
    (project / "sources" / "reference-novels" / "novel.txt").write_text("正文", encoding="utf-8")
    (project / "sources" / "reference-novels" / "novel.epub").write_text("binary", encoding="utf-8")

    result = load_reference_sources(project)

    assert not result.ok
    assert any("unsupported reference novel format" in error for error in result.errors)


def test_outline_bootstrap_writes_analysis_run_and_derived_outline(tmp_path):
    project = make_project(tmp_path)
    (project / "sources" / "reference-novels" / "novel.txt").write_text(
        "少年在废城遭遇灵气危机，觉醒传承后逃离宗门追杀。"
        "他发现秘密线索，突破境界并赢得第一次胜利。",
        encoding="utf-8",
    )

    result = run_outline_bootstrap(project, run_id="test-run")

    assert result.ok
    assert result.run_dir == "workspace/outline-bootstrap/runs/test-run"
    assert result.outline_json == "registry/derived/outline/OUTLINE-00001.json"
    assert (project / result.run_dir / "sources.snapshot.json").exists()
    assert (project / result.run_dir / "analysis" / "references.json").exists()
    assert (project / result.run_dir / "analysis" / "merged.json").exists()
    assert (project / result.run_dir / "candidates.json").exists()
    assert (project / result.run_dir / "reviews.json").exists()
    assert (project / result.run_dir / "final-outline.json").exists()
    assert result.import_plan_json == "workspace/outline-bootstrap/runs/test-run/import-plan.json"
    assert (project / result.import_plan_json).exists()
    assert (project / result.outline_json).exists()
    assert (project / result.outline_markdown).exists()

    outline = json.loads((project / result.outline_json).read_text(encoding="utf-8"))
    import_plan = json.loads((project / result.import_plan_json).read_text(encoding="utf-8"))
    merged = json.loads(
        (project / result.run_dir / "analysis" / "merged.json").read_text(encoding="utf-8")
    )
    assert outline["kind"] == "novel_outline"
    assert outline["title"] != "待定标题"
    assert outline["provenance"]["project_id"] == "novel"
    # The outline pins the synthesis-time analysis snapshot. The run-level
    # merged artifact is enriched later with sibling ledgers; those must not
    # mutate an already synthesized (and potentially reviewed) outline.
    analysis_snapshot = outline["provenance"]["analysis_summary"]
    assert all(analysis_snapshot[key] == merged[key] for key in analysis_snapshot)
    assert "chapter_evidence_ledger" not in analysis_snapshot
    assert "chapter_evidence_ledger" in merged
    assert outline["collaboration"]["selected_candidate"].startswith("CANDIDATE-")
    assert outline["originality_report"]["risk_level"] in {"low", "medium"}
    assert "玄幻" in merged["genre_signals"]
    assert import_plan["kind"] == "outline_import_plan"
    assert import_plan["policy"]["writes_registry_facts"] is False
    assert import_plan["review_status"] == "needs_human_review"
    assert {item["target_type"] for item in import_plan["items"]} >= {
        "Timeline",
        "Event",
        "Character",
        "WorldRule",
    }
    assert all(item["review_status"] == "needs_human_review" for item in import_plan["items"])
    assert not any((project / "registry" / "facts").rglob("*90001.yaml"))

    schemas = SchemaSet(schema_dir(), catalog=Catalog.load(schema_dir()))
    for item in import_plan["items"]:
        type_code = item["candidate_id"].split("-", 1)[0]
        errors = list(schemas.validator_for(type_code).iter_errors(item["record"]))
        assert errors == []


def outline_contract_schema() -> dict:
    path = (
        Path(__file__).resolve().parents[2]
        / "AI-Novel-Standard" / "contracts" / "outline.schema.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_genesis_preference_floats_target_genre_to_primary(tmp_path):
    # Western-flavoured 玄幻 references score 奇幻 above 玄幻; the human target
    # preference must steer primary genre back to 玄幻 (charter: references +
    # a little human preference). Reordering genre_signals flips the outline's
    # market_position.sub_genre without touching the frequency detector.
    from runtime.outline.sources import load_genesis_preference

    project = make_project(tmp_path)
    # a body whose 奇幻 hints (龙/魔法/王国/骑士) outscore its 玄幻 ones
    (project / "sources" / "reference-novels" / "novel.txt").write_text(
        "骑士在王国里与巨龙对峙，魔法与诅咒交织；他也修炼灵气、冲击境界。",
        encoding="utf-8")
    # baseline: no preference => frequency detector picks 奇幻 first
    base = run_outline_bootstrap(project, run_id="pref-base")
    base_outline = json.loads((project / base.outline_json).read_text(encoding="utf-8"))
    assert base_outline["genre"][0] == "奇幻"

    # with a human target preference => 玄幻 floats to the front
    (project / "sources" / "genesis-preference.yaml").write_text(
        "target_genre: 玄幻\n", encoding="utf-8")
    assert load_genesis_preference(project)["target_genre"] == "玄幻"
    steered = run_outline_bootstrap(project, run_id="pref-steered")
    steered_outline = json.loads((project / steered.outline_json).read_text(encoding="utf-8"))
    assert steered_outline["genre"][0] == "玄幻"
    assert steered_outline["market_position"]["sub_genre"] == "玄幻"
    assert steered_outline["market_position"]["channel"] == "男频"


def test_genesis_preference_absent_is_backward_compatible(tmp_path):
    # No preference file => load returns {} and the pipeline is unchanged.
    from runtime.outline.sources import load_genesis_preference
    project = make_project(tmp_path)
    assert load_genesis_preference(project) == {}


def test_target_genre_biases_live_candidate_selection():
    # LIVE-PATH fix: the final genre comes from the CHOSEN candidate's own genre,
    # so a genesis book opened as 都市 despite target_genre=玄幻 — the genre_signals
    # steer only shaped the fallback template. synthesize must prefer a candidate
    # MATCHING target_genre even when an off-genre candidate scored higher.
    from runtime.outline.agents import synthesize_final_outline

    candidates = [
        {"id": "CANDIDATE-A", "title": "逆命倒计时", "genre": ["都市", "悬疑"],
         "logline": "快递员看见死亡倒计时", "protagonist_engine": {}, "power_system": {}},
        {"id": "CANDIDATE-B", "title": "曜灭纪元", "genre": ["奇幻", "玄幻"],
         "logline": "矿工融合晶核", "protagonist_engine": {}, "power_system": {}},
    ]
    # A scores HIGHER than B — without the target bias, A (都市) would win.
    reviews = [
        {"candidate_id": "CANDIDATE-A", "score": 9, "risk_level": "low", "guardrails": []},
        {"candidate_id": "CANDIDATE-B", "score": 7, "risk_level": "low", "guardrails": []},
    ]

    # no target => pure score => A wins (byte-identical to before)
    o_no_target = synthesize_final_outline(candidates, reviews, {}, "p", [])
    assert o_no_target["title"] == "逆命倒计时"

    # target 玄幻 => B wins despite lower score (target match outranks score)
    o_target = synthesize_final_outline(
        candidates, reviews, {"target_genre": "玄幻"}, "p", [])
    assert o_target["title"] == "曜灭纪元"
    # target floats to PRIMARY (position 0), not just present in the list —
    # the LLM had listed ["奇幻","玄幻"] so primary would read 奇幻 otherwise.
    assert o_target["genre"][0] == "玄幻"
    assert "奇幻" in o_target["genre"]      # nothing dropped, only reordered


def test_final_outline_carries_commercial_skeleton_dsl(tmp_path):
    project = make_project(tmp_path)
    (project / "sources" / "reference-novels" / "novel.txt").write_text(
        "少年在废城遭遇灵气危机，觉醒传承后逃离宗门追杀。"
        "他发现秘密线索，突破境界并赢得第一次胜利。",
        encoding="utf-8",
    )

    result = run_outline_bootstrap(project, run_id="dsl-run")
    assert result.ok

    outline = json.loads((project / result.outline_json).read_text(encoding="utf-8"))

    # Commercial engine with a sustainable golden finger (must carry a cost).
    assert outline["protagonist_engine"]["golden_finger"]
    assert outline["protagonist_engine"]["cost"]
    # Power system backs an escalating conflict ladder.
    assert outline["power_system"]["tiers"]
    assert len(outline["conflict_ladder"]) >= 2
    # Reward loop is a short, concrete cadence.
    assert outline["reward_loop"]["cadence_chapters"] >= 1
    # First-30-chapter retention model with per-chapter end hooks.
    assert len(outline["first_30_chapters"]) == 30
    assert all(ch["end_hook"] for ch in outline["first_30_chapters"][:3])
    # Every volume carries escalation scaffolding.
    for vol in outline["plot"]["volumes"]:
        assert vol["oppressor"]
        assert vol["twist"]
    # Market position drives downstream constraints.
    assert outline["market_position"]["channel"] in {"男频", "女频"}
    assert outline["market_position"]["reader_promise"]
    # Originality differences are recorded as a delta matrix, not just prose.
    assert outline["originality_delta"]


def test_enriched_beats_are_concrete_and_urgent(tmp_path):
    """9.6 follow-up: the beat generator must weave the authored conflict ladder +
    engine into per-chapter beats — concrete enemies, time pressure, varied
    escalation — so the mandate layer folds richer mandates (温水章 count drops)."""
    from runtime.director import project_narrative_mandate, check_mandate_chapter

    project = make_project(tmp_path)
    (project / "sources" / "reference-novels" / "novel.txt").write_text(
        "少年觉醒金手指，逃离追杀，突破境界赢得胜利。", encoding="utf-8")
    result = run_outline_bootstrap(project, run_id="beat-run")
    assert result.ok
    outline = json.loads((project / result.outline_json).read_text(encoding="utf-8"))
    beats = outline["first_30_chapters"]

    # (a) no generic placeholder conflict — every beat names a concrete pressure.
    assert not any(b["conflict"] == "本章的具体冲突：主角目标与压迫源的直接碰撞"
                   for b in beats)
    # (b) escalation shape VARIES across the 30 chapters (not a uniform '升级').
    assert len({b["escalation"] for b in beats}) >= 3
    # (c) the enriched beats fold into mandates with almost no 温水章 (was 10/12
    #     on the old generic beats). Check the first 12.
    prev = None
    lukewarm = 0
    for n in range(1, 13):
        m = project_narrative_mandate(chapter_no=n, task_id=f"TASK-{n:05d}",
                                      outline=outline, prev_mandate=prev)
        r = check_mandate_chapter(m).to_dict()
        if r["findings"][0]["severity"] == "warning":
            lukewarm += 1
        prev = m
    assert lukewarm <= 2, f"expected enriched beats to shed 温水章, got {lukewarm}/12"


def test_live_authored_tier_gloss_stripped_from_skeleton_labels():
    # A live-authored power tier often carries an inline gloss
    # ("醒瞳——能捕捉灵骸残留的情绪波动"); the skeleton builders bind tier NAMES into
    # enemy/oppressor/goal labels, so the gloss must be stripped or every label
    # reads "醒瞳——能捕捉…阶段的小敌人". power_system keeps the full gloss.
    from runtime.outline.agents import _tier_name, _build_conflict_ladder

    assert _tier_name("醒瞳——能捕捉灵骸残留的情绪波动") == "醒瞳"
    assert _tier_name("共鸣：残响能量") == "共鸣"
    assert _tier_name("淬体") == "淬体"          # bare template tier unchanged

    glossed = ["醒瞳——能捕捉灵骸残留的情绪波动", "溯影——可看到死亡前七秒片段",
               "共鸣：残响能量", "织魂", "司命——切割寿命"]
    ladder = _build_conflict_ladder([_tier_name(t) for t in glossed])
    for rung in ladder:
        assert "——" not in rung["enemy"] and "：" not in rung["enemy"]


def test_first_30_chapter_goals_are_de_templated(tmp_path):
    # N100-076: non-pivot chapter goals used to be one repeated line
    # ("逼近「{desire}」的下一步，直面{enemy}") so consecutive chapters read
    # byte-identical (live preview: 11/30 unique). The woven goal must vary by
    # structural position — high uniqueness, no consecutive verbatim repeats.
    from runtime.outline.agents import _build_first_30_chapters

    engine = {"golden_finger": "灵骸感应",
              "desire": "破解自身与同面容灵骸的关联",
              "flaw": "不敢面对死亡真相", "cost": "每用一次寿命缩短七天"}
    reward_loop = {"cadence_chapters": 3, "reward_types": ["实力跃升", "真相碎片", "盟友加入"]}
    ladder = [{"enemy": "醒瞳", "pressure_source": "记忆反噬"},
              {"enemy": "灵骸司叛徒", "pressure_source": "追杀"},
              {"enemy": "同面灵骸", "pressure_source": "身份湮灭"}]
    chapters = _build_first_30_chapters(engine, reward_loop, ladder)
    goals = [c["goal"] for c in chapters]

    # high uniqueness (was 11/30 on the flat template)
    assert len(set(goals)) >= 25, f"goals not varied enough: {len(set(goals))}/30"
    # no two consecutive chapters share a byte-identical goal
    assert all(goals[i] != goals[i - 1] for i in range(1, len(goals)))
    # deterministic: same inputs => same goals
    again = [c["goal"] for c in _build_first_30_chapters(engine, reward_loop, ladder)]
    assert goals == again


def test_final_outline_validates_against_contract(tmp_path):
    project = make_project(tmp_path)
    (project / "sources" / "reference-novels" / "novel.txt").write_text(
        "少年觉醒金手指，逃离追杀，突破境界赢得胜利。", encoding="utf-8"
    )
    result = run_outline_bootstrap(project, run_id="contract-run")
    assert result.ok

    outline = json.loads((project / result.outline_json).read_text(encoding="utf-8"))
    schema = outline_contract_schema()
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(outline))
    assert errors == [], [e.message for e in errors]


def test_outline_qa_gate_blocks_incomplete_skeleton():
    # A skeleton missing the commercial engine and hooks must fail the
    # deterministic gate (ADR-003) — this is what keeps the hardcoded-template
    # failure mode from reaching a final outline.
    incomplete = {
        "protagonist_engine": {"golden_finger": "", "cost": ""},
        "power_system": {"tiers": []},
        "conflict_ladder": [],
        "reward_loop": {},
        "first_30_chapters": [],
        "plot": {"volumes": [{"id": "VOL-01"}]},
    }
    findings = check_outline(incomplete)
    checks = {f.check for f in findings}
    assert "protagonist-engine" in checks
    assert "golden-finger-cost" in checks
    assert "conflict-ladder" in checks
    assert "opening-hooks" in checks


def test_outline_evaluative_review_never_gates():
    report = review_outline({"first_30_chapters": [], "reward_loop": {}})
    # Structural invariants: evaluative axis, advisory, never gates.
    assert report.axis == "evaluative"
    assert report.gating is False


def test_outline_run_writes_evaluative_review(tmp_path):
    project = make_project(tmp_path)
    (project / "sources" / "reference-novels" / "novel.txt").write_text(
        "少年觉醒金手指，逃离追杀，突破境界赢得胜利。", encoding="utf-8"
    )
    result = run_outline_bootstrap(project, run_id="review-run")
    assert result.ok
    review_path = project / result.run_dir / "outline-review.json"
    assert review_path.exists()
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["axis"] == "evaluative"
    assert review["gating"] is False


# --------------------------------------------------------------------------- #
# Aliases baked into the flow (fix for the cross-language extraction gap): an   #
# authored alias must ride from outline → candidate fact → the reconciler's     #
# name index, so a prose reference in a different rendering than the setting     #
# name resolves back to the entity instead of a phantom `new`.                   #
# --------------------------------------------------------------------------- #
from runtime.outline.import_plan import build_import_plan
from runtime.outline.writer import outline_markdown


def _char_records(plan: dict) -> list:
    return [it["record"] for it in plan["items"] if it["target_type"] == "Character"]


def test_import_plan_carries_authored_aliases():
    outline = {"id": "OUTLINE-1", "characters": [
        {"role": "protagonist", "name": "Edric Vance",
         "aliases": ["埃德里克·万斯", "埃德里克"]}]}
    rec = _char_records(build_import_plan(outline))[0]
    assert rec["name"] == "Edric Vance"
    assert rec["aliases"] == ["埃德里克·万斯", "埃德里克"]


def test_import_plan_cleans_alias_noise():
    outline = {"id": "O", "characters": [
        {"role": "protagonist", "name": "X",
         "aliases": ["  阿福  ", "", None, 42, "小福"]}]}
    rec = _char_records(build_import_plan(outline))[0]
    assert rec["aliases"] == ["阿福", "小福"]   # trimmed, blanks/non-strings dropped


def test_import_plan_without_aliases_is_backward_compatible():
    outline = {"id": "O", "characters": [{"role": "supporting", "name": "Maren"}]}
    rec = _char_records(build_import_plan(outline))[0]
    assert rec["aliases"] == []                  # empty, not an error


def test_candidate_record_with_aliases_passes_character_schema():
    validator = Draft202012Validator(json.loads(
        (schema_dir() / "Character.schema.json").read_text(encoding="utf-8")))
    outline = {"id": "O", "characters": [
        {"role": "protagonist", "name": "Edric Vance", "aliases": ["埃德里克·万斯"]}]}
    rec = _char_records(build_import_plan(outline))[0]
    assert list(validator.iter_errors(rec)) == []


def test_outline_schema_accepts_character_with_and_without_aliases():
    validator = Draft202012Validator(outline_contract_schema())
    base = {"id": "OUTLINE-00001", "kind": "novel_outline", "title": "t", "genre": [],
            "logline": "l", "themes": [], "world": {"summary": "", "rules": []},
            "plot": {"main_arc": "", "volumes": [], "chapters": []},
            "collaboration": {"selected_candidate": "cand-1"},
            "originality_report": {"risk_level": "unknown", "notes": []},
            "provenance": {"project_id": "p", "reference_sources": []}}
    with_alias = {**base, "characters": [
        {"role": "protagonist", "name": "Edric", "aliases": ["埃德里克"]}]}
    without = {**base, "characters": [{"role": "supporting", "name": "Maren"}]}
    assert list(validator.iter_errors(with_alias)) == []
    assert list(validator.iter_errors(without)) == []


def test_outline_markdown_shows_aliases():
    md = outline_markdown({"characters": [
        {"role": "主角", "name": "Edric", "aliases": ["埃德里克"], "arc": "流亡"}]})
    assert "（别名：埃德里克）" in md
    # a character without aliases renders without the parenthetical
    md2 = outline_markdown({"characters": [{"role": "配角", "name": "Maren", "arc": "收留"}]})
    assert "别名" not in md2


def test_authored_alias_resolves_prose_reference_end_to_end():
    """The closed loop: an alias authored in the outline rides into the candidate
    fact, and (via the same name index the reconciler builds) a Chinese prose
    reference resolves back to the entity — the manual pilot patch, now automatic.
    Deterministic; no live model."""
    from runtime.candidates.reconcile import (_build_name_index, _resolve_subject,
                                              RawCandidate)

    rec = _char_records(build_import_plan({"id": "O", "characters": [
        {"role": "protagonist", "name": "Edric Vance", "aliases": ["埃德里克·万斯"]}]}))[0]

    class _Reg:  # minimal registry over the single candidate record
        facts = {rec["id"]: rec}
        def all_ids(self): return list(self.facts)
        def get(self, i): return self.facts.get(i)
        def exists(self, i): return i in self.facts

    reg = _Reg()
    index = _build_name_index(reg)
    # prose used the Chinese alias with a blank id — must resolve to the entity
    cand = RawCandidate("Character", "abilities", ["剑术"], "prose",
                        matched_entity_id="埃德里克·万斯", confidence=0.9)
    matched_id, _entity = _resolve_subject(reg, index, cand)
    assert matched_id == rec["id"]      # resolved by authored alias, not phantom new
