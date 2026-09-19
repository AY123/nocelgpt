"""
测试 Revision Task Builder (P1-1)
"""
import pytest
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from runtime.revision_task import (
    RevisionTaskBuilder,
    RevisionTaskType,
    RevisionTask,
    TextSpan,
)


def test_revision_task_basic():
    """测试基本的RevisionTask创建"""
    task = RevisionTask(
        task_id="REV-0001",
        task_type=RevisionTaskType.ANAPHORA,
        severity="medium",
        description="检测到3处连续同头排比",
        current_value=3,
        target_value=0,
        metric_name="anaphora_count",
    )

    assert task.task_id == "REV-0001"
    assert task.task_type == RevisionTaskType.ANAPHORA
    assert task.severity == "medium"
    assert task.current_value == 3
    assert task.target_value == 0


def test_revision_task_with_spans():
    """测试带文本定位的任务"""
    span1 = TextSpan(start=0, end=10, text="他站起来。", line_start=1, line_end=1)
    span2 = TextSpan(start=10, end=20, text="他走出去。", line_start=2, line_end=2)

    task = RevisionTask(
        task_id="REV-0002",
        task_type=RevisionTaskType.ANAPHORA,
        severity="medium",
        description="连续同头排比",
        current_value=2,
        target_value=0,
        metric_name="anaphora_count",
        affected_spans=[span1, span2],
    )

    assert len(task.affected_spans) == 2
    assert task.affected_spans[0].text == "他站起来。"
    assert task.affected_spans[1].line_start == 2


def test_revision_task_to_dict():
    """测试序列化"""
    task = RevisionTask(
        task_id="REV-0003",
        task_type=RevisionTaskType.END_HOOK_WEAK,
        severity="high",
        description="章末缺少钩子",
        current_value=0,
        target_value=1,
        metric_name="has_hook",
        suggested_approach="增强章末悬念",
        examples=["增加疑问", "增加转折"],
    )

    d = task.to_dict()
    assert d["task_id"] == "REV-0003"
    assert d["task_type"] == "end_hook_weak"
    assert d["severity"] == "high"
    assert d["suggested_approach"] == "增强章末悬念"
    assert len(d["examples"]) == 2


def test_builder_from_hygiene_anaphora():
    """测试从hygiene结果构建anaphora任务"""
    builder = RevisionTaskBuilder()

    hygiene_result = {
        "anaphora_count": 2,
        "anaphora_spans": [
            {"start": 0, "end": 15, "text": "他站起来走了。"},
            {"start": 15, "end": 30, "text": "他推开门出去。"},
        ],
    }

    body = "他站起来走了。他推开门出去。"
    tasks = builder.from_hygiene_warnings(body, hygiene_result)

    assert len(tasks) == 1
    assert tasks[0].task_type == RevisionTaskType.ANAPHORA
    assert tasks[0].current_value == 2
    assert tasks[0].target_value == 0
    assert len(tasks[0].affected_spans) == 2
    assert "打散句式" in tasks[0].suggested_approach


def test_builder_from_hygiene_dash_aside():
    """测试从hygiene结果构建dash_aside任务"""
    builder = RevisionTaskBuilder()

    hygiene_result = {
        "dash_aside_rate": 0.20,  # 20% > 15%
    }

    body = "他走了——其实他不想走——但他必须走。"
    tasks = builder.from_hygiene_warnings(body, hygiene_result)

    assert len(tasks) == 1
    assert tasks[0].task_type == RevisionTaskType.DASH_ASIDE
    assert tasks[0].current_value == 0.20
    assert tasks[0].target_value == 0.15
    assert "破折号" in tasks[0].description


def test_builder_from_density_simile():
    """测试从density结果构建simile任务"""
    builder = RevisionTaskBuilder()

    density_result = {
        "simile_rate": 0.05,  # 5%
        "market_band": [0.0, 0.03],  # 市场区间0-3%
        "dialogue_rate": 0.20,  # 20%，在正常范围内，不触发任务
        "dialogue_band": [0.15, 0.35],
    }

    body = "天空如铁，寒风像刀，他的心宛如冰窟。"
    tasks = builder.from_density_warnings(body, density_result)

    assert len(tasks) == 1
    assert tasks[0].task_type == RevisionTaskType.SIMILE_DENSITY
    assert tasks[0].current_value == 0.05
    assert tasks[0].target_value == 0.03
    assert "比喻密度" in tasks[0].description


