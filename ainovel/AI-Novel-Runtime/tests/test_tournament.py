import json

from runtime.execution.genesis_pairwise_judge import GENESIS_DIMS
from runtime.execution.tournament import run_tournament


def _response(winner):
    return json.dumps({dim: {"winner": winner, "evidence": "x"}
                       for dim in GENESIS_DIMS})


class _QueuedModel:
    provider = "fake"
    model_id = "queued"

    def __init__(self, winners):
        self.winners = iter(winners)

    def generate(self, prompt):
        return type("Out", (), {"text": _response(next(self.winners)),
                                  "model_id": self.model_id})()


def _candidates():
    return [{"id": value, "proposal": {"title": value}} for value in "ABC"]


def test_cycle_is_a_true_candidate_tie_with_no_advisory_winner():
    # A beats B; C beats A; B beats C. Each real candidate has one match win.
    result = run_tournament(
        _candidates(), _QueuedModel(["A", "B", "B", "A", "A", "B"]))

    assert result.candidates == ["A", "B", "C"]
    assert len(result.matches) == 3
    assert result.summary["winner"] is None
    assert {key: value["match_wins"]
            for key, value in result.summary["per_candidate"].items()} == {
                "A": 1, "B": 1, "C": 1}
    assert result.gating is False
    assert result.comparison_only is True
