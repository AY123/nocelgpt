from __future__ import annotations

from runtime.execution.redline import RedlineRule, load_ruleset, save_ruleset, check_redlines


def test_ruleset_save_load_roundtrip(tmp_path):
    rules = [RedlineRule(rule_id="r1", pattern="foo", severity="hard", scope="body", action="block", priority=1)]
    save_ruleset(tmp_path, rules, "custom")
    loaded = load_ruleset(tmp_path, "custom")
    assert loaded is not None
    assert loaded[0].rule_id == "r1"
    assert loaded[0].pattern == "foo"


def test_ruleset_dsl_priority_and_scope(tmp_path):
    rules = [
        RedlineRule(rule_id="title", pattern="禁书", severity="hard", scope="title", action="block", priority=1),
        RedlineRule(rule_id="body", pattern="危险", severity="soft", scope="body", action="review", priority=2),
    ]
    hits = check_redlines({"title": "禁书", "body": "危险"}, rules)
    assert [h.rule for h in hits] == ["title", "body"]
