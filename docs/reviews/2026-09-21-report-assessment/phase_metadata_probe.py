#!/usr/bin/env python3
"""Nine isolated observations for PA-01; synthetic evidence, no engineering closure."""
import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, default=Path('/Users/angyang/Documents/AI/ANovelOS'))
parser.add_argument('--output', type=Path, default=Path('/tmp/anovel_audit_report_phase_probe.json'))
args = parser.parse_args()
sys.path.insert(0, str((args.repo/'plan/scripts').resolve()))
from test_governance import GovernanceTests

fixture = GovernanceTests(methodName='test_valid_p0_completion_chain')
try:
    fixture.setUp()
    base = deepcopy(fixture.data)
    results = [{'case': 'positive_synthetic_p0_chain_and_deferred_future_phases', 'errors': fixture.errors()}]
    for phase_id in ('P13', 'P14'):
        for state in ('IN_PROGRESS', 'VERIFIED'):
            fixture.data = deepcopy(base)
            phase = next(p for p in fixture.data['phase-gates']['phases'] if p['id'] == phase_id)
            phase['status'] = state
            results.append({'case': f'{phase_id}_{state}_empty_tasks', 'errors': fixture.errors()})
    for milestone_id in ('M11', 'M12'):
        fixture.data = deepcopy(base)
        milestone = next(m for m in fixture.data['milestones']['milestones'] if m['id'] == milestone_id)
        milestone['status'] = 'VERIFIED'
        results.append({'case': f'{milestone_id}_VERIFIED_empty_required_tasks', 'errors': fixture.errors()})
    fixture.data = deepcopy(base)
    fixture.data['phase-gates']['phases'][13]['task_refinement'] = 'READY'
    results.append({'case': 'P13_refinement_READY_but_still_NOT_VERIFIED_and_empty', 'errors': fixture.errors()})
    fixture.data = deepcopy(base)
    fixture.data['phase-gates']['phases'][0]['task_refinement'] = 'DEFERRED_UNPLANNED'
    results.append({'case': 'positive_P0_chain_refinement_field_DEFERRED', 'errors': fixture.errors()})
    report = {'scope': 'PA-01 isolated planning governance observations only; synthetic fixture is not runtime or CI evidence', 'cases': results}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(args.output), 'cases': len(results)}, ensure_ascii=False))
finally:
    fixture.doCleanups()
