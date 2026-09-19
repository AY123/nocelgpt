"""Market observation loading for Market Intelligence (roadmap P0).

Observations are dated market inputs a project supplies under
``sources/market-observations/`` (ranking snapshots, trend notes, review-section
dumps). They are external inputs — never Registry facts. Each observation may
declare its capture date via a leading ``fetched_at: YYYY-MM-DD`` line; the
snapshot uses the EARLIEST such date to drive staleness (oldest evidence wins).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable

SUPPORTED_EXTENSIONS = {".txt", ".md"}
_FETCHED_RE = re.compile(r"fetched_at\s*[:=]\s*(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class MarketObservation:
    id: str
    path: str
    filename: str
    sha256: str
    size_bytes: int
    platform: str
    fetched_at: str | None


@dataclass(frozen=True)
class ObservationCheckResult:
    ok: bool
    observations: list[MarketObservation]
    errors: list[str]


def observations_dir(project_path: str | Path) -> Path:
    return Path(project_path) / "sources" / "market-observations"


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_fetched_at(text: str) -> str | None:
    m = _FETCHED_RE.search(text)
    return m.group(1) if m else None


def _platform_from_name(filename: str) -> str:
    stem = Path(filename).stem.lower()
    for platform in ("qidian", "fanqie", "qimao", "royalroad", "webnovel",
                     "amazon", "ao3", "起点", "番茄", "七猫"):
        if platform in stem:
            return platform
    return "unknown"


def load_market_observations(project_path: str | Path) -> ObservationCheckResult:
    source_dir = observations_dir(project_path)
    if not source_dir.exists():
        return ObservationCheckResult(
            ok=False, observations=[],
            errors=[f"missing market observations directory: {source_dir}"])

    files = sorted(p for p in source_dir.iterdir() if p.is_file())
    unsupported = [p.name for p in files if p.suffix.lower() not in SUPPORTED_EXTENSIONS]
    valid = [p for p in files if p.suffix.lower() in SUPPORTED_EXTENSIONS]

    errors: list[str] = []
    if unsupported:
        errors.append("unsupported market observation format(s): "
                      + ", ".join(unsupported) + " (supported: .txt, .md)")
    if not valid:
        errors.append("at least 1 market observation is required")

    observations = []
    for index, path in enumerate(valid, start=1):
        text = path.read_text(encoding="utf-8")
        observations.append(MarketObservation(
            id=f"OBS-{index:05d}",
            path=str(path.relative_to(Path(project_path))),
            filename=path.name,
            sha256=_hash_file(path),
            size_bytes=path.stat().st_size,
            platform=_platform_from_name(path.name),
            fetched_at=_extract_fetched_at(text),
        ))

    return ObservationCheckResult(ok=not errors, observations=observations, errors=errors)


def iter_observation_texts(project_path: str | Path, observations: Iterable[MarketObservation]):
    project = Path(project_path)
    for obs in observations:
        yield obs, (project / obs.path).read_text(encoding="utf-8")
