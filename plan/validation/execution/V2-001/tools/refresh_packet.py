#!/usr/bin/env python3
"""Snapshot reconciled V2-001 inputs; this is a task-local evidence helper, not a runner."""
from pathlib import Path
import hashlib
import json
import sys
import yaml

root = Path(__file__).resolve().parents[5]
plan = root / 'plan'
base = plan / 'validation/execution/V2-001'
stage = sys.argv[1]
if not stage.replace('-', '').replace('_', '').isalnum():
    raise SystemExit('Use a simple, unique stage name')
snapshot = base / 'snapshots' / stage
snapshot.mkdir()  # Never overwrite a previous snapshot.
packet_path = base / 'execution-packet.yaml'
(snapshot / 'packet-before.yaml.txt').write_bytes(packet_path.read_bytes())
packet = yaml.safe_load(packet_path.read_text())
sys.path.insert(0, str(plan / 'scripts'))
import validate_plan as validator
for ref, content in validator.expected_views(validator.load()).items():
    (plan / ref).write_text(content)
(plan / 'FILE_MANIFEST.json').write_text(json.dumps(validator.build_manifest(), ensure_ascii=False, indent=2) + '\n')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
packet['plan_manifest_sha256'] = sha(plan / 'FILE_MANIFEST.json')
for index, item in enumerate(packet['inputs']):
    dest = snapshot / (str(index).zfill(2) + '-' + Path(item['source_ref']).name + '.txt')
    dest.write_bytes((plan / item['source_ref']).read_bytes())
    item.update(ref=str(dest.relative_to(plan)), sha256=sha(dest))
packet_path.write_text(yaml.safe_dump(packet, allow_unicode=True, sort_keys=False))
print(json.dumps({'stage': stage, 'action': packet['action'], 'manifest': packet['plan_manifest_sha256']}))
