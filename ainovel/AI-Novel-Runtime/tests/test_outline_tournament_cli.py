from runtime import cli


def test_outline_cli_accepts_repeatable_tournament_models(monkeypatch, tmp_path):
    captured = {}

    def fake_command(args):
        captured["models"] = args.tournament_model
        return 0

    monkeypatch.setattr(cli, "_outline_bootstrap", fake_command)
    result = cli.main([
        "outline", "bootstrap",
        "--project", str(tmp_path),
        "--tournament-model", "92code:gpt-5.6-sol",
        "--tournament-model", "claude:claude-opus-5",
    ])
    assert result == 0
    assert captured["models"] == [
        "92code:gpt-5.6-sol", "claude:claude-opus-5"]


def test_outline_cli_accepts_independent_outline_qa_model(monkeypatch, tmp_path):
    captured = {}

    def fake_command(args):
        captured["model"] = args.outline_qa_model
        return 0

    monkeypatch.setattr(cli, "_outline_bootstrap", fake_command)
    result = cli.main([
        "outline", "bootstrap",
        "--project", str(tmp_path),
        "--outline-qa-model", "claude:claude-opus-5",
    ])
    assert result == 0
    assert captured["model"] == "claude:claude-opus-5"


def test_outline_cli_builds_qa_model_separately_from_generation(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from runtime.execution import llm_model

    built = []
    captured = {}

    class FakeModel:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            built.append(self)

    def fake_bootstrap(project, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            ok=True,
            message="done",
            run_dir="run",
            outline_json="outline.json",
            outline_markdown="outline.md",
            import_plan_json="import.json",
            errors=[],
        )

    monkeypatch.setattr(llm_model, "LLMExecutionModel", FakeModel)
    monkeypatch.setattr(cli, "run_outline_bootstrap", fake_bootstrap)

    result = cli.main([
        "outline", "bootstrap",
        "--project", str(tmp_path),
        "--outline-qa-model", "claude:claude-opus-5",
    ])

    assert result == 0
    assert captured["model"] is None
    assert captured["judge_models"] is None
    assert captured["outline_qa_model"] is built[0]
    assert built[0].kwargs["provider"] == "claude"
    assert built[0].kwargs["model_id"] == "claude-opus-5"
    assert built[0].kwargs["stream"] is False
