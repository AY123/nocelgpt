"""Render a semantic ledger into a compact prompt block the drafter reads."""
from __future__ import annotations

from typing import Any, Mapping


def render_semantic_ledger(ledger: Mapping[str, Any]) -> str:
    """Flatten the six-category semantic ledger into a deterministic prompt block.

    Each non-empty category renders as a `【类别】` header followed by one line per
    entry (id + text + key fields). Empty categories are omitted entirely, so a
    fresh project renders to an empty string and stays byte-identical to before
    this block existed.
    """
    ledger = ledger or {}
    lines: list[str] = []
    category_specs = [
        ("knowledge", "知识"),
        ("ability", "能力"),
        ("injury", "伤情"),
        ("items", "物品"),
        ("relationship_expectation", "关系预期"),
        ("promise", "承诺"),
    ]
    for key, label in category_specs:
        entries = ledger.get(key) or []
        if not entries:
            continue
        lines.append(f"【{label}】")
        for e in entries:
            if not isinstance(e, Mapping):
                continue
            eid = str(e.get("entry_id") or e.get("promise_id") or "")
            text = str(e.get("text") or e.get("promise_text") or "")
            status = str(e.get("status") or "") if e.get("status") else ""
            source = str(e.get("source_chapter") or "") if e.get("source_chapter") is not None else ""
            due = str(e.get("due_by") or "") if e.get("due_by") else ""
            tail_parts = []
            if status:
                tail_parts.append(f"状态={status}")
            if source:
                tail_parts.append(f"来源章={source}")
            if due:
                tail_parts.append(f"到期={due}")
            tail = "；".join(tail_parts)
            line = f"- {eid}：{text}"
            if tail:
                line += f"（{tail}）"
            lines.append(line)
    return "\n".join(lines)
