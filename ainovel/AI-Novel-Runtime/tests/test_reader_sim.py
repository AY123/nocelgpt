import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.execution.reader_sim import (
    DEFAULT_PERSONAS,
    DEFAULT_COMMERCIAL_PERSONAS,
    COMMERCIAL_PERSONAS,
    PAY_INTEREST_BAR,
    LLMReaderSimulator,
    build_persona_prompt,
    commercial_reader_simulator,
    compare_simulations,
    llm_reader_simulator,
)


class PersonaModel:
    """Returns a per-persona verdict keyed by which persona the prompt names.
    Records prompts so we can assert each persona was simulated independently."""

    model_id = "persona-fake-v1"

    def __init__(self, by_persona):
        self.by_persona = by_persona
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        # find which persona this prompt is for
        verdict = {"satisfaction": 50, "would_continue": True, "expectations": []}
        for name, v in self.by_persona.items():
            if name in prompt:
                verdict = v
                break

        class _Out:
            pass
        o = _Out()
        o.text = json.dumps(verdict, ensure_ascii=False)
        o.model_id = "persona-fake-v1"
        return o


class BrokenModel:
    model_id = "broken-v1"

    def generate(self, prompt):
        raise RuntimeError("down")


class JunkModel:
    model_id = "junk-v1"

    def generate(self, prompt):
        class _Out:
            text = "不是JSON"
            model_id = "junk-v1"
        return _Out()


ARTIFACT = {"task_id": "TASK-00001", "body": "主角一章之内连续打脸三个反派，节奏极快。"}


def reader_schema() -> dict:
    path = (Path(__file__).resolve().parents[2]
            / "AI-Novel-Standard" / "contracts" / "reader-simulation.schema.json")
    return json.loads(path.read_text(encoding="utf-8"))


def test_each_persona_simulated_independently():
    model = PersonaModel({})
    sim = llm_reader_simulator(model)
    sim.review(ARTIFACT)
    # one prompt per default persona, each naming its own persona
    assert len(model.prompts) == len(DEFAULT_PERSONAS)
    for name, prompt in zip(DEFAULT_PERSONAS, model.prompts):
        assert name in prompt
        assert ARTIFACT["body"][:10] in prompt   # the prose reached the reader


def test_aggregate_reflects_persona_split():
    # 爽文党 loves it (continue), 剧情党 drops it.
    model = PersonaModel({
        "爽文党": {"satisfaction": 90, "would_continue": True, "expectations": ["继续打脸"]},
        "剧情党": {"satisfaction": 30, "would_continue": False,
                    "drop_reason": "无意义爽点降智", "expectations": ["给点伏笔"]},
    })
    sim = llm_reader_simulator(model, personas=("爽文党", "剧情党"))
    report = sim.review(ARTIFACT)
    agg = report.aggregate
    assert agg["mean_satisfaction"] == 60          # (90+30)/2
    assert agg["continue_rate"] == 50              # 1 of 2 continue
    assert agg["drop_personas"] == ["剧情党"]


def test_report_schema_valid_and_invariants():
    model = PersonaModel({})
    report = llm_reader_simulator(model).review(ARTIFACT)
    schema = reader_schema()
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(report.to_dict()))
    assert errors == [], [e.message for e in errors]
    d = report.to_dict()
    assert d["axis"] == "evaluative"
    assert d["gating"] is False
    assert d["comparison_only"] is True


def test_one_persona_degraded_does_not_kill_sim():
    sim = LLMReaderSimulator(JunkModel(), personas=("老白", "小白"))
    report = sim.review(ARTIFACT)
    # junk output degrades each persona but the sim still returns a valid report
    assert report.gating is False
    assert all(p["degraded"] for p in report.personas)
    assert report.judge_provenance["degraded"] is True


def test_broken_model_degrades_without_raising():
    sim = LLMReaderSimulator(BrokenModel(), personas=("老白",))
    report = sim.review(ARTIFACT)
    assert report.personas[0]["degraded"] is True
    assert report.gating is False


