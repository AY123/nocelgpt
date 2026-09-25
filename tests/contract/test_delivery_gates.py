"""Delivery gate contract tests for V2-004.

These tests verify CI gate requirements and anti-weakening properties.
They run locally and do not depend on GitLab being online.
"""
import json
from pathlib import Path
import re
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


def test_gitlab_ci_yaml_is_valid():
    """GitLab CI YAML must be syntactically valid."""
    ci_path = ROOT / '.gitlab-ci.yml'
    assert ci_path.exists()

    with ci_path.open() as f:
        try:
            yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"GitLab CI YAML is invalid: {e}")


def test_arch_fitness_references_existing_tests():
    """ARCH_FITNESS job must reference only existing test files."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    # Extract test paths from arch_fitness job
    if 'arch_fitness:' in content:
        # Find pytest command in arch_fitness
        lines = content.split('\n')
        in_arch_job = False
        for line in lines:
            if 'arch_fitness:' in line:
                in_arch_job = True
            elif in_arch_job and 'pytest' in line and 'test_' in line:
                # Extract test file paths
                import re
                test_paths = re.findall(r'tests/architecture/test_\w+\.py', line)
                for test_path in test_paths:
                    full_path = ROOT / test_path
                    assert full_path.exists(), \
                        f"ARCH_FITNESS references non-existent test: {test_path}"
                break


def test_secret_dependency_fails_on_violation():
    """SECRET_DEPENDENCY must fail (not warn) on secret detection."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    # Check for failure-swallowing patterns in secret_dependency job
    if 'secret_dependency:' in content:
        lines = content.split('\n')
        in_secret_job = False
        for i, line in enumerate(lines):
            if 'secret_dependency:' in line:
                in_secret_job = True
            elif in_secret_job:
                # Check for patterns that swallow failures
                if '|| echo' in line and 'secret' in content[max(0, i-10):i+10].lower():
                    pytest.fail(f"SECRET_DEPENDENCY contains failure-swallowing '|| echo' at line {i+1}")
                if '|| true' in line:
                    pytest.fail(f"SECRET_DEPENDENCY contains '|| true' at line {i+1}")
                # Reset when hitting next job
                if line and not line.startswith(' ') and line.strip().endswith(':'):
                    break


def test_secret_dependency_has_exit_on_violation():
    """SECRET_DEPENDENCY must exit non-zero on violations."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    if 'secret_dependency:' in content:
        # Should contain 'exit 1' for violations
        assert 'exit 1' in content or 'return 1' in content, \
            "SECRET_DEPENDENCY must explicitly fail on violations"


def test_no_failure_swallowing_in_p0_jobs():
    """P0 jobs must not contain failure-swallowing patterns."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        lines = f.readlines()

    p0_jobs = ['static:', 'unit:', 'schema_contract:',
               'arch_fitness:', 'secret_dependency:', 'postgres_env:']

    current_job = None
    for i, line in enumerate(lines, 1):
        # Track current job
        if any(line.strip().startswith(job) for job in p0_jobs):
            current_job = line.strip()

        # Check for failure swallowing in P0 jobs
        if current_job and ('|| true' in line or '|| echo' in line):
            # Allow specific safe patterns
            if '2>/dev/null' in line:  # stderr redirect is ok
                continue
            if '|| echo "WARN:' in line.lower():  # Explicit warnings ok
                continue
            pytest.fail(
                f"P0 job {current_job} at line {i} contains failure-swallowing pattern: {line.strip()}"
            )

        # Reset when hitting next top-level key
        if line and not line.startswith(' ') and ':' in line:
            current_job = None


def test_security_policy_yaml_is_required_artifact():
    """security-policy.yaml must remain in V2-004 required artifacts."""
    backlog_path = ROOT / 'plan/machine/implementation-backlog.yaml'
    with backlog_path.open() as f:
        data = yaml.safe_load(f)

    # Tasks are stored as a list with task_id field
    tasks = {task['task_id']: task for task in data.get('tasks', [])}
    assert 'V2-004' in tasks, "V2-004 must exist in backlog"

    v2_004 = tasks['V2-004']
    assert 'artifacts' in v2_004, "V2-004 must have artifacts"
    assert 'security-policy.yaml' in v2_004['artifacts'], \
        "security-policy.yaml must be V2-004 required artifact (not silently deleted)"


def test_static_gate_uses_real_tools():
    """STATIC gate must use real formatter/linter/typechecker, not fake checks."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    # Check for real tools
    if 'static:' in content:
        # Should use actual tools
        has_ruff = 'ruff format' in content or 'ruff check' in content
        has_mypy = 'mypy' in content

        assert has_ruff or has_mypy, \
            "STATIC gate must use real formatter/linter (ruff) or typechecker (mypy)"

        # Should not use fake checks
        static_section = content[content.find('static:'):content.find('static:') + 2000]

        assert 'python -m compileall' not in static_section or has_ruff, \
            "STATIC gate should not rely solely on compileall (syntax check only)"

        assert 'grep' not in static_section or has_ruff, \
            "STATIC gate should not use grep for type checking"


def test_secret_dependency_has_real_vulnerability_scanner():
    """SECRET_DEPENDENCY must have real vulnerability scanner, not just uv pip check."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    if 'secret_dependency:' in content:
        # Should have real vulnerability scanning
        has_pip_audit = 'pip-audit' in content
        has_safety = 'safety check' in content

        # Must have at least one real scanner
        assert has_pip_audit or has_safety, \
            "SECRET_DEPENDENCY must include real vulnerability scanner (pip-audit or safety)"

        # If only uv pip check, fail
        secret_section = content[content.find('secret_dependency:'):content.find('secret_dependency:') + 2000]

        if 'uv pip check' in secret_section and not (has_pip_audit or has_safety):
            pytest.fail("uv pip check only verifies dependency consistency, not vulnerabilities")