def test_builder_from_density_dialogue_low():
    """测试从density结果构建dialogue任务"""
    builder = RevisionTaskBuilder()

    density_result = {
        "dialogue_rate": 0.10,  # 10%
        "dialogue_band": [0.15, 0.35],  # 市场区间15-35%
        "simile_rate": 0.02,  # 2%，在正常范围内
        "market_band": [0.0, 0.03],
    }

    body = "叙述叙述叙述叙述叙述。"
    tasks = builder.from_density_warnings(body, density_result)

    assert len(tasks) == 1
    assert tasks[0].task_type == RevisionTaskType.DIALOGUE_LOW
    assert tasks[0].current_value == 0.10
    assert tasks[0].target_value == 0.15
    assert "对话比例" in tasks[0].description


def test_builder_from_hook_weak():
    """测试从hook结果构建end_hook任务"""
    builder = RevisionTaskBuilder()

    hook_result = {
        "has_hook": False,  # 没有钩子
    }

    body = "一切都结束了。他回到了家中，安心地睡去。"
    tasks = builder.from_hook_warnings(body, hook_result)

    assert len(tasks) == 1
    assert tasks[0].task_type == RevisionTaskType.END_HOOK_WEAK
    assert tasks[0].severity == "high"
    assert tasks[0].current_value == 0
    assert tasks[0].target_value == 1
    assert tasks[0].context_span is not None
    assert "钩子" in tasks[0].suggested_approach  # 修复：实际文本包含"钩子"而非"悬念"


def test_builder_build_all():
    """测试构建所有任务"""
    builder = RevisionTaskBuilder()

    hygiene_result = {
        "anaphora_count": 1,
        "anaphora_spans": [{"start": 0, "end": 10, "text": "他走了。"}],
    }

    density_result = {
        "simile_rate": 0.05,
        "market_band": [0.0, 0.03],
        "dialogue_rate": 0.20,  # 正常范围内
        "dialogue_band": [0.15, 0.35],
    }

    hook_result = {
        "has_hook": False,
    }

    body = "测试正文"
    tasks = builder.build_all(
        body,
        hygiene_result=hygiene_result,
        density_result=density_result,
        hook_result=hook_result,
    )

    # 应该有3个任务
    assert len(tasks) == 3

    # 按严重程度排序: high > medium > ...
    assert tasks[0].severity == "high"  # end_hook
    assert tasks[1].severity == "medium"  # anaphora or simile
    assert tasks[2].severity in ["medium", "low"]


def test_builder_task_id_increment():
    """测试任务ID自增"""
    builder = RevisionTaskBuilder()

    hygiene_result = {
        "anaphora_count": 1,
        "anaphora_spans": [{"start": 0, "end": 10, "text": "他走了。"}],
        "dash_aside_rate": 0.20,
    }

    body = "测试"
    tasks = builder.from_hygiene_warnings(body, hygiene_result)

    assert len(tasks) == 2
    assert tasks[0].task_id == "REV-0001"
    assert tasks[1].task_id == "REV-0002"


def test_builder_empty_results():
    """测试空结果不生成任务"""
    builder = RevisionTaskBuilder()

    tasks = builder.build_all(
        body="正文",
        hygiene_result={},
        density_result={},
        hook_result={"has_hook": True},  # 有钩子，不生成任务
    )

    assert len(tasks) == 0


def test_task_validation_fields():
    """测试任务验证字段"""
    task = RevisionTask(
        task_id="REV-0004",
        task_type=RevisionTaskType.ANAPHORA,
        severity="medium",
        description="测试",
        current_value=1,
        target_value=0,
        metric_name="anaphora_count",
        validation_check="check_prose_hygiene",
        validation_params={"check_anaphora": True},
    )

    assert task.validation_check == "check_prose_hygiene"
    assert task.validation_params["check_anaphora"] is True

    d = task.to_dict()
    assert d["validation_check"] == "check_prose_hygiene"
    assert d["validation_params"]["check_anaphora"] is True
