"""Positive and attack fixtures for fixed-baseline weakening comparison."""
import copy
import hashlib
import importlib.util
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('weakening_checks_under_test', ROOT / 'plan/scripts/weakening_checks.py')
CHECKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKS)


def change(path, old, new, **extra):
    def encode(value):
        return value.encode() if isinstance(value, str) else value
    return {'path': path, 'layer': 'worktree', 'status': 'M',
            'old_bytes': encode(old), 'new_bytes': encode(new), **extra}


def scan(path, old, new, *, protected=(), **extra):
    return CHECKS.scan_weakening([change(path, old, new, **extra)], task_id='V2-003',
                                baseline={'protected_paths': list(protected)})


def codes(findings):
    return {item['code'] for item in findings}


def document(value):
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False)


def machine(name, old, new):
    return scan('plan/machine/' + name + '.yaml', document(old), document(new),
                protected=('plan/machine/',))


@pytest.mark.parametrize('after', [
    '# formatted\n\ndef test_valid():\n    assert (1 == 1)\n',
    'def test_valid():\n    """Explain the same check."""\n    assert 1 == 1\n',
    'def test_valid():\n    assert 1 == 1\n    assert 2 == 2\n',
    'def test_valid():\n    assert 1 == 1\n\ndef test_more():\n    assert 3 == 3\n',
])
def test_formatting_and_monotonic_test_additions_pass(after):
    assert scan('tests/architecture/test_example.py', 'def test_valid():\n    assert 1 == 1\n', after) == []


def test_new_test_and_new_checker_do_not_require_an_exception():
    assert scan('tests/architecture/test_new.py', None, 'def test_new():\n    assert 1 == 1\n') == []
    assert scan('plan/scripts/new_checker.py', None, 'def check():\n    return True\n',
                protected=('plan/scripts/',)) == []


def test_test_file_and_function_deletion_are_explicit_weakening():
    old = 'def test_one():\n    assert 1\n\ndef test_two():\n    assert 2\n'
    deleted = scan('tests/test_example.py', old, None)
    assert 'TEST_FILE_REMOVED' in codes(deleted)
    changed = scan('tests/test_example.py', old, 'def test_one():\n    assert 1\n')
    finding = next(item for item in changed if item['code'] == 'TEST_FUNCTION_REMOVED')
    assert finding['pointer'] == '/test_two'
    assert finding['severity_kind'] == 'WEAKENING'


def test_plain_assertion_deletion_is_weakening_but_replacement_requires_review():
    old = 'def test_valid():\n    assert 1\n    assert 2\n'
    removed = scan('tests/test_example.py', old, 'def test_valid():\n    assert 1\n')
    assert any(f['code'] == 'TEST_ASSERTION_REMOVED' and f['severity_kind'] == 'WEAKENING' for f in removed)
    changed = scan('tests/test_example.py', old, 'def test_valid():\n    assert 1\n    assert 3\n')
    assert any(f['code'] == 'TEST_ASSERTION_CHANGED' and f['severity_kind'] == 'REVIEW' for f in changed)


@pytest.mark.parametrize('after', [
    'def test_valid():\n    if False:\n        assert 1 == 1\n',
    'def test_valid():\n    return\n    assert 1 == 1\n',
    'def test_valid():\n    assert 1 == 1\n\ndef test_valid():\n    pass\n',
])
def test_preserving_assert_text_does_not_hide_control_flow_or_redefinition(after):
    result = scan('tests/test_example.py', 'def test_valid():\n    assert 1 == 1\n', after)
    assert codes(result) & {'TEST_LOGIC_CHANGED', 'TEST_DEFINITION_REPLACED'}


def test_fixture_and_helper_changes_require_review():
    old = 'def helper():\n    return 1\n\ndef test_valid():\n    assert helper() == 1\n'
    new = old.replace('return 1', 'return 2')
    assert 'TEST_LOGIC_CHANGED' in codes(scan('tests/conftest.py', old, new))


@pytest.mark.parametrize('source', [
    'import pytest as p\n@p.mark.skip\ndef test_x():\n    assert 1\n',
    'from pytest import skip as abandon\ndef test_x():\n    abandon("reason")\n',
    'from pytest.mark import skipif as conditional\n@conditional(True, reason="x")\ndef test_x():\n    assert 1\n',
    'import pytest as p\n@p.mark.xfail\ndef test_x():\n    assert 1\n',
    'from pytest import xfail as expected\ndef test_x():\n    expected("x")\n',
    'import unittest as u\n@u.skip("x")\ndef test_x():\n    assert 1\n',
    'from unittest import expectedFailure as expected\n@expected\ndef test_x():\n    assert 1\n',
    'def test_x(self):\n    self.skipTest("x")\n',
])
def test_skip_and_xfail_aliases_in_new_files_are_weakening(source):
    result = scan('tests/test_new.py', None, source)
    assert any(f['code'] == 'TEST_SKIP_CHANGED' and f['severity_kind'] == 'WEAKENING' for f in result)


