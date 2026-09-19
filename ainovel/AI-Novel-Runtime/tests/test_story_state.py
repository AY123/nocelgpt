"""
StoryState 单元测试
"""

import pytest
from runtime.contract.story_state import (
    StoryState,
    Character,
    Relationship,
    RelationshipType,
    Thread,
)


class TestCharacter:
    """Character 测试"""

    def test_create_character(self):
        """测试创建人物"""
        char = Character(
            id="CHR-90001",
            name="陈默",
            role="protagonist",
            status="active",
            first_appearance_chapter=1
        )

        assert char.id == "CHR-90001"
        assert char.name == "陈默"
        assert char.role == "protagonist"
        assert char.status == "active"


class TestThread:
    """Thread 测试"""

    def test_create_open_thread(self):
        """测试创建未关闭的线索"""
        thread = Thread(
            id="THREAD-001",
            description="30万违约金如何解决",
            opened_chapter=1,
            closed_chapter=None
        )

        assert thread.id == "THREAD-001"
        assert thread.opened_chapter == 1
        assert thread.closed_chapter is None

    def test_create_closed_thread(self):
        """测试创建已关闭的线索"""
        thread = Thread(
            id="THREAD-001",
            description="30万违约金如何解决",
            opened_chapter=1,
            closed_chapter=2
        )

        assert thread.closed_chapter == 2


