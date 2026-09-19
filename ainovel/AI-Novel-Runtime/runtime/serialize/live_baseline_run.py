"""live_baseline_run.py — fixed live baseline run helpers.

This module standardizes the five-chapter baseline execution parameters so a
caller can run the same live baseline repeatedly with predictable accounting and
reporting. It does not itself call a model; orchestration stays in `run_serial`
or the CLI.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

BASELINE_5CH_ID = "LIVE-5CH-001"
BASELINE_3CH_ID = "LIVE-3CH-001"
BASELINE_5CH_CHAPTERS = 5
BASELINE_3CH_CHAPTERS = 3
BASELINE_5CH_BUDGET_CNY = 20.0
BASELINE_3CH_BUDGET_CNY = 15.0
BASELINE_5CH_PROMPT_VERSION = "6.0.0"
BASELINE_5CH_MODEL_PROVIDER = "deepseek"
BASELINE_5CH_MODEL_ID = "deepseek-v4-pro"


@dataclass(frozen=True)
class LiveBaselineRunConfig:
    project_path: str
    standard_root: str
    schema_dir: str
    out_dir: str
    prompt_version: str = BASELINE_5CH_PROMPT_VERSION
    max_chapters: int = BASELINE_5CH_CHAPTERS
    budget_limit: float = BASELINE_5CH_BUDGET_CNY
    model_provider: str = BASELINE_5CH_MODEL_PROVIDER
    model_id: str = BASELINE_5CH_MODEL_ID
    commercial: bool = False
    reviewer: str = "unanchored"
    scene_planner: bool = False
    hygiene: bool = False
    originality: bool = True
    replay: bool = True
    manifest: bool = True

    def to_cli_args(self) -> list[str]:
        args = [
            "serial", "run",
            "--project", self.project_path,
            "--standard-root", self.standard_root,
            "--schema-dir", self.schema_dir,
            "--out", self.out_dir,
            "--prompt-version", self.prompt_version,
            "--max-chapters", str(self.max_chapters),
            "--budget-limit", str(self.budget_limit),
            "--model-provider", self.model_provider,
            "--model-id", self.model_id,
            "--reviewer", self.reviewer,
        ]
        if self.commercial:
            args.append("--commercial")
        if self.scene_planner:
            args.append("--scene-planner")
        if self.hygiene:
            args.append("--hygiene")
        if not self.originality:
            args.append("--no-originality")
        if not self.manifest:
            args.append("--no-manifest")
        return args


def build_live_baseline_config(*,
                               project_path: str,
                               standard_root: str,
                               schema_dir: str,
                               out_dir: str,
                               prompt_version: str = BASELINE_5CH_PROMPT_VERSION,
                               budget_limit: float = BASELINE_5CH_BUDGET_CNY,
                               model_provider: str = BASELINE_5CH_MODEL_PROVIDER,
                               model_id: str = BASELINE_5CH_MODEL_ID,
                               reviewer: str = "unanchored") -> LiveBaselineRunConfig:
    return LiveBaselineRunConfig(
        project_path=project_path,
        standard_root=standard_root,
        schema_dir=schema_dir,
        out_dir=out_dir,
        prompt_version=prompt_version,
        budget_limit=budget_limit,
        model_provider=model_provider,
        model_id=model_id,
        reviewer=reviewer,
    )
