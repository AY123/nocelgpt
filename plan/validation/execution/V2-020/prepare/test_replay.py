"""Offline preparation controls; these are not prose-understanding or reader tests.

The test-only receipt rebinding lets negative controls reach the typed reducer
and span checks. Production replay has no auto-review/rebinding operation.
"""

import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PREPARE = Path(__file__).resolve().parent
ROOT = PREPARE.parents[4]
SAMPLE = PREPARE / "samples" / "urban"
SPEC = importlib.util.spec_from_file_location(
    "prepare_draft_replay", PREPARE / "replay.py"
)
assert SPEC is not None and SPEC.loader is not None
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def write_json(path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def rebind_test_receipt(case):
    """Fabricated test binding only; this helper is not an approval source."""
    sample, review = case
    receipt = tool.load_json(review)
    receipt["sample_sha256"] = hashlib.sha256(sample.read_bytes()).hexdigest()
    write_json(review, receipt)


@pytest.fixture
def case(tmp_path):
    directory = tmp_path / "sample"
    shutil.copytree(SAMPLE, directory)
    return directory / "replay.json", directory / "review.json"


def run(case):
    return tool.replay(*case, repository_root=ROOT)


def mutate(case, change, *, rebind=True):
    sample = tool.load_json(case[0])
    change(sample)
    write_json(case[0], sample)
    if rebind:
        rebind_test_receipt(case)


def reject(case, change, *, rebind=True, match=None):
    mutate(case, change, rebind=rebind)
    with pytest.raises(tool.ReplayError, match=match):
        run(case)


def field(input_value, subject, predicate):
    return next(
        fact
        for fact in input_value["visible_facts"]
        if fact["subject"]["local_id"] == subject and fact["predicate"] == predicate
    )


def test_three_chapters_replay_preserves_money_and_separates_count_from_release(case):
    report = run(case)
    steps = report["steps"]
    assert [step["chapter"] for step in steps] == [1, 2, 3]
    assert [step["changed_fact_count"] for step in steps] == [2, 0, 1]
    assert steps[0]["after_sha256"] == steps[1]["before_sha256"]
    assert steps[1]["before_sha256"] == steps[1]["after_sha256"]
    assert steps[1]["after_sha256"] == steps[2]["before_sha256"]
    writer = report["next_writer_input"]
    assert writer["kind"] == "WINDOW_DRAFT_CONTEXT"
    assert writer["chapter"] == 4
    assert (
        field(writer, "account-factory", "ext:urban.business:account.balance_minor")[
            "state"
        ]["value"]
        == 17700000
    )
    assert (
        field(writer, "account-inspection", "ext:urban.business:account.balance_minor")[
            "state"
        ]["value"]
        == 300000
    )
    assert (
        field(writer, "stock", "ext:urban.business:resource.quantity")["state"]["value"]
        == 30
    )
    assert field(writer, "factory", "defect_report_published")["state"]["value"] is True
    assert any(fact["id"]["local_id"] == "truth" for fact in writer["visible_facts"])
    assert "待可靠复核" in writer["notes"]["inventory_qualification"]
    assert "验收仍待核" in writer["notes"]["report_receipt_acceptance"]
    body = (case[0].parent / "chapter3.txt").read_bytes().decode("utf-8")
    ending = writer["actual_ending"]
    assert body[ending["start"] : ending["end"]] == ending["quote"]
    assert ending["end"] == len(body)


def test_prefix_two_chapters_keeps_author_secret_out_of_writer_input(case):
    mutate(case, lambda sample: sample["steps"].pop())
    report = run(case)
    writer = report["next_writer_input"]
    assert writer["chapter"] == 3
    assert not any(
        fact["id"]["local_id"] == "truth" for fact in writer["visible_facts"]
    )
    serialized = json.dumps(writer, ensure_ascii=False)
    assert "旧设备校准失效" not in serialized
    assert (
        writer["notes"]["private_knowledge"]
        == tool.load_json(case[0])["initial_notes"]["private_knowledge"]
    )
    assert (
        field(writer, "factory", "defect_report_published")["state"]["value"] is False
    )


def test_repeat_replay_is_deterministic_and_leaves_inputs_unchanged(case):
    before = {
        path.name: path.read_bytes()
        for path in case[0].parent.iterdir()
        if path.is_file()
    }
    assert run(case) == run(case)
    after = {
        path.name: path.read_bytes()
        for path in case[0].parent.iterdir()
        if path.is_file()
    }
    assert before == after


@pytest.mark.parametrize("suffix", ["新", "\n", "\r\n"])
def test_candidate_byte_change_invalidates_old_review(case, suffix):
    body = case[0].parent / "chapter2.txt"
    body.write_bytes(body.read_bytes() + suffix.encode("utf-8"))
    with pytest.raises(tool.ReplayError):
        run(case)


@pytest.mark.parametrize(
    "name", ["before_sha256", "after_sha256", "previous_body_sha256"]
)
def test_chain_reset_or_different_baseline_is_rejected(case, name):
    reject(case, lambda sample: sample["steps"][1].__setitem__(name, "0" * 64))


def test_known_initial_balance_cannot_replace_preceding_draft_state(case):
    def change(sample):
        sample["steps"][1]["before_sha256"] = sample["steps"][0]["before_sha256"]

    reject(case, change, match="complete preceding draft state mismatch")


def test_changed_delta_is_not_covered_by_old_mapping_review(case):
    reject(
        case,
        lambda sample: sample["steps"][0]["delta"]["operations"][0].__setitem__(
            "value", 17700001
        ),
        rebind=False,
    )


@pytest.mark.parametrize(
    "chapter,field,value",
    [
        (1, "private_knowledge", "赵川此前不知道真因"),
        (1, "inquiry_receipt", "客户已经读完并接受"),
        (2, "inventory_qualification", "库存仍有30件，因此全部已合格放行"),
    ],
)
def test_unreviewed_knowledge_receipt_or_qualification_note_cannot_reuse_mapping(
    case, chapter, field, value
):
    def change(sample):
        notes = sample["steps"][chapter]["notes_after"]
        notes[field] = value

    reject(case, change, rebind=False)


def test_one_sided_payment_fails_actual_business_conservation(case):
    def change(sample):
        step = sample["steps"][0]
        step["delta"]["operations"].pop()
        step["operation_evidence"].pop()

    reject(case, change, match="conserved")


def test_one_fen_imbalance_fails_even_with_fresh_test_mapping_binding(case):
    reject(
        case,
        lambda sample: sample["steps"][0]["delta"]["operations"][0].__setitem__(
            "value", 17700001
        ),
        match="conserved",
    )


def test_repeated_payment_uses_stale_precondition_and_is_rejected(case):
    def change(sample):
        step = sample["steps"][2]
        delta = copy.deepcopy(sample["steps"][0]["delta"])
        delta["source_id"]["local_id"] = "repeat-payment-candidate"
        body = (case[0].parent / step["body"]["path"]).read_bytes().decode("utf-8")
        quote = "那笔还没批下来的不能算钱。就按账上十七万七，工资和交货怎么排，你现在跟我算。"
        start = body.index(quote)
        step["delta"] = delta
        step["operation_evidence"] = []
        for operation in delta["operations"]:
            operation["evidence"]["source_id"] = dict(delta["source_id"])
            operation["evidence"]["position"]["chapter"] = 3
            operation["evidence"]["evidence_ref"] = (
                f"chapter3.txt;sha256={step['body']['sha256']}"
            )
            step["operation_evidence"].append(
                {
                    "operation_id": operation["id"]["local_id"],
                    "start": start,
                    "end": start + len(quote),
                    "quote": quote,
                }
            )

    reject(case, change, match="precondition")


def test_stale_fact_revision_is_rejected(case):
    reject(
        case,
        lambda sample: sample["steps"][0]["delta"]["operations"][0][
            "expected"
        ].__setitem__("revision", 1),
        match="precondition",
    )


def test_cross_project_delta_is_rejected(case):
    reject(
        case,
        lambda sample: sample["steps"][0]["delta"]["id"].__setitem__(
            "project", "other-project"
        ),
    )


def test_changed_parent_is_rejected(case):
    reject(
        case,
        lambda sample: sample["steps"][0]["delta"].__setitem__(
            "parent_ref", "sha256:" + "b" * 64
        ),
    )


def test_wrong_operation_source_is_rejected(case):
    reject(
        case,
        lambda sample: sample["steps"][0]["delta"]["operations"][0]["evidence"][
            "source_id"
        ].__setitem__("local_id", "different-candidate"),
    )


def test_wrong_operation_chapter_is_rejected(case):
    reject(
        case,
        lambda sample: sample["steps"][0]["delta"]["operations"][0]["evidence"][
            "position"
        ].__setitem__("chapter", 2),
    )


def test_missing_typed_change_quote_is_rejected(case):
    reject(case, lambda sample: sample["steps"][0]["operation_evidence"].pop())


def test_unmatched_extra_typed_change_quote_is_rejected(case):
    reject(
        case,
        lambda sample: sample["steps"][0]["operation_evidence"].append(
            dict(sample["steps"][0]["operation_evidence"][0])
        ),
    )


@pytest.mark.parametrize("location", ["ending", "operation_evidence", "notes_evidence"])
def test_inexact_quotes_are_rejected(case, location):
    def change(sample):
        step = sample["steps"][0]
        span = step[location] if location == "ending" else step[location][0]
        span["quote"] += "并不存在的原文"

    reject(case, change)


@pytest.mark.parametrize("start", [True, -1, "0"])
def test_malformed_span_offsets_are_rejected(case, start):
    reject(
        case, lambda sample: sample["steps"][0]["ending"].__setitem__("start", start)
    )


def test_empty_ending_is_rejected(case):
    def change(sample):
        ending = sample["steps"][0]["ending"]
        ending["start"] = ending["end"]
        ending["quote"] = ""

    reject(case, change)


def test_real_quote_that_is_not_actual_ending_is_rejected(case):
    def change(sample):
        step = sample["steps"][0]
        body = (case[0].parent / step["body"]["path"]).read_bytes().decode("utf-8")
        step["ending"] = {"start": 0, "end": 4, "quote": body[:4]}

    reject(case, change)


def test_changed_notes_need_current_chapter_evidence(case):
    reject(case, lambda sample: sample["steps"][0]["notes_evidence"].clear())


def test_notes_cannot_silently_disappear(case):
    reject(
        case,
        lambda sample: sample["steps"][1]["notes_after"].pop(
            next(iter(sample["initial_notes"]))
        ),
    )


def test_reader_boundary_arrival_alone_does_not_disclose_hidden_fact(case):
    mutate(case, lambda sample: sample["steps"][2]["revealed_facts"].clear())
    writer = run(case)["next_writer_input"]
    assert not any(
        fact["id"]["local_id"] == "truth" for fact in writer["visible_facts"]
    )


def test_reveal_before_frozen_reader_boundary_is_rejected(case):
    def change(sample):
        step = sample["steps"][0]
        step["revealed_facts"] = [
            {
                **step["ending"],
                "fact_id": sample["steps"][2]["revealed_facts"][0]["fact_id"],
            }
        ]

    reject(case, change, match="before reader boundary")


def test_wrong_story_revision_is_rejected(case):
    reject(case, lambda sample: sample["story"].__setitem__("sha256", "0" * 64))


@pytest.mark.parametrize(
    "document",
    [
        '{"duplicate":1,"duplicate":2}',
        '{"x":NaN}',
        '{"x":Infinity}',
        '{"x":1e400}',
        '{"x":-1e400}',
        '{"x":',
    ],
)
def test_strict_json_rejects_ambiguous_or_nonfinite_input(tmp_path, document):
    path = tmp_path / "bad.json"
    path.write_text(document, encoding="utf-8")
    with pytest.raises(ValueError):
        tool.load_json(path)


def test_review_cannot_be_only_self_declared_reviewed(case):
    write_json(case[1], {"status": "REVIEWED"})
    with pytest.raises(tool.ReplayError):
        run(case)


@pytest.mark.parametrize("missing", ["sample_sha256", "reviewer"])
def test_missing_mapping_review_field_fails_closed(case, missing):
    review = tool.load_json(case[1])
    review.pop(missing)
    write_json(case[1], review)
    with pytest.raises(tool.ReplayError):
        run(case)


def test_invalid_utf8_mapping_review_fails_closed(case):
    case[1].write_bytes(b"\xff\xfe")
    with pytest.raises(tool.ReplayError):
        run(case)


@pytest.mark.parametrize(
    "key,value",
    [
        ("reviewer", ""),
        ("decision", "APPROVED_FOR_CANON"),
        ("review_basis", "HUMAN_GOLD"),
        ("limitations", []),
    ],
)
def test_missing_or_inapplicable_mapping_review_is_rejected(case, key, value):
    review = tool.load_json(case[1])
    review[key] = value
    write_json(case[1], review)
    with pytest.raises(tool.ReplayError):
        run(case)


def cli(case, output):
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(PREPARE / "replay.py"),
            "--sample",
            str(case[0]),
            "--review",
            str(case[1]),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_replays_into_fresh_directory_and_outputs_are_deterministic(case, tmp_path):
    first, second = tmp_path / "run-one", tmp_path / "run-two"
    for output in (first, second):
        result = cli(case, output)
        assert result.returncode == 0, result.stderr + result.stdout
        assert output.is_dir()
    contents = lambda output: {
        str(path.relative_to(output)): path.read_bytes()
        for path in output.rglob("*")
        if path.is_file()
    }
    assert contents(first) == contents(second)
    assert contents(first)


def test_cli_failure_does_not_export_partial_success(case, tmp_path):
    (case[0].parent / "chapter2.txt").write_text("外部改稿", encoding="utf-8")
    output = tmp_path / "rejected"
    result = cli(case, output)
    assert result.returncode != 0
    assert not output.exists()


def test_cli_refuses_overwriting_existing_output(case, tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "KEEP.txt"
    sentinel.write_text("user-owned", encoding="utf-8")
    result = cli(case, output)
    assert result.returncode != 0
    assert list(output.iterdir()) == [sentinel]
    assert sentinel.read_text(encoding="utf-8") == "user-owned"
