import json
from pathlib import Path

from runtime.outline.agents import propose_candidates, review_candidate, synthesize_final_outline
from runtime.outline.workflow import run_outline_bootstrap


def _merged():
    return {
        "genre_signals": ["玄幻"],
        "reader_rewards": ["突破"],
        "structure_signals": ["compact-opening-material"],
        "originality_guardrails": ["不得复制专名"],
    }


def _pack():
    return {
        "id": "NEP-TEST-GENESIS",
        "task": "genesis",
        "corpus_snapshot_id": "CORPUS-TEST-001",
        "patterns": [{"pattern_type": "bounded-ability-payoff"}],
        "anti_patterns": [],
        "constraints": ["能力必须有代价"],
        "originality": {"source_cluster_count": 3, "max_single_source_share": 0.34, "risk_level": "low"},
        "provenance": {"snapshot_hash": "sha256:" + "0" * 64, "query_hash": "sha256:" + "1" * 64, "retrieval_policy_version": "test-v1", "profile_ids": []},
    }


def test_evidence_changes_candidate_and_is_recorded_in_outline_provenance():
    baseline = _merged()
    without = propose_candidates(dict(baseline))
    with_evidence = {**baseline, "narrative_evidence": {"id": _pack()["id"], "patterns": _pack()["patterns"], "anti_patterns": [], "constraints": _pack()["constraints"]}}
    candidates = propose_candidates(with_evidence)
    assert candidates[0]["design_focus"] != without[0]["design_focus"]
    assert "bounded-ability-payoff" in candidates[0]["design_focus"]
    reviews = [review_candidate(candidate, with_evidence) for candidate in candidates]
    outline = synthesize_final_outline(candidates, reviews, with_evidence, "PROJECT-TEST", [])
    assert outline["provenance"]["narrative_evidence_pack"]["id"] == "NEP-TEST-GENESIS"
    assert outline["collaboration"]["selected_candidate"] in {candidate["id"] for candidate in candidates}


def test_outline_bootstrap_without_evidence_remains_compatible(tmp_path):
    project = tmp_path / "project"
    source_dir = project / "sources" / "reference-novels"
    source_dir.mkdir(parents=True)
    source_dir.joinpath("reference.txt").write_text("第一章 开端\n" + "少年面对危机，决定承担代价并开始修炼。" * 30, encoding="utf-8")
    result = run_outline_bootstrap(project, run_id="without-evidence")
    assert result.ok
    outline = json.loads((project / result.outline_json).read_text(encoding="utf-8"))
    assert "narrative_evidence_pack" not in outline["provenance"]


def test_outline_bootstrap_persists_optional_evidence_pack(tmp_path):
    project = tmp_path / "project"
    source_dir = project / "sources" / "reference-novels"
    source_dir.mkdir(parents=True)
    source_dir.joinpath("reference.txt").write_text("第一章 开端\n" + "少年面对危机，决定承担代价并开始修炼。" * 30, encoding="utf-8")
    result = run_outline_bootstrap(project, run_id="with-evidence", evidence_pack=_pack())
    assert result.ok
    outline = json.loads((project / result.outline_json).read_text(encoding="utf-8"))
    assert outline["provenance"]["narrative_evidence_pack"]["id"] == _pack()["id"]
    evidence_path = project / result.run_dir / "analysis" / "evidence-pack.json"
    assert json.loads(evidence_path.read_text(encoding="utf-8"))["id"] == _pack()["id"]
