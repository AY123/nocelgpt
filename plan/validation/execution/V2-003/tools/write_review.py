"""Encode explicit same-operator technical dispositions for reviewed changes only."""
from pathlib import Path
import argparse,hashlib,json,sys
R=Path(__file__).resolve().parents[5];B=R/'plan/validation/execution/V2-003'
p=argparse.ArgumentParser();p.add_argument('--scan',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--final',action='store_true');a=p.parse_args()
assert not a.output.exists()
v=json.loads(a.scan.read_text());assert not v['errors'] and not v['scope_findings']
baseline=json.loads((R/v['baseline_pin']['ref']).read_text())
reasons={
 'AGENTS.md':('One existing local-tool description is updated to disclose explicit V2-003 pins and before/after checks. No rule, approval, acceptance or stopping condition removed.','Execution guidance now matches tested command options; V2-004 boundary retained.'),
 'plan/machine/ai-execution-policy.yaml':('Only AI-EXEC-02/03 local capability/status/limitations reflect implemented checks. Owner tasks, acceptance mappings and p0_required are identical to opening. AI-EXEC-03 stays NOT_IMPLEMENTED overall pending V2-004.','No minimum obligation is relaxed; AI-EXEC-02 status follows actual task evidence at final binding.'),
 'plan/machine/implementation-backlog.yaml':('V2-003 concrete checker artifacts added under the prepared task scope; identity, dependencies, all acceptance criteria and other tasks are unchanged. Status/evidence are separately validated metadata.','Names existing implemented deliverables; no future feature or new task dependency.'),
 'plan/scripts/task_entry.py':('Adds paired explicit pin flags, before/after actual diff review and pre-dispatch race detection. Existing packet/ADR/budget/resume and direct-call restrictions remain. Legacy no-pin behavior is explicitly disclosed.','Strengthens scoped invocation; preserves prior local entry behavior and cannot claim remote enforcement.'),
 'tests/contract/test_task_execution.py':('Only seed fixture restores the OPEN later-task premise when copying a progressed production plan. Every existing test function/assertion remains AST-identical to opening; original missing-packet negative and legal entry pass after correction.','Production progress no longer substitutes an action mismatch for the intended missing-packet rejection; no production status or acceptance changed.'),
 'tests/contract/test_plan_governance.py':('Original diagnostic TASK_EVIDENCE means mixed/zero revisions, but V2-002 now has same-revision local evidence. The closure negative still requires rejection and now specifically asserts missing ci AND acceptance TASK_SCHEMA errors. Validator and minimum closure requirement unchanged.','Fixes a demonstrated stale expectation, adds specific refusal assertions; prior 235-pass/1-fail run and 14-pass correction retained, no deleted or skipped test.')}
paths=['raw/010_precommit_governance.json','raw/003_architecture_regression.json','raw/precommit_weakening_final.json','raw/013_legacy_diagnostic_fix.json','raw/012_precommit_bootstrap.json','review/preservation.json']
if a.final:paths=['raw/014_postcommit_tests.json','raw/015_postcommit_governance.json','raw/016_postcommit_bootstrap.json','raw/017_postcommit_preservation.json','raw/018_postcommit_entry.json']
artifacts=[]
for name in paths:
 f=B/name;data=f.read_bytes();artifacts.append({'ref':str(f.relative_to(R)),'sha256':hashlib.sha256(data).hexdigest()})
 if name.startswith('raw/'):assert json.loads(data)['exit_code']==0,name
rows=[]
for f in v['findings']:
 assert f['severity_kind']=='REVIEW' and f['path'] in reasons,f
 reason,impact=reasons[f['path']]
 row={k:f[k] for k in ['path','layer','code','old_sha','new_sha']}
 row.update(finding_id=f['id'],disposition='REVIEWED_NO_WEAKENING',reason=reason,impact=impact,reviewer='Codex primary implementer and verifier with bounded peer review; same permissions, not independent authority',replacement_validation='Exact opening comparison plus actual positive/negative tests; raw failed attempts remain separately visible. Verification artifacts listed below; no authority to weaken granted.',authorization_source=baseline['authorization_source'],verification_artifacts=artifacts)
 rows.append(row)
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'task_id':'V2-003','baseline_pin':v['baseline_pin'],'dispositions':rows,'limitation':'Local same-operator technical review only; not remote trust or an exception authorization'},ensure_ascii=False,indent=2)+'\n');print({'dispositions':len(rows),'file':str(a.output)})
