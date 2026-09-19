from __future__ import annotations

from runtime.execution.m7 import _build_similarity_report


def test_m7_similarity_uses_references_not_self_similarity():
    body = "主角站在门口，等待最后的答案。"
    references = [
        {"source_id": "REF-1", "source_type": "reference", "text": "完全不同的文本内容。"},
        {"source_id": "REF-2", "source_type": "reference", "text": "主角站在门口，等待最后的答案。"},
    ]

    report = _build_similarity_report(body=body, references=references, top_k=2)

    assert report["reference_count"] == 2
    assert report["embedding_similarity"] <= 1.0
    assert report["overall_similarity"] >= 0.0
    assert report["matches"]
    assert report["matches"][0]["source_id"] == "REF-2"
