"""redline.py — deterministic content safety gate (ANES v2, ADR-003, Phase 4.1).

This is the DETERMINISTIC half of the safety split (Phase 4 invariant #3):

    subjective "edginess risk"  -> quality-report v2 scores.safety_risk (EVALUATIVE, never gates)
    objective banned-term / hard-line hit -> HERE (DETERMINISTIC, MAY gate the build)

Rules are DATA, not code: the default ruleset is a conservative, editable seed.
A Project may override it with its own ruleset (e.g. platform-specific lines)
without touching this module — matching the "rules are authored artifacts" spirit.

Redline DSL supports:
  - literal regex patterns
  - scope (title/body/summary/any)
  - severity + action
  - required/forbidden tags
  - minimum/maximum lengths
  - priority ordering
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Sequence

import yaml

from .redline_rules import RULESET_VERSION as _RULESET_VERSION
from .redline_rules import SEED_RULES as _SEED_RULES


@dataclass(frozen=True)
class RedlineRule:
    rule_id: str
    pattern: str = ""
    severity: str = "soft"
    note: str = ""
    scope: str = "body"
    action: str = "advisory"  # advisory | review | block
    priority: int = 100
    tags_any: tuple[str, ...] = field(default_factory=tuple)
    tags_all: tuple[str, ...] = field(default_factory=tuple)
    tags_none: tuple[str, ...] = field(default_factory=tuple)
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    source_type_any: tuple[str, ...] = field(default_factory=tuple)
    source_type_none: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "pattern": self.pattern,
            "severity": self.severity,
            "note": self.note,
            "scope": self.scope,
            "action": self.action,
            "priority": self.priority,
            "tags_any": list(self.tags_any),
            "tags_all": list(self.tags_all),
            "tags_none": list(self.tags_none),
            "min_length": self.min_length,
            "max_length": self.max_length,
            "source_type_any": list(self.source_type_any),
            "source_type_none": list(self.source_type_none),
        }


@dataclass(frozen=True)
class RedlineHit:
    rule: str
    severity: str
    evidence: str
    action: str = "advisory"
    scope: str = "body"
    span: tuple[int, int] | None = None
    note: str = ""


def _rule_from_seed(item: dict) -> RedlineRule:
    return RedlineRule(
        rule_id=str(item["rule_id"]),
        pattern=str(item.get("pattern", "")),
        severity=str(item.get("severity", "soft")),
        note=str(item.get("note", "")),
        scope=str(item.get("scope", "body")),
        action=str(item.get("action", "advisory")),
        priority=int(item.get("priority", 100)),
    )


# The built-in seed is real platform redline data (see redline_rules.py), not
# placeholders. hard/block rules gate deterministically; soft/review are advisory.
DEFAULT_RULESET: tuple = tuple(_rule_from_seed(r) for r in _SEED_RULES)
DEFAULT_RULESET_VERSION = _RULESET_VERSION


def _ruleset_dir(project_path: str | Path) -> Path:
    return Path(project_path) / "registry" / "derived" / "m7"


def _ruleset_path(project_path: str | Path, rule_set_id: str) -> Path:
    return _ruleset_dir(project_path) / f"redline-rules-{rule_set_id}.yaml"


def save_ruleset(project_path: str | Path, ruleset: Sequence[RedlineRule], rule_set_id: str = "default") -> str:
    out = _ruleset_path(project_path, rule_set_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"kind": "m7_redline_ruleset", "rule_set_id": rule_set_id, "rules": [r.to_dict() for r in ruleset]}
    out.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return str(out)


def load_ruleset(project_path: str | Path, rule_set_id: str = "default") -> Optional[list[RedlineRule]]:
    path = _ruleset_path(project_path, rule_set_id)
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    rules = []
    for item in data.get("rules", []):
        if not isinstance(item, dict):
            continue
        def _tuple(name):
            v = item.get(name, [])
            return tuple(v) if isinstance(v, list) else tuple()
        try:
            rules.append(RedlineRule(
                rule_id=str(item.get("rule_id", "")),
                pattern=str(item.get("pattern", "")),
                severity=str(item.get("severity", "soft")),
                note=str(item.get("note", "")),
                scope=str(item.get("scope", "body")),
                action=str(item.get("action", "advisory")),
                priority=int(item.get("priority", 100)),
                tags_any=_tuple("tags_any"),
                tags_all=_tuple("tags_all"),
                tags_none=_tuple("tags_none"),
                min_length=item.get("min_length"),
                max_length=item.get("max_length"),
                source_type_any=_tuple("source_type_any"),
                source_type_none=_tuple("source_type_none"),
            ))
        except Exception:
            continue
    return rules or None


def _scope_text(artifact: dict, scope: str) -> str:
    if scope == "title":
        return artifact.get("title", "") or ""
    if scope == "summary":
        return artifact.get("summary", "") or ""
    if scope == "body":
        return artifact.get("body", "") or ""
    if scope == "any":
        return "\n".join(str(artifact.get(k, "") or "") for k in ("title", "summary", "body"))
    return artifact.get("body", "") or ""


def _matches_rule(rule: RedlineRule, artifact: dict) -> tuple[bool, str, tuple[int, int] | None]:
    tags = set(artifact.get("tags", []) or [])
    source_type = artifact.get("source_type", "") or ""
    text = _scope_text(artifact, rule.scope)
    if rule.min_length is not None and len(text) < rule.min_length:
        return False, "", None
    if rule.max_length is not None and len(text) > rule.max_length:
        return False, "", None
    if rule.tags_any and not (tags & set(rule.tags_any)):
        return False, "", None
    if rule.tags_all and not set(rule.tags_all).issubset(tags):
        return False, "", None
    if rule.tags_none and (tags & set(rule.tags_none)):
        return False, "", None
    if rule.source_type_any and source_type not in rule.source_type_any:
        return False, "", None
    if rule.source_type_none and source_type in rule.source_type_none:
        return False, "", None
    if not rule.pattern:
        return True, text[:40], None
    try:
        m = re.search(rule.pattern, text, re.IGNORECASE)
    except re.error:
        return False, "", None
    if not m:
        return False, "", None
    frag = m.group(0)
    evidence = frag if len(frag) <= 40 else frag[:37] + "..."
    return True, evidence, m.span()


def check_redlines(artifact: dict,
                   ruleset: Optional[Sequence[RedlineRule]] = None) -> List[RedlineHit]:
    rules = sorted(list(ruleset if ruleset is not None else DEFAULT_RULESET), key=lambda r: (r.priority, r.rule_id))
    hits: List[RedlineHit] = []
    for rule in rules:
        matched, evidence, span = _matches_rule(rule, artifact)
        if matched:
            hits.append(RedlineHit(
                rule=rule.rule_id,
                severity=rule.severity,
                evidence=evidence,
                action=rule.action,
                scope=rule.scope,
                span=span,
                note=rule.note,
            ))
    return hits


def has_hard_hit(hits: Sequence[RedlineHit]) -> bool:
    return any(h.action == "block" or h.severity == "hard" for h in hits)


def hits_to_dicts(hits: Sequence[RedlineHit]) -> List[dict]:
    return [{"rule": h.rule, "severity": h.severity, "evidence": h.evidence, "action": h.action, "scope": h.scope, "span": h.span, "note": h.note}
            for h in hits]
