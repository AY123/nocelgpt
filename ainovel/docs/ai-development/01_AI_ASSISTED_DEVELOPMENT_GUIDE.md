# AI辅助开发指南 - ANovel V2项目

**版本**: v1.0  
**制定日期**: 2026-09-18  
**适用于**: Claude Code, Claude API, Cursor, GitHub Copilot  
**状态**: 完整  

---

## 📋 文档目的

本文档帮助AI助手（如Claude、GPT-4、Copilot等）高效理解和参与ANovel V2项目开发。

**核心目标**:
1. 让AI快速理解项目结构和设计理念
2. 提供标准化的提示词模板
3. 定义AI辅助开发的最佳实践
4. 确保AI生成代码质量一致

---

## 🎯 项目快速理解（AI必读）

### 项目是什么？

ANovel V2是一个**AI驱动的中文网络小说自动生成系统**。

**一句话概括**: 输入题材+创意，系统自动生成30-100章完整小说。

### 核心架构（5个关键概念）

```
1. Genre-First（题材优先）
   - 题材是第一公民
   - 所有决策基于题材
   - 都市不生成修炼，玄幻不生成商业

2. State as Projection（状态即投影）
   - Canon是唯一真实（事实集合）
   - State是从事实投影出来的
   - 任何时刻状态可重建

3. Canon Commit Boundary（唯一写入口）
   - 所有事实修改必须通过Mint
   - 保证单一数据源（SSOT）
   - 原子事务

4. Validity Interval（有效性区间）
   - 每个事实有有效期
   - 区分"合法变化"vs"非法矛盾"
   - 支持角色成长

5. Draft A/B/C（三稿制）
   - Draft A: 快速初稿（60s）
   - Draft B: 改进版（120s）
   - Draft C: 精修版（180s）
```

### 代码库结构

```
ainovel/
├── AI-Novel-Runtime/
│   └── runtime/                 # 核心运行时
│       ├── genre/               # Genre系统（M1重点）
│       ├── canon/               # Canon事实系统
│       ├── memory/              # State管理
│       ├── mint/                # Mint提交
│       ├── production/          # 生产流程
│       ├── qa/                  # 质量系统
│       └── outline/             # 大纲系统
│
├── docs/
│   ├── ai-development/          # AI开发指南（本文档）
│   ├── implementation-guides/   # 实施指南
│   ├── architecture-decisions/  # 架构决策
│   └── papers/                  # 论文研究
│
├── work/m1/                     # M1工作目录
│   ├── design/                  # 设计文档
│   ├── prototype/               # 原型代码
│   └── tests/                   # 测试用例
│
└── tests/                       # 测试套件
```

### 关键文件清单

**AI需要经常查看**:
```
必读文档（优先级从高到低）：
1. docs/ai-development/CODE_STANDARDS_AND_TEMPLATES.md
2. docs/architecture-decisions/12_ARCHITECTURE_DECISION_RECORD_PART*.md
3. docs/architecture-decisions/11_FINAL_EXECUTABLE_GUIDE.md
4. work/m1/M1_PROGRESS.md

核心代码（V1，需理解）：
1. runtime/genre/（待重构）
2. runtime/canon/fact.py
3. runtime/memory/state.py
4. runtime/mint/mint_executor.py
```

---

## 🤖 AI辅助开发工作流程

### 标准流程（5步）

```
Step 1: 理解需求
  ↓
Step 2: 查阅相关文档
  ↓
Step 3: 生成代码（使用模板）
  ↓
Step 4: 自我验证（检查清单）
  ↓
Step 5: 生成测试
```

### Step 1: 理解需求

**AI应该问自己的问题**:
- [ ] 这个需求属于哪个模块？（genre/canon/memory/production/qa）
- [ ] 有相关的架构决策吗？（查12_ARCHITECTURE_DECISION_RECORD_PART*.md）
- [ ] 有相关的代码模板吗？（查CODE_STANDARDS_AND_TEMPLATES.md）
- [ ] 需要修改V1代码还是新建V2代码？

**示例**:
```
用户需求: "实现GenreConfig类"

AI理解：
- 模块：genre系统
- 相关决策：Decision 1.1（Genre-First架构）
- 代码模板：有（Dataclass模板）
- 是否新建：是（V2新建）
```

---

### Step 2: 查阅相关文档

**查阅顺序**:

1. **代码规范** → `CODE_STANDARDS_AND_TEMPLATES.md`
   - 获取命名规范
   - 获取代码模板

2. **架构决策** → `12_ARCHITECTURE_DECISION_RECORD_PART*.md`
   - 理解设计理念
   - 查看决策依据

