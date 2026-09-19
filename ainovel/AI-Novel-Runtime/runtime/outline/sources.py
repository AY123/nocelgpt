"""Reference source loading for Outline Bootstrap.

The source contract is intentionally narrow for v0.1: a project may provide 1-5
plain-text or markdown reference novels under ``sources/reference-novels``.
These files are external inspiration inputs, not Registry facts.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable

SUPPORTED_EXTENSIONS = {".txt", ".md"}
MIN_REFERENCE_NOVELS = 1
MAX_REFERENCE_NOVELS = 5


@dataclass(frozen=True)
class ReferenceSource:
    id: str
    path: str
    filename: str
    extension: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class SourceCheckResult:
    ok: bool
    sources: list[ReferenceSource]
    errors: list[str]


def reference_dir(project_path: str | Path) -> Path:
    return Path(project_path) / "sources" / "reference-novels"


def load_genesis_preference(project_path: str | Path) -> dict:
    """The optional human target-preference that STEERS reference-derived analysis.

    The system's charter is "1-5 reference novels + a little human preference": the
    references supply narrative/commercial STRUCTURE, but which sub-genre to actually
    write is a human product call, not a keyword-frequency verdict. Western-flavoured
    东方玄幻 references (盘龙/奥术起源: 魔法/龙/骑士) score the generic 奇幻 hint above
    the 玄幻 one, so a pure frequency detector mislabels primary genre. This preference
    lets the human pin target_genre; the workflow floats it to the front of
    genre_signals (detection stays the fallback). Absent => byte-identical behaviour.

    Read from the optional `sources/genesis-preference.yaml`. Advisory input, not a
    fact (ADR-006): it shapes the derived outline, never the registry."""
    path = Path(project_path) / "sources" / "genesis-preference.yaml"
    if not path.exists():
        return {}
    try:
        import yaml
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _candidate_files(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        return []
    return sorted(path for path in source_dir.iterdir() if path.is_file())


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_id(index: int) -> str:
    return f"REF-{index:05d}"


def load_reference_sources(project_path: str | Path) -> SourceCheckResult:
    source_dir = reference_dir(project_path)
    errors: list[str] = []

    if not source_dir.exists():
        return SourceCheckResult(
            ok=False,
            sources=[],
            errors=[f"missing reference source directory: {source_dir}"],
        )

    files = _candidate_files(source_dir)
    unsupported = [path.name for path in files if path.suffix.lower() not in SUPPORTED_EXTENSIONS]
    valid_files = [path for path in files if path.suffix.lower() in SUPPORTED_EXTENSIONS]

    if unsupported:
        errors.append(
            "unsupported reference novel format(s): "
            + ", ".join(unsupported)
            + " (supported: .txt, .md)"
        )
    if len(valid_files) < MIN_REFERENCE_NOVELS:
        errors.append("at least 1 reference novel is required")
    if len(valid_files) > MAX_REFERENCE_NOVELS:
        errors.append("at most 5 reference novels are allowed")

    sources = [
        ReferenceSource(
            id=_source_id(index),
            path=str(path.relative_to(Path(project_path))),
            filename=path.name,
            extension=path.suffix.lower(),
            sha256=_hash_file(path),
            size_bytes=path.stat().st_size,
        )
        for index, path in enumerate(valid_files[:MAX_REFERENCE_NOVELS], start=1)
    ]

    return SourceCheckResult(ok=not errors, sources=sources, errors=errors)


def render_source_report(result: SourceCheckResult) -> str:
    if not result.ok:
        lines = ["reference source check failed"]
        lines.extend(f"- {error}" for error in result.errors)
        if result.sources:
            lines.append(f"valid reference novels found: {len(result.sources)}")
        return "\n".join(lines)

    lines = [f"OK: found {len(result.sources)} reference novel(s)"]
    lines.extend(
        f"- {source.id} {source.filename} sha256={source.sha256[:12]} size={source.size_bytes}"
        for source in result.sources
    )
    return "\n".join(lines)


# Chinese web-novel .txt files in the wild are rarely UTF-8 — GBK/GB18030 is the
# dominant encoding, and `file` often mislabels them as iso-8859-1. Try UTF-8
# first (the contract default), then GB18030 (a GBK superset covering nearly all
# Simplified/Traditional text), and finally decode with replacement so a single
# stray byte can never crash the whole bootstrap over an otherwise-usable source.
_DECODE_ENCODINGS = ("utf-8", "gb18030")


def _decode_bytes(raw: bytes) -> str:
    for enc in _DECODE_ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def iter_source_texts(project_path: str | Path, sources: Iterable[ReferenceSource]):
    project = Path(project_path)
    for source in sources:
        path = project / source.path
        yield source, _decode_bytes(path.read_bytes())
