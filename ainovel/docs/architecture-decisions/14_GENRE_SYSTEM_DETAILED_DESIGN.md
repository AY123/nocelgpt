# Genre系统详细设计文档

**版本**: v2.0  
**制定日期**: 2026-09-18  
**状态**: 详细设计  
**实施阶段**: M1 Week 1-2  

---

## 📋 文档目的

本文档提供Genre系统的完整、详细设计，包括：
- 完整的数据结构定义
- 详细的类设计与方法签名
- 完整的代码示例
- 测试用例
- 实施指南

**目标**: 为M1 Week 1-2的实施提供充分准备，开发者可直接按此文档编码

---

## 🎯 系统概述

### 核心理念

**Genre-First架构**: 题材是第一公民，所有决策基于题材

### 核心目标

1. **题材隔离**: 都市不生成修炼，玄幻不生成商业
2. **题材约束**: 硬约束可阻断生成
3. **题材专用**: 每个题材有专用的Prompt、进阶模型、验证器
4. **题材检测**: 自动从参考作品检测题材

### 核心组件

```
GenreSystem
├── GenreConfig (题材配置)
├── GenreConstraints (题材约束)
├── ProgressionModel (进阶模型抽象)
│   ├── WealthProgressionModel (都市财富)
│   ├── PowerProgressionModel (玄幻力量)
│   ├── TechProgressionModel (科幻科技)
│   └── StatusProgressionModel (职场地位)
├── GenreRegistry (题材注册表)
├── GenreDetector (题材检测器)
└── GenreValidator (题材验证器)
```

---

## 📐 核心数据结构

### 1. GenreConfig（题材配置）