def test_changing_skipif_condition_is_not_hidden_by_equal_skip_count():
    old = 'import pytest\n@pytest.mark.skipif(False, reason="x")\ndef test_x():\n    assert 1\n'
    assert 'TEST_SKIP_CHANGED' in codes(scan('tests/test_x.py', old, old.replace('False', 'True')))
    assert scan('tests/test_x.py', old, '# same condition\n' + old) == []


def test_unittest_assertions_support_additions_and_detect_removal():
    old = 'class TestExample:\n    def test_x(self):\n        self.assertEqual(1, 1)\n'
    stronger = old + '        self.assertTrue(True)\n'
    assert scan('tests/test_x.py', old, stronger) == []
    assert 'TEST_ASSERTION_REMOVED' in codes(scan('tests/test_x.py', stronger, old))


def task():
    return {'task_id': 'V2-003', 'phase': 'P0', 'start_gate': 'P0_ENTRY_READY',
            'acceptance_criteria': ['legal graph', 'negative graph'], 'tests': ['AT-V2-003'],
            'dependencies': [], 'required_decisions': [], 'out_of_scope': [], 'status': 'OPEN'}


def suite():
    return {'id': 'AT-V2-003', 'task_id': 'V2-003', 'target_path': 'tests/architecture/test_x.py',
            'scenarios': [{'id': 'AT-V2-003-01', 'required_assertion': 'legal graph'},
                          {'id': 'AT-V2-003-02', 'required_assertion': 'negative graph'}], 'status': 'PLANNED'}


def test_synchronized_ac_scenario_and_test_deletion_remain_visible():
    before_task, after_task = task(), task()
    after_task['acceptance_criteria'].pop()
    before_suite, after_suite = suite(), suite()
    after_suite['scenarios'].pop()
    changes = [
        change('plan/machine/implementation-backlog.yaml', document({'tasks': [before_task]}), document({'tasks': [after_task]})),
        change('plan/machine/test-catalog.yaml', document({'suites': [before_suite]}), document({'suites': [after_suite]})),
        change('tests/test_negative.py', 'def test_negative():\n    assert False\n', None),
    ]
    result = CHECKS.scan_weakening(changes, task_id='V2-003', baseline={'protected_paths': ['plan/machine/']})
    assert {'AC_REMOVED', 'SCENARIO_REMOVED', 'TEST_FILE_REMOVED'} <= codes(result)
    assert all(item['severity_kind'] == 'WEAKENING' for item in result)


def test_machine_additions_and_evidence_status_updates_pass():
    before_task, after_task = task(), task()
    after_task.update(status='IMPLEMENTED', evidence={'tests': ['some-evidence']})
    after_task['acceptance_criteria'].append('new requirement')
    assert machine('implementation-backlog', {'tasks': [before_task]}, {'tasks': [after_task]}) == []
    before_suite, after_suite = suite(), suite()
    after_suite.update(status='IMPLEMENTED', execution_evidence=['result.yaml'])
    after_suite['scenarios'].append({'id': 'AT-V2-003-03', 'required_assertion': 'new requirement'})
    assert machine('test-catalog', {'suites': [before_suite]}, {'suites': [after_suite]}) == []


def test_same_scenario_count_with_changed_assertion_requires_review():
    before, after = suite(), suite()
    after['scenarios'][1]['required_assertion'] = 'negative graph optional'
    result = machine('test-catalog', {'suites': [before]}, {'suites': [after]})
    assert any(item['code'] == 'SCENARIO_ASSERTION_CHANGED' and item['severity_kind'] == 'REVIEW' for item in result)


def gate():
    return {'id': 'ARCH', 'checks': ['positive', 'negative'], 'activation_phase': 'P0',
            'mode': 'every_change', 'allow_failure': False, 'status': 'NOT_IMPLEMENTED'}


