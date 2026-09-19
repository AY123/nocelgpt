# 代码规范与模板 - ANovel V2项目

**版本**: v1.0  
**制定日期**: 2026-09-18  
**适用范围**: 所有AI生成的Python代码  
**状态**: 完整  

---

## 📋 文档目的

本文档为ANovel V2项目定义统一的代码规范和可复用模板，确保AI生成的代码风格一致、质量可靠。

**核心目标**:
1. 统一代码风格（AI生成代码保持一致）
2. 提供可复用模板（减少重复工作）
3. 提高代码质量（可读性、可维护性）
4. 加速开发速度（直接复制模板）

---

## 🎯 核心原则

### 1. 明确胜于隐晦（Explicit is better than implicit）

```python
# ❌ 不好：类型不明确
def process(data):
    return data.get("result")

# ✅ 好：类型明确
def process(data: Dict[str, Any]) -> Optional[str]:
    return data.get("result")
```

---

### 2. 完整胜于简洁（Complete is better than concise）

```python
# ❌ 不好：缺少文档
class GenreConfig:
    def __init__(self, genre_id, name):
        self.genre_id = genre_id
        self.name = name

# ✅ 好：完整文档
@dataclass
class GenreConfig:
    """题材配置
    
    定义一个题材的完整配置信息。
    
    Attributes:
        genre_id: 题材唯一标识
        name: 题材中文名称
        
    Example:
        >>> config = GenreConfig(GenreID.URBAN, "都市")
        >>> print(config.name)
        都市
    """
    genre_id: GenreID
    name: str
```

---

### 3. 可测试胜于复杂（Testable is better than complex）

```python
# ❌ 不好：难以测试
def validate_and_save(data):
    if not data.get("name"):
        raise ValueError("Invalid")
    db.save(data)  # 硬编码依赖
    return True

# ✅ 好：易于测试
def validate_name(name: str) -> bool:
    """验证名称（纯函数，易测试）"""
    if not name:
        raise ValueError("Name cannot be empty")
    return True

def save_data(data: Dict, storage: Storage):
    """保存数据（依赖注入，易测试）"""
    storage.save(data)
```

---

## 📐 Python代码规范

### 基础规范（遵循PEP 8 + 扩展）

#### 1. 缩进与空格

```python
# ✅ 使用4个空格缩进
def function_name():
    if condition:
        do_something()
    return result

# ❌ 不使用Tab
```

#### 2. 行长度

```python
# ✅ 每行不超过88字符（Black标准）
def long_function_name(
    parameter1: str,
    parameter2: int,
    parameter3: Optional[Dict] = None
) -> bool:
    """Long function with multiple parameters."""
    pass

# ❌ 单行过长
def long_function_name(parameter1: str, parameter2: int, parameter3: Optional[Dict] = None) -> bool:
```

#### 3. 导入语句

```python
# ✅ 正确的导入顺序
# 1. 标准库
import os
import sys
from typing import Dict, List, Optional

# 2. 第三方库
import pytest
from dataclasses import dataclass

# 3. 本地模块
from runtime.genre.config import GenreConfig
from runtime.canon.fact import Fact

# ❌ 错误：混乱的导入顺序
from runtime.genre.config import GenreConfig
import os
import pytest
```

#### 4. 空行规则

```python
# ✅ 正确的空行
import os

from typing import Dict


class MyClass:
    """Class docstring."""
    
    def __init__(self):
        """Init method."""
        pass
    
    def method1(self):
        """Method 1."""
        pass


def standalone_function():
    """Standalone function."""
    pass


# 两个顶层定义之间：2个空行
# 类方法之间：1个空行
```

---

### 命名规范

#### 1. 类名（PascalCase）

```python
# ✅ 好的类名
class GenreConfig:
    pass

class ProgressionModel:
    pass

class ConstraintViolation:
    pass

# ❌ 不好的类名
class genreconfig:  # 应该用PascalCase
class genre_config:  # 不是snake_case
class GENRECONFIG:  # 不是全大写
```

#### 2. 函数和方法名（snake_case）

```python
# ✅ 好的函数名
def validate_config():
    pass

def get_progression_model():
    pass

def check_constraint_violation():
    pass

# ❌ 不好的函数名
def ValidateConfig():  # 应该用snake_case
def getProgressionModel():  # 不是camelCase
def CHECK_VIOLATION():  # 不是全大写
```

