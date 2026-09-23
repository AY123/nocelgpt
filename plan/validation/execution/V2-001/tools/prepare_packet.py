#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create this task's PREPARE record; never starts implementation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import platform
import subprocess
import sys
import yaml

root = Path.cwd()
plan = root/'plan'
base = plan/'validation/execution/V2-001'
if (base/'execution-packet.yaml').exists():
    raise SystemExit('Existing packet: reconcile it, do not overwrite or rerun preparation.')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def run(argv):
    try:
        p = subprocess.run(argv,capture_output=True,text=True,timeout=20)
        return {'argv':argv,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    except OSError as exc:
        return {'argv':argv,'exit_code':127,'stdout':'','stderr':str(exc)}
commands = [run(argv) for argv in [
    ['git','branch','--show-current'], ['git','rev-parse','HEAD'],
    ['git','status','--porcelain=v1'], ['git','diff','--name-status','HEAD'],
    ['git','ls-files','--others','--exclude-standard'], ['uv','--version'],
    ['docker','version','--format','{{json .}}'], ['docker','compose','version']]]
preflight = {'observed_at':datetime.now(timezone.utc).isoformat(), 'commands':commands,
             'note':'First tool inventory was clean; current untracked V2-001 preparation records are this task work.',
             'root_entries':sorted(p.name for p in root.iterdir()),
             'environment':{'platform':platform.platform(),'python':platform.python_version(),
                            'python_executable':sys.executable}}
(base/'raw').mkdir(exist_ok=True)
(base/'raw/preflight.json').write_text(json.dumps(preflight,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(base/'user-request.txt').write_bytes(Path('/Users/angyang/.codex/attachments/77527038-8aea-476a-aaed-d5fbd3cf0755/pasted-text.txt').read_bytes())
reads = ['README.md','AI_EXECUTION_PROTOCOL.md','00_GOVERNANCE_AND_SOURCE_AUTHORITY.md',
         '02_ARCHITECTURE_BASELINE.md','07_PLATFORM_SECURITY_AND_DELIVERY.md',
         '08_ROADMAP_AND_GATES.md','09_TASK_EXECUTION_GUIDE.md','PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md',
         'machine/implementation-backlog.yaml','machine/phase-gates.yaml','machine/governance-baseline.yaml',
         'machine/decision-register.yaml','machine/test-catalog.yaml','machine/ai-execution-policy.yaml',
         'templates/EXECUTION_PACKET.yaml','schemas/execution-packet.schema.json']
readset = [{'path':'AGENTS.md','sha256':sha(root/'AGENTS.md')}]
readset += [{'path':'plan/'+p,'sha256':sha(plan/p)} for p in reads]
(base/'raw/readset-initial.json').write_text(json.dumps(readset,indent=2)+'\n')
bpath = plan/'machine/implementation-backlog.yaml'
text = bpath.read_text()
assert '  execution_packet_ref: null' in text
bpath.write_text(text.replace('  execution_packet_ref: null',
    '  execution_packet_ref: validation/execution/V2-001/execution-packet.yaml',1))
back = yaml.safe_load(bpath.read_text()); task=back['tasks'][0]
sys.path.insert(0,str(plan/'scripts'))
import validate_plan as validator
for name,value in validator.expected_views(validator.load()).items():
    (plan/name).write_text(value)
(plan/'FILE_MANIFEST.json').write_text(json.dumps(validator.build_manifest(),ensure_ascii=False,indent=2)+'\n')
snap=base/'snapshots/prepare'; snap.mkdir(parents=True,exist_ok=True)
inputs=[]
for index,ref in enumerate(dict.fromkeys(task['normative_specs']+reads)):
    target=snap/(str(index).zfill(2)+'-'+Path(ref).name+'.txt')
    target.write_bytes((plan/ref).read_bytes())
    inputs.append({'source_ref':ref,'ref':str(target.relative_to(plan)),'sha256':sha(target)})
fact={'ref':'validation/execution/V2-001/raw/preflight.json','sha256':sha(base/'raw/preflight.json')}
allowed=task['artifacts']+[
    'README.md','.env.example','.gitignore','tests/conftest.py',
    'scripts/check_postgres.py','scripts/test_postgres.py','scripts/check_repository.py',
    'plan/machine/implementation-backlog.yaml','plan/machine/decision-register.yaml',
    'plan/machine/test-catalog.yaml','plan/FILE_MANIFEST.json','plan/generated/',
    'plan/validation/execution/V2-001/','plan/decisions/ADR-001_RUNTIME_AND_LOCKING.md',
    'docs/V2-001_IMPLEMENTATION_REPORT.md']
packet={
    'record_type':'task_execution_packet','schema_version':'1.0','task_id':'V2-001',
    'plan_version':back['version'],'repository_revision':commands[1]['stdout'].strip(),
    'worktree_dirty':True,'plan_manifest_sha256':sha(plan/'FILE_MANIFEST.json'),
    'environment':{'fingerprint':platform.platform()+'; initial local probe',
                   'runtime_versions':{'bootstrap_python':platform.python_version(),
                                       'docker_client':'29.4.0','docker_compose':'5.1.2'},
                   'database_image':None,'ci_context':None},
    'implementer':'Codex main implementer / local operator',
    'verifier':'Codex local tests plus bounded AI review; not independent human or remote CI',
    'owner_role':task['owner_role'],
    'scope':'Only P0/V2-001 bootstrap, ADR-001, package and isolated PostgreSQL tests. No V2-002/003/004 or P1+ implementation; no Provider or publication.',
    'action':'PREPARE','inputs':inputs,'expected_outputs':task['artifacts'],
    'allowed_paths':list(dict.fromkeys(allowed)),'required_decisions':['ADR-001'],
    'claims':[
        {'id':'OBSERVED_ENVIRONMENT','kind':'FACT','statement':'Initial macOS arm64 environment has Python 3.9.6, no uv on PATH, Docker client installed but daemon unavailable.',
         'sources':[fact],'blocks_actions':[],'verification_plan':'Recheck actual binaries, daemon and image before accepting ADR-001.'},
        {'id':'ADR001_PENDING','kind':'UNKNOWN','statement':'Exact runtime, uv and PostgreSQL image digest not yet accepted.',
         'sources':[],'blocks_actions':['IMPLEMENT','LIVE_CALL','CERTIFY'],
         'verification_plan':'Inspect official metadata and local environment; write typed ADR decision before IMPLEMENT.'}],
    'estimate':{'range':None,'unit':None,'assumptions':['Download and daemon availability not yet established'],'confidence':'NOT_ESTIMATED'},
    'budget':{'paid_calls_allowed':False,'model_cost_cap':0,'infrastructure_cap':0,'maximum_attempts':3,'maximum_runtime':10800},
    'stop_conditions':['ADR-001 must be ACCEPTED before IMPLEMENT','No paid provider/infrastructure; budget currency USD',
                       'Only local isolated PostgreSQL; no production credentials or SQLite substitution',
                       'Stop at highest honest V2-001 state; no next task',
                       'Record concrete permission/failure blockers, do not weaken tests'],
    'review_notes':['Support changes are task registration, ADR, generated views, evidence and operating documentation.',
                    'No user source changes existed at initial inventory; preserve archive and local tool configuration.',
                    'An initial inline preparation script failed Python source decoding before execution; the following plan check covered the prior planning baseline only.'],
    'handoff':{'current_step':'PREPARE: inputs read; environment blockers observed; ADR-001 unresolved',
               'completed_steps':['Checked initial clean main and HEAD','Read mandated inputs and task/scenario requirements'],
               'pending_items':['Start and inspect Docker','Resolve/install exact toolchain','Accept ADR-001'],
               'next_action':'PREPARE','last_check':{'status':'FAIL','artifacts':[fact],'missing_artifact_reason':None}}}
(base/'execution-packet.yaml').write_text(yaml.safe_dump(packet,allow_unicode=True,sort_keys=False))
print(json.dumps({'task_status':task['status'],'action':packet['action'],'manifest':packet['plan_manifest_sha256']},indent=2))
