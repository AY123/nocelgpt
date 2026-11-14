"""Version-pinned inert schema contract for the first business extension."""

from __future__ import annotations

from hashlib import sha256

from anovel.canon.identity import canonical_bytes

BUSINESS_NAMESPACE = "urban.business"
BUSINESS_VERSION = "1.0.0"
BUSINESS_SCHEMA_ID = "https://anovel.dev/genres/urban.business/1.0.0/schema.json"
SHARE_PARTS = 1_000_000

_ID = {
    "type": "object",
    "required": ["project", "local_id"],
    "properties": {
        "project": {"type": "string", "minLength": 1, "pattern": "^[^/]+$"},
        "local_id": {"type": "string", "minLength": 1, "pattern": "^[^/]+$"},
    },
    "additionalProperties": False,
}


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


BUSINESS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": BUSINESS_SCHEMA_ID,
    "title": "Urban business state 1.0.0",
    "description": "Closed structure only. Strict Python integers, same-project references, exact root entity membership, unique object and fact identities, total issued shares and conserved transitions require the compiled validator. No accounting, semantic prose approval, or Canon write authority is implied.",
    **_object(
        {
            "kind": {"const": "URBAN_BUSINESS_STATE"},
            "schema_version": {"const": BUSINESS_VERSION},
            **{
                name: {
                    "type": "array",
                    "items": {"$ref": "#/$defs/" + kind},
                    "uniqueItems": True,
                }
                for name, kind in (
                    ("companies", "company"),
                    ("accounts", "account"),
                    ("holdings", "share"),
                    ("resources", "resource"),
                )
            },
        }
    ),
    "$defs": {
        "entity_id": _ID,
        "company": _object({"id": _ref(), "total_parts": {"const": SHARE_PARTS}}),
        "account": _object(
            {
                "id": _ref(),
                "owner": _ref(),
                "currency": {
                    "type": "string",
                    "pattern": "^[A-Z]{3}$",
                    "minLength": 3,
                    "maxLength": 3,
                },
                "balance_minor": _quantity(),
            }
        ),
        "share": _object(
            {
                "id": _ref(),
                "company": _ref(),
                "owner": _ref(),
                "parts": {"type": "integer", "minimum": 0, "maximum": SHARE_PARTS},
            }
        ),
        "resource": _object(
            {
                "id": _ref(),
                "owner": _ref(),
                "resource": {"type": "string", "pattern": "\\S"},
                "unit": {"type": "string", "pattern": "\\S"},
                "quantity": _quantity(),
            }
        ),
    },
}
BUSINESS_SCHEMA_BYTES = canonical_bytes(BUSINESS_SCHEMA)
BUSINESS_SCHEMA_HASH = sha256(BUSINESS_SCHEMA_BYTES).hexdigest()

# Exact new Pack pin is filled from canonical manifest bytes at implementation.
BUSINESS_PACK_IDENTITY = (
    "urban.business.realistic",
    "1.1.0",
    "aadc2b0cd538d897299be7da775ecc81e51290ad7d5f89a325bcb55b0c8395c7",
)
