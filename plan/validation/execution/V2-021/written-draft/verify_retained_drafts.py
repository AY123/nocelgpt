"""Replay the two retained Chapter 7 Writer drafts without changing their archive."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from anovel.context.scene import SceneSpan
from anovel.domain.identity import EntityId
from anovel.gateway.models import GatewayRequest
from anovel.planning.versions import PlanHistory
from anovel.workflow.chapter import (
    ChapterWorkflow,
    DraftChapterBrief,
    NextChapterDraftInput,
    _last_paragraph,
    _next_chapter_model_request,
)
from anovel.workflow.models import FrozenChapterInput
from anovel.workflow.store import WorkflowStore


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read_json(path: Path) -> dict:
    return json.loads(path.read_bytes())


def archive_hashes(job: Path) -> dict[str, str]:
    return {
        path.name: sha256(path.read_bytes()).hexdigest()
        for path in job.iterdir()
        if path.is_file()
    }


def check_spans(items: list[dict], prose: bytes) -> None:
    text = prose.decode("utf-8")
    for item in items:
        span = item["span"]
        require(
            text[span["start"] : span["end"]] == span["quote"], "Character span changed"
        )
        require(
            prose[span["byte_start"] : span["byte_end"]]
            == span["quote"].encode("utf-8"),
            "UTF-8 byte span changed",
        )


def check_report(report: dict, summary: dict, prose: bytes, *, version: int) -> dict:
    require(report["version"] == version, "Wrong Draft version")
    require(
        report["source_revision_hash"] == summary["revision_hash"],
        "Wrong saved revision",
    )
    require(
        report["prose_hash"] == sha256(prose).hexdigest() == summary["prose_hash"],
        "Wrong prose hash",
    )
    require(
        report["semantic_status"] == "UNKNOWN", "Natural prose was not marked UNKNOWN"
    )
    require(
        report["artifact_state"] == "DRAFT"
        and all(
            report[key] is False
            for key in (
                "can_commit",
                "can_issue_permit",
                "can_dispatch",
                "accepted",
                "published",
            )
        ),
        "Extraction advanced beyond Draft",
    )
    coverage = report["coverage"]
    cues = report["cues"]
    require(
        all(item["state"] == "UNKNOWN" for item in cues), "A review cue became a fact"
    )
    editorial = report["editorial_evidence"]
    notes = editorial["continuity"]
    choice = editorial["choice"]
    check_spans(coverage + cues + notes + ([{"span": choice}] if choice else []), prose)
    require(
        b"".join(item["span"]["quote"].encode("utf-8") for item in coverage) == prose,
        "Coverage does not reconstruct the complete saved prose",
    )
    cut = len(prose.decode("utf-8")) // 2
    require(
        any(
            item["kind"] == "UNSUPPORTED" and item["span"]["start"] > cut
            for item in coverage
        ),
        "No unsupported natural prose was reported in the latter half",
    )
    expected_call = "CALL_RESPONSE" if version == 1 else "CALL_DEFERRAL"
    other_call = "CALL_DEFERRAL" if version == 1 else "CALL_RESPONSE"
    # Match exact anchors without embedding the private chapter in this script.
    call_anchor = {
        1: "cd03fbe88bc5fff35f1754f1f858eaf1ee7b443ceccc4ca333293c48f30f769e",
        2: "085becba15d4a56e74b5f7142a816e70a5bc831ddf9e850950cf2a241945f545",
    }[version]
    belief_anchor = "ab697ee823535977f87e07128806d3cd38f6316911b45fe56257ef8a6126f863"
    require(
        any(
            item["kind"] == expected_call
            and sha256(item["span"]["quote"].encode("utf-8")).hexdigest() == call_anchor
            for item in cues
        ),
        "Missing revision-specific call cue",
    )
    require(
        not any(item["kind"] == other_call for item in cues),
        "Wrong revision's call cue survived",
    )
    require(
        any(
            item["kind"] == "BELIEF"
            and item["span"]["start"] > cut
            and sha256(item["span"]["quote"].encode("utf-8")).hexdigest()
            == belief_anchor
            for item in cues
        ),
        "Late character belief was not separated from the story facts",
    )
    require(
        not report["facts"], "Natural dialogue or editorial notes became typed facts"
    )
    return {
        "version": version,
        "revision_hash": report["source_revision_hash"],
        "prose_hash": report["prose_hash"],
        "observation_hash": report["observation_hash"],
        "inventory_hash": report["inventory_hash"],
        "semantic_status": report["semantic_status"],
        "coverage_segments": len(coverage),
        "diagnostics": len(report["diagnostics"]),
        "editorial_choice_present": choice is not None,
        "editorial_notes": len(notes),
        "call_cue": expected_call,
        "late_belief_grounded": True,
        "late_unsupported_prose_reported": True,
    }


def replay_writer_request(
    job: Path,
    db: Path,
    step_id: str,
    *,
    handoff_name: str,
    brief_name: str,
    request_name: str,
) -> tuple[dict, dict]:
    handoff_row = read_json(job / handoff_name)
    project, branch, run_id = (
        handoff_row[key] for key in ("project", "branch", "source_run_id")
    )
    current = FrozenChapterInput.from_dict(read_json(job / "current.json"))
    workflow = ChapterWorkflow(WorkflowStore(db), draft_handoff_step_id=step_id)
    predecessors: list = []
    # The archive may have moved across filesystems. Follow exact saved ancestry
    # for this comparison only, with no live writer or active continuation claim.
    draft, root = workflow._read_retained_written_draft(
        current,
        project=project,
        branch=branch,
        run_id=run_id,
        chapter_id=EntityId.from_dict(handoff_row["source_chapter_id"]),
        version=handoff_row["source_version"],
        earlier_sources=predecessors,
    )
    plan = PlanHistory.from_dict(current.to_dict()["history"]).active
    text = draft.prose.decode("utf-8")
    ending = _last_paragraph(text)
    handoff = NextChapterDraftInput(
        draft,
        plan.vision.chapters[draft.chapter_number],
        plan.content_hash,
        SceneSpan(len(text) - len(ending), len(text), ending),
        earlier_sources=tuple(reversed(predecessors)),
    )
    if handoff.to_dict() != handoff_row:
        handoff = replace(handoff, include_fulfilled_commitments=False)
    require(
        handoff.to_dict() == handoff_row,
        "Actual archived handoff differs from the saved lineage",
    )
    brief = DraftChapterBrief.from_dict(read_json(job / brief_name))
    archived_request = (job / request_name).read_bytes()
    policy = GatewayRequest.from_dict(json.loads(archived_request)).policies[0]
    packet = workflow._next_chapter_writer_request(current, handoff, root, brief)
    request = _next_chapter_model_request(
        handoff, packet, root.assembly.child.source.context, policy
    )
    require(
        request.to_bytes() == archived_request, "Full frozen Writer request changed"
    )
    return json.loads(packet), {
        "source_version": handoff.source_version,
        "handoff_hash": handoff.record_hash,
        "request_hash": sha256(archived_request).hexdigest(),
        "byte_identical": True,
    }


def check_chapter_8_input(packet: dict, v2: dict) -> None:
    require(
        packet["source_observation_hash"] == v2["inventory_hash"],
        "Writer did not use the v2 extraction inventory",
    )
    require(
        {item["key"]: item["status"] for item in packet["handoff"]["open_commitments"]}
        == {
            "store-pay-split": "DUE_UNEXPLAINED",
            "monday-noon-call": "DUE_UNEXPLAINED",
            "trial-cut": "NOT_DUE",
            "friday-shift-check": "NOT_DUE",
        },
        "Writer lost an unresolved v2 item",
    )
    require(
        not packet["observed_draft_facts"],
        "Writer received facts absent from the typed extraction",
    )


def verify(job: Path, temp: Path) -> dict:
    baseline = archive_hashes(job)
    handoff = read_json(job / "chapter-8-handoff.json")
    db = temp / "workflow.sqlite"
    shutil.copy2(job / db.name, db)
    db.with_suffix(".sqlite.locks").mkdir(mode=0o700)
    scope = (handoff["project"], handoff["branch"], handoff["source_run_id"])
    with sqlite3.connect(db.as_uri() + "?mode=ro&immutable=1", uri=True) as connection:
        rows = connection.execute(
            "SELECT step_id FROM extraction_observations WHERE project=? AND branch=? AND run_id=?",
            scope,
        ).fetchall()
    require(len(rows) == 1, "Expected one retained assembled root")
    [[step_id]] = rows
    argv = [
        sys.executable,
        "-B",
        "-m",
        "anovel.workflow",
        "--db",
        str(db),
        "--project",
        scope[0],
        "--branch",
        scope[1],
        "--run-id",
        scope[2],
        "--draft-handoff-step-id",
        step_id,
        "inspect-written-draft-extraction",
        "--input",
        str(job / "current.json"),
        "--chapter-id",
        handoff["source_chapter_id"]["local_id"],
    ]
    reports = []
    summaries = [
        read_json(job / f"chapter-7-v{version}-summary.json") for version in (1, 2)
    ]
    for version, summary in enumerate(summaries, 1):
        output = temp / f"extraction-v{version}.json"
        result = subprocess.run(
            [
                *argv,
                "--expected-revision-hash",
                summary["revision_hash"],
                "--version",
                str(version),
                "--output",
                str(output),
            ],
            capture_output=True,
            check=False,
        )
        require(
            result.returncode == 0,
            f"Saved Draft extraction failed for v{version}: {result.stdout!r}",
        )
        require(output.stat().st_mode & 0o077 == 0, "Extraction output is not private")
        report = check_report(
            read_json(output),
            summary,
            (job / f"chapter-7-v{version}.txt").read_bytes(),
            version=version,
        )
        reports.append(report)
    stale = subprocess.run(
        [
            *argv,
            "--expected-revision-hash",
            summaries[0]["revision_hash"],
            "--version",
            "2",
        ],
        capture_output=True,
        check=False,
    )
    require(
        stale.returncode == 2
        and json.loads(stale.stdout)["code"] == "CHAPTER_REVISION_CHANGED",
        "The v1 hash was not rejected when selecting v2",
    )
    require(
        reports[0]["observation_hash"] != reports[1]["observation_hash"],
        "Revisions share an observation hash",
    )
    _, chapter_7_writer = replay_writer_request(
        job,
        db,
        step_id,
        handoff_name="handoff.json",
        brief_name="brief.json",
        request_name="request.json",
    )
    packet, chapter_8_writer = replay_writer_request(
        job,
        db,
        step_id,
        handoff_name="chapter-8-handoff.json",
        brief_name="chapter-8-brief.json",
        request_name="chapter-8-prepared-request.json",
    )
    check_chapter_8_input(packet, reports[1])
    require(
        sha256(db.read_bytes()).hexdigest() == baseline[db.name],
        "Replay changed its saved Draft database",
    )
    require(archive_hashes(job) == baseline, "Replay changed the original archive")
    return {
        "artifact_state": "DRAFT",
        "chapter_7": reports,
        "chapter_7_writer_input": chapter_7_writer,
        "chapter_8_writer_input": chapter_8_writer,
        "cross_revision_evidence_rejected": True,
        "archive_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path, help="Retained V2-020 Writer job archive")
    args = parser.parse_args()
    with TemporaryDirectory(prefix="v2-021-retained-drafts-") as temp:
        result = verify(args.job.resolve(strict=True), Path(temp).resolve(strict=True))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
