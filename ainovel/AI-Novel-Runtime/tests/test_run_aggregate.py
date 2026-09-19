"""test_run_aggregate.py — run aggregate + the compare/select policy flow.

NOTE on the policy tests below: they used to read the W9 selection policy from
the REPO root, which promoted four dimensions to `decision` on stub evidence (40
of its 43 scored samples hold a defect label, not a chapter body). The mechanism
under test is real, so it now runs against a synthetic fixture project with real
sample bodies — the assertions are unchanged, only the evidence they stand on is.
See tests/test_w9_policy.py for the calibration downgrade itself.
"""
import sys
from pathlib import Path

from runtime.serialize.run_aggregate import build_run_aggregate
from runtime.serialize.w9_policy import build_w9_selection_policy
from runtime.serialize import build_version_comparison, build_version_selection, validate_version_selection

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_w9_policy import _fixture_project  # a project whose W9 evidence is real


def _comparison_input(root: str):
    return [
        {
            "version_id": "v1",
            "project_path": root,
            "dimension_scores": {
                "opening_hook": 5,
                "conflict_progression": 4,
                "paying_intent": 4,
                "continue_intent": 5,
                "chapter_goal": 1,
            },
        },
        {
            "version_id": "v2",
            "project_path": root,
            "dimension_scores": {
                "opening_hook": 3,
                "conflict_progression": 3,
                "paying_intent": 2,
                "continue_intent": 4,
                "chapter_goal": 5,
            },
        },
    ]


def test_run_aggregate_embeds_selection_policy(tmp_path):
    agg = build_run_aggregate(
        project_path=tmp_path,
        standard_root="/tmp/standard",
        prompt_version="6.0.0",
        model_provider="deepseek",
        model_id="deepseek-v4-pro",
        budget_limit=100.0,
        launch_report_id="L30R-0000",
        run_manifest_ref="registry/derived/run-manifests/run-0000.json",
        notes="selection",
    )

    assert agg["run_summary"].get("kind") == "30ch_launch_summary"
    assert "plan" in agg["run_summary"]


def test_selection_policy_helper_has_expected_buckets(tmp_path):
    policy = build_w9_selection_policy(str(_fixture_project(tmp_path)))
    assert policy["kind"] == "w9_selection_policy"
    assert set(policy["decision_dimensions"]) == {"opening_hook", "conflict_progression", "paying_intent", "continue_intent"}
    assert "chapter_goal" in policy["diagnostic_dimensions"]
    assert policy["unreliable_dimensions"] == []
    assert "chapter_goal" in policy["blocked_dimensions"]


def test_compare_select_manifest_policy_flow(tmp_path):
    root = str(_fixture_project(tmp_path))
    comparison = build_version_comparison(chapter_id="CH-00001",
                                          versions=_comparison_input(root))
    selection = build_version_selection(chapter_id="CH-00001", comparison=comparison,
                                        project_path=root)

    assert comparison["winner"] == "v1"
    assert comparison["versions"][0]["decision_scores"]["opening_hook"] == 5
    assert "chapter_goal" not in comparison["versions"][0]["decision_scores"]
    assert selection["selected_version"] == "v1"
    assert selection["selection_policy"]["decision_scores"] == {
        "opening_hook": 5,
        "conflict_progression": 4,
        "paying_intent": 4,
        "continue_intent": 5,
    }
    assert selection["selection_policy"]["decision_score_mean"] == 4.5
    assert validate_version_selection(selection) == []


def test_run_aggregate_structure(tmp_path):
    agg = build_run_aggregate(
        project_path=tmp_path,
        standard_root="/tmp/standard",
        prompt_version="6.0.0",
        model_provider="deepseek",
        model_id="deepseek-v4-pro",
        budget_limit=100.0,
        launch_report_id="L30R-0001",
        run_manifest_ref="registry/derived/run-manifests/run-0001.json",
        notes="aggregate",
    )

    assert agg["kind"] == "run_aggregate"
    assert agg["run_summary"]["kind"] == "30ch_launch_summary"
    assert "archive_bridge" not in agg
    assert "content_hash" in agg


def test_run_inspect_serialized_keys(tmp_path):
    agg = build_run_aggregate(
        project_path=tmp_path,
        standard_root="/tmp/standard",
        prompt_version="6.0.0",
        model_provider="deepseek",
        model_id="deepseek-v4-pro",
        budget_limit=100.0,
        launch_report_id="L30R-0002",
        run_manifest_ref="registry/derived/run-manifests/run-0002.json",
        notes="inspect",
    )

    assert agg["project_path"] == str(tmp_path)
    assert agg["run_summary"]["kind"] == "30ch_launch_summary"
    assert isinstance(agg["content_hash"], str) and agg["content_hash"]
