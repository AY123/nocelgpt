from runtime import derived
from runtime.serialize.golden_three_records import build_golden_three_review_record
from runtime.serialize.golden_three_query import list_golden_three_review_records, load_golden_three_review_record


def test_golden_three_query_lists_and_loads_records(tmp_path):
    record = build_golden_three_review_record(
        chapters=[("CH-00001", "第一章正文"), ("CH-00002", "第二章正文"), ("CH-00003", "第三章正文")],
        reviewers=["reviewer-a", "reviewer-b"],
        notes="golden three query",
    )
    rel = derived.write_artifact(
        project_path=tmp_path,
        category="golden-three-review-records",
        artifact_id="GTR-00001",
        artifact=record,
        serialized=__import__("json").dumps(record, ensure_ascii=False, sort_keys=True, indent=2),
    )
    assert rel == "registry/derived/golden-three-review-records/GTR-00001.json"
    records = list_golden_three_review_records(tmp_path)
    loaded = load_golden_three_review_record(tmp_path, "GTR-00001")

    assert records and records[0]["id"] == "GTR-00001"
    assert loaded is not None
    assert loaded["kind"] == "golden_three_review_record"
