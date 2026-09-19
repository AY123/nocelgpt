from __future__ import annotations

from pathlib import Path

from runtime.chapter.finalizer import Finalizer
from runtime.chapter.intent import ChapterIntentBuilder
from runtime.chapter.orchestrator import ChapterProductionOrchestrator
from runtime.chapter.planner import BeatPlanner
from runtime.chapter.reviewer import ChapterReviewer
from runtime.chapter.reviser import RevisionEngine
from runtime.chapter.types import ChapterRevision, ChapterReview
from runtime.chapter.writer import DraftWriter
from runtime.candidates import plan as planmod
from runtime.serialize.loop import run_serial


def test_finalizer_accepts_comparison_report_and_splices_decision():
    finalizer = Finalizer()
    revision = ChapterRevision(chapter_id="TASK-00018", revision_round=1, before_text="甲", after_text="甲乙丙", changes=["tighten hook"])
    review = ChapterReview(
        chapter_id="TASK-00018",
        overall_verdict="pass",
        scores={"readability": 0.9, "commercial_pull": 0.8},
        issues=[],
        strengths=["hook improved"],
        revision_suggestions=[],
        gating_recommendation="advisory",
        publish_readiness="ready",
    )
    comparison_report = {
        "summary": {
            "headline": "改动率12.50%｜QA=pass｜商业钩子stronger",
            "recommendation": "accept",
            "editorial": {"notes": ["整体节奏更顺", "追读动机有增强"], "editorial_verdict": "accept"},
        },
        "risk_summary": {"risks": ["hook_strength_not_improved"], "recovery_actions": ["restore stronger chapter hook"]},
        "pipeline_decision": {"action": "advance"},
        "selection_metadata": {"selected_strategy": "hook_strengthening"},
    }
    final = finalizer.finalize(revision, review, comparison_report=comparison_report, project_path=None)
    assert final.comparison_report == comparison_report
    assert final.production_decision == comparison_report["pipeline_decision"]
    assert final.final_strategy == "hook_strengthening"
    assert final.final_status == "accepted"
    assert final.artifact_id == "TASK-00018"
    assert final.next_chapter_bridge.startswith("改动率12.50%")
    assert "hook_strength_not_improved" in final.continuity_notes
    assert "整体节奏更顺" in final.commercial_notes


