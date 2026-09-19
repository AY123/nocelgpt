"""
Tests for P0-2: Fail-Closed Release Package

Validates that release packages default to NOT_READY when checks are missing,
and only reach READY status when all checks have passed.
"""
import pytest
from pathlib import Path
import json
import tempfile

from runtime.publishing.release_package import (
    build_release_package,
    ReleaseStatus,
    ReleasePackage,
    ReleasePackageMetadata,
)


class TestFailClosedDefaults:
    """Test that missing checks block release (fail-closed)"""

    def test_missing_redline_blocks_release(self, tmp_path):
        """P0-2: Missing redline check must block release"""
        pkg = build_release_package(
            tmp_path,
            redline_report=None,  # Not run!
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "recommend"},
        )

        assert pkg.status == ReleaseStatus.NOT_READY.value
        assert not pkg.can_release
        assert any("Redline" in issue for issue in pkg.blocking_issues)
        assert pkg.redline_status == "not_run"

    def test_missing_originality_blocks_release(self, tmp_path):
        """P0-2: Missing originality check must block release"""
        pkg = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report=None,  # Not run!
            publish_readiness={"recommendation": "recommend"},
        )

        assert pkg.status == ReleaseStatus.NOT_READY.value
        assert not pkg.can_release
        assert any("Originality" in issue for issue in pkg.blocking_issues)
        assert pkg.originality_status == "not_run"

    def test_missing_publish_readiness_blocks_release(self, tmp_path):
        """P0-2: Missing publish readiness must block release"""
        pkg = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L0"},
            publish_readiness=None,  # Not assessed!
        )

        assert pkg.status == ReleaseStatus.NOT_READY.value
        assert not pkg.can_release
        assert any("readiness" in issue.lower() for issue in pkg.blocking_issues)
        assert pkg.readiness_status == "not_run"

    def test_all_missing_blocks_release(self, tmp_path):
        """P0-2: All checks missing must block release"""
        pkg = build_release_package(
            tmp_path,
            redline_report=None,
            originality_report=None,
            publish_readiness=None,
        )

        assert pkg.status == ReleaseStatus.NOT_READY.value
        assert not pkg.can_release
        assert len(pkg.blocking_issues) == 3
        assert pkg.redline_status == "not_run"
        assert pkg.originality_status == "not_run"
        assert pkg.readiness_status == "not_run"


class TestFailedChecksBlockRelease:
    """Test that failed checks block release"""

    def test_redline_failure_blocks_release(self, tmp_path):
        """P0-2: Redline failure must block release"""
        pkg = build_release_package(
            tmp_path,
            redline_report={"passed": False, "hits": [{"pattern": "禁词"}]},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "recommend"},
        )

        assert pkg.status == ReleaseStatus.CHECKS_FAILED.value
        assert not pkg.can_release
        assert any("Redline failed" in issue for issue in pkg.blocking_issues)
        assert pkg.redline_status == "failed"

    def test_high_originality_risk_blocks_release(self, tmp_path):
        """P0-2: High originality risk must block release"""
        pkg = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L2"},  # High risk!
            publish_readiness={"recommendation": "recommend"},
        )

        assert pkg.status == ReleaseStatus.CHECKS_FAILED.value
        assert not pkg.can_release
        assert any("Originality risk: L2" in issue for issue in pkg.blocking_issues)
        assert pkg.originality_status == "high_risk"

    def test_blocked_readiness_blocks_release(self, tmp_path):
        """P0-2: Blocked publish readiness must block release"""
        pkg = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "block"},  # Blocked!
        )

        assert pkg.status == ReleaseStatus.CHECKS_FAILED.value
        assert not pkg.can_release
        assert any("blocked" in issue.lower() for issue in pkg.blocking_issues)
        assert pkg.readiness_status == "blocked"

    def test_held_readiness_blocks_release(self, tmp_path):
        """P0-2: Held publish readiness must block release"""
        pkg = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "hold"},  # Held!
        )

        assert pkg.status == ReleaseStatus.CHECKS_FAILED.value
        assert not pkg.can_release
        assert any("held" in issue.lower() for issue in pkg.blocking_issues)
        assert pkg.readiness_status == "held"