**位置**: `AI-Novel-Runtime/runtime/genre/config.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Type, Optional
from enum import Enum

class GenreID(Enum):
    """题材ID枚举"""
    URBAN = "urban"              # 都市
    XUANHUAN = "xuanhuan"        # 玄幻
    XIANXIA = "xianxia"          # 仙侠
    WUXIA = "wuxia"              # 武侠
    SCIFI = "scifi"              # 科幻
    HISTORY = "history"          # 历史
    MILITARY = "military"        # 军事
    GAME = "game"                # 游戏
    SPORTS = "sports"            # 体育
    SUPERNATURAL = "supernatural" # 灵异

@dataclass
class GenreConfig:
    """题材完整配置
    
    这是Genre系统的核心数据结构，包含一个题材的所有配置信息。
    每个题材必须定义一个完整的GenreConfig实例。
    
    Attributes:
        genre_id: 题材唯一标识符
        genre_name: 题材中文名称
        genre_name_en: 题材英文名称
        description: 题材描述
        constraints: 题材约束（硬约束，可阻断）
        progression_model: 进阶模型类（用于角色成长）
        prompt_templates: 题材专用Prompt模板
        detector: 题材检测器实例
        worldview_foundation: 世界观基础设定
        target_audience: 目标读者群体
        typical_themes: 典型主题
        prohibited_content: 禁止内容
        metadata: 扩展元数据
    
    Example:
        >>> urban_config = GenreConfig(
        ...     genre_id=GenreID.URBAN,
        ...     genre_name="都市",
        ...     constraints=UrbanConstraints(),
        ...     progression_model=WealthProgressionModel,
        ...     ...
        ... )
    """
    
    # 基础信息
    genre_id: GenreID
    genre_name: str
    genre_name_en: str
    description: str
    
    # 核心组件
    constraints: 'GenreConstraints'
    progression_model: Type['ProgressionModel']
    prompt_templates: Dict[str, str]
    detector: 'GenreDetector'
    
    # 世界观基础
    worldview_foundation: 'WorldviewFoundation'
    
    # 受众与主题
    target_audience: Dict[str, str] = field(default_factory=dict)
    typical_themes: List[str] = field(default_factory=list)
    
    # 禁止内容
    prohibited_content: List[str] = field(default_factory=list)
    
    # 扩展元数据
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后验证"""
        self._validate()
    
    def _validate(self):
        """验证配置完整性"""
        if not self.genre_name:
            raise ValueError("genre_name cannot be empty")
        
        if not self.constraints:
            raise ValueError(f"Genre {self.genre_id} must have constraints")
        
        if not self.progression_model:
            raise ValueError(f"Genre {self.genre_id} must have progression_model")
        
        if "outline" not in self.prompt_templates:
            raise ValueError(f"Genre {self.genre_id} must have 'outline' prompt template")
        
        if "chapter" not in self.prompt_templates:
            raise ValueError(f"Genre {self.genre_id} must have 'chapter' prompt template")
    
    def get_prompt_template(self, stage: str) -> str:
        """获取Prompt模板
        
        Args:
            stage: 阶段名称（outline/chapter/revision/...）
        
        Returns:
            Prompt模板字符串
        
        Raises:
            KeyError: 如果stage不存在
        """
        if stage not in self.prompt_templates:
            raise KeyError(f"Prompt template '{stage}' not found for genre {self.genre_id}")
        
        return self.prompt_templates[stage]
    
    def get_progression_instance(self) -> 'ProgressionModel':
        """获取进阶模型实例
        
        Returns:
            ProgressionModel实例
        """
        return self.progression_model()
    
    def to_dict(self) -> Dict:
        """转换为字典（用于序列化）"""
        return {
            "genre_id": self.genre_id.value,
            "genre_name": self.genre_name,
            "genre_name_en": self.genre_name_en,
            "description": self.description,
            "target_audience": self.target_audience,
            "typical_themes": self.typical_themes,
            "prohibited_content": self.prohibited_content,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GenreConfig':
        """从字典加载（用于反序列化）"""
        # 需要从Registry加载完整配置
        genre_id = GenreID(data["genre_id"])
        return GenreRegistry.get(genre_id)


@dataclass
class WorldviewFoundation:
    """世界观基础设定
    
    定义题材的基础世界观设定，包括时空背景、科技水平、社会结构等。
    
    Attributes:
        time_period: 时代背景
        technology_level: 科技水平
        social_structure: 社会结构
        supernatural_elements: 超自然元素（是否存在）
        power_source: 力量来源（如灵气、科技、内力）
        geography_type: 地理类型（现实/虚构）
    """
    
    time_period: str              # 如"现代中国"、"架空古代"、"未来太空"
    technology_level: str         # 如"现代科技"、"古代冷兵器"、"星际文明"
    social_structure: str         # 如"现代社会"、"封建社会"、"宗门体系"
    supernatural_elements: bool   # 是否存在超自然元素
    power_source: Optional[str]   # 力量来源（如灵气、科技、内力）
    geography_type: str           # "realistic"（现实地理）或"fictional"（虚构地理）
    
    def to_prompt(self) -> str:
        """转换为Prompt描述"""
        return f"""
【世界观基础】
时代背景: {self.time_period}
科技水平: {self.technology_level}
社会结构: {self.social_structure}
超自然元素: {"存在" if self.supernatural_elements else "不存在"}
力量来源: {self.power_source if self.power_source else "无"}
地理类型: {self.geography_type}
"""
```

---

### 2. GenreConstraints（题材约束）

**位置**: `AI-Novel-Runtime/runtime/genre/constraints.py`

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

class ViolationSeverity(Enum):
    """违规严重程度"""
    CRITICAL = "critical"    # 严重违规，必须阻断
    HIGH = "high"            # 高度违规，强烈建议修改
    MEDIUM = "medium"        # 中度违规，建议修改
    LOW = "low"              # 轻度违规，提示即可


@dataclass
class ConstraintException:
    """约束例外规则
    
    定义某些特殊情况下可以违反约束。
    例如：都市题材一般禁止"修炼"，但"都市修仙"子类型允许。
    
    Attributes:
        condition: 触发条件
        allows: 允许的元素列表
        reason: 例外原因
    """
    condition: str
    allows: List[str]
    reason: str


