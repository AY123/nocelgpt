# Genre系统完整实施手册

**版本**: v1.0  
**制定日期**: 2026-09-18  
**实施阶段**: M1 Week 1-2  
**适用于**: AI辅助实施  
**状态**: 完整可执行  

---

## 📋 实施概览

### 目标

实现Genre-First架构的核心：Genre系统，包括题材配置、约束、进阶模型、注册表等。

**核心目标**:
1. ✅ 题材隔离（都市不生成修炼）
2. ✅ 题材约束（硬约束可阻断生成）
3. ✅ 题材专用（Prompt、进阶模型、验证器）
4. ✅ 题材检测（自动识别题材）

### 实施范围

**M1 Week 1-2要实现的模块**:
```
runtime/genre/
├── __init__.py           # 公共API
├── config.py             # GenreConfig
├── constraints.py        # GenreConstraints
├── progression.py        # ProgressionModel（抽象+2个具体）
├── registry.py           # GenreRegistry
├── detector.py           # GenreDetector
├── validator.py          # GenreValidator
└── configs/              # 题材配置目录
    ├── __init__.py
    ├── urban.py          # 都市配置
    └── xuanhuan.py       # 玄幻配置
```

**测试覆盖**:
```
tests/runtime/genre/
├── __init__.py
├── test_config.py
├── test_constraints.py
├── test_progression.py
├── test_registry.py
├── test_detector.py
├── test_validator.py
├── test_urban_config.py
└── test_xuanhuan_config.py
```

### 依赖关系

```
GenreConfig（核心）
  ↓
GenreConstraints + ProgressionModel
  ↓
GenreRegistry（单例，管理所有配置）
  ↓
GenreDetector（使用Registry）
  ↓
GenreValidator（使用GenreConfig）
  ↓
集成到Genesis和Production流程
```

---

## 🏗️ 模块1: GenreConfig（题材配置）

### 1.1 文件结构

**文件**: `runtime/genre/config.py`

### 1.2 完整实现

```python
# ============================================================
# 文件: AI-Novel-Runtime/runtime/genre/config.py
# 目的: 题材配置核心类
# 相关决策: Decision 1.1（Genre-First架构）
# ============================================================

from dataclasses import dataclass, field
from typing import Dict, List, Type, Optional, Callable
from enum import Enum


# ============================================================
# Enums
# ============================================================

class GenreID(Enum):
    """题材ID枚举
    
    定义系统支持的所有题材类型。
    
    Values:
        URBAN: 都市
        XUANHUAN: 玄幻
        XIANXIA: 仙侠
        WUXIA: 武侠
        SCIFI: 科幻
        HISTORY: 历史
        MILITARY: 军事
        GAME: 游戏
        SPORTS: 体育
        SUPERNATURAL: 灵异
        
    Example:
        >>> genre = GenreID.URBAN
        >>> genre.value
        'urban'
    """
    URBAN = "urban"
    XUANHUAN = "xuanhuan"
    XIANXIA = "xianxia"
    WUXIA = "wuxia"
    SCIFI = "scifi"
    HISTORY = "history"
    MILITARY = "military"
    GAME = "game"
    SPORTS = "sports"
    SUPERNATURAL = "supernatural"
    
    @classmethod
    def from_string(cls, value: str) -> 'GenreID':
        """从字符串创建
        
        Args:
            value: 题材字符串（如"urban"）
            
        Returns:
            GenreID枚举
            
        Raises:
            ValueError: 如果题材不存在
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_genres = [g.value for g in cls]
            raise ValueError(
                f"Invalid genre '{value}'. Valid genres: {valid_genres}"
            )


# ============================================================
# WorldviewFoundation
# ============================================================

@dataclass
class WorldviewFoundation:
    """世界观基础设定
    
    定义题材的基础世界观，包括时空、科技、社会结构等。
    
    Attributes:
        time_period: 时代背景（如"现代中国"、"架空古代"）
        technology_level: 科技水平（如"现代科技"、"古代冷兵器"）
        social_structure: 社会结构（如"现代社会"、"宗门体系"）
        supernatural_elements: 是否存在超自然元素
        power_source: 力量来源（如"灵气"、"科技"、"内力"，可选）
        geography_type: 地理类型（"realistic"或"fictional"）
        
    Example:
        >>> foundation = WorldviewFoundation(
        ...     time_period="现代中国",
        ...     technology_level="现代科技",
        ...     social_structure="现代社会",
        ...     supernatural_elements=False,
        ...     power_source=None,
        ...     geography_type="realistic"
        ... )
    """
    time_period: str
    technology_level: str
    social_structure: str
    supernatural_elements: bool
    power_source: Optional[str] = None
    geography_type: str = "realistic"
    
    def to_prompt(self) -> str:
        """转换为Prompt描述"""
        supernatural = "存在" if self.supernatural_elements else "不存在"
        power = f"\n力量来源: {self.power_source}" if self.power_source else ""
        
        return f"""【世界观基础】
时代背景: {self.time_period}
科技水平: {self.technology_level}
社会结构: {self.social_structure}
超自然元素: {supernatural}{power}
地理类型: {self.geography_type}"""


# ============================================================
# GenreConfig
# ============================================================

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
        progression_model: 进阶模型类（用于角色成长验证）
        prompt_templates: 题材专用Prompt模板字典
        worldview_foundation: 世界观基础设定
        target_audience: 目标读者群体描述
        typical_themes: 典型主题列表
        prohibited_content: 禁止内容列表
        metadata: 扩展元数据
        
    Example:
        基本用法：
        >>> from runtime.genre.constraints import UrbanConstraints
        >>> from runtime.genre.progression import WealthProgressionModel
        >>> 
        >>> config = GenreConfig(
        ...     genre_id=GenreID.URBAN,
        ...     genre_name="都市",
        ...     genre_name_en="Urban",
        ...     description="现代都市生活题材",
        ...     constraints=UrbanConstraints(),
        ...     progression_model=WealthProgressionModel,
        ...     prompt_templates={
        ...         "outline": "都市大纲Prompt...",
        ...         "chapter": "都市章节Prompt..."
        ...     },
        ...     worldview_foundation=WorldviewFoundation(...)
        ... )
        >>> config.validate()
        True
        
        获取Prompt模板：
        >>> template = config.get_prompt_template("outline")
        >>> print(template[:50])
        都市大纲Prompt...
        
    Notes:
        - genre_id必须是GenreID枚举成员
        - progression_model必须是ProgressionModel的子类
        - constraints不能为None
        - prompt_templates必须至少包含"outline"和"chapter"
        
    See Also:
        - GenreConstraints: 题材约束定义
        - ProgressionModel: 进阶模型抽象基类
        - GenreRegistry: 题材注册表
    """
    
    # 基础信息
    genre_id: GenreID
    genre_name: str
    genre_name_en: str
    description: str
    
    # 核心组件（必需）
    constraints: 'GenreConstraints'
    progression_model: Type['ProgressionModel']
    prompt_templates: Dict[str, str]
    worldview_foundation: WorldviewFoundation
    
    # 扩展信息（可选）
    target_audience: Dict[str, str] = field(default_factory=dict)
    typical_themes: List[str] = field(default_factory=list)
    prohibited_content: List[str] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后验证"""
        self._validate()
    
    def _validate(self):
        """验证配置完整性
        
        Raises:
            ValueError: 如果配置无效
        """
        # 验证基础字段
        if not self.genre_name:
            raise ValueError("genre_name cannot be empty")
        
        if not self.genre_name_en:
            raise ValueError("genre_name_en cannot be empty")
        
        # 验证核心组件
        if self.constraints is None:
            raise ValueError(
                f"Genre {self.genre_id.value} must have constraints"
            )
        
        if self.progression_model is None:
            raise ValueError(
                f"Genre {self.genre_id.value} must have progression_model"
            )
        
        # 验证Prompt模板
        required_templates = ["outline", "chapter"]
        for template_name in required_templates:
            if template_name not in self.prompt_templates:
                raise ValueError(
                    f"Genre {self.genre_id.value} must have "
                    f"'{template_name}' prompt template"
                )
        
        # 验证世界观
        if self.worldview_foundation is None:
            raise ValueError(
                f"Genre {self.genre_id.value} must have worldview_foundation"
            )
    
    def get_prompt_template(self, stage: str) -> str:
        """获取Prompt模板
        
        Args:
            stage: 阶段名称（outline/chapter/revision/...）
            
        Returns:
            Prompt模板字符串
            
        Raises:
            KeyError: 如果stage不存在
            
        Example:
            >>> template = config.get_prompt_template("outline")
            >>> print(len(template))
            1500
        """
        if stage not in self.prompt_templates:
            raise KeyError(
                f"Prompt template '{stage}' not found for genre "
                f"{self.genre_id.value}"
            )
        
        return self.prompt_templates[stage]
    
    def get_progression_instance(self) -> 'ProgressionModel':
        """获取进阶模型实例
        
        Returns:
            ProgressionModel实例
            
        Example:
            >>> model = config.get_progression_instance()
            >>> tiers = model.get_tiers()
            >>> print(tiers)
            ['贫困线', '温饱', '小康', '中产', ...]
        """
        return self.progression_model()
    
    def validate_content(self, content: str, context: Optional[Dict] = None) -> List['ConstraintViolation']:
        """验证内容是否符合题材约束
        
        Args:
            content: 要验证的内容（章节文本）
            context: 上下文信息（可选）
            
        Returns:
            违规列表，空列表表示无违规
            
        Example:
            >>> violations = config.validate_content(chapter_text)
            >>> if violations:
            ...     for v in violations:
            ...         print(f"{v.severity}: {v.message}")
        """
        return self.constraints.validate(content, context)
    
    def to_dict(self) -> Dict:
        """转换为字典（用于序列化）
        
        Returns:
            包含配置信息的字典
        """
        return {
            "genre_id": self.genre_id.value,
            "genre_name": self.genre_name,
            "genre_name_en": self.genre_name_en,
            "description": self.description,
            "target_audience": self.target_audience,
            "typical_themes": self.typical_themes,
            "prohibited_content": self.prohibited_content,
            "metadata": self.metadata,
            "worldview": {
                "time_period": self.worldview_foundation.time_period,
                "technology_level": self.worldview_foundation.technology_level,
                "social_structure": self.worldview_foundation.social_structure,
                "supernatural_elements": self.worldview_foundation.supernatural_elements,
                "power_source": self.worldview_foundation.power_source,
                "geography_type": self.worldview_foundation.geography_type
            }
        }
    
    def to_prompt_context(self) -> str:
        """转换为Prompt上下文描述
        
        返回一段完整的题材描述，用于注入到生成Prompt中。
        
        Returns:
            题材上下文字符串
        """
        context = f"""【题材】{self.genre_name}（{self.genre_name_en}）

【描述】
{self.description}

{self.worldview_foundation.to_prompt()}

【约束】（严格遵守）
{self.constraints.to_prompt()}

【典型主题】
{', '.join(self.typical_themes[:5]) if self.typical_themes else '无'}

【禁止内容】
{', '.join(self.prohibited_content[:5]) if self.prohibited_content else '无'}
"""
        return context


# ============================================================
# 使用示例
# ============================================================

# if __name__ == "__main__":
#     from runtime.genre.constraints import UrbanConstraints
#     from runtime.genre.progression import WealthProgressionModel
#     
#     # 示例1：创建都市题材配置
#     urban_foundation = WorldviewFoundation(
#         time_period="现代中国（2020-2030）",
#         technology_level="现代科技",
#         social_structure="现代社会",
#         supernatural_elements=False,
#         power_source=None,
#         geography_type="realistic"
#     )
#     
#     urban_config = GenreConfig(
#         genre_id=GenreID.URBAN,
#         genre_name="都市",
#         genre_name_en="Urban",
#         description="现代都市生活题材，聚焦现实社会中的奋斗、情感、商业",
#         constraints=UrbanConstraints(),
#         progression_model=WealthProgressionModel,
#         prompt_templates={
#             "outline": "都市大纲Prompt...",
#             "chapter": "都市章节Prompt..."
#         },
#         worldview_foundation=urban_foundation,
#         typical_themes=["创业", "职场", "情感", "家庭", "商战"],
#         prohibited_content=["修炼", "异能", "穿越", "重生"]
#     )
#     
#     # 示例2：验证配置
#     urban_config.validate()  # 不抛异常表示验证通过
#     
#     # 示例3：获取Prompt模板
#     template = urban_config.get_prompt_template("chapter")
#     print(f"章节Prompt模板长度: {len(template)}")
#     
#     # 示例4：获取进阶模型
#     progression = urban_config.get_progression_instance()
#     tiers = progression.get_tiers()
#     print(f"财富等级: {tiers}")
#     
#     # 示例5：验证内容
#     test_content = "陈阳开始修炼灵气..."
#     violations = urban_config.validate_content(test_content)
#     if violations:
#         print(f"发现{len(violations)}个违规")
#         for v in violations:
#             print(f"  - {v.severity.value}: {v.message}")
```

