"""CI-M5: evidence-backed admission and completion audit for a 100-chapter run.

This module never generates prose and never writes facts. It folds existing
protocol, review, plan, run, checkpoint, recovery, and baseline artifacts into
one operator-facing decision record. Missing evidence stays missing: a module
being implemented is not evidence that a production gate passed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .serialization_utils import content_hash, dump_pretty_json


AUDIT_KIND = "hundred_chapter_acceptance_audit"
AUDIT_VERSION = "1.0"


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _project_ref(project: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(project.resolve()))
    except ValueError:
        return str(path.resolve())


def _existing(paths: Iterable[Path]) -> list[Path]:
    return sorted({path for path in paths if path.is_file()})


def _latest(paths: Iterable[Path]) -> Path | None:
    existing = _existing(paths)
    return existing[-1] if existing else None


def _check(check_id: str, passed: bool, detail: str, ref: str | None = None) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "passed": bool(passed),
        "detail": detail,
        "evidence_ref": ref,
    }


def _artifact_hash_matches(value: Mapping[str, Any] | None) -> bool:
    """Verify the repo's bare or ``sha256:``-prefixed content hash convention."""
    if not value:
        return False
    stored = str(value.get("content_hash") or "")
    if not stored:
        return False
    body = {key: item for key, item in value.items() if key != "content_hash"}
    expected = content_hash(body)
    return stored in (expected, f"sha256:{expected}")


def _combine_manifests(manifests: list[dict[str, Any]]) -> tuple[dict[str, Any], bool, str]:
    """Fold explicit immutable run segments into one audit-only chain view."""
    run_ids = [str(manifest.get("id") or "") for manifest in manifests]
    chapters = [
        chapter for manifest in manifests
        for chapter in (manifest.get("chapters") or [])
        if isinstance(chapter, Mapping)
    ]
    indices = [int(chapter.get("index") or 0) for chapter in chapters]
    expected = list(range(1, max(indices, default=0) + 1))
    contiguous = bool(indices and indices == expected and len(indices) == len(set(indices)))
    skipped = sum(
        int((manifest.get("totals") or {}).get("skipped") or 0)
        for manifest in manifests)
    produced = sum(
        int((manifest.get("totals") or {}).get("produced") or 0)
        for manifest in manifests)
    live_calls = sum(
        int((manifest.get("totals") or {}).get("live_calls") or 0)
        for manifest in manifests)
    token_usage = {
        key: sum(int(((manifest.get("totals") or {}).get("token_usage") or {}).get(key) or 0)
                 for manifest in manifests)
        for key in ("input", "output", "total")
    }
    costs = [(manifest.get("totals") or {}).get("cost") for manifest in manifests]
    priced = [cost for cost in costs if isinstance(cost, Mapping)]
    currencies = {str(cost.get("currency") or "") for cost in priced}
    cost = None
    if priced and len(priced) == len(manifests) and len(currencies) == 1:
        cost = {
            "currency": next(iter(currencies)),
            "total_cost": round(sum(float(cost.get("total_cost") or 0) for cost in priced), 6),
        }
    combined = {
        "id": "+".join(run_ids),
        "kind": "production_run_chain_view",
        "gating": False,
        "run_ids": run_ids,
        "chapters": chapters,
        "totals": {
            "planned": len(chapters),
            "produced": produced,
            "skipped": skipped,
            "live_calls": live_calls,
            "token_usage": token_usage,
            "cost": cost,
            "final_state_hash": (
                (manifests[-1].get("totals") or {}).get("final_state_hash")
                if manifests else None),
        },
    }
    detail = (
        f"runs={run_ids}, indices={indices[0] if indices else '-'}.."
        f"{indices[-1] if indices else '-'}, chapters={len(indices)}, contiguous={contiguous}")
    return combined, contiguous, detail


