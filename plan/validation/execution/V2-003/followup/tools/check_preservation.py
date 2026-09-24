"""Compare real opening content; retain obligations, tests and user inputs."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import argparse, ast, hashlib, json, subprocess, yaml
R = Path(__file__).resolve().parents[6]
BASE = 'a11693ee5ac08fd3aa102e03de0125bd8b800dd9'
p = argparse.ArgumentParser(); p.add_argument('--output', required=True, type=Path); args = p.parse_args()
assert not args.output.exists(), 'refuse overwrite'
def git(*argv): return subprocess.check_output(['git', *argv], cwd=R)
def old(name): return git('show', BASE + ':' + name)
def now(name): return (R / name).read_bytes()
checks = []
def check(label, ok): checks.append({'check': label, 'status': 'PASS' if ok else 'FAIL'})
for name in ['plan/machine/ci-gates.yaml', 'plan/machine/governance-baseline.yaml', 'plan/machine/phase-gates.yaml', 'plan/machine/milestones.yaml', 'plan/machine/authority-policy.yaml', 'plan/schemas/evidence-record.schema.json', 'pyproject.toml', 'uv.lock', '.gitignore', 'tests/contract/test_plan_governance.py']:
    check('byte-identical ' + name, old(name) == now(name))
check('V2-004 pipeline remains absent', git('ls-tree', BASE, '--', '.gitlab-ci.yml') == b'' and not (R / '.gitlab-ci.yml').exists())
for name, key in [('plan/machine/implementation-backlog.yaml', 'tasks'), ('plan/machine/test-catalog.yaml', 'suites')]:
    before, after = yaml.safe_load(old(name)), yaml.safe_load(now(name))
    for value in [before, after]:
        for row in value[key]:
            for metadata in ['status', 'evidence', 'execution_evidence', 'execution_packet_ref']: row.pop(metadata, None)
    check('all task identity/dependency/AC and scenario assertions unchanged ' + name, before == after)
name = 'plan/machine/ai-execution-policy.yaml'
before, after = yaml.safe_load(old(name)), yaml.safe_load(now(name))
for value in [before, after]:
    for row in value['controls']:
        if row['id'] in ['AI-EXEC-02', 'AI-EXEC-03']:
            for field in ['local_status', 'local_scope', 'p0_enforcement_status', 'limitation']: row.pop(field)
check('AI obligations, owners, scenarios unchanged', before == after)
name = 'plan/schemas/execution-packet.schema.json'
before, after = json.loads(old(name)), json.loads(now(name))
check('schema adds only optional typed change_review; existing constraints identical', after['properties'].pop('change_review', None) is not None and before == after)
for name in ['tests/architecture/test_change_review.py', 'tests/architecture/test_dependency_boundaries.py', 'tests/architecture/test_weakening_checks.py', 'tests/contract/test_task_execution.py']:
    def definitions(data): return {n.name:n for n in ast.parse(data).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith('test')}
    def asserts(node): return Counter(ast.dump(n, include_attributes=False) for n in ast.walk(node) if isinstance(n, ast.Assert))
    before, after = definitions(old(name)), definitions(now(name))
    check('existing tests/assertions/decorators retained ' + name, all(k in after and not (asserts(v) - asserts(after[k])) and [ast.dump(x) for x in v.decorator_list] == [ast.dump(x) for x in after[k].decorator_list] for k, v in before.items()))
for name, expected in [('审核报告.txt', '215754d0f0024fcc7fdff9b44959671fd4afd0de2a1b34ff65c213ac16b044f1'), ('V2-003_深度审核报告.md', '8d8f76fb0dc01049195ede16687e3df520a8c8c84bf478dc72867424f729e47e'), ('.claude/settings.local.json', '7ee7703ac2fc9ee9ed1e5498514f53f9e766da6d48f56fc4702c50f9eabbd039')]:
    check('user input exact protected hash ' + name, hashlib.sha256(now(name)).hexdigest() == expected)
untracked_source = git('ls-files', '--others', '--', 'src/anovel').decode().splitlines()
cache_files = [name for name in untracked_source if Path(name).parent.name == '__pycache__' and name.endswith('.pyc')]
check('production source unchanged including ignored additions; only generated pyc cache allowed', git('diff', BASE, '--', 'src/anovel') == b'' and set(untracked_source) == set(cache_files))
check('historical V2-003 evidence retained unchanged', git('diff', BASE, '--', 'plan/validation/execution/V2-003', ':(exclude)plan/validation/execution/V2-003/followup') == b'')
result = {'record_type':'local_preservation_check', 'baseline_revision':BASE, 'head':git('rev-parse', 'HEAD').decode().strip(), 'executed_at':datetime.now(timezone.utc).isoformat(), 'checks':checks, 'generated_bytecode_files':cache_files, 'status':'PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL'}
args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False)); raise SystemExit(0 if result['status']=='PASS' else 2)