@pytest.mark.parametrize('mutate,expected', [
    (lambda value: value['gates'].clear(), 'GATE_REMOVED'),
    (lambda value: value['gates'][0]['checks'].pop(), 'GATE_CHECK_REMOVED'),
    (lambda value: value['gates'][0].update(allow_failure=True), 'HARD_FAILURE_DISABLED'),
    (lambda value: value['gates'][0].update(activation_phase='P1'), 'GATE_ACTIVATION_RELAXED'),
    (lambda value: value['gates'][0].update(mode='manual'), 'GATE_TRIGGER_CHANGED'),
])
def test_gate_weakening(mutate, expected):
    before = {'gates': [gate()]}
    after = copy.deepcopy(before)
    mutate(after)
    assert expected in codes(machine('ci-gates', before, after))


def test_gate_extra_check_and_earlier_activation_are_legal():
    before = {'gates': [gate()]}
    before['gates'][0]['activation_phase'] = 'P1'
    after = copy.deepcopy(before)
    after['gates'][0].update(activation_phase='P0', status='IMPLEMENTED')
    after['gates'][0]['checks'].append('another negative')
    assert machine('ci-gates', before, after) == []


def baseline_policy():
    return {'required_ci': {'ARCH': {'required_checks': ['negative'], 'latest_activation_phase': 'P0', 'mode': 'every_change'}},
            'phase_criteria': {'P0': ['all four tasks']}, 'required_findings': ['RR-09'],
            'milestones': {'M0': {'required_tasks': ['V2-003'], 'earliest_close_phase': 'P0'}}}


@pytest.mark.parametrize('mutate,expected', [
    (lambda value: value['required_ci'].clear(), 'BASELINE_GATE_REMOVED'),
    (lambda value: value['phase_criteria']['P0'].clear(), 'BASELINE_REQUIREMENT_REMOVED'),
    (lambda value: value['required_findings'].clear(), 'BASELINE_REQUIREMENT_REMOVED'),
    (lambda value: value['milestones']['M0']['required_tasks'].clear(), 'MILESTONE_REQUIREMENT_REMOVED'),
])
def test_lowering_minimum_baseline_is_not_a_new_comparison_baseline(mutate, expected):
    old = baseline_policy()
    new = copy.deepcopy(old)
    mutate(new)
    assert expected in codes(machine('governance-baseline', old, new))


def test_baseline_enhancement_passes_and_unmodelled_policy_change_is_reviewed():
    old = baseline_policy()
    stronger = copy.deepcopy(old)
    stronger['required_ci']['ARCH']['required_checks'].append('more coverage')
    assert machine('governance-baseline', old, stronger) == []
    changed = copy.deepcopy(old)
    changed['change_policy'] = 'let current agent approve everything'
    assert 'MACHINE_POLICY_CHANGED' in codes(machine('governance-baseline', old, changed))


@pytest.mark.parametrize('path,old,new,expected', [
    ('pyproject.toml', '[tool.coverage.report]\nfail_under = 90\n', '[tool.coverage.report]\nfail_under = 70\n', 'THRESHOLD_RELAXED'),
    ('policy.yaml', 'quality:\n  max_error_rate: 0.1\n', 'quality:\n  max_error_rate: 0.8\n', 'THRESHOLD_RELAXED'),
    ('policy.yaml', 'scan:\n  exclude: [generated/]\n', 'scan:\n  exclude: [generated/, src/anovel/domain/]\n', 'SCAN_EXCLUSION_EXPANDED'),
    ('pyproject.toml', '[tool.pytest.ini_options]\ntestpaths = ["tests", "extra"]\n', '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', 'SCAN_TARGETS_CHANGED'),
    ('policy.yaml', 'gates:\n- id: check\n  allow_failure: false\n', 'gates:\n- id: check\n  allow_failure: true\n', 'HARD_FAILURE_DISABLED'),
    ('pyproject.toml', '[tool.pytest.ini_options]\naddopts="-ra"\n', '[tool.pytest.ini_options]\naddopts="-ra --deselect=tests/test_real.py"\n', 'TEST_SELECTION_CHANGED'),
])
def test_configuration_weakening_uses_structured_values(path, old, new, expected):
    assert expected in codes(scan(path, old, new))


@pytest.mark.parametrize('old,new', [
    ('coverage: {minimum: 70}\n', 'coverage:\n  minimum: 90\n'),
    ('scan: {exclude: [a, b]}\n', 'scan: {exclude: [a]}\n'),
    ('scan: {testpaths: [tests]}\n', 'scan: {testpaths: [tests, more]}\n'),
    ('minimum: 90\n', '# same\nminimum: 90\n'),
    ('unrelated_price: 90\n', 'unrelated_price: 70\n'),
])
def test_configuration_enhancement_formatting_and_unrelated_numbers_pass(old, new):
    assert scan('policy.yaml', old, new) == []