def test_run_serial_writes_serial_checkpoints_at_10_20_30(tmp_path, monkeypatch):
    from runtime import registry_loader

    class _FakeReg:
        def __init__(self):
            self.version = "v1"
            self.facts = {}
        def get(self, _eid):
            return None

    specs = []
    for i in range(1, 31):
        specs.append(type("Spec", (), {"index": i, "task_id": f"TASK-{i:05d}", "event_id": f"EVT-{i:05d}", "seeds": ["CHR-00001"], "goal": f"g{i}"})())

    monkeypatch.setattr(registry_loader, "load", lambda _project_path: _FakeReg())
    monkeypatch.setattr("runtime.serialize.loop.plan_chapters", lambda _reg: specs)
    monkeypatch.setattr("runtime.pipeline.build_task_package", lambda **kwargs: type("B", (), {"ok": True, "package": {"provenance": {"derived_from": ["CHR-00001@v1"], "source_version": "v1"}}, "message": "ok", "stage": "ok"})())
    monkeypatch.setattr("runtime.serialize.loop.build_task_package", lambda **kwargs: type("B", (), {"ok": True, "package": {"provenance": {"derived_from": ["CHR-00001@v1"], "source_version": "v1"}}, "message": "ok", "stage": "ok"})())
    monkeypatch.setattr("runtime.serialize.loop.execute_package", lambda **kwargs: type("E", (), {
        "ok": True,
        "stage": "ok",
        "message": "ok",
        "artifact_path": "registry/derived/drafts/TASK-00001.json",
        "artifact": {
            "task_id": kwargs["package"]["provenance"]["derived_from"][0].split("@",1)[0],
            "content_hash": "hash-draft",
            "body": "真实章节正文",
            "provenance": {"derived_from": ["CHR-00001@v1"], "source_version": "v1"},
            "produced_by": {"llm": {"cost": {"total_cost": 0}, "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}},
        },
        "qa_review": {"scores": {}},
        "envelope": {"artifact": {"task_id": "TASK-00001"}},
    })())

    result = run_serial(
        project_path=tmp_path,
        standard_root=tmp_path,
        schema_dir=tmp_path,
        out_dir=tmp_path / "out",
        model=None,
        reviewer=None,
        prompt_version="1.0.0",
        max_chapters=30,
    )
    assert result.produced == 30
    for idx in (10, 20, 30):
        assert (tmp_path / "registry" / "derived" / "serial-checkpoints" / f"cp-{idx:03d}.json").exists()


def test_orchestrator_generates_multiversion_candidates_automatically():
    orchestrator = ChapterProductionOrchestrator(
        writer=DraftWriter(),
        reviewer=ChapterReviewer(),
        reviser=RevisionEngine(),
        finalizer=Finalizer(),
        beat_planner=BeatPlanner(),
    )
    final = orchestrator.produce(
        chapter_no=1,
        chapter_id="TASK-00018",
        goal="推进冲突并强化钩子",
        text="甲乙丙丁戊己庚辛壬癸 " * 40,
        commercial_target="高留存",
        hook_target="结尾反转",
    )
    assert final.comparison_report is not None
    assert final.comparison_report["kind"] == "version_comparison"
    assert final.artifact_id == "TASK-00018"
    # R1/R2 fix: the deterministic engine now yields only text-complete versions
    # (draft + whole-clause revision), not the 5 removed char-slicing pseudo-variants.
    versions = final.comparison_report["versions"]
    assert len(versions) >= 2
    assert {v["version_id"] for v in versions} <= {"draft", "revision"}
    assert orchestrator.last_comparison is not None
    assert final.production_decision is not None
    # the winning final_text must not contain an injected word-splitting 「？\n\n」
    import re
    assert not re.search(r"[一-鿿]？\n\n[一-鿿]", final.final_text)


def test_orchestrator_persists_final_when_project_path_is_provided(tmp_path):
    orchestrator = ChapterProductionOrchestrator(
        writer=DraftWriter(),
        reviewer=ChapterReviewer(),
        reviser=RevisionEngine(),
        finalizer=Finalizer(),
        beat_planner=BeatPlanner(),
    )
    final = orchestrator.produce(
        chapter_no=1,
        chapter_id="TASK-00021",
        goal="推进冲突并强化钩子",
        text="甲乙丙丁戊己庚辛壬癸 " * 40,
        commercial_target="高留存",
        hook_target="结尾反转",
        project_path=str(tmp_path),
    )
    assert final.artifact_id == "TASK-00021"
    # ChapterFinal persists under chapter-final/ (final-<id>), NOT drafts/ —
    # drafts/<id> is owned by the DraftWriter envelope; writing final there would
    # clobber the frozen draft (body/director/openings).
    payload = (tmp_path / "registry" / "derived" / "chapter-final" / "final-TASK-00021.json").read_text(encoding="utf-8")
    assert "TASK-00021" in payload
    assert "registry/derived/chapter-final/final-TASK-00021.json" in (tmp_path / "registry" / "derived" / "_index.yaml").read_text(encoding="utf-8")


def test_orchestrator_uses_supplied_candidate_versions_when_present():
    orchestrator = ChapterProductionOrchestrator(
        writer=DraftWriter(),
        reviewer=ChapterReviewer(),
        reviser=RevisionEngine(),
        finalizer=Finalizer(),
        beat_planner=BeatPlanner(),
    )
    final = orchestrator.produce(
        chapter_no=1,
        chapter_id="TASK-00018",
        goal="推进冲突并强化钩子",
        text="甲乙丙丁戊己庚辛壬癸 " * 40,
        commercial_target="高留存",
        hook_target="结尾反转",
        candidate_versions=[
            {
                "version_id": "draft",
                "text": "甲乙丙丁",
                "before_review": {"overall_verdict": "revise", "scores": {}},
                "after_review": {"overall_verdict": "revise", "scores": {"commercial_pull": 0.4}},
                "director_score": 0.4,
                "reason": "原始稿",
                "strategy": "baseline",
            },
            {
                "version_id": "refined",
                "before_text": "甲乙丙丁",
                "after_text": "甲乙丙丁戊己庚辛",
                "before_review": {"overall_verdict": "revise", "scores": {"commercial_pull": 0.4}},
                "after_review": {"overall_verdict": "pass", "scores": {"commercial_pull": 0.9}},
                "director_score": 0.9,
                "reason": "强化节奏与钩子",
                "strategy": "hook_strengthening",
            },
            {
                "version_id": "revision",
                "before_text": "甲乙丙丁戊己庚辛",
                "after_text": "甲乙丙丁戊己庚辛壬癸",
                "before_review": {"overall_verdict": "pass", "scores": {"commercial_pull": 0.9}},
                "after_review": {"overall_verdict": "pass", "scores": {"commercial_pull": 0.8}},
                "director_score": 0.8,
                "reason": "修订版",
                "strategy": "length_and_hook",
            },
        ],
    )
    assert final.comparison_report is not None
    assert final.comparison_report["winner"] == "refined"
    assert orchestrator.last_comparison is not None
    assert orchestrator.last_comparison["winner"] == "refined"


def test_reviser_does_not_pad_long_cjk_draft():
    """Regression: the short-draft floor once measured len(text.split()), which
    is ~1 for space-free Chinese prose, so EVERY non-pass Chinese draft was
    padded with '补充推进与情绪收束。'×20 — a 注水 defect. With CJK-aware counting a
    genuinely long body is above the 100-word floor and must be left untouched."""
    from runtime.chapter.types import ChapterDraft, ChapterReview

    body = "周洛铭睁开眼，天花板上那道裂缝还在。和昨天一样。和车祸后睁眼的第一天一模一样。" * 6
    draft = ChapterDraft(chapter_id="TASK-00018", version=1, text=body,
                         word_count=0, draft_hash="h")
    review = ChapterReview(chapter_id="TASK-00018", overall_verdict="revise",
                           scores={}, issues=["draft too short or empty"])
    revision = RevisionEngine().revise(draft, review)

    assert "补充推进与情绪收束" not in revision.after_text, "long CJK draft was wrongly padded"
    assert "expanded short draft" not in revision.changes


def test_finalizer_persists_chapter_final_as_derived_artifact(tmp_path):
    finalizer = Finalizer()
    revision = ChapterRevision(
        chapter_id="TASK-00019",
        revision_round=1,
        before_text="甲",
        after_text="甲乙丙",
        base_draft_hash="draft-hash-001",
        changes=["tighten hook"],
        revision_reason="improve pacing",
        revision_strategy="hook_strengthening",
    )
    review = ChapterReview(
        chapter_id="TASK-00019",
        overall_verdict="pass",
        scores={"readability": 0.9, "commercial_pull": 0.8},
        issues=[],
        strengths=["hook improved"],
        revision_suggestions=[],
        gating_recommendation="advisory",
        publish_readiness="ready",
    )
    comparison_report = {
        "summary": {"headline": "ok", "recommendation": "accept", "editorial": {"notes": []}},
        "risk_summary": {"risks": []},
        "pipeline_decision": {"action": "advance"},
        "selection_metadata": {"selected_strategy": "hook_strengthening"},
    }
    final = finalizer.finalize(revision, review, comparison_report=comparison_report, project_path=tmp_path)
    assert final.artifact_id == "TASK-00019"
    index = (tmp_path / "registry" / "derived" / "_index.yaml").read_text(encoding="utf-8")
    assert "TASK-00019" in index
    # persisted under chapter-final/ (final-<id>), never drafts/ (see finalizer note)
    payload = (tmp_path / "registry" / "derived" / "chapter-final" / "final-TASK-00019.json").read_text(encoding="utf-8")
    assert "甲乙丙" in payload
    assert "draft-hash-001" in payload


def test_w12_default_resolver_prefers_real_derived_draft(tmp_path, monkeypatch):
    derived_root = tmp_path / "registry" / "derived" / "drafts"
    derived_root.mkdir(parents=True)
    (derived_root / "TASK-00020.json").write_text(
        """{
  "artifact_id": "TASK-00020",
  "content_hash": "hash-20",
  "draft_artifact_id": "TASK-00020",
  "draft_artifact_path": "registry/derived/drafts/TASK-00020.json",
  "provenance": {"derived_from": ["CHR-00001@v1"], "source_version": null},
  "task_id": "TASK-00020",
  "body": "真实章节正文",
  "source_refs": ["CHR-00001@v1"]
}""",
        encoding="utf-8",
    )
    (tmp_path / "registry" / "derived" / "_index.yaml").write_text(
        """artifacts:\n  - id: TASK-00020\n    category: drafts\n    path: registry/derived/drafts/TASK-00020.json\n    content_hash: hash-20\n    derived_from:\n      - CHR-00001@v1\n    source_version: null\n""",
        encoding="utf-8",
    )
    monkeypatch.setattr(planmod, "load_registry", lambda _project_path: None)
    monkeypatch.setattr(planmod, "_default_known_entities", lambda _project_path: [])

    seen = {}

    class _FakeDeterministic(planmod.DeterministicExtractor):
        def extract(self, draft, known_entities=None, declared_fields=None):
            seen["task_id"] = draft["task_id"]
            seen["artifact_id"] = draft["artifact_id"]
            return []

    monkeypatch.setattr(planmod, "DeterministicExtractor", _FakeDeterministic)
    result = planmod.run_w12_fact_reflow(
        project_path=tmp_path,
        plan_id="W12-00020",
        model=None,
    )

    assert seen["task_id"] == "TASK-00020"
    assert seen["artifact_id"] == "TASK-00020"
    assert result["draft_source"] == "default-resolver"
    assert result["draft_id"] == "TASK-00020"


def test_orchestrator_final_separate_from_w12_draft_source(tmp_path, monkeypatch):
    # The orchestrator persists its ChapterFinal to chapter-final/ (final-<id>).
    # W12's default resolver reads the DRAFT envelope from drafts/ — a distinct
    # artifact. The two must NOT collide: previously the finalizer clobbered
    # drafts/<id> with the final, which had no body and broke w12. This test locks
    # the separation: final in chapter-final/, draft (with body) in drafts/, and
    # w12 reads the draft.
    import json as _json
    from runtime import derived as _derived

    orchestrator = ChapterProductionOrchestrator(
        writer=DraftWriter(),
        reviewer=ChapterReviewer(),
        reviser=RevisionEngine(),
        finalizer=Finalizer(),
        beat_planner=BeatPlanner(),
    )
    final = orchestrator.produce(
        chapter_no=1,
        chapter_id="TASK-00022",
        goal="推进冲突并强化钩子",
        text="甲乙丙丁戊己庚辛壬癸 " * 40,
        commercial_target="高留存",
        hook_target="结尾反转",
        project_path=str(tmp_path),
    )
    # final persisted separately, NOT in drafts/
    assert final.artifact_id == "TASK-00022"
    assert (tmp_path / "registry" / "derived" / "chapter-final" / "final-TASK-00022.json").exists()
    assert not (tmp_path / "registry" / "derived" / "drafts" / "TASK-00022.json").exists()

    # a real draft envelope (as execute_package would write) lives in drafts/
    draft_artifact = {
        "task_id": "TASK-00022",
        "content_hash": "hash-draft-22",
        "body": "真实章节正文",
        "provenance": {"derived_from": ["CHR-00001@v1"], "source_version": "v1"},
    }
    _derived.write_artifact(
        project_path=tmp_path, category="drafts", artifact_id="TASK-00022",
        artifact=draft_artifact, serialized=_json.dumps(draft_artifact, ensure_ascii=False, indent=2))

    monkeypatch.setattr(planmod, "load_registry", lambda _project_path: None)
    monkeypatch.setattr(planmod, "_default_known_entities", lambda _project_path: [])

    seen = {}

    class _FakeDeterministic(planmod.DeterministicExtractor):
        def extract(self, draft, known_entities=None, declared_fields=None):
            seen["task_id"] = draft["task_id"]
            seen["body"] = draft.get("body")
            return []

    monkeypatch.setattr(planmod, "DeterministicExtractor", _FakeDeterministic)
    result = planmod.run_w12_fact_reflow(
        project_path=tmp_path,
        plan_id="W12-00022",
        model=None,
    )

    # w12 read the DRAFT (with body), not the final
    assert seen["task_id"] == "TASK-00022"
    assert seen["body"] == "真实章节正文"
    assert result["draft_id"] == "TASK-00022"
    assert result["draft_source"] == "default-resolver"


def test_run_serial_persists_chapter_final_and_w12_can_read_it(tmp_path, monkeypatch):
    from runtime import registry_loader

    class _FakeReg:
        def __init__(self):
            self.version = "v1"
            self.facts = {}
        def get(self, _eid):
            return None

    monkeypatch.setattr(registry_loader, "load", lambda _project_path: _FakeReg())
    monkeypatch.setattr("runtime.serialize.loop.plan_chapters", lambda _reg: [type("Spec", (), {"index": 1, "task_id": "TASK-00001", "event_id": "EVT-00001", "seeds": ["CHR-00001"], "goal": "g"})()])
    monkeypatch.setattr("runtime.serialize.loop.compiler.TaskDefinition", lambda *a, **k: type("TD", (), {"task_id": "TASK-00001", "goal": "g", "capability": "ChapterDraft", "seeds": ["CHR-00001"]})())
    monkeypatch.setattr("runtime.pipeline.build_task_package", lambda **kwargs: type("B", (), {"ok": True, "package": {"provenance": {"derived_from": ["CHR-00001@v1"], "source_version": "v1"}}, "message": "ok", "stage": "ok"})())
    monkeypatch.setattr("runtime.serialize.loop.build_task_package", lambda **kwargs: type("B", (), {"ok": True, "package": {"provenance": {"derived_from": ["CHR-00001@v1"], "source_version": "v1"}}, "message": "ok", "stage": "ok"})())

    # Fake execute_package that PERSISTS the draft envelope to drafts/ like the
    # real one (run.py writes category="drafts", id=task_id). The prior version of
    # this test skipped the write and relied on the finalizer clobbering drafts/
    # with a ChapterFinal — the very bug being fixed. Now the draft (with body)
    # lives in drafts/, and the ChapterFinal lives separately in chapter-final/.
    import json as _json
    from runtime import derived as _derived

    def _fake_execute(**kwargs):
        artifact = {
            "task_id": "TASK-00001",
            "content_hash": "hash-draft",
            "body": "真实章节正文",
            "provenance": {"derived_from": ["CHR-00001@v1"], "source_version": "v1"},
            "produced_by": {"llm": {"cost": {"total_cost": 0}, "token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}},
        }
        rel = _derived.write_artifact(
            project_path=tmp_path, category="drafts", artifact_id="TASK-00001",
            artifact=artifact, serialized=_json.dumps(artifact, ensure_ascii=False, indent=2))
        return type("E", (), {
            "ok": True, "stage": "ok", "message": "ok",
            "artifact_path": rel, "artifact": artifact,
            "qa_review": {"scores": {}}, "envelope": {"artifact": artifact},
        })()

    monkeypatch.setattr("runtime.serialize.loop.execute_package", _fake_execute)

    result = run_serial(
        project_path=tmp_path,
        standard_root=tmp_path,
        schema_dir=tmp_path,
        out_dir=tmp_path / "out",
        model=None,
        reviewer=None,
        prompt_version="1.0.0",
        max_chapters=1,
    )
    assert result.produced == 1
    # the DRAFT envelope (with body) is in drafts/ — written by execute_package
    assert (tmp_path / "registry" / "derived" / "drafts" / "TASK-00001.json").exists()
    # the ChapterFinal is a SEPARATE artifact under chapter-final/, not clobbering the draft
    assert (tmp_path / "registry" / "derived" / "chapter-final" / "final-TASK-00001.json").exists()
    assert (tmp_path / "registry" / "derived" / "_index.yaml").read_text(encoding="utf-8").find("TASK-00001") >= 0

    monkeypatch.setattr(planmod, "load_registry", lambda _project_path: None)
    monkeypatch.setattr(planmod, "_default_known_entities", lambda _project_path: [])

    seen = {}
    class _FakeDeterministic(planmod.DeterministicExtractor):
        def extract(self, draft, known_entities=None, declared_fields=None):
            seen["task_id"] = draft["task_id"]
            return []
    monkeypatch.setattr(planmod, "DeterministicExtractor", _FakeDeterministic)
    w12 = planmod.run_w12_fact_reflow(project_path=tmp_path, plan_id="W12-00001", model=None)
    assert w12["draft_id"] == "TASK-00001"
    assert seen["task_id"] == "TASK-00001"


def test_revision_engine_produces_only_text_complete_candidates():
    """R1/R2 fix: generate_candidates must never emit a body that splits a word.

    The removed char-slicing variants (hooked/conflict/relationship/worldbuilding/
    compact) cut the body at a fixed CHARACTER offset and spliced in「？\\n\\n」,
    劈断了词语 (车|祸, 缠|绕) — a defect that shipped in chapter-final.final_text.
    The deterministic engine now offers only text-complete versions (draft +
    whole-clause revision); genuine alternatives come from the C6 real-LLM path.
    """
    engine = RevisionEngine()
    body = "周洛铭睁开眼，天花板上那道裂缝还在。和昨天一样。和车祸后睁眼的第一天一模一样。" * 6
    draft = DraftWriter().write(
        ChapterIntentBuilder(chapter_no=1, chapter_id="TASK-00018", goal="推进冲突").build(),
        BeatPlanner().plan(ChapterIntentBuilder(chapter_no=1, chapter_id="TASK-00018", goal="推进冲突").build()),
        text=body,
    )
    review = ChapterReviewer().review(draft)
    candidates = engine.generate_candidates(draft, review)

    # only clean, text-complete strategies survive — no char-slicing pseudo-variants
    assert all("strategy" in c for c in candidates)
    version_ids = {c["version_id"] for c in candidates}
    assert version_ids <= {"draft", "revision"}, f"unexpected variant: {version_ids}"
    for fake in ("hooked", "conflict", "relationship", "worldbuilding", "compact"):
        assert fake not in version_ids, f"char-slicing variant {fake!r} must be gone"

    # the draft candidate must reproduce the body verbatim (no mangling)
    draft_cand = next(c for c in candidates if c["version_id"] == "draft")
    assert draft_cand["text"] == body

    # no candidate splits a word with an injected 「？\n\n」 (the shipped defect)
    import re
    for c in candidates:
        assert not re.search(r"[一-鿿]？\n\n[一-鿿]", c["text"]), \
            f"candidate {c['version_id']} splits a word with injected ？\\n\\n"
