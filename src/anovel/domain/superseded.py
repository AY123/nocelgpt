"""
SUPERSEDED character validation per frozen V2-061 Contract.

SUPERSEDED characters cannot be referenced in new content operations.
This is a pure-domain validation that does not depend on V2-007.

Contract: Frozen V2-061 §Character Lifecycle + §SUPERSEDED semantics
"""

from __future__ import annotations

from .character import Character, CharacterLifecycle


def validate_character_not_superseded(
    character: Character, operation_context: str = "new content creation"
) -> None:
    """
    Validate that character is not SUPERSEDED for new content operations.

    SUPERSEDED characters represent replaced/obsolete character versions and
    cannot be referenced when creating new story content (knowledge, goals, etc.).

    Args:
        character: Character to validate
        operation_context: Description of operation for error message

    Raises:
        ValueError: If character lifecycle is SUPERSEDED

    Contract: Frozen V2-061 §SUPERSEDED new-content rule
    """
    if character.lifecycle == CharacterLifecycle.SUPERSEDED:
        raise ValueError(
            f"Cannot reference SUPERSEDED character {character.entity_id} in {operation_context}. "
            f"SUPERSEDED characters represent replaced versions and cannot appear in new content."
        )
