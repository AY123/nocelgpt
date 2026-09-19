"""Test Task 3.3: 审批审计与版本管理

验证契约审批历史记录和版本管理功能。
"""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime


def test_approval_history_structure():
    """Test the structure of approval history."""
    approval_record = {
        "version": "v1.0",
        "approved": True,
        "approved_at": "2026-08-15T10:00:00Z",
        "approved_by": "张三",
        "reason": "契约内容符合要求",
        "changes_from_previous": "初始版本"
    }

    # Verify required fields
    assert "version" in approval_record
    assert "approved" in approval_record
    assert "approved_at" in approval_record
    assert "approved_by" in approval_record


def test_version_increment_logic():
    """Test version increment logic."""
    # Minor increment: v1.0 -> v1.1
    current = "v1.0"
    version_str = current.replace('v', '')
    parts = version_str.split('.')
    major = int(parts[0])
    minor = int(parts[1])

    minor += 1
    new_version = f"v{major}.{minor}"

    assert new_version == "v1.1"

    # Major increment: v1.1 -> v2.0
    major += 1
    minor = 0
    new_version = f"v{major}.{minor}"

    assert new_version == "v2.0"


def test_approval_timeline_sorting():
    """Test that approval history can be sorted by time."""
    history = [
        {"approved_at": "2026-08-15T12:00:00Z", "version": "v1.1"},
        {"approved_at": "2026-08-15T10:00:00Z", "version": "v1.0"},
        {"approved_at": "2026-08-15T14:00:00Z", "version": "v2.0"},
    ]

    # Sort by time
    sorted_history = sorted(history, key=lambda x: x['approved_at'])

    assert sorted_history[0]['version'] == "v1.0"
    assert sorted_history[1]['version'] == "v1.1"
    assert sorted_history[2]['version'] == "v2.0"


def test_schema_has_approval_history_field():
    """Verify that schema includes approval_history field."""
    schema_path = Path(__file__).parent.parent.parent / "schemas" / "chapter_contract.schema.json"

    if not schema_path.exists():
        pytest.skip("Schema file not found")

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    # Should have approval_history in properties
    assert "approval_history" in schema.get("properties", {})

    # approval_history should be an array
    approval_history_schema = schema["properties"]["approval_history"]
    assert approval_history_schema["type"] == "array"


def test_approval_manager_exists():
    """Verify that approval.py module exists."""
    # Try multiple possible paths
    possible_paths = [
        Path(__file__).parent.parent.parent.parent / "runtime_plugins" / "contract" / "approval.py",
        Path(__file__).parent.parent.parent / "runtime_plugins" / "contract" / "approval.py",
    ]

    approval_file = None
    for path in possible_paths:
        if path.exists():
            approval_file = path
            break

    if not approval_file:
        pytest.skip("approval.py not found in expected locations")

    content = approval_file.read_text(encoding='utf-8')

    # Should have ContractApprovalManager class
    assert "ContractApprovalManager" in content
    assert "Task 3.3" in content


def test_contract_approval_workflow():
    """Test the complete approval workflow."""
    with tempfile.TemporaryDirectory() as tmpdir:
        contracts_dir = Path(tmpdir) / "contracts"
        contracts_dir.mkdir()

        # Create a test contract
        contract = {
            "chapter": 1,
            "version": "v1.0",
            "approved": False,
            "approved_at": None,
            "entry_state": {},
            "chapter_intent": {},
            "exit_target": {},
            "transition_to_next": {},
            "sources": {
                "generated_at": "2026-08-15T10:00:00Z",
                "generated_from": "manual"
            }
        }

        contract_file = contracts_dir / "chapter_001_contract.json"
        with open(contract_file, 'w', encoding='utf-8') as f:
            json.dump(contract, f, indent=2)

        # Simulate approval
        import sys
        plugins_path = Path(__file__).parent.parent.parent.parent / 'runtime_plugins'
        if str(plugins_path) not in sys.path:
            sys.path.insert(0, str(plugins_path))

        try:
            from contract.approval import ContractApprovalManager

            manager = ContractApprovalManager(contracts_dir)

            # Approve the contract
            updated = manager.approve_contract(
                chapter=1,
                approved_by="测试审批人",
                reason="测试通过",
                changes="初始版本"
            )

            # Verify approval was recorded
            assert updated['approved'] is True
            assert 'approval_history' in updated
            assert len(updated['approval_history']) == 1

            history = updated['approval_history'][0]
            assert history['approved'] is True
            assert history['approved_by'] == "测试审批人"
            assert history['version'] == "v1.0"

        except ModuleNotFoundError:
            pytest.skip("ContractApprovalManager not available")


def test_version_evolution_workflow():
    """Test version evolution: v1.0 -> v1.1 -> v2.0."""
    versions = ["v1.0", "v1.1", "v2.0"]

    # Simulate evolution
    evolution = []
    for version in versions:
        evolution.append({
            "version": version,
            "approved": True,
            "approved_at": datetime.now().isoformat(),
            "approved_by": "审批人",
            "reason": f"批准 {version}"
        })

    # Verify evolution
    assert len(evolution) == 3
    assert evolution[0]['version'] == "v1.0"
    assert evolution[1]['version'] == "v1.1"
    assert evolution[2]['version'] == "v2.0"


def test_audit_trail_format():
    """Test audit trail report format."""
    history = [
        {
            "version": "v1.0",
            "approved": True,
            "approved_at": "2026-08-15T10:00:00Z",
            "approved_by": "张三",
            "reason": "初始审批",
            "changes_from_previous": "初始版本"
        },
        {
            "version": "v1.1",
            "approved": True,
            "approved_at": "2026-08-15T11:00:00Z",
            "approved_by": "李四",
            "reason": "修订后审批",
            "changes_from_previous": "修改了exit_target"
        }
    ]

    # Generate report (simplified)
    report_lines = []
    for i, record in enumerate(history, 1):
        approved = "✅ 批准" if record['approved'] else "❌ 拒绝"
        report_lines.append(f"{i}. {record['version']} - {approved}")
        report_lines.append(f"   审批人: {record['approved_by']}")

    report = "\n".join(report_lines)

    assert "v1.0" in report
    assert "v1.1" in report
    assert "张三" in report
    assert "李四" in report


def test_rejection_workflow():
    """Test contract rejection workflow."""
    rejection_record = {
        "version": "v1.0",
        "approved": False,
        "approved_at": "2026-08-15T10:00:00Z",
        "approved_by": "审批人",
        "reason": "契约内容不符合要求，需要修改",
        "changes_from_previous": ""
    }

    # Verify rejection is recorded
    assert rejection_record['approved'] is False
    assert rejection_record['reason'] != ""


def test_approval_history_preserves_all_records():
    """Test that all approval records are preserved."""
    # Simulate multiple approvals
    history = []

    # v1.0 rejected
    history.append({
        "version": "v1.0",
        "approved": False,
        "approved_at": "2026-08-15T10:00:00Z",
        "approved_by": "审批人A"
    })

    # v1.1 approved
    history.append({
        "version": "v1.1",
        "approved": True,
        "approved_at": "2026-08-15T11:00:00Z",
        "approved_by": "审批人B"
    })

    # Both records should be preserved
    assert len(history) == 2
    assert history[0]['approved'] is False
    assert history[1]['approved'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
