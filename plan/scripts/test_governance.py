#!/usr/bin/env python3
"""Positive closure fixtures and isolated governance regressions, not runtime tests."""
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml
import validate_plan as validator
from governance_checks import evidence_checks

REVISION = 'a' * 40


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='anovel-governance-test-')
        self.addCleanup(self.tmp.cleanup)
        self.plan = Path(self.tmp.name)/'plan'
        shutil.copytree(validator.PLAN, self.plan, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
        self.data = deepcopy(validator.load())
        self.records = self.plan/'validation/fixture'
        self.records.mkdir(parents=True, exist_ok=True)
        raw = self.records/'raw.txt'
        raw.write_text('SYNTHETIC ISOLATED TEST INPUT. NOT REAL ENGINEERING OR CI EVIDENCE.\n')
        self.artifact = {'ref':'validation/fixture/raw.txt','sha256':hashlib.sha256(raw.read_bytes()).hexdigest()}
        self.make_p0()
        self.assertEqual(self.errors(), [], 'Positive evidence fixture must be valid before mutation')

    def record(self, kind, subject, **extra):
        ref = f'validation/fixture/{kind}-{subject}.json'
        obj = {'record_type':'plan_execution_evidence','schema_version':'1.0','evidence_id':kind+'-'+subject,
               'evidence_type':kind,'subject_id':subject,'revision':REVISION,'status':'PASS',
               'producer':'isolated unit-test fixture','executed_at':'2026-09-21T00:00:00Z',
               'environment_fingerprint':'synthetic-test-only','artifacts':[deepcopy(self.artifact)],'input_evidence_refs':[]}
        if kind in {'TEST_RESULT','CI_RUN'}:
            obj.update(command='synthetic fixture; no real execution claimed',exit_code=0,check_ids=['fixture'])
        if kind == 'CI_RUN':
            obj.update(pipeline_id='fixture-pipeline',job_id='fixture-job',pipeline_url='https://ci.example.invalid/fixture')
        if kind in {'ACCEPTANCE_RECORD','ADR_DECISION','PHASE_DECISION','MILESTONE_DECISION','FINDING_CLOSURE'}:
            obj.update(decision={'PHASE_DECISION':'VERIFIED','MILESTONE_DECISION':'VERIFIED','FINDING_CLOSURE':'CLOSED'}.get(kind,'ACCEPTED'),rationale='Synthetic positive control; not a real task closure')
        obj.update(extra)
        (self.plan/ref).write_text(json.dumps(obj)+'\n')
        return ref

    def make_p0(self):
        for t in self.data['implementation-backlog']['tasks'][:4]:
            tid = t['task_id']
            suite = next(s for s in self.data['test-catalog']['suites'] if s['task_id'] == tid)
            ids = [s['id'] for s in suite['scenarios']]
            refs = {kind:self.record(typ,tid,**({'check_ids':ids} if kind=='tests' else {})) for kind,typ in [('code','CODE'),('tests','TEST_RESULT'),('ci','CI_RUN')]}
            dispositions = [{'finding_id':fid,'responsibility':'FULL','disposition':'RESOLVED',
                             'evidence_refs':[refs['tests']],'reason':'Only this task obligation is covered by the synthetic fixture'} for fid in t['related_findings']]
            external = [{'practice_id':x,'adoption_mode':'independent fixture','source_version_note':'fixture only','verification_refs':[refs['tests']],'conclusion':'no runtime claim','limitations':'isolated test'} for x in t.get('external_practices', [])]
            refs['acceptance'] = self.record('ACCEPTANCE_RECORD',tid,input_evidence_refs=list(refs.values()),check_ids=ids,finding_dispositions=dispositions,external_practice_results=external)
            t.update(status='CLOSED',evidence={kind:[{'ref':ref,'revision':REVISION,'status':'PASS'}] for kind,ref in refs.items()})
            suite.update(status='VERIFIED',execution_evidence=[refs['tests']])
            for a in self.data['decision-register']['decisions']:
                if a['id'] in t['required_decisions']:
                    a.update(status='ACCEPTED',decision_record=self.record('ADR_DECISION',a['id']))
        gates = [g for g in self.data['ci-gates']['gates'] if g['activation_phase']=='P0']
        ci = self.record('CI_RUN','P0',check_ids=[g['id'] for g in gates])
        for g in gates:
            g.update(status='VERIFIED',evidence_refs=[ci])
        accepts = [t['evidence']['acceptance'][0]['ref'] for t in self.data['implementation-backlog']['tasks'][:4]]
        phase = self.record('PHASE_DECISION','P0',input_evidence_refs=accepts+[ci],ci_evidence_refs=[ci])
        self.data['phase-gates']['phases'][0].update(status='VERIFIED',evidence_refs=[phase])
        self.data['milestones']['milestones'][0].update(status='VERIFIED',evidence_refs=[self.record('MILESTONE_DECISION','M0',input_evidence_refs=accepts+[phase])])

    def errors(self):
        return validator.validate_objects(self.data)+evidence_checks(self.data,self.plan)

    def reject(self, prefix):
        errors = self.errors()
        self.assertTrue(any(e.startswith(prefix) for e in errors), (prefix,errors))

    def mutate_record(self, kind, subject, mutate):
        path = self.records/f'{kind}-{subject}.json'
        record = json.loads(path.read_text()); mutate(record); path.write_text(json.dumps(record)+'\n')

    def test_valid_p0_completion_chain(self):
        self.assertEqual(self.errors(), [])

    def test_valid_partial_finding_disposition(self):
        self.mutate_record('ACCEPTANCE_RECORD','V2-002',lambda r:r['finding_dispositions'][0].update(responsibility='PARTIAL',disposition='PARTIALLY_RESOLVED',remaining_work='later scope',next_task='V2-005',owner_role='domain-maintainer',due_gate='G-P1'))
        self.assertEqual(self.errors(), [])

    def test_valid_future_task_start(self):
        self.data['implementation-backlog']['tasks'][4].update(status='IN_PROGRESS',readiness='READY_AFTER_GATES')
        self.assertEqual(self.errors(), [])

    def test_valid_multiple_suites_for_one_task(self):
        task = self.data['implementation-backlog']['tasks'][0]
        extra = deepcopy(self.data['test-catalog']['suites'][0])
        extra['id'] = 'AT-V2-001-EXTRA'
        extra['scenarios'] = [{'id':'AT-V2-001-EXTRA-01','required_assertion':'additional isolated assertion'}]
        self.data['test-catalog']['suites'].append(extra)
        task['tests'].append(extra['id'])
        task['acceptance_criteria'].append(extra['scenarios'][0]['required_assertion'])
        for kind in ('TEST_RESULT','ACCEPTANCE_RECORD'):
            self.mutate_record(kind,'V2-001',lambda r:r['check_ids'].append('AT-V2-001-EXTRA-01'))
        self.assertEqual(self.errors(), [])

    def test_all_ci_removed(self):
        self.data['ci-gates']['gates']=[]; self.reject('CI_BASELINE')

    def test_ci_postponed(self):
        self.data['ci-gates']['gates'][0]['activation_phase']='P14'; self.reject('CI_BASELINE')

    def test_ci_checks_removed(self):
        self.data['ci-gates']['gates'][0]['checks']=[]; self.reject('CI_BASELINE')

    def test_ci_duplicate(self):
        self.data['ci-gates']['gates'].append(deepcopy(self.data['ci-gates']['gates'][0])); self.reject('CI_BASELINE')

    def test_missing_suite_file(self):
        self.data['test-catalog']['suites'][0]['execution_evidence']=['validation/absent.json']; self.reject('EVIDENCE_RECORD')

    def test_missing_phase_file(self):
        self.data['phase-gates']['phases'][0]['evidence_refs']=['validation/absent.json']; self.reject('EVIDENCE_RECORD')

    def test_readme_not_test_record(self):
        self.data['test-catalog']['suites'][0]['execution_evidence']=['README.md']; self.reject('EVIDENCE_RECORD')

    def test_directory_not_record(self):
        self.data['test-catalog']['suites'][0]['execution_evidence']=['validation']; self.reject('EVIDENCE_RECORD')

    def test_adr_template_not_decision(self):
        self.data['decision-register']['decisions'][0]['decision_record']='templates/ADR.md'; self.reject('EVIDENCE_RECORD')

    def test_template_artifact_cannot_support_decision(self):
        template=self.plan/'templates/ADR.md'
        self.mutate_record('ADR_DECISION','ADR-001',lambda r:r.update(artifacts=[{'ref':'templates/ADR.md','sha256':hashlib.sha256(template.read_bytes()).hexdigest()}]))
        self.reject('EVIDENCE_ARTIFACT')

    def test_normalized_template_aliases_are_rejected(self):
        template = self.plan/'templates/ADR.md'
        link = self.records/'template-link.md'
        link.symlink_to(template)
        for ref in ('./templates/ADR.md','validation/../templates/ADR.md','validation/fixture/template-link.md'):
            with self.subTest(ref=ref):
                self.mutate_record('ADR_DECISION','ADR-001',lambda r:r.update(artifacts=[{'ref':ref,'sha256':hashlib.sha256(template.read_bytes()).hexdigest()}]))
                self.reject('EVIDENCE_ARTIFACT')

    def test_valid_artifact_in_nested_templates_named_directory(self):
        artifact = self.records/'templates/result.txt'
        artifact.parent.mkdir()
        artifact.write_text('Synthetic execution result; not a plan template')
        self.mutate_record('ADR_DECISION','ADR-001',lambda r:r.update(artifacts=[{'ref':str(artifact.relative_to(self.plan)),'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()}]))
        self.assertEqual(self.errors(), [])

    def test_milestone_shrink(self):
        self.data['milestones']['milestones'][6]['required_tasks']=['V2-001']; self.reject('MILESTONE_BASELINE')

    def test_milestone_requires_phase(self):
        self.data['phase-gates']['phases'][0]['status']='NOT_VERIFIED'; self.reject('MILESTONE_PHASE')

    def test_milestone_revision_matches_phase_decision(self):
        self.mutate_record('MILESTONE_DECISION','M0',lambda r:r.update(revision='b'*40))
        self.reject('EVIDENCE_REVISION')

    def test_valid_historical_task_revision_in_current_phase(self):
        task = self.data['implementation-backlog']['tasks'][0]
        for pointers in task['evidence'].values():
            for pointer in pointers:
                pointer['revision'] = 'b'*40
                path = self.plan/pointer['ref']
                record = json.loads(path.read_text())
                record['revision'] = 'b'*40
                path.write_text(json.dumps(record)+'\n')
        self.assertEqual(self.errors(), [])

    def test_adr_backlink_removed(self):
        self.data['implementation-backlog']['tasks'][0]['required_decisions']=[]; self.reject('ADR_BACKLINK')

    def test_finding_backlink_removed(self):
        self.data['implementation-backlog']['tasks'][1]['related_findings']=[]; self.reject('FINDING_BACKLINK')

    def test_planned_readiness_cannot_start(self):
        self.data['implementation-backlog']['tasks'][4]['status']='IN_PROGRESS'; self.reject('TASK_READINESS')

    def test_p0_blocked(self):
        self.data['phase-gates']['entry_gate']['status']='BLOCKED'; self.reject('ENTRY_GATE')

    def test_missing_finding_disposition(self):
        self.mutate_record('ACCEPTANCE_RECORD','V2-002',lambda r:r.update(finding_dispositions=[])); self.reject('FINDING_DISPOSITION')

    def test_partial_finding_requires_next_owner(self):
        self.mutate_record('ACCEPTANCE_RECORD','V2-002',lambda r:r['finding_dispositions'][0].update(disposition='TRANSFERRED'))
        self.reject('EVIDENCE_RECORD')

    def test_wrong_evidence_type(self):
        self.data['test-catalog']['suites'][0]['execution_evidence']=['validation/fixture/CODE-V2-001.json']; self.reject('EVIDENCE_TYPE')

    def test_wrong_subject(self):
        self.mutate_record('TEST_RESULT','V2-001',lambda r:r.update(subject_id='V2-002')); self.reject('EVIDENCE_SUBJECT')

    def test_wrong_revision(self):
        self.mutate_record('TEST_RESULT','V2-001',lambda r:r.update(revision='b'*40)); self.reject('EVIDENCE_REVISION')

    def test_bad_artifact_hash(self):
        self.mutate_record('TEST_RESULT','V2-001',lambda r:r['artifacts'][0].update(sha256='0'*64)); self.reject('EVIDENCE_ARTIFACT')

    def test_suite_coverage_not_just_nonempty(self):
        self.mutate_record('TEST_RESULT','V2-001',lambda r:r.update(check_ids=['not-a-real-scenario'])); self.reject('EVIDENCE_COVERAGE')

    def test_failed_run_rejected(self):
        self.mutate_record('CI_RUN','V2-001',lambda r:r.update(exit_code=1)); self.reject('EVIDENCE_RECORD')

    def test_runtime_failure_states_are_not_closure_witnesses(self):
        path = self.records/'CI_RUN-V2-001.json'
        original = json.loads(path.read_text())
        for status in ('FAIL','ERROR','UNKNOWN','BLOCKED'):
            with self.subTest(status=status):
                record = deepcopy(original)
                record['status'] = status
                path.write_text(json.dumps(record)+'\n')
                self.reject('EVIDENCE_RECORD')

    def test_cli_external_reports_do_not_change_plan(self):
        def inventory():
            return {str(p.relative_to(self.plan)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.plan.rglob('*') if p.is_file()}
        before = inventory()
        reports = Path(self.tmp.name)/'dist/validation/job-1'
        for mode, name in [('--check','plan-validation.json'),('--self-test','validator-self-test.json')]:
            result = subprocess.run([sys.executable,'-B',str(self.plan/'scripts/validate_plan.py'),mode,'--output-dir',str(reports)], capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(json.loads((reports/name).read_text())['status'],'PASS')
        self.assertEqual(before,inventory())

    def test_phase_requires_applicable_ci(self):
        self.mutate_record('CI_RUN','P0',lambda r:r.update(check_ids=['STATIC'])); self.reject('EVIDENCE_COVERAGE')

    def test_phase_input_binding(self):
        self.mutate_record('PHASE_DECISION','P0',lambda r:r.update(input_evidence_refs=['validation/fixture/CI_RUN-P0.json'])); self.reject('PHASE_INPUTS')

    def test_evidence_cycle(self):
        self.mutate_record('TEST_RESULT','V2-001',lambda r:r.update(input_evidence_refs=['validation/fixture/TEST_RESULT-V2-001.json'])); self.reject('EVIDENCE_CYCLE')

    def test_source_registry_does_not_claim_fresh_verification(self):
        self.data['foundational-reference-register']['references'][0]['verification_status']='VERIFIED'; self.reject('FOUNDATION_EVIDENCE')

    def test_valid_exported_cli_and_single_negative(self):
        for name in validator.NAMES:
            (self.plan/'machine'/f'{name}.yaml').write_text(yaml.safe_dump(self.data[name],allow_unicode=True,sort_keys=False))
        # Explicit generation is allowed for intended changes; it must not weaken semantic checks.
        result=subprocess.run([sys.executable,'-B',str(self.plan/'scripts/validate_plan.py'),'--write-views'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        result=subprocess.run([sys.executable,'-B',str(self.plan/'scripts/validate_plan.py'),'--check'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        gates=self.data['ci-gates']; gates['gates']=[]
        (self.plan/'machine/ci-gates.yaml').write_text(yaml.safe_dump(gates))
        result=subprocess.run([sys.executable,'-B',str(self.plan/'scripts/validate_plan.py'),'--check'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertTrue(any(e.startswith('CI_BASELINE') for e in json.loads(result.stdout)['errors']))


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.cases.append({'case':test.id(), 'status':'PASS'})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.cases.append({'case':test.id(), 'status':'FAIL'})

    def addError(self, test, err):
        super().addError(test, err)
        self.cases.append({'case':test.id(), 'status':'ERROR'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=validator.PLAN/'validation')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GovernanceTests)
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    report = {'scope':'Planning governance regressions in disposable copies; synthetic records are not runtime evidence',
              'generated_at_utc':datetime.now(timezone.utc).isoformat(),
              'manifest_sha256':validator.sha(validator.PLAN/'FILE_MANIFEST.json'),
              'status':'PASS' if result.wasSuccessful() else 'FAIL',
              'test_count':result.testsRun,'cases':result.cases}
    (args.output_dir/'governance-regression.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
