"""Test semantic severity classification stability.

Validates that severity classification is based on task semantics,
not message wording.
"""

import sys
import os

# Add plan/scripts to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../plan/scripts"))

from task_entry import classify_error_severity as task_classify
from validate_plan import classify_error_severity as validate_classify


def test_task_entry_severity_semantic_classification():
    """Test task_entry severity classification is semantic, not string-based."""

    # V2-005 and V2-006 are grandfathered - should be INFORMATIONAL
    # regardless of exact message wording

    # Original wording
    error1 = "EXEC_PACKET_ABSENT V2-005: no genuine historical execution packet exists (absence record registered, INFORMATIONAL)"
    assert task_classify(error1) == "INFORMATIONAL"

    # Different wording - same semantic meaning
    error2 = "EXEC_PACKET_ABSENT V2-005: historical packet missing"
    assert task_classify(error2) == "INFORMATIONAL"

    # Completely different message
    error3 = "EXEC_PACKET_ABSENT V2-005: whatever message here"
    assert task_classify(error3) == "INFORMATIONAL"

    # V2-006 also grandfathered
    error4 = "EXEC_PACKET_ABSENT V2-006: some message"
    assert task_classify(error4) == "INFORMATIONAL"

    # Non-grandfathered task should be BLOCKING
    error5 = "EXEC_PACKET_ABSENT V2-061: no packet"
    assert task_classify(error5) == "BLOCKING"

    # Other error types should be BLOCKING
    error6 = "TASK_SCHEMA V2-061: validation error"
    assert task_classify(error6) == "BLOCKING"


def test_validate_plan_severity_semantic_classification():
    """Test validate_plan severity classification is semantic, not string-based."""

    # V2-005 and V2-006 are grandfathered - should be INFORMATIONAL

    # Original wording
    error1 = "EXEC_PACKET_ABSENT V2-005: no genuine historical execution packet exists (absence record registered, INFORMATIONAL)"
    assert validate_classify(error1) == "INFORMATIONAL"

    # Different wording - same semantic meaning
    error2 = "EXEC_PACKET_ABSENT V2-005: historical packet missing"
    assert validate_classify(error2) == "INFORMATIONAL"

    # Completely different message
    error3 = "EXEC_PACKET_ABSENT V2-005: whatever message here"
    assert validate_classify(error3) == "INFORMATIONAL"

    # V2-006 also grandfathered
    error4 = "EXEC_PACKET_ABSENT V2-006: some message"
    assert validate_classify(error4) == "INFORMATIONAL"

    # Non-grandfathered task should be FATAL
    error5 = "EXEC_PACKET_ABSENT V2-061: no packet"
    assert validate_classify(error5) == "FATAL"

    # Other error types should be FATAL
    error6 = "TASK_SCHEMA V2-061: validation error"
    assert validate_classify(error6) == "FATAL"


def test_severity_classification_wording_independence():
    """Verify classification is stable across message wording changes."""

    # Test that completely removing the "(absence record registered, INFORMATIONAL)"
    # marker from grandfathered tasks still results in INFORMATIONAL classification

    # No special marker - pure semantic classification
    messages = [
        "EXEC_PACKET_ABSENT V2-005: packet not found",
        "EXEC_PACKET_ABSENT V2-005: missing",
        "EXEC_PACKET_ABSENT V2-005: error",
        "EXEC_PACKET_ABSENT V2-006: packet not found",
        "EXEC_PACKET_ABSENT V2-006: missing",
    ]

    for msg in messages:
        assert task_classify(msg) == "INFORMATIONAL", f"Failed for: {msg}"
        assert validate_classify(msg) == "INFORMATIONAL", f"Failed for: {msg}"

    # Non-grandfathered should be blocking/fatal regardless of wording similarity
    non_grandfathered = [
        "EXEC_PACKET_ABSENT V2-007: packet not found",
        "EXEC_PACKET_ABSENT V2-061: missing",
        "EXEC_PACKET_ABSENT V2-999: (absence record registered, INFORMATIONAL)",  # Wrong task!
    ]

    for msg in non_grandfathered:
        assert task_classify(msg) == "BLOCKING", f"Failed for: {msg}"
        assert validate_classify(msg) == "FATAL", f"Failed for: {msg}"
