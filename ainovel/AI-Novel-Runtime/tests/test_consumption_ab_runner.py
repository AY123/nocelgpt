import json
from pathlib import Path

from runtime.consumption_ab_runner import run_live_consumption_ab
from runtime.execution.model import ModelOutput


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
PROJECT = ROOT / "tests" / "fixtures" / "live-baseline-5ch"
PACKAGE = (ROOT / "tests" / "fixtures" / "live-baseline-5ch"
           / "build-assistant-92code-5ch" / "TASK-00005.package.json")
STANDARD = REPO / "AI-Novel-Standard"
SCHEMA = STANDARD / "phase-1" / "generated" / "json-schema"


class _PromptAwareModel:
    provider = "fake"
    model_id = "prompt-aware-v1"

    def generate(self, prompt):
        marker = "赤纹星钥" if "赤纹星钥" in prompt else "空手"
        return ModelOutput(
            text=(f"林照夜{marker}踏入石门，迎面挡住追兵。"
                  "他没有等待援手，而是借石壁回声判断敌人的位置，"
                  "随后改变路线，把危险引向废弃长廊。"),
            model_id=self.model_id, model_kind="llm")


def test_live_runner_executes_isolated_mint_recompute_and_two_arms(tmp_path):
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    out = tmp_path / "ab-run"

    report = run_live_consumption_ab(
        project_path=PROJECT, package=package,
        standard_root=STANDARD, schema_dir=SCHEMA, output_dir=out,
        model_without=_PromptAwareModel(), model_with=_PromptAwareModel(),
        fact_name="赤纹星钥", confirmed=True, actor="test-human")

    assert report["all_criteria_met"] is True
    assert all(report["criteria"].values())
    assert report["criteria"]["approved_facts_absent_without"] is True
    assert report["criteria"]["approved_facts_reflected"] is True
    assert report["live_provenance"]["arms_isolated"] is True
    assert report["live_provenance"]["source_project_mutated"] is False
    assert report["arm_without"]["prompt_rendered_hash"] != report["arm_with"]["prompt_rendered_hash"]
    for name in (
        "consumption-ab-report.json", "arm-without.json", "arm-with.json",
        "fact-plan.json", "mint-receipt.json", "recompute-report.json",
        "run-state.json",
    ):
        assert (out / name).is_file()
    run_state = json.loads((out / "run-state.json").read_text(encoding="utf-8"))
    assert run_state == {"phase": "report", "status": "completed"}
    receipt = json.loads((out / "mint-receipt.json").read_text(encoding="utf-8"))
    assert receipt["authorized"]["confirmed"] is True
    assert receipt["minted"][0]["classification"] == "new"
    assert receipt["minted"][0]["value"] == "赤纹星钥"


def test_live_runner_requires_explicit_confirmation(tmp_path):
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    try:
        run_live_consumption_ab(
            project_path=PROJECT, package=package,
            standard_root=STANDARD, schema_dir=SCHEMA,
            output_dir=tmp_path / "refused",
            model_without=_PromptAwareModel(), model_with=_PromptAwareModel(),
            fact_name="赤纹星钥", confirmed=False)
        assert False, "expected explicit confirmation refusal"
    except ValueError as exc:
        assert "explicit mint confirmation" in str(exc)


def test_live_runner_checkpoints_model_failure(tmp_path):
    class _BrokenModel(_PromptAwareModel):
        def generate(self, prompt):
            raise TimeoutError("provider timed out")

    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    out = tmp_path / "failed-run"
    try:
        run_live_consumption_ab(
            project_path=PROJECT, package=package,
            standard_root=STANDARD, schema_dir=SCHEMA, output_dir=out,
            model_without=_BrokenModel(), model_with=_PromptAwareModel(),
            fact_name="赤纹星钥", confirmed=True)
        assert False, "expected provider failure"
    except TimeoutError:
        pass

    run_state = json.loads((out / "run-state.json").read_text(encoding="utf-8"))
    assert run_state["status"] == "failed"
    assert run_state["phase"] == "arm_without"
    assert run_state["error"]["type"] == "TimeoutError"
    assert "provider timed out" in run_state["error"]["message"]