@dataclass
class GenreConstraints:
    """题材约束
    
    定义题材的硬约束，用于验证内容是否符合题材规范。
    约束分为允许和禁止两个维度。
    
    Attributes:
        allowed_elements: 允许的元素列表
        forbidden_elements: 禁止的元素列表
        allowed_scenes: 允许的场景类型
        forbidden_scenes: 禁止的场景类型
        allowed_plot_devices: 允许的剧情设定
        forbidden_plot_devices: 禁止的剧情设定
        violation_severity: 违规严重程度映射
        exceptions: 例外规则列表
    
    Example:
        >>> urban_constraints = GenreConstraints(
        ...     allowed_elements=["商战", "职场", "创业", "投资"],
        ...     forbidden_elements=["修炼", "灵气", "法宝", "宗门"],
        ...     violation_severity={
        ...         "修炼": ViolationSeverity.CRITICAL,
        ...         "灵气": ViolationSeverity.CRITICAL
        ...     }
        ... )
    """
    
    # 元素约束
    allowed_elements: List[str] = field(default_factory=list)
    forbidden_elements: List[str] = field(default_factory=list)
    
    # 场景约束
    allowed_scenes: List[str] = field(default_factory=list)
    forbidden_scenes: List[str] = field(default_factory=list)
    
    # 剧情设定约束
    allowed_plot_devices: List[str] = field(default_factory=list)
    forbidden_plot_devices: List[str] = field(default_factory=list)
    
    # 违规严重程度
    violation_severity: Dict[str, ViolationSeverity] = field(default_factory=dict)
    
    # 例外规则
    exceptions: List[ConstraintException] = field(default_factory=list)
    
    def validate(self, content: str, context: Optional[Dict] = None) -> List['ConstraintViolation']:
        """验证内容是否符合约束
        
        Args:
            content: 要验证的内容（章节文本）
            context: 上下文信息（可选）
        
        Returns:
            违规列表，空列表表示无违规
        """
        violations = []
        
        # 检查禁止元素
        for element in self.forbidden_elements:
            if self._contains_element(content, element):
                # 检查是否有例外规则
                if not self._check_exceptions(element, context):
                    severity = self.violation_severity.get(
                        element,
                        ViolationSeverity.HIGH
                    )
                    
                    violations.append(ConstraintViolation(
                        type="forbidden_element",
                        element=element,
                        severity=severity,
                        evidence=self._extract_evidence(content, element),
                        message=f"检测到禁止元素: {element}"
                    ))
        
        # 检查禁止场景
        for scene in self.forbidden_scenes:
            if self._contains_scene(content, scene):
                if not self._check_exceptions(scene, context):
                    violations.append(ConstraintViolation(
                        type="forbidden_scene",
                        element=scene,
                        severity=ViolationSeverity.HIGH,
                        evidence=self._extract_evidence(content, scene),
                        message=f"检测到禁止场景: {scene}"
                    ))
        
        return violations
    
    def _contains_element(self, content: str, element: str) -> bool:
        """检测内容是否包含元素
        
        使用简单的关键词匹配 + 可选的LLM验证
        """
        # 简单关键词匹配
        if element in content:
            return True
        
        # 相关词匹配
        related_words = self._get_related_words(element)
        for word in related_words:
            if word in content:
                return True
        
        return False
    
    def _get_related_words(self, element: str) -> List[str]:
        """获取相关词
        
        例如："修炼" -> ["修行", "炼化", "突破境界"]
        """
        RELATED_WORDS = {
            "修炼": ["修行", "炼化", "突破境界", "炼气", "筑基"],
            "灵气": ["天地灵气", "灵力", "真气"],
            "法宝": ["灵宝", "仙器", "神兵"],
            "宗门": ["仙宗", "道门", "魔教"],
            # ... 更多映射
        }
        
        return RELATED_WORDS.get(element, [])
    
    def _contains_scene(self, content: str, scene: str) -> bool:
        """检测是否包含场景类型"""
        # 场景检测需要更复杂的逻辑，可能需要LLM
        # 暂时使用关键词
        return scene in content
    
    def _check_exceptions(self, element: str, context: Optional[Dict]) -> bool:
        """检查是否满足例外条件"""
        if not context:
            return False
        
        for exception in self.exceptions:
            if element in exception.allows:
                # 检查条件是否满足
                if self._eval_condition(exception.condition, context):
                    return True
        
        return False
    
    def _eval_condition(self, condition: str, context: Dict) -> bool:
        """评估例外条件"""
        # 简单的条件评估
        # 例如: "subgenre == 'urban_xiuxian'"
        try:
            return eval(condition, {}, context)
        except:
            return False
    
    def _extract_evidence(self, content: str, element: str, max_length: int = 100) -> str:
        """提取文本证据"""
        idx = content.find(element)
        if idx == -1:
            return ""
        
        start = max(0, idx - 50)
        end = min(len(content), idx + 50)
        
        excerpt = content[start:end]
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(content):
            excerpt = excerpt + "..."
        
        return excerpt
    
    def to_prompt(self) -> str:
        """转换为Prompt约束描述"""
        prompt = "【题材约束】（严格遵守）\n"
        
        if self.allowed_elements:
            allowed = ", ".join(self.allowed_elements[:10])
            prompt += f"✅ 允许：{allowed}\n"
        
        if self.forbidden_elements:
            forbidden = ", ".join(self.forbidden_elements[:10])
            prompt += f"❌ 禁止：{forbidden}\n"
        
        if self.forbidden_scenes:
            scenes = ", ".join(self.forbidden_scenes[:5])
            prompt += f"❌ 禁止场景：{scenes}\n"
        
        return prompt


