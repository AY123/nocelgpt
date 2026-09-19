"""D180-02: version dimension decoupling.

Separates pipeline / prompt / schema / model / reviewer version dimensions so any
single capability can be independently toggled without affecting the others.
Advisory-only (ADR-003); never gates.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class VersionDimension:
    dimension: str
    current_version: str
    available_versions: list[str] = field(default_factory=list)
    enabled: bool = True
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VersionMatrix:
    kind: str
    version: str
    dimensions: list[VersionDimension]
    comparison_only: bool = True
    gating: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "version": self.version,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "comparison_only": self.comparison_only,
            "gating": self.gating,
            "metadata": self.metadata,
        }


def build_version_matrix() -> VersionMatrix:
    dims = [
        VersionDimension(
            dimension="pipeline",
            current_version="1.0",
            available_versions=["1.0"],
            description="生产管线版本（genesis → serial → baseline）",
        ),
        VersionDimension(
            dimension="prompt",
            current_version="v12",
            available_versions=["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10", "v11", "v12"],
            description="章节草稿 prompt 模板版本",
        ),
        VersionDimension(
            dimension="schema",
            current_version="1.0",
            available_versions=["1.0"],
            description="事实 / ledger / envelope schema 版本",
        ),
        VersionDimension(
            dimension="model",
            current_version="deepseek-v3",
            available_versions=["deepseek-v3", "gpt-5.4", "stub"],
            description="生成模型版本",
        ),
        VersionDimension(
            dimension="reviewer",
            current_version="judge-v1",
            available_versions=["judge-v1", "human"],
            description="评审器版本",
        ),
    ]
    return VersionMatrix(
        kind="version_matrix",
        version="1.0",
        dimensions=dims,
        metadata={"dimension_count": len(dims)},
    )
