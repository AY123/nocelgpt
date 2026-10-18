"""V2-002 engineering integration; fixtures never stand in for real CI."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'plan/scripts'))
import validate_plan as validator

spec = importlib.util.spec_from_file_location('engineering_governance', ROOT / 'scripts/check_governance.py')
engineering = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engineering)


def test_current_normative_registry_and_owner_mapping():
    data = validator.load()
    registry, errors = validator.normative_registry(data, ROOT / 'plan')
    assert errors == []
    assert 'V2-002' in registry['AI_EXECUTION_PROTOCOL.md']
    assert set().union(*(set(owners) for owners in registry.values())) == {t['task_id'] for t in data['implementation-backlog']['tasks']}
    assert not any(name.startswith('archive/') for name in registry)


@pytest.mark.parametrize('alias', ['archive/history.md', './archive/history.md', 'current/../archive/history.md', 'alias.md'])
def test_resolved_history_cannot_be_normative(tmp_path, alias):
    plan = tmp_path / 'plan'
    (plan / 'archive').mkdir(parents=True)
    (plan / 'current').mkdir()
    (plan / 'archive/history.md').write_text('HISTORICAL ONLY')
    (plan / 'current/spec.md').write_text('Current requirement')
    (plan / 'alias.md').symlink_to(plan / 'archive/history.md')
    data = {'implementation-backlog': {'tasks': [{'task_id': 'V2-002', 'normative_specs': ['current/spec.md'], 'design_references': ['archive/history.md']}]}}
    assert validator.normative_registry(data, plan)[1] == []
    data['implementation-backlog']['tasks'][0]['normative_specs'] = [alias]
    assert any('resolved archive' in error for error in validator.normative_registry(data, plan)[1])


def test_missing_normative_reference_rejected(tmp_path):
    data = {'implementation-backlog': {'tasks': [{'task_id': 'V2-002', 'normative_specs': ['missing.md']}]}}
    assert any('missing/outside' in error for error in validator.normative_registry(data, tmp_path)[1])


def test_actual_repository_context_entries_and_configuration():
    result = engineering.context_inventory(ROOT)
    assert result['errors'] == []
    by = {row['path']: row for row in result['files']}
    assert by['AGENTS.md']['exists'] and by['README.md']['exists']
    if by['.claude/settings.local.json']['exists']:
        assert by['.claude/settings.local.json']['top_level_keys'] == ['permissions']
        assert by['.claude/settings.local.json']['automatic_context_configuration'] == {}


def test_context_permissions_are_distinct_from_automatic_load(tmp_path):
    (tmp_path / '.claude').mkdir()
    for name in ('README.md', 'AGENTS.md'):
        (tmp_path / name).write_text('Read plan/README.md; archive is historical.')
    settings = tmp_path / '.claude/settings.local.json'
    settings.write_text(json.dumps({'permissions': {'allow': ['Read(plan/archive/history.md)']}}))
    assert engineering.context_inventory(tmp_path)['errors'] == []
    settings.write_text(json.dumps({'contextFiles': ['plan/archive/history.md']}))
    assert any('CONTEXT_ARCHIVE' in error for error in engineering.context_inventory(tmp_path)['errors'])


def test_context_import_alias_resolves_to_history(tmp_path):
    (tmp_path / 'plan/archive').mkdir(parents=True)
    (tmp_path / 'plan/archive/history.md').write_text('old')
    (tmp_path / 'alias.md').symlink_to(tmp_path / 'plan/archive/history.md')
    for name in ('README.md', 'AGENTS.md'):
        (tmp_path / name).write_text('Read plan/README.md')
    (tmp_path / 'CLAUDE.md').write_text('@alias.md\n')
    assert any('CONTEXT_ARCHIVE' in error for error in engineering.context_inventory(tmp_path)['errors'])


@pytest.mark.parametrize('mutate,prefix', [
    (lambda d: d['implementation-backlog']['tasks'][1].update(phase='P1'), 'TASK_PHASE'),
    (lambda d: d['implementation-backlog']['tasks'][1].update(status='CLOSED', evidence={**d['implementation-backlog']['tasks'][1]['evidence'], 'ci': [], 'acceptance': []}), 'TASK_SCHEMA'),
    (lambda d: d['implementation-backlog']['tasks'][4].update(status='IN_PROGRESS'), 'TASK_START'),
    (lambda d: d['external-practice-register']['practices'][0].update(source_refs=['MISSING']), 'EXTERNAL_SOURCE'),
])
def test_existing_rules_reject_single_mutations(mutate, prefix):
    data = deepcopy(validator.load())
    if prefix == 'TASK_START':
        # Explicit missing predecessor gate; real project progress is irrelevant.
        # Reset downstream tasks in this isolated copy as well: an active V2-006
        # cannot be a valid control while its predecessor/P0 are reset below.
        for task in data['implementation-backlog']['tasks']:
            if task['phase'] != 'P0':
                task['status'] = 'OPEN'
        data['implementation-backlog']['tasks'][4].update(status='OPEN', readiness='PLANNED')
        for phase in data['phase-gates']['phases']:
            phase.update(status='NOT_VERIFIED', evidence_refs=[])
        for milestone in data['milestones']['milestones']:
            milestone.update(status='NOT_VERIFIED', evidence_refs=[])
    assert validator.validate_objects(data) == []
    mutate(data)
    errors = validator.validate_objects(data)
    assert any(error.startswith(prefix) for error in errors), errors
    if prefix == 'TASK_START':
        assert any(error.startswith('TASK_START V2-005: phase entry not verified')
                   for error in errors), errors
    if prefix == 'TASK_SCHEMA':
        # This isolated mutation removes CI and acceptance from a real valid
        # record. Each absent witness must still block closure after P0 ends.
        for kind in ('ci', 'acceptance'):
            assert any(error.startswith(f"TASK_SCHEMA V2-002 ['evidence', '{kind}']:")
                       for error in errors), errors


def test_generated_views_match_current_source():
    for name, content in validator.expected_views(validator.load()).items():
        assert (ROOT / 'plan' / name).read_text() == content


def test_validator_self_test_rejects_empty_evidence_after_p0_completion():
    # Exercise all negative mutations against valid live data, including CLOSED
    # tasks and VERIFIED P0. Self-test must mutate evidence, not merely set a
    # status which can already be true in the real project.
    data = deepcopy(validator.load())
    assert validator.validate_objects(data) == []
    results = validator.self_test(data)
    assert all(item['expected'] == item['actual'] for item in results), results
    assert {'empty CLOSED evidence', 'false verified phase', 'premature P1 start'}.issubset(
        {item['case'] for item in results})