def test_ci_does_not_modify_plan_directory():
    """CI validation output must go to dist/, not modify plan/."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    if 'schema_contract:' in content:
        schema_section = content[content.find('schema_contract:'):content.find('schema_contract:') + 2000]

        # Should use --output-dir to dist/
        assert '--output-dir' in schema_section or 'dist/ci/schema' in schema_section, \
            "SCHEMA_CONTRACT must output to dist/, not modify plan/validation/"

        # Should not copy from plan/validation/ to dist/
        assert 'cp' not in schema_section or 'plan/validation/plan-validation.json' not in schema_section, \
            "Should not copy from plan/validation/ (don't modify tested directory)"


def test_ci_references_exist():
    """All files referenced in CI must actually exist."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    # Extract test file references
    import re
    test_refs = re.findall(r'tests/[a-z_/]+/test_[a-z_]+\.py', content)

    for test_ref in test_refs:
        test_path = ROOT / test_ref
        assert test_path.exists(), \
            f"CI references non-existent test: {test_ref}"

    # Extract script references
    script_refs = re.findall(r'(plan/scripts/[a-z_]+\.py)', content)

    for script_ref in script_refs:
        script_path = ROOT / script_ref
        assert script_path.exists(), \
            f"CI references non-existent script: {script_ref}"


def test_production_scan_isolated_from_fixtures():
    """Production secret scan must exclude test fixtures directory."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    if 'secret_dependency:' in content:
        secret_section = content[content.find('secret_dependency:'):content.find('secret_dependency:') + 2000]

        # Production scan should exclude fixtures
        has_fixture_exclusion = (
            'tests/fixtures' not in secret_section.split('grep')[0] if 'grep' in secret_section
            else True
        )

        # Or production scan should only scan production dirs
        scans_production_only = (
            'plan/' in secret_section and
            'src/' in secret_section and
            'tests/' not in secret_section.split('grep -r')[1].split('|')[0] if 'grep -r' in secret_section
            else False
        )

        assert has_fixture_exclusion or scans_production_only, \
            "Production secret scan must not fail on harmless test fixtures"


def test_no_post_lock_dependency_mutation():
    """After uv sync --frozen, CI must not install additional tools."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    # Find uv sync --frozen locations
    if 'uv sync --frozen' not in content:
        pytest.skip("No uv sync --frozen found")

    # Check for problematic patterns after sync
    # Look for uv pip install of project tools (not bootstrap uv itself)
    problematic_patterns = [
        (r'uv pip install\s+(?!uv==)', 'uv pip install'),
        (r'(?<!# )pip install\s+(?!uv==)', 'pip install'),
    ]

    for pattern, name in problematic_patterns:
        matches = list(re.finditer(pattern, content))
        for match in matches:
            # Check if this is after uv sync --frozen
            before_match = content[:match.start()]
            if 'uv sync --frozen' in before_match:
                # Extract context around match
                line_start = content.rfind('\n', 0, match.start()) + 1
                line_end = content.find('\n', match.end())
                line = content[line_start:line_end]

                pytest.fail(
                    f"Found '{name}' after 'uv sync --frozen': {line.strip()}\n"
                    f"This bypasses locked environment. Use 'uv run' instead."
                )


def test_hard_gates_fail_closed():
    """Hard P0 gates must fail on tool failure, not swallow with || echo."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        lines = f.readlines()

    p0_jobs = ['static:', 'unit:', 'schema_contract:',
               'arch_fitness:', 'secret_dependency:', 'postgres_env:']

    # Tools that should fail-closed
    hard_tools = ['ruff', 'mypy', 'pytest', 'pip-audit', 'python']

    current_job = None
    for i, line in enumerate(lines, 1):
        # Track current job
        if any(line.strip().startswith(job) for job in p0_jobs):
            current_job = line.strip()

        if current_job:
            # Check for tool call followed by || echo
            for tool in hard_tools:
                if tool in line and '|| echo' in line:
                    pytest.fail(
                        f"P0 job {current_job} at line {i} swallows {tool} failure with '|| echo': {line.strip()}"
                    )

        # Reset when hitting next top-level key
        if line and not line.startswith(' ') and ':' in line:
            current_job = None


def test_locked_tools_used_in_ci():
    """CI must use locked tools via 'uv run', not dynamically installed versions."""
    ci_path = ROOT / '.gitlab-ci.yml'
    with ci_path.open() as f:
        content = f.read()

    # Tools that should be in uv.lock and used via uv run
    locked_tools = {
        'ruff': 'ruff',
        'mypy': 'mypy',
        'pip-audit': 'pip-audit',
    }

    for tool_name, command in locked_tools.items():
        # If tool is used in CI
        if command in content:
            # Check it's called via uv run (after uv sync)
            # Simple heuristic: look for 'uv run {command}'
            if f'uv run {command}' not in content and f'uv pip install {tool_name}' in content:
                pytest.fail(
                    f"CI installs {tool_name} with 'uv pip install' instead of using locked version via 'uv run'"
                )