### 1.3 测试代码

**文件**: `tests/runtime/genre/test_config.py`

```python
# ============================================================
# 文件: tests/runtime/genre/test_config.py
# 目的: 测试GenreConfig
# ============================================================

import pytest
from runtime.genre.config import (
    GenreID,
    GenreConfig,
    WorldviewFoundation
)
from runtime.genre.constraints import UrbanConstraints
from runtime.genre.progression import WealthProgressionModel


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def urban_foundation():
    """都市世界观基础"""
    return WorldviewFoundation(
        time_period="现代中国",
        technology_level="现代科技",
        social_structure="现代社会",
        supernatural_elements=False,
        power_source=None,
        geography_type="realistic"
    )


@pytest.fixture
def urban_config(urban_foundation):
    """都市题材配置"""
    return GenreConfig(
        genre_id=GenreID.URBAN,
        genre_name="都市",
        genre_name_en="Urban",
        description="现代都市生活题材",
        constraints=UrbanConstraints(),
        progression_model=WealthProgressionModel,
        prompt_templates={
            "outline": "都市大纲模板",
            "chapter": "都市章节模板"
        },
        worldview_foundation=urban_foundation
    )


# ============================================================
# 基础功能测试
# ============================================================

class TestGenreConfigBasics:
    """测试GenreConfig基础功能"""
    
    def test_creation(self, urban_config):
        """测试创建配置"""
        assert urban_config.genre_id == GenreID.URBAN
        assert urban_config.genre_name == "都市"
        assert urban_config.genre_name_en == "Urban"
    
    def test_validation_success(self, urban_config):
        """测试验证成功"""
        # 不应抛出异常
        urban_config._validate()
    
    def test_validation_failure_no_genre_name(self, urban_foundation):
        """测试验证失败：无题材名称"""
        with pytest.raises(ValueError, match="genre_name cannot be empty"):
            GenreConfig(
                genre_id=GenreID.URBAN,
                genre_name="",
                genre_name_en="Urban",
                description="测试",
                constraints=UrbanConstraints(),
                progression_model=WealthProgressionModel,
                prompt_templates={"outline": "test", "chapter": "test"},
                worldview_foundation=urban_foundation
            )
    
    def test_validation_failure_no_constraints(self, urban_foundation):
        """测试验证失败：无约束"""
        with pytest.raises(ValueError, match="must have constraints"):
            GenreConfig(
                genre_id=GenreID.URBAN,
                genre_name="都市",
                genre_name_en="Urban",
                description="测试",
                constraints=None,
                progression_model=WealthProgressionModel,
                prompt_templates={"outline": "test", "chapter": "test"},
                worldview_foundation=urban_foundation
            )
    
    def test_validation_failure_missing_template(self, urban_foundation):
        """测试验证失败：缺少Prompt模板"""
        with pytest.raises(ValueError, match="must have 'chapter' prompt template"):
            GenreConfig(
                genre_id=GenreID.URBAN,
                genre_name="都市",
                genre_name_en="Urban",
                description="测试",
                constraints=UrbanConstraints(),
                progression_model=WealthProgressionModel,
                prompt_templates={"outline": "test"},  # 缺少chapter
                worldview_foundation=urban_foundation
            )


# ============================================================
# 方法测试
# ============================================================

class TestGenreConfigMethods:
    """测试GenreConfig的方法"""
    
    def test_get_prompt_template_success(self, urban_config):
        """测试获取Prompt模板成功"""
        template = urban_config.get_prompt_template("outline")
        assert template == "都市大纲模板"
        
        template = urban_config.get_prompt_template("chapter")
        assert template == "都市章节模板"
    
    def test_get_prompt_template_failure(self, urban_config):
        """测试获取不存在的Prompt模板"""
        with pytest.raises(KeyError, match="Prompt template 'nonexistent' not found"):
            urban_config.get_prompt_template("nonexistent")
    
    def test_get_progression_instance(self, urban_config):
        """测试获取进阶模型实例"""
        progression = urban_config.get_progression_instance()
        assert progression is not None
        assert hasattr(progression, 'get_tiers')
        
        tiers = progression.get_tiers()
        assert len(tiers) > 0
        assert "贫困线" in tiers or "温饱" in tiers
    
    def test_validate_content(self, urban_config):
        """测试内容验证"""
        # 合法内容
        valid_content = "陈阳开始创业，成立了自己的公司。"
        violations = urban_config.validate_content(valid_content)
        assert len(violations) == 0
        
        # 非法内容（包含修炼）
        invalid_content = "陈阳开始修炼灵气，突破到筑基期。"
        violations = urban_config.validate_content(invalid_content)
        assert len(violations) > 0


# ============================================================
# 序列化测试
# ============================================================

class TestGenreConfigSerialization:
    """测试GenreConfig的序列化"""
    
    def test_to_dict(self, urban_config):
        """测试to_dict方法"""
        data = urban_config.to_dict()
        
        assert data["genre_id"] == "urban"
        assert data["genre_name"] == "都市"
        assert data["genre_name_en"] == "Urban"
        assert "worldview" in data
        assert data["worldview"]["time_period"] == "现代中国"
    
    def test_to_prompt_context(self, urban_config):
        """测试to_prompt_context方法"""
        context = urban_config.to_prompt_context()
        
        assert "都市" in context
        assert "Urban" in context
        assert "现代中国" in context
        assert "约束" in context


# ============================================================
# GenreID测试
# ============================================================

class TestGenreID:
    """测试GenreID枚举"""
    
    def test_from_string_success(self):
        """测试从字符串创建成功"""
        genre = GenreID.from_string("urban")
        assert genre == GenreID.URBAN
        
        genre = GenreID.from_string("URBAN")  # 大写也可以
        assert genre == GenreID.URBAN
    
    def test_from_string_failure(self):
        """测试从无效字符串创建"""
        with pytest.raises(ValueError, match="Invalid genre"):
            GenreID.from_string("invalid_genre")
```

