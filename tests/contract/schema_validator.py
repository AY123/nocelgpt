"""JSON Schema validation utilities for contract tests.

This module provides schema validation helpers that are intentionally
separated from the domain layer to avoid introducing jsonschema as a
runtime dependency.
"""

import json
from pathlib import Path
from typing import Any


def validate_against_schema(data: dict[str, Any]) -> None:
    """
    Validate serialized Character against character.schema.json.

    Args:
        data: Serialized Character dict

    Raises:
        ValueError: If validation fails

    Contract: character.schema.json compliance
    """
    import jsonschema

    # Path from tests/contract/ to specs/schemas/
    schema_path = (
        Path(__file__).parent.parent.parent
        / "specs"
        / "schemas"
        / "character.schema.json"
    )
    with open(schema_path) as f:
        schema = json.load(f)

    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise ValueError(f"Schema validation failed: {e.message}") from e
