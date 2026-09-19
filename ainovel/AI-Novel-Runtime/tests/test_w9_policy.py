"""test_w9_policy.py — the W9 dimension-grading facade.

This file used to assert `dimension_policy["decision"]` was non-empty against the
REPO's own golden set, and `opening_hook == "decision"`. Both passed only because
the golden set promoted four dimensions on stub evidence: 40 of its 43 scored
samples hold a 54-58 char defect label ("同义反复拖慢节奏") instead of a chapter
body, and 7 more have no body at all. So the test was encoding a FALSE
calibration as the contract.

Per the Schema-First rule, the test serves the honest contract, not the other way
round. The facade's MECHANISM (filter/classify) is now tested against a synthetic
fixture with real bodies, and the repo's own set is asserted to be DOWNGRADED —
which is what its evidence actually supports.
"""
from __future__ import annotations

import json
from pathlib import Path

from runtime.serialize.w9_policy import (
    build_w9_selection_policy,
    load_w9_dimension_policy,
    classify_w9_dimension,
    can_use_w9_dimension_for_decision,
    filter_w9_decision_scores,
)

ROOT = "/Users/angyang/Documents/xiaoshuo/AINovel"

# Long enough to clear MIN_REAL_BODY_CHARS: a body, not a label.
_PROSE = "他推开门，血腥味扑面而来。" * 30


def _fixture_project(root: Path, *, n_real: int = 6, body: str = _PROSE) -> Path:
    """A minimal project whose W9 results point at REAL sample bodies."""
    meta = root / "AI-Novel-Runtime" / "quality-golden-set" / "metadata"
    samples = root / "AI-Novel-Runtime" / "quality-golden-set" / "samples"
    meta.mkdir(parents=True, exist_ok=True)

    rows = []
    for i in range(1, n_real + 1):
        sid = f"QGS-{i:05d}"
        d = samples / sid
        d.mkdir(parents=True, exist_ok=True)
        (d / "body.txt").write_text(body, encoding="utf-8")
        # human vs reviewer scores that agree => a high correlation
        rows.append({
            "sample_id": sid,
            "kind": "reviewer_calibration_row",
            "sample_category": "positive",
            "decision_mode": "calibration",
            "body_ref": str(d / "body.txt"),
            "dimension_scores": {"opening_hook": i % 5 + 1, "chapter_goal": i % 4 + 1},
            "comparison": {"human_mean": {"opening_hook": i % 5 + 1,
                                          "chapter_goal": (i % 4 + 1) * 0.9}},
        })

    (meta / "w9-calibration-results.json").write_text(
        json.dumps({"kind": "w9_reviewer_calibration_results", "version": "1.0",
                    "status": "complete", "sample_count": n_real,
                    "results": rows, "skipped": []},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return root


def test_facade_grades_and_filters_when_evidence_is_real(tmp_path):
    """With enough real-bodied samples the facade promotes and filters normally."""
    proj = str(_fixture_project(tmp_path, n_real=6))

    policy = build_w9_selection_policy(proj)
    dimension_policy = load_w9_dimension_policy(proj)

    assert policy["kind"] == "w9_selection_policy"
    assert dimension_policy["decision"], "real evidence should support decision dims"
    assert classify_w9_dimension(proj, "opening_hook") == "decision"
    assert can_use_w9_dimension_for_decision(proj, "opening_hook") is True
    # a diagnostic dimension is never decision-eligible
    assert can_use_w9_dimension_for_decision(proj, "chapter_goal") is False
    # the filter keeps decision dims and drops the rest
    assert filter_w9_decision_scores(proj, {"opening_hook": 5, "chapter_goal": 1}) \
        == {"opening_hook": 5}


def test_label_only_samples_do_not_earn_decision_status(tmp_path):
    """Stub bodies must NOT promote a dimension, however well they correlate.

    This is the exact defect the repo's own golden set had: scoring a one-line
    defect label is not evidence that the reviewer agrees with humans on prose.
    """
    proj = str(_fixture_project(tmp_path, n_real=6, body="同义反复拖慢节奏"))

    dimension_policy = load_w9_dimension_policy(proj)

    assert dimension_policy["decision"] == set(), \
        "label-only samples must not promote any dimension to decision"
    assert can_use_w9_dimension_for_decision(proj, "opening_hook") is False
    # nothing survives the filter, so no score can drive an automatic choice
    assert filter_w9_decision_scores(proj, {"opening_hook": 5}) == {}


def test_repo_golden_set_is_honestly_downgraded():
    """The repo's own W9 set is stub-backed, so it must report as uncalibrated.

    Kept as an explicit assertion rather than deleted: if someone later "fixes"
    the wiring or backfills the set, this test is where the change must be
    justified — a silent return to four decision dimensions is the accident this
    guards against.
    """
    from runtime.serialize.w9_calibration_summary import build_w9_summary

    summary = build_w9_summary(ROOT)

    assert summary["status"] == "uncalibrated_insufficient_real_samples"
    assert summary["real_sample_count"] == 3       # only 3 real prose fragments
    assert summary["label_only_sample_count"] == 40
    assert summary["dimension_grading"]["decision"] == []
    assert summary["trusted_dimensions"] == []
    # the demoted four are recorded, not silently dropped
    assert summary["grading_downgraded"]["demoted_from_decision"] == [
        "conflict_progression", "continue_intent", "opening_hook", "paying_intent",
    ]
    # correlations are RETAINED for diagnosis — downgraded, not deleted
    assert summary["dimension_stats"]["opening_hook"]["correlation"] is not None
    assert summary["dimension_stats"]["opening_hook"]["level"] == "diagnostic"
    # and no consumer can pull a decision score out of it
    assert filter_w9_decision_scores(ROOT, {"opening_hook": 5}) == {}
