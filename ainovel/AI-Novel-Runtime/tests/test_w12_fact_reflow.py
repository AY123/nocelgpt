from __future__ import annotations

from runtime.candidates import plan as planmod


def test_w12_fact_reflow_uses_deterministic_extractor_when_no_model(tmp_path, monkeypatch):
    monkeypatch.setattr(planmod, "_default_draft", lambda _project_path: {
        "task_id": "TASK-00099",
        "content_hash": "sha256:demo",
        "body": "demo body",
        "provenance": {"derived_from": ["CHR-00001@v1"]},
    })
    monkeypatch.setattr(planmod, "_default_known_entities", lambda _project_path: [
        {"id": "CHR-00001", "type": "CHR", "name": "Edric", "aliases": []}
    ])
    monkeypatch.setattr(planmod, "load_registry", lambda _project_path: None)

    captured = {}

    class _FakeDeterministic(planmod.DeterministicExtractor):
        def extract(self, draft, known_entities=None, declared_fields=None):
            captured["draft"] = draft
            captured["known_entities"] = known_entities
            return []

    monkeypatch.setattr(planmod, "DeterministicExtractor", _FakeDeterministic)

    result = planmod.run_w12_fact_reflow(
        project_path=tmp_path,
        plan_id="W12-00001",
        model=None,
    )

    assert result["plan"]["id"] == "W12-00001"
    # draft_source rides the return dict (envelope sibling), NOT plan.source —
    # fact-candidate-plan.schema.json declares source as additionalProperties:false.
    assert result["draft_source"] == "default-resolver"
    assert "draft_source" not in result["plan"]["source"]
    assert captured["draft"]["task_id"] == "TASK-00099"
    assert captured["known_entities"][0]["name"] == "Edric"
    assert result["approval_status"] == "pending"
    assert result["review_findings"]


def test_w12_fact_reflow_records_approval_when_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(planmod, "_default_draft", lambda _project_path: {
        "task_id": "TASK-00100",
        "content_hash": "sha256:demo2",
        "body": "demo body",
        "provenance": {"derived_from": ["CHR-00001@v1"]},
    })
    monkeypatch.setattr(planmod, "_default_known_entities", lambda _project_path: [
        {"id": "CHR-00001", "type": "CHR", "name": "Edric", "aliases": []}
    ])
    monkeypatch.setattr(planmod, "load_registry", lambda _project_path: None)

    class _FakeDeterministic(planmod.DeterministicExtractor):
        def extract(self, draft, known_entities=None, declared_fields=None):
            return []

    monkeypatch.setattr(planmod, "DeterministicExtractor", _FakeDeterministic)

    result = planmod.run_w12_fact_reflow(
        project_path=tmp_path,
        plan_id="W12-00002",
        model=None,
        accepted=["CAND-00001"],
    )

    assert result["approval_status"] == "approved"
    assert result["accepted_candidates"] == ["CAND-00001"]


def test_w12_fact_reflow_uses_explicit_chapter_draft_id_when_provided(tmp_path, monkeypatch):
    loaded = {}

    def fake_load_draft_from_index(project_path, draft_id):
        loaded["project_path"] = project_path
        loaded["draft_id"] = draft_id
        return {
            "task_id": draft_id,
            "content_hash": "sha256:loaded",
            "body": "loaded body",
            "provenance": {"derived_from": ["CHR-00002@v1"]},
        }

    monkeypatch.setattr(planmod, "_load_draft_from_index", fake_load_draft_from_index)
    monkeypatch.setattr(planmod, "_default_draft", lambda _project_path: {
        "task_id": "TASK-DEFAULT",
        "draft_artifact_id": "TASK-DEFAULT",
        "draft_artifact_path": "registry/derived/drafts/TASK-DEFAULT.json",
        "content_hash": "sha256:default",
        "body": "default body",
        "provenance": {"derived_from": ["CHR-00001@v1"]},
    })
    monkeypatch.setattr(planmod, "_default_known_entities", lambda _project_path: [])
    monkeypatch.setattr(planmod, "load_registry", lambda _project_path: None)

    class _FakeDeterministic(planmod.DeterministicExtractor):
        def extract(self, draft, known_entities=None, declared_fields=None):
            assert draft["task_id"] == "TASK-EXP-001"
            return []

    monkeypatch.setattr(planmod, "DeterministicExtractor", _FakeDeterministic)

    result = planmod.run_w12_fact_reflow(
        project_path=tmp_path,
        plan_id="W12-00003",
        chapter_draft_id="TASK-EXP-001",
        model=None,
    )

    assert loaded["draft_id"] == "TASK-EXP-001"
    assert result["draft_id"] == "TASK-EXP-001"
    assert result["draft_source"] == "derived-index:TASK-EXP-001"
    assert "draft_source" not in result["plan"]["source"]
    assert result["plan"]["source"]["chapter_draft_id"] == "TASK-EXP-001"


