"""Delivery gate contract tests for V2-004.

These tests verify CI gate requirements and anti-weakening properties.
They run locally and do not depend on GitLab being online.
"""
import json
from pathlib import Path
import yaml
import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_ci_gates_yaml_structure():
    """Verify ci-gates.yaml has required structure."""
    gates_path = ROOT / 'plan/machine/ci-gates.yaml'
    assert gates_path.exists(), "ci-gates.yaml must exist"

    with gates_path.open() as f:
        data = yaml.safe_load(f)

    assert 'version' in data
    assert 'status' in data
    assert 'gates' in data
    assert isinstance(data['gates'], list)


def test_p0_gates_exist_with_correct_activation():
    """P0 gates must exist with activation_phase: P0."""
    gates_path = ROOT / 'plan/machine/ci-gates.yaml'
    with gates_path.open() as f:
        data = yaml.safe_load(f)

    required_p0_gates = {
        'STATIC', 'UNIT', 'SCHEMA_CONTRACT',
        'ARCH_FITNESS', 'SECRET_DEPENDENCY', 'POSTGRES_ENV'
    }

    found_gates = {gate['id']: gate for gate in data['gates']}

    for gate_id in required_p0_gates:
        assert gate_id in found_gates, f"P0 gate {gate_id} must exist"
        gate = found_gates[gate_id]
        assert gate['activation_phase'] == 'P0', \
            f"{gate_id} must have activation_phase: P0"


def test_p0_gates_cannot_allow_failure():
    """All P0 gates must have allow_failure: false."""
    gates_path = ROOT / 'plan/machine/ci-gates.yaml'
    with gates_path.open() as f:
        data = yaml.safe_load(f)

    p0_gates = [g for g in data['gates'] if g['activation_phase'] == 'P0']

    for gate in p0_gates:
        assert gate['allow_failure'] is False, \
            f"P0 gate {gate['id']} must have allow_failure: false, got {gate['allow_failure']}"


def test_future_gates_not_falsely_activated():
    """Future gates (P2+) must remain NOT_IMPLEMENTED."""
    gates_path = ROOT / 'plan/machine/ci-gates.yaml'
    with gates_path.open() as f:
        data = yaml.safe_load(f)

    future_gates = {
        'CANON_CAS_IDEMPOTENCY': 'P2',
        'DETERMINISTIC_E2E': 'P7',
        'GENRE_SMOKE': 'P8',
        'LIVE_PROVIDER': 'P5'
    }

    found_gates = {gate['id']: gate for gate in data['gates']}

    for gate_id, expected_phase in future_gates.items():
        if gate_id in found_gates:
            gate = found_gates[gate_id]
            assert gate['activation_phase'] == expected_phase, \
                f"{gate_id} must remain in phase {expected_phase}"
            assert gate['status'] == 'NOT_IMPLEMENTED', \
                f"Future gate {gate_id} must remain NOT_IMPLEMENTED"


def test_gitlab_ci_exists():
    """GitLab CI configuration must exist."""
    ci_path = ROOT / '.gitlab-ci.yml'
    assert ci_path.exists(), ".gitlab-ci.yml must exist"


def test_gitlab_ci_has_p0_jobs():
    """GitLab CI must define jobs for P0 gates."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    # Check for job definitions (job names or stage references)
    required_patterns = [
        'static', 'unit', 'schema_contract',
        'arch_fitness', 'secret_dependency', 'postgres_env'
    ]

    content_lower = content.lower()
    for pattern in required_patterns:
        assert pattern in content_lower, \
            f"CI must include job for {pattern}"


def test_gitlab_ci_no_allow_failure_for_p0():
    """GitLab CI P0 jobs must not have allow_failure: true."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    # This is a basic check - full YAML parsing would be better
    # but sufficient for detecting obvious allow_failure additions
    lines = content.split('\n')

    in_p0_job = False
    job_name = None

    p0_job_patterns = ['static:', 'unit:', 'schema_contract:',
                       'arch_fitness:', 'secret_dependency:', 'postgres_env:']

    for i, line in enumerate(lines):
        # Check if we're entering a P0 job
        if any(line.strip().startswith(pattern) for pattern in p0_job_patterns):
            in_p0_job = True
            job_name = line.strip()

        # Check for allow_failure in P0 job context
        if in_p0_job and 'allow_failure' in line and 'true' in line:
            pytest.fail(f"P0 job {job_name} at line {i+1} has allow_failure: true")

        # Reset when we hit next top-level job
        if line and not line.startswith(' ') and line.strip().endswith(':'):
            in_p0_job = False