@dataclass
class ConstraintViolation:
    """约束违规
    
    记录一次约束违规的详细信息。
    
    Attributes:
        type: 违规类型
        element: 违规元素
        severity: 严重程度
        evidence: 文本证据
        message: 违规描述
        location: 违规位置（可选）
    """
    type: str
    element: str
    severity: ViolationSeverity
    evidence: str
    message: str
    location: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "type": self.type,
            "element": self.element,
            "severity": self.severity.value,
            "evidence": self.evidence,
            "message": self.message,
            "location": self.location
        }
    
    def is_critical(self) -> bool:
        """是否为严重违规"""
        return self.severity == ViolationSeverity.CRITICAL
```

---

### 3. ProgressionModel（进阶模型抽象）

**位置**: `AI-Novel-Runtime/runtime/genre/progression.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class TransitionType(Enum):
    """晋级类型"""
    NORMAL = "normal"          # 正常晋级
    BREAKTHROUGH = "breakthrough"  # 突破性晋级
    RAPID = "rapid"            # 快速晋级
    REGRESSION = "regression"  # 退步/降级


@dataclass
class TransitionContext:
    """晋级上下文
    
    提供晋级验证所需的上下文信息。
    
    Attributes:
        chapters_passed: 经过的章节数
        has_opportunity: 是否有机缘/机会
        has_mentor: 是否有导师指导
        has_resources: 是否有资源支持
        story_state: 当前故事状态
        custom_context: 自定义上下文
    """
    chapters_passed: int
    has_opportunity: bool = False
    has_mentor: bool = False
    has_resources: bool = False
    story_state: Optional['StoryState'] = None
    custom_context: Dict = None


