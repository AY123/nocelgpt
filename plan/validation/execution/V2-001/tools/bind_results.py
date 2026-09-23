#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bind actual V2-001 local results to the committed implementation; no CI claims."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shlex
import subprocess
import xml.etree.ElementTree as ET
import yaml

root = Path.cwd()
plan = root / 'plan'
base = plan / 'validation/execution/V2-001'
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert revision == '390aa0f4f28068fdd146fca3eb98df1a5ec1a334'
assert not (base / 'code-evidence.yaml').exists(), 'Do not overwrite historical evidence'
assert not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], text=True).strip(), 'Tracked source changed after formal tests'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
artifact = lambda path: {'ref': str(path.relative_to(plan)), 'sha256': sha(path)}
raw_names = ['025_formal_locked_sync', '026_formal_package_import', '027_formal_discovery',
             '028_formal_pytest', '029_formal_plan_check', '030_formal_self_test',
             '031_formal_governance', '032_formal_ai_execution']
raw = {}
for name in raw_names:
    result = json.loads((base / 'raw' / (name + '.json')).read_text())
    assert result['exit_code'] == 0 and result['repository_revision'] == revision, name
    raw[name] = result
suite = ET.parse(base / 'checks/formal/pytest.xml').getroot().find('testsuite')
assert int(suite.attrib['tests']) == 15
assert all(int(suite.attrib.get(k, '0')) == 0 for k in ('failures', 'errors', 'skipped'))
for rel, count in [('formal-governance/governance-regression.json', 39), ('formal-ai/ai-execution-regression.json', 36)]:
    obj = json.loads((base / 'checks' / rel).read_text())
    assert obj['status'] == 'PASS' and obj['test_count'] == count
selftest = json.loads((base / 'checks/formal-self/validator-self-test.json').read_text())
assert selftest['status'] == 'PASS' and len(selftest['cases']) == 32
assert json.loads((base / 'checks/formal-plan/plan-validation.json').read_text())['status'] == 'PASS'

paths = ['pyproject.toml', 'uv.lock', '.python-version', 'compose.yaml', 'src/anovel/__init__.py',
         'scripts/check_postgres.py', 'tests/integration/test_repository_bootstrap.py',
         'tests/integration/test_postgres_environment.py', 'README.md', '.env.example',
         'docs/repository-layout-migration.md', 'plan/scripts/test_ai_execution.py']
index = []
artifacts = []
for name in paths:
    contents = subprocess.check_output(['git', 'show', revision + ':' + name])
    assert contents == (root / name).read_bytes(), name
    dest = base / 'artifacts/code' / (name + '.txt')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(contents)
    item = artifact(dest)
    artifacts.append(item)
    index.append({'source_path': name, 'source_revision': revision, **item})
(base / 'artifacts/code-index.json').write_text(json.dumps(index, indent=2) + '\n')
artifacts.append(artifact(base / 'artifacts/code-index.json'))

def record(filename, kind, artifacts, **extra):
    obj = dict(record_type='plan_execution_evidence', schema_version='1.0',
               evidence_id='V2-001-' + filename.removesuffix('.yaml') + '-' + revision[:12],
               evidence_type=kind, subject_id='V2-001', revision=revision, status='PASS',
               producer='Codex main implementer / local verifier; not independent human or remote CI',
               executed_at=datetime.now(timezone.utc).isoformat(),
               environment_fingerprint='macOS15.1.1-arm64; CPython3.12.14; uv0.12.17; Docker29.4.0; Compose5.1.2; PostgreSQL170011',
               artifacts=artifacts, input_evidence_refs=[], **extra)
    path = base / filename
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False))
    return str(path.relative_to(plan))

code = record('code-evidence.yaml', 'CODE', artifacts)
tests = record('test-result.yaml', 'TEST_RESULT',
    [artifact(base / 'raw' / (name + '.json')) for name in raw_names[:4]] + [artifact(base / 'checks/formal/pytest.xml')],
    check_ids=['AT-V2-001-' + str(i).zfill(2) for i in range(1, 6)],
    command=shlex.join(raw['028_formal_pytest']['command']), exit_code=0)
