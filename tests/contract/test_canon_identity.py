"""ADR-005 fixed byte/hash vectors and strict persistence identity boundaries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256

import pytest

from anovel.canon.identity import (
    MAX_NESTING_DEPTH,
    canonical_bytes,
    content_hash,
    decode_canonical,
    raw_prose_hash,
    utc_timestamp,
)


@pytest.mark.parametrize(
    "value,expected,digest",
    [
        ({}, b"{}", "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"),
        ([], b"[]", "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"),
        (1, b"1", "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b"),
        (1.0, b"1", "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b"),
        (
            -0.0,
            b"0",
            "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9",
        ),
        (
            True,
            b"true",
            "b5bea41b6c623f7c09f1bf24dcae58ebab3c0cdd90ad966bc43a45b44867e12b",
        ),
        (
            0.1,
            b"0.1000000000000000055511151231257827021181583404541015625",
            "96db2f78fe4cd6af75a1ad444060e0f5bc0c712c17e8356f0355e09980b10716",
        ),
        (
            {"z": [True, None, "é"], "a": 1},
            b'{"a":1,"z":[true,null,"\xc3\xa9"]}',
            "37fd05785c4b3fec2eec9144720d57bb913b4fd47f7091d37a2591527d777bfe",
        ),
        (
            "中",
            b'"\xe4\xb8\xad"',
            "a4b3fd00fee95c70ae66d7028d19f8f744057fd0f45f2d2949054e3f0f03e630",
        ),
        (
            "é",
            b'"\xc3\xa9"',
            "f2886017e9c7abacf804b54d64787dce2b611c9544ba21f3affdd126a6e50086",
        ),
        (
            "e\u0301",
            b'"e\xcc\x81"',
            "3d68ce21f2899a475713cdbe7562ba9bdb6b1dfde8af1f221bdff4a0935b53b2",
        ),
    ],
)
def test_canonical_fixed_bytes_and_hash_vectors(value, expected, digest):
    assert canonical_bytes(value) == expected
    assert content_hash(value) == digest
    assert canonical_bytes(decode_canonical(expected)) == expected


def test_smallest_finite_float_keeps_every_digit_and_round_trips():
    value = float.fromhex("0x0.0000000000001p-1022")
    expected = (
        b"0."
        + b"0" * 323
        + (
            b"494065645841246544176568792868221372365059802614324764425585682500675"
            b"507270208751865299836361635992379796564695445717730926656710355939"
            b"796398774796010781878126300713190311404527845817167848982103688718"
            b"636056998730723050006387409153564984387312473397273169615140031715"
            b"385398074126238565591171026658556686768187039560310624931945271591"
            b"492455329305456544401127480129709999541931989409080416563324524757"
            b"147869014726780159355238611550134803526493472019379026810710749170"
            b"333222684475333572083243193609238289345836806010601150616980975307"
            b"834227731832924790498252473077637592724787465608477820373446969953"
            b"364701797267771758512566055119913150489110145103786273816725095583"
            b"738973359899366480994116420570263709027924276754456522908753868250"
            b"6419718265533447265625"
        )
    )
    assert canonical_bytes(value) == expected
    assert (
        content_hash(value)
        == "f45aeb158809dfc2e30ccb794028e77653ebdd39eb58ff0f53a66cf3d2e79438"
    )
    assert decode_canonical(expected) == value


def test_huge_integer_is_exact_without_global_interpreter_limit_changes():
    value = 10**5000 + 123
    expected = b"1" + b"0" * 4997 + b"123"
    assert canonical_bytes(value) == expected
    assert (
        content_hash(value)
        == "56e13a6906b3b66585766258924f713b78c55709b4f7e0fe360baec25e66ecee"
    )
    assert decode_canonical(expected) == value
    assert decode_canonical(b"-" + expected) == -value


def test_numeric_sign_and_precision_do_not_collapse_distinct_values():
    assert canonical_bytes(-1.5) == b"-1.5"
    assert canonical_bytes(-2.0) == b"-2"
    assert canonical_bytes(-0.1) == (
        b"-0.1000000000000000055511151231257827021181583404541015625"
    )
    precise_integer = 9_007_199_254_740_993
    assert canonical_bytes(precise_integer) == b"9007199254740993"
    assert canonical_bytes(float(precise_integer)) == b"9007199254740992"
    assert content_hash(precise_integer) != content_hash(float(precise_integer))
    largest_float = float.fromhex("0x1.fffffffffffffp+1023")
    assert decode_canonical(canonical_bytes(largest_float)) == largest_float


def test_object_order_is_irrelevant_but_list_and_unicode_order_are_not():
    assert content_hash({"b": 2, "a": 1}) == content_hash({"a": 1, "b": 2})
    assert canonical_bytes({"\U0001f600": 1, "\ue000": 2}) == (
        '{"\ue000":2,"\U0001f600":1}'.encode()
    )
    assert content_hash([1, 2]) != content_hash([2, 1])
    assert content_hash("é") != content_hash("e\u0301")
    assert content_hash(True) != content_hash(1)
    assert content_hash(False) != content_hash(0)
    assert content_hash(None) != content_hash("null")


def test_fixed_string_escapes_preserve_non_ascii_and_newline_semantics():
    value = '"\\\b\f\n\r\t\x00\x1f/\u2028'
    expected = b'"\\"\\\\\\b\\f\\n\\r\\t\\u0000\\u001f/' + "\u2028".encode() + b'"'
    assert canonical_bytes(value) == expected
    assert decode_canonical(expected) == value
    assert content_hash(" x\r\n") != content_hash("x\n")


@pytest.mark.parametrize(
    "value",
    [
        (),
        set(),
        frozenset(),
        Decimal(1),
        datetime(2026, 10, 19, tzinfo=UTC),
        b"x",
        object(),
    ],
)
def test_unsupported_types_are_not_stringified(value):
    with pytest.raises(ValueError, match="exact JSON"):
        canonical_bytes(value)


@pytest.mark.parametrize("base", [str, int, float, dict, list])
def test_primitive_subclasses_cannot_supply_custom_behavior(base):
    derived = type("Derived", (base,), {})
    with pytest.raises(ValueError, match="exact JSON"):
        canonical_bytes(derived())


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_numbers_rejected(value):
    with pytest.raises(ValueError, match="finite"):
        canonical_bytes(value)


@pytest.mark.parametrize(
    "value", [chr(0xD800), chr(0xDFFF), {chr(0xD800): 1}, [chr(0xDFFF)]]
)
def test_surrogate_strings_are_rejected(value):
    with pytest.raises(ValueError, match="surrogate"):
        canonical_bytes(value)


@pytest.mark.parametrize("key", [1, True, None, type("Derived", (str,), {})("x")])
def test_object_key_must_be_exact_string(key):
    with pytest.raises(ValueError, match="keys"):
        canonical_bytes({key: 1})


def test_cycles_reject_but_shared_non_cyclic_containers_are_valid():
    sequence = []
    sequence.append(sequence)
    with pytest.raises(ValueError, match="cycle"):
        canonical_bytes(sequence)
    record = {}
    record["self"] = record
    with pytest.raises(ValueError, match="cycle"):
        canonical_bytes(record)
    shared = [1]
    assert canonical_bytes([shared, shared]) == b"[[1],[1]]"


def test_depth_limit_is_explicit_for_encoder_and_decoder():
    value = None
    for _ in range(MAX_NESTING_DEPTH):
        value = [value]
    encoded = b"[" * MAX_NESTING_DEPTH + b"null" + b"]" * MAX_NESTING_DEPTH
    assert canonical_bytes(value) == encoded
    assert canonical_bytes(decode_canonical(encoded)) == encoded
    with pytest.raises(ValueError, match="depth"):
        canonical_bytes([value])
    with pytest.raises(ValueError, match="depth"):
        decode_canonical(b"[" + encoded + b"]")
    with pytest.raises(ValueError):
        decode_canonical(b"[" * 2000 + b"0" + b"]" * 2000)


@pytest.mark.parametrize(
    "encoded",
    [
        b"",
        b"{}\n",
        b" {}",
        b'{"b":2,"a":1}',
        b'{"a": 1}',
        b'{"a":1,"a":2}',
        b'{"a":1,"\\u0061":2}',
        b"NaN",
        b"Infinity",
        b"-Infinity",
        b"1e9999",
        b"1.0",
        b"1e0",
        b"-0",
        b"0.1",
        b"01",
        b'"\\u00e9"',
        b'"\\/"',
        b'"\\u0008"',
        b'"\\ud800"',
        b"{}[]",
        b"\xef\xbb\xbf{}",
        b"\xff",
        b"\xed\xa0\x80",
        b'"\n"',
    ],
)
def test_decode_rejects_malformed_or_noncanonical_bytes(encoded):
    with pytest.raises(ValueError):
        decode_canonical(encoded)


@pytest.mark.parametrize("value", ["text", bytearray(b"text"), memoryview(b"text")])
def test_raw_and_structured_decoders_require_exact_bytes(value):
    with pytest.raises(ValueError, match="exact bytes"):
        raw_prose_hash(value)
    with pytest.raises(ValueError, match="exact bytes"):
        decode_canonical(value)


@pytest.mark.parametrize("value", [b"\xff", b"\xed\xa0\x80", b"\xc0\x80"])
def test_raw_prose_must_be_valid_utf8(value):
    with pytest.raises(ValueError, match="valid UTF-8"):
        raw_prose_hash(value)


def test_raw_prose_retains_bom_crlf_spaces_and_is_not_structured_content():
    text = b"\xef\xbb\xbf text\r\n"
    assert raw_prose_hash(text) == sha256(text).hexdigest()
    assert raw_prose_hash(text) != raw_prose_hash(b" text\n")
    assert raw_prose_hash(b"abc") != content_hash("abc")
    assert (
        raw_prose_hash(b"")
        == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_system_time_normalizes_aware_offsets_with_six_microseconds():
    local = datetime(2026, 10, 19, 8, 1, 2, 3, timezone(timedelta(hours=8)))
    assert utc_timestamp(local) == "2026-10-19T00:01:02.000003Z"
    assert utc_timestamp(local) == utc_timestamp(
        datetime(2026, 10, 19, 0, 1, 2, 3, UTC)
    )
    assert utc_timestamp(datetime(1, 1, 1, tzinfo=UTC)) == "0001-01-01T00:00:00.000000Z"
    assert canonical_bytes("2026-10-19T08:01:02+08:00") != canonical_bytes(
        utc_timestamp(local)
    )


@pytest.mark.parametrize(
    "value",
    [None, "2026-10-19", datetime(2026, 10, 19, tzinfo=UTC).replace(tzinfo=None)],
)
def test_system_time_rejects_missing_or_naive_timezone(value):
    with pytest.raises(ValueError, match="aware datetime"):
        utc_timestamp(value)


def test_system_time_rejects_utc_conversion_overflow():
    value = datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=1)))
    with pytest.raises(ValueError, match="UTC datetime range"):
        utc_timestamp(value)


def test_root_seed_preserves_typed_domain_and_canonical_set_order():
    from anovel.canon.models import RootSeed
    from anovel.domain.character import Relationship
    from anovel.domain.identity import Entity, EntityId
    from anovel.domain.knowledge import Proposition, WorldFact

    a = Entity(EntityId("p", "a"), "甲")
    b = Entity(EntityId("p", "b"), "乙")
    relation = Relationship(EntityId("p", "r"), a.id, b.id, {"friends"})
    fact = WorldFact(EntityId("p", "f"), Proposition(a.id, "balance", 0.1), "root:1")
    seed = RootSeed((a, b), (relation,), (fact,))
    assert (
        RootSeed.from_dict(decode_canonical(canonical_bytes(seed.to_dict()))).to_dict()
        == seed.to_dict()
    )
    assert canonical_bytes(
        RootSeed((b, a), (relation,), (fact,)).to_dict()
    ) == canonical_bytes(seed.to_dict())
    for bad in [
        RootSeed.__name__,
        {},
        {**seed.to_dict(), "extra": True},
        {**seed.to_dict(), "schema_version": "2.0"},
    ]:
        with pytest.raises(ValueError):
            RootSeed.from_dict(bad)
    for entities, relationships, facts in [
        ([], (), ()),
        ((), (), ()),
        ((a, a), (), ()),
        ((a,), (relation,), ()),
        ((b,), (), (fact,)),
        ((a, Entity(EntityId("q", "b"), "乙")), (), ()),
    ]:
        with pytest.raises(ValueError):
            RootSeed(entities, relationships, facts)


@pytest.mark.parametrize(
    "field,value",
    [
        ("authorization_version", True),
        ("execution_version", -1),
        ("project", ""),
        ("actor", "\x00"),
        ("request_id", "x" * 201),
    ],
)
def test_execution_ticket_rejects_ambiguous_identity_or_version(field, value):
    from anovel.canon.models import ExecutionTicket

    args = dict(
        project="p",
        branch="b",
        actor="owner",
        request_id="r",
        authorization_version=0,
        execution_version=0,
    )
    args[field] = value
    with pytest.raises(ValueError):
        ExecutionTicket(**args)