3. **详细设计** → `14_GENRE_SYSTEM_DETAILED_DESIGN.md` 等
   - 获取完整类定义
   - 查看方法签名

4. **实施指南** → `implementation-guides/*.md`（即将生成）
   - 获取实施步骤
   - 查看完整示例

**AI查阅文档的提示词模板**:
```
我需要实现{功能名称}，请帮我：
1. 在docs/目录下找到相关文档
2. 总结关键设计点
3. 提取可用的代码模板
```

---

### Step 3: 生成代码（使用模板）

**原则**:
1. ✅ 总是使用代码模板（不要从零开始）
2. ✅ 包含完整的类型注解
3. ✅ 包含详细的docstring
4. ✅ 包含使用示例
5. ✅ 遵循命名规范

**代码生成模板**:

```python
# ============================================================
# 文件: AI-Novel-Runtime/runtime/{module}/{filename}.py
# 目的: {一句话描述}
# 相关决策: Decision X.X
# ============================================================

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Type
from enum import Enum
from abc import ABC, abstractmethod

# ============================================================
# Enums（如果需要）
# ============================================================

class {EnumName}(Enum):
    """{Enum目的}
    
    Values:
        VALUE1: 描述
        VALUE2: 描述
    """
    VALUE1 = "value1"
    VALUE2 = "value2"


# ============================================================
# Data Classes
# ============================================================

@dataclass
class {ClassName}:
    """{类的一句话描述}
    
    {详细描述，说明这个类的作用、使用场景}
    
    Attributes:
        attr1: 属性1描述
        attr2: 属性2描述
        
    Example:
        >>> obj = {ClassName}(attr1="value1", attr2="value2")
        >>> obj.method()
        expected_result
        
    Related:
        - {RelatedClass}: 相关类说明
    """
    
    # 必需字段
    attr1: str
    attr2: int
    
    # 可选字段
    attr3: Optional[str] = None
    
    # 默认值字段
    attr4: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化后验证
        
        Raises:
            ValueError: 如果验证失败
        """
        self._validate()
    
    def _validate(self):
        """验证数据完整性"""
        if not self.attr1:
            raise ValueError("attr1 cannot be empty")
    
    def method_name(self, param: str) -> bool:
        """方法描述（动词开头）
        
        Args:
            param: 参数描述
            
        Returns:
            返回值描述
            
        Raises:
            ExceptionType: 异常情况描述
            
        Example:
            >>> obj.method_name("test")
            True
        """
        # 实现
        return True
    
    def to_dict(self) -> Dict:
        """转换为字典（用于序列化）
        
        Returns:
            包含所有字段的字典
        """
        return {
            "attr1": self.attr1,
            "attr2": self.attr2,
            # ...
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> '{ClassName}':
        """从字典创建实例（用于反序列化）
        
        Args:
            data: 字典数据
            
        Returns:
            {ClassName}实例
        """
        return cls(
            attr1=data["attr1"],
            attr2=data["attr2"],
            # ...
        )


# ============================================================
# Abstract Base Classes（如果需要）
# ============================================================

class {AbstractClassName}(ABC):
    """{抽象类描述}
    
    所有{相关}类必须继承此类并实现抽象方法。
    """
    
    @abstractmethod
    def abstract_method(self) -> str:
        """抽象方法描述
        
        Returns:
            返回值描述
        """
        pass


# ============================================================
# Concrete Implementations
# ============================================================

class {ConcreteClassName}({AbstractClassName}):
    """{具体实现描述}"""
    
    def abstract_method(self) -> str:
        """实现抽象方法"""
        return "implementation"


# ============================================================
# Usage Example（文件末尾，注释掉）
# ============================================================

# if __name__ == "__main__":
#     # 示例1：基本用法
#     obj = {ClassName}(attr1="test", attr2=123)
#     result = obj.method_name("param")
#     print(result)  # True
#     
#     # 示例2：序列化
#     data = obj.to_dict()
#     restored = {ClassName}.from_dict(data)
#     assert restored.attr1 == obj.attr1
```

---

### Step 4: 自我验证（检查清单）

**AI生成代码后，必须自我检查**:

