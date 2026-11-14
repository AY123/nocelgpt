"""Inert, version-pinned closed schema for structured progression facts."""

from hashlib import sha256

from anovel.canon.identity import canonical_bytes

PROGRESSION_NAMESPACE = "fantasy.progression"
PROGRESSION_VERSION = "1.0.0"
PROGRESSION_SCHEMA_ID = (
    "https://anovel.dev/genres/fantasy.progression/1.0.0/schema.json"
)


def _object(fields: dict[str, object]) -> dict[str, object]:
    return {
        "type": "object",
        "required": list(fields),
        "properties": fields,
        "additionalProperties": False,
    }


def _ref() -> dict[str, str]:
    return {"$ref": "#/$defs/entity_id"}


def _quantity() -> dict[str, object]:
    return {"type": "integer", "minimum": 0}


def _positive() -> dict[str, object]:
    return {"type": "integer", "minimum": 1}


def _text() -> dict[str, str]:
    return {"type": "string", "pattern": "\\S"}


PROGRESSION_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": PROGRESSION_SCHEMA_ID,
    "title": "Eastern fantasy progression state 1.0.0",
    "description": "Closed structural input only. Strict integer types, registered references, consecutive realm ranks, immutable rules, before-state prerequisites and exact actor-specific costs require the compiled validator. This schema does not interpret prose or grant Canon write authority.",
    **_object(
        {
            "kind": {"const": "EASTERN_PROGRESSION_STATE"},
            "schema_version": {"const": PROGRESSION_VERSION},
            **{
                name: {
                    "type": "array",
                    "items": {"$ref": "#/$defs/" + kind},
                    "uniqueItems": True,
                    **(
                        {"minItems": 1}
                        if name in {"realms", "cultivators", "resources"}
                        else {}
                    ),
                }
                for name, kind in (
                    ("realms", "realm"),
                    ("cultivators", "cultivator"),
                    ("abilities", "ability"),
                    ("ability_states", "ability_state"),
                    ("resources", "resource"),
                )
            },
        }
    ),
    "$defs": {
        "entity_id": _object(
            {
                "project": {"type": "string", "minLength": 1, "pattern": "^[^/]+$"},
                "local_id": {"type": "string", "minLength": 1, "pattern": "^[^/]+$"},
            }
        ),
        "realm": {
            **_object(
                {
                    "id": _ref(),
                    "rank": _quantity(),
                    "resource": _text(),
                    "unit": _text(),
                    "breakthrough_cost": _quantity(),
                }
            ),
            "allOf": [
                {
                    "if": {"properties": {"rank": {"const": 0}}},
                    "then": {"properties": {"breakthrough_cost": {"const": 0}}},
                    "else": {"properties": {"breakthrough_cost": _positive()}},
                }
            ],
        },
        "cultivator": _object({"id": _ref(), "realm": _ref()}),
        "ability": _object(
            {
                "id": _ref(),
                "minimum_realm": _ref(),
                "resource": _text(),
                "unit": _text(),
                "learning_cost": _positive(),
                "use_cost": _positive(),
            }
        ),
        "ability_state": {
            **_object(
                {
                    "id": _ref(),
                    "owner": _ref(),
                    "ability": _ref(),
                    "learned": {"type": "boolean"},
                    "uses": _quantity(),
                }
            ),
            "allOf": [
                {
                    "if": {"properties": {"learned": {"const": False}}},
                    "then": {"properties": {"uses": {"const": 0}}},
                }
            ],
        },
        "resource": _object(
            {
                "id": _ref(),
                "owner": _ref(),
                "resource": _text(),
                "unit": _text(),
                "quantity": _quantity(),
                "spent": _quantity(),
            }
        ),
    },
}
PROGRESSION_SCHEMA_BYTES = canonical_bytes(PROGRESSION_SCHEMA)
PROGRESSION_SCHEMA_HASH = sha256(PROGRESSION_SCHEMA_BYTES).hexdigest()

# Filled from the canonical new manifest; old Pack identities stay unchanged.
PROGRESSION_PACK_IDENTITY = (
    "fantasy.eastern.progression",
    "1.1.0",
    "c6da5ad88ad3ff3cc5566fc6d941cf6f87328695ff1c5128bc40a3915cd9b720",
)
