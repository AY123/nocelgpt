#!/usr/bin/env python3
"""Repository command for local task action checks and resumption."""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plan/scripts'))
from task_entry import main

if __name__ == '__main__':
    raise SystemExit(main())
