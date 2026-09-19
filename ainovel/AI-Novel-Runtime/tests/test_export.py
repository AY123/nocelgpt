"""test_export.py — book + IP-bible exporters (roadmap P20, SOP stages 15/16).

Proves the exporters are pure read-side folds: the book assembles chapters in
order, scope='published' exports ONLY chapters a human authorized in the
published log (ADR-009) while 'produced' exports all drafts, md/txt render
deterministically, the IP bible folds the Story State, and NOTHING is written to
registry/ or the published log by exporting.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from runtime.export import (assemble_book, render_markdown, render_txt,
                            assemble_ip_bible, render_ip_markdown)

STANDARD = Path(__file__).resolve().parent.parent.parent / "AI-Novel-Standard"


def _write_draft(root: Path, i: int):
    task_id = f"TASK-{i:05d}"
    rel = f"registry/derived/drafts/{task_id}.json"
    obj = {"envelope_format": "runtime-draft/1.0",
           "draft": {"artifact_format": "1.0", "kind": "prose",
                     "capability": "ChapterDraft", "task_id": task_id,
                     "body": f"第{i}章的正文内容。", "content_hash": f"sha256:{i:064d}"},
           "qa_review": None}
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return {"id": task_id, "category": "drafts", "path": rel,
            "content_hash": f"sha256:{i:064d}"}


def _scaffold_drafts(root: Path, n: int):
    entries = [_write_draft(root, i) for i in range(1, n + 1)]
    idx = root / "registry" / "derived"
    idx.mkdir(parents=True, exist_ok=True)
    (idx / "_index.yaml").write_text(
        yaml.safe_dump({"artifacts": entries}, allow_unicode=True), encoding="utf-8")


def _publish(root: Path, task_ids):
    log = {"id": "PUBLOG-00001", "kind": "published_log", "version": "1.0",
           "published": [{"task_id": t} for t in task_ids]}
    (root / "sources").mkdir(parents=True, exist_ok=True)
    (root / "sources" / "published-log.yaml").write_text(
        yaml.safe_dump(log, allow_unicode=True), encoding="utf-8")


def _scaffold_facts(root: Path, n_events=3):
    facts = root / "registry" / "facts"
    meta = root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")

    def w(p, o):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.safe_dump(o, allow_unicode=True, sort_keys=False),
                     encoding="utf-8")

    w(facts / "timelines" / "TML-00001.yaml", {
        "id": "TML-00001", "name": "主线", "status": "active",
        "fact_version": 1, "kind": "main"})
    w(facts / "characters" / "CHR-00001.yaml", {
        "id": "CHR-00001", "name": "主角", "status": "active", "fact_version": 1})
    for i in range(1, n_events + 1):
        w(facts / "events" / f"EVT-{i:05d}.yaml", {
            "id": f"EVT-{i:05d}", "name": f"事件{i}", "status": "active",
            "fact_version": 1, "timeline": "TML-00001", "sequence_index": i,
            "participants": ["CHR-00001"],
            "causes": ([f"EVT-{i-1:05d}"] if i > 1 else []),
            "summary": f"第{i}章核心"})


# --------------------------------------------------------------------------- #
# Book: assembly, scope, render                                                #
# --------------------------------------------------------------------------- #
def test_produced_scope_exports_all_drafts_in_order(tmp_path):
    _scaffold_drafts(tmp_path, 3)
    book = assemble_book(tmp_path, scope="produced")
    assert [c.task_id for c in book.chapters] == \
        ["TASK-00001", "TASK-00002", "TASK-00003"]
    # chapter numbering is sequential over the exported set
    assert [c.title for c in book.chapters] == ["第1章", "第2章", "第3章"]


def test_published_scope_exports_only_authorized(tmp_path):
    # 3 drafts exist, but only 2 are authorized as published (ADR-009).
    _scaffold_drafts(tmp_path, 3)
    _publish(tmp_path, ["TASK-00001", "TASK-00003"])
    book = assemble_book(tmp_path, scope="published")
    assert [c.task_id for c in book.chapters] == ["TASK-00001", "TASK-00003"]


def test_published_scope_is_default(tmp_path):
    _scaffold_drafts(tmp_path, 3)
    _publish(tmp_path, ["TASK-00001"])
    # no scope arg -> published
    assert [c.task_id for c in assemble_book(tmp_path).chapters] == ["TASK-00001"]


def test_published_scope_without_log_is_empty(tmp_path):
    # Drafts exist but nothing authorized -> a published export is empty. The
    # exporter must NOT fall back to produced (ADR-009: never infer publication).
    _scaffold_drafts(tmp_path, 3)
    assert assemble_book(tmp_path, scope="published").chapters == []
    # produced still returns everything
    assert len(assemble_book(tmp_path, scope="produced").chapters) == 3


def test_render_markdown_and_txt_deterministic(tmp_path):
    _scaffold_drafts(tmp_path, 2)
    book = assemble_book(tmp_path, scope="produced", title="测试书")
    md1, md2 = render_markdown(book), render_markdown(book)
    assert md1 == md2
    assert md1.startswith("# 测试书")
    assert "## 第1章" in md1 and "第1章的正文内容。" in md1
    txt = render_txt(book)
    assert txt.startswith("测试书")
    assert "第2章的正文内容。" in txt


# --------------------------------------------------------------------------- #
# Exporting NEVER writes registry or the published log (ADR-009 / ADR-006)     #
# --------------------------------------------------------------------------- #
def test_export_does_not_write_published_log_or_registry(tmp_path):
    _scaffold_drafts(tmp_path, 2)
    before = {p: p.read_bytes() for p in (tmp_path / "registry").rglob("*")
              if p.is_file()}
    assemble_book(tmp_path, scope="produced")
    render_markdown(assemble_book(tmp_path, scope="produced"))
    after = {p: p.read_bytes() for p in (tmp_path / "registry").rglob("*")
             if p.is_file()}
    assert before == after                        # registry byte-unchanged
    assert not (tmp_path / "sources" / "published-log.yaml").exists()  # never authored by us


# --------------------------------------------------------------------------- #
# IP bible: folds the Story State                                              #
# --------------------------------------------------------------------------- #
def test_ip_bible_folds_state(tmp_path):
    _scaffold_facts(tmp_path, n_events=3)
    bible = assemble_ip_bible(tmp_path)
    assert "CHR-00001" in bible.characters
    assert bible.event_order == ["EVT-00001", "EVT-00002", "EVT-00003"]
    md = render_ip_markdown(bible)
    assert "IP 设定集" in md
    assert "主角" in md
    # deterministic
    assert render_ip_markdown(assemble_ip_bible(tmp_path)) == md


def test_ip_bible_empty_project_degrades(tmp_path):
    _scaffold_facts(tmp_path, n_events=0)
    bible = assemble_ip_bible(tmp_path)
    assert bible.event_order == []
    # renders without error, shows the empty markers
    assert "（无）" in render_ip_markdown(bible)