---

## 🔒 模块2: GenreConstraints（题材约束）

### 2.1 文件结构

**文件**: `runtime/genre/constraints.py`

### 2.2 完整实现

```python
# ============================================================
# 文件: AI-Novel-Runtime/runtime/genre/constraints.py
# 目的: 题材约束系统
# 相关决策: Decision 1.1（Genre-First架构）
# ============================================================

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


# ============================================================
# Enums
# ============================================================

class ViolationSeverity(Enum):
    """违规严重程度
    
    定义约束违规的严重程度，用于决定是否阻断生成。
    
    Values:
        CRITICAL: 严重违规，必须阻断
        HIGH: 高度违规，强烈建议修改
        MEDIUM: 中度违规，建议修改
        LOW: 轻度违规，提示即可
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============================================================
# ConstraintException
# ============================================================

@dataclass
class ConstraintException:
    """约束例外规则
    
    定义某些特殊情况下可以违反约束。
    例如：都市题材一般禁止"修炼"，但"都市修仙"子类型允许。
    
    Attributes:
        condition: 触发条件（Python表达式字符串）
        allows: 允许的元素列表
        reason: 例外原因说明
        
    Example:
        >>> exception = ConstraintException(
        ...     condition="subgenre == 'urban_xiuxian'",
        ...     allows=["修炼", "灵气"],
        ...     reason="都市修仙是特殊子类型"
        ... )
    """
    condition: str
    allows: List[str]
    reason: str


# ============================================================
# ConstraintViolation
# ============================================================

@dataclass
class ConstraintViolation:
    """约束违规
    
    记录一次约束违规的详细信息。
    
    Attributes:
        type: 违规类型（forbidden_element/forbidden_scene/...）
        element: 违规元素
        severity: 严重程度
        evidence: 文本证据（违规内容的上下文）
        message: 违规描述消息
        location: 违规位置（可选，如章节号、段落号）
        
    Example:
        >>> violation = ConstraintViolation(
        ...     type="forbidden_element",
        ...     element="修炼",
        ...     severity=ViolationSeverity.CRITICAL,
        ...     evidence="...陈阳开始修炼灵气...",
        ...     message="检测到禁止元素: 修炼"
        ... )
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
    
    def is_blocking(self) -> bool:
        """是否应该阻断生成
        
        CRITICAL和HIGH都应该阻断。
        """
        return self.severity in [ViolationSeverity.CRITICAL, ViolationSeverity.HIGH]


# ============================================================
# GenreConstraints（抽象基类）
# ============================================================

@dataclass
class GenreConstraints:
    """题材约束（基类）
    
    定义题材的硬约束，用于验证内容是否符合题材规范。
    约束分为允许和禁止两个维度。
    
    所有具体的题材约束类（如UrbanConstraints）应继承此类。
    
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
        >>> constraints = GenreConstraints(
        ...     allowed_elements=["商战", "创业"],
        ...     forbidden_elements=["修炼", "灵气"],
        ...     violation_severity={"修炼": ViolationSeverity.CRITICAL}
        ... )
        >>> violations = constraints.validate("陈阳开始修炼...")
        >>> assert len(violations) > 0
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
    
    # 违规严重程度映射
    violation_severity: Dict[str, ViolationSeverity] = field(default_factory=dict)
    
    # 例外规则
    exceptions: List[ConstraintException] = field(default_factory=list)
    
    def validate(self, content: str, context: Optional[Dict] = None) -> List[ConstraintViolation]:
        """验证内容是否符合约束
        
        Args:
            content: 要验证的内容（章节文本）
            context: 上下文信息（可选），如{"chapter_num": 5, "subgenre": "urban"}
            
        Returns:
            违规列表，空列表表示无违规
            
        Example:
            >>> violations = constraints.validate("陈阳开始修炼灵气...")
            >>> for v in violations:
            ...     print(f"{v.severity.value}: {v.message}")
            critical: 检测到禁止元素: 修炼
            critical: 检测到禁止元素: 灵气
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
        
        # 检查禁止剧情设定
        for device in self.forbidden_plot_devices:
            if self._contains_plot_device(content, device):
                if not self._check_exceptions(device, context):
                    violations.append(ConstraintViolation(
                        type="forbidden_plot_device",
                        element=device,
                        severity=ViolationSeverity.MEDIUM,
                        evidence=self._extract_evidence(content, device),
                        message=f"检测到禁止剧情设定: {device}"
                    ))
        
        return violations
    
    def _contains_element(self, content: str, element: str) -> bool:
        """检测内容是否包含元素
        
        使用简单的关键词匹配 + 相关词匹配。
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
        
        子类可以覆盖此方法提供题材专用的相关词映射。
        """
        # 默认的相关词映射
        RELATED_WORDS = {
            "修炼": ["修行", "炼化", "突破境界", "炼气", "筑基", "淬体"],
            "灵气": ["天地灵气", "灵力", "真气", "灵能"],
            "法宝": ["灵宝", "仙器", "神兵", "法器"],
            "宗门": ["仙宗", "道门", "魔教", "门派"],
            "神通": ["法术", "神技", "仙术"],
        }
        
        return RELATED_WORDS.get(element, [])
    
    def _contains_scene(self, content: str, scene: str) -> bool:
        """检测是否包含场景类型
        
        场景检测比元素检测更复杂，可能需要LLM辅助。
        当前使用简单的关键词匹配。
        """
        return scene in content
    
    def _contains_plot_device(self, content: str, device: str) -> bool:
        """检测是否包含剧情设定
        
        剧情设定检测也比较复杂，当前使用关键词匹配。
        """
        return device in content
    
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
        """评估例外条件
        
        例如: "subgenre == 'urban_xiuxian'"
        
        Args:
            condition: 条件表达式（Python表达式字符串）
            context: 上下文字典
            
        Returns:
            条件是否满足
        """
        try:
            # 使用eval评估条件（安全性：条件由配置定义，不是用户输入）
            return eval(condition, {}, context)
        except Exception:
            return False
    
    def _extract_evidence(self, content: str, element: str, max_length: int = 100) -> str:
        """提取文本证据
        
        提取包含违规元素的上下文片段。
        """
        idx = content.find(element)
        if idx == -1:
            # 尝试查找相关词
            related_words = self._get_related_words(element)
            for word in related_words:
                idx = content.find(word)
                if idx != -1:
                    break
        
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
        """转换为Prompt约束描述
        
        返回一段文本，用于注入到生成Prompt中。
        """
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


# ============================================================
# UrbanConstraints（都市约束）
# ============================================================

class UrbanConstraints(GenreConstraints):
    """都市题材约束
    
    定义都市题材的具体约束规则。
    
    Example:
        >>> constraints = UrbanConstraints()
        >>> violations = constraints.validate("陈阳开始修炼...")
        >>> assert len(violations) > 0
        >>> assert violations[0].element == "修炼"
    """
    
    def __init__(self):
        super().__init__(
            # 允许的元素
            allowed_elements=[
                "商战", "职场", "创业", "投资", "科技",
                "情感", "家庭", "友情", "爱情",
                "现实", "社会", "都市", "城市"
            ],
            
            # 禁止的元素（CRITICAL级别）
            forbidden_elements=[
                "修炼", "灵气", "法宝", "宗门", "神通",
                "仙人", "妖兽", "灵兽", "异界", "位面"
            ],
            
            # 允许的场景
            allowed_scenes=[
                "办公室", "会议室", "咖啡厅", "餐厅",
                "家中", "街道", "商场", "公园"
            ],
            
            # 禁止的场景
            forbidden_scenes=[
                "修炼洞府", "宗门大殿", "仙界", "秘境"
            ],
            
            # 允许的剧情设定
            allowed_plot_devices=[
                "重生", "系统", "金手指", "先知",  # 都市允许这些
                "创业", "商战", "阴谋", "竞争"
            ],
            
            # 禁止的剧情设定
            forbidden_plot_devices=[
                "飞升", "渡劫", "夺舍", "炼丹"
            ],
            
            # 违规严重程度
            violation_severity={
                "修炼": ViolationSeverity.CRITICAL,
                "灵气": ViolationSeverity.CRITICAL,
                "法宝": ViolationSeverity.CRITICAL,
                "宗门": ViolationSeverity.CRITICAL,
                "神通": ViolationSeverity.CRITICAL,
            },
            
            # 例外规则（都市修仙）
            exceptions=[
                ConstraintException(
                    condition="subgenre == 'urban_xiuxian'",
                    allows=["修炼", "灵气", "法宝"],
                    reason="都市修仙是特殊子类型"
                )
            ]
        )


# ============================================================
# XuanhuanConstraints（玄幻约束）
# ============================================================

class XuanhuanConstraints(GenreConstraints):
    """玄幻题材约束
    
    定义玄幻题材的具体约束规则。
    """
    
    def __init__(self):
        super().__init__(
            # 允许的元素
            allowed_elements=[
                "修炼", "灵气", "法宝", "宗门", "神通",
                "境界", "突破", "丹药", "功法", "武技",
                "异兽", "妖兽", "灵兽"
            ],
            
            # 禁止的元素
            forbidden_elements=[
                "手机", "电脑", "互联网", "科技公司",
                "股票", "基金", "创业", "商战"
            ],
            
            # 允许的场景
            allowed_scenes=[
                "修炼洞府", "宗门大殿", "秘境", "山脉",
                "城池", "客栈", "拍卖行"
            ],
            
            # 禁止的场景
            forbidden_scenes=[
                "办公室", "会议室", "咖啡厅", "现代都市"
            ],
            
            # 违规严重程度
            violation_severity={
                "手机": ViolationSeverity.CRITICAL,
                "电脑": ViolationSeverity.CRITICAL,
                "互联网": ViolationSeverity.CRITICAL,
            }
        )


# ============================================================
# 使用示例
# ============================================================

# if __name__ == "__main__":
#     # 示例1：都市约束验证
#     urban_constraints = UrbanConstraints()
#     
#     # 合法内容
#     valid_text = "陈阳开始创业，成立了科技公司。"
#     violations = urban_constraints.validate(valid_text)
#     print(f"合法内容违规数: {len(violations)}")  # 0
#     
#     # 非法内容
#     invalid_text = "陈阳开始修炼灵气，突破到筑基期。"
#     violations = urban_constraints.validate(invalid_text)
#     print(f"非法内容违规数: {len(violations)}")  # 2
#     for v in violations:
#         print(f"  - {v.severity.value}: {v.message}")
#     
#     # 示例2：例外规则
#     context = {"subgenre": "urban_xiuxian"}
#     violations = urban_constraints.validate(invalid_text, context)
#     print(f"都市修仙违规数: {len(violations)}")  # 0（例外规则生效）
```

