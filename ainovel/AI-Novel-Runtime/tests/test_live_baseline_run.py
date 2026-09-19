from __future__ import annotations

from runtime.serialize.live_baseline_run import (
    BASELINE_5CH_BUDGET_CNY,
    BASELINE_5CH_CHAPTERS,
    BASELINE_5CH_ID,
    BASELINE_5CH_MODEL_ID,
    BASELINE_5CH_MODEL_PROVIDER,
    BASELINE_5CH_PROMPT_VERSION,
    build_live_baseline_config,
)


def test_live_baseline_run_config_and_cli_args():
    cfg = build_live_baseline_config(
        project_path="/tmp/project",
        standard_root="/tmp/standard",
        schema_dir="/tmp/schema",
        out_dir="/tmp/out",
    )
    args = cfg.to_cli_args()

    assert cfg.max_chapters == BASELINE_5CH_CHAPTERS
    assert cfg.budget_limit == BASELINE_5CH_BUDGET_CNY
    assert cfg.model_provider == BASELINE_5CH_MODEL_PROVIDER
    assert cfg.model_id == BASELINE_5CH_MODEL_ID
    assert cfg.prompt_version == BASELINE_5CH_PROMPT_VERSION
    assert BASELINE_5CH_ID == "LIVE-5CH-001"
    assert "--max-chapters" in args and "5" in args
    assert "--budget-limit" in args and str(BASELINE_5CH_BUDGET_CNY) in args
