"""launch_30ch.py — launch helpers for the 30 chapter baseline run."""
from __future__ import annotations

from .serialization_utils import content_hash


def build_30ch_launch_plan(*, project_path: str, standard_root: str, prompt_version: str,
                           model_provider: str, model_id: str, budget_limit: float) -> dict:
    plan = {
        "kind": "30ch_launch_plan",
        "version": "1.0",
        "project_path": project_path,
        "standard_root": standard_root,
        "prompt_version": prompt_version,
        "model_provider": model_provider,
        "model_id": model_id,
        "budget_limit": budget_limit,
        "chapter_target": 30,
    }
    plan["content_hash"] = content_hash(plan)
    return plan


def build_30ch_run_preset(*, project_path: str, standard_root: str, model_provider: str,
                          model_id: str, budget_limit: float = 0.0,
                          prompt_version: str = "10.0.0") -> dict:
    return {
        "project_path": project_path,
        "standard_root": standard_root,
        "prompt_version": prompt_version,
        "model_provider": model_provider,
        "model_id": model_id,
        "budget_limit": budget_limit,
        "max_chapters": 30,
        "long_arc": True,
        "vary_openings": True,
        "mandate": True,
        "speech": True,
        "commercial": False,
        "hygiene": False,
        "reviewer": "unanchored",
        "candidates": 1,
    }