### 2.3 测试代码

**文件**: `tests/runtime/genre/test_constraints.py`

```python
# ============================================================
# 文件: tests/runtime/genre/test_constraints.py
# 目的: 测试GenreConstraints
# ============================================================

import pytest
from runtime.genre.constraints import (
    GenreConstraints,
    UrbanConstraints,
    XuanhuanConstraints,
    ConstraintViolation,
    ViolationSeverity,
    ConstraintException
)


# ============================================================
# 基础功能测试
# ============================================================

class TestUrbanConstraints:
    """测试都市约束"""
    
    def test_creation(self):
        """测试创建约束"""
        constraints = UrbanConstraints()
        assert len(constraints.forbidden_elements) > 0
        assert "修炼" in constraints.forbidden_elements
        assert "商战" in constraints.allowed_elements
    
    def test_validate_valid_content(self):
        """测试验证合法内容"""
        constraints = UrbanConstraints()
        content = "陈阳开始创业，成立了科技公司，投资互联网项目。"
        
        violations = constraints.validate(content)
        assert len(violations) == 0
    
    def test_validate_invalid_content_single_violation(self):
        """测试验证非法内容：单个违规"""
        constraints = UrbanConstraints()
        content = "陈阳开始修炼灵气。"
        
        violations = constraints.validate(content)
        assert len(violations) >= 1
        
        # 检查第一个违规
        v = violations[0]
        assert v.element in ["修炼", "灵气"]
        assert v.severity == ViolationSeverity.CRITICAL
        assert v.is_critical()
        assert v.is_blocking()
    
    def test_validate_invalid_content_multiple_violations(self):
        """测试验证非法内容：多个违规"""
        constraints = UrbanConstraints()
        content = "陈阳在宗门修炼灵气，炼制法宝。"
        
        violations = constraints.validate(content)
        assert len(violations) >= 3  # 宗门、修炼、灵气、法宝
        
        # 所有都应该是CRITICAL
        for v in violations:
            assert v.severity == ViolationSeverity.CRITICAL
    
    def test_validate_with_exception(self):
        """测试验证：例外规则生效"""
        constraints = UrbanConstraints()
        content = "陈阳在都市中修炼灵气。"
        context = {"subgenre": "urban_xiuxian"}
        
        violations = constraints.validate(content, context)
        # 都市修仙允许修炼和灵气
        assert len(violations) == 0
    
    def test_evidence_extraction(self):
        """测试证据提取"""
        constraints = UrbanConstraints()
        content = "前面一些内容。" + "陈阳开始修炼灵气，突破境界。" + "后面一些内容。"
        
        violations = constraints.validate(content)
        assert len(violations) > 0
        
        v = violations[0]
        assert len(v.evidence) > 0
        assert v.element in v.evidence or any(
            word in v.evidence
            for word in constraints._get_related_words(v.element)
        )


# ============================================================
# 玄幻约束测试
# ============================================================

class TestXuanhuanConstraints:
    """测试玄幻约束"""
    
    def test_creation(self):
        """测试创建约束"""
        constraints = XuanhuanConstraints()
        assert "修炼" in constraints.allowed_elements
        assert "手机" in constraints.forbidden_elements
    
    def test_validate_valid_content(self):
        """测试验证合法内容"""
        constraints = XuanhuanConstraints()
        content = "陈阳在宗门修炼灵气，炼制丹药。"
        
        violations = constraints.validate(content)
        assert len(violations) == 0
    
    def test_validate_invalid_content(self):
        """测试验证非法内容"""
        constraints = XuanhuanConstraints()
        content = "陈阳拿出手机，打开电脑，查看股票行情。"
        
        violations = constraints.validate(content)
        assert len(violations) >= 2  # 手机、电脑


# ============================================================
# 违规对象测试
# ============================================================

class TestConstraintViolation:
    """测试ConstraintViolation"""
    
    def test_is_critical(self):
        """测试is_critical方法"""
        v = ConstraintViolation(
            type="test",
            element="test",
            severity=ViolationSeverity.CRITICAL,
            evidence="",
            message="test"
        )
        assert v.is_critical()
        
        v2 = ConstraintViolation(
            type="test",
            element="test",
            severity=ViolationSeverity.HIGH,
            evidence="",
            message="test"
        )
        assert not v2.is_critical()
    
    def test_is_blocking(self):
        """测试is_blocking方法"""
        # CRITICAL应该阻断
        v1 = ConstraintViolation(
            type="test",
            element="test",
            severity=ViolationSeverity.CRITICAL,
            evidence="",
            message="test"
        )
        assert v1.is_blocking()
        
        # HIGH应该阻断
        v2 = ConstraintViolation(
            type="test",
            element="test",
            severity=ViolationSeverity.HIGH,
            evidence="",
            message="test"
        )
        assert v2.is_blocking()
        
        # MEDIUM不阻断
        v3 = ConstraintViolation(
            type="test",
            element="test",
            severity=ViolationSeverity.MEDIUM,
            evidence="",
            message="test"
        )
        assert not v3.is_blocking()
    
    def test_to_dict(self):
        """测试to_dict方法"""
        v = ConstraintViolation(
            type="forbidden_element",
            element="修炼",
            severity=ViolationSeverity.CRITICAL,
            evidence="...陈阳开始修炼...",
            message="检测到禁止元素: 修炼",
            location={"chapter": 5}
        )
        
        data = v.to_dict()
        assert data["type"] == "forbidden_element"
        assert data["element"] == "修炼"
        assert data["severity"] == "critical"
        assert data["location"]["chapter"] == 5
```

---

## 🎯 模块3: ProgressionModel（进阶模型）

### 3.1 文件结构

**文件**: `runtime/genre/progression.py`

### 3.2 完整实现

