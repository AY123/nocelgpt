"""test_idmint.py — the ID Mint Ledger (roadmap Phase 5.4).

Pins the normative minting procedure (ID Naming Specification §8, §9; Registry
Directory Specification §5) as implemented by runtime/idmint/:

  - MONOTONE per type-code: the next ordinal is strictly max+1, one sequence per
    type code, independent across codes.
  - TOMBSTONE RESERVATION (ID spec §7): a tombstoned entry's ordinal is counted
    in max, so it is never reminted — allocation never fills a gap.
  - APPEND-ONLY: a mint only appends; prior entries are never rewritten/reordered.
  - WIDTH PROMOTION (§8): ordinals ≤ 99999 zero-pad to 5; larger widen naturally.
  - HEADER DRIFT: a ledger seeded without a top-level `version` still loads/mints.
  - SERIALIZED (§9): concurrent mints (separate processes under the OS flock)
    produce no duplicate IDs.
  - The emitted ledger conforms to the frozen MintLedger contract.

Deterministic — no live model.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from runtime import idmint
from runtime.idmint import ledger as ledger_mod

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
_LEDGER_SCHEMA = Draft202012Validator(json.loads(
    (STANDARD / "contracts" / "mint-ledger.schema.json").read_text(encoding="utf-8")))


def _ledger_errors(led: dict) -> list:
    return [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}"
            for e in _LEDGER_SCHEMA.iter_errors(led)]


# --------------------------------------------------------------------------- #
# Monotone per-type-code allocation                                           #
# --------------------------------------------------------------------------- #
def test_allocates_monotone_per_type_code(tmp_path):
    a = idmint.mint_id(tmp_path, "CHR", minter="t")
    b = idmint.mint_id(tmp_path, "CHR", minter="t")
    c = idmint.mint_id(tmp_path, "CHR", minter="t")
    assert [a, b, c] == ["CHR-00001", "CHR-00002", "CHR-00003"]


def test_type_codes_are_independent_sequences(tmp_path):
    assert idmint.mint_id(tmp_path, "CHR", minter="t") == "CHR-00001"
    assert idmint.mint_id(tmp_path, "EVT", minter="t") == "EVT-00001"
    assert idmint.mint_id(tmp_path, "CHR", minter="t") == "CHR-00002"
    assert idmint.mint_id(tmp_path, "ITM", minter="t") == "ITM-00001"
    assert idmint.type_code_summary(idmint.load_ledger(tmp_path)) == {
        "CHR": 2, "EVT": 1, "ITM": 1}


# --------------------------------------------------------------------------- #
# Tombstone reservation (ID spec §7): a gap is NEVER filled                    #
# --------------------------------------------------------------------------- #
def test_tombstoned_ordinal_is_never_reminted(tmp_path):
    idmint.mint_id(tmp_path, "CHR", minter="t")  # CHR-00001
    idmint.mint_id(tmp_path, "CHR", minter="t")  # CHR-00002
    # tombstone the middle one directly in the ledger (status lives on the entry)
    led = idmint.load_ledger(tmp_path)
    led["entries"][1]["status"] = "tombstoned"
    ledger_mod.ledger_path(tmp_path).write_text(
        yaml.safe_dump(led, sort_keys=False, allow_unicode=True), encoding="utf-8")

    assert idmint.is_tombstoned(idmint.load_ledger(tmp_path), "CHR-00002") is True
    # the next mint is strictly above the historical max — the ordinal 2 stays
    # reserved forever even though its entity is dead.
    assert idmint.mint_id(tmp_path, "CHR", minter="t") == "CHR-00003"


def test_max_ordinal_counts_tombstoned_entries(tmp_path):
    led = {"entries": [
        {"id": "CHR-00001", "type_code": "CHR", "minted_at": "x", "minter": "t"},
        {"id": "CHR-00007", "type_code": "CHR", "minted_at": "x", "minter": "t",
         "status": "tombstoned"},
    ]}
    assert idmint.max_ordinal(led, "CHR") == 7
    assert idmint.max_ordinal(led, "EVT") == 0


# --------------------------------------------------------------------------- #
# Append-only                                                                  #
# --------------------------------------------------------------------------- #
def test_mint_only_appends(tmp_path):
    idmint.mint_id(tmp_path, "CHR", minter="t")
    idmint.mint_id(tmp_path, "EVT", minter="t")
    before = idmint.load_ledger(tmp_path)["entries"]
    idmint.mint_id(tmp_path, "CHR", minter="t")
    after = idmint.load_ledger(tmp_path)["entries"]
    # every prior entry is byte-for-byte preserved and in order; only a tail append
    assert after[:len(before)] == before
    assert len(after) == len(before) + 1


# --------------------------------------------------------------------------- #
# Width promotion (ID spec §8)                                                 #
# --------------------------------------------------------------------------- #
def test_width_promotes_past_five_digits(tmp_path):
    assert ledger_mod.format_id("CHR", 7) == "CHR-00007"
    assert ledger_mod.format_id("CHR", 99999) == "CHR-99999"
    # past the 5-digit ceiling the width grows rather than truncating (grammar \d{5,})
    assert ledger_mod.format_id("CHR", 100000) == "CHR-100000"
    assert ledger_mod.format_id("CHR", 1234567) == "CHR-1234567"


def test_allocation_above_five_digit_ceiling(tmp_path):
    led = {"entries": [
        {"id": "CHR-99999", "type_code": "CHR", "minted_at": "x", "minter": "t"}]}
    ledger_mod.ledger_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    ledger_mod.ledger_path(tmp_path).write_text(
        yaml.safe_dump(led, sort_keys=False), encoding="utf-8")
    assert idmint.mint_id(tmp_path, "CHR", minter="t") == "CHR-100000"


# --------------------------------------------------------------------------- #
# floor: allocate above ids that exist OUTSIDE the ledger (header-drift safety) #
# --------------------------------------------------------------------------- #
def test_floor_keeps_allocation_above_out_of_ledger_ids(tmp_path):
    # A Project seeded before the ledger existed holds CHR-00001..3 with an EMPTY
    # ledger. Without a floor, the first mint would allocate CHR-00001 and clobber
    # an existing entity; the floor forces it strictly above the on-disk max.
    assert idmint.mint_id(tmp_path, "CHR", minter="t", floor=3) == "CHR-00004"
    # once the ledger has an entry, it drives allocation as usual (floor is only a
    # lower bound, never lowers the ledger max)
    assert idmint.mint_id(tmp_path, "CHR", minter="t", floor=2) == "CHR-00005"
    assert idmint.mint_id(tmp_path, "CHR", minter="t") == "CHR-00006"


# --------------------------------------------------------------------------- #
# Header drift: a ledger without a top-level `version` still loads + mints      #
# --------------------------------------------------------------------------- #
def test_header_drift_no_version_key(tmp_path):
    p = ledger_mod.ledger_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # the older seeded form — entries only, no `version`
    p.write_text(yaml.safe_dump({"entries": [
        {"id": "CHR-00001", "type_code": "CHR", "minted_at": "x", "minter": "t"}]}),
        encoding="utf-8")
    assert idmint.mint_id(tmp_path, "CHR", minter="t") == "CHR-00002"


def test_missing_ledger_is_empty_not_error(tmp_path):
    assert idmint.load_ledger(tmp_path) == {"entries": []}
    assert idmint.max_ordinal(idmint.load_ledger(tmp_path), "CHR") == 0


# --------------------------------------------------------------------------- #
# Schema conformance: the emitted ledger matches the frozen contract            #
# --------------------------------------------------------------------------- #
def test_emitted_ledger_conforms_to_contract(tmp_path):
    idmint.mint_id(tmp_path, "CHR", minter="operator:alice")
    idmint.mint_id(tmp_path, "EVT", minter="runtime:mint-executor")
    led = idmint.load_ledger(tmp_path)
    assert _ledger_errors(led) == []


def test_seeded_version_form_conforms(tmp_path):
    # the template-seeded form: version + entries
    led = {"version": 1, "entries": [
        {"id": "CHR-00001", "type_code": "CHR", "minted_at": "2026-01-01T00:00:00+00:00",
         "minter": "t", "status": "tombstoned"}]}
    assert _ledger_errors(led) == []


# --------------------------------------------------------------------------- #
# Serialized (ID spec §9): concurrent mints produce no duplicate IDs            #
# --------------------------------------------------------------------------- #
_CHILD = """
import sys
from runtime import idmint
proj = sys.argv[1]
for _ in range(int(sys.argv[2])):
    idmint.mint_id(proj, "CHR", minter="proc")
"""


def test_concurrent_mints_produce_no_duplicates(tmp_path):
    import subprocess

    child = tmp_path / "_child.py"
    child.write_text(_CHILD, encoding="utf-8")
    runtime_parent = str(Path(__file__).resolve().parent.parent)
    env = dict(os.environ, PYTHONPATH=runtime_parent)

    per_proc, procs = 25, 4
    running = [
        subprocess.Popen([sys.executable, str(child), str(tmp_path), str(per_proc)],
                         env=env, cwd=runtime_parent)
        for _ in range(procs)
    ]
    for p in running:
        assert p.wait() == 0

    led = idmint.load_ledger(tmp_path)
    ids = [e["id"] for e in led["entries"]]
    # no collisions, and the sequence is exactly contiguous 1..N (the lock made
    # read-max→append atomic; a lost update would show as a duplicate + a gap).
    assert len(ids) == per_proc * procs
    assert len(set(ids)) == len(ids)
    ordinals = sorted(int(i.split("-")[1]) for i in ids)
    assert ordinals == list(range(1, per_proc * procs + 1))
