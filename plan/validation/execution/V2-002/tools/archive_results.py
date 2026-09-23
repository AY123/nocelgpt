"""Archive real worktree results without pretending the opening HEAD contains new code."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[5]
PLAN = ROOT / 'plan'
BASE = PLAN / 'validation/execution/V2-002'


def artifact(path):
    return {'ref': str(path.relative_to(PLAN)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    assert not (BASE / 'local-results.json').exists(), 'Preserve existing result history'
    summary = json.loads((ROOT / 'dist/validation/v2-002-final-governance/governance-summary.json').read_text())
    entry = json.loads((ROOT / 'dist/validation/v2-002-final-entry.json').read_text())
    assert summary['status'] == entry['status'] == 'PASS'
    assert all(row['exit_code'] == 0 for row in summary['commands'])
    assert entry['command_result']['exit_code'] == 0
    for filename, count in [('contract.xml', 39), ('bootstrap.xml', 5)]:
        suite = ET.parse(BASE / 'checks/final' / filename).getroot().find('testsuite')
        assert int(suite.attrib['tests']) == count
        assert all(int(suite.attrib.get(key, 0)) == 0 for key in ('failures','errors','skipped'))
    shutil.copytree(ROOT / 'dist/validation/v2-002-final-governance', BASE / 'checks/final-governance')
    shutil.copyfile(ROOT / 'dist/validation/v2-002-final-entry.json', BASE / 'raw/final-entry.json')
    source_files = ['AGENTS.md','README.md','scripts/task_execution.py','scripts/check_governance.py',
        'tests/contract/test_plan_governance.py','tests/contract/test_task_execution.py',
        'plan/scripts/task_entry.py','plan/scripts/validate_plan.py','plan/scripts/governance_checks.py',
        'plan/scripts/execution_checks.py','plan/scripts/test_ai_execution.py',
        'plan/scripts/test_governance.py','plan/scripts/probe_governance_legacy.py',
        'plan/machine/implementation-backlog.yaml','plan/machine/test-catalog.yaml',
        'plan/machine/ai-execution-policy.yaml','plan/machine/governance-baseline.yaml',
        'plan/schemas/execution-packet.schema.json','plan/schemas/evidence-record.schema.json']
    observed = {item['path']: item['sha256'] for item in entry['after']['files']}
    sources = []
    for name in source_files:
        path = ROOT / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert observed[name] == digest, 'Source changed since final engineering run: '+name
        target = BASE / 'artifacts/code' / (name+'.txt')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        sources.append({'source_path': name, **artifact(target)})
    (BASE / 'artifacts/code-index.json').write_text(json.dumps(sources, ensure_ascii=False, indent=2)+'\n')
    results = {
        'record_type': 'local_worktree_results', 'task_id': 'V2-002', 'status': 'PASS',
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'source_kind': 'WORKTREE_SNAPSHOT',
        'checkout_head': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
        'tested_source_commit': None,
        'limitations': ['Not plan_execution_evidence or a closure witness',
                       'Opening HEAD does not contain this uncommitted implementation',
                       'No remote CI, protected permissions or independent certification',
                       'Subagents interrupted by account limit; primary completed and verified work'],
        'counts': {'contract_pytest':39, 'bootstrap_pytest':5, 'validator_self_test':32,
                   'governance_regression':39, 'ai_execution_regression':36, 'legacy_probes':13},
        'local_scenario_mapping': ['AT-V2-002-'+str(index).zfill(2) for index in range(1,17)],
        'code_snapshots': sources,
        'artifacts': [artifact(BASE / 'checks/final/contract.xml'), artifact(BASE / 'checks/final/bootstrap.xml'),
            artifact(BASE / 'checks/final-governance/governance-summary.json'),
            artifact(BASE / 'raw/final-entry.json'), artifact(BASE / 'raw/fixture-baseline-reproduction.json'),
            artifact(BASE / 'raw/scope-review.json')],
        'remaining': ['Source commit and typed CODE/TEST_RESULT binding', 'Real trusted CI_RUN',
                      'Final acceptance and finding dispositions', 'G-P0/M0 remain NOT_VERIFIED']}
    (BASE / 'local-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')
    path = BASE / 'execution-packet.yaml'
    (BASE / 'snapshots/packet-before-final-handoff.yaml.txt').write_bytes(path.read_bytes())
    packet = yaml.safe_load(path.read_text())
    packet['review_notes'] += [
        'User subsequently said 继续; continued the same V2-002 scope and local execution window. No paid budget, task or phase expansion.',
        'Final source bytes are worktree snapshots checked against the real entry observation. No source commit was made; do not label opening HEAD as the implementation revision.',
        'Subagents hit account usage limits; primary completed implementation/testing. No independent review or successful subagent final audit is claimed.']
    packet['handoff'] = {
        'current_step': 'STOPPED: V2-002 IMPLEMENTED; local commands/tests complete, uncommitted worktree results archived; no next task started',
        'completed_steps': ['Observed clean opening main/HEAD, Plan version and manifest; baseline PASS',
            'Created and validated dedicated PREPARE packet, then passed IMPLEMENT start gate',
            'Reused governance system; integrated normative index, real local action/resume entry and contract tests',
            'Preserved and retrospectively reproduced old fixture failures; all original test assertions retained',
            'Contract tests 39, bootstrap regression 5, self-test 32, governance 39, AI 36, legacy probes 13 PASS',
            'Compared acceptance/scope/protection to opening Git revision; no weakening or other task implementation',
            'Archived exact code bytes, commands, real outputs and worktree context'],
        'pending_items': results['remaining'] + ['V2-003/004 remain OPEN; P1+ forbidden until verified G-P0'],
        'next_action': 'IMPLEMENT',
        'last_check': {'status': 'PASS', 'artifacts': [artifact(BASE / 'local-results.json'),
                        artifact(BASE / 'checks/final-governance/governance-summary.json')], 'missing_artifact_reason': None}}
    path.write_text(yaml.safe_dump(packet, allow_unicode=True, sort_keys=False, width=100000))
    print(json.dumps({'task':'V2-002','state':'IMPLEMENTED','tested_source_commit':None,'counts':results['counts']}))


if __name__ == '__main__':
    main()