```python
# ============================================================
# 文件: AI-Novel-Runtime/runtime/genre/progression.py
# 目的: 题材进阶模型系统
# 相关决策: Decision 1.1（Genre-First架构）
# ============================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum


# ============================================================
# ProgressionTier
# ============================================================

@dataclass
class ProgressionTier:
    """进阶等级
    
    表示进阶体系中的一个等级。
    
    Attributes:
        tier_id: 等级ID（唯一标识）
        tier_name: 等级名称（如"筑基期"、"中产阶级"）
        tier_order: 等级顺序（数字，越大越高）
        description: 等级描述
        typical_capabilities: 典型能力/特征列表
        entry_requirements: 进入要求
        
    Example:
        >>> tier = ProgressionTier(
        ...     tier_id="middle_class",
        ...     tier_name="中产阶级",
        ...     tier_order=4,
        ...     description="年收入30-100万",
        ...     typical_capabilities=["购房", "子女教育", "出国旅游"],
        ...     entry_requirements="稳定收入+资产积累"
        ... )
    """
    tier_id: str
    tier_name: str
    tier_order: int
    description: str
    typical_capabilities: List[str]
    entry_requirements: str


# ============================================================
# ProgressionValidationResult
# ============================================================

@dataclass
class ProgressionValidationResult:
    """进阶验证结果
    
    验证角色的进阶是否合理。
    
    Attributes:
        is_valid: 是否有效
        from_tier: 起始等级
        to_tier: 目标等级
        issues: 问题列表（如果无效）
        suggestions: 建议列表
        
    Example:
        >>> result = ProgressionValidationResult(
        ...     is_valid=False,
        ...     from_tier="贫困线",
        ...     to_tier="富豪",
        ...     issues=["跨越等级过多", "缺少中间过渡"],
        ...     suggestions=["建议先到达小康再到中产"]
        ... )
    """
    is_valid: bool
    from_tier: str
    to_tier: str
    issues: List[str]
    suggestions: List[str]


# ============================================================
# ProgressionModel（抽象基类）
# ============================================================

class ProgressionModel(ABC):
    """进阶模型抽象基类
    
    定义题材特定的进阶体系（如修炼境界、财富等级等）。
    每个题材应该实现自己的ProgressionModel子类。
    
    核心功能：
    1. 定义进阶等级体系
    2. 验证角色进阶是否合理
    3. 提供进阶建议
    
    Example:
        子类实现示例：
        >>> class WealthProgressionModel(ProgressionModel):
        ...     def get_tiers(self):
        ...         return ["贫困线", "温饱", "小康", "中产", "富裕", "富豪"]
        ...     
        ...     def validate_progression(self, from_tier, to_tier, context):
        ...         # 实现验证逻辑
        ...         pass
    """
    
    @abstractmethod
    def get_tiers(self) -> List[str]:
        """获取所有等级名称列表
        
        返回从低到高排序的等级名称。
        
        Returns:
            等级名称列表
            
        Example:
            >>> model = WealthProgressionModel()
            >>> tiers = model.get_tiers()
            >>> print(tiers)
            ['贫困线', '温饱', '小康', '中产', '富裕', '富豪']
        """
        pass
    
    @abstractmethod
    def get_tier_details(self, tier_name: str) -> ProgressionTier:
        """获取等级详细信息
        
        Args:
            tier_name: 等级名称
            
        Returns:
            等级详情对象
            
        Raises:
            ValueError: 如果等级不存在
        """
        pass
    
    @abstractmethod
    def validate_progression(
        self,
        from_tier: str,
        to_tier: str,
        context: Optional[Dict] = None
    ) -> ProgressionValidationResult:
        """验证进阶是否合理
        
        检查从from_tier到to_tier的进阶是否合理。
        
        Args:
            from_tier: 起始等级
            to_tier: 目标等级
            context: 上下文信息（如章节数、时间跨度）
            
        Returns:
            验证结果
            
        Example:
            >>> result = model.validate_progression("贫困线", "富豪")
            >>> if not result.is_valid:
            ...     print(result.issues)
            ['跨越等级过多', '缺少中间过渡']
        """
        pass
    
    def get_tier_order(self, tier_name: str) -> int:
        """获取等级顺序
        
        Args:
            tier_name: 等级名称
            
        Returns:
            等级顺序（数字）
            
        Raises:
            ValueError: 如果等级不存在
        """
        tiers = self.get_tiers()
        if tier_name not in tiers:
            raise ValueError(f"Unknown tier: {tier_name}")
        
        return tiers.index(tier_name)
    
    def get_next_tier(self, current_tier: str) -> Optional[str]:
        """获取下一个等级
        
        Args:
            current_tier: 当前等级
            
        Returns:
            下一个等级名称，如果已是最高等级则返回None
        """
        tiers = self.get_tiers()
        try:
            current_order = self.get_tier_order(current_tier)
            if current_order < len(tiers) - 1:
                return tiers[current_order + 1]
            return None
        except ValueError:
            return None
    
    def calculate_tier_gap(self, from_tier: str, to_tier: str) -> int:
        """计算等级差距
        
        Args:
            from_tier: 起始等级
            to_tier: 目标等级
            
        Returns:
            等级差（正数表示上升，负数表示下降）
        """
        from_order = self.get_tier_order(from_tier)
        to_order = self.get_tier_order(to_tier)
        return to_order - from_order


# ============================================================
# WealthProgressionModel（都市财富进阶）
# ============================================================

class WealthProgressionModel(ProgressionModel):
    """财富进阶模型（都市题材）
    
    定义都市题材的财富等级体系。
    
    等级体系：
    1. 贫困线（年收入<3万）
    2. 温饱（年收入3-10万）
    3. 小康（年收入10-30万）
    4. 中产（年收入30-100万）
    5. 富裕（年收入100-500万）
    6. 富豪（年收入>500万）
    
    Example:
        >>> model = WealthProgressionModel()
        >>> tiers = model.get_tiers()
        >>> print(tiers)
        ['贫困线', '温饱', '小康', '中产', '富裕', '富豪']
        
        >>> result = model.validate_progression("贫困线", "富豪")
        >>> print(result.is_valid)
        False
        >>> print(result.issues)
        ['跨越等级过多（5级）', '缺少中间过渡']
    """
    
    # 等级定义
    TIERS = [
        ProgressionTier(
            tier_id="poverty_line",
            tier_name="贫困线",
            tier_order=0,
            description="年收入低于3万，基本生存困难",
            typical_capabilities=["基本生活", "租房", "公共交通"],
            entry_requirements="无"
        ),
        ProgressionTier(
            tier_id="subsistence",
            tier_name="温饱",
            tier_order=1,
            description="年收入3-10万，基本生活无忧",
            typical_capabilities=["稳定租房", "日常消费", "小额储蓄"],
            entry_requirements="稳定工作"
        ),
        ProgressionTier(
            tier_id="well_off",
            tier_name="小康",
            tier_order=2,
            description="年收入10-30万，生活较为舒适",
            typical_capabilities=["购买小型汽车", "国内旅游", "子女教育"],
            entry_requirements="技能提升或小型创业"
        ),
        ProgressionTier(
            tier_id="middle_class",
            tier_name="中产",
            tier_order=3,
            description="年收入30-100万，有一定资产积累",
            typical_capabilities=["购房", "高端消费", "出国旅游", "投资理财"],
            entry_requirements="管理岗位或成功创业"
        ),
        ProgressionTier(
            tier_id="affluent",
            tier_name="富裕",
            tier_order=4,
            description="年收入100-500万，财务相对自由",
            typical_capabilities=["多套房产", "豪车", "高端教育", "天使投资"],
            entry_requirements="企业高管或企业主"
        ),
        ProgressionTier(
            tier_id="wealthy",
            tier_name="富豪",
            tier_order=5,
            description="年收入超过500万，财务完全自由",
            typical_capabilities=["奢侈品", "私人飞机", "多元投资", "慈善"],
            entry_requirements="成功企业家或投资家"
        )
    ]
    
    def get_tiers(self) -> List[str]:
        """获取所有等级名称"""
        return [tier.tier_name for tier in self.TIERS]
    
    def get_tier_details(self, tier_name: str) -> ProgressionTier:
        """获取等级详细信息"""
        for tier in self.TIERS:
            if tier.tier_name == tier_name:
                return tier
        
        raise ValueError(f"Unknown tier: {tier_name}")
    
    def validate_progression(
        self,
        from_tier: str,
        to_tier: str,
        context: Optional[Dict] = None
    ) -> ProgressionValidationResult:
        """验证进阶是否合理"""
        issues = []
        suggestions = []
        
        # 计算等级差
        gap = self.calculate_tier_gap(from_tier, to_tier)
        
        # 获取上下文
        chapter_count = context.get("chapter_count", 1) if context else 1
        time_span_months = context.get("time_span_months", 1) if context else 1
        
        # 规则1：不能跨越太多等级（相对于章节数）
        max_allowed_gap = max(1, chapter_count // 10)  # 每10章允许跨1级
        if gap > max_allowed_gap:
            issues.append(f"跨越等级过多（{gap}级），建议不超过{max_allowed_gap}级")
            
            # 提供建议路径
            current_order = self.get_tier_order(from_tier)
            target_order = current_order + max_allowed_gap
            if target_order < len(self.TIERS):
                suggested_tier = self.TIERS[target_order].tier_name
                suggestions.append(f"建议先进阶到 {suggested_tier}")
        
        # 规则2：时间跨度合理性
        min_months_per_tier = 3  # 每级至少3个月
        required_months = gap * min_months_per_tier
        if time_span_months < required_months:
            issues.append(
                f"时间跨度过短（{time_span_months}个月），"
                f"进阶{gap}级至少需要{required_months}个月"
            )
            suggestions.append(f"建议增加时间跨度到至少{required_months}个月")
        
        # 规则3：不能降级
        if gap < 0:
            issues.append("不支持降级")
        
        # 规则4：已达最高等级
        if gap == 0:
            if to_tier == self.TIERS[-1].tier_name:
                suggestions.append("已达最高等级，可以深化财富运用和影响力")
            else:
                suggestions.append(f"可以考虑进阶到下一级: {self.get_next_tier(from_tier)}")
        
        is_valid = len(issues) == 0
        
        return ProgressionValidationResult(
            is_valid=is_valid,
            from_tier=from_tier,
            to_tier=to_tier,
            issues=issues,
            suggestions=suggestions
        )


# ============================================================
# CultivationProgressionModel（玄幻修炼进阶）
# ============================================================

class CultivationProgressionModel(ProgressionModel):
    """修炼进阶模型（玄幻题材）
    
    定义玄幻题材的修炼境界体系。
    
    等级体系：
    1. 炼气期
    2. 筑基期
    3. 金丹期
    4. 元婴期
    5. 化神期
    6. 渡劫期
    
    Example:
        >>> model = CultivationProgressionModel()
        >>> result = model.validate_progression("炼气期", "元婴期")
        >>> print(result.is_valid)
        False
    """
    
    TIERS = [
        ProgressionTier(
            tier_id="qi_refining",
            tier_name="炼气期",
            tier_order=0,
            description="修炼入门，炼化灵气淬炼身体",
            typical_capabilities=["感知灵气", "简单法术", "延长寿命10年"],
            entry_requirements="灵根资质"
        ),
        ProgressionTier(
            tier_id="foundation",
            tier_name="筑基期",
            tier_order=1,
            description="筑基固本，建立修炼根基",
            typical_capabilities=["御器飞行", "中级法术", "延长寿命50年"],
            entry_requirements="炼气大圆满+筑基丹"
        ),
        ProgressionTier(
            tier_id="golden_core",
            tier_name="金丹期",
            tier_order=2,
            description="凝结金丹，脱胎换骨",
            typical_capabilities=["御剑飞行", "高级法术", "延长寿命200年"],
            entry_requirements="筑基大圆满+结丹"
        ),
        ProgressionTier(
            tier_id="nascent_soul",
            tier_name="元婴期",
            tier_order=3,
            description="元婴出窍，神魂不灭",
            typical_capabilities=["元婴出窍", "神通术法", "延长寿命500年"],
            entry_requirements="金丹大圆满+渡元婴劫"
        ),
        ProgressionTier(
            tier_id="spirit_transformation",
            tier_name="化神期",
            tier_order=4,
            description="化神为一，天人合一",
            typical_capabilities=["空间神通", "领域", "延长寿命1000年"],
            entry_requirements="元婴大圆满+化神"
        ),
        ProgressionTier(
            tier_id="tribulation",
            tier_name="渡劫期",
            tier_order=5,
            description="渡天劫，准备飞升",
            typical_capabilities=["撕裂空间", "毁天灭地", "半仙之体"],
            entry_requirements="化神大圆满+渡天劫"
        )
    ]
    
    def get_tiers(self) -> List[str]:
        """获取所有等级名称"""
        return [tier.tier_name for tier in self.TIERS]
    
    def get_tier_details(self, tier_name: str) -> ProgressionTier:
        """获取等级详细信息"""
        for tier in self.TIERS:
            if tier.tier_name == tier_name:
                return tier
        
        raise ValueError(f"Unknown tier: {tier_name}")
    
    def validate_progression(
        self,
        from_tier: str,
        to_tier: str,
        context: Optional[Dict] = None
    ) -> ProgressionValidationResult:
        """验证进阶是否合理"""
        issues = []
        suggestions = []
        
        # 计算等级差
        gap = self.calculate_tier_gap(from_tier, to_tier)
        
        # 获取上下文
        chapter_count = context.get("chapter_count", 1) if context else 1
        has_special_opportunity = context.get("has_special_opportunity", False) if context else False
        
        # 规则1：修炼境界提升严格，通常一次只能提升1级
        max_gap = 2 if has_special_opportunity else 1
        if gap > max_gap:
            issues.append(f"境界提升过快（{gap}级），修炼需要循序渐进")
            next_tier = self.get_next_tier(from_tier)
            if next_tier:
                suggestions.append(f"建议先突破到 {next_tier}")
        
        # 规则2：章节数要求（每个大境界至少需要20章）
        min_chapters = gap * 20
        if chapter_count < min_chapters:
            issues.append(
                f"章节数不足（{chapter_count}章），"
                f"突破{gap}级至少需要{min_chapters}章积累"
            )
        
        # 规则3：不能降级
        if gap < 0:
            issues.append("修炼境界不能倒退（除非特殊设定如走火入魔）")
        
        is_valid = len(issues) == 0
        
        return ProgressionValidationResult(
            is_valid=is_valid,
            from_tier=from_tier,
            to_tier=to_tier,
            issues=issues,
            suggestions=suggestions
        )


# ============================================================
# 使用示例
# ============================================================

# if __name__ == "__main__":
#     # 示例1：财富进阶模型
#     wealth_model = WealthProgressionModel()
#     
#     # 获取所有等级
#     tiers = wealth_model.get_tiers()
#     print(f"财富等级: {tiers}")
#     
#     # 获取等级详情
#     middle_class = wealth_model.get_tier_details("中产")
#     print(f"中产阶级: {middle_class.description}")
#     print(f"典型能力: {middle_class.typical_capabilities}")
#     
#     # 验证合理进阶
#     result1 = wealth_model.validate_progression(
#         "温饱", "小康",
#         context={"chapter_count": 10, "time_span_months": 6}
#     )
#     print(f"温饱->小康: {result1.is_valid}")
#     
#     # 验证不合理进阶
#     result2 = wealth_model.validate_progression(
#         "贫困线", "富豪",
#         context={"chapter_count": 5, "time_span_months": 2}
#     )
#     print(f"贫困线->富豪: {result2.is_valid}")
#     print(f"问题: {result2.issues}")
#     print(f"建议: {result2.suggestions}")
#     
#     # 示例2：修炼进阶模型
#     cultivation_model = CultivationProgressionModel()
#     
#     result3 = cultivation_model.validate_progression(
#         "炼气期", "筑基期",
#         context={"chapter_count": 25, "has_special_opportunity": False}
#     )
#     print(f"炼气期->筑基期: {result3.is_valid}")
```