def test_compare_simulations_detects_improvement():
    before = {
        "personas": [
            {"name": "爽文党", "satisfaction": 40, "would_continue": False},
            {"name": "剧情党", "satisfaction": 50, "would_continue": True},
        ],
        "aggregate": {"mean_satisfaction": 45, "continue_rate": 50},
    }
    after = {
        "personas": [
            {"name": "爽文党", "satisfaction": 80, "would_continue": True},
            {"name": "剧情党", "satisfaction": 55, "would_continue": True},
        ],
        "aggregate": {"mean_satisfaction": 68, "continue_rate": 100},
    }
    cmp = compare_simulations(before, after)
    assert cmp["gating"] is False
    assert cmp["comparison_only"] is True
    assert cmp["verdict"] == "improved"
    assert cmp["per_persona_delta"]["爽文党"] == 40
    assert cmp["newly_retained"] == ["爽文党"]
    assert cmp["mean_satisfaction_delta"] == 23


def test_compare_simulations_detects_regression():
    before = {
        "personas": [{"name": "剧情党", "satisfaction": 70, "would_continue": True}],
        "aggregate": {"mean_satisfaction": 70, "continue_rate": 100},
    }
    after = {
        "personas": [{"name": "剧情党", "satisfaction": 40, "would_continue": False}],
        "aggregate": {"mean_satisfaction": 40, "continue_rate": 0},
    }
    cmp = compare_simulations(before, after)
    assert cmp["verdict"] == "regressed"
    assert cmp["newly_dropped"] == ["剧情党"]


def test_simulator_drops_into_reviewer_seam():
    # LLMReaderSimulator has .reviewer_id + .review(artifact, package), matching
    # the DraftReviewer protocol so it can ride execute/refine unchanged.
    sim = llm_reader_simulator(PersonaModel({}))
    assert hasattr(sim, "reviewer_id")
    report = sim.review(ARTIFACT, {"task": {}, "context": {}})
    assert report.reviewer == "reader-simulator-v1"


def test_prompt_asks_for_roleplay_not_editing():
    prompt = build_persona_prompt("老白", ARTIFACT)
    assert "老白" in prompt
    assert "读者" in prompt
    assert "would_continue" in prompt
    assert "编辑" in prompt   # explicitly tells it NOT to act as an editor


# --------------------------------------------------------------------------- #
# v2 (roadmap 4.4) — six fixed COMMERCIAL personas + pay/continue signals      #
# --------------------------------------------------------------------------- #
def test_commercial_panel_is_six_fixed_pay_behavior_personas():
    assert len(DEFAULT_COMMERCIAL_PERSONAS) == 6
    assert set(DEFAULT_COMMERCIAL_PERSONAS) == set(COMMERCIAL_PERSONAS)
    # distinct from the appetite panel — no overlap
    assert set(DEFAULT_COMMERCIAL_PERSONAS).isdisjoint(set(DEFAULT_PERSONAS))


def test_commercial_simulator_uses_commercial_panel_and_v2_id():
    model = PersonaModel({})
    sim = commercial_reader_simulator(model)
    sim.review(ARTIFACT)
    assert len(model.prompts) == 6
    for name, prompt in zip(DEFAULT_COMMERCIAL_PERSONAS, model.prompts):
        assert name in prompt
        assert COMMERCIAL_PERSONAS[name][:8] in prompt   # its pay-behavior desc
    assert sim.reviewer_id == "commercial-reader-simulator-v2"


def test_prompt_requests_pay_and_continue_probability():
    prompt = build_persona_prompt("首订党", ARTIFACT)
    assert "首订党" in prompt
    assert "pay_probability" in prompt
    assert "continue_probability" in prompt


def test_pay_probability_parsed_and_aggregated():
    model = PersonaModel({
        "首订党": {"satisfaction": 80, "would_continue": True,
                    "continue_probability": 90, "pay_probability": 70},
        "白嫖党": {"satisfaction": 60, "would_continue": True,
                    "continue_probability": 65, "pay_probability": 20,
                    "drop_reason": "免费能看就不订"},
    })
    report = commercial_reader_simulator(
        model, personas=("首订党", "白嫖党")).review(ARTIFACT)
    agg = report.aggregate
    assert agg["mean_pay_probability"] == 45           # (70+20)/2
    assert agg["mean_continue_probability"] == 78       # round((90+65)/2)=78
    # only 首订党 clears the soft pay bar
    assert agg["pay_personas"] == ["首订党"]
    per = {p["name"]: p for p in report.personas}
    assert per["首订党"]["pay_probability"] == 70


def test_report_with_pay_signals_validates_against_v11_schema():
    model = PersonaModel({
        n: {"satisfaction": 70, "would_continue": True,
            "continue_probability": 75, "pay_probability": 60}
        for n in DEFAULT_COMMERCIAL_PERSONAS
    })
    report = commercial_reader_simulator(model).review(ARTIFACT)
    schema = reader_schema()
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(report.to_dict()))
    assert errors == [], [e.message for e in errors]
    # invariants unchanged by v2
    d = report.to_dict()
    assert d["gating"] is False and d["comparison_only"] is True


