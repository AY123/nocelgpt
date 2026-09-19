"""selection_policy.py — N100-014 consumer policy derived from W9 calibration.

This module turns the calibration summary into a concrete consumption policy:
decision dimensions can sort / choose; diagnostic dimensions may inspect but may
not gate alone; unreliable dimensions are disabled for selection.
"""
from __future__ import annotations

from .w9_calibration_summary import build_w9_selection_policy
from .serialization_utils import content_hash, dump_pretty_json

POLICY_KIND = "n100_selection_consumer_policy"
POLICY_VERSION = "1.0"


def build_selection_consumer_policy(project_root: str) -> dict:
    w9_policy = build_w9_selection_policy(project_root)
    policy = {
        "kind": POLICY_KIND,
        "version": POLICY_VERSION,
        "project_root": project_root,
        "status": w9_policy.get("status"),
        "decision_dimensions": w9_policy.get("decision_dimensions") or [],
        "diagnostic_dimensions": w9_policy.get("diagnostic_dimensions") or [],
        "unreliable_dimensions": w9_policy.get("unreliable_dimensions") or [],
        "blocked_dimensions": w9_policy.get("blocked_dimensions") or [],
        "trusted_dimensions": w9_policy.get("trusted_dimensions") or [],
        "consumption_rules": {
            "decision_may_sort": True,
            "decision_may_gate_with_human_authorization": True,
            "diagnostic_may_not_gate_alone": True,
            "unreliable_disabled": True,
            "publish_requires_human": True,
        },
    }
    policy["content_hash"] = content_hash({k: v for k, v in policy.items() if k != "content_hash"})
    return policy


def serialize_selection_consumer_policy(project_root: str) -> str:
    return dump_pretty_json(build_selection_consumer_policy(project_root)) + "\n"
