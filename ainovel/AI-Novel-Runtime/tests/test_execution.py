"""test_execution.py — proves the Phase 3 execution loop closes (ANES v2).

Task Package -> agent -> deterministic model -> ChapterDraft
             -> draft QA gate -> output Artifact Contract -> derived artifact.

Runs with no network/API key (deterministic model), so the loop is provable in
CI. Run: python3 -m tests.test_execution
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from runtime import compiler, contracts, derived, registry_loader
from runtime.pipeline import build_task_package
from runtime.execution.run import execute_package
from runtime.execution.agent import ChapterDraftAgent
from runtime.execution.draft_qa import check_draft
from runtime.execution.envelope import ENVELOPE_FORMAT, unwrap

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "proj-demo"
STANDARD = HERE.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"

_passed = 0
_failed = 0


def check(name, cond, detail=""):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed += 1
        print(f"  FAIL  {name}  {detail}")


def _build(project, out) -> dict:
    r = build_task_package(
        project_path=project, schema_dir=SCHEMA,
        task=compiler.TaskDefinition("TASK-00018", "draft chapter 18: the severance",
                                     "ChapterDraft", ["CHR-00001", "EVT-00002"]),
        out_dir=out)
    assert r.ok, r.message
    return r.package


def main() -> int:
    print("ANES v2 — Phase 3 execution loop proofs")
    tmp = Path(tempfile.mkdtemp(prefix="anes-exec-"))
    project = tmp / "proj"            # temp Project copy; loop writes into it
    shutil.copytree(FIXTURE, project)
    out = tmp / "build"
    package = _build(project, out)

    # full loop — writes into the Project's registry/derived/
    r1 = execute_package(package=package, standard_root=STANDARD,
                         project_path=project)
    check("execution loop closes (package -> draft)", r1.ok, r1.message)
    check("draft written under registry/derived/ (not facts)",
          "registry/derived/" in (r1.artifact_path or "")
          and "facts" not in (r1.artifact_path or ""))
    check("draft registered in provenance index",
          derived.index_path(project).exists())
    check("draft carries package_hash provenance",
          r1.artifact["provenance"]["package_hash"] == package["content_hash"])
    check("draft pins same source versions as package",
          r1.artifact["provenance"]["derived_from"]
          == package["provenance"]["derived_from"])

    # reproducibility
    r2 = execute_package(package=package, standard_root=STANDARD,
                         project_path=project)
    check("draft is byte-reproducible (same package => same hash)",
          r1.artifact["content_hash"] == r2.artifact["content_hash"],
          f"{r1.artifact['content_hash']} != {r2.artifact['content_hash']}")

    # output validates against the contract the CAPABILITY declares (not a const)
    cs = contracts.ContractSet(STANDARD)
    cap = cs.capability("ChapterDraft")
    check("capability declares its output schema", cap.output_schema is not None)
    check("draft validates against capability's declared output contract",
          cs.validate_artifact(r1.artifact, cap.output_schema) == [])

    # staleness guard (ADR-006): bump a source fact past the package's pin
    reg = registry_loader.load(project)
    stale = derived.check_staleness(
        reg, ["CHR-00001@v1"])   # package pinned v5; pretend an older pin
    check("staleness check flags an out-of-date source pin", len(stale) >= 1)

    # draft QA gate catches an empty body (deterministic gate, ADR-003)
    broken = dict(r1.artifact)
    broken["body"] = ""
    broken["word_count"] = 0
    check("draft QA gate flags an empty body", len(check_draft(broken)) >= 1)

    # word-floor gate blocks a too-short draft through the orchestrator
    r3 = execute_package(package=package, standard_root=STANDARD,
                         project_path=project, min_words=10_000)
    check("word-floor gate blocks a too-short draft",
          not r3.ok and r3.stage == "draft-qa")

    # the package itself is unchanged by execution (read-only consumer, ADR-001)
    check("execution does not mutate the package",
          package["content_hash"] == "sha256:cd2771d31ad969ef0eed5925f0a9ff6db68079d5dd88ab7a53ba7b7c1c120146")

    # --- Runtime envelope: PromptManifest provenance rides WITH the draft on
    # disk, while the inner draft stays byte-identical to the contract artifact.
    import json as _json
    on_disk = _json.loads((project / r1.artifact_path).read_text(encoding="utf-8"))
    check("draft file on disk is a Runtime envelope",
          on_disk.get("envelope_format") == ENVELOPE_FORMAT)
    check("envelope carries prompt_provenance",
          isinstance(on_disk.get("prompt_provenance"), dict)
          and on_disk["prompt_provenance"]["prompt_id"] == "chapter-draft")
    check("envelope prompt_provenance pins the rendered/template/binding hashes",
          all(on_disk["prompt_provenance"].get(k, "").startswith("sha256:")
              for k in ("rendered_hash", "template_hash", "binding_hash")))
    # the inner draft, unwrapped, IS the returned contract artifact (byte-identical)
    inner = unwrap(on_disk)
    check("envelope inner draft == returned contract artifact (unmodified)",
          inner == r1.artifact)
    check("inner draft still validates against the frozen output contract",
          cs.validate_artifact(inner, cap.output_schema) == [])
    check("envelope did NOT alter the inner draft content_hash",
          inner["content_hash"] == r1.artifact["content_hash"])

    # --- Evaluative QA hook (ADR-003): runs, is advisory, NEVER gates, and
    # rides in the envelope (not the contract artifact).
    check("execution result carries an evaluative QA review",
          isinstance(r1.qa_review, dict) and r1.qa_review.get("reviewer"))
    check("QA review is on the evaluative axis and non-gating (ADR-003)",
          r1.qa_review["axis"] == "evaluative" and r1.qa_review["gating"] is False)
    check("QA review rides in the envelope, not the contract artifact",
          on_disk.get("qa_review") == r1.qa_review
          and "qa_review" not in inner)
    # a reviewer emitting 'error'-severity findings must STILL NOT block the loop
    from runtime.execution.draft_review import (ReviewReport, ReviewFinding)

    class _HarshReviewer:
        reviewer_id = "harsh-test-reviewer"

        def review(self, artifact, package):
            return ReviewReport(reviewer=self.reviewer_id, findings=[
                ReviewFinding("voice", "error", "tone drifts from the protagonist"),
            ])

    r_review = execute_package(package=package, standard_root=STANDARD,
                               project_path=project, reviewer=_HarshReviewer())
    check("evaluative 'error' findings do NOT gate the loop (ADR-003)",
          r_review.ok and r_review.stage == "done")
    check("custom reviewer's findings are recorded in the result",
          r_review.qa_review["reviewer"] == "harsh-test-reviewer"
          and r_review.qa_review["findings"][0]["check"] == "voice")
    check("evaluative review does NOT perturb the inner draft content_hash",
          r_review.artifact["content_hash"] == r1.artifact["content_hash"])

    # --- Publish readiness ('Build Gate ≠ Publish Readiness', Phase 4.1) + the
    # deterministic red-line gate (the safety split). Proves: publish readiness is
    # human-authority + never gates the build; a HARD red-line DOES gate; and the
    # verdict rides the envelope + validates against its contract.
    import json as _json2
    pr_schema = _json2.loads(
        (STANDARD / "contracts" / "publish-readiness.schema.json").read_text(encoding="utf-8"))
    from jsonschema import Draft202012Validator as _V

    check("execution result carries a publish-readiness verdict",
          isinstance(r1.publish_readiness, dict) and r1.publish_readiness.get("recommendation"))
    check("publish readiness is human-authority (ADR-009) and NEVER gates build",
          r1.publish_readiness["authority"] == "human"
          and r1.publish_readiness["gates_build"] is False)
    check("publish-readiness verdict validates against its contract",
          list(_V(pr_schema).iter_errors(r1.publish_readiness)) == [])
    check("publish readiness rides the envelope, not the contract artifact",
          on_disk.get("publish_readiness") == r1.publish_readiness
          and "publish_readiness" not in inner)
    check("clean draft (no red-line) is not blocked by red-line",
          r1.ok and r1.publish_readiness["basis"]["redline"]["passed"] is True)

    # a HARD red-line hit GATES the build (deterministic axis of safety, ADR-003)
    from runtime.execution.redline import RedlineRule
    body_word = r1.artifact["body"][:2]   # a substring guaranteed present
    hard_rule = [RedlineRule("test-hard-line", body_word, "hard", "test")]
    r_hard = execute_package(package=package, standard_root=STANDARD,
                             project_path=project, redline_ruleset=hard_rule)
    check("a HARD red-line hit GATES the build (build blocked, ADR-003)",
          (not r_hard.ok) and r_hard.stage == "redline")
    check("gated red-line result records the hit",
          r_hard.redline_hits and r_hard.redline_hits[0]["severity"] == "hard")

    # a SOFT red-line hit does NOT gate; it survives to publish readiness as advisory
    soft_rule = [RedlineRule("test-soft-line", body_word, "soft", "test")]
    r_soft = execute_package(package=package, standard_root=STANDARD,
                             project_path=project, redline_ruleset=soft_rule)
    check("a SOFT red-line hit does NOT gate the build",
          r_soft.ok and r_soft.stage == "done")
    check("soft hit survives to publish readiness (redline passed, hit recorded)",
          r_soft.publish_readiness["basis"]["redline"]["passed"] is True
          and any(h["severity"] == "soft"
                  for h in r_soft.publish_readiness["basis"]["redline"]["hits"]))

    shutil.rmtree(tmp)
    print(f"\n{_passed} passed, {_failed} failed")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
