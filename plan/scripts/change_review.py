"""Local Git scope and review binding; a Git pin is not protected remote trust.

The candidate cannot supply its own scope or exceptions: baseline/authorization
bytes are read from separately named immutable Git revisions. Shared writers can
still bypass or change the caller; V2-004 must establish the external boundary.
"""
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile

import yaml
from execution_checks import bounded_path


class ReviewError(ValueError):
    pass


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def digest(value):
    return hashlib.sha256(value).hexdigest() if value is not None else None


def matches(path, scopes):
    return any(path == s or (s.endswith('/') and path.startswith(s)) for s in scopes)


def tree(root, revision):
    result = {}
    for row in git(root, 'ls-tree', '-rz', '--full-tree', revision).split(b'\0'):
        if not row:
            continue
        fields, raw = row.split(b'\t', 1)
        mode, kind, oid = fields.decode().split()
        if kind != 'blob':
            raise ReviewError('DIFF_TYPE: Git submodules/unsupported objects require explicit review')
        result[os.fsdecode(raw)] = {'mode': mode, 'oid': oid}
    return result


def index_tree(root):
    result = {}
    for row in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if not row:
            continue
        fields, raw = row.split(b'\t', 1)
        mode, oid, stage = fields.decode().split()
        if stage != '0' or mode == '160000':
            raise ReviewError('DIFF_INDEX: unmerged index or submodule cannot be certified')
        result[os.fsdecode(raw)] = {'mode': mode, 'oid': oid}
    return result


def pinned_file(root, revision, path):
    if not bounded_path(path) or path.endswith('/'):
        raise ReviewError('DIFF_PIN: invalid pinned file path')
    info = tree(root, revision).get(path)
    if not info or info['mode'] not in {'100644', '100755'}:
        raise ReviewError('DIFF_PIN: pinned input must be a regular committed file')
    return git(root, 'cat-file', 'blob', info['oid'])


def candidate_file(root, ref):
    """Reject symlink parents before any candidate content is read."""
    if not bounded_path(ref) or ref.endswith('/'):
        raise ReviewError('DIFF_PATH: invalid candidate file path')
    current = root
    for component in PurePosixPath(ref).parts:
        current = current / component
        if current.is_symlink():
            raise ReviewError('DIFF_PATH: candidate file or parent is a symlink')
    if not current.resolve().is_relative_to(root):
        raise ReviewError('DIFF_PATH: candidate file escapes repository')
    return current


def require_revision(root, revision):
    if not isinstance(revision, str) or len(revision) not in (40, 64) or any(c not in '0123456789abcdef' for c in revision):
        raise ReviewError('DIFF_PIN: use an explicit full Git commit ID')
    if git(root, 'rev-parse', revision+'^{commit}').decode().strip() != revision:
        raise ReviewError('DIFF_PIN: input is not a commit')
    if subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', revision, 'HEAD'], capture_output=True).returncode:
        raise ReviewError('DIFF_PIN: pinned revision is not an ancestor of current checkout')


def host_local_input(name):
    """Recognize concrete tool artifacts, never a source-directory exclusion."""
    if name == '.claude/settings.local.json':
        return True
    parts = PurePosixPath(name).parts
    if len(parts) == 2:
        return parts[0] in {'.ruff_cache', '.mypy_cache'} and parts[1] in {'.gitignore', 'CACHEDIR.TAG'}
    if len(parts) != 3 or re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', parts[1]) is None:
        return False
    return ((parts[0] == '.ruff_cache' and re.fullmatch(r'[0-9]+', parts[2]) is not None)
            or (parts[0] == '.mypy_cache' and parts[2] == 'cache.db'))


