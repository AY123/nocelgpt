"""Test Task 2.4: Schema 严格化.

Verifies that the chapter_contract schema is properly strict:
1. Nested objects have additionalProperties: false
2. Required fields are enforced
3. Schema rejects invalid contracts
"""
import pytest
import json
import jsonschema
from pathlib import Path


@pytest.fixture
def schema():
    """Load the chapter_contract schema."""
    schema_path = Path(__file__).parent.parent.parent / "schemas" / "chapter_contract.schema.json"
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture
def valid_contract():
    """A valid minimal contract."""
    return {
        "chapter": 1,
        "version": "v1.0",
        "approved": True,
        "entry_state": {
            "location_id": "loc_city_square",
            "time_relation": "immediate",
            "pov": "段奕尘"
        },
        "chapter_intent": {
            "objective": "建立世界观",
            "main_conflict": "主角与环境的冲突"
        },
        "exit_target": {
            "location_id": "loc_city_square",
            "hook_id": "hook_001_01",
            "hook_promise": "远处传来不祥的声音"
        },
        "transition_to_next": {
            "scene_continuity": "immediate"
        },
        "sources": {
            "generated_at": "2026-08-15T10:00:00Z",
            "generated_from": "manual"
        }
    }


def test_schema_has_top_level_additional_properties_false(schema):
    """Top level should have additionalProperties: false."""
    assert schema.get("additionalProperties") is False


def test_schema_nested_objects_have_additional_properties_false(schema):
    """All nested objects should have additionalProperties: false."""
    nested_objects = [
        "entry_state",
        "chapter_intent",
        "exit_target",
        "transition_to_next",
        "sources"
    ]

    for obj_name in nested_objects:
        obj_schema = schema["properties"][obj_name]
        assert obj_schema.get("additionalProperties") is False, \
            f"{obj_name} should have additionalProperties: false"


def test_valid_contract_passes(schema, valid_contract):
    """A valid contract should pass validation."""
    # Should not raise
    jsonschema.validate(instance=valid_contract, schema=schema)


def test_top_level_extra_field_rejected(schema, valid_contract):
    """Extra fields at top level should be rejected."""
    invalid = valid_contract.copy()
    invalid["extra_field"] = "not allowed"

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    # The error message contains "Additional properties" (capital A)
    assert "additional properties" in str(exc.value).lower()


def test_entry_state_extra_field_rejected(schema, valid_contract):
    """Extra fields in entry_state should be rejected."""
    invalid = valid_contract.copy()
    invalid["entry_state"]["extra_field"] = "not allowed"

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    assert "additional properties" in str(exc.value).lower()


def test_chapter_intent_extra_field_rejected(schema, valid_contract):
    """Extra fields in chapter_intent should be rejected."""
    invalid = valid_contract.copy()
    invalid["chapter_intent"]["extra_field"] = "not allowed"

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    assert "additional properties" in str(exc.value).lower()


def test_exit_target_extra_field_rejected(schema, valid_contract):
    """Extra fields in exit_target should be rejected."""
    invalid = valid_contract.copy()
    invalid["exit_target"]["extra_field"] = "not allowed"

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    assert "additional properties" in str(exc.value).lower()


def test_transition_to_next_extra_field_rejected(schema, valid_contract):
    """Extra fields in transition_to_next should be rejected."""
    invalid = valid_contract.copy()
    invalid["transition_to_next"]["extra_field"] = "not allowed"

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    assert "additional properties" in str(exc.value).lower()


def test_sources_extra_field_rejected(schema, valid_contract):
    """Extra fields in sources should be rejected."""
    invalid = valid_contract.copy()
    invalid["sources"]["extra_field"] = "not allowed"

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    assert "additional properties" in str(exc.value).lower()


def test_chapter_intent_requires_objective(schema, valid_contract):
    """chapter_intent must have objective field."""
    invalid = valid_contract.copy()
    del invalid["chapter_intent"]["objective"]

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    assert "objective" in str(exc.value).lower() or "required" in str(exc.value).lower()


def test_chapter_intent_requires_main_conflict(schema, valid_contract):
    """chapter_intent must have main_conflict field."""
    invalid = valid_contract.copy()
    del invalid["chapter_intent"]["main_conflict"]

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    assert "main_conflict" in str(exc.value).lower() or "required" in str(exc.value).lower()


def test_exit_target_requires_hook_promise(schema, valid_contract):
    """exit_target must have hook_promise field."""
    invalid = valid_contract.copy()
    del invalid["exit_target"]["hook_promise"]

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    assert "hook_promise" in str(exc.value).lower() or "required" in str(exc.value).lower()


def test_sources_requires_generated_at(schema, valid_contract):
    """sources must have generated_at field."""
    invalid = valid_contract.copy()
    del invalid["sources"]["generated_at"]

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    assert "generated_at" in str(exc.value).lower() or "required" in str(exc.value).lower()


def test_sources_requires_generated_from(schema, valid_contract):
    """sources must have generated_from field."""
    invalid = valid_contract.copy()
    del invalid["sources"]["generated_from"]

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    assert "generated_from" in str(exc.value).lower() or "required" in str(exc.value).lower()


def test_objective_cannot_be_empty(schema, valid_contract):
    """objective must have minLength 1."""
    invalid = valid_contract.copy()
    invalid["chapter_intent"]["objective"] = ""

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    # minLength validation


def test_hook_promise_cannot_be_empty(schema, valid_contract):
    """hook_promise must have minLength 1."""
    invalid = valid_contract.copy()
    invalid["exit_target"]["hook_promise"] = ""

    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(instance=invalid, schema=schema)

    # minLength validation


def test_schema_strictness_prevents_typos(schema, valid_contract):
    """Strict schema helps catch typos in field names."""
    # Common typo: "objectives" instead of "objective"
    invalid = valid_contract.copy()
    del invalid["chapter_intent"]["objective"]
    invalid["chapter_intent"]["objectives"] = "typo"  # Wrong field name

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=invalid, schema=schema)


def test_required_fields_comprehensive(schema):
    """Verify all expected required fields are marked as required."""
    # Top level
    assert set(schema["required"]) == {
        "chapter", "version", "approved", "entry_state",
        "chapter_intent", "exit_target", "transition_to_next", "sources"
    }

    # Nested required fields
    assert set(schema["properties"]["entry_state"]["required"]) == {
        "location_id", "time_relation", "pov"
    }

    assert set(schema["properties"]["chapter_intent"]["required"]) == {
        "objective", "main_conflict"
    }

    assert set(schema["properties"]["exit_target"]["required"]) == {
        "location_id", "hook_id", "hook_promise"
    }

    assert set(schema["properties"]["transition_to_next"]["required"]) == {
        "scene_continuity"
    }

    assert set(schema["properties"]["sources"]["required"]) == {
        "generated_at", "generated_from"
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
