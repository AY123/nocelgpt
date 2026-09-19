"""mint.py — serial ID allocation under an OS file lock (ID spec §8, §9).

The single critical section of the ID Mint Ledger. `mint_id` runs the normative
minting procedure with an exclusive `fcntl.flock` around read-max→allocate→
append, so concurrent mints (separate processes/threads) never collide — §9's
"concurrent mints produce no duplicate IDs".

POSIX only (darwin/linux). fcntl is not available on Windows; a Windows lock
backend would slot in behind the same `mint_id` seam.
"""
from __future__ import annotations

import fcntl
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from . import ledger as ledger_mod

_LOCK_SUFFIX = ".lock"


class MintLockError(RuntimeError):
    """Raised when the serial mint lock cannot be acquired."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lock_path(project_path) -> Path:
    # A sidecar lock file next to the ledger. Locking the ledger file directly
    # would race with the rewrite; a dedicated lock file is the stable target.
    return ledger_mod.ledger_path(project_path).with_suffix(
        ledger_mod.ledger_path(project_path).suffix + _LOCK_SUFFIX)


def mint_id(project_path, type_code: str, *, minter: str,
            min_width: int = 5, floor: int = 0) -> str:
    """Allocate and record the next ID for `type_code`. Returns the minted ID.

    Runs the §8 procedure under an exclusive OS lock: read the current max
    ordinal (over ALL entries incl. tombstones), allocate max+1 (width-promoted),
    append `{id, type_code, minted_at, minter}`, release. The whole section is
    serialized so two concurrent callers never allocate the same ordinal.

    `floor` is an additional lower bound applied INSIDE the lock: the ordinal is
    strictly above `max(ledger_max, floor)`. It lets a caller keep allocation
    above ids that exist outside the ledger — e.g. facts hand-seeded or minted by
    a pre-ledger Project (the documented header-drift case) — so a divergent
    ledger never re-allocates an ordinal already on disk. It does not weaken
    concurrency: once the first mint appends, ledger_max advances past floor and
    subsequent mints allocate off the ledger as usual."""
    lp = _lock_path(project_path)
    lp.parent.mkdir(parents=True, exist_ok=True)
    lock_fh = open(lp, "w", encoding="utf-8")
    try:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        except OSError as exc:  # pragma: no cover - platform/edge dependent
            raise MintLockError(f"could not acquire mint lock at {lp}: {exc}") from exc

        # --- critical section (serialized) ---
        led = ledger_mod.load_ledger(project_path)
        ordinal = max(ledger_mod.max_ordinal(led, type_code), floor) + 1
        new_id = ledger_mod.format_id(type_code, ordinal, min_width=min_width)
        led.setdefault("entries", []).append({
            "id": new_id,
            "type_code": type_code,
            "minted_at": _now_iso(),
            "minter": minter,
        })
        _write_ledger(project_path, led)
        return new_id
        # --- end critical section ---
    finally:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        lock_fh.close()


def _write_ledger(project_path, ledger: dict) -> None:
    """Persist the ledger. Kept append-only by construction: callers only ever
    append to `entries`; this serializes the whole dict back."""
    p = ledger_mod.ledger_path(project_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(ledger, sort_keys=False, allow_unicode=True),
                 encoding="utf-8")