def test_checker_changes_are_review_and_formatting_is_legal():
    old = 'def check():\n    return True\n'
    assert scan('plan/scripts/checker.py', old, '# same\n' + old, protected=('plan/scripts/',)) == []
    result = scan('plan/scripts/checker.py', old, 'def check():\n    return False\n', protected=('plan/scripts/',))
    assert any(f['code'] == 'PROTECTION_CHANGED' and f['severity_kind'] == 'REVIEW' for f in result)


def test_protected_rename_is_review_while_normal_test_rename_passes():
    content = 'def test_x():\n    assert 1\n'
    assert scan('tests/test_moved.py', content, content, old_path='tests/test_old.py', status='R') == []
    moved = scan('scripts/elsewhere.py', content, content, old_path='plan/scripts/checker.py', status='R',
                 protected=('plan/scripts/checker.py',))
    assert codes(moved) == {'PROTECTION_MOVED'}
    assert moved[0]['severity_kind'] == 'REVIEW'


@pytest.mark.parametrize('path,old,new', [
    ('.gitignore', 'dist/\n', 'dist/\ntests/\n'),
    ('tests/.gitignore', None, 'test_new.py\n'),
    ('src/anovel/.gitignore', None, '*.py\n'),
    ('tests/.gitignore', 'test_old.py\n', 'test_new.py\n'),
    ('tests/.gitignore', 'test_old.py\n', None),
])
def test_ignore_changes_at_any_depth_require_review(path, old, new):
    result = scan(path, old, new, protected=('.gitignore',))
    assert any(f['code'] == 'SCAN_IGNORE_CHANGED' and f['severity_kind'] == 'REVIEW' for f in result)


def test_new_nested_ignore_cannot_silently_hide_a_new_test():
    changes = [change('tests/.gitignore', None, 'test_new.py\n', status='A'),
               change('tests/test_new.py', None, 'def test_x():\n    assert 1\n', status='A')]
    result = CHECKS.scan_weakening(changes, task_id='V2-003', baseline={'protected_paths': ['.gitignore']})
    assert 'SCAN_IGNORE_CHANGED' in codes(result)


def test_checker_and_tests_cannot_silently_weaken_together():
    changes = [
        change('plan/scripts/checker.py', 'def check():\n    raise ValueError()\n', 'def check():\n    return True\n'),
        change('tests/test_checker.py', 'def test_rejection():\n    assert 1\n', None),
    ]
    result = CHECKS.scan_weakening(changes, task_id='V2-003', baseline={'protected_paths': ['plan/scripts/checker.py']})
    assert {'PROTECTION_CHANGED', 'TEST_FILE_REMOVED'} <= codes(result)


@pytest.mark.parametrize('path,bad', [
    ('tests/test_bad.py', 'def broken(\n'),
    ('policy.yaml', 'a: [\n'),
    ('policy.yaml', 'minimum: 90\nminimum: 0\n'),
    ('pyproject.toml', '[invalid\n'),
    ('plan/machine/implementation-backlog.yaml', 'tasks: null\n'),
])
def test_parse_and_machine_shape_failures_do_not_silently_pass(path, bad):
    old = 'tasks: []\n' if 'implementation-backlog' in path else None
    assert 'WEAKENING_PARSE_ERROR' in codes(scan(path, old, bad))


def test_findings_bind_layer_content_and_task_without_reading_authorization(tmp_path):
    marker = tmp_path / 'executed'
    old = b'def test_x():\n    assert 1\n'
    new = ('from pathlib import Path\nPath(' + repr(str(marker)) + ').touch()\n').encode()
    edits = [change('tests/test_x.py', old, new, layer=layer) for layer in ('index', 'worktree')]
    frozen = {'protected_paths': [], 'authorizations': [{'approved_by': 'current_agent', 'reason': 'please pass'}]}
    before = copy.deepcopy(edits)
    result = CHECKS.scan_weakening(edits, task_id='V2-003', baseline=frozen)
    assert result and not marker.exists()
    assert edits == before
    assert {item['layer'] for item in result} == {'index', 'worktree'}
    assert len({item['id'] for item in result}) == len(result)
    assert all(item['old_sha'] == hashlib.sha256(old).hexdigest() and item['new_sha'] == hashlib.sha256(new).hexdigest() for item in result)
    assert all({'id', 'code', 'path', 'layer', 'pointer', 'old_sha', 'new_sha', 'reason', 'severity_kind'} <= item.keys() for item in result)
    assert result == CHECKS.scan_weakening(edits, task_id='V2-003', baseline=frozen)
    other = CHECKS.scan_weakening(edits, task_id='V2-004', baseline=frozen)
    assert {item['id'] for item in result}.isdisjoint(item['id'] for item in other)