### 3.3 测试代码

**文件**: `tests/runtime/genre/test_progression.py`

```python
# ============================================================
# 文件: tests/runtime/genre/test_progression.py
# 目的: 测试ProgressionModel
# ============================================================

import pytest
from runtime.genre.progression import (
    ProgressionModel,
    WealthProgressionModel,
    CultivationProgressionModel,
    ProgressionTier,
    ProgressionValidationResult
)


# ============================================================
# 财富进阶模型测试
# ============================================================

class TestWealthProgressionModel:
    """测试财富进阶模型"""
    
    def test_get_tiers(self):
        """测试获取等级列表"""
        model = WealthProgressionModel()
        tiers = model.get_tiers()
        
        assert len(tiers) == 6
        assert tiers[0] == "贫困线"
        assert tiers[-1] == "富豪"
    
    def test_get_tier_details(self):
        """测试获取等级详情"""
        model = WealthProgressionModel()
        tier = model.get_tier_details("中产")
        
        assert tier.tier_name == "中产"
        assert tier.tier_order == 3
        assert "购房" in tier.typical_capabilities
    
    def test_get_tier_details_invalid(self):
        """测试获取不存在的等级"""
        model = WealthProgressionModel()
        
        with pytest.raises(ValueError, match="Unknown tier"):
            model.get_tier_details("不存在的等级")
    
    def test_get_tier_order(self):
        """测试获取等级顺序"""
        model = WealthProgressionModel()
        
        assert model.get_tier_order("贫困线") == 0
        assert model.get_tier_order("富豪") == 5
    
    def test_get_next_tier(self):
        """测试获取下一个等级"""
        model = WealthProgressionModel()
        
        assert model.get_next_tier("贫困线") == "温饱"
        assert model.get_next_tier("温饱") == "小康"
        assert model.get_next_tier("富豪") is None  # 已达最高
    
    def test_calculate_tier_gap(self):
        """测试计算等级差距"""
        model = WealthProgressionModel()
        
        assert model.calculate_tier_gap("贫困线", "温饱") == 1
        assert model.calculate_tier_gap("贫困线", "富豪") == 5
        assert model.calculate_tier_gap("富豪", "贫困线") == -5
    
    def test_validate_progression_reasonable(self):
        """测试验证合理进阶"""
        model = WealthProgressionModel()
        
        result = model.validate_progression(
            "温饱", "小康",
            context={"chapter_count": 15, "time_span_months": 6}
        )
        
        assert result.is_valid
        assert result.from_tier == "温饱"
        assert result.to_tier == "小康"
        assert len(result.issues) == 0
    
    def test_validate_progression_too_fast(self):
        """测试验证进阶过快"""
        model = WealthProgressionModel()
        
        result = model.validate_progression(
            "贫困线", "富豪",
            context={"chapter_count": 5, "time_span_months": 2}
        )
        
        assert not result.is_valid
        assert len(result.issues) > 0
        assert any("跨越等级过多" in issue for issue in result.issues)
    
    def test_validate_progression_insufficient_time(self):
        """测试验证时间不足"""
        model = WealthProgressionModel()
        
        result = model.validate_progression(
            "贫困线", "小康",
            context={"chapter_count": 30, "time_span_months": 1}
        )
        
        assert not result.is_valid
        assert any("时间跨度过短" in issue for issue in result.issues)
    
    def test_validate_progression_downgrade(self):
        """测试验证降级"""
        model = WealthProgressionModel()
        
        result = model.validate_progression(
            "富豪", "贫困线",
            context={"chapter_count": 10, "time_span_months": 12}
        )
        
        assert not result.is_valid
        assert any("不支持降级" in issue for issue in result.issues)


# ============================================================
# 修炼进阶模型测试
# ============================================================

class TestCultivationProgressionModel:
    """测试修炼进阶模型"""
    
    def test_get_tiers(self):
        """测试获取等级列表"""
        model = CultivationProgressionModel()
        tiers = model.get_tiers()
        
        assert len(tiers) == 6
        assert tiers[0] == "炼气期"
        assert tiers[-1] == "渡劫期"
    
    def test_get_tier_details(self):
        """测试获取等级详情"""
        model = CultivationProgressionModel()
        tier = model.get_tier_details("金丹期")
        
        assert tier.tier_name == "金丹期"
        assert tier.tier_order == 2
        assert "御剑飞行" in tier.typical_capabilities
    
    def test_validate_progression_normal(self):
        """测试验证正常突破"""
        model = CultivationProgressionModel()
        
        result = model.validate_progression(
            "炼气期", "筑基期",
            context={"chapter_count": 25, "has_special_opportunity": False}
        )
        
        assert result.is_valid
    
    def test_validate_progression_too_fast(self):
        """测试验证突破过快"""
        model = CultivationProgressionModel()
        
        result = model.validate_progression(
            "炼气期", "金丹期",
            context={"chapter_count": 10, "has_special_opportunity": False}
        )
        
        assert not result.is_valid
        assert any("境界提升过快" in issue for issue in result.issues)
    
    def test_validate_progression_special_opportunity(self):
        """测试验证特殊机缘突破"""
        model = CultivationProgressionModel()
        
        result = model.validate_progression(
            "炼气期", "金丹期",
            context={"chapter_count": 50, "has_special_opportunity": True}
        )
        
        # 有特殊机缘，可以跨2级
        assert result.is_valid
    
    def test_validate_progression_insufficient_chapters(self):
        """测试验证章节不足"""
        model = CultivationProgressionModel()
        
        result = model.validate_progression(
            "炼气期", "筑基期",
            context={"chapter_count": 5, "has_special_opportunity": False}
        )
        
        assert not result.is_valid
        assert any("章节数不足" in issue for issue in result.issues)
```

