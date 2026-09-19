from __future__ import annotations

from pathlib import Path


def test_live_baseline_fixture_layout():
    root = Path(__file__).resolve().parents[0] / "fixtures" / "live-baseline-5ch"

    assert (root / "README.txt").exists()
    assert (root / "sources" / "reference-novels" / "reference-01.txt").exists()
    assert (root / "registry" / "_meta" / "README.txt").exists()
    assert (root / "registry" / "facts" / "characters" / "README.txt").exists()
    assert (root / "registry" / "facts" / "events" / "README.txt").exists()
    assert (root / "registry" / "facts" / "timelines" / "README.txt").exists()
    assert (root / "registry" / "facts" / "world_rules" / "README.txt").exists()
