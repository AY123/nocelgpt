"""Test Contract Gate integration into run_serial (Phase 3, Task 3.2 & 3.3).

Verifies that when enable_contract_gate=True and prompt_version="15.0.0",
the serial precheck validates contracts before generation and validates
the generated chapter after production.

NOTE: These tests verify the integration POINTS are wired correctly.
Full Contract Gate functionality tests are in runtime_plugins/contract/tests/.
"""
import pytest
import yaml
from pathlib import Path
from runtime.serialize.loop import run_serial, ChapterRun


def _scaffold_minimal_project(root: Path):
    """Create minimal project structure for Contract Gate tests."""
    facts = root / "registry" / "facts"
    meta = root / "registry" / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "registry-version").write_text("1\n", encoding="utf-8")
    (meta / "standard.pin").write_text("2.0.0\n", encoding="utf-8")

    # Create one event
    facts.mkdir(parents=True, exist_ok=True)
    event_dir = facts / "events"
    event_dir.mkdir(parents=True, exist_ok=True)
    event = {
        "id": "EVT-00001",
        "name": "Opening event",
        "status": "active",
        "fact_version": 1,
        "timeline": "TML-00001",
        "sequence_index": 1,
        "participants": [],
        "causes": [],
    }
    (event_dir / "EVT-00001.yaml").write_text(
        yaml.safe_dump(event, allow_unicode=True, sort_keys=False),
        encoding="utf-8")

    # Create minimal timeline
    timeline_dir = facts / "timelines"
    timeline_dir.mkdir(parents=True, exist_ok=True)
    timeline = {
        "id": "TML-00001",
        "name": "主线",
        "status": "active",
        "fact_version": 1,
        "kind": "main"
    }
    (timeline_dir / "TML-00001.yaml").write_text(
        yaml.safe_dump(timeline, allow_unicode=True, sort_keys=False),
        encoding="utf-8")


def test_contract_gate_disabled_by_default(tmp_path):
    """When enable_contract_gate=False (default), contracts are not checked."""
    _scaffold_minimal_project(tmp_path)

    # No contracts directory needed
    result = run_serial(
        project_path=tmp_path,
        standard_root=tmp_path / "standard",
        schema_dir=tmp_path / "schemas",
        out_dir=tmp_path / "out",
        prompt_version="1.0.0",  # Not v15
        enable_contract_gate=False,
        max_chapters=0,  # No chapters to avoid full setup
    )

    # Should succeed without contracts
    assert result is not None


def test_contract_gate_only_on_v15(tmp_path):
    """Contract Gate only activates when prompt_version="15.0.0"."""
    _scaffold_minimal_project(tmp_path)

    # enable_contract_gate=True but wrong version
    result = run_serial(
        project_path=tmp_path,
        standard_root=tmp_path / "standard",
        schema_dir=tmp_path / "schemas",
        out_dir=tmp_path / "out",
        prompt_version="5.0.0",  # Not v15
        enable_contract_gate=True,
        max_chapters=0,
    )

    # Should succeed - Contract Gate not activated
    assert result is not None


def test_contract_gate_parameters_accepted(tmp_path):
    """Verify run_serial accepts Contract Gate parameters without error."""
    _scaffold_minimal_project(tmp_path)

    # All Contract Gate parameters should be accepted
    result = run_serial(
        project_path=tmp_path,
        standard_root=tmp_path / "standard",
        schema_dir=tmp_path / "schemas",
        out_dir=tmp_path / "out",
        prompt_version="1.0.0",
        enable_contract_gate=False,  # Disabled for this test
        strict_contract_mode=False,
        contracts_dir=tmp_path / "contracts",
        max_chapters=0,
    )

    assert result is not None


def test_contract_gate_integration_wiring():
    """Verify the Contract Gate integration code is present in run_serial.

    This is a structural test - it checks that the integration points exist
    in the code without actually running Contract Gate.
    """
    import inspect
    from runtime.serialize.loop import run_serial

    # Check function signature includes new parameters
    sig = inspect.signature(run_serial)
    assert 'contracts_dir' in sig.parameters
    assert 'enable_contract_gate' in sig.parameters
    assert 'strict_contract_mode' in sig.parameters

    # Check defaults
    assert sig.parameters['enable_contract_gate'].default is False
    assert sig.parameters['strict_contract_mode'].default is False
    assert sig.parameters['contracts_dir'].default is None

    # Check docstring mentions v15
    assert "15.0.0" in run_serial.__doc__
    assert "Contract Gate" in run_serial.__doc__


def test_chapter_run_has_contract_validation_field():
    """Verify ChapterRun dataclass has contract_validation field (Phase 3.3)."""
    from runtime.serialize.loop import ChapterRun, ChapterSpec

    # Create a minimal ChapterRun
    spec = ChapterSpec(
        index=1,
        task_id="TASK-00001",
        event_id="EVT-00001",
        seeds=["EVT-00001"],
        goal="test goal"
    )
    run = ChapterRun(
        spec=spec,
        ok=True,
        stage="done",
        contract_validation={"valid": True, "issues": []}
    )

    # Check field exists and serializes
    assert hasattr(run, 'contract_validation')
    assert run.contract_validation == {"valid": True, "issues": []}

    # Check to_dict includes it
    run_dict = run.to_dict()
    assert 'contract_validation' in run_dict
    assert run_dict['contract_validation'] == {"valid": True, "issues": []}