class ProgressionModel(ABC):
    """进阶模型抽象基类
    
    定义角色在该题材中的成长/进阶体系。
    不同题材有不同的进阶语义：
    - 都市：财富进阶（贫困→小康→富裕→富豪）
    - 玄幻：境界进阶（炼气→筑基→金丹→元婴）
    - 职场：地位进阶（实习生→员工→主管→经理）
    - 科幻：文明进阶（行星→恒星→星系→宇宙）
    
    所有具体的进阶模型必须继承此类并实现抽象方法。
    """
    
    @abstractmethod
    def get_tiers(self) -> List[str]:
        """获取所有等级/阶段
        
        返回从低到高的所有等级列表。
        
        Returns:
            等级列表，如["炼气期", "筑基期", "金丹期"]
        """
        pass
    
    @abstractmethod
    def validate_transition(self, 
                           from_tier: str, 
                           to_tier: str, 
                           context: TransitionContext) -> 'TransitionValidation':
        """验证晋级是否合理
        
        检查从from_tier到to_tier的晋级是否符合该题材的规则。
        
        Args:
            from_tier: 当前等级
            to_tier: 目标等级
            context: 晋级上下文
        
        Returns:
            TransitionValidation对象，包含验证结果
        """
        pass
    
    @abstractmethod
    def get_tier_description(self, tier: str) -> str:
        """获取等级描述
        
        Args:
            tier: 等级名称
        
        Returns:
            等级的详细描述
        """
        pass
    
    def get_tier_index(self, tier: str) -> int:
        """获取等级索引
        
        Args:
            tier: 等级名称
        
        Returns:
            等级索引（0-based）
        
        Raises:
            ValueError: 如果等级不存在
        """
        tiers = self.get_tiers()
        try:
            return tiers.index(tier)
        except ValueError:
            raise ValueError(f"Tier '{tier}' not found in progression model")
    
    def get_next_tier(self, current_tier: str) -> Optional[str]:
        """获取下一个等级
        
        Args:
            current_tier: 当前等级
        
        Returns:
            下一个等级，如果已是最高则返回None
        """
        tiers = self.get_tiers()
        try:
            idx = tiers.index(current_tier)
            if idx < len(tiers) - 1:
                return tiers[idx + 1]
            return None
        except ValueError:
            raise ValueError(f"Tier '{current_tier}' not found")
    
    def calculate_jump(self, from_tier: str, to_tier: str) -> int:
        """计算等级跨度
        
        Args:
            from_tier: 起始等级
            to_tier: 目标等级
        
        Returns:
            跨度（正数表示升级，负数表示降级）
        """
        from_idx = self.get_tier_index(from_tier)
        to_idx = self.get_tier_index(to_tier)
        return to_idx - from_idx
    
    def to_prompt(self) -> str:
        """转换为Prompt描述"""
        tiers = self.get_tiers()
        progression_line = " → ".join(tiers)
        
        return f"""
【进阶体系】
等级: {progression_line}
说明: {self.get_tier_description(tiers[0])}（起点） → {self.get_tier_description(tiers[-1])}（终点）
"""


@dataclass
class TransitionValidation:
    """晋级验证结果
    
    Attributes:
        is_valid: 是否合理
        transition_type: 晋级类型
        reason: 原因说明
        suggestions: 改进建议
        required_chapters: 建议需要的章节数
    """
    is_valid: bool
    transition_type: TransitionType
    reason: str
    suggestions: List[str] = None
    required_chapters: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "transition_type": self.transition_type.value,
            "reason": self.reason,
            "suggestions": self.suggestions or [],
            "required_chapters": self.required_chapters
        }