#### 3. 变量名（snake_case）

```python
# ✅ 好的变量名
genre_config = GenreConfig()
user_input = "test"
is_valid = True
total_count = 0

# ❌ 不好的变量名
GenreConfig = GenreConfig()  # 与类名冲突
userInput = "test"  # 不是camelCase
IsValid = True  # 不是PascalCase
```

#### 4. 常量（UPPER_SNAKE_CASE）

```python
# ✅ 好的常量
MAX_LENGTH = 1000
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.example.com"

# ❌ 不好的常量
max_length = 1000  # 应该全大写
MaxLength = 1000  # 不是PascalCase
```

#### 5. 私有成员（_leading_underscore）

```python
# ✅ 私有方法和属性
class MyClass:
    def __init__(self):
        self._private_attr = "private"
    
    def _private_method(self):
        """私有方法，不对外暴露"""
        pass
    
    def public_method(self):
        """公共方法"""
        self._private_method()
```

---

### 类型注解

#### 1. 基础类型

```python
from typing import List, Dict, Set, Tuple, Optional, Union, Any

# ✅ 完整的类型注解
def process_data(
    name: str,
    age: int,
    score: float,
    is_valid: bool,
    tags: List[str],
    metadata: Dict[str, Any],
    optional_param: Optional[int] = None
) -> Tuple[bool, str]:
    """处理数据
    
    Args:
        name: 用户名称
        age: 用户年龄
        score: 分数
        is_valid: 是否有效
        tags: 标签列表
        metadata: 元数据字典
        optional_param: 可选参数
        
    Returns:
        (是否成功, 消息)
    """
    return True, "Success"
```

#### 2. 复杂类型

```python
from typing import Callable, Iterator, Generator

# ✅ 函数类型
def apply_function(
    data: List[int],
    func: Callable[[int], int]
) -> List[int]:
    """应用函数到列表"""
    return [func(x) for x in data]

# ✅ 生成器类型
def generate_numbers(n: int) -> Generator[int, None, None]:
    """生成数字"""
    for i in range(n):
        yield i
```

#### 3. 泛型类型

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Container(Generic[T]):
    """泛型容器
    
    Example:
        >>> container = Container[int]()
        >>> container.add(42)
    """
    
    def __init__(self):
        self._items: List[T] = []
    
    def add(self, item: T) -> None:
        self._items.append(item)
    
    def get(self, index: int) -> T:
        return self._items[index]
```

---

### 文档字符串（Docstring）

#### 1. 模块级文档

```python
"""Genre系统核心模块

本模块包含Genre系统的核心类和函数：
- GenreConfig: 题材配置
- GenreConstraints: 题材约束
- ProgressionModel: 进阶模型

Example:
    >>> from runtime.genre import GenreConfig, GenreID
    >>> config = GenreConfig(GenreID.URBAN, "都市")
    
Author: Claude Opus 4.8
Created: 2026-09-18
"""

from typing import Dict
# ... rest of module
```

#### 2. 类级文档（完整格式）

```python
class GenreConfig:
    """题材配置
    
    定义一个题材的完整配置信息，包括约束、进阶模型、Prompt模板等。
    
    每个题材必须定义一个GenreConfig实例并注册到GenreRegistry。
    
    Attributes:
        genre_id: 题材唯一标识符（枚举）
        genre_name: 题材中文名称
        constraints: 题材约束配置
        progression_model: 进阶模型类
        
    Example:
        基本用法：
        >>> config = GenreConfig(
        ...     genre_id=GenreID.URBAN,
        ...     genre_name="都市",
        ...     constraints=UrbanConstraints(),
        ...     progression_model=WealthProgressionModel
        ... )
        >>> config.validate()
        True
        
        获取Prompt模板：
        >>> template = config.get_prompt_template("outline")
        >>> print(template[:50])
        你是起点中文网资深编辑，擅长都市题材...
        
    Notes:
        - genre_id必须是GenreID枚举成员
        - progression_model必须是ProgressionModel的子类
        - constraints不能为None
        
    See Also:
        - GenreConstraints: 题材约束定义
        - ProgressionModel: 进阶模型抽象基类
        - GenreRegistry: 题材注册表
    """
    
    def __init__(self, ...):
        pass