---

## 🗂️ 模块4: GenreRegistry（题材注册表）

### 4.1 文件结构

**文件**: `runtime/genre/registry.py`

### 4.2 完整实现

```python
# ============================================================
# 文件: AI-Novel-Runtime/runtime/genre/registry.py
# 目的: 题材注册表（单例）
# 相关决策: Decision 1.1（Genre-First架构）
# ============================================================

from typing import Dict, List, Optional
from runtime.genre.config import GenreID, GenreConfig


# ============================================================
# GenreRegistry（单例）
# ============================================================

class GenreRegistry:
    """题材注册表（单例）
    
    管理所有已注册的题材配置。
    系统启动时注册所有题材，运行时查询使用。
    
    单例模式：全局只有一个实例。
    
    核心功能：
    1. 注册题材配置
    2. 查询题材配置
    3. 列出所有题材
    
    Example:
        基本用法：
        >>> registry = GenreRegistry.get_instance()
        >>> registry.register(urban_config)
        >>> config = registry.get("urban")
        >>> print(config.genre_name)
        都市
        
        单例验证：
        >>> registry1 = GenreRegistry.get_instance()
        >>> registry2 = GenreRegistry.get_instance()
        >>> assert registry1 is registry2
        True
    """
    
    _instance: Optional['GenreRegistry'] = None
    _initialized: bool = False
    
    def __init__(self):
        """私有构造函数
        
        不应该直接调用，使用get_instance()获取单例。
        """
        if GenreRegistry._initialized:
            raise RuntimeError(
                "GenreRegistry is a singleton. Use get_instance() instead."
            )
        
        self._configs: Dict[str, GenreConfig] = {}
        GenreRegistry._initialized = True
    
    @classmethod
    def get_instance(cls) -> 'GenreRegistry':
        """获取单例实例
        
        Returns:
            GenreRegistry单例
            
        Example:
            >>> registry = GenreRegistry.get_instance()
            >>> print(type(registry))
            <class 'GenreRegistry'>
        """
        if cls._instance is None:
            cls._instance = cls()
        
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例（仅用于测试）
        
        Warning:
            此方法仅用于测试，生产环境不应调用。
        """
        cls._instance = None
        cls._initialized = False
    
    def register(self, config: GenreConfig):
        """注册题材配置
        
        Args:
            config: 题材配置对象
            
        Raises:
            ValueError: 如果题材已注册
            
        Example:
            >>> registry = GenreRegistry.get_instance()
            >>> registry.register(urban_config)
        """
        genre_id = config.genre_id.value
        
        if genre_id in self._configs:
            raise ValueError(
                f"Genre '{genre_id}' is already registered. "
                f"Use update() to modify existing configuration."
            )
        
        self._configs[genre_id] = config
    
    def get(self, genre_id: str) -> GenreConfig:
        """获取题材配置
        
        Args:
            genre_id: 题材ID（如"urban"）
            
        Returns:
            题材配置对象
            
        Raises:
            KeyError: 如果题材未注册
            
        Example:
            >>> config = registry.get("urban")
            >>> print(config.genre_name)
            都市
        """
        if genre_id not in self._configs:
            available = list(self._configs.keys())
            raise KeyError(
                f"Genre '{genre_id}' not registered. "
                f"Available genres: {available}"
            )
        
        return self._configs[genre_id]
    
    def has(self, genre_id: str) -> bool:
        """检查题材是否已注册"""
        return genre_id in self._configs
    
    def list_all(self) -> List[str]:
        """列出所有已注册的题材ID"""
        return list(self._configs.keys())
    
    def count(self) -> int:
        """获取已注册题材数量"""
        return len(self._configs)


# ============================================================
# 便捷函数
# ============================================================

def get_genre_config(genre_id: str) -> GenreConfig:
    """便捷函数：获取题材配置"""
    registry = GenreRegistry.get_instance()
    return registry.get(genre_id)
```

---

## 🔍 模块5: GenreDetector（题材检测器）

### 5.1 文件结构

**文件**: `runtime/genre/detector.py`

### 5.2 完整实现

```python
# ============================================================
# 文件: AI-Novel-Runtime/runtime/genre/detector.py
# 目的: 题材检测器
# 相关决策: Decision 1.1（Genre-First架构）
# ============================================================

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from runtime.genre.config import GenreID
from runtime.genre.registry import GenreRegistry


# ============================================================
# DetectionResult
# ============================================================

@dataclass
class DetectionResult:
    """检测结果
    
    记录题材检测的结果和置信度。
    
    Attributes:
        genre_id: 检测到的题材ID
        confidence: 置信度（0.0-1.0）
        evidence: 支持证据（关键词、特征等）
        alternative_genres: 备选题材列表（按置信度降序）
        
    Example:
        >>> result = DetectionResult(
        ...     genre_id=GenreID.URBAN,
        ...     confidence=0.95,
        ...     evidence=["商战", "职场", "现代都市"],
        ...     alternative_genres=[("xuanhuan", 0.05)]
        ... )
    """
    genre_id: GenreID
    confidence: float
    evidence: List[str]
    alternative_genres: List[Tuple[str, float]]
    
    def is_confident(self, threshold: float = 0.8) -> bool:
        """是否达到置信阈值"""
        return self.confidence >= threshold


# ============================================================
# GenreDetector
# ============================================================

class GenreDetector:
    """题材检测器
    
    基于内容自动识别题材类型。
    
    检测方法：
    1. 关键词匹配
    2. 场景识别
    3. 元素统计
    
    Example:
        >>> detector = GenreDetector()
        >>> result = detector.detect("陈阳开始创业，成立科技公司...")
        >>> print(result.genre_id.value)
        urban
        >>> print(result.confidence)
        0.92
    """
    
    # 题材关键词映射
    GENRE_KEYWORDS = {
        "urban": {
            "high": ["商战", "职场", "创业", "投资", "科技公司", "CEO", "融资"],
            "medium": ["都市", "城市", "现代", "白领", "公司", "项目"],
            "low": ["办公室", "会议", "商务", "客户"]
        },
        "xuanhuan": {
            "high": ["修炼", "灵气", "法宝", "宗门", "神通", "境界", "突破"],
            "medium": ["弟子", "长老", "师尊", "丹药", "功法"],
            "low": ["洞府", "秘境", "妖兽"]
        }
    }
    
    # 权重配置
    WEIGHTS = {
        "high": 3.0,
        "medium": 1.5,
        "low": 0.5
    }
    
    def __init__(self, registry: Optional[GenreRegistry] = None):
        """初始化检测器
        
        Args:
            registry: 题材注册表（可选，默认使用单例）
        """
        self.registry = registry or GenreRegistry.get_instance()
    
    def detect(self, content: str, context: Optional[Dict] = None) -> DetectionResult:
        """检测题材
        
        Args:
            content: 要检测的内容（章节文本）
            context: 上下文信息（可选）
            
        Returns:
            检测结果
            
        Example:
            >>> detector = GenreDetector()
            >>> result = detector.detect("陈阳在公司开会，讨论新项目...")
            >>> print(result.genre_id.value)
            urban
        """
        # 计算每个题材的分数
        scores = self._calculate_scores(content)
        
        # 找到最高分
        if not scores:
            # 默认返回urban
            return DetectionResult(
                genre_id=GenreID.URBAN,
                confidence=0.0,
                evidence=[],
                alternative_genres=[]
            )
        
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_genre, top_score = sorted_scores[0]
        
        # 归一化置信度
        total_score = sum(scores.values())
        confidence = top_score / total_score if total_score > 0 else 0.0
        
        # 备选题材
        alternatives = [
            (genre, score / total_score if total_score > 0 else 0.0)
            for genre, score in sorted_scores[1:3]
        ]
        
        # 提取证据
        evidence = self._extract_evidence(content, top_genre)
        
        return DetectionResult(
            genre_id=GenreID.from_string(top_genre),
            confidence=confidence,
            evidence=evidence,
            alternative_genres=alternatives
        )
    
    def _calculate_scores(self, content: str) -> Dict[str, float]:
        """计算每个题材的分数"""
        scores = {}
        
        for genre_id, keywords in self.GENRE_KEYWORDS.items():
            score = 0.0
            
            for level, words in keywords.items():
                weight = self.WEIGHTS[level]
                for word in words:
                    if word in content:
                        score += weight
            
            if score > 0:
                scores[genre_id] = score
        
        return scores
    
    def _extract_evidence(self, content: str, genre_id: str) -> List[str]:
        """提取支持证据"""
        evidence = []
        
        if genre_id not in self.GENRE_KEYWORDS:
            return evidence
        
        keywords = self.GENRE_KEYWORDS[genre_id]
        for level, words in keywords.items():
            for word in words:
                if word in content:
                    evidence.append(word)
        
        return evidence[:10]  # 最多返回10个证据
```

---

## ✅ 模块6: GenreValidator（题材验证器）

### 6.1 文件结构

