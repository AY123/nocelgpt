"""Compile current Python sources in memory, preserving files and legacy style."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    paths = [
        p
        for area in ("src/anovel", "scripts", "plan/scripts", "tests")
        for p in (ROOT / area).rglob("*.py")
    ]
    if not paths:
        raise ValueError("Empty Python scan")
    for path in paths:
        if path.is_symlink():
            raise ValueError("Python source symlinks need explicit review")
        compile(path.read_bytes(), str(path), "exec")
    print(f"Syntax checked {len(paths)} current Python files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
