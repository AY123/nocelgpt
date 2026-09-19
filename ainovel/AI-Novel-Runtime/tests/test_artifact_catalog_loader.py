from __future__ import annotations

from pathlib import Path

from runtime.serialize.artifact_catalog import catalog_artifacts, catalog_sections, load_artifact_catalog


def test_artifact_catalog_loader_reads_sections(tmp_path: Path):
    root = tmp_path / "quality-golden-set" / "metadata"
    root.mkdir(parents=True)
    (root / "artifact-catalog.json").write_text(
        '{"kind":"artifact_catalog","version":"1.0","sections":[{"section":"a","artifacts":["x"]},{"section":"b","artifacts":["y","z"]}]}',
        encoding="utf-8",
    )

    catalog = load_artifact_catalog(tmp_path)
    assert catalog["kind"] == "artifact_catalog"
    assert catalog_sections(tmp_path) == ["a", "b"]
    assert catalog_artifacts(tmp_path) == ["x", "y", "z"]