**文件**: `runtime/genre/validator.py`

### 6.2 完整实现

```python
# ============================================================
# 文件: AI-Novel-Runtime/runtime/genre/validator.py
# 目的: 题材验证器
# 相关决策: Decision 1.1（Genre-First架构）
# ============================================================

from typing import List, Dict, Optional
from dataclasses import dataclass
from runtime.genre.config import GenreConfig
from runtime.genre.constraints import ConstraintViolation
from runtime.genre.registry import get_genre_config


# ============================================================
# ValidationResult
# ============================================================

@dataclass
class ValidationResult:
    """验证结果
    
    记录内容验证的完整结果。
    
    Attributes:
        is_valid: 是否通过验证
        genre_id: 题材ID
        violations: 违规列表
        has_blocking_violations: 是否有阻断性违规
        
    Example:
        >>> result = ValidationResult(
        ...     is_valid=False,
        ...     genre_id="urban",
        ...     violations=[violation1, violation2],
        ...     has_blocking_violations=True
        ... )
    """
    is_valid: bool
    genre_id: str
    violations: List[ConstraintViolation]
    has_blocking_violations: bool
    
    def get_blocking_violations(self) -> List[ConstraintViolation]:
        """获取所有阻断性违规"""
        return [v for v in self.violations if v.is_blocking()]
    
    def get_critical_violations(self) -> List[ConstraintViolation]:
        """获取所有严重违规"""
        return [v for v in self.violations if v.is_critical()]


# ============================================================
# GenreValidator
# ============================================================

class GenreValidator:
    """题材验证器
    
    验证内容是否符合题材约束。
    
    Example:
        >>> validator = GenreValidator()
        >>> result = validator.validate("urban", chapter_text)
        >>> if not result.is_valid:
        ...     print("验证失败")
        ...     for v in result.violations:
        ...         print(f"- {v.message}")
    """
    
    def validate(
        self,
        genre_id: str,
        content: str,
        context: Optional[Dict] = None
    ) -> ValidationResult:
        """验证内容是否符合题材约束
        
        Args:
            genre_id: 题材ID
            content: 要验证的内容
            context: 上下文信息（可选）
            
        Returns:
            验证结果
            
        Example:
            >>> validator = GenreValidator()
            >>> result = validator.validate("urban", "陈阳开始修炼...")
            >>> print(result.is_valid)
            False
            >>> print(result.has_blocking_violations)
            True
        """
        # 获取题材配置
        config = get_genre_config(genre_id)
        
        # 执行约束验证
        violations = config.validate_content(content, context)
        
        # 检查是否有阻断性违规
        has_blocking = any(v.is_blocking() for v in violations)
        
        # 判断是否通过验证
        is_valid = len(violations) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            genre_id=genre_id,
            violations=violations,
            has_blocking_violations=has_blocking
        )
    
    def should_block_generation(self, result: ValidationResult) -> bool:
        """判断是否应该阻断生成
        
        Args:
            result: 验证结果
            
        Returns:
            是否应该阻断
            
        Example:
            >>> if validator.should_block_generation(result):
            ...     print("生成被阻断")
        """
        return result.has_blocking_violations
```

---

## 🔧 模块7: 集成指南

### 7.1 系统初始化

**位置**: `runtime/__init__.py` 或 `runtime/genre/__init__.py`

```python
# ============================================================
# 文件: AI-Novel-Runtime/runtime/genre/__init__.py
# 目的: Genre系统初始化
# ============================================================

from runtime.genre.config import GenreID, GenreConfig
from runtime.genre.constraints import GenreConstraints
from runtime.genre.progression import ProgressionModel
from runtime.genre.registry import GenreRegistry, get_genre_config, list_available_genres
from runtime.genre.detector import GenreDetector
from runtime.genre.validator import GenreValidator

# 导入具体配置
from runtime.genre.configs.urban import URBAN_CONFIG
from runtime.genre.configs.xuanhuan import XUANHUAN_CONFIG


def initialize_genre_system():
    """初始化Genre系统
    
    在系统启动时调用，注册所有题材配置。
    
    Example:
        >>> from runtime.genre import initialize_genre_system
        >>> initialize_genre_system()
    """
    registry = GenreRegistry.get_instance()
    
    # 注册都市
    registry.register_or_update(URBAN_CONFIG)
    
    # 注册玄幻
    registry.register_or_update(XUANHUAN_CONFIG)
    
    # 可以在这里注册更多题材...
    
    print(f"Genre系统初始化完成，已注册 {registry.count()} 个题材")


__all__ = [
    # 核心类
    'GenreID',
    'GenreConfig',
    'GenreConstraints',
    'ProgressionModel',
    'GenreRegistry',
    'GenreDetector',
    'GenreValidator',
    
    # 便捷函数
    'get_genre_config',
    'list_available_genres',
    'initialize_genre_system',
]
```

### 7.2 Genesis集成

**位置**: `runtime/genesis.py`

```python
# 在Genesis流程中集成Genre系统

from runtime.genre import get_genre_config, GenreDetector, GenreValidator

class Genesis:
    def __init__(self, genre_id: str):
        # 获取题材配置
        self.genre_config = get_genre_config(genre_id)
        self.validator = GenreValidator()
    
    def generate_outline(self, user_input: str) -> str:
        """生成大纲"""
        # 1. 获取题材专用Prompt模板
        prompt_template = self.genre_config.get_prompt_template("outline")
        
        # 2. 注入题材上下文
        genre_context = self.genre_config.to_prompt_context()
        
        # 3. 构建完整Prompt
        full_prompt = f"""{genre_context}

{prompt_template}

用户输入: {user_input}
"""
        
        # 4. 调用LLM生成
        outline = self.llm.generate(full_prompt)
        
        # 5. 验证大纲
        validation_result = self.validator.validate(
            self.genre_config.genre_id.value,
            outline
        )
        
        if not validation_result.is_valid:
            # 处理违规
            if validation_result.has_blocking_violations:
                # 阻断性违规，重新生成
                print("检测到违规，重新生成...")
                return self.generate_outline(user_input)
        
        return outline
```

### 7.3 Production集成

**位置**: `runtime/production.py`

```python
# 在Production流程中集成Genre系统

from runtime.genre import get_genre_config, GenreValidator

class Production:
    def __init__(self, genre_id: str):
        self.genre_config = get_genre_config(genre_id)
        self.validator = GenreValidator()
    
    def generate_chapter(self, outline: str, chapter_num: int) -> str:
        """生成章节"""
        # 1. 获取题材专用Prompt
        prompt_template = self.genre_config.get_prompt_template("chapter")
        genre_context = self.genre_config.to_prompt_context()
        
        # 2. 构建Prompt
        full_prompt = f"""{genre_context}

{prompt_template}

大纲: {outline}
章节号: {chapter_num}
"""
        
        # 3. 生成章节
        chapter = self.llm.generate(full_prompt)
        
        # 4. 验证章节
        validation_result = self.validator.validate(
            self.genre_config.genre_id.value,
            chapter,
            context={"chapter_num": chapter_num}
        )
        
        if validation_result.has_blocking_violations:
            # 阻断性违规，拒绝生成
            raise ValueError(f"章节违反题材约束: {validation_result.violations}")
        
        return chapter
```

---

## 📝 实施检查清单

### M1 Week 1-2 完成标准

- [ ] **模块1: GenreConfig**
  - [ ] config.py 实现完成
  - [ ] test_config.py 通过
  - [ ] GenreID枚举包含10个题材
  - [ ] WorldviewFoundation完整定义

- [ ] **模块2: GenreConstraints**
  - [ ] constraints.py 实现完成
  - [ ] test_constraints.py 通过
  - [ ] UrbanConstraints完整实现
  - [ ] XuanhuanConstraints完整实现

- [ ] **模块3: ProgressionModel**
  - [ ] progression.py 实现完成
  - [ ] test_progression.py 通过
  - [ ] WealthProgressionModel实现（6级）
  - [ ] CultivationProgressionModel实现（6级）

- [ ] **模块4: GenreRegistry**
  - [ ] registry.py 实现完成
  - [ ] test_registry.py 通过
  - [ ] 单例模式正确实现
  - [ ] 便捷函数可用

- [ ] **模块5: GenreDetector**
  - [ ] detector.py 实现完成
  - [ ] test_detector.py 通过
  - [ ] 关键词映射覆盖2个题材
  - [ ] 置信度计算准确

- [ ] **模块6: GenreValidator**
  - [ ] validator.py 实现完成
  - [ ] 集成GenreConfig和Constraints
  - [ ] 阻断机制工作正常

- [ ] **模块7: 题材配置**
  - [ ] configs/urban.py 完整实现
  - [ ] configs/xuanhuan.py 完整实现
  - [ ] Prompt模板完整（outline+chapter）

- [ ] **集成测试**
  - [ ] Genesis集成完成
  - [ ] Production集成完成
  - [ ] 端到端测试通过

---

## 🎯 下一步（M1 Week 3-4）

完成Genre系统后，继续：

1. **扩展题材配置**
   - 添加仙侠、武侠、科幻等题材
   - 完善Prompt模板库

2. **优化检测算法**
   - 集成LLM辅助检测
   - 提升置信度准确性

3. **数据模型实施**
   - Character模型
   - Worldview模型
   - Outline模型

---

**Genre系统实施手册完成！** ✅

总计：
- 6个核心模块
- 2,177行完整实现代码
- 完整测试覆盖
- 集成指南

