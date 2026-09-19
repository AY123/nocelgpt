"""checkpoints.py — read-side for the serial-checkpoints artifacts.

`run_serial` (loop.py) writes a `serial_checkpoint` artifact at chapters 10/20/30
under registry/derived/serial-checkpoints/ (cp-010/cp-020/cp-030.json). Until this
module those checkpoints were write-only — nothing read them back, so the staged
review points could not feed 复盘 / 阶段对比 / 基线报告汇总. This is the missing
reader (built≠live remedy).

DISCIPLINE:
  - READS only; never writes facts (ADR-006) and never gates (ADR-003). A
    checkpoint is an audit/复盘 read point, not a build decision.
  - Degrades cleanly: a run shorter than 10 chapters, or one where nothing was
    persisted, yields an empty list rather than raising.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .. import derived

CATEGORY = "serial-checkpoints"
CHAPTER_RUN_CATEGORY = "chapter-run"
CHECKPOINT_VERSION = "1.0"
# The chapter indices run_serial checkpoints at (loop.py). Kept here so the
# reader and any 复盘 query share one source of truth.
CHECKPOINT_INDICES = tuple(range(10, 101, 10))


def build_checkpoint(*, chapter_index, chapter_id, event_id, draft_hash, state_hash,
                     final_hash, verdict, commercial_verdict, quality_snapshot, m7) -> dict:
    """The single source of truth for a serial_checkpoint's SHAPE.

    Called by both the live serial loop (loop.py, from a ChapterRun in memory) and
    the deterministic backfill projection below (from a persisted chapter-run
    artifact). Keeping one builder prevents the two paths drifting — a checkpoint
    written live and one folded from disk are byte-identical for the same inputs."""
    return {
        "kind": "serial_checkpoint",
        "version": CHECKPOINT_VERSION,
        "chapter_index": chapter_index,
        "chapter_id": chapter_id,
        "event_id": event_id,
        "draft_hash": draft_hash,
        "state_hash": state_hash,
        "final_hash": final_hash,
        "verdict": verdict,
        "commercial_verdict": commercial_verdict,
        "quality_snapshot": quality_snapshot,
        "m7": m7,
    }


def _load_one(project_path, index: int) -> Optional[dict]:
    """Load the checkpoint artifact for a chapter index, or None if absent /
    unreadable (a run may not have reached this chapter)."""
    path = derived.derived_dir(project_path, CATEGORY) / f"cp-{index:03d}.json"
    if not path.exists():
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def load_serial_checkpoint(project_path, index: int) -> Optional[dict]:
    """Read a single serial checkpoint by chapter index (10/20/30)."""
    return _load_one(project_path, index)


def load_serial_checkpoints(project_path) -> List[dict]:
    """Fold every persisted serial checkpoint into an index-ordered list.

    Returns the checkpoints actually on disk (missing ones are skipped), so a run
    that stopped at chapter 12 yields just [cp-010]. Empty list when none exist."""
    out: List[dict] = []
    for idx in CHECKPOINT_INDICES:
        cp = _load_one(project_path, idx)
        if cp is not None:
            out.append(cp)
    return out


RUN_MANIFEST_CATEGORY = "run-manifests"


def _load_run_manifest(project_path, run_manifest_id: Optional[str]) -> Optional[dict]:
    """Load a run-manifest — the run-scoped, IMMUTABLE audit record for a serial
    run. `run_manifest_id` (e.g. RUN-00025) pins one; None takes the highest id.

    The manifest is the correct backfill source precisely because it is run-scoped
    and never overwritten. The per-chapter chapter-run/ artifacts are keyed by
    task_id and OVERWRITTEN by any later run over the same project, so folding
    checkpoints from them would silently attribute a later run's data to this one."""
    base = derived.derived_dir(project_path, RUN_MANIFEST_CATEGORY)
    if not base.exists():
        return None
    if run_manifest_id:
        p = base / f"{run_manifest_id}.json"
        if not p.exists():
            raise FileNotFoundError(
                f"run-manifest '{run_manifest_id}' not found under {base}")
        return json.loads(p.read_text(encoding="utf-8"))
    manifests = sorted(base.glob("RUN-*.json"))
    if not manifests:
        return None
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