```

#### 3. 方法级文档（完整格式）

```python
def validate_transition(
    self,
    from_tier: str,
    to_tier: str,
    context: TransitionContext
) -> TransitionValidation:
    """验证晋级是否合理
    
    检查从from_tier到to_tier的晋级是否符合该题材的进阶规则。
    考虑晋级跨度、经过章节数、是否有机缘等因素。
    
    Args:
        from_tier: 当前等级名称
        to_tier: 目标等级名称
        context: 晋级上下文，包含章节数、机缘等信息
        
    Returns:
        TransitionValidation对象，包含验证结果和原因
        
    Raises:
        ValueError: 如果from_tier或to_tier不在等级列表中
        
    Example:
        正常晋级：
        >>> model = WealthProgressionModel()
        >>> context = TransitionContext(chapters_passed=10)
        >>> result = model.validate_transition("温饱", "小康", context)
        >>> result.is_valid
        True
        
        跨度过大：
        >>> context = TransitionContext(chapters_passed=2)
        >>> result = model.validate_transition("贫困线", "富豪", context)
        >>> result.is_valid
        False
        >>> result.reason
        '跨度过大，不符合现实逻辑'
        
    Notes:
        - 不同题材有不同的晋级规则
        - 有机缘可以加快晋级速度
        - 晋级必须有足够的章节数支撑
        
    See Also:
        - TransitionContext: 晋级上下文定义
        - TransitionValidation: 验证结果定义
    """
    pass
```

#### 4. 函数级文档（简化格式，用于简单函数）

```python
def calculate_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """计算两点之间的欧几里得距离
    
    Args:
        x1, y1: 第一个点的坐标
        x2, y2: 第二个点的坐标
        
    Returns:
        两点之间的距离
    """
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
```

---

## 📦 代码模板库

### 模板1: Dataclass（数据类）

```python
# ============================================================
# Dataclass模板
# 用于：数据容器、配置类、简单的值对象
# ============================================================

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum

@dataclass
class ClassName:
    """类的一句话描述
    
    详细描述这个类的作用、使用场景。
    
    Attributes:
        required_field: 必需字段描述
        optional_field: 可选字段描述
        list_field: 列表字段描述
        dict_field: 字典字段描述
        
    Example:
        >>> obj = ClassName(
        ...     required_field="value",
        ...     optional_field=42
        ... )
        >>> obj.method()
        expected_result
        
    Notes:
        - 重要的使用注意事项
        - 常见的使用模式
    """
    
    # 必需字段（按字母顺序）
    required_field: str
    required_field2: int
    
    # 可选字段
    optional_field: Optional[str] = None
    optional_field2: Optional[int] = None
    
    # 有默认值的字段
    list_field: List[str] = field(default_factory=list)
    dict_field: Dict[str, Any] = field(default_factory=dict)
    bool_field: bool = False
    
    def __post_init__(self):
        """初始化后验证
        
        在所有字段赋值后立即调用，用于验证或转换。
        
        Raises:
            ValueError: 如果验证失败
        """
        self._validate()
    
    def _validate(self):
        """验证字段有效性
        
        Raises:
            ValueError: 字段无效时
        """
        if not self.required_field:
            raise ValueError("required_field cannot be empty")
        
        if self.required_field2 < 0:
            raise ValueError("required_field2 must be non-negative")
    
    def method_name(self, param: str) -> bool:
        """方法描述
        
        Args:
            param: 参数描述
            
        Returns:
            返回值描述
        """
        # 实现
        return True
    
    def to_dict(self) -> Dict:
        """转换为字典（用于序列化）
        
        Returns:
            包含所有字段的字典
        """
        return {
            "required_field": self.required_field,
            "required_field2": self.required_field2,
            "optional_field": self.optional_field,
            "list_field": self.list_field,
            "dict_field": self.dict_field,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ClassName':
        """从字典创建实例（用于反序列化）
        
        Args:
            data: 字典数据
            
        Returns:
            ClassName实例
            
        Raises:
            KeyError: 如果缺少必需字段
        """
        return cls(
            required_field=data["required_field"],
            required_field2=data["required_field2"],
            optional_field=data.get("optional_field"),
            list_field=data.get("list_field", []),
            dict_field=data.get("dict_field", {}),
        )


# ============================================================
# 使用示例
# ============================================================

# if __name__ == "__main__":
#     # 示例1：创建对象
#     obj = ClassName(
#         required_field="test",
#         required_field2=42
#     )
#     
#     # 示例2：调用方法
#     result = obj.method_name("param")
#     print(result)  # True
#     
#     # 示例3：序列化
#     data = obj.to_dict()
#     restored = ClassName.from_dict(data)
#     assert restored.required_field == obj.required_field
```

---

### 模板2: 抽象基类（ABC）

```python
# ============================================================
# 抽象基类模板
# 用于：定义接口、多态、策略模式
# ============================================================

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class AbstractClassName(ABC):
    """抽象类描述
    
    定义{功能}的抽象接口。所有具体实现必须继承此类。
    
    Subclasses must implement:
        - abstract_method1: 描述
        - abstract_method2: 描述
        
    Example:
        >>> class ConcreteClass(AbstractClassName):
        ...     def abstract_method1(self):
        ...         return "implementation"
        >>> obj = ConcreteClass()
        >>> obj.abstract_method1()
        'implementation'
    """
    
    @abstractmethod
    def abstract_method1(self, param: str) -> str:
        """抽象方法1描述
        
        Args:
            param: 参数描述
            
        Returns:
            返回值描述
        """
        pass
    
    @abstractmethod
    def abstract_method2(self) -> List[str]:
        """抽象方法2描述
        
        Returns:
            返回值描述
        """
        pass
    
    # 具体方法（可选，提供默认实现）
    def concrete_method(self, param: int) -> bool:
        """具体方法描述
        
        提供默认实现，子类可以覆盖。
        
        Args:
            param: 参数描述
            
        Returns:
            返回值描述
        """
        return param > 0


# ============================================================
# 具体实现
# ============================================================

class ConcreteClassName(AbstractClassName):
    """具体实现描述
    
    {AbstractClassName}的具体实现，用于{场景}。
    """
    
    def __init__(self, config: Dict):
        """初始化
        
        Args:
            config: 配置字典
        """
        self.config = config
    
    def abstract_method1(self, param: str) -> str:
        """实现abstract_method1"""
        return f"processed: {param}"
    
    def abstract_method2(self) -> List[str]:
        """实现abstract_method2"""
        return ["item1", "item2"]
```

---

### 模板3: 枚举（Enum）

```python
# ============================================================
# 枚举模板
# 用于：定义固定的选项集合
# ============================================================

from enum import Enum, auto

class EnumName(Enum):
    """枚举描述
    
    定义{功能}的所有可能值。
    
    Values:
        VALUE1: 值1描述
        VALUE2: 值2描述
        VALUE3: 值3描述
        
    Example:
        >>> value = EnumName.VALUE1
        >>> value.name
        'VALUE1'
        >>> value.value
        'value1'
    """
    VALUE1 = "value1"
    VALUE2 = "value2"
    VALUE3 = "value3"
    
    def to_string(self) -> str:
        """转换为字符串"""
        return self.value
    
    @classmethod
    def from_string(cls, value: str) -> 'EnumName':
        """从字符串创建
        
        Args:
            value: 字符串值
            
        Returns:
            EnumName实例
            
        Raises:
            ValueError: 如果值无效
        """
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Invalid value: {value}")


# ============================================================
# 使用auto()自动赋值
# ============================================================

class StatusEnum(Enum):
    """状态枚举"""
    PENDING = auto()     # 自动赋值为1
    IN_PROGRESS = auto() # 自动赋值为2
    COMPLETED = auto()   # 自动赋值为3
```

---

### 模板4: 异常类

```python
# ============================================================
# 异常类模板
# 用于：自定义异常，更清晰的错误处理
# ============================================================

class ProjectBaseException(Exception):
    """项目基础异常
    
    所有项目自定义异常的基类。
    """
    pass


class ValidationError(ProjectBaseException):
    """验证错误
    
    当数据验证失败时抛出。
    
    Attributes:
        message: 错误消息
        field: 出错的字段名
        value: 导致错误的值
    """
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)
    
    def __str__(self):
        if self.field:
            return f"Validation failed for field '{self.field}': {self.message}"
        return f"Validation failed: {self.message}"


class NotFoundError(ProjectBaseException):
    """资源未找到错误"""
    
    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(
            f"{resource_type} with id '{resource_id}' not found"
        )


# ============================================================
# 使用示例
# ============================================================