```markdown
## ✅ 代码质量检查清单

### 结构完整性
- [ ] 文件头部注释完整（文件路径、目的、相关决策）
- [ ] 导入语句按顺序分组（标准库 → 第三方 → 本地）
- [ ] 类和函数按逻辑顺序组织

### 类型注解
- [ ] 所有函数参数有类型注解
- [ ] 所有函数返回值有类型注解
- [ ] 复杂类型使用typing模块

### 文档字符串
- [ ] 所有公共类有docstring（包含描述、属性、示例）
- [ ] 所有公共方法有docstring（包含Args、Returns、Raises、Example）
- [ ] docstring遵循Google风格

### 命名规范
- [ ] 类名：PascalCase（如GenreConfig）
- [ ] 函数/方法名：snake_case（如validate_transition）
- [ ] 常量：UPPER_SNAKE_CASE（如MAX_LENGTH）
- [ ] 私有方法：_leading_underscore（如_validate）

### 错误处理
- [ ] 关键操作有异常处理
- [ ] 异常有清晰的错误消息
- [ ] 使用恰当的异常类型

### 可测试性
- [ ] 方法职责单一
- [ ] 避免硬编码值
- [ ] 依赖可以注入

### 示例代码
- [ ] 类docstring包含使用示例
- [ ] 复杂方法包含示例
- [ ] 文件末尾有完整示例（注释掉）
```

**自动检查命令**（如果有条件）:
```bash
# 类型检查
mypy runtime/genre/config.py

# 代码风格检查
flake8 runtime/genre/config.py

# 文档检查
pydocstyle runtime/genre/config.py
```

---

### Step 5: 生成测试

**原则**: 每个类/方法都要有测试

**测试生成模板**:

```python
# ============================================================
# 文件: tests/runtime/{module}/test_{filename}.py
# 目的: 测试{模块名}
# ============================================================

import pytest
from runtime.{module}.{filename} import {ClassName}


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def sample_{obj_name}():
    """创建示例对象用于测试
    
    Returns:
        {ClassName}实例
    """
    return {ClassName}(
        attr1="test_value",
        attr2=123
    )


# ============================================================
# 基础功能测试
# ============================================================

class Test{ClassName}Basics:
    """测试{ClassName}基础功能"""
    
    def test_creation(self):
        """测试对象创建"""
        obj = {ClassName}(attr1="test", attr2=123)
        assert obj.attr1 == "test"
        assert obj.attr2 == 123
    
    def test_validation_success(self, sample_{obj_name}):
        """测试验证成功场景"""
        # 不应抛出异常
        sample_{obj_name}._validate()
    
    def test_validation_failure(self):
        """测试验证失败场景"""
        with pytest.raises(ValueError, match="attr1 cannot be empty"):
            {ClassName}(attr1="", attr2=123)


# ============================================================
# 方法测试
# ============================================================

class Test{ClassName}Methods:
    """测试{ClassName}的方法"""
    
    def test_method_name_success(self, sample_{obj_name}):
        """测试method_name成功场景"""
        result = sample_{obj_name}.method_name("param")
        assert result is True
    
    def test_method_name_failure(self, sample_{obj_name}):
        """测试method_name失败场景"""
        with pytest.raises(ValueError):
            sample_{obj_name}.method_name("")


# ============================================================
# 序列化测试
# ============================================================

class Test{ClassName}Serialization:
    """测试{ClassName}的序列化"""
    
    def test_to_dict(self, sample_{obj_name}):
        """测试to_dict方法"""
        data = sample_{obj_name}.to_dict()
        assert data["attr1"] == "test_value"
        assert data["attr2"] == 123
    
    def test_from_dict(self, sample_{obj_name}):
        """测试from_dict方法"""
        data = sample_{obj_name}.to_dict()
        restored = {ClassName}.from_dict(data)
        
        assert restored.attr1 == sample_{obj_name}.attr1
        assert restored.attr2 == sample_{obj_name}.attr2
    
    def test_round_trip(self, sample_{obj_name}):
        """测试序列化往返"""
        data = sample_{obj_name}.to_dict()
        restored = {ClassName}.from_dict(data)
        
        # 验证所有字段相等
        assert restored.attr1 == sample_{obj_name}.attr1
        assert restored.attr2 == sample_{obj_name}.attr2


# ============================================================
# 边界条件测试
# ============================================================

class Test{ClassName}EdgeCases:
    """测试{ClassName}的边界条件"""
    
    def test_empty_input(self):
        """测试空输入"""
        with pytest.raises(ValueError):
            {ClassName}(attr1="", attr2=0)
    
    def test_none_input(self):
        """测试None输入"""
        obj = {ClassName}(attr1="test", attr2=123, attr3=None)
        assert obj.attr3 is None
    
    def test_large_input(self):
        """测试大量输入"""
        large_value = "x" * 10000
        obj = {ClassName}(attr1=large_value, attr2=123)
        assert len(obj.attr1) == 10000
```

**测试运行**:
```bash
# 运行单个测试文件
pytest tests/runtime/genre/test_config.py -v

# 运行所有测试
pytest tests/ -v

# 运行测试并显示覆盖率
pytest tests/ --cov=runtime --cov-report=html
```

