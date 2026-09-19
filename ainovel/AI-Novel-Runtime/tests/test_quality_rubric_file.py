from __future__ import annotations

from pathlib import Path

from runtime.serialize.quality_rubric import RUBRIC_FILENAME, write_quality_rubric_file


def test_write_quality_rubric_file(tmp_path: Path):
    out = write_quality_rubric_file(tmp_path)

    assert out.name == RUBRIC_FILENAME
    text = out.read_text(encoding="utf-8")
    assert 'kind: "quality_rubric"' in text
    assert 'opening_hook' in text
