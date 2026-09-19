from __future__ import annotations

from runtime.serialize import render_w9_summary_markdown, write_w9_summary_markdown


def test_w9_summary_markdown_contains_key_sections():
    md = render_w9_summary_markdown("/Users/angyang/Documents/xiaoshuo/AINovel")
    assert "# W9 Reviewer Calibration Summary" in md
    assert "## Boundary" in md
    assert "## Dimension Stats" in md
    assert "real_sample_count" not in md
    assert "opening_hook" in md


def test_w9_summary_markdown_write():
    path = write_w9_summary_markdown("/Users/angyang/Documents/xiaoshuo/AINovel")
    assert path.name == "w9-calibration-summary.md"
    assert path.exists()