governance = record('governance-result.yaml', 'TEST_RESULT',
    [artifact(base / 'raw' / (name + '.json')) for name in raw_names[4:]] +
    [artifact(base / 'checks' / name) for name in ['formal-plan/plan-validation.json',
        'formal-self/validator-self-test.json', 'formal-governance/governance-regression.json', 'formal-ai/ai-execution-regression.json']],
    check_ids=['LOCAL_PLAN_CHECK', 'LOCAL_VALIDATOR_SELF_TEST_32', 'LOCAL_GOVERNANCE_39', 'LOCAL_AI_EXECUTION_36'],
    command=shlex.join(raw['029_formal_plan_check']['command']), exit_code=0)
# The supplementary command lines and all outputs are independently preserved in
# artifacts. This aggregation is not a command runner or a remote attestation.
for name in ['test-result.yaml', 'governance-result.yaml']:
    path = base / name
    obj = yaml.safe_load(path.read_text()); obj['input_evidence_refs'] = [code]
    path.write_text(yaml.safe_dump(obj, allow_unicode=True, sort_keys=False))

p = plan / 'machine/implementation-backlog.yaml'
text = p.read_text()
needle = '    code: []\n    tests: []\n    ci: []\n    acceptance: []'
replacement = ('    code:\n    - ref: ' + code + '\n      revision: ' + revision + '\n      status: PASS\n'
    '    tests:\n    - ref: ' + tests + '\n      revision: ' + revision + '\n      status: PASS\n'
    '    - ref: ' + governance + '\n      revision: ' + revision + '\n      status: PASS\n'
    '    ci: []\n    acceptance: []')
assert needle in text
p.write_text(text.replace(needle, replacement, 1))
p = plan / 'machine/test-catalog.yaml'
text = p.read_text(); p.write_text(text.replace('  execution_evidence: []', '  execution_evidence:\n  - ' + tests, 1))

p = base / 'execution-packet.yaml'
packet = yaml.safe_load(p.read_text())
packet['handoff'].update(current_step='STOPPED AS REQUESTED: V2-001 IMPLEMENTED; local results bound to 390aa0f4f28068fdd146fca3eb98df1a5ec1a334; no next task started',
    completed_steps=packet['handoff']['completed_steps'] + ['Committed actual implementation', 'Formal local tests on implementation revision: pytest15, self32, governance39, AI36, plan check PASS', 'Bound CODE and TEST_RESULT artifacts to implementation revision'],
    pending_items=['V2-001 remains IMPLEMENTED: real CI_RUN and final ACCEPTANCE_RECORD absent', 'Recommend V2-002 only; requires a separately authorized task scope', 'V2-003 architecture and V2-004 trusted CI/permissions remain OPEN; P1 forbidden until G-P0'],
    last_check={'status':'PASS', 'artifacts':[artifact(base / 'raw/028_formal_pytest.json'), artifact(base / 'raw/032_formal_ai_execution.json')], 'missing_artifact_reason':None})
packet['review_notes'].append('Final read-only AI code review found no actionable issue; same AI trust boundary, no independent human/platform/remote CI validation. repository_revision remains original opening baseline; evidence revision is the committed implementation. Stop instruction is preserved; IMPLEMENT identifies the performed action, not authorization to start V2-002.')
p.write_text(yaml.safe_dump(packet, allow_unicode=True, sort_keys=False))
(base / 'raw/code-review.json').write_text(json.dumps({'reviewer':'v2001_final_code_review / AI subagent', 'mode':'read-only', 'reviewed_implementation_revision':revision, 'actionable_findings':[], 'limitations':['same AI trust boundary','no independent human verification','did not rerun Docker tests','no other-platform or remote CI validation']}, indent=2) + '\n')
print(json.dumps({'implementation_revision':revision,'state':'IMPLEMENTED','code':code,'tests':[tests,governance],'ci':[],'acceptance':[]}))
