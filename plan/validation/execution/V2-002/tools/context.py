#!/usr/bin/env python3
"""Task-local V2-002 preparation/reconciliation; preserves every prior packet."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import platform
import shutil
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[5]
PLAN = ROOT / 'plan'
BASE = PLAN / 'validation/execution/V2-002'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, obj):
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False, width=100000))


def refresh(stage):
    # Reconcile both active P0 packets because the shared backlog/manifest changed.
    # V2-001 remains stopped; no status, implementation or historic evidence changes.
    sys.path.insert(0, str(PLAN / 'scripts'))
    import validate_plan as validator
    for ref, value in validator.expected_views(validator.load()).items():
        (PLAN / ref).write_text(value)
    (PLAN / 'FILE_MANIFEST.json').write_text(json.dumps(validator.build_manifest(), ensure_ascii=False, indent=2)+'\n')
    for tid in ('V2-001', 'V2-002'):
        path = PLAN / f'validation/execution/{tid}/execution-packet.yaml'
        packet = yaml.safe_load(path.read_text())
        dest = BASE / 'snapshots' / stage / tid
        dest.mkdir(parents=True)  # Existing stage is an error, never overwrite history.
        (dest / 'packet-before.yaml.txt').write_bytes(path.read_bytes())
        for index, item in enumerate(packet['inputs']):
            snapshot = dest / (f'{index:02d}-' + Path(item['source_ref']).name + '.txt')
            snapshot.write_bytes((PLAN / item['source_ref']).read_bytes())
            item.update(ref=str(snapshot.relative_to(PLAN)), sha256=sha(snapshot))
        packet['plan_manifest_sha256'] = sha(PLAN / 'FILE_MANIFEST.json')
        packet['review_notes'].append(f'V2-002 {stage}: reconciled live inputs/manifest; previous packet preserved under V2-002 snapshots. No V2-001 work or evidence recertification.')
        save(path, packet)


def prepare():
    path = BASE / 'execution-packet.yaml'
    if path.exists():
        raise SystemExit('Existing V2-002 packet; reconcile instead of recreating.')
    (BASE / 'raw').mkdir(parents=True, exist_ok=True)
    commands = []
    for argv in (['git', 'branch', '--show-current'], ['git', 'rev-parse', 'HEAD'],
                 ['git', 'status', '--porcelain=v1'], ['git', 'diff', '--name-status', 'HEAD']):
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=True)
        commands.append({'argv': argv, 'exit_code': result.returncode, 'stdout': result.stdout})
    baseline = json.loads((ROOT / 'dist/validation/v2-002-baseline/plan-validation.json').read_text())
    assert baseline['status'] == 'PASS' and baseline['validated_worktree_dirty'] is False
    shutil.copyfile(ROOT / 'dist/validation/v2-002-baseline/plan-validation.json', BASE / 'raw/baseline-plan-validation.json')
    preflight = {'observed_at': datetime.now(timezone.utc).isoformat(), 'commands': commands,
                 'initial_baseline': baseline, 'environment': platform.platform(),
                 'python': platform.python_version(), 'python_executable': sys.executable,
                 'note': 'Initial read-only inventory clean; current untracked preparation helper belongs to V2-002.'}
    (BASE / 'raw/preflight.json').write_text(json.dumps(preflight, ensure_ascii=False, indent=2)+'\n')
    backlog_path = PLAN / 'machine/implementation-backlog.yaml'
    backlog = yaml.safe_load(backlog_path.read_text())
    task = next(t for t in backlog['tasks'] if t['task_id'] == 'V2-002')
    assert task['status'] == 'OPEN' and task['execution_packet_ref'] is None
    task['execution_packet_ref'] = 'validation/execution/V2-002/execution-packet.yaml'
    save(backlog_path, backlog)
    refs = list(dict.fromkeys(task['normative_specs'] + [
        'README.md', 'machine/implementation-backlog.yaml', 'machine/test-catalog.yaml',
        'machine/decision-register.yaml', 'machine/ai-execution-policy.yaml',
        'machine/phase-gates.yaml', 'machine/governance-baseline.yaml', 'machine/ci-gates.yaml',
        'machine/authority-policy.yaml', 'machine/external-practice-register.yaml',
        'machine/source-register.yaml', 'machine/remediation-register.yaml',
        'schemas/execution-packet.schema.json', 'schemas/evidence-record.schema.json',
        'templates/EXECUTION_PACKET.yaml', 'templates/AI_HANDOFF_RECORD.yaml']))
    allowed = list(dict.fromkeys(task['artifacts'] + [
        'scripts/task_execution.py', 'scripts/check_governance.py', 'plan/scripts/task_entry.py',
        'tests/contract/', 'plan/scripts/probe_governance_legacy.py',
        'plan/README.md', 'plan/09_TASK_EXECUTION_GUIDE.md', 'plan/PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md',
        'plan/machine/test-catalog.yaml', 'plan/FILE_MANIFEST.json', 'plan/generated/',
        'plan/validation/execution/V2-002/', 'plan/validation/execution/V2-001/execution-packet.yaml',
        'docs/V2-002_IMPLEMENTATION_REPORT.md']))
    packet = {
        'record_type': 'task_execution_packet', 'schema_version': '1.0', 'task_id': 'V2-002',
        'plan_version': backlog['version'], 'repository_revision': commands[1]['stdout'].strip(),
        'worktree_dirty': True, 'plan_manifest_sha256': sha(PLAN / 'FILE_MANIFEST.json'),
        'environment': {'fingerprint': platform.platform()+'; local CPython '+platform.python_version(),
                        'runtime_versions': {'python': platform.python_version(), 'uv': '0.12.17'},
                        'database_image': None, 'ci_context': None},
        'implementer': 'Codex primary implementer / local operator',
        'verifier': 'Codex local tests and bounded AI review; shared trust boundary, not independent certification',
        'owner_role': task['owner_role'],
        'scope': 'Only P0 V2-002: reuse normative validation, engineering command integration and local action/resume checks. No V2-003/004 or P1+, paid Provider, deployment or remote changes. Currency USD; zero spend.',
        'action': 'PREPARE', 'inputs': [{'source_ref': ref, 'ref': ref, 'sha256': sha(PLAN / ref)} for ref in refs],
        'expected_outputs': task['artifacts'] + ['scripts/task_execution.py', 'scripts/check_governance.py', 'plan/scripts/task_entry.py'],
        'allowed_paths': allowed, 'required_decisions': task['required_decisions'],
        'claims': [{'id': 'BASELINE', 'kind': 'FACT',
                    'statement': 'Clean initial main at 21849ed8919086982dd94d0a4c852db40eca5d40; Plan 1.3.0 PASS; V2-002 OPEN with no dependencies/required ADR; P0 entry ready. V2-001 IMPLEMENTED, CI/acceptance absent.',
                    'sources': [{'ref': 'validation/execution/V2-002/raw/preflight.json', 'sha256': sha(BASE / 'raw/preflight.json')}],
                    'blocks_actions': [], 'verification_plan': 'Full plan checks before IMPLEMENT; preserve missing remote CI status.'}],
        'estimate': {'range': None, 'unit': None, 'assumptions': ['Reuse installed locked environment and existing governance logic'], 'confidence': 'NOT_ESTIMATED'},
        'budget': {'paid_calls_allowed': False, 'model_cost_cap': 0, 'infrastructure_cap': 0, 'maximum_attempts': 5, 'maximum_runtime': 14400},
        'stop_conditions': ['Stop at highest legal V2-002 state; absent remote CI prevents VERIFIED/CLOSED.',
                            'No other task implementation, paid calls or gate weakening.', 'Preserve actual failures, user changes and prior evidence.'],
        'review_notes': ['User explicitly authorized V2-002 and normal task steps. Existing V2-001 active packet must track shared input changes; only its context is reconciled.',
                         'Normative registry remains backlog normative_specs plus existing source/authority registers; no parallel governance system.',
                         'Any fixture isolation correction retains positive controls and all rejection assertions. Minimum baseline/acceptance remains unchanged.'],
        'handoff': {'current_step': 'PREPARE: baseline checked; implementation has not started',
                    'completed_steps': ['Read required handoff and current normative task/scenario/gate policies', 'Observed actual Git/environment and baseline plan PASS'],
                    'pending_items': ['Validate PREPARE packet', 'Confirm IMPLEMENT gate then integrate commands and tests', 'Real CI and final acceptance remain deferred to P0 delivery'],
                    'next_action': 'PREPARE', 'last_check': {'status': 'PASS', 'artifacts': [{'ref': 'validation/execution/V2-002/raw/baseline-plan-validation.json', 'sha256': sha(BASE / 'raw/baseline-plan-validation.json')}], 'missing_artifact_reason': None}}}
    save(path, packet)
    refresh('prepare')


if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'implement':
        report = json.loads((BASE / 'checks/prepare/plan-validation.json').read_text())
        assert report['status'] == 'PASS'
        bpath = PLAN / 'machine/implementation-backlog.yaml'
        backlog = yaml.safe_load(bpath.read_text())
        task = next(t for t in backlog['tasks'] if t['task_id'] == 'V2-002')
        assert task['status'] == 'OPEN' and not task['dependencies'] and not task['required_decisions']
        task['status'] = 'IN_PROGRESS'
        save(bpath, backlog)
        ppath = BASE / 'execution-packet.yaml'
        packet = yaml.safe_load(ppath.read_text())
        (BASE / 'snapshots/prepare/packet-passed.yaml.txt').write_bytes(ppath.read_bytes())
        packet['action'] = packet['handoff']['next_action'] = 'IMPLEMENT'
        packet['handoff']['current_step'] = 'IMPLEMENT gate pending; PREPARE validated'
        packet['handoff']['completed_steps'].append('PREPARE packet validated with current inputs and P0 entry')
        save(ppath, packet)
        refresh('implementation-start')
    else:
        refresh(sys.argv[1])