class TestPassedChecksAllowRelease:
    """Test that all checks passed allows release (after human approval)"""

    def test_all_checks_passed_ready_for_approval(self, tmp_path):
        """P0-2: All checks passed → READY for human approval"""
        pkg = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "recommend"},
        )

        assert pkg.status == ReleaseStatus.READY.value
        assert len(pkg.blocking_issues) == 0
        assert pkg.redline_status == "passed"
        assert pkg.originality_status == "passed"
        assert pkg.readiness_status == "ready"

        # But still cannot release until APPROVED
        assert not pkg.can_release  # Needs human approval

    def test_can_release_only_when_approved(self):
        """P0-2: Only APPROVED packages can be released"""
        # READY package cannot release
        ready_pkg = ReleasePackage(
            id="TEST-001",
            kind="release_package",
            version="1.2",
            project_id="test",
            metadata=ReleasePackageMetadata(
                title="Test",
                logline="Test",
                genre=["test"],
            ),
            outline_ref={"id": "OUTLINE-00001", "title": "Test"},
            golden_three=[],
            first_30_chapters=[],
            status=ReleaseStatus.READY.value,
        )
        assert not ready_pkg.can_release

        # APPROVED package can release
        approved_pkg = ReleasePackage(
            id="TEST-001",
            kind="release_package",
            version="1.2",
            project_id="test",
            metadata=ReleasePackageMetadata(
                title="Test",
                logline="Test",
                genre=["test"],
            ),
            outline_ref={"id": "OUTLINE-00001", "title": "Test"},
            golden_three=[],
            first_30_chapters=[],
            status=ReleaseStatus.APPROVED.value,
        )
        assert approved_pkg.can_release


class TestStatusTransitions:
    """Test status field values"""

    def test_not_ready_when_checks_missing(self, tmp_path):
        """P0-2: Status is NOT_READY when checks missing"""
        pkg = build_release_package(
            tmp_path,
            redline_report=None,
            originality_report=None,
            publish_readiness=None,
        )
        assert pkg.status == ReleaseStatus.NOT_READY.value

    def test_checks_failed_when_checks_fail(self, tmp_path):
        """P0-2: Status is CHECKS_FAILED when checks fail"""
        pkg = build_release_package(
            tmp_path,
            redline_report={"passed": False, "hits": [{"pattern": "test"}]},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "recommend"},
        )
        assert pkg.status == ReleaseStatus.CHECKS_FAILED.value

    def test_ready_when_all_checks_pass(self, tmp_path):
        """P0-2: Status is READY when all checks pass"""
        pkg = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "recommend"},
        )
        assert pkg.status == ReleaseStatus.READY.value


class TestCheckStatuses:
    """Test individual check status fields"""

    def test_redline_status_values(self, tmp_path):
        """P0-2: Redline status reflects check state"""
        # Not run
        pkg1 = build_release_package(tmp_path, redline_report=None)
        assert pkg1.redline_status == "not_run"

        # Passed
        pkg2 = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "recommend"},
        )
        assert pkg2.redline_status == "passed"

        # Failed
        pkg3 = build_release_package(
            tmp_path,
            redline_report={"passed": False, "hits": [{"pattern": "test"}]},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "recommend"},
        )
        assert pkg3.redline_status == "failed"

    def test_originality_status_values(self, tmp_path):
        """P0-2: Originality status reflects check state"""
        # Not run
        pkg1 = build_release_package(tmp_path, originality_report=None)
        assert pkg1.originality_status == "not_run"

        # Passed (L0 or L1)
        pkg2 = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "recommend"},
        )
        assert pkg2.originality_status == "passed"

        # High risk (L2 or L3)
        pkg3 = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L2"},
            publish_readiness={"recommendation": "recommend"},
        )
        assert pkg3.originality_status == "high_risk"

    def test_readiness_status_values(self, tmp_path):
        """P0-2: Readiness status reflects check state"""
        # Not run
        pkg1 = build_release_package(tmp_path, publish_readiness=None)
        assert pkg1.readiness_status == "not_run"

        # Ready
        pkg2 = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "recommend"},
        )
        assert pkg2.readiness_status == "ready"

        # Held
        pkg3 = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "hold"},
        )
        assert pkg3.readiness_status == "held"

        # Blocked
        pkg4 = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "block"},
        )
        assert pkg4.readiness_status == "blocked"


class TestBackwardCompatibility:
    """Test that legacy fields are preserved"""

    def test_legacy_fields_present(self, tmp_path):
        """P0-2: Legacy fields still present for compatibility"""
        pkg = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "recommend"},
        )

        # Legacy fields
        assert pkg.publish_authority == "human"
        assert pkg.gating == False
        assert pkg.comparison_only == True

        # Reports are still accessible
        assert pkg.redline_report is not None
        assert pkg.originality_report is not None
        assert pkg.publish_readiness is not None

    def test_to_dict_includes_new_fields(self, tmp_path):
        """P0-2: to_dict() includes new P0-2 fields"""
        pkg = build_release_package(
            tmp_path,
            redline_report={"passed": True, "hits": []},
            originality_report={"risk_level": "L0"},
            publish_readiness={"recommendation": "recommend"},
        )

        d = pkg.to_dict()

        # New P0-2 fields present
        assert "status" in d
        assert "blocking_issues" in d
        assert "redline_status" in d
        assert "originality_status" in d
        assert "readiness_status" in d

        # Version bumped
        assert d["version"] == "1.2"
