"""
SUPERSEDED character validation tests.

Tests that SUPERSEDED characters cannot be referenced in new content operations
per frozen V2-061 Contract lifecycle semantics.

Contract Authority: Frozen V2-061 §SUPERSEDED new-content rule
"""

import pytest

from anovel.domain import (
    Character,
    CharacterLifecycle,
    create_character,
)
from anovel.domain.identity import ProjectId
from anovel.domain.superseded import validate_character_not_superseded


class TestSupersededValidation:
    """SUPERSEDED character cannot be referenced in new content."""

    def test_active_character_passes(self):
        """ACTIVE character passes SUPERSEDED validation."""
        char = create_character(ProjectId("proj_01"), "张三")

        # Should not raise
        validate_character_not_superseded(char, "test operation")

    def test_inactive_character_passes(self):
        """INACTIVE character passes SUPERSEDED validation."""
        char = create_character(ProjectId("proj_01"), "张三")

        from dataclasses import replace
        char = replace(char, lifecycle=CharacterLifecycle.INACTIVE)

        # Should not raise
        validate_character_not_superseded(char, "test operation")

    def test_deceased_character_passes(self):
        """DECEASED character passes SUPERSEDED validation."""
        char = create_character(ProjectId("proj_01"), "张三")

        from dataclasses import replace
        char = replace(char, lifecycle=CharacterLifecycle.DECEASED)

        # Should not raise
        validate_character_not_superseded(char, "test operation")

    def test_superseded_character_rejects(self):
        """SUPERSEDED character rejects for new content operations."""
        char = create_character(ProjectId("proj_01"), "张三")

        from dataclasses import replace
        char = replace(char, lifecycle=CharacterLifecycle.SUPERSEDED)

        with pytest.raises(ValueError, match="SUPERSEDED character.*cannot.*new content"):
            validate_character_not_superseded(char, "knowledge creation")

    def test_superseded_character_rejects_with_context(self):
        """SUPERSEDED character rejection includes operation context."""
        char = create_character(ProjectId("proj_01"), "张三")

        from dataclasses import replace
        char = replace(char, lifecycle=CharacterLifecycle.SUPERSEDED)

        with pytest.raises(ValueError, match="goal formation"):
            validate_character_not_superseded(char, "goal formation")
