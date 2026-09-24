#!/usr/bin/env python3
"""V2-003 command recorder only; no task selection, authorization or CI claims."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument('name')
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
base = Path(__file__).resolve().parents[1]
out = base/'raw'
out.mkdir(exist_ok=True)
start = datetime.now(timezone.utc).isoformat()
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
worktree = subprocess.check_output(['git', 'status', '--porcelain=v1'], text=True)
target = out/(args.name+'.json')
if target.exists():
    raise SystemExit('Refusing to overwrite a prior command record: '+str(target))
try:
    result = subprocess.run(args.command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    code, stdout, stderr = result.returncode, result.stdout, result.stderr
except OSError as exc:
    code, stdout, stderr = 127, '', str(exc)
record = {'command':args.command, 'cwd':str(Path.cwd()), 'started_at':start,
          'repository_revision':revision, 'worktree_dirty':bool(worktree),
          'finished_at':datetime.now(timezone.utc).isoformat(), 'exit_code':code,
          'stdout':stdout, 'stderr':stderr, 'scope':'local V2-003 execution, not remote CI'}
target.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(stdout, end='')
print(stderr, end='', file=sys.stderr)
print('\nRECORD '+str(target)+' EXIT '+str(code), file=sys.stderr)
raise SystemExit(code)
