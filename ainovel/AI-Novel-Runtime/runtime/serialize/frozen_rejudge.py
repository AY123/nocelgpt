"""Rejudge persisted chapter drafts without regenerating prose or writing Facts."""
from __future__ import annotations

import json
from pathlib import Path

from .. import derived
from ..execution.publish_readiness import assess_publish_readiness
from ..execution.quality_center import LLMQualityJudge, chapter_quality_verdict
from ..execution.redline import RedlineHit
from .serialization_utils import content_hash


def rejudge_frozen_chapters(*, project_path, package_dir, model, start_chapter, end_chapter) -> dict:
    project = Path(project_path)
    package_root = Path(package_dir)
    judge = LLMQualityJudge(model)
    rows = []
    previous_scores = None
    for index in range(start_chapter, end_chapter + 1):
        task_id = f"TASK-{index:05d}"
        draft_path = project / "registry" / "derived" / "drafts" / f"{task_id}.json"
        run_path = project / "registry" / "derived" / "chapter-run" / f"run-{task_id}.json"
        package_path = package_root / f"{task_id}.package.json"
        envelope = json.loads(draft_path.read_text(encoding="utf-8"))
        package = json.loads(package_path.read_text(encoding="utf-8"))
        chapter_run = json.loads(run_path.read_text(encoding="utf-8"))
        report = judge.review(envelope["draft"], package).to_dict()
        degraded = bool((report.get("judge_provenance") or {}).get("degraded"))

        old_redline = ((envelope.get("publish_readiness") or {}).get("basis") or {}).get("redline") or {}
        redline_hits = [
            RedlineHit(rule=str(hit.get("rule") or ""),
                       severity=str(hit.get("severity") or "soft"),
                       evidence=str(hit.get("evidence") or ""))
            for hit in (old_redline.get("hits") or []) if isinstance(hit, dict)
        ]
        review_ref = f"registry/derived/chapter-quality-review/review-{task_id}.json"
        readiness = assess_publish_readiness(
            chapter_id=task_id, redline_hits=redline_hits, quality_report=report,
            draft_content_hash=envelope["draft"].get("content_hash"),
            quality_report_ref=review_ref).to_dict()
        envelope["qa_review"] = report
        envelope["publish_readiness"] = readiness
        derived.write_artifact(
            project_path=project, category="drafts", artifact_id=task_id,
            artifact=envelope["draft"],
            serialized=json.dumps(envelope, ensure_ascii=False, indent=2) + "\n")

        artifact = {
            "kind": "frozen_chapter_quality_review", "version": "1.0",
            "chapter_index": index, "task_id": task_id,
            "draft_hash": envelope["draft"].get("content_hash"),
            "report": report, "comparison_only": True, "gating": False,
        }
        artifact["content_hash"] = "sha256:" + content_hash(artifact)
        derived.write_artifact(
            project_path=project, category="chapter-quality-review",
            artifact_id=f"review-{task_id}", artifact=artifact,
            serialized=json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")

        chapter_run["qa_scores"] = report.get("scores")
        chapter_run["verdict"] = chapter_quality_verdict(report, previous_scores)
        if not degraded:
            previous_scores = report.get("scores")
        derived.write_artifact(
            project_path=project, category="chapter-run", artifact_id=f"run-{task_id}",
            artifact=chapter_run,
            serialized=json.dumps(chapter_run, ensure_ascii=False, indent=2) + "\n")
        rows.append({
            "chapter_index": index, "task_id": task_id,
            "degraded": degraded, "parse_ok": not degraded,
            "review_ref": review_ref,
            "provider": (report.get("judge_provenance") or {}).get("provider"),
            "model_id": (report.get("judge_provenance") or {}).get("model_id"),
        })
        if degraded:
            break
    return {
        "kind": "frozen_chapter_rejudge_run", "version": "1.0",
        "start_chapter": start_chapter, "end_chapter": end_chapter,
        "n_reviewed": len(rows),
        "n_degraded": sum(1 for row in rows if row["degraded"]),
        "chapters": rows, "comparison_only": True, "gating": False,
    }
