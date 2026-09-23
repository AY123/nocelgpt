#!/usr/bin/env python3
"""Audit a plan in disposable copies. Never mutate the source plan.

Requires the same PyYAML/jsonschema dependencies as the plan validator.
The synthetic closure fixtures are NOT engineering/CI evidence.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import yaml

sys.dont_write_bytecode = True


def inventory(plan):
    return {str(p.relative_to(plan)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(plan.rglob('*')) if p.is_file()
            and p.name != '.DS_Store' and '__pycache__' not in p.parts
            and 'validation' not in p.relative_to(plan).parts}


def task(data, number):
    return next(t for t in data['implementation-backlog']['tasks']
                if t['task_id'] == f'V2-{number:03d}')


def suite(data, number):
    return next(t for t in data['test-catalog']['suites']
                if t['task_id'] == f'V2-{number:03d}')


def synthetic_close(data, numbers):
    # Existing README is intentionally used to expose untyped evidence handling.
    for number in numbers:
        t = task(data, number)
        t['status'] = 'CLOSED'
        t['evidence'] = {kind: [{'ref': 'README.md', 'revision': 'SYNTHETIC-NOT-A-COMMIT', 'status': 'PASS'}]
                         for kind in ('code', 'tests', 'ci', 'acceptance')}
        suite(data, number).update(status='VERIFIED', execution_evidence=['README.md'])
        for adr in data['decision-register']['decisions']:
            if adr['id'] in t['required_decisions']:
                adr.update(status='ACCEPTED', decision_record='templates/ADR.md')


def p0_closed(data):
    synthetic_close(data, range(1, 5))


def milestone_shrink(data):
    synthetic_close(data, [1])
    data['milestones']['milestones'][6].update(
        required_tasks=['V2-001'], status='VERIFIED', evidence_refs=['README.md'])


def missing_phase_ref(data):
    p0_closed(data)
    data['phase-gates']['phases'][0].update(status='VERIFIED', evidence_refs=['validation/DOES-NOT-EXIST.json'])


def readiness_bypass(data):
    p0_closed(data)
    data['phase-gates']['phases'][0].update(status='VERIFIED', evidence_refs=['README.md'])
    task(data, 5).update(status='IN_PROGRESS', readiness='PLANNED')


def adr_bypass(data):
    task(data, 1).update(status='IMPLEMENTED', required_decisions=[])


def unknown_defect_closed(data):
    synthetic_close(data, [2])


def change_entry_status(data):
    data['phase-gates']['entry_gate']['status'] = 'BLOCKED'
    task(data, 1)['status'] = 'IN_PROGRESS'


def reconcile_fixture_inputs(data, plan):
    """Refresh only incidental bytes changed by fixture YAML serialization.

    The copied task/action/ADR/evidence declarations remain untouched, including
    every injected defect. This is not available to real execution as a bypass.
    """
    for item in data['implementation-backlog']['tasks']:
        ref = item.get('execution_packet_ref')
        if item['status'] not in {'OPEN', 'IN_PROGRESS', 'IMPLEMENTED'} or not ref:
            continue
        path = plan / ref
        if not path.is_file():
            continue
        packet = yaml.safe_load(path.read_text())
        packet['plan_manifest_sha256'] = hashlib.sha256((plan / 'FILE_MANIFEST.json').read_bytes()).hexdigest()
        for source in packet['inputs']:
            live = plan / source['source_ref']
            snapshot = plan / source['ref']
            if live.is_file() and snapshot.is_file():
                snapshot.write_bytes(live.read_bytes())
                source['sha256'] = hashlib.sha256(live.read_bytes()).hexdigest()
        path.write_text(yaml.safe_dump(packet, allow_unicode=True, sort_keys=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1]/'validation/governance-probe-v1.2.json')
    args = ap.parse_args()
    source = args.plan.resolve()
    before = inventory(source)
    spec = importlib.util.spec_from_file_location('audited_validator', source/'scripts/validate_plan.py')
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    baseline = validator.load()
    baseline_errors = validator.validate_objects(baseline) + validator.check_files(baseline, validator.expected_views(baseline))
    original_self_tests = validator.self_test(baseline)
    cases = [
        ('CONTROL-VALID', 'Unmodified current plan', 'ACCEPT', lambda d: None),
        ('CONTROL-CI-FAIL', 'A hard CI gate is changed to allow_failure=true', 'REJECT',
         lambda d: d['ci-gates']['gates'][0].update(allow_failure=True)),
        ('CONTROL-LOCAL-REF', 'Task normative reference does not exist', 'REJECT',
         lambda d: task(d, 1)['normative_specs'].append('DOES-NOT-EXIST.md')),
        ('PROBE-01', 'All mandatory CI gates removed', 'REJECT',
         lambda d: d['ci-gates'].update(gates=[])),
        ('PROBE-02', 'Mandatory P0 CI gates silently postponed to P14', 'REJECT',
         lambda d: [g.update(activation_phase='P14') for g in d['ci-gates']['gates']]),
        ('PROBE-03', 'Suite declared VERIFIED with nonexistent execution evidence', 'REJECT',
         lambda d: suite(d, 1).update(status='VERIFIED', execution_evidence=['validation/DOES-NOT-EXIST.json'])),
        ('PROBE-04', 'Remove required ADR backlink and mark task IMPLEMENTED', 'REJECT', adr_bypass),
        ('PROBE-05', 'Shrink 10-chapter milestone to bootstrap and mark it VERIFIED', 'REJECT', milestone_shrink),
        ('PROBE-06', 'P0 declared VERIFIED with nonexistent phase evidence', 'REJECT', missing_phase_ref),
        ('PROBE-07', 'README and PROPOSED ADR template used as P0 closure evidence', 'REJECT', p0_closed),
        ('PROBE-08', 'Start a P1 task while its readiness remains PLANNED', 'REJECT', readiness_bypass),
        ('PROBE-09', 'Close task while all related findings remain open without disposition', 'REJECT', unknown_defect_closed),
        ('PROBE-10', 'P0 task starts while entry gate is explicitly BLOCKED', 'REJECT', change_entry_status),
    ]
    results = []
    for case_id, description, expected, mutate in cases:
        data = deepcopy(baseline)
        mutate(data)
        with tempfile.TemporaryDirectory(prefix='anovel-plan-audit-') as tmp:
            sandbox = Path(tmp)/'plan'
            shutil.copytree(source, sandbox, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
            for name in validator.NAMES:
                (sandbox/'machine'/f'{name}.yaml').write_text(yaml.safe_dump(data[name], allow_unicode=True, sort_keys=False))
            # Explicit regeneration is the documented way to submit intentional edits.
            # Regenerating hashes is not a bypass: semantic checks should still reject invalid states.
            regen = subprocess.run([sys.executable, '-B', str(sandbox/'scripts/validate_plan.py'), '--write-views'],
                                   cwd=tmp, capture_output=True, text=True)
            reconcile_fixture_inputs(data, sandbox)
            check = subprocess.run([sys.executable, '-B', str(sandbox/'scripts/validate_plan.py'), '--check'],
                                   cwd=tmp, capture_output=True, text=True)
            try:
                report = json.loads(check.stdout)
            except json.JSONDecodeError:
                report = {'status': 'ERROR', 'errors': [check.stdout, check.stderr]}
            actual = 'ACCEPT' if check.returncode == 0 and report.get('status') == 'PASS' else 'REJECT'
            results.append({'id': case_id, 'description': description, 'expected': expected,
                            'actual': actual, 'finding_reproduced': expected == 'REJECT' and actual == 'ACCEPT',
                            'regenerate_exit': regen.returncode, 'check_exit': check.returncode,
                            'reported_status': report.get('status'), 'errors': report.get('errors', [])})
    after = inventory(source)
    output = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'scope': 'Plan governance mutation probes only; no actual engineering task or phase was completed',
              'source_plan_version': baseline['implementation-backlog']['version'], 'source_manifest_sha256': before['FILE_MANIFEST.json'],
              'source_plan_unchanged': before == after, 'source_inventory': before,
              'baseline_errors': baseline_errors,
              'existing_self_tests': {'count': len(original_self_tests),
                                      'all_pass': all(r['expected'] == r['actual'] for r in original_self_tests)},
              'case_count': len(results), 'unexpected_acceptances': sum(r['finding_reproduced'] for r in results),
              'cases': results}
    output['status'] = 'PASS' if not baseline_errors and all(c['expected'] == c['actual'] for c in results) and all(r['expected'] == r['actual'] for r in original_self_tests) else 'FAIL'
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in output.items() if k not in {'source_inventory','cases'}}, ensure_ascii=False, indent=2))
    for row in results:
        print(f"{row['id']}: expected={row['expected']} actual={row['actual']}")
    assert before == after, 'Source plan mutated'
    return 0 if output['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