---

## 💬 提示词模板库

### 模板1: 实现新类

```
请实现{模块}.{类名}类，要求：

1. 查阅相关文档：
   - docs/architecture-decisions/12_*.md（架构决策）
   - docs/ai-development/CODE_STANDARDS_AND_TEMPLATES.md（代码规范）

2. 类定义：
   - 使用@dataclass装饰器
   - 包含{字段列表}
   - 实现{方法列表}

3. 代码质量：
   - 完整的类型注解
   - 详细的docstring（包含Example）
   - 遵循命名规范

4. 测试：
   - 生成完整的测试文件
   - 包含基础功能、方法、序列化、边界条件测试

5. 输出格式：
   - 先输出类实现代码
   - 再输出测试代码
   - 最后输出验证清单
```

---

### 模板2: 重构现有代码

```
请重构{文件路径}，从V1迁移到V2，要求：

1. 保留的部分：
   - {列出要保留的设计/方法}

2. 需要修改的部分：
   - {列出要修改的内容}

3. 新增的部分：
   - {列出要新增的功能}

4. 迁移步骤：
   - 先阅读V1代码并总结
   - 识别可保留和需修改的部分
   - 生成V2代码
   - 生成迁移测试（确保行为一致）

5. 输出：
   - V1分析总结
   - V2完整代码
   - 迁移对比表
   - 测试代码
```

---

### 模板3: 实现抽象方法

```
请为抽象类{AbstractClass}实现具体类{ConcreteClass}，要求：

1. 查阅抽象类定义：
   - 位置：{文件路径}
   - 需要实现的方法：{方法列表}

2. 实现要求：
   - 实现所有抽象方法
   - 符合{具体场景}的语义
   - 参考{参考实现}

3. 代码质量：
   - 完整类型注解和docstring
   - 实现示例代码
   - 完整测试

4. 输出：
   - 具体类实现
   - 使用示例
   - 测试代码
```

---

### 模板4: 修复Bug

```
发现Bug：{Bug描述}

位置：{文件路径}:{行号}

请修复这个Bug，要求：

1. 分析根因：
   - 为什么会出现这个Bug？
   - 影响范围是什么？

2. 修复方案：
   - 提出2-3个修复方案
   - 推荐最佳方案并说明理由

3. 实施修复：
   - 修改代码
   - 添加防御性检查
   - 更新相关文档

4. 测试：
   - 添加回归测试（防止再次出现）
   - 验证修复效果

5. 输出：
   - 根因分析
   - 修复代码
   - 测试代码
   - 提交消息
```

---

### 模板5: 添加测试

```
为{文件路径}添加测试，要求：

1. 测试覆盖：
   - 基础功能测试
   - 方法测试（每个公共方法）
   - 边界条件测试
   - 异常处理测试

2. 测试质量：
   - 使用pytest fixtures
   - 测试名称清晰（test_功能_场景）
   - 每个测试只测一件事
   - 使用AAA模式（Arrange-Act-Assert）

3. 覆盖率目标：
   - 目标覆盖率 > 80%
   - 关键路径 100%覆盖

4. 输出：
   - 完整测试文件
   - 测试运行命令
   - 覆盖率报告
```

---

### 模板6: 生成文档

```
为{模块}生成文档，要求：

1. 文档类型：
   - README.md（模块概览）
   - API文档（类和方法）
   - 使用指南（示例代码）

2. 文档内容：
   - 模块目的
   - 核心概念
   - 类图（如果适用）
   - 完整示例
   - 常见问题

3. 文档格式：
   - Markdown格式
   - 代码块有语法高亮
   - 包含目录导航

4. 输出：
   - README.md
   - API文档
   - 使用指南
```

---

## 🎓 最佳实践（AI必须遵守）

### 1. 总是查阅文档

❌ **错误做法**:
```
直接凭记忆或常识生成代码
```

✅ **正确做法**:
```
1. 先查CODE_STANDARDS_AND_TEMPLATES.md
2. 再查相关的架构决策文档
3. 最后查详细设计文档
4. 基于文档生成代码
```

---

### 2. 使用完整示例

❌ **错误做法**:
```python
# 只给类定义，没有示例
class GenreConfig:
    def __init__(self, genre_id, genre_name):
        self.genre_id = genre_id
        self.genre_name = genre_name
```

