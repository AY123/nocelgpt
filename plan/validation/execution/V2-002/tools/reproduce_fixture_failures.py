"""Retrospective reproduction with trusted baseline test code in a disposable copy."""
from pathlib import Path
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / 'plan/validation/execution/V2-002'
revision = '21849ed8919086982dd94d0a4c852db40eca5d40'
results = []
with tempfile.TemporaryDirectory(prefix='v2002-old-fixture-') as name:
    root = Path(name)
    shutil.copytree(ROOT / 'plan', root / 'plan', ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
    for script in ('test_ai_execution.py', 'probe_governance_legacy.py'):
        source = subprocess.check_output(['git', '-C', str(ROOT), 'show', revision+':plan/scripts/'+script])
        (root / 'plan/scripts' / script).write_bytes(source)
    context_path = root / 'plan/validation/execution/V2-002/tools/context.py'
    spec = importlib.util.spec_from_file_location('copied_context', context_path)
    context = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(context)
    context.refresh('old-fixture-reproduction')
    for script, args in [('test_ai_execution.py', ['--output-dir', str(root / 'output/ai')]),
                         ('probe_governance_legacy.py', ['--output', str(root / 'output/legacy.json')])]:
        command = [sys.executable, '-B', str(root / 'plan/scripts' / script), *args]
        result = subprocess.run(command, cwd=root, capture_output=True, text=True)
        row = {'script': script, 'baseline_revision': revision, 'command': command,
               'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        if script.startswith('test_ai'):
            row['failure_observed'] = result.returncode != 0 and 'EXEC_PACKET V2-002' in result.stderr
        else:
            probe = json.loads((root / 'output/legacy.json').read_text())
            control = next(case for case in probe['cases'] if case['id'] == 'CONTROL-VALID')
            row['control'] = control
            row['failure_observed'] = result.returncode != 0 and control['actual'] == 'REJECT'
        results.append(row)
output = BASE / 'raw/fixture-baseline-reproduction.json'
with output.open('x') as stream:
    json.dump({'scope': 'Retrospective isolated failure reproduction, not a production test result', 'results': results}, stream, ensure_ascii=False, indent=2)
assert all(row['failure_observed'] for row in results), results
print(json.dumps([{key: row[key] for key in ('script', 'exit_code', 'failure_observed')} for row in results]))
