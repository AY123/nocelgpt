from __future__ import annotations

from runtime.cli import main


def test_cli_w12_runs_end_to_end_with_stubbed_pipeline(monkeypatch, tmp_path, capsys):
    from runtime.candidates import plan as planmod

    def fake_run_w12_fact_reflow(**kwargs):
        return {
            "plan": {"id": kwargs["plan_id"]},
            "derived_path": "registry/derived/fact-candidates/W12-00001.json",
            "draft_source": "default-resolver",
            "approval_request_id": "APR-W12-W12-00001",
            "approval_status": "pending",
            "candidate_count": 2,
            "reconciled_counts": {
                "new": 0,
                "additive": 1,
                "consistent": 0,
                "conflicting": 0,
                "unverifiable": 1,
            },
            "review_findings": [
                {"check": "entity-roster", "severity": "advisory", "message": "unresolved name"}
            ],
        }

    monkeypatch.setattr(planmod, "run_w12_fact_reflow", fake_run_w12_fact_reflow)

    code = main([
        "candidates", "w12",
        "--project", str(tmp_path),
        "--plan-id", "W12-00001",
        "--accept", "CAND-00001",
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "w12 plan   : W12-00001" in out
    assert "draft     : chapter-final" in out
    assert "source    : default-resolver" in out
    assert "approval  : APR-W12-W12-00001 [pending]" in out
    assert "additive=1" in out
    assert "review    : 1 finding(s)" in out


def test_cli_serial_30ch_preset_applies_fixed_run_profile(monkeypatch, tmp_path):
    from runtime.cli import main
    captured = {}

    def fake_run_serial(**kwargs):
        captured.update(kwargs)
        return type("R", (), {"chapters": [], "produced": 0, "skipped": 0, "gating": False, "final_state_hash": None, "llm_cost": None, "llm_usage": None})()

    def fake_write_run_manifest(**kwargs):
        return ({"id": "RUN-00001", "totals": {"cost": None, "live_calls": 0}}, "registry/derived/run-manifests/RUN-00001.json")

    def fake_write_run_aggregate(**kwargs):
        return "registry/derived/run-aggregates/RUN-00001.json"

    def fake_write_30ch_run_summary(**kwargs):
        return "registry/derived/30ch-run-summaries/RUN-00001.json"

    # Patch the SOURCE modules, not runtime.cli.* — _cmd_serial_run re-imports
    # run_serial / write_* from .serialize inside the function (the existing
    # convention the serial-cli tests rely on), so patching runtime.cli.<name>
    # would miss.
    monkeypatch.setattr("runtime.serialize.run_serial", fake_run_serial)
    monkeypatch.setattr("runtime.cli._load_dotenv", lambda _args: None)
    monkeypatch.setattr("runtime.cli.registry_loader.load", lambda _project_path: type("Reg", (), {"version": "v1", "facts": {}, "get": lambda self, _eid: None})())
    monkeypatch.setattr("runtime.approval.load_approval_queue", lambda _project_path: None)
    monkeypatch.setattr("runtime.serialize.write_run_manifest", fake_write_run_manifest)
    monkeypatch.setattr("runtime.serialize.write_run_aggregate", fake_write_run_aggregate)
    monkeypatch.setattr("runtime.serialize.write_30ch_run_summary", fake_write_30ch_run_summary)
    monkeypatch.setattr("runtime.cli.run_outline_bootstrap", lambda *a, **k: None, raising=False)

    code = main([
        "serial", "run",
        "--project", str(tmp_path),
        "--standard-root", str(tmp_path),
        "--preset", "30ch",
    ])
    assert code == 0
    assert captured["max_chapters"] == 30
    # The preset's long_arc/mandate/speech/vary_openings flags are resolved INTO
    # prompt_version="10.0.0" before run_serial is called (v10 ⊃ v9 ⊃ v8 ⊃ v7),
    # so the observable proof they applied is the resolved prompt_version — those
    # flags are not themselves run_serial kwargs.
    assert captured["prompt_version"] == "10.0.0"
    assert captured["candidate_models"] is None
    assert captured["reviewer"].reviewer_id == "unanchored-entity-reviewer-v1"


def test_cli_w12_confirm_branch_calls_mint_and_recompute(monkeypatch, tmp_path, capsys):
    from runtime.candidates import plan as planmod

    def fake_run_w12_fact_reflow(**kwargs):
        return {
            "plan": {
                "id": kwargs["plan_id"],
                "reconciled_against": ["CHR-00001@v1"],
            },
            "derived_path": "registry/derived/fact-candidates/W12-00002.json",
            "draft_source": "default-resolver",
            "approval_request_id": "APR-W12-W12-00002",
            "approval_status": "approved",
            "candidate_count": 1,
            "reconciled_counts": {
                "new": 0,
                "additive": 1,
                "consistent": 0,
                "conflicting": 0,
                "unverifiable": 0,
            },
        }

    monkeypatch.setattr(planmod, "run_w12_fact_reflow", fake_run_w12_fact_reflow)

    mint_calls = {}

    def fake_execute_mint(**kwargs):
        mint_calls["kwargs"] = kwargs
        return {
            "id": "MINT-00001",
            "minted": [{"classification": "additive"}],
            "registry_version": {"before": 1, "after": 2},
            "revalidation": {"passed": True},
        }

    def fake_execute_recompute(*args, **kwargs):
        return {"id": "RCP-00001", "impacted": ["story-state"]}

    monkeypatch.setattr("runtime.cli.execute_mint", fake_execute_mint)
    monkeypatch.setattr("runtime.cli.recompute.execute_recompute", fake_execute_recompute)

    code = main([
        "candidates", "w12",
        "--project", str(tmp_path),
        "--plan-id", "W12-00002",
        "--accept", "CAND-00001",
        "--confirm",
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "mint     : MINT-00001 facts=1" in out
    assert "recompute: RCP-00001 impacted=1" in out
    assert mint_calls["kwargs"]["confirmed"] is True