def load_baseline(root, task_id, revision, ref):
    require_revision(root, revision)
    raw = pinned_file(root, revision, ref)
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get('record_type') != 'local_change_baseline' or value.get('schema_version') != '1.0' or value.get('task_id') != task_id:
        raise ReviewError('DIFF_BASELINE: invalid record/task')
    require_revision(root, value.get('opening_revision'))
    if subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', value['opening_revision'], revision], capture_output=True).returncode:
        raise ReviewError('DIFF_BASELINE: opening revision is not an ancestor of scope pin')
    if not value.get('allowed_paths') or not all(bounded_path(p) for p in value['allowed_paths']):
        raise ReviewError('DIFF_SCOPE: baseline contains invalid scope')
    if not isinstance(value.get('pre_existing'), dict):
        raise ReviewError('DIFF_BASELINE: pre-existing inventory is required')
    opening_files = tree(root, value['opening_revision'])
    for name, record in value['pre_existing'].items():
        if not bounded_path(name) or not isinstance(record, dict) or not isinstance(record.get('worktree'), (dict, type(None))):
            raise ReviewError('DIFF_BASELINE: malformed pre-existing identity')
        if 'allow_absent' in record and type(record['allow_absent']) is not bool:
            raise ReviewError('DIFF_LOCAL_INPUT: allow_absent must be a boolean')
        if record.get('allow_absent'):
            identity = record.get('worktree') or {}
            if (not host_local_input(name) or name in opening_files or 'index' not in record or record['index'] is not None
                    or identity.get('kind') != 'file' or identity.get('mode') != '100644'
                    or re.fullmatch(r'[0-9a-f]{64}', str(identity.get('sha256', ''))) is None):
                raise ReviewError('DIFF_LOCAL_INPUT: only exact untracked regular host-local files may be absent')
    # Ref/hash identifies the actual authorization input; it is not an approval
    # merely because a candidate writes a matching string into a new document.
    source = value.get('authorization_source', {})
    authority = pinned_file(root, revision, source.get('ref', ''))
    if digest(authority) != source.get('sha256') or source.get('kind') != 'existing_user_task_authorization':
        raise ReviewError('DIFF_AUTHORITY: baseline authorization input changed or unsupported')
    for grant in value.get('exception_authorizations', []):
        source = grant.get('authorization_source', {})
        required_kind = ('explicit_scope_change_authorization' if grant.get('code') == 'PRODUCTION_SCOPE_REVIEW'
                         else 'explicit_rule_revision_authorization')
        if source.get('kind') != required_kind or digest(pinned_file(root, revision, source.get('ref',''))) != source.get('sha256'):
            raise ReviewError('DIFF_AUTHORITY: exception grant has no fixed authorization source')
        identities = [grant.get(k) for k in ('old_sha', 'new_sha')]
        valid_sha = lambda v: v is None or (isinstance(v, str) and len(v) == 64 and all(c in '0123456789abcdef' for c in v))
        if (grant.get('task_id') != task_id or not all(grant.get(k) for k in ('code','path'))
                or not all(k in grant for k in ('old_sha','new_sha'))
                or not all(valid_sha(v) for v in identities) or identities == [None, None]):
            raise ReviewError('DIFF_AUTHORITY: exception grant lacks exact task/change identity')
        if not bounded_path(grant['path']) or grant['path'].endswith('/'):
            raise ReviewError('DIFF_AUTHORITY: grant needs an exact file path')
        prior = tree(root, revision).get(grant['path'])
        if prior and prior['mode'] not in {'100644', '100755'}:
            raise ReviewError('DIFF_AUTHORITY: grant baseline must be a regular file')
        pinned_old = digest(git(root, 'cat-file', 'blob', prior['oid'])) if prior else None
        if pinned_old != grant['old_sha']:
            raise ReviewError('DIFF_AUTHORITY: grant must be pinned with the pre-change file identity')
    current = candidate_file(root, ref)
    if not current.is_file() or current.read_bytes() != raw:
        raise ReviewError('DIFF_BASELINE: candidate modified/deleted the frozen baseline')
    index = index_tree(root)
    indexed_scope = index.get(ref)
    if not indexed_scope or indexed_scope['mode'] not in {'100644','100755'} or git(root,'cat-file','blob',indexed_scope['oid']) != raw:
        raise ReviewError('DIFF_BASELINE: index modified/deleted the frozen baseline')
    packet_path = candidate_file(root, value['packet_ref'])
    packet = yaml.safe_load(packet_path.read_text())
    if not isinstance(packet, dict) or packet.get('task_id') != task_id or packet.get('repository_revision') != value['opening_revision'] or packet.get('allowed_paths') != value['allowed_paths']:
        raise ReviewError('DIFF_SCOPE: candidate task, opening revision or allowed paths differ from frozen scope')
    indexed_packet = index.get(value['packet_ref'])
    if not indexed_packet or indexed_packet['mode'] not in {'100644','100755'}:
        raise ReviewError('DIFF_SCOPE: index packet must exist as a regular file')
    staged = yaml.safe_load(git(root,'cat-file','blob',indexed_packet['oid']))
    if not isinstance(staged,dict) or any(staged.get(k)!=packet[k] for k in ('task_id','repository_revision','allowed_paths')):
        raise ReviewError('DIFF_SCOPE: index task scope differs from frozen scope')
    value['_pin'] = {'revision': revision, 'ref': ref, 'sha256': digest(raw)}
    return value