def _select_manifest(project: Path, run_id: str | list[str] | tuple[str, ...] | None
                     ) -> tuple[Path | None, dict[str, Any] | None, bool, str]:
    root = project / "registry" / "derived" / "run-manifests"
    if isinstance(run_id, (list, tuple)):
        manifests: list[dict[str, Any]] = []
        missing: list[str] = []
        for item in run_id:
            path = root / f"{item}.json"
            value = _load_json(path)
            if value is None:
                missing.append(str(item))
            else:
                manifests.append(value)
        if missing:
            return None, None, False, f"missing run manifests: {missing}"
        combined, valid, detail = _combine_manifests(manifests)
        return None, combined, valid, detail
    if run_id:
        path = root / f"{run_id}.json"
        value = _load_json(path)
        if value is None:
            return path, None, False, f"missing run manifest: {run_id}"
        combined, valid, detail = _combine_manifests([value])
        return path, value, valid, detail
    candidates: list[tuple[int, str, Path, dict[str, Any]]] = []
    for path in _existing(root.glob("*.json")):
        value = _load_json(path)
        if value is None:
            continue
        chapters = value.get("chapters") or []
        produced = int((value.get("totals") or {}).get("produced") or 0)
        candidates.append((max(produced, len(chapters)), path.name, path, value))
    if not candidates:
        return None, None, False, "no run manifests"
    _, _, path, value = max(candidates, key=lambda item: (item[0], item[1]))
    _, valid, detail = _combine_manifests([value])
    return path, value, valid, detail


def _protocol_path(project: Path, explicit: str | Path | None) -> Path | None:
    if explicit:
        return Path(explicit)
    return _latest([
        *(project / "registry" / "derived" / "experiment-protocols").glob("*.json"),
        *(project / "analysis").glob("*protocol*.json"),
    ])


def _ledger_path(project: Path, run_id: str | None, explicit: str | Path | None) -> Path | None:
    if explicit:
        return Path(explicit)
    candidates: list[Path] = []
    if run_id:
        candidates.append(project / "analysis" / f"{run_id.lower()}-chapter-evidence-ledger.json")
    candidates.extend((project / "analysis").glob("*chapter-evidence-ledger*.json"))
    candidates.extend(
        (project / "registry" / "derived" / "chapter-evidence-ledgers").glob("*.json"))
    return _latest(candidates)


def _outline(project: Path) -> tuple[Path | None, dict[str, Any] | None]:
    paths = [project / "registry" / "derived" / "outline" / "OUTLINE-00001.json"]
    paths.extend((project / "workspace" / "outline-bootstrap" / "runs").glob("*/final-outline.json"))
    path = _latest(paths)
    return path, _load_json(path)


def _long_arc(project: Path) -> tuple[Path | None, dict[str, Any] | None]:
    path = _latest((project / "registry" / "derived" / "long-arc").glob("*.json"))
    return path, _load_json(path)


def _covered_chapters_from_bands(value: Mapping[str, Any] | None) -> set[int]:
    covered: set[int] = set()
    for band in ((value or {}).get("chapter_bands") or (value or {}).get("bands") or []):
        try:
            start, end = int(band.get("start")), int(band.get("end"))
        except (AttributeError, TypeError, ValueError):
            continue
        covered.update(range(start, end + 1))
    return covered


def _planned_chapters(project: Path, outline: Mapping[str, Any] | None) -> set[int]:
    planned: set[int] = set()
    for key in ("first_30_chapters", "chapters", "chapter_plan"):
        for position, chapter in enumerate((outline or {}).get(key) or [], start=1):
            if not isinstance(chapter, Mapping):
                continue
            raw = chapter.get("chapter_no") or chapter.get("index") or chapter.get("chapter") or position
            try:
                planned.add(int(raw))
            except (TypeError, ValueError):
                continue
    for path in _existing((project / "registry" / "derived" / "rolling-plans").glob("*.json")):
        plan = _load_json(path) or {}
        for goal in list(plan.get("active_goals") or []) + list(plan.get("preview_goals") or []):
            if not isinstance(goal, Mapping):
                continue
            try:
                planned.add(int(goal.get("chapter_no")))
            except (TypeError, ValueError):
                continue
    return planned


def _golden_three_status(project: Path) -> tuple[bool, str, str | None]:
    paths = _existing((project / "registry" / "derived" / "golden-three-reviews").glob("*.json"))
    if not paths:
        return False, "no golden-three human review artifact", None
    path = paths[-1]
    review = _load_json(path) or {}
    records = review.get("independent_reviews") or review.get("reviews") or []
    human_reviewers: set[str] = set()
    passed_records = 0
    for record in records:
        if not isinstance(record, Mapping):
            continue
        reviewer = str(record.get("reviewer") or record.get("reviewer_id") or "").strip()
        authority = str(record.get("authority") or "human")
        verdict = str(record.get("verdict") or record.get("decision") or "").lower()
        if reviewer and "TBD" not in reviewer.upper() and authority == "human":
            human_reviewers.add(reviewer)
            if verdict in ("pass", "approve", "approved"):
                passed_records += 1
    outcome = review.get("review_outcome") or {}
    mode = str(outcome.get("mode") or "")
    outcome_passed = str(outcome.get("verdict") or "").lower() in ("pass", "approve", "approved")
    outcome_reviewer = str(outcome.get("reviewer") or "").strip()
    if (outcome_reviewer and "TBD" not in outcome_reviewer.upper()
            and str(outcome.get("authority") or "") == "human"):
        if outcome_reviewer not in human_reviewers and outcome_passed:
            passed_records += 1
        human_reviewers.add(outcome_reviewer)
    passed = len(human_reviewers) >= 2 and (
        passed_records >= 2 or (mode in ("dual_reviewer", "adjudicated") and outcome_passed))
    detail = (
        f"independent_human_reviewers={len(human_reviewers)}, "
        f"passed_records={passed_records}, outcome_mode={mode or 'missing'}")
    return passed, detail, _project_ref(project, path)


