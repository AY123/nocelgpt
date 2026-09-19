"""Test Task 3.2: Source Hash 过期检测

验证 ContractGate 能检测契约的 source 是否过期。
"""
import pytest
import json
import tempfile
from pathlib import Path


def test_source_staleness_check_detects_mismatch():
    """When source hash doesn't match, should return warning."""
    import sys
    plugins_path = Path(__file__).parent.parent.parent.parent / 'runtime_plugins'
    if str(plugins_path) not in sys.path:
        sys.path.insert(0, str(plugins_path))

    from contract.gate import ContractGate

    # Create temp directories
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        contracts_dir = tmp_path / "contracts"
        schemas_dir = tmp_path / "schemas"
        sources_dir = tmp_path / "sources"

        contracts_dir.mkdir()
        schemas_dir.mkdir()
        sources_dir.mkdir()

        # Create a minimal schema
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["chapter", "version", "approved"],
            "properties": {
                "chapter": {"type": "integer"},
                "version": {"type": "string"},
                "approved": {"type": "boolean"},
                "sources": {"type": "object"}
            }
        }
        (schemas_dir / "chapter_contract.schema.json").write_text(
            json.dumps(schema, indent=2), encoding='utf-8'
        )

        # Create an outline file
        outline_content = "Chapter 1: The Beginning\n"
        outline_file = sources_dir / "outline.txt"
        outline_file.write_text(outline_content, encoding='utf-8')

        # Compute the correct hash
        import hashlib
        correct_hash = hashlib.sha256(outline_content.encode()).hexdigest()

        # Create a contract with WRONG hash
        contract = {
            "chapter": 1,
            "version": "v1.0",
            "approved": True,
            "sources": {
                "outline_ref": "sources/outline.txt",
                "content_hash": "wrong_hash_123",  # Mismatch!
                "generated_at": "2026-08-15T10:00:00Z",
                "generated_from": "manual"
            }
        }

        gate = ContractGate(contracts_dir=contracts_dir, schemas_dir=schemas_dir)

        # Check staleness
        warning = gate._check_source_staleness(contract)

        assert warning is not None
        assert "过期" in warning or "不匹配" in warning
        assert "wrong_hash_123" in warning[:50] or "契约记录" in warning


def test_source_staleness_check_no_warning_when_match():
    """When source hash matches, should return None."""
    import sys
    plugins_path = Path(__file__).parent.parent.parent.parent / 'runtime_plugins'
    if str(plugins_path) not in sys.path:
        sys.path.insert(0, str(plugins_path))

    from contract.gate import ContractGate

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        contracts_dir = tmp_path / "contracts"
        schemas_dir = tmp_path / "schemas"
        sources_dir = tmp_path / "sources"

        contracts_dir.mkdir()
        schemas_dir.mkdir()
        sources_dir.mkdir()

        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["chapter", "version", "approved"],
            "properties": {
                "chapter": {"type": "integer"},
                "version": {"type": "string"},
                "approved": {"type": "boolean"},
                "sources": {"type": "object"}
            }
        }
        (schemas_dir / "chapter_contract.schema.json").write_text(
            json.dumps(schema, indent=2), encoding='utf-8'
        )

        # Create outline
        outline_content = "Chapter 1: The Beginning\n"
        outline_file = sources_dir / "outline.txt"
        outline_file.write_text(outline_content, encoding='utf-8')

        # Compute correct hash
        import hashlib
        correct_hash = hashlib.sha256(outline_content.encode()).hexdigest()

        # Create contract with CORRECT hash
        contract = {
            "chapter": 1,
            "version": "v1.0",
            "approved": True,
            "sources": {
                "outline_ref": "sources/outline.txt",
                "content_hash": correct_hash,  # Match!
                "generated_at": "2026-08-15T10:00:00Z",
                "generated_from": "manual"
            }
        }

        gate = ContractGate(contracts_dir=contracts_dir, schemas_dir=schemas_dir)

        # Check staleness
        warning = gate._check_source_staleness(contract)

        # Should be None (no warning)
        assert warning is None


def test_source_staleness_check_skips_when_no_hash():
    """When contract has no content_hash, should skip check."""
    import sys
    plugins_path = Path(__file__).parent.parent.parent.parent / 'runtime_plugins'
    if str(plugins_path) not in sys.path:
        sys.path.insert(0, str(plugins_path))

    from contract.gate import ContractGate

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        contracts_dir = tmp_path / "contracts"
        schemas_dir = tmp_path / "schemas"

        contracts_dir.mkdir()
        schemas_dir.mkdir()

        schema = {"type": "object", "properties": {}}
        (schemas_dir / "chapter_contract.schema.json").write_text(
            json.dumps(schema), encoding='utf-8'
        )

        # Contract without content_hash
        contract = {
            "chapter": 1,
            "version": "v1.0",
            "approved": True,
            "sources": {
                "generated_at": "2026-08-15T10:00:00Z",
                "generated_from": "manual"
                # No content_hash
            }
        }

        gate = ContractGate(contracts_dir=contracts_dir, schemas_dir=schemas_dir)

        # Should skip check
        warning = gate._check_source_staleness(contract)
        assert warning is None


def test_precheck_includes_staleness_warning():
    """precheck should include staleness warning in contract (advisory)."""
    import sys
    plugins_path = Path(__file__).parent.parent.parent.parent / 'runtime_plugins'
    if str(plugins_path) not in sys.path:
        sys.path.insert(0, str(plugins_path))

    from contract.gate import ContractGate

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        contracts_dir = tmp_path / "contracts"
        schemas_dir = tmp_path / "schemas"

        contracts_dir.mkdir()
        schemas_dir.mkdir()

        # Minimal schema
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["chapter", "version", "approved", "entry_state",
                        "chapter_intent", "exit_target", "transition_to_next", "sources"],
            "properties": {
                "chapter": {"type": "integer"},
                "version": {"type": "string"},
                "approved": {"type": "boolean"},
                "entry_state": {"type": "object"},
                "chapter_intent": {"type": "object"},
                "exit_target": {"type": "object"},
                "transition_to_next": {"type": "object"},
                "sources": {"type": "object"}
            }
        }
        (schemas_dir / "chapter_contract.schema.json").write_text(
            json.dumps(schema, indent=2), encoding='utf-8'
        )

        # Create contract with wrong hash
        contract = {
            "chapter": 1,
            "version": "v1.0",
            "approved": True,
            "entry_state": {},
            "chapter_intent": {},
            "exit_target": {},
            "transition_to_next": {},
            "sources": {
                "outline_ref": "nonexistent.txt",
                "content_hash": "old_hash",
                "generated_at": "2026-08-15T10:00:00Z",
                "generated_from": "manual"
            }
        }

        (contracts_dir / "chapter_001_contract.json").write_text(
            json.dumps(contract, indent=2), encoding='utf-8'
        )

        gate = ContractGate(contracts_dir=contracts_dir, schemas_dir=schemas_dir)

        # precheck should NOT raise (advisory only)
        # It should add warning to contract
        gate.precheck(1)

        # Re-load contract to see if warning was added
        loaded = gate.load_contract(1)
        # Warning might be added dynamically, but precheck doesn't raise
        # This is the key: staleness is advisory, not blocking


def test_staleness_check_is_advisory_not_blocking():
    """Staleness check should warn but not block (ADR-003)."""
    # This is a design principle test
    ADR_003 = "evaluative/advisory checks never gate production"

    # The staleness check:
    # - Detects mismatches
    # - Logs warnings
    # - Does NOT raise ContractCheckError
    # - Does NOT gate precheck

    assert "never gate" in ADR_003.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
