"""Contract tests for review triage policy validator.

Validates that the review_triage_checks validator correctly enforces
all policy constraints and fails closed on violations.
"""
import json
import tempfile
from pathlib import Path

import pytest

# Import validator
import sys
sys.path.insert(0, str(Path(__file__).parents[2] / 'plan/scripts'))
from review_triage_checks import validate_report, TriageValidationError


def create_valid_report():
    """Create a minimal valid triage report."""
    return {
        'record_type': 'external_review_triage_report',
        'schema_version': '1.0',
        'report_date': '2026-09-25',
        'audit_report_ref': {
            'path': 'audit.txt',
            'baseline': 'abc123'
        },
        'repository_baseline': {
            'branch': 'main',
            'head': '1234567890abcdef1234567890abcdef12345678',
            'worktree_clean': True,
            'plan_version': '1.3.0'
        },
        'findings': [],
        'observations': [],
        'summary': {
            'total_findings': 0,
            'confirmed': 0,
            'adopted': 0,
            'deferred': 0,
            'rejected': 0
        }
    }


def create_valid_finding():
    """Create a minimal valid finding."""
    return {
        'id': 'F-001',
        'claim': 'Test finding claim',
        'baseline_status': 'STILL_PRESENT',
        'verification': 'CONFIRMED',
        'evidence_level': 'E2',
        'severity': 'P2',
        'recommendation_validity': 'VALID',
        'decision': 'TRACK_ONLY',
        'owner': 'V2-004',
        'reason': 'Test rationale for this decision'
    }


def test_valid_report_passes():
    """Valid report should pass validation."""
    report = create_valid_report()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        temp_path = f.name

    try:
        valid, errors = validate_report(temp_path)
        assert valid, f'Expected valid report to pass, got errors: {errors}'
        assert len(errors) == 0
    finally:
        Path(temp_path).unlink()


def test_false_positive_cannot_adopt():
    """FALSE_POSITIVE + ADOPT_NOW must fail."""
    report = create_valid_report()
    finding = create_valid_finding()
    finding['verification'] = 'FALSE_POSITIVE'
    finding['decision'] = 'ADOPT_NOW'
    report['findings'] = [finding]
    report['summary']['total_findings'] = 1

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        temp_path = f.name

    try:
        valid, errors = validate_report(temp_path)
        assert not valid, 'FALSE_POSITIVE + ADOPT_NOW should fail'
        assert any('Prohibited combination' in e for e in errors)
    finally:
        Path(temp_path).unlink()


def test_already_fixed_cannot_adopt():
    """ALREADY_FIXED + ADOPT_NOW must fail."""
    report = create_valid_report()
    finding = create_valid_finding()
    finding['verification'] = 'ALREADY_FIXED'
    finding['decision'] = 'ADOPT_NOW'
    report['findings'] = [finding]
    report['summary']['total_findings'] = 1

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        temp_path = f.name

    try:
        valid, errors = validate_report(temp_path)
        assert not valid, 'ALREADY_FIXED + ADOPT_NOW should fail'
        assert any('Prohibited combination' in e for e in errors)
    finally:
        Path(temp_path).unlink()


def test_cannot_verify_cannot_adopt():
    """CANNOT_VERIFY + ADOPT_NOW must fail."""
    report = create_valid_report()
    finding = create_valid_finding()
    finding['verification'] = 'CANNOT_VERIFY'
    finding['decision'] = 'ADOPT_NOW'
    report['findings'] = [finding]
    report['summary']['total_findings'] = 1

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        temp_path = f.name

    try:
        valid, errors = validate_report(temp_path)
        assert not valid, 'CANNOT_VERIFY + ADOPT_NOW should fail'
        assert any('Prohibited combination' in e for e in errors)
    finally:
        Path(temp_path).unlink()


def test_needs_more_evidence_cannot_adopt():
    """NEEDS_MORE_EVIDENCE + ADOPT_NOW must fail."""
    report = create_valid_report()
    finding = create_valid_finding()
    finding['verification'] = 'NEEDS_MORE_EVIDENCE'
    finding['decision'] = 'ADOPT_NOW'
    report['findings'] = [finding]
    report['summary']['total_findings'] = 1

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        temp_path = f.name

    try:
        valid, errors = validate_report(temp_path)
        assert not valid, 'NEEDS_MORE_EVIDENCE + ADOPT_NOW should fail'
        assert any('Prohibited combination' in e for e in errors)
    finally:
        Path(temp_path).unlink()


