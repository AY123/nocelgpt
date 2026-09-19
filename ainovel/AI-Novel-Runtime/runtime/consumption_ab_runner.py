"""Live CI-M2-04 runner for proving approved-fact consumption in chapter N+1."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

from . import recompute
from .candidates.plan import stage_plan
from .candidates.reconcile import RawCandidate, reconcile
from .director.consumption import build_consumption_evidence
from .director.consumption_report import build_consumption_ab_report
from .execution.run import execute_package
from .mint import execute_mint
from .registry_loader import load as load_registry
from .serialize.serialization_utils import canonical_json, dump_pretty_json


def _sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _fact_hashes(project: Path, schema_dir: Path) -> dict[str, str]:
    reg = load_registry(project, schema_dir=schema_dir)
    out = {}
    for fact_id, record in sorted(reg.facts.items()):
        clean = {key: value for key, value in record.items() if key != "_source_path"}
        out[fact_id] = _sha256(clean)
    return out


def _registry_state(project: Path, schema_dir: Path) -> dict[str, Any]:
    hashes = _fact_hashes(project, schema_dir)
    return {"state_hash": _sha256(hashes), "fact_count": len(hashes)}


def _semantic_snapshot(project: Path) -> dict[str, str]:
    root = project / "registry" / "derived" / "semantic-ledger"
    if not root.is_dir():
        return {}
    return {
        path.name: "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.glob("*.json"))
    }


def _write_artifact(output_dir: Path, name: str, payload: Mapping[str, Any]) -> None:
    (output_dir / name).write_text(
        dump_pretty_json(dict(payload)) + "\n", encoding="utf-8")


def _write_run_state(output_dir: Path, *, status: str, phase: str,
                     error: Exception | None = None) -> None:
    payload: dict[str, Any] = {"status": status, "phase": phase}
    if error is not None:
        payload["error"] = {
            "type": type(error).__name__,
            "message": str(error)[:2000],
        }
    _write_artifact(output_dir, "run-state.json", payload)


def _arm_result(result, model) -> dict[str, Any]:
    if not result.ok:
        raise RuntimeError(
            f"chapter arm failed at {result.stage}: {result.message}; "
            f"qa={result.qa_findings}; contract={result.contract_errors}")
    prompt = (result.envelope or {}).get("prompt_provenance") or {}
    llm = (result.artifact.get("produced_by") or {}).get("llm") or {}
    request = getattr(model, "last_request", None)
    request_hash = None
    if request is not None:
        from .llm.replay import stable_request_hash
        request_hash = stable_request_hash(request)
    audit = {
        "provider": llm.get("provider"),
        "model": llm.get("model"),
        "request_hash": request_hash,
        "response_hash": llm.get("response_hash"),
        "provider_request_id": llm.get("provider_request_id"),
        "token_usage": llm.get("token_usage"),
        "cost": llm.get("cost"),
        "cost_status": "priced" if llm.get("cost") is not None else "unpriced",
        "finish_reason": llm.get("finish_reason"),
        "replay_ref": llm.get("replay_ref"),
    }
    return {
        "prompt_manifest_hash": prompt.get("binding_hash"),
        "prompt_rendered_hash": prompt.get("rendered_hash"),
        "draft_content_hash": result.artifact.get("content_hash"),
        "body": result.artifact.get("body") or "",
        "model_audit": audit,
        "draft": result.artifact,
        "prompt_provenance": prompt,
    }


def _prompt_variables() -> dict[str, Any]:
    """Minimum complete v14 context, identical across both experimental arms."""
    return {
        "story_state": "承接当前事实与任务包，不重开已解决冲突。",
        "narrative_mandate": "主角必须立即推进任务目标，并让行动产生不可逆进展。",
        "chapter_ir": "以具体行动推进目标，在冲突中兑现一次可见变化。",
        "scene_plan": "发现阻力 -> 主动选择 -> 承担代价 -> 推进目标 -> 留下新钩子。",
        "character_runtime": "主角以当前目标为行动依据，不改变既有动机。",
        "chapter_objective": "完成任务包目标，并通过行动呈现事实后果。",
        "director_brief": "必须具体推进；避免总结、元叙事和凭空新增专名。",
        "speech_profiles": "保持角色既有中文语域与说话习惯。",
        "recent_openings": "无可用近期章首。",
        "long_arc": "本章承担局部推进，不提前透支长弧高潮。",
        "genre_contract": "保持既定题材机制、冲突方式与专名边界。",
        "target_length_cjk": 500,
    }


def run_live_consumption_ab(
    *,
    project_path: str | Path,
    package: Mapping[str, Any],
    standard_root: str | Path,
    schema_dir: str | Path,
    output_dir: str | Path,
    model_without,
    model_with,
    fact_name: str,
    prompt_version: str = "14.0.0",
    actor: str = "human",
    confirmed: bool = False,
) -> dict[str, Any]:
    """Run both live arms in isolated project copies and archive the evidence."""
    if not confirmed:
        raise ValueError("live consumption A/B requires explicit mint confirmation")
    fact_name = fact_name.strip()
    if not fact_name:
        raise ValueError("fact_name must be non-empty")
    project_path = Path(project_path).resolve()
    output_dir = Path(output_dir).resolve()
    schema_dir = Path(schema_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(f"output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    _write_run_state(output_dir, status="running", phase="initializing")
    source_fact_hashes_before = _fact_hashes(project_path, schema_dir)

    with tempfile.TemporaryDirectory(prefix="anes-consumption-ab-") as temp:
        temp_root = Path(temp)
        arm_without_project = temp_root / "without"
        arm_with_project = temp_root / "with"
        shutil.copytree(project_path, arm_without_project)
        shutil.copytree(project_path, arm_with_project)

        historical_before = _fact_hashes(arm_without_project, schema_dir)
        semantic_before = _semantic_snapshot(arm_without_project)
        state_before = _registry_state(arm_without_project, schema_dir)

        _write_run_state(output_dir, status="running", phase="arm_without")
        try:
            without_result = execute_package(
                package=dict(package), standard_root=standard_root,
                project_path=arm_without_project, model=model_without,
                prompt_version=prompt_version, extra_prompt_variables=_prompt_variables(),
                min_words=1, assess_publish=False, write=False)
            arm_without = _arm_result(without_result, model_without)
        except Exception as exc:
            _write_run_state(
                output_dir, status="failed", phase="arm_without", error=exc)
            raise
        _write_artifact(output_dir, "arm-without.json", arm_without)

        reg = load_registry(arm_with_project, schema_dir=schema_dir)
        recon = reconcile(reg, [RawCandidate(
            "Item", "name", fact_name, "human-approved-consumption-ab", None, 1.0)])
        plan, _ = stage_plan(
            project_path=arm_with_project, plan_id="CI-M2-04-FACT-PLAN",
            draft={
                "task_id": str(package.get("task", {}).get("task_id") or ""),
                "content_hash": str(package.get("content_hash") or ""),
                "provenance": {"derived_from": []},
            },
            recon=recon, extractor_id="human-approved-consumption-ab")
        _write_artifact(output_dir, "fact-plan.json", plan)
        candidates = [
            item["candidate_id"] for item in plan.get("items") or []
            if item.get("classification") == "new"
            and item.get("extracted_value") == fact_name
        ]
        if len(candidates) != 1:
            raise RuntimeError(
                f"expected one new fact candidate for {fact_name!r}, got {candidates}")
        receipt = execute_mint(
            project_path=arm_with_project, plan=plan, accepted=candidates,
            schema_dir=schema_dir, confirmed=True, actor=actor)
        _write_artifact(output_dir, "mint-receipt.json", receipt)
        recompute_report = recompute.execute_recompute(
            load_registry(arm_with_project, schema_dir=schema_dir),
            arm_with_project, mint_receipt=receipt)
        _write_artifact(output_dir, "recompute-report.json", recompute_report)
        state_after = _registry_state(arm_with_project, schema_dir)
        historical_after_all = _fact_hashes(arm_with_project, schema_dir)
        historical_after = {
            fact_id: historical_after_all.get(fact_id)
            for fact_id in historical_before
        }
        semantic_after = _semantic_snapshot(arm_with_project)
        minted_records = [
            {
                "id": item["entity_id"],
                "name": str(item.get("value") or fact_name),
                "field": item.get("field"),
                "value": item.get("value"),
            }
            for item in receipt.get("minted") or []
        ]
        evidence = build_consumption_evidence(
            chapter_id=str(package.get("task", {}).get("task_id") or ""),
            approved_candidates=[{"id": cid} for cid in candidates],
            mint_records=minted_records, recompute=recompute_report,
            state_before=state_before, state_after=state_after,
            objective_id=f"OBJ-{package.get('task', {}).get('task_id', '')}")

        _write_run_state(output_dir, status="running", phase="arm_with")
        try:
            with_result = execute_package(
                package=dict(package), standard_root=standard_root,
                project_path=arm_with_project, model=model_with,
                prompt_version=prompt_version, extra_prompt_variables=_prompt_variables(),
                consumption_evidence=evidence, recomputed_state=state_after,
                min_words=1, assess_publish=False, write=False)
            arm_with = _arm_result(with_result, model_with)
        except Exception as exc:
            _write_run_state(
                output_dir, status="failed", phase="arm_with", error=exc)
            raise
        _write_artifact(output_dir, "arm-with.json", arm_with)

        report = build_consumption_ab_report(
            chapter_id=str(package.get("task", {}).get("task_id") or ""),
            consumption_evidence=evidence,
            arm_without=arm_without, arm_with=arm_with,
            approved_facts=minted_records,
            historical_fact_hashes_before=historical_before,
            historical_fact_hashes_after=historical_after,
            semantic_ledger_before=semantic_before,
            semantic_ledger_after=semantic_after)
        source_fact_hashes_after = _fact_hashes(project_path, schema_dir)
        source_project_mutated = source_fact_hashes_before != source_fact_hashes_after
        report["criteria"]["source_project_unchanged"] = not source_project_mutated
        report["all_criteria_met"] = all(report["criteria"].values())
        report["live_provenance"] = {
            "package_hash": package.get("content_hash"),
            "prompt_version": prompt_version,
            "fact_plan_hash": plan.get("content_hash"),
            "mint_receipt_id": receipt.get("id"),
            "recompute_report_id": recompute_report.get("id"),
            "state_before_hash": state_before["state_hash"],
            "state_after_hash": state_after["state_hash"],
            "source_project_mutated": source_project_mutated,
            "arms_isolated": True,
        }
        report["report_hash"] = _sha256({
            key: value for key, value in report.items() if key != "report_hash"})

        _write_artifact(output_dir, "consumption-ab-report.json", report)
        _write_run_state(output_dir, status="completed", phase="report")
        return report
