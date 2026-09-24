#!/usr/bin/env python3
"""Inspect the complete production package using the current P0 static policy."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plan/scripts'))
from architecture_checks import check_architecture
from task_entry import safe_output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--disable-gate', action='append', default=[])
    args = parser.parse_args(argv)
    try:
        output = safe_output(ROOT, args.output)
    except ValueError as exc:
        parser.error(str(exc))
    report = check_architecture(ROOT, disabled_gates=args.disable_gate)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'files': report['coverage']['file_count'],
                      'findings': len(report['findings']), 'report': str(output)}, ensure_ascii=False))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
