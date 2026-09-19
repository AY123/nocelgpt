import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.execution.pairwise_judge import (
    CHARACTER_DIMS,
    PairwiseComparison,
    aggregate_comparisons,
    build_pairwise_prompt,
    compare_character,
)

_SCHEMA = (Path(__file__).resolve().parents[1].parent
           / "AI-Novel-Standard" / "contracts" / "character-comparison.schema.json")


class SeqModel:
    """Returns queued raw outputs in order — one per generate() call. Records
    prompts so a test can assert both orderings were issued."""

    model_id = "seq-fake-v1"

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.i = 0
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        text = self.outputs[self.i]
        self.i += 1

        class _Out:
            pass
        o = _Out()
        o.text = text
        o.model_id = "seq-fake-v1"
        return o


class BrokenModel:
    model_id = "broken-v1"

    def generate(self, prompt):
        raise RuntimeError("down")


def _verdict(cc, cg):
    """A raw single-order judge output picking `cc` on consistency, `cg` on growth."""
    return json.dumps({
        "character_consistency": {"winner": cc, "evidence": "quote"},
        "character_growth": {"winner": cg, "evidence": "quote"},
    }, ensure_ascii=False)


def test_genuine_win_survives_the_swap():
    # Real A is better on both dims. order-1 (A first) => slot A wins ("A").
    # order-2 (B first, so A is the SECOND slot) => the judge, being honest,
    # picks the second slot ("B"). After flip-back both agree on real A.
    model = SeqModel([_verdict("A", "A"), _verdict("B", "B")])
    c = compare_character("bodyA", "bodyB", model)
    assert c.winner == "a"
    assert c.dimensions["character_consistency"]["verdict"] == "a"
    assert c.dimensions["character_growth"]["verdict"] == "a"
    # both orderings were issued
    assert len(model.prompts) == 2


def test_position_bias_cancels_to_tie():
    # A biased judge always picks the FIRST slot regardless of content. In the
    # real frame the two orderings then disagree, so every dim must tie.
    model = SeqModel([_verdict("A", "A"), _verdict("A", "A")])
    c = compare_character("bodyA", "bodyB", model)
    assert c.winner == "tie"
    for dim in CHARACTER_DIMS:
        assert c.dimensions[dim]["verdict"] == "tie"


def test_split_dimensions_make_overall_tie():
    # A wins consistency in both orders; B wins growth in both orders => 1-1 tie.
    model = SeqModel([_verdict("A", "B"), _verdict("B", "A")])
    c = compare_character("bodyA", "bodyB", model)
    assert c.dimensions["character_consistency"]["verdict"] == "a"
    assert c.dimensions["character_growth"]["verdict"] == "b"
    assert c.winner == "tie"


def test_model_failure_degrades_to_tie_never_raises():
    c = compare_character("a", "b", BrokenModel())
    assert c.winner == "tie"
    assert c.judge_provenance is not None and c.judge_provenance["degraded"] is True
    for dim in CHARACTER_DIMS:
        assert c.dimensions[dim]["verdict"] == "tie"


def test_unparseable_output_degrades():
    model = SeqModel(["not json", "still not json"])
    c = compare_character("a", "b", model)
    assert c.winner == "tie"
    assert c.judge_provenance["degraded"] is True


def test_structural_invariants_and_schema():
    model = SeqModel([_verdict("A", "A"), _verdict("B", "B")])
    c = compare_character("bodyA", "bodyB", model, label_a="deepened", label_b="baseline")
    d = c.to_dict()
    assert d["gating"] is False
    assert d["comparison_only"] is True
    assert d["calibrates"] is False
    assert d["axis"] == "evaluative"
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(d))
    assert not errors, errors


def test_aggregate_win_rate():
    # Two decisive A wins, one tie, one degraded.
    a_win = compare_character("A", "B", SeqModel([_verdict("A", "A"), _verdict("B", "B")]))
    a_win2 = compare_character("A", "B", SeqModel([_verdict("A", "A"), _verdict("B", "B")]))
    tie = compare_character("A", "B", SeqModel([_verdict("A", "A"), _verdict("A", "A")]))
    degraded = compare_character("A", "B", BrokenModel())
    agg = aggregate_comparisons([a_win, a_win2, tie, degraded])
    assert agg["overall"]["a"] == 2
    assert agg["overall"]["b"] == 0
    assert agg["n_degraded"] == 1
    assert agg["decisive_win_rate_a"] == 1.0
    assert agg["gating"] is False and agg["comparison_only"] is True


def test_prompt_contains_both_bodies():
    p = build_pairwise_prompt("ALPHA_BODY", "BETA_BODY")
    assert "ALPHA_BODY" in p and "BETA_BODY" in p
