from runtime.serialize.chapter_baseline import build_thirty_chapter_baseline, write_thirty_chapter_baseline


CHAPTERS = []
for i in range(1, 31):
    CHAPTERS.append({
        "chapter_index": i,
        "chapter_id": f"CH-{i:03d}",
        "title": f"第{i}章",
        "draft_hash": f"sha256:draft{i}",
        "state_hash": f"sha256:state{i}",
        "final_hash": f"sha256:final{i}",
        "quality": {"verdict": "pass"},
        "commercial_verdict": "ok",
        "publish_readiness": {"recommendation": "publish"},
        "prompt_provenance": {"route_summary": {"model": "deepseek"}},
    })


def test_thirty_chapter_baseline_builds():
    baseline = build_thirty_chapter_baseline(chapters=CHAPTERS, reviewers=["editor-A", "editor-B"], notes="30章基线")
    data = baseline.to_dict()

    assert data["kind"] == "thirty_chapter_baseline"
    assert data["comparison_only"] is True
    assert data["gating"] is False
    assert data["chapter_count"] == 30
    assert len(data["summaries"]) == 30
    assert data["summaries"][0]["chapter_id"] == "CH-001"
    assert data["summaries"][0]["draft_hash"] == "sha256:draft1"
    assert data["summaries"][0]["quality_verdict"] == "pass"
    assert len(data["human_reviews"]) == 30
    assert data["reviewers"] == ["editor-A", "editor-B"]


def test_thirty_chapter_baseline_writes(tmp_path):
    baseline = build_thirty_chapter_baseline(chapters=CHAPTERS)
    out = write_thirty_chapter_baseline(tmp_path / "baseline.json", baseline)
    assert out.exists()
