from runtime.director.consumption import build_consumption_evidence
from runtime.director.consumption_report import build_consumption_ab_report


APPROVED_FACTS = [
    {"id": "FACT-1", "name": "钥匙", "aliases": ["金钥匙"]},
    {"id": "FACT-2", "name": "门", "aliases": []},
]


def test_consumption_ab_report_detects_prompt_and_draft_changes():
    evidence = build_consumption_evidence(
        chapter_id="CH-01",
        approved_candidates=[{"id": "CAND-1"}],
        mint_records=[{"id": "FACT-1", "name": "钥匙", "field": "item", "value": "金钥匙"}],
        recompute={"id": "RC-1"},
        state_before={"state_hash": "sha256:before"},
        state_after={"state_hash": "sha256:after"},
        objective_id="OBJ-1",
        prompt_manifest_id="PM-1",
        draft_ref="DRAFT-1",
    )
    report = build_consumption_ab_report(
        chapter_id="CH-01",
        consumption_evidence=evidence,
        arm_without={
            "prompt_manifest_hash": "sha256:pm-before",
            "prompt_rendered_hash": "sha256:render-before",
            "draft_content_hash": "sha256:draft-before",
            "body": "主角空手站在封闭入口前",
        },
        arm_with={
            "prompt_manifest_hash": "sha256:pm-after",
            "prompt_rendered_hash": "sha256:render-after",
            "draft_content_hash": "sha256:draft-after",
            "body": "主角握住金钥匙，推开那扇门",
        },
        approved_facts=APPROVED_FACTS,
        historical_fact_hashes_before={"FACT-BASE": "sha256:base"},
        historical_fact_hashes_after={"FACT-BASE": "sha256:base"},
    )

    assert report["criteria"]["prompt_content_changed"] is True
    assert report["criteria"]["prompt_manifest_hash_changed"] is True
    assert report["criteria"]["draft_content_hash_changed"] is True
    assert report["criteria"]["historical_fact_hashes_unchanged"] is True
    assert report["criteria"]["approved_facts_absent_without"] is True
    assert report["criteria"]["approved_facts_reflected"] is True
    assert report["criteria"]["report_replayable"] is True
    assert report["all_criteria_met"] is True


def test_consumption_ab_report_flags_missing_reflection():
    evidence = build_consumption_evidence(
        chapter_id="CH-02",
        approved_candidates=[],
        mint_records=[{"id": "FACT-9", "name": "隐藏之门", "field": "item", "value": "门"}],
        recompute={"id": "RC-2"},
        state_before={"state_hash": "sha256:before"},
        state_after={"state_hash": "sha256:after"},
        objective_id="OBJ-2",
        prompt_manifest_id="PM-2",
        draft_ref="DRAFT-2",
    )
    report = build_consumption_ab_report(
        chapter_id="CH-02",
        consumption_evidence=evidence,
        arm_without={
            "prompt_manifest_hash": "sha256:pm-before",
            "prompt_rendered_hash": "sha256:render-before",
            "draft_content_hash": "sha256:draft-before",
            "body": "平静的一章",
        },
        arm_with={
            "prompt_manifest_hash": "sha256:pm-after",
            "prompt_rendered_hash": "sha256:render-after",
            "draft_content_hash": "sha256:draft-after",
            "body": "平静的一章",
        },
        approved_facts=[{"id": "FACT-9", "name": "隐藏之门", "aliases": []}],
        historical_fact_hashes_before={"FACT-BASE": "sha256:base"},
        historical_fact_hashes_after={"FACT-BASE": "sha256:base"},
    )

    assert report["criteria"]["approved_facts_reflected"] is False
    assert report["all_criteria_met"] is False


def test_consumption_ab_report_flags_fact_leakage_into_without_arm():
    evidence = build_consumption_evidence(
        chapter_id="CH-03",
        mint_records=[{"id": "FACT-1", "name": "金钥匙", "field": "name", "value": "金钥匙"}],
    )
    report = build_consumption_ab_report(
        chapter_id="CH-03", consumption_evidence=evidence,
        arm_without={
            "prompt_manifest_hash": "sha256:a", "prompt_rendered_hash": "sha256:a",
            "draft_content_hash": "sha256:a", "body": "他拿起金钥匙。"},
        arm_with={
            "prompt_manifest_hash": "sha256:b", "prompt_rendered_hash": "sha256:b",
            "draft_content_hash": "sha256:b", "body": "他拿起金钥匙。"},
        approved_facts=[{"id": "FACT-1", "name": "金钥匙"}],
    )
    assert report["criteria"]["approved_facts_absent_without"] is False
    assert report["all_criteria_met"] is False
