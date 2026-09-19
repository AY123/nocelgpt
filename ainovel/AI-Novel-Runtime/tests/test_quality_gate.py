"""
测试 A.2 质量门控
"""
import pytest
from runtime.chapter.quality_gate import (
    assess_final_quality_gate,
    GateSeverity,
    FinalQualityGateResult,
)


class MockChapterRun:
    """模拟 ChapterRun 对象"""
    def __init__(self):
        self.integrity = None
        self.length = None
        self.ai_taste = None


def test_quality_gate_pass_clean_chapter():
    """测试：干净的章节应该通过"""
    chapter_draft = {"body": "这是一个正常的章节内容" * 100}
    chapter_run = MockChapterRun()
    chapter_run.integrity = {"status": "pass"}

    result = assess_final_quality_gate(
        chapter_index=1,
        chapter_draft=chapter_draft,
        chapter_run=chapter_run
    )

    assert result.passed is True
    assert result.blocked is False
    assert result.requires_approval is False
    assert result.recommendation == "proceed"
    assert result.block_count == 0


def test_quality_gate_block_integrity_fail():
    """测试：文本完整性失败应该阻断"""
    chapter_draft = {"body": "broken text"}
    chapter_run = MockChapterRun()
    chapter_run.integrity = {
        "status": "fail",
        "reason_codes": ["invalid_encoding", "malformed_text"]
    }

    result = assess_final_quality_gate(
        chapter_index=1,
        chapter_draft=chapter_draft,
        chapter_run=chapter_run
    )

    assert result.passed is False
    assert result.blocked is True
    assert result.recommendation == "block"
    assert result.block_count == 1
    assert len(result.issues) >= 1
    assert result.issues[0].severity == GateSeverity.BLOCK
    assert result.issues[0].dimension == "integrity"


def test_quality_gate_hold_critical_promise_debt():
    """测试：严重承诺债务需要审批"""
    chapter_draft = {"body": "chapter content"}
    chapter_run = MockChapterRun()
    chapter_run.integrity = {"status": "pass"}

    promise_ledger = {
        "PROMISE-001": {
            "created_chapter": 1,
            "status": "pending",
            "description": "主角获得神秘力量"
        }
    }

    result = assess_final_quality_gate(
        chapter_index=25,  # 25 - 1 = 24 章未兑现 > 20 章阈值
        chapter_draft=chapter_draft,
        chapter_run=chapter_run,
        promise_ledger=promise_ledger
    )

    assert result.passed is True  # 不硬阻断
    assert result.blocked is False
    assert result.requires_approval is True  # 需要审批
    assert result.recommendation == "hold_for_review"
    assert result.hold_count == 1

    hold_issue = [i for i in result.issues if i.severity == GateSeverity.HOLD][0]
    assert hold_issue.dimension == "promise_debt"
    assert "严重逾期" in hold_issue.message


def test_quality_gate_warn_high_promise_debt():
    """测试：高度紧急承诺债务发出警告"""
    chapter_draft = {"body": "chapter content"}
    chapter_run = MockChapterRun()
    chapter_run.integrity = {"status": "pass"}

    promise_ledger = {
        "PROMISE-001": {
            "created_chapter": 1,
            "status": "pending",
            "description": "角色关系线索"
        }
    }

    result = assess_final_quality_gate(
        chapter_index=18,  # 18 - 1 = 17 章 (15-20 范围)
        chapter_draft=chapter_draft,
        chapter_run=chapter_run,
        promise_ledger=promise_ledger
    )

    assert result.passed is True
    assert result.blocked is False
    assert result.requires_approval is False
    assert result.warn_count == 1

    warn_issue = [i for i in result.issues if i.severity == GateSeverity.WARN][0]
    assert warn_issue.dimension == "promise_debt"
    assert "高度紧急" in warn_issue.message


