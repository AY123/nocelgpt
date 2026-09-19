"""test_stage_a_cli_integration.py — Stage A CLI parameter integration test.

Verifies that the new --enable-final-quality-review and
--enable-final-reader-simulation flags are properly wired from CLI to run_serial.
"""
import sys
from pathlib import Path


def test_stage_a_cli_help_includes_new_parameters():
    """Verify Stage A parameters appear in CLI help."""
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "runtime.cli", "serial", "run", "--help"],
        capture_output=True,
        text=True,
    )

    help_text = result.stdout

    # Check that Stage A parameters are in the help
    assert "--enable-final-quality-review" in help_text, \
        "Help should include --enable-final-quality-review"
    assert "--final-review-threshold" in help_text, \
        "Help should include --final-review-threshold"
    assert "--enable-final-reader-simulation" in help_text, \
        "Help should include --enable-final-reader-simulation"
    assert "--final-reader-threshold" in help_text, \
        "Help should include --final-reader-threshold"

    # Check that Stage A is mentioned in the help text
    assert "Stage A Phase 2" in help_text, \
        "Help should mention Stage A Phase 2"
    assert "Stage A Phase 3" in help_text, \
        "Help should mention Stage A Phase 3"


def test_run_serial_function_signature_includes_stage_a_params():
    """Verify run_serial function signature includes Stage A parameters."""
    from runtime.serialize.loop import run_serial
    import inspect

    sig = inspect.signature(run_serial)
    params = sig.parameters

    # Check that Stage A parameters exist in the function signature
    assert "enable_final_quality_review" in params, \
        "run_serial should have enable_final_quality_review parameter"
    assert "final_review_threshold" in params, \
        "run_serial should have final_review_threshold parameter"
    assert "enable_final_reader_simulation" in params, \
        "run_serial should have enable_final_reader_simulation parameter"
    assert "final_reader_threshold" in params, \
        "run_serial should have final_reader_threshold parameter"

    # Check default values
    assert params["enable_final_quality_review"].default is False, \
        "enable_final_quality_review default should be False"
    assert params["final_review_threshold"].default == "always", \
        "final_review_threshold default should be 'always'"
    assert params["enable_final_reader_simulation"].default is False, \
        "enable_final_reader_simulation default should be False"
    assert params["final_reader_threshold"].default == "commercial-revised", \
        "final_reader_threshold default should be 'commercial-revised'"


def test_stage_a_parameters_used_in_loop():
    """Verify Stage A parameters are actually used in the loop code."""
    loop_file = Path(__file__).parent.parent / "runtime" / "serialize" / "loop.py"
    content = loop_file.read_text(encoding="utf-8")

    # Check that the TODO comments have been removed (parameters are wired)
    assert "TODO: wire CLI flag --enable-final-quality-review" not in content, \
        "TODO for enable_final_quality_review should be removed"
    assert "TODO: wire CLI flag --enable-final-reader-simulation" not in content, \
        "TODO for enable_final_reader_simulation should be removed"

    # Check that parameters are used in conditions
    assert "if enable_final_quality_review and final_review_model" in content, \
        "enable_final_quality_review should be used in condition"
    assert "if enable_final_reader_simulation and final_reader_sim_model" in content, \
        "enable_final_reader_simulation should be used in condition"

    # Check that threshold parameters are used
    assert "final_review_threshold" in content, \
        "final_review_threshold should be referenced in code"
    assert "final_reader_threshold" in content, \
        "final_reader_threshold should be referenced in code"
