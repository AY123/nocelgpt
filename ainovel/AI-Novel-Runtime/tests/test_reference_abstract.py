from pathlib import Path

from runtime.reference.abstract import build_reference_abstraction, write_reference_abstraction


def _write_reference_novel(path: Path) -> None:
    path.write_text(
        """序章
强钩子开局。

第一章
主角立刻遭遇冲突，目标明确，代价清晰，章末留钩子。

第二章
冲突升级，人物关系变化，信息差持续释放，结尾继续推进。
""",
        encoding="utf-8",
    )


def test_build_reference_abstraction(tmp_path):
    project = tmp_path
    ref_dir = project / "sources" / "reference-novels"
    ref_dir.mkdir(parents=True)
    _write_reference_novel(ref_dir / "ref1.txt")

    abstraction = build_reference_abstraction(project)

    assert abstraction["kind"] == "reference_lm_abstraction"
    assert abstraction["id"] == "REFABSTRACT-001"
    assert abstraction["market_positioning"]["core_promise"]
    assert abstraction["structural_patterns"]["opening"]
    assert abstraction["source_summaries"]
    assert abstraction["evidence_spans"]

    rel = write_reference_abstraction(project, abstraction)
    assert rel == "registry/derived/reference-abstract/REFABSTRACT-001.json"
    assert (project / rel).exists()
