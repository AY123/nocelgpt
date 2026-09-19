from pathlib import Path

from runtime.cli import main


def _write_reference_novel(path: Path) -> None:
    path.write_text(
        """序章
强钩子开局。

第一章
主角立刻遭遇冲突，目标明确，章末留钩子。
""",
        encoding="utf-8",
    )


def test_reference_abstract_cli(tmp_path, capsys):
    project = tmp_path
    ref_dir = project / "sources" / "reference-novels"
    ref_dir.mkdir(parents=True)
    _write_reference_novel(ref_dir / "ref1.txt")

    code = main([
        "reference",
        "abstract",
        "--project",
        str(project),
    ])
    assert code == 0
    out = capsys.readouterr().out
    assert "reference abstraction produced" in out
    assert "registry/derived/reference-abstract/REFABSTRACT-001.json" in out


def test_reference_show_and_validate_cli(tmp_path, capsys):
    project = tmp_path
    ref_dir = project / "sources" / "reference-novels"
    ref_dir.mkdir(parents=True)
    _write_reference_novel(ref_dir / "ref1.txt")

    assert main(["reference", "validate", "--project", str(project)]) == 0
    assert main(["reference", "abstract", "--project", str(project)]) == 0
    assert main(["reference", "show", "--project", str(project)]) == 0
    out = capsys.readouterr().out
    assert "OK: M5 reference abstraction input is valid" in out
    assert "REFABSTRACT-001" in out