def _gate_status(project: Path, chapter: int, explicit: str | Path | None) -> tuple[bool, str, str | None]:
    path = Path(explicit) if explicit else _latest([
        project / "registry" / "derived" / "long-run-gates" / f"gate-{chapter:03d}.json",
        *(project / "analysis").glob(f"*gate*{chapter:03d}*.json"),
    ])
    value = _load_json(path)
    if value is None:
        return False, "missing human-authority gate decision", _project_ref(project, path)
    decision = str(value.get("decision") or value.get("verdict") or value.get("status") or "").lower()
    authority = str(value.get("authority") or "")
    passed = decision in ("go", "pass", "approved", "approve") and authority == "human"
    return passed, f"decision={decision or 'missing'}, authority={authority or 'missing'}", _project_ref(project, path)


def _recovery_status(project: Path, explicit: str | Path | None) -> tuple[bool, str, str | None]:
    path = Path(explicit) if explicit else _latest([
        *(project / "analysis").glob("*recovery*audit*.json"),
        *(project / "registry" / "derived" / "recovery-audits").glob("*.json"),
    ])
    value = _load_json(path)
    if value is None:
        return False, "missing recovery audit", _project_ref(project, path)
    audit = value.get("recovery_audit") if isinstance(value.get("recovery_audit"), Mapping) else value
    passed = (
        bool(audit.get("interrupted"))
        and bool(audit.get("resumed"))
        and not bool(audit.get("rewritten_final"))
        and not bool(audit.get("duplicate_cost"))
        and not bool(audit.get("half_written_facts")))
    return passed, (
        f"interrupted={bool(audit.get('interrupted'))}, resumed={bool(audit.get('resumed'))}, "
        f"rewritten_final={bool(audit.get('rewritten_final'))}, "
        f"duplicate_cost={bool(audit.get('duplicate_cost'))}, "
        f"half_written_facts={bool(audit.get('half_written_facts'))}"), _project_ref(project, path)


def _baseline_status(project: Path, explicit: str | Path | None) -> tuple[bool, str, str | None]:
    path = Path(explicit) if explicit else _latest([
        *(project / "analysis").glob("*100*baseline*.json"),
        *(project / "registry" / "derived" / "long-run-baselines").glob("*.json"),
    ])
    value = _load_json(path)
    if value is None:
        return False, "missing 100-chapter baseline", _project_ref(project, path)
    front = value.get("front_half") or {}
    back = value.get("back_half") or {}
    full = value.get("full_run") or {}
    segments = (front, back)
    segment_metrics = all(
        isinstance(segment.get("avg_quality"), (int, float))
        and isinstance(segment.get("cost_total"), (int, float))
        and bool(segment.get("cost_currency"))
        and isinstance(segment.get("promise_overdue"), list)
        and isinstance(segment.get("promise_resolved"), list)
        for segment in segments
    )
    counts_ok = (
        int(front.get("chapter_count") or 0) == 50
        and int(back.get("chapter_count") or 0) == 50
        and int(full.get("chapter_count") or 0) == 100
        and all(int(segment.get("produced") or 0) == 50 for segment in segments)
        and all(int(segment.get("skipped") or 0) == 0 for segment in segments)
    )
    decision = str(value.get("go_iterate_stop") or "")
    passed = bool(
        value.get("kind") == "hundred_chapter_baseline"
        and counts_ok
        and segment_metrics
        and decision in ("go", "iterate", "stop")
        and value.get("comparison_only") is True
        and value.get("gating") is False
    )
    return passed, (
        f"front={int(front.get('chapter_count') or 0)}, "
        f"back={int(back.get('chapter_count') or 0)}, "
        f"full={int(full.get('chapter_count') or 0)}, "
        f"metrics_complete={segment_metrics}, "
        f"decision={decision or 'missing'}"), _project_ref(project, path)


