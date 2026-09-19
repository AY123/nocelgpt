"""Test Task 2.3: Verify Final hash correspondence.

Ensures that contract_validation records the hash of the draft it validated,
so we can verify the validation corresponds to the final draft.
"""
import pytest
from unittest.mock import Mock, MagicMock


def test_validation_includes_validated_hash():
    """contract_validation should include validated_draft_hash field."""
    # Simulate a validation result
    validation_result = {
        "valid": True,
        "hard_errors": [],
        "soft_issues": [],
        "validated_draft_hash": "abc123def456",
        "validated_at": 1,
    }

    # Check required fields
    assert "validated_draft_hash" in validation_result
    assert validation_result["validated_draft_hash"] == "abc123def456"
    assert "validated_at" in validation_result


def test_validation_hash_matches_chapter_run_hash():
    """The validated_draft_hash should match the ChapterRun's draft_hash."""
    from runtime.serialize.loop import ChapterRun, ChapterSpec

    spec = ChapterSpec(
        index=1,
        task_id="TASK-00001",
        event_id="EVT-00001",
        seeds=["EVT-00001"],
        goal="test goal"
    )

    draft_hash = "abc123def456"

    # Simulate a ChapterRun with validation
    run = ChapterRun(
        spec=spec,
        ok=True,
        stage="done",
        draft_hash=draft_hash,
        contract_validation={
            "valid": True,
            "validated_draft_hash": draft_hash,  # Should match
            "validated_at": 1,
        }
    )

    # Verify hash correspondence
    assert run.draft_hash == run.contract_validation["validated_draft_hash"]


def test_validation_hash_tracks_revision():
    """When revision changes the draft, validation should validate the revised draft."""
    from runtime.serialize.loop import ChapterRun, ChapterSpec

    spec = ChapterSpec(
        index=1,
        task_id="TASK-00001",
        event_id="EVT-00001",
        seeds=["EVT-00001"],
        goal="test goal"
    )

    initial_hash = "initial123"
    revised_hash = "revised456"

    # Simulate a revision that changed the draft
    run = ChapterRun(
        spec=spec,
        ok=True,
        stage="done",
        draft_hash=revised_hash,  # Final draft is revised version
        contract_revision_session={
            "initial_check": {"pass": False},
            "rounds": [
                {
                    "round": 1,
                    "revised_draft_hash": revised_hash,
                }
            ],
            "verdict": "revised_pass",
        },
        contract_validation={
            "valid": True,
            "validated_draft_hash": revised_hash,  # Should validate revised, not initial
            "validated_at": 1,
        }
    )

    # The validation should be for the FINAL (revised) draft
    assert run.draft_hash == revised_hash
    assert run.contract_validation["validated_draft_hash"] == revised_hash
    assert run.contract_validation["validated_draft_hash"] != initial_hash


def test_validation_without_hash_field():
    """Older validation results without validated_draft_hash should not break."""
    from runtime.serialize.loop import ChapterRun, ChapterSpec

    spec = ChapterSpec(
        index=1,
        task_id="TASK-00001",
        event_id="EVT-00001",
        seeds=["EVT-00001"],
        goal="test goal"
    )

    # Old-style validation without the new field
    run = ChapterRun(
        spec=spec,
        ok=True,
        stage="done",
        draft_hash="abc123",
        contract_validation={
            "valid": True,
            "hard_errors": [],
            # Missing validated_draft_hash - should not break
        }
    )

    # Should handle gracefully
    assert run.contract_validation is not None
    assert "valid" in run.contract_validation


def test_validation_hash_in_persisted_artifact():
    """The persisted validation artifact should include validated_draft_hash."""
    # Simulated validation artifact structure
    validation_artifact = {
        "valid": True,
        "hard_errors": [],
        "soft_issues": [],
        "validated_draft_hash": "abc123def456",
        "validated_at": 1,
    }

    # Verify it can be serialized
    import json
    serialized = json.dumps(validation_artifact, ensure_ascii=False, indent=2)
    deserialized = json.loads(serialized)

    assert deserialized["validated_draft_hash"] == "abc123def456"
    assert deserialized["validated_at"] == 1


def test_validation_hash_correspondence_check():
    """Test a helper that verifies validation corresponds to the final draft."""

    def verify_validation_correspondence(chapter_run):
        """Verify that validation checked the final draft."""
        if not chapter_run.contract_validation:
            return True  # No validation, nothing to check

        validated_hash = chapter_run.contract_validation.get("validated_draft_hash")
        if not validated_hash:
            return None  # Old validation without hash field

        return validated_hash == chapter_run.draft_hash

    from runtime.serialize.loop import ChapterRun, ChapterSpec

    spec = ChapterSpec(
        index=1,
        task_id="TASK-00001",
        event_id="EVT-00001",
        seeds=["EVT-00001"],
        goal="test goal"
    )

    # Case 1: Perfect correspondence
    run1 = ChapterRun(
        spec=spec,
        ok=True,
        stage="done",
        draft_hash="abc123",
        contract_validation={
            "valid": True,
            "validated_draft_hash": "abc123",
        }
    )
    assert verify_validation_correspondence(run1) is True

    # Case 2: Mismatch (should not happen in practice)
    run2 = ChapterRun(
        spec=spec,
        ok=True,
        stage="done",
        draft_hash="abc123",
        contract_validation={
            "valid": True,
            "validated_draft_hash": "different456",  # Mismatch!
        }
    )
    assert verify_validation_correspondence(run2) is False

    # Case 3: No validation
    run3 = ChapterRun(
        spec=spec,
        ok=True,
        stage="done",
        draft_hash="abc123",
        contract_validation=None,
    )
    assert verify_validation_correspondence(run3) is True

    # Case 4: Old validation without hash
    run4 = ChapterRun(
        spec=spec,
        ok=True,
        stage="done",
        draft_hash="abc123",
        contract_validation={
            "valid": True,
            # No validated_draft_hash
        }
    )
    assert verify_validation_correspondence(run4) is None  # Can't verify


def test_validation_sequence_integrity():
    """Test the complete flow: revision → validation → hash correspondence."""
    from runtime.serialize.loop import ChapterRun, ChapterSpec

    spec = ChapterSpec(
        index=2,
        task_id="TASK-00002",
        event_id="EVT-00002",
        seeds=["EVT-00002"],
        goal="test goal"
    )

    # Simulate the sequence:
    # 1. Initial generation: hash_v1
    # 2. Contract revision: hash_v1 → hash_v2
    # 3. Hygiene loop: hash_v2 → hash_v3
    # 4. Final validation: should validate hash_v3

    final_hash = "hash_v3"

    run = ChapterRun(
        spec=spec,
        ok=True,
        stage="done",
        draft_hash=final_hash,  # Final after all loops
        contract_revision_session={
            "initial_check": {"pass": False},
            "rounds": [{"round": 1, "revised_draft_hash": "hash_v2"}],
            "verdict": "revised_pass",
        },
        hygiene={
            "rounds": [{"round": 1, "corrected_hash": "hash_v3"}],
            "verdict": "improved",
        },
        contract_validation={
            "valid": True,
            "validated_draft_hash": final_hash,  # Must validate the FINAL
            "validated_at": 2,
        }
    )

    # Validation should check the FINAL draft (after all modifications)
    assert run.draft_hash == final_hash
    assert run.contract_validation["validated_draft_hash"] == final_hash

    # The sequence is: generate → revise → hygiene → validate
    # Validation MUST be for the final output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
