from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from .narrative import project_narrative_state
from .reference.abstract import load_reference_abstraction


@dataclass(frozen=True)
class DashboardReport:
    project: str
    narrative: dict
    reference_anchor: dict

    def to_dict(self) -> dict:
        return {
            "project": self.project,
            "narrative": self.narrative,
            "reference_anchor": self.reference_anchor,
        }


def build_dashboard(project_path: str | Path, **kwargs: Any) -> DashboardReport:
    project = Path(project_path)
    ref = load_reference_abstraction(project) or {}
    narrative = project_narrative_state(type("R", (), {"version": 0, "facts": {}})(), project).to_dict()
    if ref:
        narrative.setdefault("reference_anchor", ref)
    return DashboardReport(project=str(project), narrative=narrative, reference_anchor=ref)
