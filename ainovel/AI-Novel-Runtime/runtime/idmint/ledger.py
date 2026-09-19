"""ledger.py — read/parse the append-only mint ledger (ID spec §8, Registry §5).

Pure read + parse helpers. The write (append under lock) lives in mint.py so the
critical section is in one place. Tolerant of header drift: early Projects seeded
the ledger without a top-level `version` key; both forms load.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml

LEDGER_REL = ("registry", "_meta", "mint-ledger.yaml")
_INACTIVE = ("deprecated", "tombstoned")


def ledger_path(project_path: str | Path) -> Path:
    return Path(project_path).joinpath(*LEDGER_REL)


def load_ledger(project_path: str | Path) -> dict:
    """Load the ledger dict. A missing file is an empty ledger (a fresh Project
    that never minted). Header drift is tolerated: `version` may be absent."""
    p = ledger_path(project_path)
    if not p.exists():
        return {"entries": []}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    data.setdefault("entries", [])
    return data


def _ordinal(entity_id: str) -> Optional[int]:
    """The integer ordinal of an ID (CHR-00007 -> 7). None if malformed."""
    _, _, tail = entity_id.partition("-")
    return int(tail) if tail.isdigit() else None


def max_ordinal(ledger: dict, type_code: str) -> int:
    """Highest ordinal ever minted for a type code (0 if none). Reads EVERY
    entry, including tombstoned ones — a tombstoned ordinal is reserved forever
    (ID spec §7), so the next allocation is strictly above the historical max,
    never reusing a gap."""
    hi = 0
    for e in ledger.get("entries", []):
        if e.get("type_code") != type_code:
            continue
        o = _ordinal(e.get("id", ""))
        if o is not None and o > hi:
            hi = o
    return hi


def is_tombstoned(ledger: dict, entity_id: str) -> bool:
    """Whether an id is recorded and marked tombstoned in the ledger. (Status is
    normally tracked on the fact record; this is a convenience for callers that
    only hold the ledger.)"""
    for e in ledger.get("entries", []):
        if e.get("id") == entity_id:
            return e.get("status") in _INACTIVE
    return False


def existing_ids(ledger: dict) -> set:
    return {e.get("id") for e in ledger.get("entries", []) if e.get("id")}


def type_code_summary(ledger: dict) -> Dict[str, int]:
    """{type_code: max_ordinal} across the whole ledger — for `idmint status`."""
    out: Dict[str, int] = {}
    for e in ledger.get("entries", []):
        tc = e.get("type_code")
        o = _ordinal(e.get("id", ""))
        if tc and o is not None:
            out[tc] = max(out.get(tc, 0), o)
    return out


def format_id(type_code: str, ordinal: int, *, min_width: int = 5) -> str:
    """Render an ordinal as an ID with width promotion past 999... (ID spec §8:
    'if it would exceed current width, promote width'). The grammar is `\\d{5,}`,
    so ordinals ≤ 99999 are zero-padded to 5, and larger ones widen naturally."""
    return f"{type_code}-{ordinal:0{min_width}d}"
