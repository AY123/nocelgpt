"""experiment_protocol.py — N100-002 100-chapter experiment protocol.

This records the frozen execution boundary for a chapter-run experiment:
model / prompt / reviewer policy / budget / checkpoint / fact-flow rules.
It is a config artifact, not an executor, and it intentionally avoids business
logic. The point is to give N100 runs a single auditable configuration hash.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from .serialization_utils import content_hash, dump_pretty_json

PROTOCOL_KIND = "hundred_chapter_experiment_protocol"
PROTOCOL_VERSION = "1.1"


@dataclass(frozen=True)
class ExperimentProtocol:
    kind: str
    version: str
    protocol_id: str
    project_id: str
    run_scope: str
    model_provider: str
    model_id: str
    prompt_version: str
    prompt_bundle_ref: str
    schema_ref: str
    budget_limit_cny: float
    temperature_contract: dict
    max_output_tokens: int | None
    role_models: dict
    max_chapters: int
    checkpoint_interval: int
    reviewer_policy: dict
    fact_flow_policy: dict
    resume_policy: dict
    change_control: dict
    notes: str = ""


def build_experiment_protocol(
    *,
    protocol_id: str,
    project_id: str,
    model_provider: str,
    model_id: str,
    prompt_version: str,
    prompt_bundle_ref: str,
    schema_ref: str,
    budget_limit_cny: float,
    temperature_contract: Optional[dict] = None,
    max_output_tokens: int | None = None,
    role_models: Optional[dict] = None,
    max_chapters: int = 100,
    checkpoint_interval: int = 10,
    reviewer_policy: Optional[dict] = None,
    fact_flow_policy: Optional[dict] = None,
    resume_policy: Optional[dict] = None,
    change_control: Optional[dict] = None,
    run_scope: str = "100-chapter-production-validation",
    notes: str = "",
) -> dict:
    protocol = ExperimentProtocol(
        kind=PROTOCOL_KIND,
        version=PROTOCOL_VERSION,
        protocol_id=protocol_id,
        project_id=project_id,
        run_scope=run_scope,
        model_provider=model_provider,
        model_id=model_id,
        prompt_version=prompt_version,
        prompt_bundle_ref=prompt_bundle_ref,
        schema_ref=schema_ref,
        budget_limit_cny=budget_limit_cny,
        temperature_contract=temperature_contract or {
            "temperature": 0.7,
            "top_p": None,
        },
        max_output_tokens=max_output_tokens,
        role_models=role_models or {},
        max_chapters=max_chapters,
        checkpoint_interval=checkpoint_interval,
        reviewer_policy=reviewer_policy or {
            "human_review_required": True,
            "decision_only_dimensions": [],
            "diagnostic_dimensions": [],
            "unreliable_dimensions": [],
            "tie_break": "human",
        },
        fact_flow_policy=fact_flow_policy or {
            "fact_writer": "mint.executor.execute_mint",
            "candidate_flow": "stage -> approve -> mint -> recompute",
            "w12_extract": True,
            "never_bypass_mint": True,
        },
        resume_policy=resume_policy or {
            "resume_enabled": True,
            "checkpoint_resumption": True,
            "idempotent_resume": True,
            "no_duplicate_billing": True,
        },
        change_control=change_control or {
            "freeze_prompt_between_checkpoints": True,
            "freeze_schema_between_checkpoints": True,
            "changes_require_new_protocol_version": True,
            "changes_only_at_checkpoint": True,
        },
        notes=notes,
    )
    data = asdict(protocol)
    data["content_hash"] = content_hash(data)
    return data


def protocol_filename(protocol_id: str) -> str:
    return f"{protocol_id}.json"


def write_experiment_protocol(path: str | Path, protocol: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_pretty_json(protocol) + "\n", encoding="utf-8")
    return path
