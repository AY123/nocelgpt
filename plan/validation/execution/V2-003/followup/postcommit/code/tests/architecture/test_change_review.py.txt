"""Real Git/index/worktree and pinned-authority tests in disposable repositories."""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'plan/scripts'))
import change_review as cr

TASK='V2-003'
SCOPE='meta/scope.json'
BEFORE=b'def test_required():\n    assert 1 == 1\n'
AFTER=b'\n'


def run(repo,*argv):
    result=subprocess.run(argv,cwd=repo,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    return result.stdout.strip()


def write(repo,path,data):
    p=repo/path;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(data if isinstance(data,bytes) else data.encode())


def commit(repo,message):
    run(repo,'git','add','.')
    run(repo,'git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm',message)
    return run(repo,'git','rev-parse','HEAD')


def make_repo(path, *, grants=None, grant_kind="explicit_rule_revision_authorization"):
    path.mkdir();repo=path.resolve()
    run(repo,'git','init','-b','main')
    for name,data in {'.gitignore':'dist/\n__pycache__/\n','allowed/existing.py':'value = 1\n','outside.py':'original\n','user.txt':'original user\n','tests/test_sample.py':BEFORE,'authority.txt':'Synthetic fixture: authorized local task integration, not remote trust.\n','scripts/checker.py':'def check():\n    return True\n'}.items():write(repo,name,data)
    opening=commit(repo,'opening fixture')
    write(repo,'user.txt','user already edited this\n')
    info=cr.index_tree(repo)['user.txt']
    scopes=['allowed/','tests/','meta/','scripts/checker.py','.gitignore','src/anovel/']
    packet={'task_id':TASK,'repository_revision':opening,'allowed_paths':scopes}
    write(repo,'meta/packet.yaml',yaml.safe_dump(packet))
    base={'record_type':'local_change_baseline','schema_version':'1.0','task_id':TASK,'opening_revision':opening,'packet_ref':'meta/packet.yaml','allowed_paths':scopes,'pre_existing':{'user.txt':{'worktree':{'kind':'file','mode':'100644','sha256':cr.digest((repo/'user.txt').read_bytes())},'index':info,'task_edit_authorized':False}},'protected_paths':['scripts/checker.py','.gitignore'],'authorization_source':{'kind':'existing_user_task_authorization','ref':'authority.txt','sha256':cr.digest((repo/'authority.txt').read_bytes())}}
    if grants:
        write(repo,'meta/rule-grant.txt','Synthetic prior explicit rule-revision grant; only listed content.\n')
        source={'kind':grant_kind,'ref':'meta/rule-grant.txt','sha256':cr.digest((repo/'meta/rule-grant.txt').read_bytes())}
        base['exception_authorizations']=[dict(g,authorization_source=source,task_id=TASK) for g in grants]
    write(repo,SCOPE,json.dumps(base))
    # Keep the user-owned dirty content out of both preparation commits.
    run(repo,'git','add','meta')
    run(repo,'git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixed local scope')
    return repo,run(repo,'git','rev-parse','HEAD'),base


@pytest.fixture
def context(tmp_path):
    return make_repo(tmp_path/'repo')


def review(context,**kwargs):
    repo,pin,_=context
    return cr.review_changes(repo,task_id=TASK,scope_revision=pin,scope_ref=SCOPE,**kwargs)


def assert_pass(report):
    assert report['status']=='PASS',report


def test_real_baseline_and_unchanged_user_edit_pass(context):
    result=review(context);assert_pass(result)
    assert result['scanned_files']>0 and result['pre_existing_unchanged']==['user.txt']
    assert not any(c['path']=='user.txt' for c in result['changes'])


@pytest.mark.parametrize('mutation',['added','modified','deleted','renamed','staged','committed'])
def test_ordinary_in_scope_changes_pass(context,mutation):
    repo,_,_=context
    assert_pass(review(context))
    if mutation=='added':write(repo,'allowed/new.py','answer=42\n')
    elif mutation=='modified':write(repo,'allowed/existing.py','value=2\n')
    elif mutation=='deleted':(repo/'allowed/existing.py').unlink()
    elif mutation=='renamed':(repo/'allowed/existing.py').rename(repo/'allowed/moved.py')
    else:
        write(repo,'allowed/existing.py','value=2\n');run(repo,'git','add','allowed/existing.py')
        if mutation=='committed':run(repo,'git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','legitimate task file')
    result=review(context);assert_pass(result)
    assert any(c['path'].startswith('allowed/') for c in result['changes'])
    if mutation=='renamed':assert result['rename_hints']
    if mutation=='staged':assert any(c['staged'] for c in result['changes'])


@pytest.mark.parametrize('mutation',['untracked','modified','deleted','rename_out','rename_in','changed_user','staged_user'])
def test_out_of_scope_changes_cannot_hide(context,mutation):
    repo,_,_=context
    assert_pass(review(context))
    if mutation=='untracked':write(repo,'unrelated/new.py','oops\n')
    elif mutation=='modified':write(repo,'outside.py','oops\n')
    elif mutation=='deleted':(repo/'outside.py').unlink()
    elif mutation=='rename_out':(repo/'allowed/existing.py').rename(repo/'unrelated.py')
    elif mutation=='rename_in':(repo/'outside.py').rename(repo/'allowed/moved.py')
    elif mutation=='changed_user':write(repo,'user.txt','agent changed user file\n')
    else:run(repo,'git','add','user.txt')
    result=review(context)
    assert result['status']=='FAIL' and any(f['code']=='SCOPE_OUTSIDE' for f in result['scope_findings'])


def test_new_candidate_ignore_cannot_conceal_untracked_change(context):
    repo,_,_=context
    write(repo,'.gitignore','dist/\n__pycache__/\nconcealed.py\n');write(repo,'concealed.py','bad=1\n')
    result=review(context);assert result['status']=='FAIL'
    assert any(c['path']=='concealed.py' for c in result['changes'])


@pytest.mark.parametrize('target',['../../outside-repository','../outside.py','/tmp/external-file'])
def test_symlink_scope_escape_fails_without_reading_target(context,target):
    repo,_,_=context;(repo/'allowed/link.py').symlink_to(target)
    result=review(context);assert result['status']=='FAIL'
    assert any(f['code']=='SCOPE_SYMLINK' for f in result['scope_findings'])


def test_internal_allowed_symlink_is_observed_by_link_text(context):
    repo,_,_=context;(repo/'allowed/link.py').symlink_to('existing.py')
    result=review(context);assert_pass(result)
    row=next(c for c in result['changes'] if c['path']=='allowed/link.py')
    assert row['new_mode']=='120000' and row['new_sha']==cr.digest(b'existing.py')


def test_parent_symlink_escape_cannot_read_external_contents(context,tmp_path):
    repo,_,_=context;external=tmp_path/'external';external.mkdir();(external/'private.py').write_text('private')
    (repo/'allowed/dir').symlink_to(external,target_is_directory=True)
    result=review(context);assert result['status']=='FAIL'
    assert any(f['code']=='SCOPE_SYMLINK' for f in result.get('scope_findings',[])) or result['errors']


@pytest.mark.parametrize('mutation',['scope_file','packet_scope','packet_revision','wrong_pin'])
def test_candidate_cannot_redefine_its_own_scope(context,mutation):
    repo,pin,_=context
    if mutation=='scope_file':
        data=json.loads((repo/SCOPE).read_text());data['allowed_paths'].append('outside.py');write(repo,SCOPE,json.dumps(data))
    elif mutation=='wrong_pin':
        report=cr.review_changes(repo,task_id=TASK,scope_revision='f'*40,scope_ref=SCOPE)
        assert report['status']=='FAIL' and report['errors'];return
    else:
        data=yaml.safe_load((repo/'meta/packet.yaml').read_text());data['allowed_paths'].append('outside.py') if mutation=='packet_scope' else data.update(repository_revision=pin)
        write(repo,'meta/packet.yaml',yaml.safe_dump(data))
    result=review(context);assert result['status']=='FAIL' and result['errors']


def test_index_weakening_is_seen_even_when_worktree_restores_original(context):
    repo,_,_=context
    write(repo,'tests/test_sample.py',AFTER);run(repo,'git','add','tests/test_sample.py');write(repo,'tests/test_sample.py',BEFORE)
    result=review(context);assert result['status']=='FAIL'
    assert any(f['layer']=='index' and f['severity_kind']=='WEAKENING' for f in result['findings'])


def test_coverage_rejects_injected_empty_change_collection(context,monkeypatch):
    repo,_,_=context;write(repo,'allowed/new.py','new=1\n')
    monkeypatch.setattr(cr,'collect_changes',lambda *args:([],[]))
    result=review(context);assert result['status']=='FAIL' and any('DIFF_COVERAGE' in e for e in result['errors'])


def test_race_is_not_a_success(context,monkeypatch):
    original=cr.snapshot;count=0
    def changed(*args):
        nonlocal count
        result=original(*args);count+=1
        if count==2:result['identity_sha256']='different'
        return result
    monkeypatch.setattr(cr,'snapshot',changed)
    result=review(context);assert result['status']=='FAIL' and any('DIFF_RACE' in e for e in result['errors'])


def test_real_detached_checkout_supported(context):
    repo,pin,_=context;run(repo,'git','checkout','--detach',pin)
    assert_pass(review(context))


def test_test_file_rename_keeps_requirements_but_scope_checks_both_ends(context):
    repo,_,_=context;(repo/'tests/test_sample.py').rename(repo/'tests/test_renamed.py')
    result=review(context);assert_pass(result);assert result['rename_hints']


def test_test_moved_out_of_discovery_is_not_lossless(context):
    repo,_,_=context;(repo/'tests/test_sample.py').rename(repo/'allowed/disguised.py')
    result=review(context);assert result['status']=='FAIL' and result['findings']


def pin_review(context, findings, disposition='REVIEWED_NO_WEAKENING', source=None):
    repo,pin,base=context
    write(repo,'meta/verification.txt','Synthetic fixture verification actually checked by this pytest; not production evidence.\n')
    baseline=cr.load_baseline(repo,TASK,pin,SCOPE)
    rows=[]
    for finding in findings:
        row={k:finding[k] for k in ['path','layer','code','old_sha','new_sha']}
        row.update(finding_id=finding['id'],disposition=disposition,reason='Fixture-specific equivalence reviewed',impact='Only the exact fixture rule bytes',reviewer='test fixture reviewer, not an independent production verifier',replacement_validation='This test asserts exact review pin and artifact binding',authorization_source=source or base['authorization_source'],verification_artifacts=[{'ref':'meta/verification.txt','sha256':cr.digest((repo/'meta/verification.txt').read_bytes())}]);rows.append(row)
    write(repo,'meta/review.json',json.dumps({'task_id':TASK,'baseline_pin':baseline['_pin'],'dispositions':rows}))
    # Stage only task files, retaining user.txt as a pre-existing dirty edit.
    run(repo,'git','add','meta','scripts/checker.py')
    if (repo/'tests/test_sample.py').exists():
        run(repo,'git','add','tests/test_sample.py')
    run(repo,'git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','exact fixture review')
    return run(repo,'git','rev-parse','HEAD')


def test_exact_pinned_technical_review_can_resolve_uncertain_protection_change(context):
    repo,_,_=context
    write(repo,'scripts/checker.py','def check():\n    result = True\n    return result\n');run(repo,'git','add','scripts/checker.py')
    blocked=review(context);assert blocked['status']=='FAIL' and blocked['findings']
    assert all(f['severity_kind']=='REVIEW' for f in blocked['findings'])
    revision=pin_review(context,blocked['findings'])
    result=review(context,review_revision=revision,review_ref='meta/review.json');assert_pass(result)
    assert all(f['disposition']=='REVIEWED_NO_WEAKENING' for f in result['findings'])
    write(repo,'scripts/checker.py','def check():\n    return False\n')
    stale=review(context,review_revision=revision,review_ref='meta/review.json')
    assert stale['status']=='FAIL' and stale['errors']


def test_self_signed_disposition_cannot_approve_real_test_deletion(context):
    repo,_,_=context
    write(repo,'tests/test_sample.py',AFTER);run(repo,'git','add','tests/test_sample.py')
    blocked=review(context);assert any(f['severity_kind']=='WEAKENING' for f in blocked['findings'])
    revision=pin_review(context,blocked['findings'])
    result=review(context,review_revision=revision,review_ref='meta/review.json')
    assert result['status']=='FAIL' and any('AUTH' in e or 'authorization' in e for e in result['errors'])


def test_new_production_module_requires_phase_review_even_inside_allowed_paths(context):
    repo,_,_=context;write(repo,'src/anovel/future_feature.py','class FutureBusiness:\n    pass\n')
    result=review(context);assert result['status']=='FAIL'
    assert any(f['code']=='PRODUCTION_SCOPE_REVIEW' for f in result['findings'])


def test_real_cli_saves_failure_and_refuses_overwrite(context):
    repo,_,_=context
    shutil.copytree(ROOT/'plan/scripts',repo/'plan/scripts',ignore=shutil.ignore_patterns('__pycache__'))
    write(repo,'scripts/check_changes.py',(ROOT/'scripts/check_changes.py').read_bytes())
    output=repo/'dist/result.json'
    command=[sys.executable,'-B',str(repo/'scripts/check_changes.py'),'--task',TASK,'--scope-revision',context[1],'--scope-ref',SCOPE,'--output',str(output)]
    result=subprocess.run(command,cwd=repo,capture_output=True,text=True)
    assert result.returncode==2 and json.loads(output.read_text())['status']=='FAIL'
    first=output.read_bytes();again=subprocess.run(command,cwd=repo,capture_output=True,text=True)
    assert again.returncode==2 and output.read_bytes()==first


def test_prior_exact_rule_authorization_allows_real_revision_fixture(tmp_path):
    from weakening_checks import scan_weakening
    sample={'path':'tests/test_sample.py','layer':'worktree','status':'M','old_bytes':BEFORE,'new_bytes':AFTER}
    detected=scan_weakening([sample],task_id=TASK,baseline={'protected_paths':[]})
    grants=[{k:f[k] for k in ['code','path','old_sha','new_sha']} for f in detected]
    context=make_repo(tmp_path/'authorized',grants=grants)
    repo,_,base=context
    write(repo,'tests/test_sample.py',AFTER);run(repo,'git','add','tests/test_sample.py')
    blocked=review(context);assert blocked['status']=='FAIL'
    revision=pin_review(context,blocked['findings'],disposition='AUTHORIZED_EXCEPTION',source=base['exception_authorizations'][0]['authorization_source'])
    approved=review(context,review_revision=revision,review_ref='meta/review.json')
    assert_pass(approved)
    assert any(f['severity_kind']=='WEAKENING' and f['disposition']=='AUTHORIZED_EXCEPTION' for f in approved['findings'])


def test_changed_user_file_mode_is_not_preexisting_exemption(context):
    repo,_,_=context;(repo/'user.txt').chmod(0o755)
    result=review(context)
    assert result['status']=='FAIL' and any(f['path']=='user.txt' for f in result['scope_findings'])


def test_task_entry_blocks_bad_diff_before_child_and_checks_effects_after_child(context,monkeypatch):
    import task_entry
    repo,pin,_=context
    # Only existing declaration validation is isolated; real Git diff and child
    # subprocess execution remain active. Full-context legacy entry tests run too.
    monkeypatch.setattr(task_entry,'__file__',str(repo/'plan/scripts/task_entry.py'))
    monkeypatch.setattr(task_entry,'validate_context',lambda *args:([],{'budget':{'maximum_runtime':30},'change_review':{'scope_revision':pin,'scope_ref':SCOPE}}))
    (repo/'dist').mkdir(exist_ok=True)
    command=[sys.executable,'-c',"from pathlib import Path; Path('dist/child-ran').write_text('yes')"]
    def entry(output,child):
        return task_entry.main(['run','--task',TASK,'--action','IMPLEMENT','--scope-revision',pin,'--scope-ref',SCOPE,'--output',str(repo/'dist'/output),'--',*child])
    assert entry('valid.json',command)==0
    assert (repo/'dist/child-ran').exists()
    (repo/'dist/child-ran').unlink()
    write(repo,'outside.py','unauthorized before command\n')
    assert entry('blocked.json',command)==2
    assert not (repo/'dist/child-ran').exists()
    write(repo,'outside.py','original\n')
    changed=[sys.executable,'-c',"from pathlib import Path; Path('outside.py').write_text('unauthorized effect')"]
    assert entry('effect.json',changed)==2
    report=json.loads((repo/'dist/effect.json').read_text())
    assert report['status']=='FAIL' and report['command_result']['exit_code']==0
    assert any('ENTRY_DIFF_AFTER' in e for e in report['errors'])


def test_restoring_user_dirty_file_to_old_git_blob_is_still_detected(context):
    repo,_,_=context;assert_pass(review(context))
    write(repo,'user.txt','original user\n')
    result=review(context)
    assert result['status']=='FAIL'
    assert any(f['code']=='PRE_EXISTING_CHANGED' and f['path']=='user.txt' for f in result['scope_findings'])


@pytest.mark.parametrize('path,field',[('meta/scope.json','allowed_paths'),('meta/packet.yaml','allowed_paths')])
def test_staged_scope_change_cannot_hide_behind_restored_worktree(context,path,field):
    repo,_,_=context;original=(repo/path).read_bytes()
    data=yaml.safe_load(original);data[field].append('outside.py');write(repo,path,yaml.safe_dump(data))
    run(repo,'git','add',path);write(repo,path,original)
    result=review(context)
    assert result['status']=='FAIL' and any('index' in e for e in result['errors'])


def test_test_rename_to_text_does_not_preserve_discovery(context):
    repo,_,_=context;(repo/'tests/test_sample.py').rename(repo/'tests/test_sample.txt')
    result=review(context)
    assert result['status']=='FAIL' and any(f['code']=='TEST_FILE_REMOVED' for f in result['findings'])


def test_protected_checker_move_requires_review(context):
    repo,_,_=context;(repo/'scripts/checker.py').rename(repo/'allowed/renamed.py')
    result=review(context)
    assert result['status']=='FAIL' and any(f['code']=='PROTECTION_MOVED' for f in result['findings'])


def test_source_in_ignored_bytecode_directory_is_still_reviewed(context):
    repo,_,_=context
    write(repo,'src/anovel/__pycache__/future_business.py','class FutureBusiness:\n    pass\n')
    result=review(context)
    assert result['status']=='FAIL'
    assert any(c['path']=='src/anovel/__pycache__/future_business.py' for c in result['changes'])


def test_test_move_into_hidden_directory_does_not_preserve_discovery(context):
    repo,_,_=context;(repo/'tests/.hidden').mkdir()
    (repo/'tests/test_sample.py').rename(repo/'tests/.hidden/test_sample.py')
    result=review(context)
    assert result['status']=='FAIL' and any(f['code']=='TEST_FILE_REMOVED' for f in result['findings'])


def test_symlink_parent_is_rejected_before_reading_baseline_content(context,tmp_path,monkeypatch):
    repo,_,_=context;outside=tmp_path/'outside-meta';(repo/'meta').rename(outside);(repo/'meta').symlink_to(outside,target_is_directory=True)
    original=Path.read_bytes;seen=[]
    def read(path):
        if path==repo/SCOPE:seen.append(str(path))
        return original(path)
    monkeypatch.setattr(Path,'read_bytes',read)
    result=review(context)
    assert result['status']=='FAIL' and not seen


def test_task_entry_rejects_race_between_validation_and_scope_review(context,monkeypatch):
    import task_entry
    repo,pin,_=context;(repo/'dist').mkdir()
    monkeypatch.setattr(task_entry,'__file__',str(repo/'plan/scripts/task_entry.py'))
    monkeypatch.setattr(task_entry,'validate_context',lambda *args:([],{'budget':{'maximum_runtime':30},'change_review':{'scope_revision':pin,'scope_ref':SCOPE}}))
    original=cr.review_changes
    def raced(*args,**kwargs):
        write(repo,'allowed/existing.py','value=999\n')
        return original(*args,**kwargs)
    monkeypatch.setattr(cr,'review_changes',raced)
    code=task_entry.main(['run','--task',TASK,'--action','IMPLEMENT','--scope-revision',pin,'--scope-ref',SCOPE,'--output',str(repo/'dist/race.json'),'--',sys.executable,'-c',"from pathlib import Path; Path('dist/ran').write_text('yes')"])
    report=json.loads((repo/'dist/race.json').read_text())
    assert code==2 and report['status']=='BLOCKED' and not (repo/'dist/ran').exists()
    assert any('ENTRY_RACE' in e for e in report['errors'])


def test_index_packet_deletion_cannot_hide_behind_present_worktree(context):
    repo,_,_=context
    run(repo,'git','rm','--cached','meta/packet.yaml')
    assert (repo/'meta/packet.yaml').is_file()
    result=review(context)
    assert result['status']=='FAIL' and any('index packet' in e for e in result['errors'])


def test_prior_exact_deletion_grant_accepts_null_new_identity(tmp_path):
    from weakening_checks import scan_weakening
    detected=scan_weakening([{'path':'tests/test_sample.py','layer':'worktree','status':'D','old_bytes':BEFORE,'new_bytes':None}],task_id=TASK,baseline={'protected_paths':[]})
    grants=[{k:f[k] for k in ['code','path','old_sha','new_sha']} for f in detected]
    assert grants and all(g['new_sha'] is None for g in grants)
    context=make_repo(tmp_path/'authorized-delete',grants=grants)
    repo,_,base=context
    (repo/'tests/test_sample.py').unlink();run(repo,'git','add','tests/test_sample.py')
    blocked=review(context);assert blocked['status']=='FAIL' and blocked['findings']
    revision=pin_review(context,blocked['findings'],disposition='AUTHORIZED_EXCEPTION',source=base['exception_authorizations'][0]['authorization_source'])
    assert_pass(review(context,review_revision=revision,review_ref='meta/review.json'))


def test_generic_technical_review_cannot_approve_production_scope(context):
    repo,_,_=context
    write(repo,'src/anovel/future_feature.py','class FutureBusiness:\n    pass\n');run(repo,'git','add','src')
    initial=review(context)
    assert initial['status']=='FAIL'
    assert all(f['severity_kind']=='AUTHORIZATION_REQUIRED' for f in initial['findings'])
    revision=pin_review(context,initial['findings'])
    final=review(context,review_revision=revision,review_ref='meta/review.json')
    assert final['status']=='FAIL' and any('authorization' in e for e in final['errors'])


def test_prior_exact_scope_grant_allows_only_the_pinned_production_bytes(tmp_path):
    content=b'class AuthorizedFixture:\n    pass\n'
    grants=[{'code':'PRODUCTION_SCOPE_REVIEW','path':'src/anovel/future_feature.py','old_sha':None,'new_sha':cr.digest(content)}]
    context=make_repo(tmp_path/'exact-scope',grants=grants,grant_kind='explicit_scope_change_authorization')
    repo,_,base=context
    write(repo,'src/anovel/future_feature.py',content);run(repo,'git','add','src')
    initial=review(context)
    revision=pin_review(context,initial['findings'],disposition='AUTHORIZED_EXCEPTION',source=base['exception_authorizations'][0]['authorization_source'])
    assert_pass(review(context,review_revision=revision,review_ref='meta/review.json'))
    write(repo,'src/anovel/future_feature.py',content+b'other=1\n')
    assert review(context,review_revision=revision,review_ref='meta/review.json')['status']=='FAIL'


@pytest.mark.parametrize('binding,explicit',[('missing',False),('missing',True),('different',True)])
def test_restricted_entry_cannot_omit_or_override_packet_binding(context,monkeypatch,binding,explicit):
    import task_entry
    repo,pin,_=context;(repo/'dist').mkdir()
    packet={'budget':{'maximum_runtime':30}}
    if binding=='different':packet['change_review']={'scope_revision':'f'*40,'scope_ref':SCOPE}
    monkeypatch.setattr(task_entry,'__file__',str(repo/'plan/scripts/task_entry.py'))
    monkeypatch.setattr(task_entry,'validate_context',lambda *args:([],packet))
    argv=['run','--task',TASK,'--action','IMPLEMENT','--output',str(repo/'dist/entry.json')]
    if explicit:argv+=['--scope-revision',pin,'--scope-ref',SCOPE]
    argv+=['--',sys.executable,'-c',"from pathlib import Path; Path('dist/ran').write_text('bad')"]
    assert task_entry.main(argv)==2
    report=json.loads((repo/'dist/entry.json').read_text())
    assert report['status']=='BLOCKED' and not (repo/'dist/ran').exists()
    assert any('ENTRY_DIFF_BINDING' in e for e in report['errors'])


def test_new_conftest_requires_exact_technical_review_but_legal_fixture_can_pass(context):
    repo,_,_=context
    write(repo,'tests/conftest.py','import pytest\n@pytest.fixture\ndef sample():\n    return 1\n');run(repo,'git','add','tests/conftest.py')
    initial=review(context)
    assert initial['status']=='FAIL' and any(f['code']=='TEST_CONFTEST_CHANGED' for f in initial['findings'])
    revision=pin_review(context,initial['findings'])
    assert_pass(review(context,review_revision=revision,review_ref='meta/review.json'))


def test_scope_grant_committed_with_candidate_production_bytes_is_not_prior(tmp_path):
    content=b'class FutureBusiness:\n    pass\n'
    grants=[{'code':'PRODUCTION_SCOPE_REVIEW','path':'src/anovel/future_feature.py','old_sha':None,'new_sha':cr.digest(content)}]
    repo,_,base=make_repo(tmp_path/'late-scope',grants=grants,grant_kind='explicit_scope_change_authorization')
    write(repo,'src/anovel/future_feature.py',content);run(repo,'git','add','src')
    run(repo,'git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','candidate bundled with claimed prior scope')
    context=(repo,run(repo,'git','rev-parse','HEAD'),base)
    result=review(context)
    assert result['status']=='FAIL' and any('pre-change' in error for error in result['errors'])
