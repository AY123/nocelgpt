#!/usr/bin/env python3
"""Validate planning data; never runs V2, CI, PostgreSQL or a model provider.

--write-views regenerates read-only views and the content manifest.
--check verifies them without repairing inconsistencies.
--self-test checks the validator against deliberately invalid in-memory plans.
Results default to plan/validation/; --output-dir separates CI artifacts from
versioned planning inputs. Requires PyYAML and jsonschema.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
import subprocess
from urllib.parse import urlparse, unquote

import yaml
from jsonschema import Draft202012Validator

PLAN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from governance_checks import object_checks, evidence_checks
from execution_checks import execution_checks

APPROVED_GOVERNANCE_BASELINE = "ab7a40f13686601f34a339c04005efd5a8d65e92e3d561ab94bc6f2b8898e68c"
NAMES = ['implementation-backlog', 'phase-gates', 'milestones', 'test-catalog',
         'decision-register', 'remediation-register', 'authority-policy', 'ci-gates', 'source-register',
         'external-practice-register', 'governance-baseline', 'foundational-reference-register',
         'ai-execution-policy']
EVIDENCE = {'E0': 'deterministic_check', 'E1': 'structured_extraction',
            'E2': 'model_evaluation_including_simulated_reader', 'E3': 'human_gold_blind_review',
            'E4': 'real_reader_market_observation'}
PHASE_NAMES = ['Repository & Governance', 'Narrative Kernel', 'Canon Kernel', 'Genre Kernel',
               'Planning & Contracts', 'Context & Model Gateway', 'Single-Chapter Production',
               'Quality & Repair', 'Dual-Genre 10-Chapter Certification', '30-Chapter Certification',
               'Genesis & Reference Intelligence', 'Human Calibration / Learning', '100-Chapter Reliability',
               'Reader / Market Feedback', '300+ Chapter / Million-word Evolution']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load():
    data = {n: yaml.safe_load((PLAN / 'machine' / (n + '.yaml')).read_text()) for n in NAMES}
    data['task_schema'] = json.loads((PLAN / 'schemas/implementation-task.schema.json').read_text())
    data['frozen_backlog'] = yaml.safe_load((PLAN / 'archive/gptdoc/ANovel_V2_Implementation_Plan_v1.0/implementation-backlog.yaml').read_text())
    return data


def validate_objects(data):
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)
    tasks = data['implementation-backlog']['tasks']
    by = {t['task_id']: t for t in tasks}
    phases = data['phase-gates']['phases']
    phase_by = {p['id']: p for p in phases}
    suites = data['test-catalog']['suites']
    suite_by = {s['id']: s for s in suites}
    decisions = data['decision-register']['decisions']
    decision_by = {a['id']: a for a in decisions}
    findings = data['remediation-register']['findings']
    finding_by = {r['id']: r for r in findings}
    check(len(tasks) == len(by) == 60, 'TASK_COUNT: exactly 60 unique frozen task IDs required')
    frozen = {t['task_id']: t for t in data['frozen_backlog']['tasks']}
    check(set(by) == set(frozen), 'TASK_IDENTITIES: frozen task IDs changed')
    check([p['id'] for p in phases] == [f'P{i}' for i in range(15)], 'PHASE_ORDER: expected P0 through P14')
    check([p['name'] for p in phases] == PHASE_NAMES, 'PHASE_NAMES: frozen route name drift')
    check(len(suites) == len(suite_by), 'TEST_IDS: duplicate suite IDs')
    check(len(decisions) == len(decision_by), 'ADR_IDS: duplicate ADR IDs')
    check(len(findings) == len(finding_by), 'FINDING_IDS: duplicate finding IDs')
    check(data['authority-policy']['evidence_levels'] == EVIDENCE, 'EVIDENCE_SEMANTICS: EVIDENCE-1 drift')
    check(data['authority-policy']['sole_writers'] == {
        'canon_head': 'CanonCommitService', 'production_state': 'WorkflowStateService',
        'commit_permit': 'ProtectedPermitIssuer'}, 'AUTHORITY: sole writer drift')
    check(data['authority-policy']['anchor_genres'] == ['urban.business.realistic', 'fantasy.eastern.progression'], 'ANCHORS: frozen anchor drift')
    check(data['authority-policy']['automatic_publication'] is False, 'SCOPE: automatic publication outside initial scope')
    try:
        Draft202012Validator.check_schema(data['task_schema'])
    except Exception as exc:
        errors.append('TASK_SCHEMA: ' + str(exc))
    validator = Draft202012Validator(data['task_schema'])
    active = {'IN_PROGRESS', 'IMPLEMENTED', 'VERIFIED', 'CLOSED'}
    complete = {'VERIFIED', 'CLOSED'}
    for task in tasks:
        tid = task['task_id']
        for e in validator.iter_errors(task):
            errors.append(f'TASK_SCHEMA {tid} {list(e.path)}: {e.message}')
        old = frozen.get(tid, {})
        check(task['title'] == old.get('title'), f'TASK_TITLE {tid}: mismatch with frozen identity')
        check(task['phase'] == old.get('phase'), f'TASK_PHASE {tid}: mismatch with frozen phase')
        check(task['dependencies'] == old.get('dependencies'), f'TASK_DEP_BASELINE {tid}: dependency change needs explicit baseline revision')
        check(all(not ref.startswith('archive/') for ref in task['normative_specs']), f'TASK_NORMATIVE {tid}: archive cannot be normative')
        p = phase_by.get(task['phase'])
        check(p is not None, f'TASK_PHASE {tid}: phase missing')
        if p:
            check(task['start_gate'] == p['entry_gate'], f'TASK_ENTRY {tid}: phase gate mismatch')
        for dep in task['dependencies']:
            check(dep in by, f'TASK_DEP {tid}: unknown {dep}')
            check(dep != tid, f'TASK_DEP {tid}: self dependency')
            if task['status'] in active and dep in by:
                check(by[dep]['status'] in complete, f'TASK_START {tid}: dependency {dep} not verified')
        if task['status'] in active and task['phase'] != 'P0':
            prev = next((p for p in phases if p['exit_gate'] == task['start_gate']), None)
            check(prev and prev['status'] == 'VERIFIED', f'TASK_START {tid}: phase entry not verified')
        for ref in task['tests']:
            check(ref in suite_by, f'TASK_TEST {tid}: unknown {ref}')
            if ref in suite_by:
                check(suite_by[ref]['task_id'] == tid, f'TASK_TEST {tid}: wrong owner {ref}')
                if task['status'] in complete:
                    check(suite_by[ref]['status'] == 'VERIFIED', f'TASK_TEST {tid}: planned suite cannot close task')
        assertions = {c['required_assertion'] for ref in task['tests'] if ref in suite_by
                      for c in suite_by[ref]['scenarios']}
        check(set(task['acceptance_criteria']) == assertions, f'TASK_ACCEPTANCE {tid}: task and scenario assertions differ')
        for ref in task['required_decisions']:
            check(ref in decision_by, f'TASK_ADR {tid}: unknown {ref}')
            if ref in decision_by:
                check(tid in decision_by[ref]['related_tasks'], f'TASK_ADR {tid}: ownership mismatch')
                if task['status'] in {'IMPLEMENTED', 'VERIFIED', 'CLOSED'}:
                    check(decision_by[ref]['status'] == 'ACCEPTED', f'TASK_ADR {tid}: unresolved {ref}')
        for ref in task['related_findings']:
            check(ref in finding_by and tid in finding_by[ref]['related_tasks'], f'TASK_FINDING {tid}: invalid {ref}')
        if task['status'] in complete:
            records = [r for records in task['evidence'].values() for r in records]
            check(len({r.get('revision') for r in records}) == 1, f'TASK_EVIDENCE {tid}: mixed revisions')

    colors = {}
    def visit(tid):
        if colors.get(tid) == 1:
            errors.append(f'TASK_CYCLE: {tid}')
            return
        if colors.get(tid) == 2 or tid not in by:
            return
        colors[tid] = 1
        for dep in by[tid]['dependencies']:
            visit(dep)
        colors[tid] = 2
    for tid in by:
        visit(tid)

    for index, p in enumerate(phases):
        check(p['status'] in {'NOT_VERIFIED','VERIFIED'}, f'PHASE_STATUS {p["id"]}: unsupported status')
        check(p['entry_gate'] == ('P0_ENTRY_READY' if index == 0 else f'G-P{index-1}'), f'PHASE_ENTRY {p["id"]}: invalid predecessor')
        check(p['exit_gate'] == 'G-' + p['id'], f'PHASE_EXIT {p["id"]}: invalid gate ID')
        check(p['tasks'] == [t['task_id'] for t in tasks if t['phase'] == p['id']], f'PHASE_MEMBERSHIP {p["id"]}: tasks/count mismatch')
        check(bool(p['exit_criteria']), f'PHASE_CRITERIA {p["id"]}: empty')
        if p['status'] == 'VERIFIED':
            check(bool(p['tasks']), f'PHASE_VERIFIED {p["id"]}: unrefined future phase')
            check(bool(p['evidence_refs']), f'PHASE_VERIFIED {p["id"]}: missing evidence')
            check(all(by.get(t, {}).get('status') == 'CLOSED' for t in p['tasks']), f'PHASE_VERIFIED {p["id"]}: tasks must be CLOSED')
            if index:
                check(phases[index-1]['status'] == 'VERIFIED', f'PHASE_VERIFIED {p["id"]}: previous phase unverified')
    for tid in data['phase-gates']['critical_path']:
        check(tid in by, f'CRITICAL_PATH: unknown {tid}')

    scenario_ids = []
    for suite in suites:
        check(suite['status'] in {'PLANNED','IMPLEMENTED','VERIFIED'}, f'SUITE_STATUS {suite["id"]}: unsupported status')
        check(suite['task_id'] in by, f'SUITE_OWNER {suite["id"]}: unknown task')
        if suite['task_id'] in by:
            check(suite['phase'] == by[suite['task_id']]['phase'], f'SUITE_PHASE {suite["id"]}: mismatch')
        check(bool(suite['scenarios']), f'SUITE_CASES {suite["id"]}: empty')
        for case in suite['scenarios']:
            scenario_ids.append(case['id'])
            check(bool(case['required_assertion'].strip()), f'SCENARIO {case["id"]}: empty assertion')
        if suite['status'] == 'VERIFIED':
            check(bool(suite['execution_evidence']), f'SUITE_EVIDENCE {suite["id"]}: missing')
    check(len(scenario_ids) == len(set(scenario_ids)), 'SCENARIO_IDS: duplicate case IDs')

    external = data['external-practice-register']
    sources = external['sources']
    source_by = {s['id']: s for s in sources}
    practices = external['practices']
    practice_by = {p['id']: p for p in practices}
    scenario_by = {c['id']: s for s in suites for c in s['scenarios']}
    check(len(sources) == len(source_by), 'EXTERNAL_SOURCE_IDS: duplicate source')
    check(len(practices) == len(practice_by), 'EXTERNAL_PRACTICE_IDS: duplicate practice')
    for source in sources:
        sid = source['id']
        url = urlparse(source.get('url', ''))
        check(url.scheme == 'https' and bool(url.netloc), f'EXTERNAL_SOURCE_URL {sid}: invalid URL')
        check(source.get('source_kind') in {'OFFICIAL_REPOSITORY', 'PUBLIC_ISSUE_REPORT', 'OFFICIAL_PRODUCT_DOCUMENTATION'}, f'EXTERNAL_SOURCE_KIND {sid}: invalid')
        check(bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(source.get('reviewed_on', '')))), f'EXTERNAL_SOURCE_DATE {sid}: absent')
        check(source.get('review_level') == 'PUBLIC_DOCUMENT_REVIEW', f'EXTERNAL_SOURCE_LEVEL {sid}: document registry cannot certify runtime')
        check(source.get('code_review') == source.get('runtime_verification') == 'NOT_PERFORMED', f'EXTERNAL_SOURCE_EVIDENCE {sid}: source audit requires separate evidence registry')
        check(bool(source.get('observation')) and bool(source.get('limitation')), f'EXTERNAL_SOURCE_LIMIT {sid}: absent observation/limitation')
    for practice in practices:
        pid = practice['id']
        check(practice['decision'] in {'REFINE_EXISTING','ADD_TRACEABILITY','DEFER','REJECT'}, f'EXTERNAL_DECISION {pid}: invalid')
        check(practice['status'] in {'PLANNED','VERIFIED','DEFERRED','REJECTED'}, f'EXTERNAL_STATUS {pid}: invalid')
        refs = practice['source_refs']
        check(bool(refs) and len(refs) == len(set(refs)) and all(r in source_by for r in refs), f'EXTERNAL_SOURCE_REF {pid}: missing/unknown/duplicate')
        for key in ('baseline_coverage', 'local_adaptation', 'expected_benefit', 'normative_refs'):
            check(bool(practice.get(key)), f'EXTERNAL_MEANING {pid}: absent {key}')
        owners = practice['related_tasks']
        cases = practice['acceptance_scenarios']
        check(len(owners) == len(set(owners)), f'EXTERNAL_TASKS {pid}: duplicate owner')
        check(len(cases) == len(set(cases)), f'EXTERNAL_CASES {pid}: duplicate scenario')
        deferred = practice['decision'] in {'DEFER','REJECT'}
        if deferred:
            check(practice['status'] == ('DEFERRED' if practice['decision'] == 'DEFER' else 'REJECTED'), f'EXTERNAL_DEFER_STATUS {pid}: invalid')
            check(not owners and not cases and not practice['verification_refs'], f'EXTERNAL_DEFER_SCOPE {pid}: unapproved task/evidence')
            phase = practice.get('earliest_reconsider_phase')
            if practice['decision'] == 'DEFER':
                check(phase in phase_by and int(phase[1:]) >= 10, f'EXTERNAL_DEFER_PHASE {pid}: advanced work moved early')
        else:
            check(practice['status'] in {'PLANNED','VERIFIED'}, f'EXTERNAL_ADOPT_STATUS {pid}: invalid')
            check(bool(owners) and bool(cases), f'EXTERNAL_MAPPING {pid}: empty')
            check(all(t in by for t in owners), f'EXTERNAL_TASKS {pid}: unknown owner')
            check(all(c in scenario_by for c in cases), f'EXTERNAL_CASES {pid}: unknown scenario')
            case_owners = {scenario_by[c]['task_id'] for c in cases if c in scenario_by}
            check(case_owners == set(owners), f'EXTERNAL_CASE_OWNER {pid}: scenario owners differ')
            for tid in owners:
                if tid in by:
                    check(pid in by[tid].get('external_practices', []), f'EXTERNAL_BACKLINK {pid}: absent on {tid}')
                    check(set(practice['normative_refs']).issubset(by[tid]['normative_specs']), f'EXTERNAL_NORMATIVE {pid}: task {tid} omits specification')
            if practice['status'] == 'VERIFIED':
                check(bool(practice['verification_refs']), f'EXTERNAL_VERIFIED {pid}: absent evidence')
                check(all(by.get(t, {}).get('status') in complete for t in owners), f'EXTERNAL_VERIFIED {pid}: unfinished tasks')
                check(all(scenario_by.get(c, {}).get('status') == 'VERIFIED' for c in cases), f'EXTERNAL_VERIFIED {pid}: unverified suites')
    for task in tasks:
        for pid in task.get('external_practices', []):
            check(pid in practice_by and task['task_id'] in practice_by[pid]['related_tasks'], f'EXTERNAL_TASK_REF {task["task_id"]}: unknown/wrong practice {pid}')

    for adr in decisions:
        check(adr['status'] in {'REQUIRED','ACCEPTED','SUPERSEDED'}, f'ADR_STATUS {adr["id"]}: unsupported status')
        check(adr['decision_due_task'] in adr['related_tasks'], f'ADR_DUE {adr["id"]}: no responsible task')
        check(all(t in by for t in adr['related_tasks']), f'ADR_OWNER {adr["id"]}: unknown task')
        if adr['status'] == 'ACCEPTED':
            check(bool(adr['decision_record']), f'ADR_RECORD {adr["id"]}: absent decision')
    for finding in findings:
        check(finding['status'] in {'OPEN_TRACKED','IN_PROGRESS','VERIFIED','CLOSED'}, f'FINDING_STATUS {finding["id"]}: unsupported status')
        check(bool(finding['related_tasks']) and all(t in by for t in finding['related_tasks']), f'FINDING_OWNER {finding["id"]}: invalid')
        check(bool(finding['acceptance_evidence']), f'FINDING_CRITERIA {finding["id"]}: absent')
        if finding['status'] in {'VERIFIED', 'CLOSED'}:
            check(bool(finding['closure_refs']), f'FINDING_CLOSURE {finding["id"]}: absent evidence')
    expected_findings = {f'AR-{i:02d}' for i in range(1,21)} | {f'CA-{i:02d}' for i in range(1,25)} | {f'RR-{i:02d}' for i in range(1,13)} | {f'SUP-{i:02d}' for i in range(1,9)}
    expected_findings |= {f'DA-{i:02d}' for i in range(1,12)} | {'PR-01'}
    check(set(finding_by) == expected_findings, 'FINDING_COVERAGE: missing/extra audit mappings')

    milestones = data['milestones']['milestones']
    check([m['id'] for m in milestones] == [f'M{i}' for i in range(13)], 'MILESTONES: IDs drift')
    for m in milestones:
        check(m['status'] in {'NOT_VERIFIED','VERIFIED'}, f'MILESTONE_STATUS {m["id"]}: unsupported status')
        check(m['introduced_phase'] in phase_by and m['earliest_close_phase'] in phase_by, f'MILESTONE_PHASE {m["id"]}: unknown')
        for tid in m['required_tasks']:
            check(tid in by, f'MILESTONE_TASK {m["id"]}: unknown {tid}')
            if tid in by:
                check(int(by[tid]['phase'][1:]) <= int(m['earliest_close_phase'][1:]), f'MILESTONE_CLOSE {m["id"]}: closes before required task')
        if m['status'] == 'VERIFIED':
            check(bool(m['required_tasks']) and bool(m['evidence_refs']), f'MILESTONE_VERIFIED {m["id"]}: missing scope/evidence')
            check(all(by.get(t, {}).get('status') in complete for t in m['required_tasks']), f'MILESTONE_VERIFIED {m["id"]}: unfinished tasks')
    m4 = next((m for m in milestones if m['id'] == 'M4'), {})
    check(m4.get('earliest_close_phase') == 'P7' and 'V2-026' in m4.get('required_tasks', []), 'M4_GATE: requires real Q0-Q3 permit integration')
    for gate in data['ci-gates']['gates']:
        check(gate['allow_failure'] is False, f'CI_HARD_GATE {gate["id"]}: allow_failure must be false when applicable')
        check(gate['activation_phase'] in phase_by, f'CI_PHASE {gate["id"]}: unknown phase')
    errors += object_checks(data)
    controls = data['ai-execution-policy']['controls']
    check(len(controls) == 6 and {c['id'] for c in controls} == {f'AI-EXEC-{i:02d}' for i in range(1, 7)},
          'AI_EXEC_POLICY: six execution controls required')
    for control in controls:
        owners = control['owner_tasks']
        cases = control['acceptance_scenarios']
        check(bool(owners) and all(t in by for t in owners), f'AI_EXEC_OWNER {control["id"]}: missing task')
        check(bool(cases) and all(c in scenario_by for c in cases), f'AI_EXEC_SCENARIO {control["id"]}: missing scenario')
        check({scenario_by[c]['task_id'] for c in cases if c in scenario_by} == set(owners),
              f'AI_EXEC_OWNER {control["id"]}: scenario owners differ')
        check(control['local_status'] in {'PLANNED', 'IMPLEMENTED_LOCAL'},
              f'AI_EXEC_STATUS {control["id"]}: unsupported local claim')
        status = control['p0_enforcement_status']
        check(status in {'NOT_IMPLEMENTED', 'IMPLEMENTED', 'VERIFIED'},
              f'AI_EXEC_STATUS {control["id"]}: unsupported engineering state')
        if status != 'NOT_IMPLEMENTED':
            eligible = {'VERIFIED', 'CLOSED'} if status == 'VERIFIED' else {'IMPLEMENTED', 'VERIFIED', 'CLOSED'}
            check(bool(owners) and all(by.get(t, {}).get('status') in eligible for t in owners),
                  f'AI_EXEC_STATUS {control["id"]}: owners have not reached the claimed state')
    return errors


def expected_views(data):
    tasks = data['implementation-backlog']['tasks']
    lines = ['# 阶段与任务注册表（自动生成）', '', '唯一源：`machine/implementation-backlog.yaml` 与 `machine/phase-gates.yaml`。不要手工修改。', '', f'共 {len(tasks)} 个任务。当前任务状态：' + json.dumps(dict(Counter(t['status'] for t in tasks)), ensure_ascii=False), '']
    for phase in data['phase-gates']['phases']:
        group = [t for t in tasks if t['phase'] == phase['id']]
        lines += [f'## {phase["id"]} — {phase["name"]}', '', f'准入：{phase["entry_gate"]}；退出：{phase["exit_gate"]}；任务数：{len(group)}。', '', '| ID | 名称 | 依赖 | 状态 |', '|---|---|---|---|']
        lines += [f'| {t["task_id"]} | {t["title"]} | {", ".join(t["dependencies"]) or "无任务依赖，仍须阶段门禁"} | {t["status"]} |' for t in group]
        if not group:
            lines += ['本阶段任务将在对应阶段前细化，当前不宣称可直接执行。']
        lines += ['']
    ms = ['# 里程碑映射（自动生成）', '', '唯一源：`machine/milestones.yaml`。编号采用冻结实施计划；M4 关闭时点按真实集成纠正。', '', '| ID | 名称 | 引入阶段 | 最早关闭阶段 | 状态 |', '|---|---|---|---|---|']
    for m in data['milestones']['milestones']:
        ms.append(f'| {m["id"]} | {m["name"]} | {m["introduced_phase"]} | {m["earliest_close_phase"]} | {m["status"]} |')
    ext = ['# 外部经验与任务映射（自动生成）', '',
           '唯一源：`machine/external-practice-register.yaml`。PLANNED 是采纳计划；不是上游或本项目运行认证。', '',
           '| ID | 本地改进 | 处理 | 状态 | 关联任务 | 计划验收 |', '|---|---|---|---|---|---|']
    for p in data['external-practice-register']['practices']:
        ext.append(f'| {p["id"]} | {p["title"]} | {p["decision"]} | {p["status"]} | {", ".join(p["related_tasks"]) or "未安排"} | {", ".join(p["acceptance_scenarios"]) or "无早期实施要求"} |')
    ext += ['', '来源均为公开资料查阅，未完成源码审计或运行验证；不可变上游版本按实际复用需要在实施时补齐。', '', '| 来源 ID | 原始页面 |', '|---|---|']
    ext += [f'| {s["id"]} | [{s["name"]}]({s["url"]}) |' for s in data['external-practice-register']['sources']]
    return {'generated/PHASE_TASK_REGISTRY.md':'\n'.join(lines)+'\n', 'generated/MILESTONE_MAP.md':'\n'.join(ms)+'\n',
            'generated/EXTERNAL_PRACTICE_MAP.md':'\n'.join(ext)+'\n'}


def manifest_files():
    return sorted(p for p in PLAN.rglob('*') if p.is_file() and p.name != '.DS_Store'
                  and p.name != 'FILE_MANIFEST.json' and 'validation' not in p.relative_to(PLAN).parts
                  and '__pycache__' not in p.parts)


def build_manifest():
    return [{'path':str(p.relative_to(PLAN)), 'bytes':p.stat().st_size, 'sha256':sha(p)} for p in manifest_files()]


def check_files(data, views):
    errors = []
    for name, expected in views.items():
        p = PLAN/name
        if not p.exists() or p.read_text() != expected:
            errors.append(f'GENERATED_VIEW: stale or missing {name}')
    paths = list(data['phase-gates']['entry_gate'].get('evidence', []))
    baseline = PLAN/'machine/governance-baseline.yaml'
    if not baseline.is_file() or sha(baseline) != APPROVED_GOVERNANCE_BASELINE:
        errors.append('GOVERNANCE_BASELINE: change needs explicit baseline revision')
    errors += evidence_checks(data, PLAN)
    errors += execution_checks(data, PLAN)
    paths.append(data['ai-execution-policy']['source_normative'])
    for task in data['implementation-backlog']['tasks']:
        paths += task['normative_specs']
        paths += task['design_references']
        paths += [r['ref'] for records in task['evidence'].values() for r in records]
    for d in data['decision-register']['decisions']:
        if d['decision_record']:
            paths.append(d['decision_record'])
    for r in data['remediation-register']['findings']:
        paths += [r['source']] + r['closure_refs']
    for p in data['external-practice-register']['practices']:
        paths += p['normative_refs'] + p['verification_refs']
    for f in data['foundational-reference-register']['references']:
        paths += [f['source_ref'], f['study_ref']] + f['normative_refs']
    for source in data['source-register']['files']:
        p = (PLAN/source['archive_path']).resolve()
        if (PLAN/'archive').resolve() not in p.parents or not p.is_file() or sha(p) != source['sha256']:
            errors.append(f'SOURCE_SNAPSHOT: mismatch {source["archive_path"]}')
    registered = [s['archive_path'] for s in data['source-register']['files']]
    archived = [str(p.relative_to(PLAN)) for p in (PLAN/'archive').rglob('*') if p.is_file() and p != PLAN/'archive/README.md' and p.name != '.DS_Store']
    if len(registered) != len(set(registered)) or set(registered) != set(archived):
        errors.append('SOURCE_INVENTORY: duplicate/missing snapshot registration')
    for ref in paths:
        if urlparse(ref).scheme in {'https', 'http'}:
            continue  # Presence only; does not assert remote CI or acceptance result.
        p = (PLAN/ref).resolve()
        if PLAN.resolve() not in p.parents or not p.is_file():
            errors.append(f'LOCAL_REF: absent/outside package {ref}')
    for p in PLAN.rglob('*.md'):
        if 'archive' in p.relative_to(PLAN).parts:
            continue
        for dest in re.findall(r'\]\(([^)]+)\)', p.read_text()):
            if dest.startswith('#') or urlparse(dest).scheme:
                continue
            target = p.parent/unquote(dest.split('#')[0])
            if not target.exists():
                errors.append(f'MARKDOWN_LINK: {p.relative_to(PLAN)} -> {dest}')
    manifest = PLAN/'FILE_MANIFEST.json'
    if not manifest.is_file() or json.loads(manifest.read_text()) != build_manifest():
        errors.append('MANIFEST: missing/stale file manifest; explicit --write-views required for intentional changes')
    return errors


def self_test(data):
    def task(d, i=0): return d['implementation-backlog']['tasks'][i]
    mutations = [
        ('wrong phase', lambda d: task(d,4).update(phase='P3')),
        ('wrong title', lambda d: task(d).update(title='Unregistered identity')),
        ('empty CLOSED evidence', lambda d: task(d).update(status='CLOSED')),
        ('premature P1 start', lambda d: task(d,4).update(status='IN_PROGRESS')),
        ('task dependency cycle', lambda d: task(d).update(dependencies=['V2-005'])),
        ('unknown dependency', lambda d: task(d).update(dependencies=['V2-999'])),
        ('empty acceptance criteria', lambda d: task(d).update(acceptance_criteria=[])),
        ('missing test suite', lambda d: task(d).update(tests=['MISSING-SUITE'])),
        ('wrong ADR owner', lambda d: d['decision-register']['decisions'][0].update(related_tasks=['V2-999'])),
        ('simulated reader mislabeled human', lambda d: d['authority-policy']['evidence_levels'].update(E3='simulated_reader')),
        ('softened hard CI', lambda d: d['ci-gates']['gates'][0].update(allow_failure=True)),
        ('premature M4 closure phase', lambda d: d['milestones']['milestones'][4].update(earliest_close_phase='P6')),
        ('false verified phase', lambda d: d['phase-gates']['phases'][0].update(status='VERIFIED')),
        ('wrong phase task count', lambda d: d['phase-gates']['phases'][6].update(tasks=[])),
        ('wrong phase name', lambda d: d['phase-gates']['phases'][1].update(name='Genre Foundation')),
        ('archive treated as normative', lambda d: task(d).update(normative_specs=['archive/README.md'])),
        ('closed finding without evidence', lambda d: d['remediation-register']['findings'][0].update(status='CLOSED')),
        ('scenario assertion removed', lambda d: d['test-catalog']['suites'][0]['scenarios'][0].update(required_assertion='')),
        ('missing audit mapping', lambda d: d['remediation-register']['findings'].pop()),
        ('acceptance and scenario drift', lambda d: task(d)['acceptance_criteria'].append('Unmapped criterion')),
        ('unknown external source', lambda d: d['external-practice-register']['practices'][0].update(source_refs=['MISSING'])),
        ('duplicate external source', lambda d: d['external-practice-register']['sources'].append(deepcopy(d['external-practice-register']['sources'][0]))),
        ('duplicate external practice', lambda d: d['external-practice-register']['practices'].append(deepcopy(d['external-practice-register']['practices'][0]))),
        ('missing external task backlink', lambda d: task(d,12).update(external_practices=['EXT-009'])),
        ('wrong external scenario owner', lambda d: d['external-practice-register']['practices'][0].update(acceptance_scenarios=['AT-V2-001-01'])),
        ('missing external scenario', lambda d: d['external-practice-register']['practices'][0].update(acceptance_scenarios=['MISSING'])),
        ('false verified adoption', lambda d: d['external-practice-register']['practices'][0].update(status='VERIFIED')),
        ('deferred work attached to early task', lambda d: d['external-practice-register']['practices'][9].update(related_tasks=['V2-001'])),
        ('deferred work moved to P0', lambda d: d['external-practice-register']['practices'][9].update(earliest_reconsider_phase='P0')),
        ('public document mislabeled runtime verified', lambda d: d['external-practice-register']['sources'][0].update(runtime_verification='VERIFIED')),
        ('unknown task practice', lambda d: task(d).update(external_practices=['EXT-999'])),
    ]
    results = [{'case':'valid current package objects','expected':'ACCEPT','actual':'ACCEPT' if not validate_objects(data) else 'REJECT'}]
    for name, mutate in mutations:
        bad = deepcopy(data)
        mutate(bad)
        errors = validate_objects(bad)
        results.append({'case':name,'expected':'REJECT','actual':'REJECT' if errors else 'ACCEPT','evidence':errors[:2]})
    return results


def repository_identity():
    try:
        revision = subprocess.run(['git','-C',str(PLAN.parent),'rev-parse','HEAD'], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(['git','-C',str(PLAN.parent),'status','--porcelain'], capture_output=True, text=True, check=True).stdout
        return {'validated_repository_revision':revision, 'validated_worktree_dirty':bool(dirty),
                'validation_input_kind':'WORKTREE_SNAPSHOT', 'input_identity_note':'manifest SHA identifies actual plan bytes; HEAD is checkout context, not proof all inputs were committed'}
    except (OSError, subprocess.CalledProcessError):
        return {'validated_repository_revision':None,'validated_worktree_dirty':None,'validation_input_kind':'EXPORTED_PACKAGE'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true')
    mode.add_argument('--write-views',action='store_true')
    mode.add_argument('--self-test',action='store_true')
    parser.add_argument('--output-dir', type=Path, default=PLAN/'validation',
                        help='Directory for generated validation reports, not source views')
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        data = load()
        errors = validate_objects(data)
        views = expected_views(data)
        if args.write_views and not errors and not evidence_checks(data, PLAN):
            for name, value in views.items():
                (PLAN/name).write_text(value)
            (PLAN/'FILE_MANIFEST.json').write_text(json.dumps(build_manifest(),ensure_ascii=False,indent=2)+'\n')
        if args.self_test:
            cases = self_test(data)
            report = {'scope':'planning validator self-test only',
                      'generated_at_utc':datetime.now(timezone.utc).isoformat(),
                      'manifest_sha256':sha(PLAN/'FILE_MANIFEST.json') if (PLAN/'FILE_MANIFEST.json').exists() else None,
                      'status':'PASS' if all(r['expected']==r['actual'] for r in cases) else 'FAIL','cases':cases}
            (output_dir/'validator-self-test.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps({'scope':report['scope'],'status':report['status'],'cases':len(cases)},ensure_ascii=False))
            return 0 if report['status']=='PASS' else 1
        output = output_dir/'plan-validation.json'
        if not output.exists():
            output.write_text(json.dumps({'scope':'planning validation','status':'IN_PROGRESS'})+'\n')
        errors += check_files(data, views)
        tasks = data['implementation-backlog']['tasks']
        report = {'generated_at_utc':datetime.now(timezone.utc).isoformat(),
                  'scope':'planning structure, IDs, graph, ownership, evidence fields, snapshots, links, external practice traceability and generated views',
                  'status':'PASS' if not errors else 'FAIL',
                  'not_certified':['P0 engineering exit','runtime','PostgreSQL','remote CI','live provider','reader/market result'],
                  'source_snapshot_baseline_commit':data['source-register']['source_snapshot_baseline_commit'],
                  **repository_identity(),
                  'manifest_sha256':sha(PLAN/'FILE_MANIFEST.json') if (PLAN/'FILE_MANIFEST.json').exists() else None,
                  'counts':{'tasks':len(tasks),'phase_distribution':dict(Counter(t['phase'] for t in tasks)),
                            'statuses':dict(Counter(t['status'] for t in tasks)),
                            'suites':len(data['test-catalog']['suites']),
                            'scenarios':sum(len(s['scenarios']) for s in data['test-catalog']['suites']),
                            'decisions':len(data['decision-register']['decisions']),
                            'findings':len(data['remediation-register']['findings']),
                            'source_snapshots':len(data['source-register']['files']),
                            'external_sources':len(data['external-practice-register']['sources']),
                            'external_practices':dict(Counter(p['status'] for p in data['external-practice-register']['practices']))},
                  'errors':errors}
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 1 if errors else 0
    except Exception as exc:
        report={'scope':'planning validation','status':'FAIL','errors':[f'{type(exc).__name__}: {exc}']}
        (output_dir/'plan-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 1


if __name__ == '__main__':
    sys.exit(main())