def test_quality_gate_warn_length_overshoot():
    """测试：长度超标发出警告"""
    chapter_draft = {"body": "x" * 10000}
    chapter_run = MockChapterRun()
    chapter_run.integrity = {"status": "pass"}
    chapter_run.length = {
        "findings": [
            {
                "dimension": "length",
                "severity": "warning",
                "message": "章节长度超出目标 150%"
            }
        ]
    }

    result = assess_final_quality_gate(
        chapter_index=1,
        chapter_draft=chapter_draft,
        chapter_run=chapter_run
    )

    assert result.passed is True
    assert result.blocked is False
    assert result.warn_count >= 1

    length_warnings = [i for i in result.issues if i.dimension == "length"]
    assert len(length_warnings) >= 1


def test_quality_gate_warn_ai_taste_issues():
    """测试：多个AI味道问题发出警告"""
    chapter_draft = {"body": "content with ai taste"}
    chapter_run = MockChapterRun()
    chapter_run.integrity = {"status": "pass"}
    chapter_run.ai_taste = {
        "findings": [
            {"severity": "warning", "message": "anaphora detected"},
            {"severity": "warning", "message": "em-dash overuse"},
            {"severity": "warning", "message": "monotone rhythm"}
        ]
    }

    result = assess_final_quality_gate(
        chapter_index=1,
        chapter_draft=chapter_draft,
        chapter_run=chapter_run
    )

    assert result.passed is True
    assert result.warn_count >= 1

    ai_warnings = [i for i in result.issues if i.dimension == "ai_taste"]
    assert len(ai_warnings) >= 1


def test_quality_gate_warn_continuity_length_jump():
    """测试：章节长度突变发出警告"""
    chapter_draft = {"body": "x" * 10000}
    chapter_run = MockChapterRun()
    chapter_run.integrity = {"status": "pass"}

    previous_chapters = [
        {"body": "short" * 100}  # ~500 chars
    ]

    result = assess_final_quality_gate(
        chapter_index=2,
        chapter_draft=chapter_draft,
        chapter_run=chapter_run,
        previous_chapters=previous_chapters
    )

    assert result.passed is True
    assert result.warn_count >= 1

    continuity_warnings = [i for i in result.issues if i.dimension == "continuity"]
    assert len(continuity_warnings) >= 1
    assert "突变" in continuity_warnings[0].message


def test_quality_gate_multiple_issues():
    """测试：多个问题综合判断"""
    chapter_draft = {"body": "x" * 10000}
    chapter_run = MockChapterRun()
    chapter_run.integrity = {"status": "pass"}
    chapter_run.length = {
        "findings": [{"severity": "warning", "message": "too long"}]
    }
    chapter_run.ai_taste = {
        "findings": [
            {"severity": "warning", "message": "issue 1"},
            {"severity": "warning", "message": "issue 2"},
            {"severity": "warning", "message": "issue 3"}
        ]
    }

    promise_ledger = {
        "PROMISE-001": {
            "created_chapter": 1,
            "status": "pending",
            "description": "test"
        }
    }

    result = assess_final_quality_gate(
        chapter_index=25,
        chapter_draft=chapter_draft,
        chapter_run=chapter_run,
        promise_ledger=promise_ledger
    )

    # 有 hold 级别的问题（promise debt）
    assert result.passed is True
    assert result.blocked is False
    assert result.requires_approval is True
    assert result.recommendation == "hold_for_review"

    # 应该有多个问题
    assert len(result.issues) >= 3
    assert result.hold_count >= 1
    assert result.warn_count >= 2


def test_quality_gate_to_dict():
    """测试：结果可以序列化为字典"""
    chapter_draft = {"body": "content"}
    chapter_run = MockChapterRun()
    chapter_run.integrity = {"status": "pass"}

    result = assess_final_quality_gate(
        chapter_index=1,
        chapter_draft=chapter_draft,
        chapter_run=chapter_run
    )

    result_dict = result.to_dict()

    assert isinstance(result_dict, dict)
    assert "passed" in result_dict
    assert "blocked" in result_dict
    assert "requires_approval" in result_dict
    assert "issues" in result_dict
    assert "recommendation" in result_dict
    assert isinstance(result_dict["issues"], list)
