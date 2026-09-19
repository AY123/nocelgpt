import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.corpus import build_snapshot, query_analysis_books
from runtime.narrative_mining import DeterministicBookProfileAnalyzer, LLMBookProfileAnalyzer, build_consensus_profile

ROOT = Path(__file__).parent / "fixtures" / "corpus-xuanhuan-10"


class Response:
    def __init__(self, text): self.text = text


class FakeModel:
    def generate(self, prompt):
        if "自上而下" in prompt:
            payload = {
                "findings": {
                    "core_fantasy": "从受限资源中建立优势", "target_reader": ["玄幻读者"],
                    "selling_point": "限制驱动主动破局", "protagonist_deficit": "资源不足",
                    "long_term_desire": "扩大行动权", "core_ability": "受限能力",
                    "limitations": ["只有一次"], "growth_axes": ["能力", "身份"],
                    "first_visible_payoff_chapter": 1, "first_volume_promise": "完成第一次破局",
                    "sustainability_sources": ["限制", "身份"], "mid_stage_risks": ["前后复述"]
                },
                "evidence": [{"field": "selling_point", "chapter_indexes": [1], "feature_codes": ["hook"]}],
                "confidence": {"level": "medium", "score": 0.7, "limitations": ["抽样有限"]}
            }
        else:
            payload = {
                "findings": {
                    "core_fantasy": "通过选择改变处境", "target_reader": ["玄幻读者"],
                    "selling_point": "任务推进带来代价", "protagonist_deficit": "起点低",
                    "long_term_desire": "提高行动空间", "core_ability": "任务能力",
                    "limitations": [], "growth_axes": ["任务", "关系"],
                    "first_visible_payoff_chapter": 2, "first_volume_promise": "建立稳定回报",
                    "sustainability_sources": ["任务", "关系"], "mid_stage_risks": ["目标单一"]
                },
                "evidence": [{"field": "growth_axes", "chapter_indexes": [2], "feature_codes": ["task_growth"]}],
                "confidence": {"level": "medium", "score": 0.74, "limitations": ["抽样有限"]}
            }
        return Response(json.dumps(payload, ensure_ascii=False))


def _snapshot():
    return build_snapshot(**json.loads((ROOT / "snapshot-input.json").read_text(encoding="utf-8")))


def _schema():
    path = Path(__file__).resolve().parents[2] / "AI-Novel-Standard" / "contracts" / "book-narrative-profile.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_consensus_merges_multiple_passes_and_preserves_snapshot_binding():
    snapshot = _snapshot(); book = query_analysis_books(snapshot)[0]
    text = (ROOT / book["relative_path"]).read_text(encoding="utf-8")
    det = DeterministicBookProfileAnalyzer().analyze(book, text, snapshot=snapshot)
    llm = LLMBookProfileAnalyzer(FakeModel())
    top = llm.analyze_pass(book, text, snapshot=snapshot, pass_type="top_down")
    bottom = llm.analyze_pass(book, text, snapshot=snapshot, pass_type="bottom_up")
    consensus = build_consensus_profile(deterministic=det, top_down=top, bottom_up=bottom, snapshot=snapshot)
    Draft202012Validator(_schema()).validate(consensus)
    assert consensus["analysis"]["method"] == "consensus"
    assert consensus["corpus_snapshot_id"] == snapshot["id"]
    assert consensus["commercial"]["first_visible_payoff_chapter"] in {1, 2}
    assert consensus["confidence"]["level"] in {"medium", "high"}
    assert len(consensus["evidence"]) >= len(det["evidence"])


def test_consensus_requires_at_least_one_completed_pass():
    snapshot = _snapshot(); book = query_analysis_books(snapshot)[0]
    text = (ROOT / book["relative_path"]).read_text(encoding="utf-8")
    det = DeterministicBookProfileAnalyzer().analyze(book, text, snapshot=snapshot)
    degraded = LLMBookProfileAnalyzer(FakeModel()).analyze_pass(book, "", snapshot=snapshot, pass_type="top_down")
    degraded["status"] = "degraded"
    degraded["confidence"]["score"] = 0.0
    try:
        build_consensus_profile(deterministic=det, top_down=degraded, bottom_up=degraded, snapshot=snapshot)
        raise AssertionError("expected failure")
    except Exception as exc:
        assert "completed analysis pass" in str(exc)
