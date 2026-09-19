"""ipbible.py — assemble + render an IP reference bible from the Story State.

The IP bible (SOP stage 16) is what an adaptation team (影视/漫画/游戏) needs:
a consolidated reference of characters, timeline, relationships, items, and
world. It is a PURE fold over the Story State projection (P14) — itself a fold
over facts (ADR-008) — so it inherits reproducibility and never touches facts.
assemble (fold to a model) is separated from render (model to bytes) like the
book exporter, so a new format is just another renderer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from .. import registry_loader
from ..memory.state import project_state


@dataclass(frozen=True)
class IPBible:
    title: str
    characters: Dict[str, dict] = field(default_factory=dict)
    items: Dict[str, dict] = field(default_factory=dict)
    relationships: Dict[str, dict] = field(default_factory=dict)
    timelines: Dict[str, dict] = field(default_factory=dict)
    event_order: List[str] = field(default_factory=list)
    resolved_setups: List[dict] = field(default_factory=list)
    open_setups: List[dict] = field(default_factory=list)


def assemble_ip_bible(project_path: str | Path, *, title: str | None = None) -> IPBible:
    """Fold the full Story State projection into an IP bible model. Pure
    read-side: projects from facts, never mutates or writes them."""
    project_path = Path(project_path)
    reg = registry_loader.load(project_path)
    state = project_state(reg).core()
    return IPBible(
        title=title or project_path.name,
        characters=state.get("characters", {}),
        items=state.get("items", {}),
        relationships=state.get("relationships", {}),
        timelines=state.get("timelines", {}),
        event_order=state.get("event_order", []),
        resolved_setups=state.get("resolved_setups", []),
        open_setups=state.get("open_setups", []),
    )


def _lines(header: str, rows: List[str]) -> str:
    body = "\n".join(rows) if rows else "- （无）"
    return f"## {header}\n\n{body}\n"


def render_ip_markdown(bible: IPBible) -> str:
    """Render an IPBible to markdown. Deterministic: same model => same bytes."""
    parts = [f"# {bible.title} — IP 设定集\n"]

    char_rows = [
        f"- {cid} {c.get('name', '')}（{c.get('status', '?')}）："
        f"出场 {len(c.get('appears_in', []))} 次，最近 {c.get('last_event') or '-'}"
        for cid, c in sorted(bible.characters.items())]
    parts.append(_lines("人物", char_rows))

    rel_rows = [
        f"- {r.get('from')} → {r.get('to')}（{r.get('kind')}）"
        f"{'（当前）' if r.get('active') else ''}"
        for _, r in sorted(bible.relationships.items())]
    parts.append(_lines("关系", rel_rows))

    item_rows = [
        f"- {iid} {it.get('name', '')}"
        f"{'，持有者 ' + it['owner'] if it.get('owner') else ''}"
        for iid, it in sorted(bible.items.items())]
    parts.append(_lines("物品/能力", item_rows))

    tl_rows = [f"- {tid} {t.get('name', '')}（{t.get('status', '?')}）"
               for tid, t in sorted(bible.timelines.items())]
    parts.append(_lines("时间线", tl_rows))

    ev_rows = [f"{i}. {eid}" for i, eid in enumerate(bible.event_order, start=1)]
    parts.append(_lines("事件顺序", ev_rows))

    fs_rows = [f"- {s['event']}：{s.get('summary', '')}" for s in bible.open_setups]
    parts.append(_lines("未回收伏笔", fs_rows))

    return "\n".join(parts)