def test_appetite_panel_omits_pay_aggregate_when_no_pay_reported():
    # A v1-style output (no pay_probability key) must NOT be counted as 0-pay.
    model = PersonaModel({
        "老白": {"satisfaction": 70, "would_continue": True},   # no pay field
    })
    report = llm_reader_simulator(model, personas=("老白",)).review(ARTIFACT)
    assert "mean_pay_probability" not in report.aggregate
    assert "pay_probability" not in report.personas[0]
    # continue_probability is still backfilled from would_continue
    assert report.personas[0]["continue_probability"] == 80


def test_compare_detects_pay_loss_even_when_reader_stays():
    # A rewrite where the reader keeps reading but drops below the pay bar.
    before = {
        "personas": [{"name": "追订党", "satisfaction": 70, "would_continue": True,
                      "continue_probability": 80, "pay_probability": 65,
                      "degraded": False}],
        "aggregate": {"mean_satisfaction": 70, "continue_rate": 100,
                      "mean_continue_probability": 80, "mean_pay_probability": 65},
    }
    after = {
        "personas": [{"name": "追订党", "satisfaction": 68, "would_continue": True,
                      "continue_probability": 78, "pay_probability": 30,
                      "degraded": False}],
        "aggregate": {"mean_satisfaction": 68, "continue_rate": 100,
                      "mean_continue_probability": 78, "mean_pay_probability": 30},
    }
    cmp = compare_simulations(before, after)
    assert cmp["newly_dropped"] == []                  # still reading
    assert cmp["newly_pay_lost"] == ["追订党"]          # but stopped paying
    assert cmp["mean_pay_probability_delta"] == -35
    assert cmp["mean_continue_probability_delta"] == -2
    assert cmp["gating"] is False and cmp["comparison_only"] is True


def test_pay_bar_is_configurable_and_threads_to_aggregate():
    # 追订党 pay 45 is BELOW the default bar (50) but ABOVE a custom bar (40).
    model = PersonaModel({
        "追订党": {"satisfaction": 70, "would_continue": True,
                    "continue_probability": 80, "pay_probability": 45},
    })
    default = commercial_reader_simulator(
        model, personas=("追订党",)).review(ARTIFACT)
    assert default.aggregate["pay_personas"] == []          # 45 < 50
    lower = commercial_reader_simulator(
        model, personas=("追订党",), pay_bar=40).review(ARTIFACT)
    assert lower.aggregate["pay_personas"] == ["追订党"]     # 45 >= 40
    assert PAY_INTEREST_BAR == 50                            # default unchanged


def test_compare_pay_bar_matches_crossing_detection():
    before = {
        "personas": [{"name": "追订党", "satisfaction": 70, "would_continue": True,
                      "pay_probability": 60, "degraded": False}],
        "aggregate": {"mean_satisfaction": 70, "continue_rate": 100,
                      "mean_pay_probability": 60},
    }
    after = {
        "personas": [{"name": "追订党", "satisfaction": 72, "would_continue": True,
                      "pay_probability": 45, "degraded": False}],
        "aggregate": {"mean_satisfaction": 72, "continue_rate": 100,
                      "mean_pay_probability": 45},
    }
    # default bar 50: 60 -> 45 crosses
    assert compare_simulations(before, after)["newly_pay_lost"] == ["追订党"]
    # custom bar 40: 45 stays above -> no crossing
    assert compare_simulations(before, after, pay_bar=40)["newly_pay_lost"] == []


def test_compare_without_pay_signals_stays_v1_shaped():
    # An appetite-only comparison never emits pay deltas; newly_pay_lost is empty.
    before = {
        "personas": [{"name": "小白", "satisfaction": 50, "would_continue": True}],
        "aggregate": {"mean_satisfaction": 50, "continue_rate": 100},
    }
    after = {
        "personas": [{"name": "小白", "satisfaction": 60, "would_continue": True}],
        "aggregate": {"mean_satisfaction": 60, "continue_rate": 100},
    }
    cmp = compare_simulations(before, after)
    assert cmp["newly_pay_lost"] == []
    assert "mean_pay_probability_delta" not in cmp
    assert "mean_continue_probability_delta" not in cmp
    assert cmp["verdict"] == "improved"
