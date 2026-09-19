"""test_chapter_length.py — the shared per-role length source of truth.

接下来两周执行清单 Week-1 item 2 (长度区间设计). Pins that:
  - every chapter role has a function-bound length band,
  - the historical reviewer min_chars floors are preserved EXACTLY (verdicts
    must not shift),
  - the default/advance band equals the old global 0.6–1.5 (role-less path
    unchanged),
  - role inference is deterministic and matches the reviewer's historical tokens.
"""
from __future__ import annotations

from runtime.chapter_length import (
    ROLE_LENGTH, CHAPTER_ROLES, role_length, infer_chapter_role,
    DEFAULT_BAND_LOW, DEFAULT_BAND_HIGH,
)


def test_min_chars_floors_are_unchanged():
    # These are the reviewer's historical verdict floors — changing them shifts
    # verdicts, so they are pinned.
    assert ROLE_LENGTH["opening"]["min_chars"] == 900
    assert ROLE_LENGTH["advance"]["min_chars"] == 700
    assert ROLE_LENGTH["turn"]["min_chars"] == 800
    assert ROLE_LENGTH["hook"]["min_chars"] == 600
    assert ROLE_LENGTH["default"]["min_chars"] == 700


def test_default_band_equals_historical_global_band():
    # A role-less chapter must resolve to the old global band.
    assert DEFAULT_BAND_LOW == 0.6 and DEFAULT_BAND_HIGH == 1.5
    assert role_length("default")["band_low"] == 0.6
    assert role_length("default")["band_high"] == 1.5
    assert role_length(None)["band_low"] == 0.6


def test_bands_are_function_bound():
    # Opening tolerates longer (world-building), hook tolerates shorter (punch).
    assert role_length("opening")["band_low"] > role_length("advance")["band_low"]
    assert role_length("hook")["band_low"] < role_length("advance")["band_low"]
    assert role_length("hook")["band_high"] < role_length("advance")["band_high"]
    # every declared role has a full length contract
    for r in CHAPTER_ROLES:
        rl = role_length(r)
        assert {"min_chars", "band_low", "band_high"} <= set(rl)
        assert 0 < rl["band_low"] < 1 < rl["band_high"]


def test_infer_role_matches_headings():
    assert infer_chapter_role("第一章：开篇\n正文") == "opening"
    assert infer_chapter_role("楔子\n正文") == "opening"
    assert infer_chapter_role("第二章：反转来临\n正文") == "turn"
    assert infer_chapter_role("尾声：钩子\n正文") == "hook"
    assert infer_chapter_role("第三章：日常推进\n正文") == "advance"
    assert infer_chapter_role("") == "advance"


def test_unknown_role_falls_back_to_default():
    assert role_length("nonsense") == ROLE_LENGTH["default"]
