import json

from runtime.execution.genesis_pairwise_judge import GENESIS_DIMS
from runtime.outline.tournament import run_outline_tournament


def _response(winner: str) -> str:
    return json.dumps({
        dim: {"winner": winner, "evidence": f"evidence-{dim}"}
        for dim in GENESIS_DIMS
    })


class _RankModel:
    provider = "fake"

    def __init__(self, model_id: str, *, reverse: bool = False):
        self.model_id = model_id
        self.reverse = reverse
        self.prompts = []

    def generate(self, prompt: str):
        self.prompts.append(prompt)
        left = json.loads(prompt.split("<<<A>>>", 1)[1].split("<<<END A>>>", 1)[0])
        right = json.loads(prompt.split("<<<B>>>", 1)[1].split("<<<END B>>>", 1)[0])
        left_rank = left["rank"]
        right_rank = right["rank"]
        left_wins = left_rank > right_rank
        if self.reverse:
            left_wins = not left_wins
        text = _response("A" if left_wins else "B")
        return type("Out", (), {"text": text, "model_id": self.model_id})()


def _candidates(order=("A", "B", "C")):
    ranks = {"A": 1, "B": 2, "C": 3}
    return [{"id": candidate_id, "proposal": {"rank": ranks[candidate_id]}}
            for candidate_id in order]


def test_outline_tournament_archives_each_judge_and_third_candidate_wins():
    model = _RankModel("rank-v1")
    out = run_outline_tournament(
        _candidates(), judge_models=[("fake:rank-v1", model)])

    assert out["kind"] == "outline_tournament"
    assert out["gating"] is False
    assert out["comparison_only"] is True
    assert out["calibrates"] is False
    assert out["human_authority"] is True
    assert out["winner"] == "C"
    result = out["judges"][0]["result"]
    assert result["summary"]["n_pairs"] == 3
    assert result["summary"]["per_candidate"]["C"]["match_wins"] == 2
    assert result["summary"]["position_consistency_rate"] == 1.0
    assert len(model.prompts) == 6
    assert out["judges"][0]["acceptance"] == {
        "expected_pairs": 3,
        "completed_pairs": 3,
        "expected_calls": 6,
        "completed_calls": 6,
        "n_degraded": 0,
        "call_error_count": 0,
        "position_consistency_rate": 1.0,
        "passed": True,
    }
    assert out["summary"]["all_judges_passed_acceptance"] is True


def test_input_order_does_not_change_real_candidate_winner():
    first = run_outline_tournament(
        _candidates(("A", "B", "C")),
        judge_models=[("fake:rank-v1", _RankModel("rank-v1"))],
    )
    permuted = run_outline_tournament(
        _candidates(("C", "A", "B")),
        judge_models=[("fake:rank-v1", _RankModel("rank-v1"))],
    )
    assert first["winner"] == permuted["winner"] == "C"


def test_provider_winner_disagreement_requires_human_and_has_no_winner():
    out = run_outline_tournament(
        _candidates(),
        judge_models=[
            ("fake:high", _RankModel("high")),
            ("fake:low", _RankModel("low", reverse=True)),
        ],
    )
    assert out["winner"] is None
    assert out["summary"]["provider_winners"] == {
        "fake:high": "C", "fake:low": "A"}
    assert out["summary"]["provider_disagreements"][0]["kind"] == "winner_disagreement"
    assert {item["candidate_hash"] for item in out["judges"]} == {out["candidate_hash"]}


def test_no_judge_is_explicitly_not_a_fake_lm_tournament():
    out = run_outline_tournament(_candidates(), judge_models=[])
    assert out["judges"] == []
    assert out["winner"] is None
    assert out["summary"]["all_complete"] is False
    assert out["summary"]["all_judges_passed_acceptance"] is False
    assert out["outline_qa"]["status"] == "not_model_integrated"


class _PositionBiasedModel:
    provider = "fake"
    model_id = "position-biased"

    def generate(self, prompt):
        return type("Out", (), {
            "text": _response("A"), "model_id": self.model_id})()


def test_position_consistency_below_threshold_cannot_produce_consensus_winner():
    out = run_outline_tournament(
        _candidates(),
        judge_models=[("fake:position-biased", _PositionBiasedModel())],
    )
    assert out["judges"][0]["acceptance"]["position_consistency_rate"] == 0.0
    assert out["judges"][0]["acceptance"]["passed"] is False
    assert out["winner"] is None
    assert out["summary"]["all_judges_passed_acceptance"] is False
