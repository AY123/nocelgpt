"""Task-local actual baseline comparison; not a CI attestation."""
from pathlib import Path
import argparse,ast,copy,hashlib,json,subprocess
from datetime import datetime,timezone
import yaml
R=Path(__file__).resolve().parents[5]
BASE='c6f26c6188f0b6ad82ce73bf04024d1eab96e1cf'
p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args()
if a.output.exists():raise SystemExit('refuse overwrite')
def old(name):return subprocess.check_output(['git','show',BASE+':'+name],cwd=R)
def current(name):return (R/name).read_bytes()
checks=[]
def check(label,ok):checks.append({'check':label,'status':'PASS' if ok else 'FAIL'})
for name in ['plan/machine/ci-gates.yaml','plan/machine/governance-baseline.yaml','plan/machine/phase-gates.yaml','plan/machine/milestones.yaml','plan/machine/authority-policy.yaml','plan/schemas/execution-packet.schema.json','plan/schemas/evidence-record.schema.json','pyproject.toml','uv.lock','.gitignore']:
 check('byte-identical '+name,old(name)==current(name))
check('V2-004 pipeline remains absent, not falsely certified',subprocess.check_output(['git','ls-tree',BASE,'--','.gitlab-ci.yml'],cwd=R)==b'' and not (R/'.gitlab-ci.yml').exists())
for name,key in [('plan/machine/implementation-backlog.yaml','tasks'),('plan/machine/test-catalog.yaml','suites')]:
 before=yaml.safe_load(old(name));after=yaml.safe_load(current(name))
 for value in [before,after]:
  for row in value[key]:
   for metadata in ['status','evidence','execution_evidence','execution_packet_ref']:row.pop(metadata,None)
   if row.get('task_id')=='V2-003' and key=='tasks':row.pop('artifacts',None)
 check('all task identity/dependency/AC and all scenario assertions unchanged '+name,before==after)
name='plan/machine/ai-execution-policy.yaml';before=yaml.safe_load(old(name));after=yaml.safe_load(current(name))
for v in [before,after]:
 for row in v['controls']:
  if row['id'] in ['AI-EXEC-02','AI-EXEC-03']:
   for field in ['local_status','local_scope','p0_enforcement_status','limitation']:row.pop(field)
check('AI obligations, owners, scenarios unchanged',before==after)
name='tests/contract/test_task_execution.py'
def definitions(data):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(data).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name.startswith('test')}
check('every existing task-entry test definition/assertion unchanged',definitions(old(name))==definitions(current(name)))
check('user review file exact protected hash',hashlib.sha256(current('审核报告.txt')).hexdigest()=='215754d0f0024fcc7fdff9b44959671fd4afd0de2a1b34ff65c213ac16b044f1')
check('no production business source change',subprocess.check_output(['git','diff',BASE,'--','src/anovel'],cwd=R)==b'' and subprocess.check_output(['git','ls-files','--others','--exclude-standard','--','src/anovel'],cwd=R)==b'')
result={'record_type':'local_preservation_check','baseline_revision':BASE,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'executed_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'status':'PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL'}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if result['status']=='PASS' else 2)
