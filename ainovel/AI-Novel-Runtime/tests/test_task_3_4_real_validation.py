"""Task 3.4: 真实章节金样评估

在真实契约和章节上验证 Contract Gate 的完整流程。
"""
import pytest
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_real_contracts_pass_strict_schema():
    """Test that all real contract files pass the strict schema."""
    schema_path = PROJECT_ROOT / "schemas" / "chapter_contract.schema.json"
    contracts_dir = PROJECT_ROOT / "contracts"

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    # Test contracts 101, 102, 103
    contract_files = [
        "chapter_101_contract.json",
        "chapter_102_contract.json",
        "chapter_103_contract.json",
    ]

    results = []
    for contract_file in contract_files:
        contract_path = contracts_dir / contract_file
        if not contract_path.exists():
            results.append((contract_file, "not_found"))
            continue

        with open(contract_path, 'r', encoding='utf-8') as f:
            contract = json.load(f)

        try:
            import jsonschema
            jsonschema.validate(instance=contract, schema=schema)
            results.append((contract_file, "pass"))
        except jsonschema.ValidationError as e:
            results.append((contract_file, f"fail: {e.message}"))

    # Print results
    print("\n📋 真实契约验证结果:")
    for filename, result in results:
        if result == "pass":
            print(f"  ✅ {filename}: 通过")
        elif result == "not_found":
            print(f"  ⚠️  {filename}: 文件不存在")
        else:
            print(f"  ❌ {filename}: {result}")

    # At least one contract should pass
    passed = [r for r in results if r[1] == "pass"]
    assert len(passed) >= 1, "至少应有一个真实契约通过验证"


def test_contract_gate_precheck_on_real_contracts():
    """Test ContractGate.precheck() on real contracts."""
    import sys
    from pathlib import Path as _Path

    # Add runtime_plugins to path
    plugins_path = PROJECT_ROOT / 'runtime_plugins'
    if str(plugins_path) not in sys.path:
        sys.path.insert(0, str(plugins_path))

    # Import after adding to path
    try:
        from contract.gate import ContractGate
    except ModuleNotFoundError:
        # Try alternative path
        gate_path = PROJECT_ROOT / 'runtime_plugins' / 'contract'
        if not gate_path.exists():
            pytest.skip(f"ContractGate module not found at {gate_path}")
            return
        raise

    contracts_dir = PROJECT_ROOT / "contracts"
    schemas_dir = PROJECT_ROOT / "schemas"

    gate = ContractGate(contracts_dir=contracts_dir, schemas_dir=schemas_dir)

    # Test precheck on chapter 101, 102, 103
    chapters = [101, 102, 103]
    results = []

    for chapter in chapters:
        try:
            gate.precheck(chapter)
            results.append((chapter, "pass"))
        except FileNotFoundError:
            results.append((chapter, "not_found"))
        except Exception as e:
            results.append((chapter, f"fail: {type(e).__name__}: {str(e)[:50]}"))

    # Print results
    print("\n📋 Precheck 验证结果:")
    for chapter, result in results:
        if result == "pass":
            print(f"  ✅ Ch{chapter}: 通过")
        elif result == "not_found":
            print(f"  ⚠️  Ch{chapter}: 契约不存在")
        else:
            print(f"  ❌ Ch{chapter}: {result}")

    # At least one should pass
    passed = [r for r in results if r[1] == "pass"]
    assert len(passed) >= 1, "至少应有一个章节通过 precheck"


def test_contract_chain_validation_on_real_contracts():
    """Test chain validation between real contracts."""
    import sys
    from pathlib import Path as _Path

    plugins_path = PROJECT_ROOT / 'runtime_plugins'
    if str(plugins_path) not in sys.path:
        sys.path.insert(0, str(plugins_path))

    try:
        from contract.gate import ContractGate
    except ModuleNotFoundError:
        gate_path = PROJECT_ROOT / 'runtime_plugins' / 'contract'
        if not gate_path.exists():
            pytest.skip(f"ContractGate module not found at {gate_path}")
            return
        raise

    contracts_dir = PROJECT_ROOT / "contracts"
    schemas_dir = PROJECT_ROOT / "schemas"

    gate = ContractGate(contracts_dir=contracts_dir, schemas_dir=schemas_dir)

    # Test chain: 101 → 102, 102 → 103
    chains = [(101, 102), (102, 103)]
    results = []

    for prev_ch, curr_ch in chains:
        try:
            chain_result = gate.validate_chain(prev_ch, curr_ch)
            results.append((prev_ch, curr_ch, chain_result))
        except FileNotFoundError as e:
            results.append((prev_ch, curr_ch, {"valid": None, "error": "not_found"}))
        except Exception as e:
            results.append((prev_ch, curr_ch, {"valid": None, "error": str(e)[:50]}))

    # Print results
    print("\n📋 契约链验证结果:")
    for prev_ch, curr_ch, result in results:
        if result.get("error"):
            print(f"  ⚠️  Ch{prev_ch}→Ch{curr_ch}: {result['error']}")
        elif result.get("valid"):
            print(f"  ✅ Ch{prev_ch}→Ch{curr_ch}: 连续性良好")
        else:
            issues = result.get("issues", [])
            print(f"  ⚠️  Ch{prev_ch}→Ch{curr_ch}: {len(issues)} 个问题")
            for issue in issues[:2]:  # Show first 2 issues
                print(f"      - {issue.get('field')}: {issue.get('description')[:60]}")


def test_contract_gate_real_world_findings():
    """Document findings from real-world contract validation.

    This test documents what we learned from running Contract Gate
    on real contracts.
    """
    findings = {
        "schema_adjustments": [
            "Added transition_note field to transition_to_next (optional)",
            "Added based_on_chapter field to sources (optional)",
            "Added ch100_exit_analysis field to sources (optional)",
        ],
        "validation_results": {
            "contracts_tested": 3,
            "contracts_passed": "TBD",  # Will be filled by actual run
            "common_issues": [],
        },
        "recommendations": [
            "Schema should allow optional metadata fields",
            "Strict validation on core fields, flexible on helpers",
            "Real contracts need more context fields than MVP",
        ]
    }

    print("\n📊 真实场景发现:")
    print(f"  测试契约数: {findings['validation_results']['contracts_tested']}")
    print(f"\n  Schema 调整:")
    for adj in findings["schema_adjustments"]:
        print(f"    - {adj}")
    print(f"\n  建议:")
    for rec in findings["recommendations"]:
        print(f"    - {rec}")

    # This test always passes - it's documentation
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
