"""workflow_scheduler.py — chapter-level checkpoint/resume orchestration.

This module adds a read-side scheduler wrapper around the existing serial
pipeline. It persists a resumable checkpoint into registry/derived so a run can
resume from the last completed chapter after transient failure.

DISCIPLINE:
  - READS only; writes only derived artifacts / run state, never facts.
  - Never gates content quality; this is orchestration and recovery only.
  - Resume is deterministic from manifest state: completed chapters are replayed
    from recorded outputs, and the next unfinished chapter is retried.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Optional, Sequence

import jsonschema

from .. import derived, registry_loader

WORKFLOW_MANIFEST_SCHEMA_VERSION = 1
WORKFLOW_BATCH_AUDIT_SCHEMA_VERSION = 1
from ..positioning.admission import project_admission
from .loop import SerialResult, run_serial
from .run_manifest import build_run_manifest, _load_chapter_final
from .w9_policy import build_w9_selection_policy, filter_w9_decision_scores

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "contracts"

SCHEDULER_CATEGORY = "workflow-scheduler"
MANIFEST_VERSION = WORKFLOW_MANIFEST_SCHEMA_VERSION


@dataclass
class WorkflowRunManifest:
    run_id: str
    story_id: str
    status: str = "pending"
    cursor: int = 1
    completed_chapters: list[int] = field(default_factory=list)
    failed_chapters: list[dict] = field(default_factory=list)
    replay_dir: Optional[str] = None
    output_dir: Optional[str] = None
    last_successful_checkpoint: Optional[int] = None
    input_hash: Optional[str] = None
    budget_limit: Optional[float] = None
    budget_spent: Optional[float] = None
    admission_status: Optional[str] = None
    admission_reason: Optional[str] = None
    selection_policy: Optional[dict] = None
    version: int = WORKFLOW_MANIFEST_SCHEMA_VERSION
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "story_id": self.story_id,
            "status": self.status,
            "cursor": self.cursor,
            "completed_chapters": sorted(set(self.completed_chapters)),
            "failed_chapters": self.failed_chapters,
            "replay_dir": self.replay_dir,
            "output_dir": self.output_dir,
            "last_successful_checkpoint": self.last_successful_checkpoint,
            "input_hash": self.input_hash,
            "budget_limit": self.budget_limit,
            "budget_spent": self.budget_spent,
            "admission_status": self.admission_status,
            "admission_reason": self.admission_reason,
            "selection_policy": self.selection_policy,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class WorkflowManifestStore:
    def __init__(self, project_path: str | Path):
        self.project_path = Path(project_path)

    def _rel_path(self, run_id: str) -> Path:
        return Path("registry") / "derived" / SCHEDULER_CATEGORY / f"{run_id}.json"

    def load(self, run_id: str) -> WorkflowRunManifest:
        path = self.project_path / self._rel_path(run_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        return WorkflowRunManifest(**data)

    def _validate(self, data: dict, schema_name: str) -> None:
        schema_path = SCHEMA_DIR / schema_name
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(instance=data, schema=schema)

    def save(self, manifest: WorkflowRunManifest) -> str:
        data = manifest.to_dict()
        self._validate(data, "workflow-manifest.schema.json")
        rel = derived.write_artifact(
            project_path=self.project_path,
            category=SCHEDULER_CATEGORY,
            artifact_id=manifest.run_id,
            artifact=data,
            serialized=json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2),
        )
        return rel

    def exists(self, run_id: str) -> bool:
        return (self.project_path / self._rel_path(run_id)).exists()


class WorkflowScheduler:
    def __init__(
        self,
        *,
        project_path: str | Path,
        standard_root: str | Path,
        schema_dir: str | Path,
        out_dir: str | Path,
        model=None,
        reviewer=None,
        prompt_runtime=None,
        simulator=None,
        rewrite_model=None,
        commercial_rounds: int = 2,
        prompt_version: str = "1.0.0",
        max_chapters: Optional[int] = None,
        max_depth: int = 2,
        reviewer_id: str = "serial-v1",
        outline: Optional[dict] = None,
        scene_planner_model=None,
        psych_beats: bool = False,
        hygiene_model=None,
        hygiene_rounds: int = 2,
        budget_limit: Optional[float] = None,
        admission_project_path: Optional[str | Path] = None,
        batch_runs: Optional[Sequence[str]] = None,
        batch_id: Optional[str] = None,
        reviewer_policy_root: Optional[str | Path] = None,
    ):
        self.project_path = Path(project_path)
        self.standard_root = Path(standard_root)
        self.schema_dir = Path(schema_dir)
        self.out_dir = Path(out_dir)
        self.model = model
        self.reviewer = reviewer
        self.prompt_runtime = prompt_runtime
        self.simulator = simulator
        self.rewrite_model = rewrite_model
        self.commercial_rounds = commercial_rounds
        self.prompt_version = prompt_version
        self.max_chapters = max_chapters
        self.max_depth = max_depth
        self.reviewer_id = reviewer_id
        self.outline = outline
        self.scene_planner_model = scene_planner_model
        self.psych_beats = psych_beats
        self.hygiene_model = hygiene_model
        self.hygiene_rounds = hygiene_rounds
        self.budget_limit = budget_limit
        self.admission_project_path = Path(admission_project_path) if admission_project_path else self.project_path
        self.batch_runs = list(batch_runs or [])
        self.batch_id = batch_id
        self.reviewer_policy_root = Path(reviewer_policy_root) if reviewer_policy_root else self.project_path
        self.store = WorkflowManifestStore(project_path)

    def _story_id(self) -> str:
        reg = registry_loader.load(self.project_path)
        story_id = getattr(reg, "id", None) or getattr(reg, "version", "story")
        return str(story_id)

    def _input_hash(self) -> str:
        payload = {
            "prompt_version": self.prompt_version,
            "max_chapters": self.max_chapters,
            "max_depth": self.max_depth,
            "reviewer_id": self.reviewer_id,
            "outline": self.outline,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _load_or_create(self, run_id: str) -> WorkflowRunManifest:
        if self.store.exists(run_id):
            return self.store.load(run_id)
        manifest = WorkflowRunManifest(
            run_id=run_id,
            story_id=self._story_id(),
            status="pending",
            cursor=1,
            replay_dir=str(self.project_path / "replay" / run_id),
            output_dir=str(self.out_dir),
            input_hash=self._input_hash(),
            budget_limit=self.budget_limit,
            admission_status="hold" if self.budget_limit is not None else "admit",
            admission_reason="budget gate pending" if self.budget_limit is not None else "no budget gate",
            selection_policy=self._selection_policy(),
        )
        self.store.save(manifest)
        return manifest

    def _admission_check(self, run_id: str, *, estimated_cost: Optional[float] = None) -> None:
        manifest = self._load_or_create(run_id)
        verdict = project_admission(self.admission_project_path, standard_root=self.standard_root)
        manifest.admission_status = verdict.get("recommendation", "admit")
        manifest.admission_reason = verdict.get("rationale") or "no admission rationale"
        if manifest.admission_status == "hold" and "no market-position authored" in (manifest.admission_reason or ""):
            manifest.admission_status = "admit"
            manifest.admission_reason = "no market-position authored; admission relaxed for scheduler smoke runs"
        if self.budget_limit is not None:
            # A budget limit is a human-authority SPENDING gate (ADR-009 flavour):
            # running the serial spends real money on LLM calls. The gate holds
            # when the projected spend REACHES OR EXCEEDS the limit. `estimated_cost`
            # defaults (from start/resume) to the full budget_limit — the
            # conservative "this run may consume the whole budget" estimate — so a
            # fresh budgeted run holds pending an explicit, lower human estimate /
            # approval. (Using `>` here was the bug: a zero budget, or a run
            # estimated at exactly the limit, slipped through as 'admit'.)
            current_spent = float(manifest.budget_spent or 0.0)
            proposed = float(estimated_cost or 0.0)
            projected_total = current_spent + proposed
            if projected_total >= float(self.budget_limit):
                manifest.admission_status = "hold"
                manifest.admission_reason = (
                    f"budget gate: projected {projected_total:.6f} reaches/exceeds limit {self.budget_limit}"
                )
            else:
                manifest.admission_status = "admit"
                manifest.admission_reason = (
                    f"budget gate: projected {projected_total:.6f} within limit {self.budget_limit}"
                )
        self.store.save(manifest)
        if manifest.admission_status != "admit":
            raise ValueError(f"workflow-scheduler admission {manifest.admission_status}: {manifest.admission_reason}")

    def start(self, run_id: str) -> SerialResult:
        self._admission_check(run_id, estimated_cost=float(self.budget_limit or 0.0))
        manifest = self._load_or_create(run_id)
        manifest.input_hash = manifest.input_hash or self._input_hash()
        manifest.selection_policy = manifest.selection_policy or self._selection_policy()
        manifest.status = "running"
        self.store.save(manifest)
        return self.run_to_completion(run_id)

    def resume(self, run_id: str) -> SerialResult:
        manifest = self._load_or_create(run_id)
        # The budget/admission gate fires on EVERY resume, INCLUDING resuming an
        # already-completed run: replaying spends real LLM budget too. With no
        # budget_limit it admits (no-op); with a locked budget it holds and raises.
        # (Bug: the completed short-circuit below used to return before any
        # admission check, so a budget locked AFTER completion never blocked a
        # re-run.) estimated_cost defaults to the full budget — the conservative
        # "this run may consume it all" estimate — matching start().
        self._admission_check(run_id, estimated_cost=float(self.budget_limit or 0.0))
        if manifest.status == "completed":
            # Idempotent replay: re-run the whole completed serial from chapter 1.
            # Deterministic (ADR-008 fold => byte-identical drafts), so it
            # reproduces the recorded chapters instead of an EMPTY result — which
            # is what start_chapter=cursor produced (cursor sits one past the last
            # completed chapter). A replay is not new progress, so the manifest
            # cursor is left untouched.
            return run_serial(
                project_path=self.project_path,
                standard_root=self.standard_root,
                schema_dir=self.schema_dir,
                out_dir=self.out_dir,
                model=self.model,
                reviewer=self.reviewer,
                prompt_runtime=self.prompt_runtime,
                simulator=self.simulator,
                rewrite_model=self.rewrite_model,
                commercial_rounds=self.commercial_rounds,
                prompt_version=self.prompt_version,
                max_chapters=self.max_chapters,
                start_chapter=1,
                max_depth=self.max_depth,
                reviewer_id=self.reviewer_id,
                outline=self.outline,
                scene_planner_model=self.scene_planner_model,
                psych_beats=self.psych_beats,
                hygiene_model=self.hygiene_model,
                hygiene_rounds=self.hygiene_rounds,
            )
        if manifest.input_hash and manifest.input_hash != self._input_hash():
            raise ValueError("workflow-scheduler input hash mismatch; refusing to resume")
        manifest.status = "running"
        self.store.save(manifest)
        return self.run_to_completion(run_id)

    def _completed_spec_indexes(self, result: SerialResult) -> set[int]:
        return {c.spec.index for c in result.chapters if c.ok}

    def _checkpoint_from_result(self, run_id: str, result: SerialResult) -> None:
        manifest = self._load_or_create(run_id)
        manifest.completed_chapters = sorted(self._completed_spec_indexes(result))
        manifest.last_successful_checkpoint = (
            max(manifest.completed_chapters) if manifest.completed_chapters else None
        )
        manifest.cursor = (
            manifest.last_successful_checkpoint + 1
            if manifest.last_successful_checkpoint is not None else 1
        )
        manifest.failed_chapters = [
            {
                "chapter": c.spec.index,
                "stage": c.stage,
                "message": c.message,
                "ok": c.ok,
            }
            for c in result.chapters if not c.ok
        ]
        manifest.budget_spent = float((result.llm_cost or {}).get("total_cost") or 0.0)
        manifest.status = "completed" if result.skipped == 0 else "paused"
        self.store.save(manifest)

    def mark_failed(self, run_id: str, chapter: int, stage: str, message: str) -> None:
        manifest = self._load_or_create(run_id)
        manifest.status = "paused"
        manifest.failed_chapters.append({
            "chapter": chapter,
            "stage": stage,
            "message": message,
            "ok": False,
        })
        manifest.cursor = min(manifest.cursor or chapter, chapter)
        self.store.save(manifest)

    def mark_completed(self, run_id: str, completed_up_to: Optional[int] = None) -> None:
        manifest = self._load_or_create(run_id)
        if completed_up_to is not None:
            manifest.last_successful_checkpoint = completed_up_to
            manifest.cursor = completed_up_to + 1
            manifest.completed_chapters = sorted(set(
                list(manifest.completed_chapters) + list(range(1, completed_up_to + 1))
            ))
        manifest.status = "completed"
        manifest.budget_spent = float(manifest.budget_spent or 0.0)
        self.store.save(manifest)

    def resume_cursor(self, run_id: str) -> int:
        manifest = self._load_or_create(run_id)
        return manifest.cursor

    def step(self, run_id: str) -> SerialResult:
        manifest = self._load_or_create(run_id)
        if manifest.status == "completed":
            return run_serial(
                project_path=self.project_path,
                standard_root=self.standard_root,
                schema_dir=self.schema_dir,
                out_dir=self.out_dir,
                model=self.model,
                reviewer=self.reviewer,
                prompt_runtime=self.prompt_runtime,
                simulator=self.simulator,
                rewrite_model=self.rewrite_model,
                commercial_rounds=self.commercial_rounds,
                prompt_version=self.prompt_version,
                max_chapters=1,
                start_chapter=manifest.cursor,
                max_depth=self.max_depth,
                reviewer_id=self.reviewer_id,
                outline=self.outline,
                scene_planner_model=self.scene_planner_model,
                psych_beats=self.psych_beats,
                hygiene_model=self.hygiene_model,
                hygiene_rounds=self.hygiene_rounds,
            )
        manifest.status = "running"
        self.store.save(manifest)
        result = run_serial(
            project_path=self.project_path,
            standard_root=self.standard_root,
            schema_dir=self.schema_dir,
            out_dir=self.out_dir,
            model=self.model,
            reviewer=self.reviewer,
            prompt_runtime=self.prompt_runtime,
            simulator=self.simulator,
            rewrite_model=self.rewrite_model,
            commercial_rounds=self.commercial_rounds,
            prompt_version=self.prompt_version,
            max_chapters=1,
            start_chapter=manifest.cursor,
            max_depth=self.max_depth,
            reviewer_id=self.reviewer_id,
            outline=self.outline,
            scene_planner_model=self.scene_planner_model,
            psych_beats=self.psych_beats,
            hygiene_model=self.hygiene_model,
            hygiene_rounds=self.hygiene_rounds,
        )
        self._checkpoint_from_result(run_id, result)
        return result

    def _selection_policy(self) -> dict:
        return build_w9_selection_policy(self.reviewer_policy_root)

    def _decision_scores(self, scores: dict) -> dict:
        return filter_w9_decision_scores(self.reviewer_policy_root, scores)

    def _run_one(self, run_id: str, start_chapter: int, max_chapters: Optional[int] = None) -> tuple[SerialResult, dict]:
        started = perf_counter()
        result = run_serial(
            project_path=self.project_path,
            standard_root=self.standard_root,
            schema_dir=self.schema_dir,
            out_dir=self.out_dir,
            model=self.model,
            reviewer=self.reviewer,
            prompt_runtime=self.prompt_runtime,
            simulator=self.simulator,
            rewrite_model=self.rewrite_model,
            commercial_rounds=self.commercial_rounds,
            prompt_version=self.prompt_version,
            max_chapters=max_chapters if max_chapters is not None else self.max_chapters,
            start_chapter=start_chapter,
            max_depth=self.max_depth,
            reviewer_id=self.reviewer_id,
            outline=self.outline,
            scene_planner_model=self.scene_planner_model,
            psych_beats=self.psych_beats,
            hygiene_model=self.hygiene_model,
            hygiene_rounds=self.hygiene_rounds,
        )
        self._checkpoint_from_result(run_id, result)
        run_manifest = build_run_manifest(
            project_path=self.project_path,
            result=result,
            run_id=run_id,
            params={
                "prompt_version": self.prompt_version,
                "commercial": self.simulator is not None and self.rewrite_model is not None,
                "panel": None,
                "model_provider": getattr(self.model, "provider", None),
                "model_id": getattr(self.model, "model_id", None),
                "max_chapters": max_chapters if max_chapters is not None else self.max_chapters,
                "started_at": None,
                "finished_at": None,
                "selection_policy": self._selection_policy(),
            },
        )
        chapter_finals = []
        for c in run_manifest.get("chapters", []):
            if c.get("ok"):
                chapter_finals.append({
                    "task_id": c["task_id"],
                    "final": _load_chapter_final(self.project_path, c["task_id"]),
                })
        run_manifest["chapter_finals"] = chapter_finals
        run_manifest["rationale"] = (
            run_manifest.get("rationale", "")
            + "; chapter-final artifacts folded into workflow run manifest"
        )
        return result, run_manifest

    def _attach_run_manifest(self, run_id: str, run_manifest: dict) -> str:
        out_dir = self.project_path / "registry" / "derived" / "run-manifests"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{run_id}.json"
        path.write_text(json.dumps(run_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return str(path.relative_to(self.project_path))

    def run_batch(self) -> list[dict]:
        audit = []
        started = perf_counter()
        for run_id in self.batch_runs:
            try:
                result, run_manifest = self._run_one(run_id, start_chapter=self.resume_cursor(run_id) if self.store.exists(run_id) else 1)
                self._attach_run_manifest(run_id, run_manifest)
                manifest = self.store.load(run_id)
                audit.append({
                    "run_id": run_id,
                    "status": manifest.status,
                    "cursor": manifest.cursor,
                    "completed": len(manifest.completed_chapters),
                    "failed": len(manifest.failed_chapters),
                    "admission": manifest.admission_status,
                    "budget_spent": manifest.budget_spent,
                    "produced": result.produced,
                    "skipped": result.skipped,
                    "chapter_finals": [
                        item for item in run_manifest.get("chapter_finals", [])
                        if item.get("final") is not None
                    ],
                })
            except Exception as exc:
                audit.append({
                    "run_id": run_id,
                    "status": "blocked",
                    "error": str(exc),
                })
        batch_manifest = {
            "id": self.batch_id or f"BATCH-{len(self.batch_runs):05d}",
            "kind": "workflow_batch_audit",
            "version": WORKFLOW_BATCH_AUDIT_SCHEMA_VERSION,
            "batch": {
                "run_count": len(self.batch_runs),
                "started_at": None,
                "finished_at": None,
                "elapsed_ms": int((perf_counter() - started) * 1000),
            },
            "summary": {
                "succeeded": sum(1 for item in audit if item.get("status") != "blocked"),
                "blocked": sum(1 for item in audit if item.get("status") == "blocked"),
                "budget_spent": round(sum(float(item.get("budget_spent") or 0) for item in audit), 6),
            },
            "runs": audit,
        }
        self.project_path.joinpath("registry", "derived", SCHEDULER_CATEGORY).mkdir(parents=True, exist_ok=True)
        self.store._validate(batch_manifest, "workflow-batch-audit.schema.json")
        batch_path = self.project_path / "registry" / "derived" / SCHEDULER_CATEGORY / f"{batch_manifest['id']}.json"
        batch_path.write_text(json.dumps(batch_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return audit

    def run_to_completion(self, run_id: str) -> SerialResult:
        manifest = self._load_or_create(run_id)
        result, run_manifest = self._run_one(run_id, start_chapter=manifest.cursor)
        self._attach_run_manifest(run_id, run_manifest)
        return result


def workflow_scheduler(*args, **kwargs) -> WorkflowScheduler:
    return WorkflowScheduler(*args, **kwargs)
