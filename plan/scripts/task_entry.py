"""Local action entry using existing plan rules. Not a protected CI runner.

Git/content observations support resumption, not semantic diff authorization
(V2-003) or remote provenance/credential enforcement (V2-004).
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys

import yaml
import validate_plan as validator


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def observe(root):
    """Observe exact tracked/untracked bytes, index, branch and checkout.

    Ignored build outputs are excluded by Git, not a task-defined scan exclusion.
    Symlinks bind their link text; we do not read arbitrary external targets.
    """
    actual_root = Path(os.fsdecode(git(root, 'rev-parse', '--show-toplevel')).strip()).resolve()
    if root != actual_root:
        raise ValueError('ENTRY_ROOT: entry must belong to the repository root')
    names = set(git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0')) - {b''}
    inventory = []
    for raw in sorted(names):
        name = os.fsdecode(raw)
        path = root / name
        if path.is_symlink():
            kind, value = 'symlink', os.fsencode(os.readlink(path))
        elif path.is_file():
            kind, value = 'file', path.read_bytes()
        elif not path.exists():
            kind, value = 'missing', b''
        else:
            raise ValueError('ENTRY_WORKTREE: unsupported tracked path ' + name)
        inventory.append({'path': name, 'kind': kind, 'sha256': digest(value),
                          'executable': bool(path.lstat().st_mode & 0o111) if path.exists() else False})
    status = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    return {'root': str(root), 'branch': os.fsdecode(git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD')).strip(),
            'head': git(root, 'rev-parse', 'HEAD').decode().strip(),
            'dirty': bool(status), 'status_sha256': digest(status),
            'index_sha256': digest(git(root, 'ls-files', '--stage', '-z')),
            'files': inventory, 'python': platform.python_version()}


def validate_context(root, task_id, action):
    """Reuse the full current rules, then bind selected action to the real Git base."""
    data = validator.load()
    errors = validator.validate_objects(data) + validator.check_files(data, validator.expected_views(data))
    task = next((t for t in data['implementation-backlog']['tasks'] if t['task_id'] == task_id), None)
    if task is None:
        return errors + ['ENTRY_TASK: task not registered'], None
    ref = task.get('execution_packet_ref')
    packet = None
    if not ref:
        errors.append('ENTRY_PACKET: selected task requires its own packet even for PREPARE')
    else:
        path = (root / 'plan' / ref).resolve()
        if not path.is_relative_to((root / 'plan/validation').resolve()) or not path.is_file():
            errors.append('ENTRY_PACKET: packet must resolve beneath plan/validation')
        else:
            packet = yaml.safe_load(path.read_text())
    if isinstance(packet, dict):
        if packet.get('task_id') != task_id or packet.get('action') != action:
            errors.append('ENTRY_ACTION: requested task/action does not match the bound packet')
        if task['status'] in {'VERIFIED', 'CLOSED'}:
            errors.append('ENTRY_STATE: completed task must be explicitly reopened before new actions')
        if action != 'PREPARE' and task['status'] not in {'IN_PROGRESS', 'IMPLEMENTED'}:
            errors.append('ENTRY_STATE: implementation requires task start transition')
        revision = packet.get('repository_revision', '')
        if not isinstance(revision, str) or len(revision) != 40:
            errors.append('ENTRY_BASE: invalid opening revision')
        else:
            exists = subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', revision, 'HEAD'], capture_output=True)
            if exists.returncode:
                errors.append('ENTRY_BASE: opening revision is absent or not an ancestor of current HEAD')
    return errors, packet


def safe_output(root, output):
    """Reports cannot rewrite sources, tracked files, or their own prior record."""
    output = output.resolve()
    if output.exists():
        raise ValueError('ENTRY_OUTPUT: use a new output file; prior records are immutable')
    if output.is_relative_to(root):
        relative = output.relative_to(root)
        if relative.parts[0] in {'plan', '.git'}:
            raise ValueError('ENTRY_OUTPUT: reports must be outside plan/.git')
        # Keep output writes from changing the observed source worktree. Using an
        # arbitrary task-specified ignore list here would conceal source changes.
        ignored = subprocess.run(['git', '-C', str(root), 'check-ignore', '--quiet', '--', str(relative)])
        tracked = git(root, 'ls-files', '--', str(relative)).strip()
        if ignored.returncode or tracked:
            raise ValueError('ENTRY_OUTPUT: in-repository reports require an untracked Git-ignored destination, e.g. dist/')
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['check', 'run', 'resume'])
    parser.add_argument('--task', required=True)
    parser.add_argument('--action', required=True, choices=['PREPARE', 'IMPLEMENT', 'LIVE_CALL', 'CERTIFY'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path)
    # argparse REMAINDER after a positional consumes options too; separate the
    # explicit command delimiter so normal options can occur after mode.
    raw = list(sys.argv[1:] if argv is None else argv)
    command = []
    if '--' in raw:
        index = raw.index('--')
        raw, command = raw[:index], raw[index+1:]
    args = parser.parse_args(raw)
    root = Path(__file__).resolve().parents[2]
    report = {'record_type': 'local_task_execution', 'schema_version': '1.0',
              'task_id': args.task, 'action': args.action, 'mode': args.mode,
              'started_at': datetime.now(timezone.utc).isoformat(), 'status': 'BLOCKED',
              'errors': [], 'command': command, 'command_result': None,
              'limitations': ['local observations; not CI or completion evidence',
                             'direct tools/shared writers are not protected by this entry',
                             'command semantics and actual diff scope belong to caller/V2-003']}
    output = None
    code = 2
    command_started = False
    try:
        output = safe_output(root, args.output)
        if args.mode == 'run' and not command:
            raise ValueError('ENTRY_COMMAND: run requires a command after --')
        if args.mode == 'check' and (command or args.checkpoint):
            raise ValueError('ENTRY_COMMAND: check neither executes nor resumes')
        if args.mode == 'resume' and not args.checkpoint:
            raise ValueError('ENTRY_RESUME: checkpoint required')
        if args.mode != 'resume' and args.checkpoint:
            raise ValueError('ENTRY_RESUME: checkpoint only applies to resume')
        before = observe(root)
        report['before'] = before
        errors, packet = validate_context(root, args.task, args.action)
        after_validation = observe(root)
        if before != after_validation:
            errors.append('ENTRY_RACE: repository changed during validation; reconcile and retry')
        if args.mode == 'resume':
            previous = json.loads(args.checkpoint.read_text())
            report['checkpoint'] = {'path': str(args.checkpoint.resolve()), 'sha256': digest(args.checkpoint.read_bytes())}
            if (previous.get('record_type') != 'local_task_execution' or previous.get('schema_version') != '1.0'
                    or previous.get('status') != 'PASS' or previous.get('task_id') != args.task
                    or previous.get('action') != args.action or previous.get('after') != before):
                errors.append('ENTRY_RESUME: prior success/context does not match actual repository and inputs')
            if packet and packet.get('handoff', {}).get('last_check', {}).get('status') != 'PASS':
                errors.append('ENTRY_HANDOFF: resume cannot inherit missing, failed or unknown last check')
        if command and args.action in {'LIVE_CALL', 'CERTIFY'}:
            errors.append('ENTRY_AUTHORIZATION: paid/certification dispatch requires the future protected authorization adapter; this local entry checks declarations only')
        report['errors'] = errors
        if not errors:
            code = 0
            if command:
                command_started = True
                result = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                        timeout=packet['budget']['maximum_runtime'])
                report['command_result'] = {'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
                code = result.returncode if result.returncode >= 0 else 128 - result.returncode
            report['status'] = 'PASS' if code == 0 else 'FAIL'
        report['after'] = observe(root)
    except subprocess.TimeoutExpired as exc:
        report['status'] = 'UNKNOWN'
        report['errors'].append('ENTRY_TIMEOUT: command interrupted; inspect effects before a fresh check')
        report['command_result'] = {'exit_code': None, 'stdout': str(exc.stdout or ''), 'stderr': str(exc.stderr or '')}
        code = 124
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, yaml.YAMLError) as exc:
        # A successful child is not a successful handoff if post-run observation
        # failed. Preserve uncertainty instead of returning a false green result.
        code = 2
        report['status'] = 'UNKNOWN' if command_started else 'BLOCKED'
        report['errors'].append(f'{type(exc).__name__}: {exc}')
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'task_id', 'action', 'errors')}, ensure_ascii=False))
    return code