✅ **正确做法**:
```python
@dataclass
class GenreConfig:
    """题材配置
    
    Example:
        >>> config = GenreConfig(
        ...     genre_id=GenreID.URBAN,
        ...     genre_name="都市"
        ... )
        >>> config.validate()
        True
    """
    genre_id: GenreID
    genre_name: str
    
    def validate(self) -> bool:
        """验证配置"""
        return True

# 文件末尾
# if __name__ == "__main__":
#     config = GenreConfig(GenreID.URBAN, "都市")
#     print(config.validate())  # True
```

---

### 3. 增量实现

❌ **错误做法**:
```
一次性实现复杂的完整功能
```

✅ **正确做法**:
```
Step 1: 实现最简单的版本
Step 2: 添加基础功能
Step 3: 添加高级功能
Step 4: 优化性能
```

**示例**:
```python
# Step 1: 最简单版本
@dataclass
class GenreConfig:
    genre_id: str
    genre_name: str

# Step 2: 添加验证
@dataclass
class GenreConfig:
    genre_id: str
    genre_name: str
    
    def validate(self):
        if not self.genre_name:
            raise ValueError("genre_name required")

# Step 3: 添加序列化
@dataclass
class GenreConfig:
    genre_id: str
    genre_name: str
    
    def validate(self):
        ...
    
    def to_dict(self):
        return {"genre_id": self.genre_id, ...}
```

---

### 4. 先测试后实现（TDD）

❌ **错误做法**:
```
先写代码，最后才写测试（或不写测试）
```

✅ **正确做法**:
```
1. 先写测试（定义期望行为）
2. 运行测试（应该失败）
3. 实现代码
4. 运行测试（应该通过）
5. 重构优化
```

---

### 5. 明确的错误消息

❌ **错误做法**:
```python
if not genre_name:
    raise ValueError("Invalid")  # 不清楚什么invalid
```

✅ **正确做法**:
```python
if not genre_name:
    raise ValueError(
        f"Genre name cannot be empty for genre_id={genre_id}"
    )
```

---

## 🐛 常见问题与解决方案

### 问题1: AI不知道从哪里开始

**症状**: AI问"需要什么信息才能开始"

**解决方案**:
1. 告诉AI查阅`00_DOCUMENTATION_GENERATION_PLAN.md`
2. 告诉AI当前在M1 Week X
3. 告诉AI查阅`work/m1/M1_PROGRESS.md`获取当前任务

---

### 问题2: AI生成的代码风格不一致

**症状**: 每次生成的代码格式不同

**解决方案**:
1. 在每次请求中明确提到`CODE_STANDARDS_AND_TEMPLATES.md`
2. 使用提示词模板（强制使用模板）
3. 要求AI先查阅代码规范再生成

---

### 问题3: AI忘记生成测试

**症状**: 只有代码实现，没有测试

**解决方案**:
1. 在提示词中明确要求"包括测试"
2. 使用"模板1: 实现新类"（自动包含测试要求）
3. 验证时检查是否有测试文件

---

### 问题4: AI不理解项目结构

**症状**: 文件放错位置，导入路径错误

**解决方案**:
1. 要求AI先总结项目结构（基于本文档）
2. 明确指定文件路径
3. 验证导入语句是否正确

---

### 问题5: AI生成代码过于复杂

**症状**: 第一版就实现了所有功能

**解决方案**:
1. 强调"增量实现"原则
2. 要求"最简单可用版本"
3. 分步骤请求（Step 1, Step 2, ...）

---

## 🔗 相关文档

### 必读文档
1. [代码规范与模板](./CODE_STANDARDS_AND_TEMPLATES.md)
2. [V1到V2迁移指南](./V1_TO_V2_MIGRATION_GUIDE.md)
3. [架构决策记录](../architecture-decisions/12_ARCHITECTURE_DECISION_RECORD_PART1.md)

### 实施指南（即将生成）
1. Genre系统完整实施手册
2. 数据模型完整定义
3. 测试驱动开发指南

### 进度跟踪
1. [M1进度跟踪](../../work/m1/M1_PROGRESS.md)
2. [每日行动清单](../../DAILY_ACTION_CHECKLIST.md)

---

## ✅ AI自检清单

每次生成代码后，AI应该自我检查：

```markdown
- [ ] 查阅了CODE_STANDARDS_AND_TEMPLATES.md
- [ ] 查阅了相关架构决策文档
- [ ] 使用了标准代码模板
- [ ] 包含完整类型注解
- [ ] 包含详细docstring（含Example）
- [ ] 遵循命名规范
- [ ] 包含使用示例
- [ ] 生成了测试代码
- [ ] 测试覆盖关键路径
- [ ] 文件路径正确
- [ ] 导入语句正确
```

---

**制定人**: Claude Opus 4.8  
**文档版本**: v1.0  
**最后更新**: 2026-09-18  
**状态**: ✅ 完整
