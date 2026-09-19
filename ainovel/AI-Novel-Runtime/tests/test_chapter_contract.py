"""
ChapterContract 单元测试
"""

import pytest
from runtime.contract.chapter_contract import ChapterContract, ValidationResult


class TestChapterContract:
    """ChapterContract 测试"""

    def test_create_contract(self):
        """测试创建契约"""
        contract = ChapterContract(
            chapter_id="TASK-00001",
            chapter_number=1,
            objective="避免重蹈前世覆辙，用另一种方式解决",
            antagonist="赵鹏程（盛达咨询法务总监）",
            required_beats=[
                "赵鹏程提供灰色项目陷阱",
                "陈默决定直接见周子铭",
            ],
            irreversible_change="陈默主动介入周子铭案件，改变了历史轨迹",
            next_hook="周子铭短信：明天晚上八点，云顶会所",
            protagonist_name="陈默",
            date="2013-01-15",
            allowed_locations=["恒远投资公司"],
            story_bible_hash="test-hash",
            story_bible_version="1.2",
        )

        assert contract.chapter_id == "TASK-00001"
        assert contract.chapter_number == 1
        assert contract.protagonist_name == "陈默"

    def test_validate_correct_draft(self):
        """测试验证正确的草稿"""
        contract = ChapterContract(
            chapter_id="TASK-00001",
            chapter_number=1,
            objective="测试目标",
            antagonist="测试对手",
            required_beats=[],
            irreversible_change="测试改变",
            next_hook="测试钩子",
            protagonist_name="陈默",
            date="2013-01-15",
            allowed_locations=["恒远投资公司"],
            story_bible_hash="test-hash",
        )

        draft_text = "陈默" * 100 + "恒远投资公司" * 10 + "测试内容" * 100
        extracted_data = {
            'protagonist_name': '陈默',
            'date': '2013-01-15',
            'locations': ['恒远投资公司'],
            'characters': ['陈默'],
        }

        result = contract.validate(draft_text, extracted_data)
        assert result.passed
        assert len(result.errors) == 0

    def test_validate_wrong_protagonist_name(self):
        """测试检测错误的主角名字"""
        contract = ChapterContract(
            chapter_id="TASK-00001",
            chapter_number=1,
            objective="测试",
            antagonist="测试",
            required_beats=[],
            irreversible_change="测试",
            next_hook="测试",
            protagonist_name="陈默",
            story_bible_hash="test-hash",
        )

        draft_text = "林远" * 100  # 错误的主角名
        extracted_data = {
            'protagonist_name': '林远',  # 错误
        }

        result = contract.validate(draft_text, extracted_data)
        assert not result.passed
        assert len(result.errors) > 0
        assert "主角名字错误" in result.errors[0]

    def test_validate_wrong_date(self):
        """测试检测错误的日期"""
        contract = ChapterContract(
            chapter_id="TASK-00001",
            chapter_number=1,
            objective="测试",
            antagonist="测试",
            required_beats=[],
            irreversible_change="测试",
            next_hook="测试",
            protagonist_name="陈默",
            date="2013-01-15",
            story_bible_hash="test-hash",
        )

        draft_text = "陈默" * 100
        extracted_data = {
            'protagonist_name': '陈默',
            'date': '2013-01-20',  # 错误的日期
        }

        result = contract.validate(draft_text, extracted_data)
        assert not result.passed
        assert any("日期错误" in err for err in result.errors)

    def test_validate_missing_protagonist_in_opening(self):
        """测试主角名字未在开头出现（警告）"""
        contract = ChapterContract(
            chapter_id="TASK-00001",
            chapter_number=1,
            objective="测试",
            antagonist="测试",
            required_beats=[],
            irreversible_change="测试",
            next_hook="测试",
            protagonist_name="陈默",
            story_bible_hash="test-hash",
        )

        # 主角名字在很后面才出现
        draft_text = "其他内容" * 500 + "陈默"
        extracted_data = {
            'protagonist_name': '陈默',
        }

        result = contract.validate(draft_text, extracted_data)
        assert result.passed  # 不是错误，只是警告
        assert len(result.warnings) > 0
        assert any("未在开头1000字内出现" in warn for warn in result.warnings)

    def test_to_dict(self):
        """测试转换为字典"""
        contract = ChapterContract(
            chapter_id="TASK-00001",
            chapter_number=1,
            objective="测试目标",
            antagonist="测试对手",
            required_beats=["beat1", "beat2"],
            irreversible_change="测试改变",
            next_hook="测试钩子",
            protagonist_name="陈默",
            date="2013-01-15",
            allowed_locations=["测试地点"],
            story_bible_hash="test-hash",
        )

        data = contract.to_dict()
        assert data['chapter_id'] == "TASK-00001"
        assert data['chapter_number'] == 1
        assert data['protagonist_name'] == "陈默"
        assert data['date'] == "2013-01-15"

    def test_from_story_bible(self):
        """测试从 Story Bible 生成契约"""
        bible_chapter = {
            'chapter': 1,
            'protagonist_goal': '避免重蹈前世覆辙',
            'conflict': {
                'antagonist': '赵鹏程'
            },
            'key_beats': ['beat1', 'beat2'],
            'irreversible_change': '改变了历史',
            'end_hook': {
                'content': '明天见周子铭'
            },
            'date': '2013-01-15',
            'location': '恒远投资公司',
        }

        contract = ChapterContract.from_story_bible(
            bible_chapter=bible_chapter,
            chapter_number=1,
            story_bible_hash="test-hash",
            previous_chapter_hash=None
        )

        assert contract.chapter_id == "TASK-00001"
        assert contract.chapter_number == 1
        assert contract.objective == '避免重蹈前世覆辙'
        assert contract.antagonist == '赵鹏程'
        assert contract.date == '2013-01-15'
        assert contract.protagonist_name == '陈默'


class TestValidationResult:
    """ValidationResult 测试"""

    def test_passed_result(self):
        """测试通过的结果"""
        result = ValidationResult(passed=True, errors=[], warnings=[])
        assert result.passed
        assert bool(result) is True

    def test_failed_result(self):
        """测试失败的结果"""
        result = ValidationResult(
            passed=False,
            errors=["错误1", "错误2"],
            warnings=["警告1"]
        )
        assert not result.passed
        assert bool(result) is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
