"""Writers for Outline Bootstrap artifacts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..serialize.serialization_utils import dump_pretty_json
from .sources import ReferenceSource


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def derived_outline_dir(project_path: str | Path) -> Path:
    return Path(project_path) / "registry" / "derived" / "outline"


def load_project_outline(project_path: str | Path) -> dict | None:
    """Load the project's final outline from its stable derived home
    (registry/derived/outline/OUTLINE-00001.json) — the file BOTH genesis paths
    write (write_mock_outline + write_outline_run). Returns the outline dict, or
    None when absent or unreadable.

    This is the read seam that lets the serial consume what genesis produced:
    the outline drives the chapter IR / scene plan / director objective (major>=3
    prompt versions). It never raises — a missing or corrupt outline degrades the
    serial to event-only planning (today's behavior), it does not abort a run."""
    path = derived_outline_dir(project_path) / "OUTLINE-00001.json"
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return obj if isinstance(obj, dict) else None


def new_run_dir(project_path: str | Path, run_id: str | None = None) -> Path:
    runs = Path(project_path) / "workspace" / "outline-bootstrap" / "runs"
    if run_id:
        # An explicit run id must be unique — a named collision is a real error.
        path = runs / run_id
        path.mkdir(parents=True, exist_ok=False)
        return path
    # Auto-generated stamp: seconds-granularity, so two runs in the same second
    # (e.g. genesis preview then --confirm) would collide. Disambiguate with a
    # numeric suffix instead of crashing.
    base = f"outline-{_utc_stamp()}"
    path = runs / base
    suffix = 1
    while path.exists():
        path = runs / f"{base}-{suffix}"
        suffix += 1
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_pretty_json(data) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def mock_outline(project_id: str, sources: list[ReferenceSource], evidence_pack: dict | None = None) -> dict:
    provenance = {
        "project_id": project_id,
        "reference_sources": [source.__dict__ for source in sources],
        "analysis_summary": {},
    }
    if evidence_pack is not None:
        provenance["narrative_evidence_pack"] = {
            "id": evidence_pack.get("id"),
            "task": evidence_pack.get("task"),
            "corpus_snapshot_id": evidence_pack.get("corpus_snapshot_id"),
            "provenance": evidence_pack.get("provenance"),
        }
    return {
        "id": "OUTLINE-00001",
        "kind": "novel_outline",
        "schema_version": "0.2.0",
        "title": "待定标题",
        "genre": [],
        "logline": "基于参考作品结构分析生成的原创小说大纲占位稿。",
        "themes": [],
        "core_hook": "",
        "market_position": {},
        "protagonist_engine": {},
        "power_system": {},
        "conflict_ladder": [],
        "reward_loop": {},
        "world": {"summary": "", "rules": []},
        "characters": [],
        "plot": {"main_arc": "", "volumes": [], "chapters": []},
        "first_30_chapters": [],
        "originality_delta": [],
        "collaboration": {"selected_candidate": "CANDIDATE-A", "agents": []},
        "originality_report": {
            "risk_level": "unknown",
            "notes": ["v0.1 mock outline; real originality review is not yet executed."],
        },
        "provenance": provenance,
    }


def outline_markdown(outline: dict) -> str:
    refs = outline.get("provenance", {}).get("reference_sources", [])
    ref_lines = "\n".join(f"- {ref['id']} `{ref['filename']}`" for ref in refs) or "- 无"
    world_rules = outline.get("world", {}).get("rules", [])
    world_rule_lines = "\n".join(f"- {rule}" for rule in world_rules) or "- 待生成"
    characters = outline.get("characters", [])

    def _char_line(item: dict) -> str:
        aliases = [a for a in (item.get("aliases") or []) if isinstance(a, str) and a.strip()]
        alias_str = f"（别名：{'、'.join(aliases)}）" if aliases else ""
        return f"- {item.get('role', '')}: {item.get('name', '')}{alias_str}，{item.get('arc', '')}"

    character_lines = "\n".join(_char_line(item) for item in characters) or "- 待生成"
    volumes = outline.get("plot", {}).get("volumes", [])
    volume_lines = "\n".join(
        f"- {item.get('id', '')}《{item.get('title', '')}》：{item.get('purpose', '')}"
        for item in volumes
    ) or "- 待生成"
    originality = outline.get("originality_report", {})
    notes = originality.get("notes", [])
    note_lines = "\n".join(f"- {note}" for note in notes) or "- 待生成"
    collaboration = outline.get("collaboration", {})
    market_position = outline.get("market_position", {})
    conflict_ladder = outline.get("conflict_ladder", [])
    first_30 = outline.get("first_30_chapters", [])
    originality_delta = outline.get("originality_delta", [])
    delta_lines = "\n".join(
        f"- {item.get('axis', '')}: {item.get('reference_pattern', '')} → {item.get('our_variation', '')}"
        for item in originality_delta
    ) or "- 待生成"
    evidence_pack = outline.get("provenance", {}).get("narrative_evidence_pack", {})
    evidence_pack_lines = "\n".join([
        f"- id: {evidence_pack.get('id', '待定')}" if evidence_pack else "- 待生成",
        f"- provenance: {evidence_pack.get('provenance', {})}" if evidence_pack else "",
        f"- constraint_count: {evidence_pack.get('constraint_count', '待生成')}" if evidence_pack else "",
    ]).strip()
    if not evidence_pack_lines:
        evidence_pack_lines = "- 待生成"
    ladder_lines = "\n".join(
        f"- {item.get('level', '')}: {item.get('enemy', '')} / {item.get('pressure_source', '')}"
        for item in conflict_ladder
    ) or "- 待生成"
    chapter_lines = "\n".join(
        f"- 第{item.get('chapter_no', '')}章：{item.get('goal', '')} → {item.get('end_hook', '')}"
        for item in first_30
    ) or "- 待生成"
    return (
        f"# {outline.get('title', '待生成')}\n\n"
        f"## 一句话核心\n\n{outline.get('logline', '待生成')}\n\n"
        "## 参考输入\n\n"
        f"{ref_lines}\n\n"
        "## 市场定位\n\n"
        f"{market_position.get('reader_promise', '待生成。')}\n\n"
        "## 世界观\n\n"
        f"{outline.get('world', {}).get('summary', '待生成。')}\n\n"
        f"{world_rule_lines}\n\n"
        "## 人物\n\n"
        f"{character_lines}\n\n"
        "## 主线\n\n"
        f"{outline.get('plot', {}).get('main_arc', '待生成。')}\n\n"
        f"{volume_lines}\n\n"
        "## 冲突梯度\n\n"
        f"{ladder_lines}\n\n"
        "## 前30章\n\n"
        f"{chapter_lines}\n\n"
        "## 原创性差异\n\n"
        f"{delta_lines}\n\n"
        "## 协作\n\n"
        f"selected_candidate: {collaboration.get('selected_candidate', '待定')}\n\n"
        "## 原创性约束\n\n"
        f"风险等级：{originality.get('risk_level', 'unknown')}\n\n"
        f"{note_lines}\n\n"
        "## 语料证据包\n\n"
        f"{evidence_pack_lines}\n"
    )


def write_mock_outline(project_path: str | Path, sources: list[ReferenceSource]) -> tuple[Path, Path]:
    project = Path(project_path)
    project_id_path = project / "registry" / "_meta" / "project-id"
    project_id = project_id_path.read_text(encoding="utf-8").strip() if project_id_path.exists() else project.name
    outline = mock_outline(project_id, sources)

    out_dir = derived_outline_dir(project)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "OUTLINE-00001.json"
    md_path = out_dir / "OUTLINE-00001.md"
    json_path.write_text(dump_pretty_json(outline) + "\n", encoding="utf-8")
    md_path.write_text(outline_markdown(outline), encoding="utf-8")
    return json_path, md_path


def project_id(project_path: str | Path) -> str:
    project = Path(project_path)
    project_id_path = project / "registry" / "_meta" / "project-id"
    return project_id_path.read_text(encoding="utf-8").strip() if project_id_path.exists() else project.name


def write_outline_run(
    project_path: str | Path,
    *,
    sources: list[ReferenceSource],
    analysis: list[dict],
    merged_analysis: dict,
    candidates: list[dict],
    reviews: list[dict],
    final_outline: dict,
    import_plan: dict,
    outline_review: dict | None = None,
    evidence_pack: dict | None = None,
    tournament: dict | None = None,
    ci_m4_ledger: dict | None = None,
    promise_ledger: dict | None = None,
    semantic_ledger: dict | None = None,
    chapter_evidence_ledger: dict | None = None,
    proposal_comparison: dict | None = None,
    run_id: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    """Persist the v0.2 analysis trail and final derived outline."""
    project = Path(project_path)
    run_dir = new_run_dir(project, run_id)

    source_snapshot = {
        "version": 1,
        "sources": [source.__dict__ for source in sources],
    }
    _write_json(run_dir / "sources.snapshot.json", source_snapshot)
    _write_json(run_dir / "analysis" / "references.json", analysis)
    if evidence_pack is not None:
        _write_json(run_dir / "analysis" / "evidence-pack.json", evidence_pack)
    _write_json(run_dir / "analysis" / "merged.json", merged_analysis)
    _write_json(run_dir / "candidates.json", candidates)
    _write_json(run_dir / "reviews.json", reviews)
    _write_json(run_dir / "final-outline.json", final_outline)
    _write_text(run_dir / "final-outline.md", outline_markdown(final_outline))
    if outline_review is not None:
        _write_json(run_dir / "outline-review.json", outline_review)
    if tournament is not None:
        _write_json(run_dir / "tournament.json", tournament)
    if proposal_comparison is not None:
        _write_json(run_dir / "proposal-comparison.json", proposal_comparison)
    if ci_m4_ledger is not None:
        _write_json(run_dir / "ci-m4-ledger.json", ci_m4_ledger)
    if promise_ledger is not None:
        _write_json(run_dir / "promise-ledger.json", promise_ledger)
    if semantic_ledger is not None:
        _write_json(run_dir / "semantic-ledger.json", semantic_ledger)
    if chapter_evidence_ledger is not None:
        _write_json(run_dir / "chapter-evidence-ledger.json", chapter_evidence_ledger)
    _write_json(run_dir / "import-plan.json", import_plan)

    out_dir = derived_outline_dir(project)
    json_path = out_dir / "OUTLINE-00001.json"
    md_path = out_dir / "OUTLINE-00001.md"
    _write_json(json_path, final_outline)
    _write_text(md_path, outline_markdown(final_outline))
    return run_dir, json_path, md_path, run_dir / "import-plan.json"