def test_w12_fact_reflow_raises_when_explicit_chapter_draft_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(planmod, "_load_draft_from_index", lambda _project_path, _draft_id: {})
    monkeypatch.setattr(planmod, "_default_draft", lambda _project_path: {
        "task_id": "TASK-DEFAULT",
        "draft_artifact_id": "TASK-DEFAULT",
        "draft_artifact_path": "registry/derived/drafts/TASK-DEFAULT.json",
        "content_hash": "sha256:default",
        "body": "default body",
        "provenance": {"derived_from": ["CHR-00001@v1"]},
    })
    monkeypatch.setattr(planmod, "_default_known_entities", lambda _project_path: [])
    monkeypatch.setattr(planmod, "load_registry", lambda _project_path: None)

    try:
        planmod.run_w12_fact_reflow(
            project_path=tmp_path,
            plan_id="W12-00004",
            chapter_draft_id="TASK-MISSING",
            model=None,
        )
    except FileNotFoundError as exc:
        assert "TASK-MISSING" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_w12_fact_reflow_uses_direct_draft_over_chapter_id(tmp_path, monkeypatch):
    monkeypatch.setattr(planmod, "_load_draft_from_index", lambda _project_path, _draft_id: {
        "task_id": "TASK-INDEX",
        "content_hash": "sha256:index",
        "body": "index body",
        "provenance": {"derived_from": ["CHR-00009@v1"]},
    })
    monkeypatch.setattr(planmod, "_default_draft", lambda _project_path: {
        "task_id": "TASK-DEFAULT",
        "draft_artifact_id": "TASK-DEFAULT",
        "draft_artifact_path": "registry/derived/drafts/TASK-DEFAULT.json",
        "content_hash": "sha256:default",
        "body": "default body",
        "provenance": {"derived_from": ["CHR-00001@v1"]},
    })
    monkeypatch.setattr(planmod, "_default_known_entities", lambda _project_path: [])
    monkeypatch.setattr(planmod, "load_registry", lambda _project_path: None)

    seen = {}

    class _FakeDeterministic(planmod.DeterministicExtractor):
        def extract(self, draft, known_entities=None, declared_fields=None):
            seen["task_id"] = draft["task_id"]
            return []

    monkeypatch.setattr(planmod, "DeterministicExtractor", _FakeDeterministic)

    result = planmod.run_w12_fact_reflow(
        project_path=tmp_path,
        plan_id="W12-00005",
        draft={
            "task_id": "TASK-DIRECT",
            "content_hash": "sha256:direct",
            "body": "direct body",
            "provenance": {"derived_from": ["CHR-00007@v1"]},
        },
        chapter_draft_id="TASK-INDEX",
        model=None,
    )

    assert seen["task_id"] == "TASK-DIRECT"
    assert result["draft_id"] == "TASK-DIRECT"
    assert result["draft_source"] == "direct-draft"
    assert "draft_source" not in result["plan"]["source"]
