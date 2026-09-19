import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.corpus import build_snapshot, query_analysis_books
from runtime.narrative_mining import DeterministicBookProfileAnalyzer, build_consensus_profile
from runtime.retrieval.genesis import build_narrative_evidence_pack, build_query_hash

ROOT = Path(__file__).parent / "fixtures" / "corpus-xuanhuan-10"


def _schema():
    path = Path(__file__).resolve().parents[2] / "AI-Novel-Standard" / "contracts" / "narrative-evidence-pack.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot():
    return build_snapshot(**json.loads((ROOT / "snapshot-input.json").read_text(encoding="utf-8")))


def _profiles(snapshot):
    books = query_analysis_books(snapshot)
    analyzer = DeterministicBookProfileAnalyzer()
    profiles = []
    for book in books:
        text = (ROOT / book["relative_path"]).read_text(encoding="utf-8")
        profiles.append(analyzer.analyze(book, text, snapshot=snapshot))
    return profiles


def test_evidence_pack_schema_and_provenance_binding():
    snapshot = _snapshot()
    profiles = _profiles(snapshot)
    query = {
        "genre": "玄幻",
        "target_reader": ["升级流读者"],
        "chapter_index": 1,
        "arc_stage": "open",
        "target_function": "genesis",
        "current_problem": ["开局缺少破局点"],
        "required_effect": ["第一章可见回报"],
        "forbidden": ["复刻单本事件顺序"],
    }
    pack = build_narrative_evidence_pack(
        task="genesis",
        snapshot=snapshot,
        query=query,
        baselines=[{"id": "baseline-1", "slice": "open", "sample_size": 7, "signals": {"first_visible_payoff_chapter": 1}}],
        patterns=[{"id": "pattern-1", "pattern_type": "opening-payoff", "mechanism": "限制驱动主动破局", "conditions": ["limit", "choice"], "effects": ["visible payoff"], "support": {"source_clusters": 2, "top_profiles": [profiles[0]["id"]]}}],
        anti_patterns=[{"id": "anti-1", "pattern_type": "mid-stage-risk", "mechanism": "无代价升级", "conditions": ["power without limit"], "effects": ["risk of flat growth"], "support": {"source_clusters": 1, "top_profiles": [profiles[-1]["id"]]}, "risk": ["single_axis_growth"]}],
        constraints=["不得暴露连续原文", "不得复制单书事件顺序"],
        originality={"source_cluster_count": 3, "max_single_source_share": 0.34, "risk_level": "low", "notes": ["multi-source synthesis"]},
        profile_ids=[p["id"] for p in profiles],
    )
    Draft202012Validator(_schema()).validate(pack)
    assert pack["provenance"]["snapshot_hash"] == snapshot["manifest_hash"]
    assert pack["provenance"]["query_hash"] == build_query_hash(query, snapshot["id"])
    assert len(pack["provenance"]["profile_ids"]) == len(profiles)


def test_evidence_pack_uses_snapshot_and_query_only_for_provenance():
    snapshot = _snapshot()
    query = {"genre": "玄幻", "target_reader": ["升级流读者"], "chapter_index": 1, "arc_stage": "open", "target_function": "genesis"}
    assert build_query_hash(query, snapshot["id"]) == build_query_hash(query, snapshot["id"])
    assert build_query_hash(query, snapshot["id"]) != build_query_hash({**query, "chapter_index": 2}, snapshot["id"])