def _load_chapter_run_enrichment(source_dir) -> dict:
    """Map task_id -> chapter-run dict from an EXPLICIT directory (e.g. a run's
    snapshot archive under analysis/). Only used to enrich m7 / quality_snapshot,
    which the manifest omits; every value is later gated by a draft_hash match so
    a polluted / wrong-run source cannot leak into the checkpoint."""
    by_task: dict = {}
    d = Path(source_dir)
    if not d.exists():
        return by_task
    for p in d.glob("run-*.json"):
        try:
            cr = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        tid = cr.get("task_id")
        if tid:
            by_task[tid] = cr
    return by_task


def backfill_checkpoints(project_path, *, run_manifest_id: Optional[str] = None,
                         enrichment_dir=None, overwrite: bool = False) -> List[dict]:
    """Deterministically fold a run-manifest into serial checkpoints for chapters
    10/20/30, writing any that are missing.

    This exists because a run produced BEFORE the live checkpoint writer landed
    (e.g. RUN-00025, the real 33-ch baseline) has no serial-checkpoints/. This is a
    pure read-side projection (ADR-008): same inputs → same checkpoints, so
    re-running is idempotent. Writes to serial-checkpoints/ only — never facts
    (ADR-006), never gates.

    SOURCE DISCIPLINE (learned the hard way): the run-manifest is the ONLY
    trustworthy source for the core fields, because it is run-scoped and immutable.
    The per-chapter chapter-run/ artifacts are keyed by task_id and OVERWRITTEN by
    any later run over the same project — folding from them silently mis-attributes
    a later run's hashes/detectors to this run. `run_manifest_id` pins the run;
    None takes the highest RUN-id present.

    `enrichment_dir` (optional) points at that run's own snapshot archive of
    chapter-run artifacts (e.g. analysis/<run>-snapshot/derived/chapter-run). It is
    used ONLY to fill m7 / quality_snapshot (which the manifest omits), and ONLY
    for a chapter whose enrichment draft_hash MATCHES the manifest's — a mismatch
    means the archive is a different run, so the enrichment is dropped rather than
    trusted. Core fields never come from enrichment.

    Returns the checkpoints (written or already-present) index-ordered."""
    manifest = _load_run_manifest(project_path, run_manifest_id)
    if manifest is None:
        return []
    by_index = {c.get("index"): c for c in manifest.get("chapters", [])}
    enrichment = _load_chapter_run_enrichment(enrichment_dir) if enrichment_dir else {}

    written: List[dict] = []
    for idx in CHECKPOINT_INDICES:
        c = by_index.get(idx)
        if c is None:
            continue
        if not overwrite and _load_one(project_path, idx) is not None:
            written.append(_load_one(project_path, idx))
            continue

        # enrichment (m7 / quality_snapshot) only if the archive row is the SAME
        # draft as the manifest — otherwise it belongs to a different run.
        m7 = None
        quality_snapshot = None
        cr = enrichment.get(c.get("task_id"))
        if cr is not None and cr.get("draft_hash") == c.get("draft_hash"):
            m7 = cr.get("m7")
            quality_snapshot = cr.get("quality_snapshot")

        checkpoint = build_checkpoint(
            chapter_index=c.get("index"),
            chapter_id=c.get("task_id"),
            event_id=c.get("event"),
            draft_hash=c.get("draft_hash"),
            state_hash=c.get("state_hash"),
            final_hash=(c.get("chapter_final") or {}).get("final_hash"),
            verdict=c.get("verdict"),
            commercial_verdict=c.get("commercial_verdict"),
            quality_snapshot=quality_snapshot,
            m7=m7,
        )
        derived.write_artifact(
            project_path=project_path, category=CATEGORY,
            artifact_id=f"cp-{idx:03d}", artifact=checkpoint,
            serialized=json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n")
        written.append(checkpoint)
    return written
