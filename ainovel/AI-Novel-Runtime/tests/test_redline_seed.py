"""M1-B1: the default redline seed is real platform data, not inert placeholders.

Locks in: hard rules gate (block), soft rules are advisory (review, never hard),
clean prose passes, and the seed version is exposed for manifest provenance.
"""
from __future__ import annotations

from runtime.execution.redline import (
    DEFAULT_RULESET,
    DEFAULT_RULESET_VERSION,
    check_redlines,
    has_hard_hit,
)


def test_seed_has_no_placeholder_patterns():
    for rule in DEFAULT_RULESET:
        assert "占位符" not in rule.pattern, f"{rule.rule_id} still a placeholder"
    assert DEFAULT_RULESET_VERSION  # non-empty version string


def test_hard_political_redline_blocks():
    hits = check_redlines({"body": "有人企图颠覆国家政权，煽动分裂。"})
    assert has_hard_hit(hits)
    assert any(h.rule == "political-redline" and h.action == "block" for h in hits)


def test_hard_explicit_sexual_blocks():
    hits = check_redlines({"body": "露骨的抽插描写。"})
    assert has_hard_hit(hits)


def test_crime_instruction_blocks():
    hits = check_redlines({"body": "他开始制造冰毒，详细讲解提炼过程。"})
    assert has_hard_hit(hits)


def test_soft_gore_is_advisory_not_hard():
    hits = check_redlines({"body": "战场上血肉模糊，惨不忍睹。"})
    assert hits, "gore should be flagged"
    assert not has_hard_hit(hits), "gore is soft/review, must not gate"
    assert all(h.action == "review" for h in hits if h.rule == "graphic-violence")


def test_clean_prose_passes():
    hits = check_redlines({"body": "他在城门外停下脚步，重新整理行囊，望向远处的群山。"})
    assert hits == []
    assert not has_hard_hit(hits)


def test_title_violation_is_soft_only():
    hits = check_redlines({"title": "禁书传说", "body": "普通正文。"})
    assert any(h.rule == "title-violation" for h in hits)
    assert not has_hard_hit(hits)
