"""idmint/ — the ID Mint Ledger (roadmap Phase 5.4).

Implements the FROZEN Standard spec (ID Naming Specification §8 minting
procedure + §9 conformance, Registry Directory Specification §5): the serial,
append-only allocation of entity IDs. This is not new design — the ledger
contract is fixed and the file (`_meta/mint-ledger.yaml`) already exists; this
subdomain is its Runtime implementation.

The minting procedure (§8, normative):
  1. Acquire the Project's serial mint lock.
  2. Read the current max ordinal for the requested type-code from the ledger.
  3. Allocate max + 1; promote width past 999... .
  4. Record the new ID in the ledger with timestamp + minter.
  5. Release the lock.

DISCIPLINE:
  - The ledger is a FACT (it records what was minted; ground truth, not
    inference), living under `_meta/`. Writing it is NOT a `registry/facts/**`
    write, so it does not conflict with the "mint/ is the only facts-writer"
    guard — but a `new` entity's fact file and its ledger entry are written
    together by the mint executor (5.2), the one human-authorized crossing.
  - APPEND-ONLY: entries are never rewritten or reordered. A tombstoned
    entity's ordinal stays in the ledger forever and is therefore never
    reminted (ID spec §7).
  - SERIALIZED: the read-max→allocate→append critical section runs under an OS
    file lock (fcntl.flock), so concurrent mints never collide (§9).
"""
from .mint import mint_id, MintLockError
from .ledger import (
    load_ledger,
    max_ordinal,
    is_tombstoned,
    ledger_path,
    type_code_summary,
    format_id,
)

__all__ = [
    "mint_id", "MintLockError",
    "load_ledger", "max_ordinal", "is_tombstoned", "ledger_path",
    "type_code_summary", "format_id",
]
