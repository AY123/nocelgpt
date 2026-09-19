#!/usr/bin/env python3
"""Initialize a new ANES Project from the Standard catalog.

The Template owns project shape. It scaffolds an empty facts registry from the
Standard catalog and adds the Outline Bootstrap workspace used to turn 1-5
reference novels into a derived outline before any facts are imported.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


DEFAULT_DERIVED_DIRS = ("summary", "snapshot", "analysis", "outline")

# The Novel Brain (roadmap P15) is the AUTHORED static constitution. It is not a
# fact and not a derived artifact — it lives here under sources/, hand-written.
# Scaffolded as a commented example so every project has the slot; its
# writing_style + forbidden_style feed the chapter-draft prompt. Validate with
# `runtime.cli brain check` (advisory, never gates).
_BRAIN_TEMPLATE = """\
# Novel Brain — the authored constitution of this novel (roadmap P15).
# It is not a fact and not a derived artifact; you write it by hand.
# UNCOMMENT and fill these in, then run:
#   python -m runtime.cli brain check --project <this-dir>
# Until you do, this file parses as empty and prompts fall back to defaults
# (a blank/all-commented Brain is treated exactly like an absent one).
#
# id: BRAIN-00001
# kind: novel_brain
# version: "1.0"
# mission: ""            # the one-sentence reason this novel exists
# genre:
#   primary: ""          # e.g. 玄幻 / 都市 / 言情
#   channel: ""          # 男频 / 女频 / general
# target_reader:
#   who: ""              # who this is written for
#   wants: []            # what they come for
#   avoids: []           # what makes them drop a book
# promise: ""            # the core payoff the whole book is contracted to deliver
# writing_style:
#   voice: ""            # narrative voice/tone
#   pov: ""              # e.g. 第三人称限知
#   pacing: ""
#   devices: []
# forbidden_style:       # hard 'never do this' rules (at least one)
#   - 注水
# # Optional:
# # commercial_position: { hook: "", comparables: [], monetization: "" }
# # emotional_curve: [ { beat: "憋屈 -> 爆发", at: "第一卷末", intent: "" } ]
# # long_term_theme: ""
# # reader_expectation: []
"""

# The Serial Plan (roadmap P17) is the AUTHORED serialization plan — like the
# Novel Brain it lives under sources/, hand-written, and is not a fact or a
# derived artifact. It is the INPUT to the schedule projection (backlog /
# break-risk / update-calendar). Scaffolded fully commented so a pristine project
# reads as "no plan yet". Validate with `runtime.cli schedule check`.
_SERIAL_PLAN_TEMPLATE = """\
# Serial Plan — the authored serialization plan of this novel (roadmap P17).
# UNCOMMENT and fill these in, then run:
#   python -m runtime.cli schedule check --project <this-dir>
# Until you do, this file parses as empty and the serial can still produce.
#
# id: PLAN-00001
# kind: serial_plan
# version: "1.0"
# start_date: "2026-01-01"   # ISO date publishing starts / started
# daily_target: 2            # chapters to publish per active day
# backlog_target: 14         # desired stock (库存); below it warns of break risk
# rest_days: []              # ISO weekdays with no update (1=Mon .. 7=Sun)
# note: ""
"""

# The Market Position (roadmap 4.5) is the AUTHORED commercial thesis, written
# BEFORE the book is opened — like the Novel Brain it lives under sources/,
# hand-written, and is not a fact or a derived artifact. It is the INPUT to the
# pre-book admission check. Scaffolded fully commented so a pristine project reads
# as "no positioning yet" (the admission check then recommends 'hold'). Validate
# with `runtime.cli positioning admit`.
_MARKET_POSITION_TEMPLATE = """\
# Market Position — the authored commercial thesis of this novel (roadmap 4.5).
# UNCOMMENT and fill these in, then run:
#   python -m runtime.cli positioning admit --project <this-dir>
# Until you do, this file parses as empty and the admission check recommends
# 'hold' (nothing to open on). It folds with the Novel Brain + Market Snapshot.
#
# id: MPOS-00001
# kind: market_position
# version: "1.0"
# channel: ""                 # 男频 / 女频 / general (matched against the snapshot)
# reader_segment:
#   primary: ""               # the core reader segment this book is for
#   secondary: []             # adjacent segments it can also capture
#   pull_triggers: []         # what makes them start AND keep reading
#   drop_triggers: []         # what makes them abandon the book
# trope_map:
#   leans_on:                 # tropes embraced to meet expectation (at least one)
#     - 废柴逆袭
#   subverts: []              # tropes twisted to differentiate
#   differentiation: ""       # why THIS book and not the 100 like it
# commercial_promise:
#   pay_trigger: ""           # the moment/mechanic that converts free -> paying
#   first_30_hook: ""         # why a reader opens ch 2..30 (earns the subscription)
#   sustainability_100: ""    # why the book still has fuel at ch 100 (long-arc engine)
#   comparables: []           # comparable successful titles benchmarked against
"""

# Reader signals (roadmap 5.6) are REAL platform data (订阅/追读/掉粉/打赏), the
# ground-truth counterpart to the PREDICTED reader-simulation. Like Market
# observations they are imported, dated evidence under sources/ — never a fact,
# never a projection. Each signal is one YAML file under sources/reader-signals/;
# a leading-underscore file (like this example) is skipped by the loader.
# Validate + compare with `runtime.cli signals check|compare` (never gates, never
# calibrates the model — the seam is wired, not fired).
_READER_SIGNAL_EXAMPLE = """\
# Reader Signal EXAMPLE (roadmap 5.6) — a real platform observation.
# COPY this to a non-underscore file (e.g. ch-00001.yaml), fill it, then:
#   python -m runtime.cli signals check --project <this-dir>
#   python -m runtime.cli signals compare --project <this-dir> --chapter TASK-00001
# This underscore-prefixed file is a template and is IGNORED by the loader.
#
# kind: reader_signal
# version: "1.0"
# scope: chapter            # chapter | book
# chapter_id: TASK-00001    # required when scope=chapter (the draft's task id)
# source: 起点              # the platform the numbers came from
# collected_at: "2026-01-01"
# metrics:                  # all optional — platforms expose different metrics
#   subscription_count: 0
#   first_day_subscriptions: 0   # 首订
#   retention_rate: 0            # 追读率 % (the clean pair to predicted continue_rate)
#   drop_rate: 0                 # 掉粉 %
#   reward_count: 0              # 打赏
#   monthly_votes: 0             # 月票
#   collection_count: 0          # 收藏
# confidence:
#   level: medium            # low | medium | high — low is flagged, never over-read
#   sample_size: 0
#   is_estimated: false
# provenance:
#   imported_by: ""
#   note: ""
"""


def _mkdirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def _write_once(path: Path, content: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _keep(paths: Iterable[Path]) -> None:
    """Drop a .gitkeep into each dir so the empty Registry skeleton is tracked by
    git (git does not track empty directories). A freshly-initialized Project
    must be committable with its layout intact."""
    for path in paths:
        _write_once(path / ".gitkeep", "")


def _load_catalog(standard_root: Path) -> dict:
    catalog_path = standard_root / "phase-1" / "generated" / "json-schema" / "catalog.json"
    with catalog_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _project_fact_dirs(catalog: dict) -> list[str]:
    dirs = {
        record["facts_dir"]
        for record in catalog.get("by_type_code", {}).values()
        if record.get("scope") == "project"
    }
    return sorted(dirs)


def init_project(*, standard: Path, out: Path, project_id: str) -> None:
    catalog = _load_catalog(standard)
    version_path = standard / "VERSION"
    standard_version = version_path.read_text(encoding="utf-8").strip() if version_path.exists() else "unknown"

    facts_root = out / "registry" / "facts"
    derived_root = out / "registry" / "derived"
    meta_root = out / "registry" / "_meta"

    _mkdirs([out, facts_root, derived_root, meta_root])
    fact_dirs = [facts_root / dirname for dirname in _project_fact_dirs(catalog)]
    derived_dirs = [derived_root / dirname for dirname in DEFAULT_DERIVED_DIRS]
    source_dirs = [
        out / "sources" / "reference-novels",
        out / "sources" / "reader-signals",
        out / "workspace" / "outline-bootstrap" / "runs",
    ]
    _mkdirs(fact_dirs)
    _mkdirs(derived_dirs)
    _mkdirs(source_dirs)
    # git does not track empty dirs; keep the scaffolded skeleton committable.
    _keep(fact_dirs + derived_dirs + source_dirs)

    _write_once(out / "README.md", f"# {project_id}\n\nANES Project initialized from AI-Novel-Template.\n")
    _write_once(meta_root / "registry-version", "1\n")
    _write_once(meta_root / "standard.pin", f"{standard_version}\n")
    _write_once(meta_root / "project-id", f"{project_id}\n")
    _write_once(meta_root / "mint-ledger.yaml", "version: 1\nentries: []\n")
    _write_once(
        out / "sources" / "manifest.yaml",
        "version: 1\n"
        "usage_policy: structure_reference_only\n"
        "reference_novels: []\n",
    )
    _write_once(out / "sources" / "novel-brain.yaml", _BRAIN_TEMPLATE)
    _write_once(out / "sources" / "serial-plan.yaml", _SERIAL_PLAN_TEMPLATE)
    _write_once(out / "sources" / "market-position.yaml", _MARKET_POSITION_TEMPLATE)
    _write_once(out / "sources" / "reader-signals" / "_EXAMPLE.yaml",
                _READER_SIGNAL_EXAMPLE)
    _write_once(
        out / "workspace" / "outline-bootstrap" / "README.md",
        "# Outline Bootstrap Workspace\n\n"
        "Each run records source snapshots, analysis, candidate outlines, reviews, "
        "and the final derived outline before any facts are imported.\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize a new ANES Project")
    parser.add_argument("--standard", required=True, help="Path to AI-Novel-Standard")
    parser.add_argument("--out", required=True, help="Output project directory")
    parser.add_argument("--project-id", required=True, help="Stable project identifier")
    args = parser.parse_args()

    init_project(
        standard=Path(args.standard).resolve(),
        out=Path(args.out).resolve(),
        project_id=args.project_id,
    )
    print(f"initialized project at {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