# def validate_config(config):
#     if not config.get("name"):
#         raise ValidationError(
#             "Name is required",
#             field="name",
#             value=config.get("name")
#         )
```

---

### 模板5: 单例模式

```python
# ============================================================
# 单例模式模板
# 用于：注册表、配置管理器、全局状态
# ============================================================

from typing import Optional

class Singleton:
    """单例基类
    
    使用示例：
        >>> class MyRegistry(Singleton):
        ...     def __init__(self):
        ...         self.data = {}
        >>> r1 = MyRegistry()
        >>> r2 = MyRegistry()
        >>> r1 is r2
        True
    """
    _instance: Optional['Singleton'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


# ============================================================
# 具体实现
# ============================================================

class GenreRegistry(Singleton):
    """题材注册表（单例）
    
    全局唯一的题材配置注册表。
    """
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._configs: Dict[GenreID, GenreConfig] = {}
            self._initialized = True
    
    def register(self, config: GenreConfig):
        """注册题材配置"""
        self._configs[config.genre_id] = config
    
    def get(self, genre_id: GenreID) -> GenreConfig:
        """获取题材配置"""
        if genre_id not in self._configs:
            raise NotFoundError("GenreConfig", genre_id.value)
        return self._configs[genre_id]
```

---

## 🧪 测试模板

### 模板1: 基础测试类

```python
# ============================================================
# 测试文件: tests/runtime/module/test_classname.py
# ============================================================

import pytest
from runtime.module.classname import ClassName


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def sample_object():
    """创建示例对象用于测试
    
    Returns:
        ClassName实例
    """
    return ClassName(
        required_field="test",
        required_field2=42
    )


# ============================================================
# 基础功能测试
# ============================================================

class TestClassNameBasics:
    """测试ClassName基础功能"""
    
    def test_creation(self):
        """测试对象创建"""
        obj = ClassName(
            required_field="test",
            required_field2=42
        )
        assert obj.required_field == "test"
        assert obj.required_field2 == 42
    
    def test_validation_success(self, sample_object):
        """测试验证成功场景"""
        # 不应抛出异常
        sample_object._validate()
    
    def test_validation_failure_empty_field(self):
        """测试验证失败：空字段"""
        with pytest.raises(ValueError, match="required_field cannot be empty"):
            ClassName(required_field="", required_field2=42)
    
    def test_validation_failure_negative_number(self):
        """测试验证失败：负数"""
        with pytest.raises(ValueError, match="must be non-negative"):
            ClassName(required_field="test", required_field2=-1)


# ============================================================
# 方法测试
# ============================================================

class TestClassNameMethods:
    """测试ClassName的方法"""
    
    def test_method_name_success(self, sample_object):
        """测试method_name成功场景"""
        result = sample_object.method_name("param")
        assert result is True
    
    def test_method_name_with_empty_param(self, sample_object):
        """测试method_name：空参数"""
        result = sample_object.method_name("")
        assert result is False


# ============================================================
# 序列化测试
# ============================================================

class TestClassNameSerialization:
    """测试ClassName的序列化"""
    
    def test_to_dict(self, sample_object):
        """测试to_dict方法"""
        data = sample_object.to_dict()
        
        assert isinstance(data, dict)
        assert data["required_field"] == "test"
        assert data["required_field2"] == 42
    
    def test_from_dict(self):
        """测试from_dict方法"""
        data = {
            "required_field": "test",
            "required_field2": 42,
            "optional_field": "optional"
        }
        
        obj = ClassName.from_dict(data)
        
        assert obj.required_field == "test"
        assert obj.required_field2 == 42
        assert obj.optional_field == "optional"
    
    def test_round_trip(self, sample_object):
        """测试序列化往返"""
        data = sample_object.to_dict()
        restored = ClassName.from_dict(data)
        
        assert restored.required_field == sample_object.required_field
        assert restored.required_field2 == sample_object.required_field2


# ============================================================
# 边界条件测试
# ============================================================

class TestClassNameEdgeCases:
    """测试ClassName的边界条件"""
    
    def test_with_none_optional_field(self):
        """测试可选字段为None"""
        obj = ClassName(
            required_field="test",
            required_field2=42,
            optional_field=None
        )
        assert obj.optional_field is None
    
    def test_with_empty_list_field(self, sample_object):
        """测试空列表字段"""
        assert sample_object.list_field == []
    
    def test_with_large_value(self):
        """测试大数值"""
        obj = ClassName(
            required_field="test",
            required_field2=1000000
        )
        assert obj.required_field2 == 1000000
```

---

## 📝 文件组织规范

### 1. 文件命名

```bash
# ✅ 模块文件（小写+下划线）
genre_config.py
progression_model.py
constraint_validator.py

# ✅ 测试文件（test_前缀）
test_genre_config.py
test_progression_model.py

# ❌ 不好的命名
GenreConfig.py  # 不要用大写
genre-config.py  # 不要用连字符
```

### 2. 目录结构

```
runtime/
├── __init__.py
├── genre/
│   ├── __init__.py
│   ├── config.py           # GenreConfig
│   ├── constraints.py      # GenreConstraints
│   ├── progression.py      # ProgressionModel
│   ├── registry.py         # GenreRegistry
│   └── detector.py         # GenreDetector
│
├── canon/
│   ├── __init__.py
│   ├── fact.py
│   └── ...
│
tests/
├── __init__.py
├── runtime/
│   ├── __init__.py
│   ├── genre/
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── test_constraints.py
│   │   └── ...
```

### 3. __init__.py规范

```python
# runtime/genre/__init__.py

"""Genre系统

题材优先架构的核心模块。

Public API:
    - GenreConfig: 题材配置
    - GenreConstraints: 题材约束
    - ProgressionModel: 进阶模型抽象
    - GenreRegistry: 题材注册表
"""

from .config import GenreConfig
from .constraints import GenreConstraints, ConstraintViolation
from .progression import ProgressionModel, TransitionContext
from .registry import GenreRegistry

__all__ = [
    "GenreConfig",
    "GenreConstraints",
    "ConstraintViolation",
    "ProgressionModel",
    "TransitionContext",
    "GenreRegistry",
]
```

---

## 🎨 代码风格检查清单

### 生成代码后必须检查

```markdown
## ✅ 代码质量检查清单

### 基础规范
- [ ] 使用4空格缩进（不使用Tab）
- [ ] 行长度不超过88字符
- [ ] 导入语句按顺序分组（标准库→第三方→本地）
- [ ] 顶层定义之间有2个空行

### 命名规范
- [ ] 类名：PascalCase
- [ ] 函数/方法名：snake_case
- [ ] 变量名：snake_case
- [ ] 常量：UPPER_SNAKE_CASE
- [ ] 私有成员：_leading_underscore

### 类型注解
- [ ] 所有函数参数有类型注解
- [ ] 所有函数返回值有类型注解
- [ ] 复杂类型使用typing模块

### 文档字符串
- [ ] 所有公共类有docstring
- [ ] 所有公共方法有docstring
- [ ] docstring包含Args/Returns/Raises
- [ ] docstring包含Example（类和复杂方法）

### 代码结构
- [ ] 使用@dataclass装饰器（数据类）
- [ ] 验证逻辑在__post_init__中
- [ ] 提供to_dict/from_dict方法（需要序列化时）
- [ ] 文件末尾有使用示例（注释掉）

### 测试
- [ ] 有对应的测试文件
- [ ] 测试覆盖基础功能
- [ ] 测试覆盖边界条件
- [ ] 测试覆盖异常情况
```

---

## 📦 Git提交消息规范

### 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type类型

```
feat:     新功能
fix:      Bug修复
docs:     文档更新
style:    代码格式（不影响功能）
refactor: 重构
test:     测试相关
chore:    构建/工具相关
```

### 示例

```bash
# 好的提交消息
git commit -m "feat(genre): add GenreConfig class

Implement GenreConfig with full type annotations and validation.

Includes:
- Complete dataclass definition
- Validation in __post_init__
- Serialization methods (to_dict/from_dict)
- Comprehensive docstrings with examples
- Unit tests with 95% coverage

Related to M1 Week 1 Genre system implementation.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 🔗 相关文档

### 必读
1. [AI辅助开发指南](./01_AI_ASSISTED_DEVELOPMENT_GUIDE.md)
2. [V1到V2迁移指南](./03_V1_TO_V2_MIGRATION_GUIDE.md)

### 参考
1. [PEP 8 -- Style Guide for Python Code](https://peps.python.org/pep-0008/)
2. [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

---

**制定人**: Claude Opus 4.8  
**文档版本**: v1.0  
**最后更新**: 2026-09-18  
**状态**: ✅ 完整
