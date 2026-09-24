"""Bind successful post-commit local results; never invent CI or acceptance."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,gzip,hashlib,json,platform,subprocess,yaml
R=Path(__file__).resolve().parents[6];P=R/'plan';B=P/'validation/execution/V2-003/followup'
p=argparse.ArgumentParser();p.add_argument('--revision',required=True);a=p.parse_args()
rev=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
assert rev==a.revision,'bind only after execution at the actual source HEAD'
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.write_text(yaml.safe_dump(value,allow_unicode=True,sort_keys=False,width=100000))
def ref(path):return {'ref':str(path.relative_to(P)),'sha256':sha(path.read_bytes())}
for record in ['009_postcommit_tests','010_postcommit_governance','011_postcommit_bootstrap','012_postcommit_preservation','013_postcommit_entry']:
 data=json.loads((B/'raw'/(record+'.json')).read_text());assert data['repository_revision']==rev and data['exit_code']==0,record
out=B/'postcommit';out.mkdir(exist_ok=False)
code_files=['plan/scripts/architecture_checks.py','plan/scripts/change_review.py','plan/scripts/weakening_checks.py','plan/scripts/task_entry.py','scripts/check_architecture.py','scripts/check_changes.py','tests/architecture/test_dependency_boundaries.py','tests/architecture/test_change_review.py','tests/architecture/test_weakening_checks.py','tests/contract/test_task_execution.py','tests/contract/test_plan_governance.py','plan/machine/ai-execution-policy.yaml','plan/machine/implementation-backlog.yaml','plan/schemas/execution-packet.schema.json']
code_artifacts=[];index=[]
for name in code_files:
 data=subprocess.check_output(['git','show',rev+':'+name],cwd=R);assert data==(R/name).read_bytes(),name
 dest=out/'code'/(name+'.txt');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);code_artifacts.append(ref(dest));index.append({'path':name,'sha256':sha(data)})
(out/'code-index.json').write_text(json.dumps({'revision':rev,'files':index},indent=2)+'\n');code_artifacts.append(ref(out/'code-index.json'))
artifacts=[]
for src in sorted((R/'dist/validation/v2-003-followup-postcommit').rglob('*')):
 if not src.is_file():continue
 relative=src.relative_to(R/'dist/validation/v2-003-followup-postcommit');dest=out/'checks'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
 if src.name.startswith('entry') and src.suffix=='.json':
  dest=dest.with_suffix('.json.gz');dest.write_bytes(gzip.compress(src.read_bytes(),mtime=0))
 else:dest.write_bytes(src.read_bytes())
 artifacts.append(ref(dest))
for name in ['009_postcommit_tests','010_postcommit_governance','011_postcommit_bootstrap','012_postcommit_preservation','013_postcommit_entry']:artifacts.append(ref(B/'raw'/(name+'.json')))
common={'record_type':'plan_execution_evidence','schema_version':'1.0','subject_id':'V2-003','revision':rev,'status':'PASS','producer':'Codex primary implementer and local verifier; same operator, no independent review or remote CI','executed_at':datetime.now(timezone.utc).isoformat(),'environment_fingerprint':platform.platform()+'; CPython '+platform.python_version()+'; local locked environment; uv 0.12.17; offline bootstrap'}
code=dict(common,evidence_id='V2-003-followup-code-'+rev[:12],evidence_type='CODE',artifacts=code_artifacts,input_evidence_refs=[]);save(B/'code-evidence.yaml',code)
test=dict(common,evidence_id='V2-003-followup-tests-'+rev[:12],evidence_type='TEST_RESULT',artifacts=artifacts,input_evidence_refs=['validation/execution/V2-003/followup/code-evidence.yaml'],check_ids=['AT-V2-003-'+str(i).zfill(2) for i in range(1,7)],command='Actual argv/stdout/stderr/exit in raw/009..013: architecture+contract pytest, check_governance aggregate, locked offline repository bootstrap, preservation comparison, task_execution run without CLI scope/review flags, automatically consuming packet-bound pins dispatching production architecture CLI',exit_code=0);save(B/'test-result.yaml',test)
p=P/'machine/implementation-backlog.yaml';data=yaml.safe_load(p.read_text());task=next(t for t in data['tasks'] if t['task_id']=='V2-003');task['status']='IMPLEMENTED'
for kind,name in [('code','code-evidence.yaml'),('tests','test-result.yaml')]:task['evidence'][kind]=[{'ref':'validation/execution/V2-003/followup/'+name,'revision':rev,'status':'PASS'}]
assert not task['evidence']['ci'] and not task['evidence']['acceptance'];save(p,data)
p=P/'machine/test-catalog.yaml';data=yaml.safe_load(p.read_text());suite=next(s for s in data['suites'] if s['id']=='AT-V2-003');suite.update(status='IMPLEMENTED',execution_evidence=['validation/execution/V2-003/followup/test-result.yaml']);save(p,data)
p=P/'machine/ai-execution-policy.yaml';data=yaml.safe_load(p.read_text());next(c for c in data['controls'] if c['id']=='AI-EXEC-02')['p0_enforcement_status']='IMPLEMENTED';save(p,data)
print(json.dumps({'bound_revision':rev,'code_artifacts':len(code_artifacts),'test_artifacts':len(artifacts),'task_status':'IMPLEMENTED','ci':[],'acceptance':[]}))