def build_long_run_acceptance_audit(
    *,
    project_path: str | Path,
    run_id: str | list[str] | tuple[str, ...] | None = None,
    protocol_path: str | Path | None = None,
    ledger_path: str | Path | None = None,
    gate_30_path: str | Path | None = None,
    gate_60_path: str | Path | None = None,
    recovery_audit_path: str | Path | None = None,
    baseline_path: str | Path | None = None,
) -> dict[str, Any]:
    project = Path(project_path)
    project_id_path = project / "registry" / "_meta" / "project-id"
    project_id = (
        project_id_path.read_text(encoding="utf-8").strip()
        if project_id_path.is_file() else project.name)

    manifest_path, manifest, run_chain_ok, run_chain_detail = _select_manifest(project, run_id)
    selected_run_id = str((manifest or {}).get("id") or run_id or "") or None
    totals = (manifest or {}).get("totals") or {}
    chapters = [c for c in ((manifest or {}).get("chapters") or []) if isinstance(c, Mapping)]
    produced = int(totals.get("produced") or sum(1 for c in chapters if c.get("ok")))
    skipped = int(totals.get("skipped") or sum(1 for c in chapters if not c.get("ok")))

    protocol_file = _protocol_path(project, protocol_path)
    protocol = _load_json(protocol_file)
    protocol_hash = (protocol or {}).get("content_hash")
    protocol_hash_ok = _artifact_hash_matches(protocol)
    protocol_ok = bool(
        protocol_hash and int((protocol or {}).get("max_chapters") or 0) == 100
        and str((protocol or {}).get("project_id") or project_id) == project_id
        and protocol_hash_ok)

    ledger_file = _ledger_path(project, selected_run_id, ledger_path)
    ledger = _load_json(ledger_file)
    ledger_rows = [
        row for row in ((ledger or {}).get("chapters") or [])
        if isinstance(row, Mapping)
    ]
    ledger_count = int((ledger or {}).get("chapter_count") or len(ledger_rows))
    ledger_protocol = (ledger or {}).get("protocol_content_hash")
    ledger_indices = [int(row.get("chapter_index") or 0) for row in ledger_rows]
    expected_indices = list(range(1, min(produced, 100) + 1))
    ledger_rows_ok = bool(
        len(ledger_rows) == ledger_count
        and ledger_indices == expected_indices
        and all(row.get("ok") is True for row in ledger_rows)
    )
    ledger_ok = bool(
        ledger and ledger_count >= min(produced, 100)
        and protocol_hash and ledger_protocol == protocol_hash
        and str(ledger.get("run_id") or "") == str(selected_run_id or "")
        and ledger_rows_ok
        and _artifact_hash_matches(ledger))

    outline_path, outline = _outline(project)
    long_arc_path, long_arc = _long_arc(project)
    arc_covered = _covered_chapters_from_bands(long_arc)
    planned = _planned_chapters(project, outline)
    golden_ok, golden_detail, golden_ref = _golden_three_status(project)
    gate30_ok, gate30_detail, gate30_ref = _gate_status(project, 30, gate_30_path)
    gate60_ok, gate60_detail, gate60_ref = _gate_status(project, 60, gate_60_path)

    checkpoint_root = project / "registry" / "derived" / "serial-checkpoints"
    checkpoint_numbers = {
        int(path.stem.split("-", 1)[1])
        for path in _existing(checkpoint_root.glob("cp-*.json"))
        if path.stem.split("-", 1)[1].isdigit()
    }
    cp30_required = {10, 20, 30}
    cp100_required = set(range(10, 101, 10))

    admission_checks = [
        _check("run_chain_contiguous", run_chain_ok, run_chain_detail,
               _project_ref(project, manifest_path)),
        _check("protocol_frozen", protocol_ok,
               f"max_chapters={(protocol or {}).get('max_chapters')}, "
               f"hash={protocol_hash or 'missing'}, integrity={protocol_hash_ok}",
               _project_ref(project, protocol_file)),
        _check("golden_three_two_humans", golden_ok, golden_detail, golden_ref),
        _check("thirty_chapter_run", produced >= 30 and skipped == 0,
               f"produced={produced}, skipped={skipped}", _project_ref(project, manifest_path)),
        _check("gate_30_human_go", gate30_ok, gate30_detail, gate30_ref),
        _check("long_arc_100_coverage", set(range(1, 101)).issubset(arc_covered),
               f"covered={len(arc_covered)}/100", _project_ref(project, long_arc_path)),
        _check("next_window_plan_31_40", set(range(31, 41)).issubset(planned),
               f"planned_next_window={len(planned & set(range(31, 41)))}/10; "
               f"all_detailed={len(planned & set(range(1, 101)))}/100",
               _project_ref(project, outline_path)),
        _check("chapter_evidence_current", ledger_ok,
               f"rows={ledger_count}, rows_valid={ledger_rows_ok}, "
               f"integrity={_artifact_hash_matches(ledger)}, "
               f"protocol_hash_matches={bool(protocol_hash and ledger_protocol == protocol_hash)}",
               _project_ref(project, ledger_file)),
        _check("checkpoints_10_20_30", cp30_required.issubset(checkpoint_numbers),
               f"present={sorted(checkpoint_numbers & cp30_required)}", _project_ref(project, checkpoint_root)),
    ]
    ready_for_31_60 = all(item["passed"] for item in admission_checks)

    sixty_checks = [
        _check("ready_for_31_60", ready_for_31_60,
               "all 30-chapter admission evidence passed" if ready_for_31_60 else "admission evidence incomplete"),
        _check("sixty_chapter_run", produced >= 60 and skipped == 0,
               f"produced={produced}, skipped={skipped}", _project_ref(project, manifest_path)),
        _check("gate_60_human_go", gate60_ok, gate60_detail, gate60_ref),
    ]
    ready_for_61_100 = all(item["passed"] for item in sixty_checks)

    recovery_ok, recovery_detail, recovery_ref = _recovery_status(project, recovery_audit_path)
    baseline_ok, baseline_detail, baseline_ref = _baseline_status(project, baseline_path)
    completion_checks = [
        _check("ready_for_61_100", ready_for_61_100,
               "60-chapter gate passed" if ready_for_61_100 else "60-chapter gate incomplete"),
        _check("hundred_chapter_run", produced == 100 and skipped == 0,
               f"produced={produced}, skipped={skipped}", _project_ref(project, manifest_path)),
        _check("chapter_evidence_100", ledger_ok and ledger_count == 100,
               f"rows={ledger_count}, rows_valid={ledger_rows_ok}, "
               f"integrity={_artifact_hash_matches(ledger)}, "
               f"protocol_hash_matches={bool(protocol_hash and ledger_protocol == protocol_hash)}",
               _project_ref(project, ledger_file)),
        _check("checkpoints_10_to_100", cp100_required.issubset(checkpoint_numbers),
               f"present={sorted(checkpoint_numbers & cp100_required)}", _project_ref(project, checkpoint_root)),
        _check("recovery_audit", recovery_ok, recovery_detail, recovery_ref),
        _check("front_back_baseline", baseline_ok, baseline_detail, baseline_ref),
    ]
    complete_100 = all(item["passed"] for item in completion_checks)

    if complete_100:
        status, recommendation = "complete", "review_100_chapter_baseline"
    elif ready_for_61_100:
        status, recommendation = "ready_for_61_100", "run_61_100"
    elif ready_for_31_60:
        status, recommendation = "ready_for_31_60", "run_31_60"
    else:
        status, recommendation = "blocked_before_31", "hold_and_close_admission_gaps"

    report = {
        "kind": AUDIT_KIND,
        "version": AUDIT_VERSION,
        "project_id": project_id,
        "run_id": selected_run_id,
        "status": status,
        "recommendation": recommendation,
        "ready_for_31_60": ready_for_31_60,
        "ready_for_61_100": ready_for_61_100,
        "complete_100": complete_100,
        "observed": {
            "produced": produced,
            "skipped": skipped,
            "planned_chapters": len(planned & set(range(1, 101))),
            "long_arc_coverage": len(arc_covered & set(range(1, 101))),
            "evidence_rows": ledger_count,
            "checkpoints": sorted(checkpoint_numbers),
            "token_usage": totals.get("token_usage"),
            "cost": totals.get("cost"),
        },
        "admission_checks": admission_checks,
        "sixty_chapter_checks": sixty_checks,
        "completion_checks": completion_checks,
        "comparison_only": True,
        "gating": False,
        "human_authority_required": True,
    }
    report["content_hash"] = "sha256:" + content_hash(report)
    return report


def write_long_run_acceptance_audit(path: str | Path, report: Mapping[str, Any]) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(dump_pretty_json(dict(report)) + "\n", encoding="utf-8")
    return out