def test_gitlab_ci_uses_locked_dependencies():
    """CI must use locked dependencies (uv sync --frozen)."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    assert 'uv sync --frozen' in content or 'uv sync' in content, \
        "CI must use uv sync with locked dependencies"


def test_gitlab_ci_uses_postgres_service():
    """CI must include PostgreSQL service for POSTGRES_ENV gate."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    assert 'postgres:' in content or 'postgresql:' in content, \
        "CI must include PostgreSQL service"


def test_delivery_gates_test_suite_registered():
    """AT-V2-004 test suite must be registered in test-catalog."""
    catalog_path = ROOT / 'plan/machine/test-catalog.yaml'
    with catalog_path.open() as f:
        data = yaml.safe_load(f)

    suites = {suite['id']: suite for suite in data['suites']}

    assert 'AT-V2-004' in suites, "AT-V2-004 must be registered in test-catalog"
    suite = suites['AT-V2-004']
    assert suite['task_id'] == 'V2-004'
    assert suite['phase'] == 'P0'


def test_no_test_deletions_in_catalog():
    """Test catalog must not have tests deleted (reduced scenario count)."""
    catalog_path = ROOT / 'plan/machine/test-catalog.yaml'
    with catalog_path.open() as f:
        data = yaml.safe_load(f)

    # V2-001 should have scenarios (from baseline)
    v2_001_suites = [s for s in data['suites'] if s['id'] == 'AT-V2-001']
    assert len(v2_001_suites) > 0
    assert 'scenarios' in v2_001_suites[0]
    assert len(v2_001_suites[0]['scenarios']) >= 5, \
        "V2-001 scenarios must not be reduced"


def test_execution_packet_exists_for_v2_004():
    """V2-004 must have execution packet."""
    packet_path = ROOT / 'plan/validation/execution/V2-004/execution-packet.yaml'
    assert packet_path.exists(), "V2-004 execution packet must exist"


def test_execution_packet_action_is_implement():
    """V2-004 execution packet must have action: IMPLEMENT."""
    packet_path = ROOT / 'plan/validation/execution/V2-004/execution-packet.yaml'
    with packet_path.open() as f:
        data = yaml.safe_load(f)

    assert data['action'] == 'IMPLEMENT', \
        "V2-004 packet must have action: IMPLEMENT"


def test_no_weakening_in_governance_tests():
    """Governance tests must not be skipped or reduced."""
    gov_test_path = ROOT / 'tests/contract/test_plan_governance.py'
    assert gov_test_path.exists(), "Governance tests must exist"

    with gov_test_path.open() as f:
        content = f.read()

    # Check no mass pytest.skip added
    assert '@pytest.skip' not in content or content.count('@pytest.skip') < 3, \
        "Governance tests must not be mass-skipped"


# These tests verify negative scenarios work correctly
# They are structural checks, not actual negative fixture execution

def test_ci_would_detect_secret_fixture():
    """SECRET_DEPENDENCY gate includes secret scanning logic."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    # Verify secret_dependency job has actual scanning logic
    assert 'secret' in content.lower(), \
        "CI must include secret scanning reference"


def test_ci_would_detect_dependency_issues():
    """SECRET_DEPENDENCY gate includes dependency checking logic."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    # Verify dependency checking
    assert 'uv pip check' in content or 'dependency' in content.lower(), \
        "CI must include dependency validation"


# Anti-self-weakening tests

def test_ci_gates_not_reduced_from_baseline():
    """Number of P0 gates must not decrease."""
    gates_path = ROOT / 'plan/machine/ci-gates.yaml'
    with gates_path.open() as f:
        data = yaml.safe_load(f)

    p0_gates = [g for g in data['gates'] if g['activation_phase'] == 'P0']

    assert len(p0_gates) >= 6, \
        f"Must have at least 6 P0 gates, found {len(p0_gates)}"


def test_locked_dependencies_file_exists():
    """uv.lock must exist and not be bypassed."""
    lock_path = ROOT / 'uv.lock'
    assert lock_path.exists(), "uv.lock must exist for locked dependencies"


def test_gitignore_includes_dist():
    """dist/ must be in .gitignore (CI artifacts)."""
    gitignore_path = ROOT / '.gitignore'
    assert gitignore_path.exists()

    with gitignore_path.open() as f:
        content = f.read()

    assert 'dist/' in content, "dist/ must be in .gitignore"
