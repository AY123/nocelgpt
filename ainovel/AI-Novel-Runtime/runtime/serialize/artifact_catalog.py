"""artifact_catalog.py — unified discovery index for runtime governance artifacts.

This loader reads the JSON catalog stored with the quality golden set so runtime
code can discover standardized artifacts without hardcoding every path.
"""
from __future__ import annotations

from pathlib import Path
import json

ARTIFACT_CATALOG_KIND = "artifact_catalog"
ARTIFACT_CATALOG_VERSION = "1.0"
ARTIFACT_CATALOG_FILENAME = "artifact-catalog.json"


def _catalog_path(project_path: str | Path) -> Path:
    return Path(project_path) / "quality-golden-set" / "metadata" / ARTIFACT_CATALOG_FILENAME


def load_artifact_catalog(project_path: str | Path) -> dict:
    path = _catalog_path(project_path)
    return json.loads(path.read_text(encoding="utf-8"))


def catalog_sections(project_path: str | Path) -> list[str]:
    catalog = load_artifact_catalog(project_path)
    return [section["section"] for section in catalog.get("sections", [])]


def catalog_artifacts(project_path: str | Path) -> list[str]:
    catalog = load_artifact_catalog(project_path)
    artifacts: list[str] = []
    for section in catalog.get("sections", []):
        artifacts.extend(section.get("artifacts", []))
    return artifacts
