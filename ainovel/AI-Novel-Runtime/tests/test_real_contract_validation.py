"""Test real contract files against strict schema (Task 3.4).

Validates existing contract files to see if they pass the strict schema.
"""
import json
import jsonschema
from pathlib import Path
import pytest  # P0-4: Add pytest import


def test_real_contract_101_against_strict_schema():
    """Test chapter_101_contract.json against strict schema."""
    schema_path = Path(__file__).parent.parent.parent / "schemas" / "chapter_contract.schema.json"
    contract_path = Path(__file__).parent.parent.parent / "contracts" / "chapter_101_contract.json"

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    with open(contract_path, 'r', encoding='utf-8') as f:
        contract = json.load(f)

    # This will likely fail due to extra fields in transition_to_next and sources
    try:
        jsonschema.validate(instance=contract, schema=schema)
        print("✅ Contract 101 passes strict schema")
        assert True  # P0-4: Use assert instead of return
    except jsonschema.ValidationError as e:
        print(f"❌ Contract 101 fails strict schema:")
        print(f"   Field: {'.'.join(str(p) for p in e.path)}")
        print(f"   Error: {e.message}")
        pytest.fail(f"Contract validation failed: {e.message}")  # P0-4: Use pytest.fail instead of return


if __name__ == "__main__":
    test_real_contract_101_against_strict_schema()
