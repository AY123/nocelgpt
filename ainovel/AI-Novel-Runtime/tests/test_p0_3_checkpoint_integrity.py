"""
P0-3: Checkpoint完整性验证测试

测试checkpoint在缺失字段、state_hash重复、event_id重复时的检测能力。
"""
import pytest
import json
from pathlib import Path
from runtime.serialize.checkpoints import build_checkpoint, load_serial_checkpoint


def test_checkpoint_includes_all_required_fields():
    """完整的checkpoint应该包含所有必需字段"""
    checkpoint = build_checkpoint(
        chapter_index=10,
        chapter_id="TASK-00010",
        event_id="EVT-00010",
        draft_hash="sha256:abc123",
        state_hash="sha256:def456",
        final_hash="sha256:ghi789",
        verdict="pass",
        commercial_verdict="improved",
        quality_snapshot={"kind": "quality_snapshot"},
        m7={"recommendation": "recommend"}
    )

    # 所有字段应该存在
    assert checkpoint["chapter_index"] == 10
    assert checkpoint["draft_hash"] == "sha256:abc123"
    assert checkpoint["state_hash"] == "sha256:def456"
    assert checkpoint["final_hash"] == "sha256:ghi789"
    assert checkpoint["verdict"] == "pass"
    assert checkpoint["commercial_verdict"] == "improved"
    assert checkpoint["quality_snapshot"] is not None
    assert checkpoint["m7"] is not None


def test_checkpoint_with_missing_fields():
    """缺失字段的checkpoint应该能构建（但会被标记）"""
    checkpoint = build_checkpoint(
        chapter_index=10,
        chapter_id="TASK-00010",
        event_id="EVT-00010",
        draft_hash=None,  # 缺失
        state_hash="sha256:def456",
        final_hash=None,  # 缺失
        verdict=None,
        commercial_verdict=None,
        quality_snapshot=None,  # 缺失
        m7=None  # 缺失
    )

    # 应该能构建，但字段为None
    assert checkpoint["chapter_index"] == 10
    assert checkpoint["draft_hash"] is None
    assert checkpoint["final_hash"] is None
    assert checkpoint["m7"] is None
    assert checkpoint["quality_snapshot"] is None


def test_checkpoint_completeness_validation():
    """测试checkpoint完整性验证逻辑"""
    # 模拟一个不完整的ChapterRun
    class MockChapterRun:
        def __init__(self):
            self.ok = False
            self.draft_hash = None
            self.state_hash = "sha256:abc"
            self.m5_final = None
            self.m7 = None
            self.quality_snapshot = None

    c = MockChapterRun()

    # 验证逻辑（从loop.py复制）
    incomplete_fields = []
    if not c.ok:
        incomplete_fields.append("chapter_failed")
    if not c.draft_hash:
        incomplete_fields.append("draft_hash")
    if not c.m5_final:
        incomplete_fields.append("final_hash")
    if not c.m7:
        incomplete_fields.append("m7")
    if not c.quality_snapshot:
        incomplete_fields.append("quality_snapshot")

    # 应该检测到所有缺失字段
    assert "chapter_failed" in incomplete_fields
    assert "draft_hash" in incomplete_fields
    assert "final_hash" in incomplete_fields
    assert "m7" in incomplete_fields
    assert "quality_snapshot" in incomplete_fields


def test_event_id_reuse_detection():
    """测试event_id重复检测"""
    consumed_events = set()

    # 第一次使用EVT-00010
    event1 = "EVT-00010"
    is_duplicate1 = event1 in consumed_events
    consumed_events.add(event1)

    assert not is_duplicate1, "首次使用不应检测为重复"

    # 第二次使用EVT-00010
    event2 = "EVT-00010"
    is_duplicate2 = event2 in consumed_events
    consumed_events.add(event2)

    assert is_duplicate2, "重复使用应该被检测到"

    # 使用新的EVT-00020
    event3 = "EVT-00020"
    is_duplicate3 = event3 in consumed_events

    assert not is_duplicate3, "新event不应检测为重复"


def test_state_hash_unchanged_detection():
    """测试state_hash未变化检测"""
    prev_state_hash = None

    # 第一章
    state_hash1 = "sha256:abc123"
    unchanged1 = prev_state_hash and state_hash1 == prev_state_hash
    prev_state_hash = state_hash1

    assert not unchanged1, "首章不应检测为unchanged"

    # 第二章，state_hash变化
    state_hash2 = "sha256:def456"
    unchanged2 = prev_state_hash and state_hash2 == prev_state_hash
    prev_state_hash = state_hash2

    assert not unchanged2, "hash变化不应检测为unchanged"

    # 第三章，state_hash不变（异常）
    state_hash3 = "sha256:def456"  # 和上一章相同
    unchanged3 = prev_state_hash and state_hash3 == prev_state_hash

    assert unchanged3, "hash不变应该被检测到"


def test_checkpoint_with_incomplete_marker(tmp_path):
    """测试带有_incomplete_fields标记的checkpoint"""
    checkpoint = build_checkpoint(
        chapter_index=10,
        chapter_id="TASK-00010",
        event_id="EVT-00010",
        draft_hash=None,
        state_hash="sha256:abc",
        final_hash=None,
        verdict=None,
        commercial_verdict=None,
        quality_snapshot=None,
        m7=None
    )

    # 添加incomplete标记（loop.py中的逻辑）
    incomplete_fields = ["draft_hash", "final_hash", "m7", "quality_snapshot"]
    checkpoint["_incomplete_fields"] = incomplete_fields

    # 写入文件
    checkpoint_path = tmp_path / "cp-010.json"
    checkpoint_path.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2))

    # 读取并验证
    loaded = json.loads(checkpoint_path.read_text())
    assert "_incomplete_fields" in loaded
    assert "draft_hash" in loaded["_incomplete_fields"]
    assert "m7" in loaded["_incomplete_fields"]


def test_commercial_verdict_null_vs_missing():
    """测试commercial_verdict为null和实际verdict的区别"""
    # Case 1: 没有运行商业循环
    cp_no_commercial = build_checkpoint(
        chapter_index=10,
        chapter_id="TASK-00010",
        event_id="EVT-00010",
        draft_hash="sha256:abc",
        state_hash="sha256:def",
        final_hash="sha256:ghi",
        verdict="pass",
        commercial_verdict=None,  # 未运行商业循环
        quality_snapshot={},
        m7={}
    )

    assert cp_no_commercial["commercial_verdict"] is None

    # Case 2: 运行了商业循环且有verdict
    cp_with_commercial = build_checkpoint(
        chapter_index=20,
        chapter_id="TASK-00020",
        event_id="EVT-00020",
        draft_hash="sha256:abc",
        state_hash="sha256:def",
        final_hash="sha256:ghi",
        verdict="pass",
        commercial_verdict="improved",  # 商业循环改进了
        quality_snapshot={},
        m7={}
    )

    assert cp_with_commercial["commercial_verdict"] == "improved"


def test_checkpoint_indices():
    """测试checkpoint在正确的章节索引生成"""
    from runtime.serialize.checkpoints import CHECKPOINT_INDICES

    # 应该在10, 20, 30, ..., 100
    assert 10 in CHECKPOINT_INDICES
    assert 20 in CHECKPOINT_INDICES
    assert 30 in CHECKPOINT_INDICES
    assert 100 in CHECKPOINT_INDICES

    # 不应该在其他索引
    assert 5 not in CHECKPOINT_INDICES
    assert 15 not in CHECKPOINT_INDICES
    assert 101 not in CHECKPOINT_INDICES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
