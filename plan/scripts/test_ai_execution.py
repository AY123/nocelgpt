#!/usr/bin/env python3
"""Isolated packet/claim/action tests; no real CI, runner or paid calls."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import shutil
import tempfile
import unittest

import validate_plan as validator
from execution_checks import execution_checks, CONTROL_INPUTS
from test_governance import GovernanceTests, RecordedResult


class AIExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='anovel-ai-execution-test-')
        self.addCleanup(self.tmp.cleanup)
        self.plan = Path(self.tmp.name)/'plan'
        self.records = self.plan/'validation/fixture'
        self.records.mkdir(parents=True)
        self.data = deepcopy(validator.load())
        self.task = self.data['implementation-backlog']['tasks'][0]
        for ref in self.task['normative_specs'] + list(CONTROL_INPUTS) + ['schemas/execution-packet.schema.json', 'FILE_MANIFEST.json']:
            dest = self.plan/ref
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(validator.PLAN/ref, dest)
        self.task['status'] = 'IN_PROGRESS'
        self.packet = GovernanceTests.make_packet(self, self.task, 'PREPARE')
        self.assertEqual(self.errors(), [], 'Each single mutation starts from a valid preparation context')

    def save(self):
        (self.plan/self.task['execution_packet_ref']).write_text(json.dumps(self.packet)+'\n')

    def errors(self):
        return validator.validate_objects(self.data) + execution_checks(self.data, self.plan)

    def reject(self, prefix):
        errors = self.errors()
        self.assertTrue(any(e.startswith(prefix) for e in errors), (prefix, errors))

    def set_action(self, action):
        self.packet['action'] = self.packet['handoff']['next_action'] = action
        self.save()

    def accept_decision(self):
        # Structural declaration only. Full ADR evidence is covered by the
        # existing governance tests; this helper cannot attest a real decision.
        adr = self.data['decision-register']['decisions'][0]
        adr.update(status='ACCEPTED', decision_record='validation/fixture/synthetic-adr.json')

    def test_preparation_allows_required_decision(self):
        self.assertEqual(self.errors(), [])

    def test_active_task_requires_packet(self):
        self.task['execution_packet_ref'] = None
        self.reject('EXEC_PACKET')

    def test_open_task_can_only_prepare(self):
        self.task['status'] = 'OPEN'
        self.assertEqual(self.errors(), [])
        self.accept_decision(); self.set_action('IMPLEMENT'); self.reject('EXEC_ACTION')

    def test_packet_cannot_create_manifest_hash_cycle(self):
        path = self.plan/'task-packets/context.json'
        path.parent.mkdir()
        path.write_text(json.dumps(self.packet))
        self.task['execution_packet_ref'] = 'task-packets/context.json'
        self.reject('EXEC_PACKET')

    def test_policy_cannot_claim_unimplemented_p0_is_verified(self):
        self.data['ai-execution-policy']['controls'][0]['p0_enforcement_status'] = 'VERIFIED'
        self.reject('AI_EXEC_STATUS')

    def test_policy_rejects_unsupported_local_success_label(self):
        self.data['ai-execution-policy']['controls'][0]['local_status'] = 'PRODUCTION_READY'
        self.reject('AI_EXEC_STATUS')

    def test_missing_packet_file(self):
        self.task['execution_packet_ref'] = 'validation/missing.json'
        self.reject('EXEC_PACKET')

    def test_template_alias_cannot_be_packet(self):
        template = self.plan/'templates/packet.json'
        template.parent.mkdir()
        template.write_text(json.dumps(self.packet))
        alias = self.records/'alias.json'
        alias.symlink_to(template)
        self.task['execution_packet_ref'] = str(alias.relative_to(self.plan))
        self.reject('EXEC_PACKET')

    def test_wrong_task(self):
        self.packet['task_id'] = 'V2-002'; self.save(); self.reject('EXEC_SUBJECT')

    def test_stale_plan_version(self):
        self.packet['plan_version'] = 'stale'; self.save(); self.reject('EXEC_VERSION')

    def test_stale_manifest_on_resume(self):
        self.packet['plan_manifest_sha256'] = '0'*64; self.save(); self.reject('EXEC_VERSION')

    def test_missing_normative_input(self):
        self.packet['inputs'].pop(); self.save(); self.reject('EXEC_INPUT')

    def test_changed_live_input(self):
        source = self.plan/self.packet['inputs'][0]['source_ref']
        source.write_text(source.read_text()+'\nchanged\n')
        self.reject('EXEC_INPUT')

    def test_changed_snapshot(self):
        (self.plan/self.packet['inputs'][0]['ref']).write_text('wrong input')
        self.reject('EXEC_INPUT')

    def test_input_escape(self):
        self.packet['inputs'][0]['ref'] = '../outside.txt'
        self.save(); self.reject('EXEC_INPUT')

    def test_root_and_wildcard_scopes_rejected(self):
        original = deepcopy(self.packet)
        for path in ('.', '../', '/', '**', 'src/../', '.git/config'):
            with self.subTest(path=path):
                self.packet = deepcopy(original)
                self.packet['allowed_paths'].append(path)
                self.save(); self.reject('EXEC_SCOPE')

    def test_declared_output_outside_scope(self):
        self.packet['allowed_paths'].pop()
        self.save(); self.reject('EXEC_SCOPE')

    def test_task_output_not_silently_dropped(self):
        self.packet['expected_outputs'].pop()
        self.save(); self.reject('EXEC_OUTPUTS')

    def test_interface_requires_decision(self):
        self.set_action('IMPLEMENT'); self.reject('EXEC_ADR')

    def test_implementation_with_declared_decision(self):
        self.accept_decision(); self.set_action('IMPLEMENT')
        self.assertEqual(self.errors(), [])

    def test_required_decision_not_silently_removed(self):
        self.packet['required_decisions'] = []
        self.save(); self.reject('EXEC_ADR')

    def test_unknown_decision_timing_rejected(self):
        self.data['decision-register']['decisions'][0]['timing'] = 'whenever'
        self.reject('EXEC_ADR')

    def test_fact_needs_source(self):
        self.packet['claims'] = [{'id':'C1','kind':'FACT','statement':'unproven',
                                  'sources':[],'blocks_actions':[], 'verification_plan':'verify'}]
        self.save(); self.reject('EXEC_SCHEMA')

    def test_unknown_blocks_implementation_but_allows_preparation(self):
        self.packet['claims'] = [{'id':'C1','kind':'UNKNOWN','statement':'interface undecided',
                                  'sources':[],'blocks_actions':['IMPLEMENT'],'verification_plan':'inspect actual consumer'}]
        self.save(); self.assertEqual(self.errors(), [])
        self.accept_decision(); self.set_action('IMPLEMENT'); self.reject('EXEC_CLAIM')

    def test_sourced_fact_declaration(self):
        source = self.packet['inputs'][0]
        self.packet['claims'] = [{'id':'C1','kind':'FACT','statement':'synthetic source declaration only',
                                  'sources':[{'ref':source['ref'],'sha256':source['sha256']}],
                                  'blocks_actions':[],'verification_plan':'fixture, not truth certification'}]
        self.save(); self.assertEqual(self.errors(), [])

    def test_missing_handoff_rejected(self):
        del self.packet['handoff']; self.save(); self.reject('EXEC_SCHEMA')

    def test_next_action_mismatch(self):
        self.packet['handoff']['next_action'] = 'IMPLEMENT'
        self.save(); self.reject('EXEC_HANDOFF')

    def test_fabricated_pass_without_artifact_rejected(self):
        self.packet['handoff']['last_check']['status'] = 'PASS'
        self.save(); self.reject('EXEC_SCHEMA')

    def test_handoff_template_and_alias_are_not_run_results(self):
        path = self.plan/'templates/result.txt'
        path.parent.mkdir()
        path.write_text('template only')
        alias = self.records/'result-alias.txt'
        alias.symlink_to(path)
        for ref in ('templates/result.txt', str(alias.relative_to(self.plan))):
            with self.subTest(ref=ref):
                self.packet['handoff']['last_check'] = {
                    'status':'PASS', 'artifacts':[{'ref':ref,'sha256':validator.sha(path)}],
                    'missing_artifact_reason':None}
                self.save(); self.reject('EXEC_HANDOFF')

    def test_missing_failure_artifacts_can_be_reported_honestly(self):
        for status in ('FAIL', 'UNKNOWN'):
            with self.subTest(status=status):
                self.packet['handoff']['last_check'] = {
                    'status':status, 'artifacts':[],
                    'missing_artifact_reason':'executor lost before logs could be retrieved'}
                self.save(); self.assertEqual(self.errors(), [])
                self.packet['handoff']['last_check']['missing_artifact_reason'] = None
                self.save(); self.reject('EXEC_SCHEMA')

    def test_live_call_early_phase_and_missing_budget_rejected(self):
        self.accept_decision(); self.set_action('LIVE_CALL')
        self.reject('EXEC_ACTION'); self.reject('EXEC_BUDGET')

    def prepare_future_action_fixture(self, task_id, action):
        """Action-level fixture only; it does not assert earlier phases completed."""
        self.task = next(t for t in self.data['implementation-backlog']['tasks'] if t['task_id'] == task_id)
        for ref in self.task['normative_specs']:
            dest = self.plan/ref
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(validator.PLAN/ref, dest)
        self.task.update(status='IN_PROGRESS', readiness='READY_AFTER_GATES')
        self.packet = GovernanceTests.make_packet(self, self.task, action)
        for decision in self.data['decision-register']['decisions']:
            if decision['id'] in self.task['required_decisions']:
                decision.update(status='ACCEPTED', decision_record='validation/fixture/synthetic-adr.json')
        self.packet['budget'].update(paid_calls_allowed=True, model_cost_cap=1)
        self.save()
        self.assertEqual(execution_checks(self.data, self.plan), [])

    def test_live_action_positive_and_decision_negative(self):
        self.prepare_future_action_fixture('V2-019', 'LIVE_CALL')
        decision = next(a for a in self.data['decision-register']['decisions'] if a['id'] == 'ADR-010')
        decision.update(status='REQUIRED', decision_record=None)
        self.assertTrue(any(e.startswith('EXEC_ADR') for e in execution_checks(self.data, self.plan)))

    def test_certification_positive_and_decision_negative(self):
        self.prepare_future_action_fixture('V2-033', 'CERTIFY')
        decision = next(a for a in self.data['decision-register']['decisions'] if a['id'] == 'ADR-013')
        decision.update(status='REQUIRED', decision_record=None)
        self.assertTrue(any(e.startswith('EXEC_ADR') for e in execution_checks(self.data, self.plan)))

    def test_live_budget_is_required_even_in_eligible_phase(self):
        self.prepare_future_action_fixture('V2-019', 'LIVE_CALL')
        self.packet['budget']['model_cost_cap'] = None
        self.save()
        self.assertTrue(any(e.startswith('EXEC_BUDGET') for e in execution_checks(self.data, self.plan)))

    def test_completed_packet_keeps_recoverable_historical_inputs(self):
        self.accept_decision(); self.set_action('IMPLEMENT')
        self.task['status'] = 'CLOSED'
        self.packet['plan_version'] = 'historical-version'
        self.packet['plan_manifest_sha256'] = '1'*64
        source = self.plan/self.packet['inputs'][0]['source_ref']
        source.write_text('later revision')
        self.save()
        # Packet validation alone, not a claimed CLOSED task or full evidence chain.
        self.assertEqual(execution_checks(self.data, self.plan), [])

    def test_historical_packet_not_rewritten_for_new_task_outputs(self):
        self.accept_decision(); self.set_action('IMPLEMENT')
        self.task['status'] = 'CLOSED'
        self.task['artifacts'].append('newly-required-future-output.txt')
        self.task['required_decisions'].append('ADR-002')
        self.assertEqual(execution_checks(self.data, self.plan), [])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=validator.PLAN/'validation')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AIExecutionTests)
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    report = {'scope':'Local declared execution packet checks only; no actual action interception, diff review or remote CI',
              'generated_at_utc':datetime.now(timezone.utc).isoformat(),
              'manifest_sha256':validator.sha(validator.PLAN/'FILE_MANIFEST.json'),
              'status':'PASS' if result.wasSuccessful() else 'FAIL',
              'test_count':result.testsRun, 'cases':result.cases}
    (args.output_dir/'ai-execution-regression.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