```

现在继续生成具体的进阶模型实现...

```python
class WealthProgressionModel(ProgressionModel):
    """都市财富进阶模型
    
    定义都市题材的财富进阶体系。
    
    等级:
    1. 贫困线（月收入<3000）
    2. 温饱（3000-8000）
    3. 小康（8000-20000）
    4. 中产（2-10万/月）
    5. 富裕（10-50万/月）
    6. 富豪（50-500万/月）
    7. 资本家（500万+/月）
    8. 商业帝国（亿级月收入）
    
    规则:
    - 每3章最多跨1级（正常情况）
    - 有重大机遇可跨2级
    - 一夜暴富跨3级需要极特殊情况（如继承、中彩票，但通常不推荐）
    """
    
    def get_tiers(self) -> List[str]:
        return [
            "贫困线",
            "温饱",
            "小康",
            "中产",
            "富裕",
            "富豪",
            "资本家",
            "商业帝国"
        ]
    
    def validate_transition(self, 
                           from_tier: str, 
                           to_tier: str, 
                           context: TransitionContext) -> TransitionValidation:
        """验证财富晋级"""
        
        jump = self.calculate_jump(from_tier, to_tier)
        
        # 降级（失败、破产）
        if jump < 0:
            return TransitionValidation(
                is_valid=True,
                transition_type=TransitionType.REGRESSION,
                reason="财富可以因失败而降低"
            )
        
        # 不变
        if jump == 0:
            return TransitionValidation(
                is_valid=True,
                transition_type=TransitionType.NORMAL,
                reason="财富保持不变"
            )
        
        # 正常晋级（跨1级）
        if jump == 1:
            required_chapters = 3
            if context.chapters_passed >= required_chapters:
                return TransitionValidation(
                    is_valid=True,
                    transition_type=TransitionType.NORMAL,
                    reason=f"经过{context.chapters_passed}章，正常晋级1级",
                    required_chapters=required_chapters
                )
            else:
                return TransitionValidation(
                    is_valid=False,
                    transition_type=TransitionType.RAPID,
                    reason=f"晋级过快，建议至少{required_chapters}章",
                    required_chapters=required_chapters
                )
        
        # 快速晋级（跨2级）
        if jump == 2:
            if context.has_opportunity:
                required_chapters = 5
                if context.chapters_passed >= required_chapters:
                    return TransitionValidation(
                        is_valid=True,
                        transition_type=TransitionType.BREAKTHROUGH,
                        reason=f"有重大机遇，可以跨2级",
                        required_chapters=required_chapters
                    )
                else:
                    return TransitionValidation(
                        is_valid=False,
                        transition_type=TransitionType.RAPID,
                        reason=f"即使有机遇，建议至少{required_chapters}章",
                        suggestions=["增加详细的财富积累过程描写"],
                        required_chapters=required_chapters
                    )
            else:
                return TransitionValidation(
                    is_valid=False,
                    transition_type=TransitionType.RAPID,
                    reason="跨2级需要重大机遇支撑",
                    suggestions=[
                        "增加机遇情节（如遇到贵人、获得资源）",
                        "或者分步骤晋级"
                    ]
                )
        
        # 一夜暴富（跨3级以上）
        if jump >= 3:
            return TransitionValidation(
                is_valid=False,
                transition_type=TransitionType.RAPID,
                reason="跨度过大，不符合现实逻辑",
                suggestions=[
                    "分多个阶段晋级",
                    "增加详细的财富积累过程",
                    "避免一夜暴富情节（除非合理解释如继承）"
                ]
            )
        
        return TransitionValidation(
            is_valid=False,
            transition_type=TransitionType.NORMAL,
            reason="未知情况"
        )
    
    def get_tier_description(self, tier: str) -> str:
        """获取财富等级描述"""
        descriptions = {
            "贫困线": "月收入不足3000元，生活拮据",
            "温饱": "月收入3000-8000元，基本生活保障",
            "小康": "月收入8000-20000元，生活舒适",
            "中产": "月收入2-10万元，财务相对自由",
            "富裕": "月收入10-50万元，高品质生活",
            "富豪": "月收入50-500万元，社会上层",
            "资本家": "月收入500万以上，掌控大量资本",
            "商业帝国": "月收入亿级，行业领袖"
        }
        return descriptions.get(tier, "未知等级")


