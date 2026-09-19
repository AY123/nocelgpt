"""
Revision Task Builder - 将确定性警告转化为结构化修订任务 (P1-1)

将 AI味、节奏、密度、钩子等确定性警告转换为结构化的 Revision Task，
包含精确 span、问题类型、修改边界、目标指标、修改后复检。
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class RevisionTaskType(Enum):
    """修订任务类型"""
    ANAPHORA = "anaphora"  # 重复开头
    DASH_ASIDE = "dash_aside"  # 破折号旁白过多
    SIMILE_DENSITY = "simile_density"  # 比喻密度过高
    DIALOGUE_LOW = "dialogue_low"  # 对话比例过低
    PACING_FLAT = "pacing_flat"  # 节奏平淡
    END_HOOK_WEAK = "end_hook_weak"  # 章末钩子弱
    OPENING_REPEAT = "opening_repeat"  # 开头重复


@dataclass
class TextSpan:
    """文本片段定位"""
    start: int  # 字符起始位置
    end: int  # 字符结束位置
    text: str  # 片段文本
    line_start: Optional[int] = None  # 行号起始
    line_end: Optional[int] = None  # 行号结束


@dataclass
class RevisionTask:
    """
    结构化修订任务

    每个任务对应一个具体的prose问题，包含：
    - 问题类型和严重程度
    - 精确的文本定位
    - 当前值和目标值
    - 修改边界（不可改变的约束）
    - 验证标准
    """
    task_id: str
    task_type: RevisionTaskType
    severity: str  # "critical" | "high" | "medium" | "low"

    # 问题描述
    description: str
    current_value: float
    target_value: float
    metric_name: str

    # 文本定位
    affected_spans: List[TextSpan] = field(default_factory=list)
    context_span: Optional[TextSpan] = None  # 更大的上下文

    # 修改边界
    must_preserve: List[str] = field(default_factory=list)  # 必须保留的内容（人名、关键事件等）
    forbidden_changes: List[str] = field(default_factory=list)  # 禁止修改的方面

    # 验证标准
    validation_check: str = ""  # 验证函数名
    validation_params: Dict[str, Any] = field(default_factory=dict)

    # 建议修改方式
    suggested_approach: str = ""
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "severity": self.severity,
            "description": self.description,
            "current_value": self.current_value,
            "target_value": self.target_value,
            "metric_name": self.metric_name,
            "affected_spans": [
                {
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                }
                for s in self.affected_spans
            ],
            "context_span": {
                "start": self.context_span.start,
                "end": self.context_span.end,
                "text": self.context_span.text,
            } if self.context_span else None,
            "must_preserve": self.must_preserve,
            "forbidden_changes": self.forbidden_changes,
            "validation_check": self.validation_check,
            "validation_params": self.validation_params,
            "suggested_approach": self.suggested_approach,
            "examples": self.examples,
        }


class RevisionTaskBuilder:
    """
    从确定性警告构建修订任务
    """

    def __init__(self):
        self.tasks: List[RevisionTask] = []
        self.task_counter = 0

    def from_hygiene_warnings(
        self,
        body: str,
        hygiene_result: Dict[str, Any]
    ) -> List[RevisionTask]:
        """
        从prose hygiene检查结果构建任务

        Args:
            body: 章节正文
            hygiene_result: prose_hygiene.check_prose_hygiene() 的返回结果

        Returns:
            修订任务列表
        """
        tasks = []

        # 1. Anaphora (连续同头排比)
        if hygiene_result.get("anaphora_count", 0) > 0:
            anaphora_spans = hygiene_result.get("anaphora_spans", [])
            task = RevisionTask(
                task_id=self._next_id(),
                task_type=RevisionTaskType.ANAPHORA,
                severity="medium",
                description=f"检测到{len(anaphora_spans)}处连续同头排比（3句及以上相同开头）",
                current_value=len(anaphora_spans),
                target_value=0,
                metric_name="anaphora_count",
                affected_spans=[
                    TextSpan(
                        start=span.get("start", 0),
                        end=span.get("end", 0),
                        text=span.get("text", ""),
                    )
                    for span in anaphora_spans
                ],
                must_preserve=["人物名称", "关键动作", "核心情节"],
                forbidden_changes=["故事逻辑", "角色行为动机"],
                validation_check="check_prose_hygiene",
                validation_params={"check_anaphora": True},
                suggested_approach="打散句式：改变句子开头，使用代词、时间词、状态词等变化；保持段落节奏",
                examples=[
                    "他站起来。他走向门口。他打开门。 → 他站起来，走向门口，然后打开了门。",
                    "段奕尘看到。段奕尘想到。段奕尘决定。 → 段奕尘看到这一幕，脑中闪过一个念头，于是决定...",
                ],
            )
            tasks.append(task)

        # 2. Dash aside (破折号旁白过多)
        if hygiene_result.get("dash_aside_rate", 0) > 0.15:  # 阈值15%
            task = RevisionTask(
                task_id=self._next_id(),
                task_type=RevisionTaskType.DASH_ASIDE,
                severity="low",
                description=f"破折号旁白比例{hygiene_result['dash_aside_rate']:.1%}，高于参考区间上限15%",
                current_value=hygiene_result["dash_aside_rate"],
                target_value=0.15,
                metric_name="dash_aside_rate",
                affected_spans=[],  # 破折号位置需要从body中提取
                must_preserve=["关键信息", "人物内心独白"],
                forbidden_changes=["叙事视角"],
                validation_check="check_prose_hygiene",
                validation_params={"check_dash_aside": True},
                suggested_approach="减少破折号旁白：部分转为直接描写，部分融入对话，保留最关键的内心独白",
                examples=[
                    "他走了——其实他不想走。 → 他走了，尽管内心充满不舍。",
                ],
            )
            tasks.append(task)

        return tasks

    def from_density_warnings(
        self,
        body: str,
        density_result: Dict[str, Any]
    ) -> List[RevisionTask]:
        """从density检查结果构建任务"""
        tasks = []

        # 比喻密度过高
        simile_rate = density_result.get("simile_rate", 0)
        market_band = density_result.get("market_band", [0, 0.03])
        if simile_rate > market_band[1]:
            task = RevisionTask(
                task_id=self._next_id(),
                task_type=RevisionTaskType.SIMILE_DENSITY,
                severity="medium",
                description=f"比喻密度{simile_rate:.2%}，超出市场参考区间",
                current_value=simile_rate,
                target_value=market_band[1],
                metric_name="simile_rate",
                affected_spans=[],
                must_preserve=["核心比喻", "特色描写"],
                forbidden_changes=["世界观设定"],
                validation_check="check_density",
                validation_params={},
                suggested_approach="精简比喻：保留最生动的比喻，删除重复或冗余的修饰，部分改为直接描写",
                examples=[
                    "像野兽一般凶猛，如雷霆般迅速 → 凶猛而迅速",
                ],
            )
            tasks.append(task)

        # 对话比例过低
        dialogue_rate = density_result.get("dialogue_rate", 0)
        dialogue_band = density_result.get("dialogue_band", [0.15, 0.35])
        if dialogue_rate < dialogue_band[0]:
            task = RevisionTask(
                task_id=self._next_id(),
                task_type=RevisionTaskType.DIALOGUE_LOW,
                severity="medium",
                description=f"对话比例{dialogue_rate:.1%}，低于参考区间{dialogue_band[0]:.1%}",
                current_value=dialogue_rate,
                target_value=dialogue_band[0],
                metric_name="dialogue_rate",
                affected_spans=[],
                must_preserve=["核心情节", "角色性格"],
                forbidden_changes=["故事主线"],
                validation_check="check_density",
                validation_params={},
                suggested_approach="增加对话：将部分内心独白转为对话，增加人物互动场景",
                examples=[
                    "他想：我该怎么办？ → \"我该怎么办？\"他低声问道。",
                ],
            )
            tasks.append(task)

        return tasks

    def from_hook_warnings(
        self,
        body: str,
        hook_result: Dict[str, Any]
    ) -> List[RevisionTask]:
        """从end hook检查结果构建任务"""
        tasks = []

        # 章末钩子弱
        if not hook_result.get("has_hook", True):
            # 获取章节末尾部分作为context
            ending_text = body[-500:] if len(body) > 500 else body
            task = RevisionTask(
                task_id=self._next_id(),
                task_type=RevisionTaskType.END_HOOK_WEAK,
                severity="high",
                description="章末缺少明确的悬念钩子或下章期待",
                current_value=0,
                target_value=1,
                metric_name="has_hook",
                context_span=TextSpan(
                    start=len(body) - len(ending_text),
                    end=len(body),
                    text=ending_text,
                ),
                must_preserve=["本章结论", "情节完整性"],
                forbidden_changes=["角色弧线"],
                validation_check="check_end_hook",
                validation_params={},
                suggested_approach="增强章末钩子：新增信息差、威胁升级、决策悬停、或前置下章爽点",
                examples=[
                    "弱：他回到了家。 → 强：他刚推开门，就看到桌上放着一封没有署名的信。",
                    "弱：今天的训练结束了。 → 强：但他不知道，有人已经盯上了他刚刚展现的能力。",
                ],
            )
            tasks.append(task)

        return tasks

    def build_all(
        self,
        body: str,
        hygiene_result: Optional[Dict] = None,
        density_result: Optional[Dict] = None,
        hook_result: Optional[Dict] = None,
    ) -> List[RevisionTask]:
        """
        从所有检查结果构建完整任务列表

        Args:
            body: 章节正文
            hygiene_result: prose hygiene检查结果
            density_result: density检查结果
            hook_result: end hook检查结果

        Returns:
            所有修订任务列表
        """
        tasks = []

        if hygiene_result:
            tasks.extend(self.from_hygiene_warnings(body, hygiene_result))

        if density_result:
            tasks.extend(self.from_density_warnings(body, density_result))

        if hook_result:
            tasks.extend(self.from_hook_warnings(body, hook_result))

        # 按严重程度排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        tasks.sort(key=lambda t: severity_order.get(t.severity, 99))

        return tasks

    def _next_id(self) -> str:
        """生成下一个任务ID"""
        self.task_counter += 1
        return f"REV-{self.task_counter:04d}"
