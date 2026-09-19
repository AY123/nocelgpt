import json
from pathlib import Path

from jsonschema import Draft202012Validator

from runtime.corpus import build_snapshot, query_analysis_books
from runtime.narrative_mining import LLMBookProfileAnalyzer, write_analysis_pass

ROOT = Path(__file__).parent / "fixtures" / "corpus-xuanhuan-10"


class Response:
    def __init__(self, text): self.text = text


class FakeModel:
    def __init__(self, payload=None, error=None):
        self.payload, self.error, self.prompts = payload, error, []
    def generate(self, prompt):
        self.prompts.append(prompt)
        if self.error: raise self.error
        return Response(json.dumps(self.payload, ensure_ascii=False))


def _snapshot():
    return build_snapshot(**json.loads((ROOT / "snapshot-input.json").read_text(encoding="utf-8")))


def _payload():
    return {
        "findings": {
            "core_fantasy": "受限能力带来可积累优势", "target_reader": ["升级流读者"],
            "selling_point": "每次选择都在收益与代价之间交易", "protagonist_deficit": "资源不足",
            "long_term_desire": "获得稳定行动权", "core_ability": "读取局部风险",
            "limitations": ["每天只能使用一次"], "growth_axes": ["能力", "身份"],
            "first_visible_payoff_chapter": 1, "first_volume_promise": "完成第一次公开破局",
            "sustainability_sources": ["能力限制升级", "势力关系"], "mid_stage_risks": ["能力解释重复"]
        },
        "evidence": [{"field": "core_ability", "chapter_indexes": [1], "feature_codes": ["bounded_ability"]}],
        "confidence": {"level": "medium", "score": 0.72, "limitations": ["仅分析抽样章节"]}
    }


def _schema():
    path = Path(__file__).resolve().parents[2] / "AI-Novel-Standard" / "contracts" / "book-profile-analysis-pass.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_two_passes_are_independent_schema_valid_and_snapshot_bound(tmp_path):
    snapshot = _snapshot(); book = query_analysis_books(snapshot)[0]
    text = (ROOT / book["relative_path"]).read_text(encoding="utf-8")
    model = FakeModel(_payload()); analyzer = LLMBookProfileAnalyzer(model)
    top = analyzer.analyze_pass(book, text, snapshot=snapshot, pass_type="top_down")
    bottom = analyzer.analyze_pass(book, text, snapshot=snapshot, pass_type="bottom_up")
    Draft202012Validator(_schema()).validate(top); Draft202012Validator(_schema()).validate(bottom)
    assert top["id"] != bottom["id"] and top["status"] == bottom["status"] == "completed"
    assert top["corpus_manifest_hash"] == snapshot["manifest_hash"]
    assert "自上而下" in model.prompts[0] and "自下而上" in model.prompts[1]
    assert write_analysis_pass(tmp_path, top).endswith("/top_down.json")
    assert write_analysis_pass(tmp_path, bottom).endswith("/bottom_up.json")


def test_model_failure_degrades_without_overwriting_other_pass():
    snapshot = _snapshot(); book = query_analysis_books(snapshot)[0]
    result = LLMBookProfileAnalyzer(FakeModel(error=RuntimeError("offline"))).analyze_pass(book, "合成文本", snapshot=snapshot, pass_type="top_down")
    Draft202012Validator(_schema()).validate(result)
    assert result["status"] == "degraded" and result["confidence"]["score"] == 0


def test_invalid_or_prose_bearing_evidence_degrades():
    snapshot = _snapshot(); book = query_analysis_books(snapshot)[0]
    payload = _payload(); payload["evidence"][0]["excerpt"] = "不应保存的原文"
    result = LLMBookProfileAnalyzer(FakeModel(payload)).analyze_pass(book, "合成文本", snapshot=snapshot, pass_type="bottom_up")
    assert result["status"] == "degraded"
    assert "不应保存的原文" not in json.dumps(result, ensure_ascii=False)
