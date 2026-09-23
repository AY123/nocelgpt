"""Task-local comparison to the actual opening commit; not V2-003 enforcement."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / 'plan/validation/execution/V2-002'
REVISION = '21849ed8919086982dd94d0a4c852db40eca5d40'


def old(name):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', REVISION+':'+name])


def functions(source):
    return {node.name: ast.dump(node) for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef)}


def main():
    packet = yaml.safe_load((BASE / 'execution-packet.yaml').read_text())
    tracked = subprocess.check_output(['git', '-C', str(ROOT), 'diff', '--name-only', REVISION, '-z']).decode().split('\0')
    untracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '--others', '--exclude-standard', '-z']).decode().split('\0')
    paths = sorted(set(tracked+untracked)-{''})
    outside = [name for name in paths if not any(name == allowed or (allowed.endswith('/') and name.startswith(allowed)) for allowed in packet['allowed_paths'])]
    assert outside == [], outside
    before = yaml.safe_load(old('plan/machine/implementation-backlog.yaml'))
    after = yaml.safe_load((ROOT / 'plan/machine/implementation-backlog.yaml').read_text())
    for a, b in zip(before['tasks'], after['tasks'], strict=True):
        assert all(a[key] == b[key] for key in ('task_id','title','phase','dependencies','acceptance_criteria','normative_specs','start_gate','required_decisions','related_findings'))
        if a['task_id'] != 'V2-002':
            assert a == b, a['task_id']
    b_suites = yaml.safe_load(old('plan/machine/test-catalog.yaml'))['suites']
    a_suites = yaml.safe_load((ROOT / 'plan/machine/test-catalog.yaml').read_text())['suites']
    for a, b in zip(b_suites, a_suites, strict=True):
        assert a['scenarios'] == b['scenarios']
        if a['id'] != 'AT-V2-002':
            assert a == b
    unchanged = ['plan/machine/governance-baseline.yaml', 'plan/machine/phase-gates.yaml',
                 'plan/machine/ci-gates.yaml', 'plan/machine/decision-register.yaml',
                 'plan/schemas/evidence-record.schema.json', 'plan/schemas/execution-packet.schema.json',
                 'plan/scripts/execution_checks.py', 'plan/scripts/governance_checks.py']
    for name in unchanged:
        assert old(name) == (ROOT / name).read_bytes(), name
    test_assertions = {}
    for name in ['plan/scripts/test_governance.py', 'plan/scripts/test_ai_execution.py']:
        previous, current = functions(old(name)), functions((ROOT / name).read_text())
        tests = {key: value for key, value in previous.items() if key.startswith('test_')}
        assert all(current.get(key) == value for key, value in tests.items()), name
        test_assertions[name] = len(tests)
    previous = functions(old('plan/scripts/validate_plan.py'))
    current = functions((ROOT / 'plan/scripts/validate_plan.py').read_text())
    for name in ('validate_objects', 'self_test', 'manifest_files', 'expected_views'):
        assert previous[name] == current[name], name
    report = {'scope': 'One-off V2-002 review against opening Git commit; no automatic V2-003 harness or independent review claim',
              'baseline_revision': REVISION, 'status': 'PASS', 'outside_scope': outside,
              'paths': paths, 'unchanged_protection_files': unchanged,
              'preserved_existing_test_bodies': test_assertions,
              'acceptance_scenarios_unchanged': sum(len(s['scenarios']) for s in a_suites),
              'authorized_support_changes': ['actual command integration and resolved normative path enforcement',
                  'minimal synthetic fixture isolation/rebinding, all old assertions unchanged',
                  'V2-001 context-only refresh preserving prior packets and implementation evidence',
                  'documentation/metadata synchronization without reducing acceptance'],
              'files': [{'path': name, 'sha256': hashlib.sha256((ROOT/name).read_bytes()).hexdigest()} for name in paths if (ROOT/name).is_file()]}
    target = BASE / 'raw' / (sys.argv[1] if len(sys.argv) > 1 else 'scope-review.json')
    with target.open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status','outside_scope','preserved_existing_test_bodies','acceptance_scenarios_unchanged')}))


if __name__ == '__main__':
    main()