class TestStoryState:
    """StoryState 测试"""

    def test_create_story_state(self):
        """测试创建故事状态"""
        protagonist = Character(
            id="CHR-90001",
            name="陈默",
            role="protagonist",
            status="active",
            first_appearance_chapter=1
        )

        state = StoryState(
            current_date="2013-01-15",
            current_location="恒远投资公司",
            chapter_number=1,
            protagonist=protagonist,
            characters={"CHR-90001": protagonist},
        )

        assert state.current_date == "2013-01-15"
        assert state.current_location == "恒远投资公司"
        assert state.chapter_number == 1
        assert state.protagonist.name == "陈默"

    def test_validate_continuity_correct(self):
        """测试验证正确的连续性"""
        protagonist = Character(
            id="CHR-90001",
            name="陈默",
            role="protagonist",
            status="active",
            first_appearance_chapter=1
        )

        state1 = StoryState(
            current_date="2013-01-15",
            current_location="恒远投资公司",
            chapter_number=1,
            protagonist=protagonist,
            characters={"CHR-90001": protagonist},
        )

        state2 = StoryState(
            current_date="2013-01-16",
            current_location="云顶会所",
            chapter_number=2,
            protagonist=protagonist,
            characters={"CHR-90001": protagonist},
        )

        errors = state2.validate_continuity(state1)
        assert len(errors) == 0

    def test_validate_continuity_protagonist_name_changed(self):
        """测试检测主角名字改变"""
        protagonist1 = Character(
            id="CHR-90001",
            name="陈默",
            role="protagonist",
            status="active",
            first_appearance_chapter=1
        )

        protagonist2 = Character(
            id="CHR-90001",
            name="林远",  # 错误的名字
            role="protagonist",
            status="active",
            first_appearance_chapter=1
        )

        state1 = StoryState(
            current_date="2013-01-15",
            current_location="恒远投资公司",
            chapter_number=1,
            protagonist=protagonist1,
        )

        state2 = StoryState(
            current_date="2013-01-16",
            current_location="云顶会所",
            chapter_number=2,
            protagonist=protagonist2,
        )

        errors = state2.validate_continuity(state1)
        assert len(errors) > 0
        assert any("主角名字改变" in err for err in errors)

    def test_validate_continuity_time_goes_back(self):
        """测试检测时间倒流"""
        protagonist = Character(
            id="CHR-90001",
            name="陈默",
            role="protagonist",
            status="active",
            first_appearance_chapter=1
        )

        state1 = StoryState(
            current_date="2013-01-15",
            current_location="恒远投资公司",
            chapter_number=1,
            protagonist=protagonist,
        )

        state2 = StoryState(
            current_date="2013-01-10",  # 时间倒流
            current_location="云顶会所",
            chapter_number=2,
            protagonist=protagonist,
        )

        errors = state2.validate_continuity(state1)
        assert len(errors) > 0
        assert any("时间倒流" in err for err in errors)

    def test_validate_continuity_chapter_not_continuous(self):
        """测试检测章节号不连续"""
        protagonist = Character(
            id="CHR-90001",
            name="陈默",
            role="protagonist",
            status="active",
            first_appearance_chapter=1
        )

        state1 = StoryState(
            current_date="2013-01-15",
            current_location="恒远投资公司",
            chapter_number=1,
            protagonist=protagonist,
        )

        state2 = StoryState(
            current_date="2013-01-16",
            current_location="云顶会所",
            chapter_number=5,  # 跳过了2、3、4
            protagonist=protagonist,
        )

        errors = state2.validate_continuity(state1)
        assert len(errors) > 0
        assert any("章节号不连续" in err for err in errors)

    def test_validate_continuity_character_disappears(self):
        """测试检测人物消失"""
        protagonist = Character(
            id="CHR-90001",
            name="陈默",
            role="protagonist",
            status="active",
            first_appearance_chapter=1
        )

        ally = Character(
            id="CHR-90002",
            name="林志远",
            role="ally",
            status="active",
            first_appearance_chapter=1
        )

        state1 = StoryState(
            current_date="2013-01-15",
            current_location="恒远投资公司",
            chapter_number=1,
            protagonist=protagonist,
            characters={"CHR-90001": protagonist, "CHR-90002": ally},
        )

        state2 = StoryState(
            current_date="2013-01-16",
            current_location="云顶会所",
            chapter_number=2,
            protagonist=protagonist,
            characters={"CHR-90001": protagonist},  # ally 消失了
        )

        errors = state2.validate_continuity(state1)
        assert len(errors) > 0
        assert any("活跃人物消失" in err and "林志远" in err for err in errors)

    def test_validate_continuity_character_resurrects(self):
        """测试检测死者复活"""
        protagonist = Character(
            id="CHR-90001",
            name="陈默",
            role="protagonist",
            status="active",
            first_appearance_chapter=1
        )

        enemy_dead = Character(
            id="CHR-90002",
            name="周子铭",
            role="antagonist",
            status="dead",
            first_appearance_chapter=1
        )

        enemy_alive = Character(
            id="CHR-90002",
            name="周子铭",
            role="antagonist",
            status="active",  # 复活了
            first_appearance_chapter=1
        )

        state1 = StoryState(
            current_date="2013-01-15",
            current_location="恒远投资公司",
            chapter_number=1,
            protagonist=protagonist,
            characters={"CHR-90001": protagonist, "CHR-90002": enemy_dead},
        )

        state2 = StoryState(
            current_date="2013-01-16",
            current_location="云顶会所",
            chapter_number=2,
            protagonist=protagonist,
            characters={"CHR-90001": protagonist, "CHR-90002": enemy_alive},
        )

        errors = state2.validate_continuity(state1)
        assert len(errors) > 0
        assert any("死者复活" in err for err in errors)

    def test_create_initial_state(self):
        """测试从 Story Bible 创建初始状态"""
        bible = {
            'protagonist': {
                'name': '陈默',
            },
            'timeline': {
                'start_date': '2013-01-15',
            },
            'world': {
                'primary_city': '江城',
            }
        }

        state = StoryState.create_initial_state(bible)

        assert state.current_date == '2013-01-15'
        assert state.current_location == '江城'
        assert state.chapter_number == 0
        assert state.protagonist.name == '陈默'

    def test_to_dict(self):
        """测试转换为字典"""
        protagonist = Character(
            id="CHR-90001",
            name="陈默",
            role="protagonist",
            status="active",
            first_appearance_chapter=1
        )

        thread = Thread(
            id="THREAD-001",
            description="测试线索",
            opened_chapter=1
        )

        state = StoryState(
            current_date="2013-01-15",
            current_location="恒远投资公司",
            chapter_number=1,
            protagonist=protagonist,
            characters={"CHR-90001": protagonist},
            open_threads=[thread],
        )

        data = state.to_dict()

        assert data['current_date'] == "2013-01-15"
        assert data['chapter_number'] == 1
        assert data['protagonist']['name'] == "陈默"
        assert len(data['open_threads']) == 1

    def test_summary(self):
        """测试生成摘要"""
        protagonist = Character(
            id="CHR-90001",
            name="陈默",
            role="protagonist",
            status="active",
            first_appearance_chapter=1
        )

        state = StoryState(
            current_date="2013-01-15",
            current_location="恒远投资公司",
            chapter_number=1,
            protagonist=protagonist,
        )

        summary = state.summary()

        assert "第1章" in summary
        assert "2013-01-15" in summary
        assert "陈默" in summary
        assert "恒远投资公司" in summary
