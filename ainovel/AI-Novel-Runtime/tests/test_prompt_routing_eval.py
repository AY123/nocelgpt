from runtime.prompt.routing import route_generation
from runtime.prompt.routing_eval import evaluate_routing


def test_routing_evaluation_reports_specialization():
    baseline = route_generation(
        model_id="gpt-5.4",
        provider="openai",
        task_type="ChapterDraft",
        prompt_version="1.0.0",
    )
    routed = route_generation(
        model_id="gpt-5.4",
        provider="openai",
        task_type="ChapterDraft",
        known_failure_mode="AI-tell and dash-aside leakage",
        prompt_version="1.0.0",
    )

    report = evaluate_routing(
        baseline=baseline,
        routed=routed,
        task_type="ChapterDraft",
        known_failure_mode="AI-tell and dash-aside leakage",
    )

    assert report.baseline_pack_id == baseline.constraint_pack_id
    assert report.routed_pack_id == routed.constraint_pack_id
    assert report.outcome in {"specialized", "routed", "no_change"}
    assert "baseline=" in report.rationale
    assert "routed=" in report.rationale
