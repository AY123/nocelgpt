#!/usr/bin/env python3
"""Run existing normative checks as one engineering command; never certify CI."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plan/scripts'))
import validate_plan as validator
from task_entry import safe_output


def context_inventory(root):
    """Inspect actual repository context entry/config files, never load archive.

    Context documents may explain historical references. Automatic load/include
    directives and config references are reviewed separately from ordinary prose.
    Unknown config keys are reported for explicit review, not called verified.
    """
    rows, errors = [], []
    for name in ('README.md', 'AGENTS.md', 'CLAUDE.md', '.claude/CLAUDE.md',
                 '.claude/settings.json', '.claude/settings.local.json', '.codex/config.toml'):
        path = root / name
        if not path.exists():
            rows.append({'path': name, 'exists': False})
            continue
        content = path.read_text()
        row = {'path': name, 'exists': True, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        if name in {'README.md', 'AGENTS.md'} and 'plan/README.md' not in content:
            errors.append('CONTEXT_ENTRY: missing current plan link in ' + name)
        if name.endswith('.json'):
            config = json.loads(content)
            row['top_level_keys'] = sorted(config)
            row['automatic_context_configuration'] = {key: value for key, value in config.items() if key != 'permissions'}
            # A permission string allows a command; it does not load context.
            automatic = json.dumps(row['automatic_context_configuration']).lower()
            if 'archive' in automatic or 'convergence' in automatic:
                errors.append('CONTEXT_ARCHIVE: automatic configuration requires explicit reconciliation: ' + name)
        elif name.endswith('.toml'):
            import tomllib
            config = tomllib.loads(content)
            row['top_level_keys'] = sorted(config)
            if any(word in content.lower() for word in ('archive/', 'convergence/')):
                errors.append('CONTEXT_ARCHIVE: configured historical path requires review: ' + name)
        else:
            imports = [line.strip() for line in content.splitlines() if line.lstrip().startswith('@')]
            row['context_imports'] = imports
            for item in imports:
                target = (path.parent / item[1:].split()[0]).resolve()
                if (root / 'plan/archive').resolve() in target.parents:
                    errors.append('CONTEXT_ARCHIVE: historical context import in ' + name)
        rows.append(row)
    # Inventory extension directories; do not infer their behavior from a name.
    for directory in ('.agents', '.codex', '.claude/rules'):
        path = root / directory
        rows.append({'path': directory, 'exists': path.exists(),
                     'files': sorted(str(p.relative_to(root)) for p in path.rglob('*') if p.is_file()) if path.is_dir() else []})
    return {'scope': 'Repository entry files/configuration only; host-global and plugin auto-context not attested',
            'files': rows, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    summary_path = safe_output(ROOT, output / 'governance-summary.json')
    if output.exists() and any(output.iterdir()):
        parser.error('Use a new empty output directory to preserve prior results')
    output.mkdir(parents=True, exist_ok=True)
    before = validator.build_manifest()
    registry, errors = validator.normative_registry(validator.load(), ROOT / 'plan')
    context = context_inventory(ROOT)
    errors += context['errors']
    (output / 'normative-index.json').write_text(json.dumps(registry, ensure_ascii=False, indent=2)+'\n')
    (output / 'context-inventory.json').write_text(json.dumps(context, ensure_ascii=False, indent=2)+'\n')
    commands = [
        ['plan/scripts/validate_plan.py', '--check', '--output-dir', str(output / 'plan')],
        ['plan/scripts/validate_plan.py', '--self-test', '--output-dir', str(output / 'self-test')],
        ['plan/scripts/test_governance.py', '--output-dir', str(output / 'governance')],
        ['plan/scripts/test_ai_execution.py', '--output-dir', str(output / 'ai')],
        ['plan/scripts/probe_governance_legacy.py', '--output', str(output / 'legacy.json')],
    ]
    results = []
    for args in commands:
        command = [sys.executable, '-B', *args]
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        row = {'command': command, 'started_at': started, 'exit_code': result.returncode,
               'stdout': result.stdout, 'stderr': result.stderr}
        results.append(row)
        print(f'{args[0]} {args[1]}: exit={result.returncode}', flush=True)
    if before != validator.build_manifest():
        errors.append('SOURCE_MUTATION: checking changed the normative source tree')
    summary = {'scope': 'Local V2-002 engineering checks; not remote CI or final acceptance',
               'status': 'PASS' if not errors and all(r['exit_code'] == 0 for r in results) else 'FAIL',
               'generated_at': datetime.now(timezone.utc).isoformat(), **validator.repository_identity(),
               'manifest_sha256': validator.sha(ROOT / 'plan/FILE_MANIFEST.json'),
               'errors': errors, 'commands': results}
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status': summary['status'], 'errors': errors, 'report': str(summary_path)}, ensure_ascii=False))
    return 0 if summary['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
