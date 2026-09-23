#!/usr/bin/env python3
"""One-time registration of the actual, committed ADR-001 decision."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import yaml

plan = Path.cwd() / 'plan'
base = plan / 'validation/execution/V2-001'
output = base / 'adr-001-decision.yaml'
if output.exists():
    raise SystemExit('ADR evidence already exists; do not overwrite')
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
adr = plan / 'decisions/ADR-001_RUNTIME_AND_LOCKING.md'
assert subprocess.check_output(['git', 'show', revision + ':plan/decisions/ADR-001_RUNTIME_AND_LOCKING.md']) == adr.read_bytes()
refs = ['decisions/ADR-001_RUNTIME_AND_LOCKING.md'] + [
    'validation/execution/V2-001/raw/' + name + '.json'
    for name in ['005_docker_running_authorized', '006_postgres_pull', '007_postgres_inspect',
                 '009_uv_install_authorized', '010_uv_version', '011_python_install', '012_python_version']]
for ref in refs[1:]:
    assert json.loads((plan / ref).read_text())['exit_code'] == 0
artifacts = [{'ref': ref, 'sha256': hashlib.sha256((plan / ref).read_bytes()).hexdigest()} for ref in refs]
record = dict(record_type='plan_execution_evidence', schema_version='1.0',
    evidence_id='ADR-001-20260922-local', evidence_type='ADR_DECISION', subject_id='ADR-001',
    revision=revision, status='PASS', producer='Codex Implementer under explicit V2-001 authorization',
    executed_at=datetime.now(timezone.utc).isoformat(),
    environment_fingerprint='macOS15.1.1-arm64; Python3.12.14; uv0.12.17; Docker29.4.0; Compose5.1.2',
    artifacts=artifacts, input_evidence_refs=[], decision='ACCEPTED',
    rationale='Committed ADR-001 makes an explicit minimal choice, with real local installation/image evidence. This accepts a decision, not remote CI or task closure.')
output.write_text(yaml.safe_dump(record, allow_unicode=True, sort_keys=False))
path = plan / 'machine/decision-register.yaml'
data = yaml.safe_load(path.read_text())
decision = next(a for a in data['decisions'] if a['id'] == 'ADR-001')
assert decision['status'] == 'REQUIRED'
decision.update(status='ACCEPTED', decision_record=str(output.relative_to(plan)))
path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
path = base / 'execution-packet.yaml'
packet = yaml.safe_load(path.read_text())
(base / 'snapshots/prepare/packet-final.yaml.txt').write_bytes(path.read_bytes())
packet['claims'][1] = dict(id='ADR001_ACCEPTED', kind='FACT',
    statement='ADR-001 is accepted and bound to the real committed decision; toolchain installed and image inspected.',
    sources=[{'ref':str(output.relative_to(plan)), 'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}],
    blocks_actions=[], verification_plan='Implementation and PostgreSQL tests still pending.')
packet['environment'].update(fingerprint=record['environment_fingerprint'],
    runtime_versions={'bootstrap_python':'3.9.6','python':'3.12.14','uv':'0.12.17','docker_client':'29.4.0','docker_compose':'5.1.2'},
    database_image='postgres:17.11-bookworm@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652')
packet['inputs'].append({'source_ref':'decisions/ADR-001_RUNTIME_AND_LOCKING.md','ref':artifacts[0]['ref'],'sha256':artifacts[0]['sha256']})
packet['handoff'].update(current_step='PREPARE: ADR-001 accepted; validate before IMPLEMENT',
    completed_steps=packet['handoff']['completed_steps'] + ['Installed fixed toolchain; Docker running; image digest verified', 'Accepted committed ADR-001'],
    pending_items=['Validate accepted decision and packet', 'Transition V2-001 to IN_PROGRESS / IMPLEMENT'],
    last_check={'status':'PASS','artifacts':artifacts[1:],'missing_artifact_reason':None})
path.write_text(yaml.safe_dump(packet,allow_unicode=True,sort_keys=False))
print(revision)
