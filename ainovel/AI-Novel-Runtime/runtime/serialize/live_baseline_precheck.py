"""live_baseline_precheck.py — helpers for two-chapter live preflight runs.

A precheck is the minimal real-model smoke test before a five-chapter baseline:
2 chapters, fixed budget, manifest/report generation, and no publish side effects.
This module only builds the audit payloads; orchestration is still performed by
`run_serial` and the caller's CLI/runtime entrypoint.
"""
from __future__ import annotations

from typing import Optional

from .live_baseline_report import build_live_baseline_report

PRECHECK_BASELINE_ID = "LIVE-5CH-PRECHECK-2CH"


def build_precheck_environment(*, provider: str, model: str, prompt_version: str,
                               runtime_version: str) -> dict:
    return {
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "runtime_version": runtime_version,
    }


def build_precheck_report(*, project_path, status: str, environment: dict,
                          chapters: list[dict], failures: list[dict], replay: dict,
                          cost: dict, resume: dict, run_manifest: Optional[dict] = None,
                          run_manifest_ref: Optional[str] = None) -> dict:
    return build_live_baseline_report(
        project_path=project_path,
        baseline_id=PRECHECK_BASELINE_ID,
        status=status,
        environment=environment,
        chapters=chapters,
        failures=failures,
        replay=replay,
        cost=cost,
        resume=resume,
        run_manifest=run_manifest,
        run_manifest_ref=run_manifest_ref,
    )
