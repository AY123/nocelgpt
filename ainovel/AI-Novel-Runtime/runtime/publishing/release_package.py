"""N100-061 / D180-06: platform-neutral release package builder.

Folds outline + golden three + first 30 chapters + originality + redline +
publish-readiness + baseline report + long-run report into a single reproducible
release package. Authority stays human (ADR-009); never gates (ADR-003).

P0-2: Fail-closed by default - missing checks block release.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional
from enum import Enum


RELEASE_PACKAGE_KIND = "release_package"
RELEASE_PACKAGE_VERSION = "1.2"  # P0-2: Version bump for fail-closed semantics


class ReleaseStatus(Enum):
    """P0-2: Release package status"""
    NOT_READY = "not_ready"          # Missing required checks
    CHECKS_FAILED = "checks_failed"   # One or more checks failed
    READY = "ready"                   # All checks passed, awaiting approval
    APPROVED = "approved"             # Human approved for release
    BLOCKED = "blocked"               # Explicitly blocked from release


@dataclass(frozen=True)
class ReleasePackageMetadata:
    title: str
    logline: str
    genre: list[str]
    tags: list[str] = field(default_factory=list)
    selling_points: list[str] = field(default_factory=list)
    publish_authority: str = "human"
    build_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReleasePackage:
    """
    Platform-neutral release package (P0-2: fail-closed)

    P0-2: status field determines if package can be released.
    blocking_issues lists what prevents release.
    """
    id: str
    kind: str
    version: str
    project_id: str
    metadata: ReleasePackageMetadata
    outline_ref: dict[str, Any]
    golden_three: list[dict[str, Any]]
    first_30_chapters: list[dict[str, Any]]

    # P0-2: Status and blocking issues (NEW)
    status: str  # ReleaseStatus value
    blocking_issues: list[str] = field(default_factory=list)
    redline_status: str = "not_run"  # "not_run" | "passed" | "failed"
    originality_status: str = "not_run"  # "not_run" | "passed" | "high_risk"
    readiness_status: str = "not_run"  # "not_run" | "ready" | "held" | "blocked"
    contract_status: str = "not_run"  # "not_run" | "passed" | "failed" | "not_available" | "error"

    # Check results
    originality_report: dict[str, Any] = field(default_factory=dict)
    redline_report: dict[str, Any] = field(default_factory=dict)
    publish_readiness: dict[str, Any] = field(default_factory=dict)
    baseline_report: dict[str, Any] = field(default_factory=dict)
    long_run_report: dict[str, Any] = field(default_factory=dict)
    contract_validation: dict[str, Any] = field(default_factory=dict)  # NEW: Contract validation report

    # Legacy fields (preserved for compatibility)
    publish_authority: str = "human"
    gating: bool = False
    comparison_only: bool = True
    content_hash: str = ""

    # P0-2: Can this package be released?
    @property
    def can_release(self) -> bool:
        """P0-2: Only APPROVED packages can be released"""
        return self.status == ReleaseStatus.APPROVED.value

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "kind": self.kind,
            "version": self.version,
            "project_id": self.project_id,
            "metadata": self.metadata.to_dict(),
            "outline_ref": self.outline_ref,
            "golden_three": self.golden_three,
            "first_30_chapters": self.first_30_chapters,
            # P0-2: Status fields
            "status": self.status,
            "blocking_issues": self.blocking_issues,
            "redline_status": self.redline_status,
            "originality_status": self.originality_status,
            "readiness_status": self.readiness_status,
            "contract_status": self.contract_status,
            # Check results
            "originality_report": self.originality_report,
            "redline_report": self.redline_report,
            "publish_readiness": self.publish_readiness,
            "baseline_report": self.baseline_report,
            "long_run_report": self.long_run_report,
            "contract_validation": self.contract_validation,
            # Legacy
            "publish_authority": self.publish_authority,
            "gating": self.gating,
            "comparison_only": self.comparison_only,
        }
        if self.content_hash:
            d["content_hash"] = self.content_hash
        return d


def build_release_package(
    project_path: str | Path,
    *,
    project_id: str = "",
    golden_three: list[Mapping[str, Any]] | None = None,
    originality_report: Mapping[str, Any] | None = None,
    redline_report: Mapping[str, Any] | None = None,
    publish_readiness: Mapping[str, Any] | None = None,
    baseline_report: Mapping[str, Any] | None = None,
    long_run_report: Mapping[str, Any] | None = None,
    package_id: str = "",
) -> ReleasePackage:
    project = Path(project_path)

    # Load outline
    outline_path = project / "registry" / "derived" / "outline" / "OUTLINE-00001.json"
    outline: dict = {}
    if outline_path.is_file():
        try:
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
        except Exception:
            outline = {}

    title = str(outline.get("title") or "待定标题")
    logline = str(outline.get("logline") or "")
    genre = list(outline.get("genre") or [])
    themes = list(outline.get("themes") or [])
    first_30 = list(outline.get("first_30_chapters") or [])

    # Selling points from market_position
    mp = outline.get("market_position") or {}
    selling_points = []
    promise = str(mp.get("reader_promise") or "")
    if promise:
        selling_points.append(promise)
    known_drop = mp.get("known_drop_points") or []
    if known_drop:
        selling_points.append(f"防弃书设计：针对{', '.join(known_drop[:2])}")

    metadata = ReleasePackageMetadata(
        title=title,
        logline=logline,
        genre=genre,
        tags=themes[:5],
        selling_points=selling_points[:5],
        publish_authority="human",
        build_note="platform-neutral release package v1.1; reproducible from raw artifacts",
    )

    # P0-2: Fail-closed validation
    # Check results default to "not_run", and missing checks block release
    blocking_issues = []

    # Redline check
    redline = dict(redline_report) if redline_report else {}
    if not redline:
        blocking_issues.append("Redline check not executed")
        redline_status = "not_run"
    elif not redline.get("passed", False):
        blocking_issues.append(f"Redline failed: {len(redline.get('hits', []))} hits")
        redline_status = "failed"
    else:
        redline_status = "passed"

    # Originality check
    orig = dict(originality_report) if originality_report else dict(outline.get("originality_report") or {})
    if not orig:
        blocking_issues.append("Originality check not executed")
        originality_status = "not_run"
    elif orig.get("risk_level") in ["L2", "L3"]:
        blocking_issues.append(f"Originality risk: {orig['risk_level']}")
        originality_status = "high_risk"
    else:
        originality_status = "passed"

    # Publish readiness
    pub = dict(publish_readiness) if publish_readiness else {}
    if not pub:
        blocking_issues.append("Publish readiness not assessed")
        readiness_status = "not_run"
    elif pub.get("recommendation") == "block":
        blocking_issues.append("Publish readiness: blocked")
        readiness_status = "blocked"
    elif pub.get("recommendation") == "hold":
        blocking_issues.append("Publish readiness: held")
        readiness_status = "held"
    else:
        readiness_status = "ready"

    # Contract validation (new - integrated from C2/C3/C4)
    contract_validation = {}
    contract_status = "not_run"
    try:
        from .contract_validator import validate_chapter_contracts_for_release

        # Extract chapter numbers from first_30
        # Try both 'chapter' and 'chapter_no' keys
        chapter_numbers = []
        for ref in first_30:
            ch = ref.get("chapter") or ref.get("chapter_no")
            if ch:
                chapter_numbers.append(ch)

        if chapter_numbers:
            validation_result = validate_chapter_contracts_for_release(
                project_path=project,
                chapter_list=chapter_numbers
            )

            contract_validation = validation_result

            if not validation_result['passed']:
                # Add blocking issues from contract validation
                for issue in validation_result['blocking_issues'][:5]:  # Limit to first 5
                    blocking_issues.append(f"Contract: {issue}")

                remaining = len(validation_result['blocking_issues']) - 5
                if remaining > 0:
                    blocking_issues.append(f"Contract: ... and {remaining} more issues")

                contract_status = "failed"
            else:
                contract_status = "passed"
    except ImportError:
        # Contract validator not available - skip check
        contract_status = "not_available"
    except Exception as e:
        # Contract validation error - don't block release
        contract_validation = {"error": str(e)}
        contract_status = "error"

    # P0-2: Determine overall status
    if blocking_issues:
        if any("not executed" in issue or "not assessed" in issue for issue in blocking_issues):
            status = ReleaseStatus.NOT_READY.value
        else:
            status = ReleaseStatus.CHECKS_FAILED.value
    else:
        # All checks passed - ready for human approval
        status = ReleaseStatus.READY.value

    # Baseline report (optional — D180-06 upgrade)
    baseline = dict(baseline_report) if baseline_report else {}

    # Long run report (optional — D180-06 upgrade)
    long_run = dict(long_run_report) if long_run_report else {}

    pid = project_id or str(outline.get("provenance", {}).get("project_id") or project.name)
    pkg_id = package_id or f"RELEASE-{pid}"

    import hashlib
    raw = json.dumps(
        {
            "id": pkg_id,
            "kind": RELEASE_PACKAGE_KIND,
            "version": RELEASE_PACKAGE_VERSION,
            "project_id": pid,
            "metadata": metadata.to_dict(),
            "outline_ref": {"id": outline.get("id"), "title": title},
            "golden_three": golden_three or [],
            "first_30_chapters": first_30,
            "originality_report": orig,
            "redline_report": redline,
            "publish_readiness": pub,
            "baseline_report": baseline,
            "long_run_report": long_run,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    content_hash = "sha256:" + hashlib.sha256(raw).hexdigest()

    return ReleasePackage(
        id=pkg_id,
        kind=RELEASE_PACKAGE_KIND,
        version=RELEASE_PACKAGE_VERSION,
        project_id=pid,
        metadata=metadata,
        outline_ref={"id": outline.get("id"), "title": title},
        golden_three=[dict(g) for g in (golden_three or [])],
        first_30_chapters=first_30,
        # P0-2: Status and blocking issues
        status=status,
        blocking_issues=blocking_issues,
        redline_status=redline_status,
        originality_status=originality_status,
        readiness_status=readiness_status,
        contract_status=contract_status,
        # Check results
        originality_report=orig,
        redline_report=redline,
        publish_readiness=pub,
        baseline_report=baseline,
        long_run_report=long_run,
        contract_validation=contract_validation,
        content_hash=content_hash,
    )


def write_release_package(path: str | Path, package: ReleasePackage) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(package.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out