def untracked_paths(root, opening):
    # Do not consume candidate .gitignore, info/exclude or host-global excludes.
    # Baseline root ignores retain existing cache/secret boundaries. Production
    # source directories are independently enumerated below, even if ignored.
    base_tree = tree(root, opening)
    if any(p.endswith('/.gitignore') for p in base_tree):
        raise ReviewError('DIFF_IGNORE: nested baseline ignore policies require an explicit adapter')
    patterns = git(root, 'cat-file', 'blob', base_tree['.gitignore']['oid']) if '.gitignore' in base_tree else b''
    with tempfile.NamedTemporaryFile() as stream:
        stream.write(patterns); stream.flush()
        names = {os.fsdecode(x) for x in git(root, 'ls-files', '--others', '-z', '--exclude-from='+stream.name).split(b'\0') if x}
    for area in ('src', 'tests', 'scripts', 'plan/scripts', 'plan/machine', 'plan/schemas'):
        path = root / area
        if path.is_symlink():
            names.add(area)
        elif path.is_dir():
            for directory, dirs, files in os.walk(path, followlinks=False):
                for name in files + [d for d in dirs if (Path(directory)/d).is_symlink()]:
                    # Cache *directories* can contain source, so still traverse
                    # them. Only generated bytecode suffixes follow the fixed
                    # Python cache exclusion; a .py there must be reviewed.
                    if name.endswith(('.pyc','.pyo')):
                        continue
                    names.add(str((Path(directory)/name).relative_to(root)))
    return names


