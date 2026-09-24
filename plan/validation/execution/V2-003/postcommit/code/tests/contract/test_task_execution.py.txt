"""Real subprocess gate/resume tests in disposable Git repositories.

Each mutation starts after a valid baseline. Sentinels prove child interception.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def call(repo, *argv):
    return subprocess.run(argv, cwd=repo, capture_output=True, text=True)


def load(path):
    return yaml.safe_load(path.read_text())


def save(path, value):
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=100000))


def reconcile(repo):
    # Fixture byte binding only; not production authorization/completion.
    plan = repo / 'plan'
    spec = importlib.util.spec_from_file_location('fixture_plan_validator', plan / 'scripts/validate_plan.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = module.load()
    for ref, value in module.expected_views(data).items():
        (plan / ref).write_text(value)
    (plan / 'FILE_MANIFEST.json').write_text(json.dumps(module.build_manifest(), ensure_ascii=False, indent=2)+'\n')
    for task in data['implementation-backlog']['tasks']:
        if not task.get('execution_packet_ref') or task['status'] not in {'OPEN', 'IN_PROGRESS', 'IMPLEMENTED'}:
            continue
        path = plan / task['execution_packet_ref']
        packet = load(path)
        packet['repository_revision'] = call(repo, 'git', 'rev-parse', 'HEAD').stdout.strip()
        packet['plan_manifest_sha256'] = module.sha(plan / 'FILE_MANIFEST.json')
        for index, item in enumerate(packet['inputs']):
            dest = plan / f'validation/fixture-current/{task["task_id"]}/{index}.txt'
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((plan / item['source_ref']).read_bytes())
            item.update(ref=str(dest.relative_to(plan)), sha256=module.sha(dest))
        save(path, packet)


@pytest.fixture(scope='module')
def seed(tmp_path_factory):
    repo = tmp_path_factory.mktemp('task-entry-seed')
    for directory in ('plan', 'scripts'):
        shutil.copytree(ROOT / directory, repo / directory, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
    # These legacy scenarios deliberately exercise V2-001/002 and an OPEN third
    # task. Production progress must not replace that fixture premise or mask the
    # intended missing-packet rejection with a different action mismatch.
    backlog_path = repo / 'plan/machine/implementation-backlog.yaml'
    backlog = load(backlog_path)
    for task in backlog['tasks'][2:]:
        task.update(status='OPEN', execution_packet_ref=None)
        task['evidence'] = {kind: [] for kind in task['evidence']}
    save(backlog_path, backlog)
    catalog_path = repo / 'plan/machine/test-catalog.yaml'
    catalog = load(catalog_path)
    for suite in catalog['suites'][2:]:
        suite.update(status='PLANNED', execution_evidence=[])
    save(catalog_path, catalog)
    policy_path = repo / 'plan/machine/ai-execution-policy.yaml'
    policy = load(policy_path)
    for control in policy['controls']:
        if set(control['owner_tasks']) - {'V2-001', 'V2-002'}:
            control['p0_enforcement_status'] = 'NOT_IMPLEMENTED'
    save(policy_path, policy)
    (repo / '.gitignore').write_text('dist/\n__pycache__/\n')
    for command in (('git', 'init', '-b', 'main'), ('git', 'add', '.'),
                    ('git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'synthetic gate fixture')):
        result = call(repo, *command)
        assert result.returncode == 0, result.stderr
    reconcile(repo)
    return repo


def entry(repo, mode='check', *, action='IMPLEMENT', task='V2-002', command=None, checkpoint=None, output=None):
    directory = repo / 'dist/entry'
    number = len(list(directory.glob('*.json'))) if directory.exists() else 0
    output = output or directory / f'{number}.json'
    argv = [sys.executable, '-B', str(repo / 'scripts/task_execution.py'), mode,
            '--task', task, '--action', action, '--output', str(output)]
    if checkpoint:
        argv += ['--checkpoint', str(checkpoint)]
    if command:
        argv += ['--', *command]
    result = call(repo, *argv)
    # Rejected output paths may point to preexisting YAML or a prior JSON report;
    # stdout carries this attempt's failure without altering either file.
    report = json.loads(output.read_text()) if result.returncode == 0 and output.exists() else json.loads(result.stdout)
    if output.exists() and result.returncode != 0:
        try:
            candidate = json.loads(output.read_text())
            if candidate.get('status') == report.get('status') and candidate.get('errors') == report.get('errors'):
                report = candidate
        except (ValueError, AttributeError):
            pass
    return result, report, output


@pytest.fixture
def repo(seed, tmp_path):
    destination = tmp_path / 'repo'
    shutil.copytree(seed, destination)
    result, report, _ = entry(destination)
    assert result.returncode == 0 and report['status'] == 'PASS', report.get('errors')
    return destination


def packet_path(repo, task='V2-002'):
    return repo / f'plan/validation/execution/{task}/execution-packet.yaml'


def mutate_packet(repo, mutate):
    path = packet_path(repo)
    packet = load(path)
    mutate(packet)
    save(path, packet)


SENTINEL = [sys.executable, '-c', "from pathlib import Path; Path('sentinel').write_text('executed')"]


def rejected(repo, prefix, **kwargs):
    result, report, _ = entry(repo, 'run', command=SENTINEL, **kwargs)
    assert result.returncode != 0
    assert report['status'] == 'BLOCKED'
    assert any(prefix in error for error in report['errors']), report['errors']
    assert not (repo / 'sentinel').exists()


def test_valid_command_runs_and_resume_rechecks_actual_state(repo):
    result, report, checkpoint = entry(repo, 'run', command=SENTINEL)
    assert result.returncode == 0 and report['status'] == 'PASS'
    assert (repo / 'sentinel').read_text() == 'executed'
    resumed, record, _ = entry(repo, 'resume', checkpoint=checkpoint)
    assert resumed.returncode == 0 and record['status'] == 'PASS'


@pytest.mark.parametrize('mutation,prefix', [
    (lambda p: p.update(task_id='V2-003'), 'EXEC_SUBJECT'),
    (lambda p: p.update(plan_version='stale'), 'EXEC_VERSION'),
    (lambda p: p['inputs'][0].update(sha256='0'*64), 'EXEC_INPUT'),
    (lambda p: p.update(record_type='execution_packet_template'), 'EXEC_SCHEMA'),
    (lambda p: p.pop('handoff'), 'EXEC_SCHEMA'),
    (lambda p: p.update(repository_revision='f'*40), 'ENTRY_BASE'),
    (lambda p: p['claims'].append({'id':'MISSING', 'kind':'UNKNOWN', 'statement':'unresolved', 'sources':[], 'blocks_actions':['IMPLEMENT'], 'verification_plan':'investigate'}), 'EXEC_CLAIM'),
    (lambda p: p['claims'].append({'id':'NO_SOURCE', 'kind':'FACT', 'statement':'unsupported', 'sources':[], 'blocks_actions':[], 'verification_plan':'investigate'}), 'EXEC_SCHEMA'),
])
def test_invalid_packet_blocks_child(repo, mutation, prefix):
    mutate_packet(repo, mutation)
    rejected(repo, prefix)


def test_missing_packet_blocks_child(repo):
    packet_path(repo).unlink()
    rejected(repo, 'EXEC_PACKET')


def test_wrong_requested_action_blocks_child(repo):
    rejected(repo, 'ENTRY_ACTION', action='PREPARE')


def test_accepted_adr_allows_actual_implementation_command(repo):
    result, report, _ = entry(repo, 'run', task='V2-001', command=[sys.executable, '-c', "print('accepted ADR')"])
    assert result.returncode == 0 and report['status'] == 'PASS'
    assert 'accepted ADR' in report['command_result']['stdout']


def test_open_prepare_allows_unresolved_adr_and_implement_blocks(repo):
    bpath = repo / 'plan/machine/implementation-backlog.yaml'
    backlog = load(bpath)
    task = backlog['tasks'][0]
    task.update(status='OPEN')
    save(bpath, backlog)
    dpath = repo / 'plan/machine/decision-register.yaml'
    decisions = load(dpath)
    decisions['decisions'][0].update(status='REQUIRED', decision_record=None)
    save(dpath, decisions)
    ppath = packet_path(repo, 'V2-001')
    packet = load(ppath)
    packet['action'] = packet['handoff']['next_action'] = 'PREPARE'
    save(ppath, packet)
    reconcile(repo)
    result, report, _ = entry(repo, 'run', task='V2-001', action='PREPARE', command=[sys.executable, '-c', "print('isolated research only')"])
    assert result.returncode == 0, report['errors']
    task['status'] = 'IN_PROGRESS'
    save(bpath, backlog)
    packet = load(ppath)
    packet['action'] = packet['handoff']['next_action'] = 'IMPLEMENT'
    save(ppath, packet)
    reconcile(repo)
    rejected(repo, 'EXEC_ADR', task='V2-001')


def test_open_task_requires_specific_packet_even_for_prepare(repo):
    rejected(repo, 'ENTRY_PACKET', task='V2-003', action='PREPARE')


def test_p1_cannot_start_before_gate(repo):
    path = repo / 'plan/machine/implementation-backlog.yaml'
    data = load(path)
    data['tasks'][4]['status'] = 'IN_PROGRESS'
    save(path, data)
    rejected(repo, 'TASK_START', task='V2-005')


@pytest.mark.parametrize('change', ['tracked', 'untracked', 'head', 'branch', 'artifact'])
def test_resume_detects_real_changes_even_when_both_states_dirty(repo, change):
    (repo / 'already-dirty').write_text('before')
    _, prior, checkpoint = entry(repo)
    assert prior['after']['dirty'] is True
    if change == 'tracked':
        (repo / 'scripts/task_execution.py').write_text((repo / 'scripts/task_execution.py').read_text()+'\n# changed\n')
    elif change == 'untracked':
        (repo / 'already-dirty').write_text('after')
    elif change == 'head':
        result = call(repo, 'git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'different checkout')
        assert result.returncode == 0
    elif change == 'branch':
        assert call(repo, 'git', 'checkout', '-b', 'other').returncode == 0
    else:
        packet = load(packet_path(repo))
        artifact = repo / 'plan' / packet['handoff']['last_check']['artifacts'][0]['ref']
        artifact.write_text('corrupted actual check output')
    result, report, _ = entry(repo, 'resume', checkpoint=checkpoint, command=SENTINEL)
    assert result.returncode != 0 and not (repo / 'sentinel').exists()
    assert any('ENTRY_RESUME' in error for error in report['errors'])


def test_child_failure_preserved_and_cannot_resume_as_success(repo):
    result, report, checkpoint = entry(repo, 'run', command=[sys.executable, '-c', "print('real failed run'); raise SystemExit(7)"])
    assert result.returncode == report['command_result']['exit_code'] == 7
    assert report['status'] == 'FAIL' and 'real failed run' in report['command_result']['stdout']
    result, report, _ = entry(repo, 'resume', checkpoint=checkpoint, command=SENTINEL)
    assert result.returncode != 0 and not (repo / 'sentinel').exists()


def test_unknown_handoff_not_inherited(repo):
    mutate_packet(repo, lambda p: p['handoff']['last_check'].update(status='UNKNOWN'))
    _, prior, checkpoint = entry(repo)
    assert prior['status'] == 'PASS'
    result, report, _ = entry(repo, 'resume', checkpoint=checkpoint, command=SENTINEL)
    assert result.returncode != 0 and any('ENTRY_HANDOFF' in error for error in report['errors'])
    assert not (repo / 'sentinel').exists()


def test_timeout_is_unknown_and_cannot_be_resumed_as_pass(repo):
    mutate_packet(repo, lambda p: p['budget'].update(maximum_runtime=0.05))
    result, report, checkpoint = entry(repo, 'run', command=[sys.executable, '-c', 'import time; time.sleep(1)'])
    assert result.returncode == 124 and report['status'] == 'UNKNOWN'
    assert report['command_result']['exit_code'] is None
    result, _, _ = entry(repo, 'resume', checkpoint=checkpoint, command=SENTINEL)
    assert result.returncode != 0 and not (repo / 'sentinel').exists()


def test_failed_post_command_observation_cannot_report_success(repo):
    command = [sys.executable, '-c', "from pathlib import Path; Path('.git/HEAD').write_text('invalid synthetic checkout')"]
    result, report, _ = entry(repo, 'run', command=command)
    assert report['command_result']['exit_code'] == 0
    assert result.returncode != 0 and report['status'] == 'UNKNOWN'


def test_reports_cannot_overwrite_plan_or_previous_result(repo):
    source = repo / 'plan/README.md'
    contents = source.read_bytes()
    result, _, _ = entry(repo, output=source)
    assert result.returncode != 0 and source.read_bytes() == contents
    _, _, checkpoint = entry(repo)
    previous = checkpoint.read_bytes()
    result, _, _ = entry(repo, output=checkpoint)
    assert result.returncode != 0 and checkpoint.read_bytes() == previous


def test_detached_head_allows_check_run_and_resume(repo):
    head = call(repo, 'git', 'rev-parse', 'HEAD').stdout.strip()
    assert call(repo, 'git', 'checkout', '--detach', head).returncode == 0
    result, report, _ = entry(repo)
    assert result.returncode == 0 and report['status'] == 'PASS'
    assert report['after']['branch'] is None and report['after']['head'] == head
    result, report, checkpoint = entry(repo, 'run', command=SENTINEL)
    assert result.returncode == 0 and (repo / 'sentinel').read_text() == 'executed'
    result, report, _ = entry(repo, 'resume', checkpoint=checkpoint)
    assert result.returncode == 0 and report['status'] == 'PASS'


@pytest.mark.parametrize('transition', ['detach', 'attach', 'detached_head_change'])
def test_resume_rejects_detached_context_changes(repo, transition):
    if transition != 'detach':
        assert call(repo, 'git', 'checkout', '--detach').returncode == 0
    _, _, checkpoint = entry(repo)
    if transition == 'detach':
        changed = call(repo, 'git', 'checkout', '--detach')
    elif transition == 'attach':
        changed = call(repo, 'git', 'checkout', 'main')
    else:
        changed = call(repo, 'git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                       'commit', '--allow-empty', '-qm', 'different detached checkout')
    assert changed.returncode == 0
    result, report, _ = entry(repo, 'resume', checkpoint=checkpoint, command=SENTINEL)
    assert result.returncode != 0 and report['status'] == 'BLOCKED'
    assert any('ENTRY_RESUME' in error for error in report['errors'])
    assert not (repo / 'sentinel').exists()


@pytest.mark.parametrize('contents', ['[]', 'null', '"text"', '1', 'true', '{}', '{"status":"PASS"}', '{'])
def test_malformed_checkpoint_writes_blocked_result_without_running_child(repo, contents):
    checkpoint = repo / 'dist/checkpoint.json'
    checkpoint.write_text(contents)
    result, report, output = entry(repo, 'resume', checkpoint=checkpoint, command=SENTINEL)
    assert result.returncode == 2 and report['status'] == 'BLOCKED'
    assert any('ENTRY_RESUME' in error for error in report['errors'])
    assert json.loads(output.read_text()) == report
    assert report['command_result'] is None and report['finished_at']
    assert 'Traceback' not in result.stderr
    assert not (repo / 'sentinel').exists()
