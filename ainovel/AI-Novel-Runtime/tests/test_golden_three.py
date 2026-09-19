from runtime.serialize.golden_three import build_golden_three_review_pack


def test_golden_three_review_pack_structure():
    pack = build_golden_three_review_pack(
        chapters=[
            ("CH-00001", "第一章正文"),
            ("CH-00002", "第二章正文"),
            ("CH-00003", "第三章正文"),
        ]
    )

    assert pack["kind"] == "golden_three_review_pack"
    assert pack["chapter_count"] == 3
    assert pack["chapter_ids"] == ["CH-00001", "CH-00002", "CH-00003"]
    assert "content_hash" in pack