def test_p0_requires_target_invariant():
    """P0 finding without target_invariant must fail."""
    report = create_valid_report()
    finding = create_valid_finding()
    finding['severity'] = 'P0'
    # Missing target_invariant
    report['findings'] = [finding]
    report['summary']['total_findings'] = 1

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        temp_path = f.name

    try:
        valid, errors = validate_report(temp_path)
        assert not valid, 'P0 without target_invariant should fail'
        assert any('target_invariant' in e for e in errors)
    finally:
        Path(temp_path).unlink()


def test_p0_requires_adversarial_validation():
    """P0 finding without adversarial_validation must fail."""
    report = create_valid_report()
    finding = create_valid_finding()
    finding['severity'] = 'P0'
    finding['target_invariant'] = 'System SHALL NOT allow X'
    # Missing adversarial_validation
    report['findings'] = [finding]
    report['summary']['total_findings'] = 1

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        temp_path = f.name

    try:
        valid, errors = validate_report(temp_path)
        assert not valid, 'P0 without adversarial_validation should fail'
        assert any('adversarial_validation' in e for e in errors)
    finally:
        Path(temp_path).unlink()


def test_p0_with_all_requirements_passes():
    """P0 finding with all requirements should pass."""
    report = create_valid_report()
    finding = create_valid_finding()
    finding['severity'] = 'P0'
    finding['target_invariant'] = 'System SHALL NOT allow X'
    finding['adversarial_validation'] = {
        'required': True,
        'cases': [
            {
                'id': 'AC-001',
                'description': 'Alternative legal path',
                'attack_path': 'Step 1, Step 2',
                'result': 'BLOCKED'
            }
        ]
    }
    report['findings'] = [finding]
    report['summary']['total_findings'] = 1

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        temp_path = f.name

    try:
        valid, errors = validate_report(temp_path)
        assert valid, f'P0 with all requirements should pass, got: {errors}'
    finally:
        Path(temp_path).unlink()


def test_adopt_requires_candidate_remediation():
    """ADOPT_NOW without candidate_remediation must fail."""
    report = create_valid_report()
    finding = create_valid_finding()
    finding['decision'] = 'ADOPT_NOW'
    # Missing candidate_remediation
    report['findings'] = [finding]
    report['summary']['total_findings'] = 1

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        temp_path = f.name

    try:
        valid, errors = validate_report(temp_path)
        assert not valid, 'ADOPT_NOW without candidate_remediation should fail'
        assert any('candidate_remediation' in e for e in errors)
    finally:
        Path(temp_path).unlink()


def test_duplicate_finding_ids_rejected():
    """Duplicate finding IDs must fail."""
    report = create_valid_report()
    finding1 = create_valid_finding()
    finding2 = create_valid_finding()
    # Same ID
    report['findings'] = [finding1, finding2]
    report['summary']['total_findings'] = 2

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        temp_path = f.name

    try:
        valid, errors = validate_report(temp_path)
        assert not valid, 'Duplicate finding IDs should fail'
        assert any('Duplicate finding ID' in e for e in errors)
    finally:
        Path(temp_path).unlink()


def test_summary_count_mismatch_rejected():
    """Summary total_findings mismatch must fail."""
    report = create_valid_report()
    finding = create_valid_finding()
    report['findings'] = [finding]
    report['summary']['total_findings'] = 999  # Wrong count

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        temp_path = f.name

    try:
        valid, errors = validate_report(temp_path)
        assert not valid, 'Summary count mismatch should fail'
        assert any('total_findings' in e and 'does not match' in e for e in errors)
    finally:
        Path(temp_path).unlink()


def test_invalid_enum_values_rejected():
    """Invalid enum values must fail."""
    report = create_valid_report()
    finding = create_valid_finding()
    finding['verification'] = 'INVALID_VALUE'
    report['findings'] = [finding]
    report['summary']['total_findings'] = 1

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report, f)
        temp_path = f.name

    try:
        valid, errors = validate_report(temp_path)
        assert not valid, 'Invalid enum value should fail'
        assert any('Invalid verification value' in e for e in errors)
    finally:
        Path(temp_path).unlink()
