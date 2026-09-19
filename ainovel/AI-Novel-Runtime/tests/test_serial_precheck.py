from __future__ import annotations

from pathlib import Path

from runtime.cli import _cmd_serial_precheck

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


def _scaffold_project(root: Path):
    facts = root / "registry" / "facts"
    meta = root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")
    (facts / "timelines").mkdir(parents=True, exist_ok=True)
    (facts / "characters").mkdir(parents=True, exist_ok=True)
    (facts / "events").mkdir(parents=True, exist_ok=True)
    (facts / "world_rules").mkdir(parents=True, exist_ok=True)
    (facts / "relationships").mkdir(parents=True, exist_ok=True)
    (facts / "timelines" / "TML-00001.yaml").write_text(
        "id: TML-00001\nname: 主线\nstatus: active\nfact_version: 1\nkind: main\n",
        encoding="utf-8")
    (facts / "characters" / "CHR-00001.yaml").write_text(
        "id: CHR-00001\nname: 主角\nstatus: active\nfact_version: 1\n",
        encoding="utf-8")
    for i in range(1, 3):
        (facts / "events" / f"EVT-{i:05d}.yaml").write_text(
            f"id: EVT-{i:05d}\nname: 事件{i}\nstatus: active\nfact_version: 1\ntimeline: TML-00001\nsequence_index: {i}\nparticipants:\n  - CHR-00001\ncauses: []\neffects: []\ncertainty: canon\nsummary: 第{i}章\n",
            encoding="utf-8")


class _Args:
    project: str
    standard_root: str
    schema_dir: str | None = None
    out: str | None = None
    prompt_version = "6.0.0"
    max_depth = 2
    budget_limit = 20.0
    per_chapter_budget = None
    model_provider = "deterministic"
    model_id = "deepseek-v4-pro"
    temperature = 0.7
    top_p = None
    max_tokens = None
    timeout = 120
    replay_dir = None
    reviewer = "unanchored"
    panel_roles = "literary,structural,commercial,logic"


def test_precheck_command_builds_report_artifacts(tmp_path):
    _scaffold_project(tmp_path)
    args = _Args()
    args.project = str(tmp_path)
    args.standard_root = str(STANDARD)
    args.schema_dir = str(SCHEMA)
    rc = _cmd_serial_precheck(args)
    assert rc in (0, 1)
    assert (tmp_path / "registry" / "derived").exists()
