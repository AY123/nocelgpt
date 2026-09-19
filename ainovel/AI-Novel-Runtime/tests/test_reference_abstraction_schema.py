from pathlib import Path

from runtime.reference.abstract import build_reference_abstraction, write_reference_abstraction


def _write_reference_novel(path: Path) -> None:
    path.write_text(
        """序章
强钩子开局。

第一章
主角立刻遭遇冲突，目标明确，章末留钩子。
""",
        encoding="utf-8",
    )


def test_reference_abstraction_schema_fields(tmp_path):
    project = tmp_path
    ref_dir = project / "sources" / "reference-novels"
    ref_dir.mkdir(parents=True)
    _write_reference_novel(ref_dir / "ref1.txt")

    abstraction = build_reference_abstraction(project)
    rel = write_reference_abstraction(project, abstraction)

    assert abstraction["schema_version"] == "1.0"
    assert abstraction["kind"] == "reference_lm_abstraction"
    assert abstraction["market_positioning"]["commercial_thesis"]
    assert abstraction["commercial_cadence"]["mid_arc"]
    assert abstraction["transferable_abstractions"]
    assert abstraction["prohibited_specifics"]
    assert (project / rel).exists()