def file_identity(root, name, algorithm):
    path = root / name
    # Never traverse a parent symlink to obtain candidate bytes.
    if not path.parent.resolve().is_relative_to(root) or any(p.is_symlink() for p in list(path.parents)[:len(PurePosixPath(name).parts)-1]):
        raise ReviewError('DIFF_PATH: symlink parent or path escape: '+name)
    if not path.exists() and not path.is_symlink():
        return None, None
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        data = os.fsencode(os.readlink(path)); git_mode = '120000'; kind = 'symlink'
    elif stat.S_ISREG(mode):
        data = path.read_bytes(); git_mode = '100755' if mode & 0o111 else '100644'; kind = 'file'
    else:
        raise ReviewError('DIFF_TYPE: unsupported worktree object: '+name)
    oid = hashlib.new(algorithm, b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    return {'mode': git_mode, 'oid': oid, 'sha256': digest(data), 'kind': kind}, data


def snapshot(root, opening):
    index = index_tree(root)
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    baseline = tree(root, opening)
    names = set(index) | set(baseline) | untracked_paths(root, opening)
    algorithm = git(root, 'rev-parse', '--show-object-format').decode().strip()
    working, contents = {}, {}
    for name in sorted(names):
        if not bounded_path(name):
            raise ReviewError('DIFF_PATH: invalid Git/worktree path')
        info, data = file_identity(root, name, algorithm)
        if info:
            working[name] = info
            # Keep only relevant changed bytes, not the full historical tree.
            if info['oid'] != baseline.get(name, {}).get('oid'):
                contents[name] = data
    identity = {'head': head, 'index': index, 'worktree': working}
    identity_hash = digest(json.dumps(identity, sort_keys=True).encode())
    return {'identity': identity, 'identity_sha256': identity_hash, 'baseline': baseline, 'contents': contents}


def collect_changes(root, observed, baseline):
    changes, preexisting = [], []
    original = observed['baseline']
    index = observed['identity']['index']
    working = observed['identity']['worktree']
    cache = {}
    def blob(info):
        if info is None:
            return None
        oid = info['oid']
        if oid not in cache:
            cache[oid] = git(root, 'cat-file', 'blob', oid)
        return cache[oid]
    head_tree = tree(root, observed['identity']['head'])
    for name in sorted(set(original) | set(index) | set(working)):
        prior = baseline['pre_existing'].get(name)
        current_work = working.get(name)
        work_identity = {k:current_work[k] for k in ('kind','mode','sha256')} if current_work else None
        if prior and prior.get('worktree') == work_identity and prior.get('index') == index.get(name):
            preexisting.append(name)
            continue
        before = original.get(name)
        for layer, value in [('index', index.get(name)), ('worktree', current_work)]:
            if value and before and (value['mode'],value['oid']) == (before['mode'],before['oid']):
                continue
            if value is None and before is None:
                continue
            status = 'A' if before is None else 'D' if value is None else 'M'
            after_bytes = (observed['contents'].get(name, blob(before)) if layer=='worktree' else blob(value)) if value else None
            changes.append({'path':name,'layer':layer,'status':status,'old_mode':before['mode'] if before else None,'new_mode':value['mode'] if value else None,'old_bytes':blob(before),'new_bytes':after_bytes,'staged':index.get(name)!=head_tree.get(name),'unstaged':(index.get(name) or {}).get('oid')!=(current_work or {}).get('oid') or (index.get(name) or {}).get('mode')!=(current_work or {}).get('mode'),'untracked':name not in index})
    return changes, preexisting


def verify_coverage(root, observed, changes, preexisting):
    # Independently recompute the expected content/mode differences. An empty or
    # truncated result cannot certify a nonempty observation.
    expected = set()
    for layer, inventory in [('index',observed['identity']['index']),('worktree',observed['identity']['worktree'])]:
        for name in set(observed['baseline']) | set(inventory):
            a,b = observed['baseline'].get(name),inventory.get(name)
            if name not in preexisting and ((a or {}).get('mode'),(a or {}).get('oid')) != ((b or {}).get('mode'),(b or {}).get('oid')):
                expected.add((name,layer))
    actual = {(c['path'],c['layer']) for c in changes}
    if expected != actual or len(actual) != len(changes):
        raise ReviewError('DIFF_COVERAGE: changed content missing or duplicated in review')


def path_findings(root, changes, baseline):
    result = []
    for item in changes:
        name = item['path']
        if not matches(name, baseline['allowed_paths']):
            result.append({'code':'SCOPE_OUTSIDE','path':name,'layer':item['layer'],'reason':'Change is outside frozen task scope'})
        if item['new_mode']=='120000':
            target = os.fsdecode(item['new_bytes'])
            resolved = (root / name).parent.joinpath(target).resolve()
            if os.path.isabs(target) or not resolved.is_relative_to(root) or not matches(str(resolved.relative_to(root)),baseline['allowed_paths']):
                result.append({'code':'SCOPE_SYMLINK','path':name,'layer':item['layer'],'reason':'Symlink target escapes frozen allowed scope'})
    return result


def preexisting_drift(observed, baseline):
    findings = []
    for name, prior in baseline['pre_existing'].items():
        current = observed['identity']['worktree'].get(name)
        work = {k:current[k] for k in ('kind','mode','sha256')} if current else None
        index = observed['identity']['index'].get(name)
        # Fresh checkouts do not contain the originating host's private config
        # or tool artifacts. Present, changed, staged and new files remain checked.
        if prior.get('allow_absent') is True and current is None and index is None:
            continue
        if work == prior['worktree'] and index == prior['index']:
            continue
        # Only an existing explicit task edit grant (the reviewed prompt here)
        # can adopt an opening user change. Matching the old Git blob again is
        # still destruction of a dirty user edit, not an empty task diff.
        if prior.get('task_edit_authorized') and matches(name,baseline['allowed_paths']):
            continue
        findings.append({'code':'PRE_EXISTING_CHANGED','path':name,'layer':'opening-worktree',
                         'reason':'User-owned opening worktree/index identity changed',
                         'opening_worktree':prior['worktree'],'current_worktree':work,
                         'opening_index':prior['index'],'current_index':index})
    return findings


def weakening_inputs(changes):
    """Preserve both scope endpoints, but recognize lossless test-file moves."""
    paired, result = set(), []
    for i, old in enumerate(changes):
        if old['status'] != 'D':
            continue
        options = [(j,new) for j,new in enumerate(changes) if j not in paired and new['status']=='A'
                   and new['layer']==old['layer'] and new['new_bytes']==old['old_bytes']
                   and new['new_mode']==old['old_mode']]
        if len(options)!=1:
            continue
        j,new = options[0]
        def discovered_test(path):
            name = PurePosixPath(path).name
            return path.startswith('tests/') and name.endswith('.py') and (name.startswith('test_') or name.endswith('_test.py'))
        if discovered_test(old['path']) and (not discovered_test(new['path'])
                or PurePosixPath(old['path']).parent != PurePosixPath(new['path']).parent):
            continue
        result.append({**new,'old_path':old['path'],'status':'R','old_bytes':old['old_bytes'],'old_mode':old['old_mode']})
        paired.update((i,j))
    return result + [c for i,c in enumerate(changes) if i not in paired]


def apply_dispositions(root, findings, baseline, revision=None, ref=None):
    """A pinned review records a disposition, never erases an original finding."""
    if not revision and not ref:
        return findings, []
    if not revision or not ref:
        raise ReviewError('DIFF_REVIEW: both review revision and ref are required')
    require_revision(root, revision)
    review = json.loads(pinned_file(root, revision, ref))
    if not isinstance(review,dict) or review.get('task_id')!=baseline['task_id'] or review.get('baseline_pin')!=baseline['_pin']:
        raise ReviewError('DIFF_REVIEW: review task/baseline mismatch')
    entries = review.get('dispositions')
    if not isinstance(entries,list):
        raise ReviewError('DIFF_REVIEW: missing dispositions')
    by_id = {f['id']:f for f in findings}
    used = set()
    for entry in entries:
        if not isinstance(entry,dict) or entry.get('finding_id') not in by_id or entry['finding_id'] in used:
            raise ReviewError('DIFF_REVIEW: stale, unknown or duplicate finding')
        finding = by_id[entry['finding_id']]
        if any(entry.get(k)!=finding[k] for k in ('path','old_sha','new_sha','code','layer')):
            raise ReviewError('DIFF_REVIEW: changed content is not authorized by this review')
        if entry.get('disposition') not in {'REVIEWED_NO_WEAKENING','AUTHORIZED_EXCEPTION'} or not all(isinstance(entry.get(k),str) and entry[k].strip() for k in ('reason','impact','reviewer','replacement_validation')):
            raise ReviewError('DIFF_REVIEW: review rationale/impact/validation missing')
        source = entry.get('authorization_source')
        # Existing task grant can support demonstrated equivalent/strengthening
        # integration, never lower a minimum requirement. Actual weakening needs
        # a separate prior explicit grant, which this task does not possess.
        technical = (entry['disposition']=='REVIEWED_NO_WEAKENING' and finding.get('severity_kind')=='REVIEW'
                     and source==baseline['authorization_source'])
        exception = (entry['disposition']=='AUTHORIZED_EXCEPTION' and any(
            grant.get('authorization_source')==source and all(grant.get(k)==finding[k] for k in ('code','path','old_sha','new_sha'))
            for grant in baseline.get('exception_authorizations', [])))
        if not (technical or exception) or not entry.get('verification_artifacts'):
            raise ReviewError('DIFF_REVIEW: missing applicable authorization (self-signed exceptions are not grants)')
        for artifact in entry['verification_artifacts']:
            data = pinned_file(root, revision, artifact['ref'])
            if digest(data)!=artifact['sha256']:
                raise ReviewError('DIFF_REVIEW: replacement verification bytes mismatch')
        finding['disposition'] = entry['disposition']; finding['review_ref'] = ref; used.add(finding['id'])
    return findings, [{'revision':revision,'ref':ref,'dispositions':len(used)}]


def review_changes(root, *, task_id, scope_revision, scope_ref, review_revision=None, review_ref=None):
    root = Path(root).resolve()
    report = {'record_type':'local_change_review','schema_version':'1.0','task_id':task_id,'started_at':datetime.now(timezone.utc).isoformat(),'status':'FAIL','errors':[],'changes':[],'findings':[],'limitations':['Local Git pins/records do not authenticate remote provenance or caller authority','Path legality does not prove task semantics or runtime permission','Shared writers can modify or bypass this tool; protected CI belongs to V2-004']}
    try:
        if Path(os.fsdecode(git(root,'rev-parse','--show-toplevel')).strip()).resolve()!=root:
            raise ReviewError('DIFF_ROOT: repository root required')
        baseline = load_baseline(root,task_id,scope_revision,scope_ref)
        report['baseline_pin']=baseline['_pin']; report['opening_revision']=baseline['opening_revision']
        observed = snapshot(root,baseline['opening_revision'])
        changes,preexisting = collect_changes(root,observed,baseline)
        verify_coverage(root,observed,changes,preexisting)
        report.update(head=observed['identity']['head'],observation_sha256=observed['identity_sha256'],scanned_files=len(observed['identity']['worktree']),pre_existing_unchanged=preexisting,scope_findings=path_findings(root,changes,baseline)+preexisting_drift(observed,baseline))
        report['optional_local_inputs_absent'] = [name for name, record in baseline['pre_existing'].items()
                                                 if record.get('allow_absent') is True
                                                 and name not in observed['identity']['worktree']
                                                 and name not in observed['identity']['index']]
        from weakening_checks import scan_weakening
        findings = scan_weakening(weakening_inputs(changes),task_id=task_id,baseline=baseline)
        # P0 scope permits boundary tooling, not arbitrary production business
        # code. A path match alone cannot attest a new production module's role.
        if task_id=='V2-003':
            for change in changes:
                if change['path'].startswith('src/anovel/'):
                    row={k:change[k] for k in ('path','layer')}
                    row.update(code='PRODUCTION_SCOPE_REVIEW',severity_kind='AUTHORIZATION_REQUIRED',pointer='V2-003/P0',old_sha=digest(change['old_bytes']),new_sha=digest(change['new_bytes']),reason='Production changes require a prior exact scope authorization grant; generic task/technical review cannot grant cross-phase scope')
                    row['id']=digest(json.dumps(row,sort_keys=True).encode());findings.append(row)
        findings, reviews = apply_dispositions(root,findings,baseline,review_revision,review_ref)
        report['findings']=findings; report['reviews']=reviews
        for item in changes:
            row={k:v for k,v in item.items() if k not in {'old_bytes','new_bytes'}}
            row.update(old_sha=digest(item['old_bytes']),new_sha=digest(item['new_bytes'])); report['changes'].append(row)
        # Matching delete/add content is reported as a rename hint only. Both
        # original paths remain in the independent scope and weakening checks.
        report['rename_hints']=[{'old_path':a['path'],'new_path':b['path'],'layer':a['layer'],'status':'content-identical rename hint'} for a in report['changes'] for b in report['changes'] if a['status']=='D' and b['status']=='A' and a['layer']==b['layer'] and a['old_sha']==b['new_sha']]
        after = snapshot(root,baseline['opening_revision'])
        if observed['identity_sha256']!=after['identity_sha256']:
            raise ReviewError('DIFF_RACE: repository changed while being reviewed')
        report['no_changes']=not changes
        if not report['scope_findings'] and all(f.get('disposition') in {'REVIEWED_NO_WEAKENING','AUTHORIZED_EXCEPTION'} for f in findings):
            report['status']='PASS'
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError,yaml.YAMLError) as exc:
        report['errors'].append(f'{type(exc).__name__}: {exc}')
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    return report