class PowerProgressionModel(ProgressionModel):
    """玄幻力量进阶模型
    
    定义玄幻题材的境界进阶体系。
    
    等级:
    1. 炼气期（1-9层）
    2. 筑基期（前/中/后期）
    3. 金丹期（初/中/后期）
    4. 元婴期（初/中/后期）
    5. 化神期
    6. 合体期
    7. 渡劫期
    8. 大乘期
    
    规则:
    - 每10-15章可突破一个大境界
    - 跨大境界需要机缘
    - 同境界内可快速提升小境界
    - 跨2个大境界通常不合理（除非特殊情节）
    """
    
    def get_tiers(self) -> List[str]:
        return [
            "炼气期",
            "筑基期",
            "金丹期",
            "元婴期",
            "化神期",
            "合体期",
            "渡劫期",
            "大乘期"
        ]
    
    def validate_transition(self, 
                           from_tier: str, 
                           to_tier: str, 
                           context: TransitionContext) -> TransitionValidation:
        """验证境界晋级"""
        
        jump = self.calculate_jump(from_tier, to_tier)
        
        # 降级（走火入魔、受伤）
        if jump < 0:
            return TransitionValidation(
                is_valid=True,
                transition_type=TransitionType.REGRESSION,
                reason="境界可因走火入魔或重伤而跌落"
            )
        
        # 不变
        if jump == 0:
            return TransitionValidation(
                is_valid=True,
                transition_type=TransitionType.NORMAL,
                reason="境界保持不变"
            )
        
        # 正常晋级（跨1个大境界）
        if jump == 1:
            required_chapters = 10
            
            if context.chapters_passed >= required_chapters:
                if context.has_opportunity or context.has_resources:
                    return TransitionValidation(
                        is_valid=True,
                        transition_type=TransitionType.BREAKTHROUGH,
                        reason=f"经过{context.chapters_passed}章积累，且有机缘/资源，成功突破",
                        required_chapters=required_chapters
                    )
                else:
                    return TransitionValidation(
                        is_valid=False,
                        transition_type=TransitionType.RAPID,
                        reason="突破大境界需要机缘或丹药等资源",
                        suggestions=["增加机缘情节", "或增加获得丹药/功法情节"]
                    )
            else:
                return TransitionValidation(
                    is_valid=False,
                    transition_type=TransitionType.RAPID,
                    reason=f"突破过快，建议至少{required_chapters}章",
                    required_chapters=required_chapters
                )
        
        # 连跨2个大境界
        if jump == 2:
            if context.has_opportunity and context.chapters_passed >= 20:
                return TransitionValidation(
                    is_valid=True,
                    transition_type=TransitionType.BREAKTHROUGH,
                    reason="特殊机缘（如吞噬异火、传承）可连跨2境界",
                    suggestions=["需要详细描写突破过程", "机缘必须足够重大"]
                )
            else:
                return TransitionValidation(
                    is_valid=False,
                    transition_type=TransitionType.RAPID,
                    reason="连跨2境界需要极特殊机缘且经过足够章节",
                    suggestions=["分步骤突破", "或增加重大机缘情节"]
                )
        
        # 跨3个以上大境界
        if jump >= 3:
            return TransitionValidation(
                is_valid=False,
                transition_type=TransitionType.RAPID,
                reason="跨度过大，不符合玄幻修炼逻辑",
                suggestions=["分多个阶段突破", "增加详细的修炼过程"]
            )
        
        return TransitionValidation(
            is_valid=False,
            transition_type=TransitionType.NORMAL,
            reason="未知情况"
        )
    
    def get_tier_description(self, tier: str) -> str:
        """获取境界描述"""
        descriptions = {
            "炼气期": "修炼入门，淬炼经脉，吸收灵气",
            "筑基期": "筑牢根基，可御剑飞行，寿命200年",
            "金丹期": "凝结金丹，脱胎换骨，寿命500年",
            "元婴期": "元婴出窍，神通广大，寿命1000年",
            "化神期": "元神化神，掌控天地之力",
            "合体期": "人道合一，接近仙人",
            "渡劫期": "准备渡劫飞升",
            "大乘期": "已成陆地神仙，随时可飞升"
        }
        return descriptions.get(tier, "未知境界")
```

**文档未完待续...**

由于篇幅限制，我需要将这个详细设计文档分成多个文件。让我先提交当前的Genre系统详细设计第一部分。

