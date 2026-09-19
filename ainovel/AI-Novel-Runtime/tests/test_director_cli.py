from __future__ import annotations

import json

from runtime import cli


def test_director_cli_accepts_live_consumption_ab_arguments(monkeypatch, tmp_path):
    captured = {}

    def fake_command(args):
        captured.update({
            "project": args.project,
            "package": args.package,
            "out": args.out,
            "fact_name": args.fact_name,
            "confirmed": args.confirm_mint,
            "provider": args.model_provider,
            "model": args.model_id,
        })
        return 0

    monkeypatch.setattr(cli, "_cmd_director_consumption_ab", fake_command)
    result = cli.main([
        "director", "consumption-ab",
        "--project", str(tmp_path / "project"),
        "--package", str(tmp_path / "package.json"),
        "--out", str(tmp_path / "out"),
        "--fact-name", "赤纹星钥",
        "--confirm-mint",
        "--model-provider", "92code",
        "--model-id", "gpt-5.6-sol",
    ])
    assert result == 0
    assert captured["fact_name"] == "赤纹星钥"
    assert captured["confirmed"] is True
    assert captured["provider"] == "92code"
    assert captured["model"] == "gpt-5.6-sol"


def test_director_plan_cli_emits_schema_valid_objective(capsys):
    result = cli.main([
        "director", "plan", "--chapter", "TASK-00018",
        "--narrative-ir-id", "NIR-00012",
    ])

    assert result == 0
    objective = json.loads(capsys.readouterr().out)
    assert objective["kind"] == "chapter_objective"
    assert objective["chapter_id"] == "TASK-00018"
    assert objective["source"]["narrative_ir_id"] == "NIR-00012"


def test_director_brief_cli_consumes_plan_artifact(tmp_path, capsys):
    objective_path = tmp_path / "objective.json"
    objective_path.write_text(json.dumps({
        "id": "OBJ-00018",
        "kind": "chapter_objective",
        "authority": "human",
        "gating": False,
        "schema_version": "1.0",
        "objective_id": "OBJ-00018",
        "chapter_id": "TASK-00018",
        "source": {},
        "primary_goal": "推进冲突",
        "secondary_goals": [],
        "reader_question": "主角如何破局？",
        "promise_to_deliver": [],
        "character_focus": [],
        "plot_threads": [],
        "commercial_intent": {
            "retention_focus": "next_chapter_pull",
            "payoff_type": "partial_payoff",
            "drop_risk_target": "low",
        },
        "pacing_role": "rising_action",
        "cliffhanger_type": "reveal",
        "constraints": [],
        "success_criteria": [],
        "notes": "",
    }, ensure_ascii=False), encoding="utf-8")

    result = cli.main([
        "director", "brief", "--chapter", "TASK-00018",
        "--objective", str(objective_path),
    ])

    assert result == 0
    brief = json.loads(capsys.readouterr().out)
    assert brief["kind"] == "director_brief"
    assert brief["chapter_id"] == "TASK-00018"
    assert brief["objective_ref"] == "OBJ-00018"


def test_director_compare_can_wrap_character_pairwise_as_sibling(
        monkeypatch, tmp_path, capsys):
    class FakeJudgeModel:
        model_id = "fake-character-judge"
        provider = "fake"

        def __init__(self, **kwargs):
            pass

        def generate(self, prompt):
            winner = "A" if "甲稿更强" in prompt.split("<<<A>>>", 1)[1].split("<<<END A>>>", 1)[0] else "B"
            text = json.dumps({
                "character_consistency": {"winner": winner, "evidence": "人物动机连续"},
                "character_growth": {"winner": winner, "evidence": "变化可追踪"},
            }, ensure_ascii=False)
            return type("Out", (), {"text": text, "model_id": self.model_id})()

    import runtime.execution.llm_model as llm_model
    monkeypatch.setattr(llm_model, "LLMExecutionModel", FakeJudgeModel)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps({
        "version_id": "baseline", "after_text": "普通甲稿"}), encoding="utf-8")
    second.write_text(json.dumps({
        "version_id": "deepened", "after_text": "甲稿更强"}), encoding="utf-8")

    result = cli.main([
        "director", "compare", "--chapter", "TASK-00018",
        "--versions", str(first), str(second),
        "--character-judge", "fake:fake-character-judge",
    ])

    assert result == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["kind"] == "director_comparison_envelope"
    assert envelope["comparison"]["kind"] == "version_comparison"
    assert envelope["character_pairwise"]["winner"] == "b"
    assert envelope["character_pairwise"]["label_b"] == "deepened"
    assert envelope["gating"] is False
    assert envelope["comparison_only"] is True