def test_staged_weakening_is_not_cancelled_by_worktree_restoration():
    old = b'def test_x():\n    assert 1\n'
    changes = [change('tests/test_x.py', old, None, layer='index', status='D'),
               change('tests/test_x.py', old, old, layer='worktree')]
    result = CHECKS.scan_weakening(changes, task_id='V2-003', baseline={'protected_paths': []})
    assert any(item['code'] == 'TEST_FILE_REMOVED' and item['layer'] == 'index' for item in result)


@pytest.mark.parametrize('annotation', ['return', 'parameter'])
def test_added_test_annotations_cannot_silently_replace_existing_checks(annotation):
    before='def test_required():\n    assert False\n'
    effect='globals().__setitem__("test_required", lambda: None)'
    added=('def test_extra() -> '+effect+':\n    pass\n' if annotation=='return'
           else 'def test_extra(value: '+effect+'):\n    pass\n')
    result=scan('tests/test_existing.py',before,before+added)
    assert 'TEST_LOGIC_CHANGED' in codes(result)
    if annotation=='return':
        namespace={};exec(before+added,namespace)
        namespace['test_required']()


def test_literal_reflective_skip_in_new_file_is_detected():
    source='import pytest as pt\nskipper=getattr(pt,"skip")\ndef test_new_required():\n    skipper("not implemented")\n'
    assert 'TEST_SKIP_CHANGED' in codes(scan('tests/test_new.py',None,source))


def test_unknown_reflective_test_control_requires_review():
    source='import pytest as pt\ncontrol=getattr(pt,choose_control())\ndef test_new_required():\n    control()\n'
    result=scan('tests/test_new.py',None,source)
    assert 'TEST_DYNAMIC_CONTROL' in codes(result)
    assert next(f for f in result if f['code']=='TEST_DYNAMIC_CONTROL')['severity_kind']=='REVIEW'


@pytest.mark.parametrize('source', [
    'def pytest_collection_modifyitems(config, items):\n    items[:] = [x for x in items if "negative" not in x.name]\n',
    'def pytest_ignore_collect(collection_path, config):\n    return True\n',
    'collect_ignore=["test_negative.py"]\n',
    'collect_ignore_glob=["test_*.py"]\n',
    'pytest_plugins=["collection_filter"]\n',
    'def pytest_sessionstart(session):\n    session.config.option.keyword="positive"\n',
])
def test_new_conftest_collection_controls_are_reviewed(source):
    findings=scan('tests/conftest.py',None,source)
    assert {'TEST_CONFTEST_CHANGED','TEST_COLLECTION_CONTROL'} <= codes(findings)


def test_new_harmless_conftest_is_reviewable_not_assumed_weakening():
    source='import pytest\n@pytest.fixture\ndef answer():\n    return 42\n'
    findings=scan('tests/conftest.py',None,source)
    assert codes(findings)=={'TEST_CONFTEST_CHANGED'}
    assert all(f['severity_kind']=='REVIEW' for f in findings)
    assert scan('tests/conftest.py',source,source)==[]


@pytest.mark.parametrize('path,section',[('pytest.ini','pytest'),('.pytest.ini','pytest'),('setup.cfg','tool:pytest'),('tox.ini','pytest')])
def test_ini_test_selection_and_targets_cannot_change_silently(path,section):
    old='['+section+']\ntestpaths = tests\naddopts = --strict-config\n'
    new='['+section+']\ntestpaths = tests/unit\naddopts = -k positive\n'
    assert {'TEST_CONFIG_CHANGED','TEST_SELECTION_CHANGED','SCAN_TARGETS_CHANGED'} <= codes(scan(path,old,new))
    assert 'TEST_CONFIG_CHANGED' in codes(scan(path,None,new))
    assert scan(path,old,old)==[]


def test_malformed_pytest_ini_is_not_a_passing_scan():
    assert 'WEAKENING_PARSE_ERROR' in codes(scan('pytest.ini',None,'[pytest\nbroken'))
