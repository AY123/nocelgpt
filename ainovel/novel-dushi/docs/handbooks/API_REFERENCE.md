# API 参考文档

**版本**: 1.0  
**日期**: 2026-09-09  
**适用于**: AI-Novel Runtime v2.0+

---

## 📖 目录

1. [runtime.contract](#runtimecontract)
2. [runtime.serialize](#runtimeserialize)
3. [runtime.publishing](#runtimepublishing)

---

## runtime.contract

契约和状态管理模块

### ChapterContract

章节契约类，定义每章必须满足的约束。

#### 构造函数

```python
ChapterContract(
    chapter_number: int,
    chapter_id: str,
    objective: str,
    antagonist: str,
    protagonist_name: str,
    date: str,
    irreversible_change: str,
    next_hook: str,
    entry_hook_resolution: Optional[str] = None,
    golden_finger_use: Optional[str] = None,
    locations: Optional[List[str]] = None,
    must_appear_characters: Optional[List[str]] = None,
    story_bible_hash: Optional[str] = None
)
```

**参数**:
- `chapter_number`: 章节号
- `chapter_id`: 章节ID（如 "CHAPTER-00001"）
- `objective`: 章节目标
- `antagonist`: 对手
- `protagonist_name`: 主角名字（硬约束）
- `date`: 日期（硬约束）
- `irreversible_change`: 不可逆改变
- `next_hook`: 下章钩子
- `entry_hook_resolution`: 入口钩子解决（可选）
- `golden_finger_use`: 金手指使用（可选）
- `locations`: 地点列表（可选）
- `must_appear_characters`: 必须出现的人物（可选）
- `story_bible_hash`: Story Bible 哈希（可选）

#### validate()

验证草稿是否满足契约。

```python
def validate(
    self,
    draft_text: str,
    extracted_data: Optional[Dict[str, Any]] = None
) -> ValidationResult
```

**参数**:
- `draft_text`: 草稿文本
- `extracted_data`: 提取的结构化数据（可选）

**返回**: `ValidationResult` 对象

**示例**:
```python
contract = ChapterContract(
    chapter_number=1,
    chapter_id="CHAPTER-00001",
    protagonist_name="陈默",
    date="2013-01-15",
    objective="避免重蹈前世覆辙",
    antagonist="赵鹏程",
    irreversible_change="改变历史轨迹",
    next_hook="明天见周子铭"
)

result = contract.validate(draft_text, {
    'protagonist_name': '陈默',
    'date': '2013-01-15'
})

if result.passed:
    print("验证通过")
else:
    print(f"错误: {result.errors}")
```

#### to_dict()

转换为字典。

```python
def to_dict(self) -> Dict[str, Any]
```

**返回**: 字典表示

---

### ValidationResult

验证结果类。

#### 属性

```python
@dataclass
class ValidationResult:
    passed: bool              # 是否通过
    errors: List[str]        # 错误列表（硬约束）
    warnings: List[str]      # 警告列表（软约束）
```

**示例**:
```python
if result.passed:
    print("✓ 验证通过")
    if result.warnings:
        print(f"警告: {result.warnings}")
else:
    print(f"✗ 验证失败")
    print(f"错误: {result.errors}")
```

---

### load_story_bible_contracts()

从 Story Bible 加载契约。

```python
def load_story_bible_contracts(
    story_bible_path: str
) -> List[ChapterContract]
```

**参数**:
- `story_bible_path`: Story Bible 文件路径

**返回**: 契约列表

**示例**:
```python
from runtime.contract import load_story_bible_contracts

contracts = load_story_bible_contracts("story-bible.yaml")
print(f"加载了 {len(contracts)} 个契约")

# 获取第1章契约
contract1 = contracts[0]
```

---

### StoryState

故事状态类，表示跨章节的世界状态。

#### 构造函数

```python
StoryState(
    current_date: str,
    current_location: str,
    chapter_number: int,
    protagonist: Character,
    characters: Dict[str, Character],
    relationships: Optional[Dict[str, Relationship]] = None,
    open_threads: Optional[List[Thread]] = None,
    completed_threads: Optional[List[Thread]] = None
)
```

**参数**:
- `current_date`: 当前日期
- `current_location`: 当前地点
- `chapter_number`: 章节号
- `protagonist`: 主角
- `characters`: 人物字典
- `relationships`: 人物关系（可选）
- `open_threads`: 未完成线索（可选）
- `completed_threads`: 已完成线索（可选）

#### create_initial_state()

创建初始状态（第0章）。

```python
@classmethod
def create_initial_state(
    cls,
    story_bible: Dict[str, Any]
) -> 'StoryState'
```

**参数**:
- `story_bible`: Story Bible 字典

**返回**: 初始 StoryState

**示例**:
```python
import yaml
from runtime.contract import StoryState

with open("story-bible.yaml") as f:
    bible = yaml.safe_load(f)

initial_state = StoryState.create_initial_state(bible)
print(initial_state.summary())
```

#### extract_from_draft()

从草稿提取状态。

```python
@classmethod
def extract_from_draft(
    cls,
    draft_text: str,
    chapter_number: int,
    previous_state: Optional['StoryState'] = None
) -> 'StoryState'
```

**参数**:
- `draft_text`: 草稿文本
- `chapter_number`: 章节号
- `previous_state`: 上一章状态（可选）

**返回**: 新的 StoryState

**示例**:
```python
# 第1章
state1 = StoryState.extract_from_draft(
    draft_text=chapter1_text,
    chapter_number=1,
    previous_state=initial_state
)

# 第2章
state2 = StoryState.extract_from_draft(
    draft_text=chapter2_text,
    chapter_number=2,
    previous_state=state1
)
```

#### validate_continuity()

验证连续性。

```python
def validate_continuity(
    self,
    previous_state: 'StoryState'
) -> List[str]
```

**参数**:
- `previous_state`: 上一章状态

**返回**: 错误列表（空列表表示连续）

**示例**:
```python
errors = state2.validate_continuity(state1)

if errors:
    print("连续性错误:")
    for err in errors:
        print(f"  - {err}")
else:
    print("✓ 连续性检查通过")
```

#### summary()

生成状态摘要。

```python
def summary(self) -> str
```

**返回**: 人类可读的摘要

**示例**:
```python
print(state.summary())
# 输出:
# StoryState 摘要 (第1章):
#   日期: 2013-01-15
#   地点: 恒远投资公司
#   主角: 陈默
#   人物数: 3
#   未完成线索: 2
#   已完成线索: 0
```

---

### ProductionState

生产状态枚举。

#### 状态值

```python
class ProductionState(Enum):
    GENERATED = "generated"              # 已生成
    NEEDS_REVISION = "needs_revision"    # 需要修改
    BLOCKED = "blocked"                  # 被阻塞
    HUMAN_APPROVED = "human_approved"    # 人工审核通过
    PUBLISHED = "published"              # 已发布
    INVALIDATED = "invalidated"          # 已作废
```

#### 判断方法

**can_export()**

是否可以导出（发布）。

```python
def can_export(self) -> bool
```

**返回**: True 如果状态为 HUMAN_APPROVED 或 PUBLISHED

**示例**:
```python
state = ProductionState.HUMAN_APPROVED
if state.can_export():
    export_chapter()
```

**can_proceed_next()**

是否可以继续下一章。

```python
def can_proceed_next(self) -> bool
```

**返回**: True 如果状态为 HUMAN_APPROVED 或 PUBLISHED

**can_revise()**

是否可以修改。

```python
def can_revise(self) -> bool
```

**返回**: True 如果状态为 GENERATED 或 NEEDS_REVISION

**can_publish()**

是否可以发布。

```python
def can_publish(self) -> bool
```

**返回**: True 如果状态为 HUMAN_APPROVED

**is_terminal()**

是否是终态。

```python
def is_terminal(self) -> bool
```

**返回**: True 如果状态为 PUBLISHED 或 INVALIDATED

**is_blocked()**

是否被阻塞。

```python
def is_blocked(self) -> bool
```

**返回**: True 如果状态为 BLOCKED

**needs_attention()**

是否需要关注。

```python
def needs_attention(self) -> bool
```

**返回**: True 如果状态为 NEEDS_REVISION, BLOCKED 或 INVALIDATED

#### 状态转换

**can_transition_to()**

是否可以转换到新状态。

```python
def can_transition_to(self, new_state: 'ProductionState') -> bool
```

**参数**:
- `new_state`: 目标状态

**返回**: True 如果转换合法

**示例**:
```python
current = ProductionState.GENERATED
new = ProductionState.HUMAN_APPROVED

if current.can_transition_to(new):
    chapter_data['production_state'] = new.value
else:
    print("非法转换")
```

**next_states()**

获取所有可能的下一个状态。

```python
def next_states(self) -> List['ProductionState']
```

**返回**: 可能的下一个状态列表

**示例**:
```python
current = ProductionState.GENERATED
next_states = current.next_states()
# [NEEDS_REVISION, BLOCKED, HUMAN_APPROVED, INVALIDATED]
```

#### 显示方法

**display_name()**

返回友好的显示名称。

```python
def display_name(self) -> str
```

**display_emoji()**

返回表情符号。

```python
def display_emoji(self) -> str
```

**示例**:
```python
state = ProductionState.HUMAN_APPROVED
print(f"{state.display_emoji()} {state.display_name()}")
# 输出: ✅ 人工审核通过
```

---

### validate_state_transition()

验证状态转换是否合法。

```python
def validate_state_transition(
    current: ProductionState,
    new: ProductionState,
    raise_on_invalid: bool = True
) -> bool
```

**参数**:
- `current`: 当前状态
- `new`: 新状态
- `raise_on_invalid`: 如果非法是否抛出异常

**返回**: bool（是否合法）

**异常**: `ValueError` 如果非法且 `raise_on_invalid=True`

**示例**:
```python
from runtime.contract import validate_state_transition, ProductionState

try:
    validate_state_transition(
        ProductionState.GENERATED,
        ProductionState.PUBLISHED,
        raise_on_invalid=True
    )
except ValueError as e:
    print(f"转换非法: {e}")
```

---

## runtime.serialize

Serial 生产流程集成模块

### ContractIntegration

契约集成助手类。

#### 构造函数

```python
ContractIntegration(
    project_path: Path,
    story_bible_path: Optional[Path] = None
)
```

**参数**:
- `project_path`: 项目路径
- `story_bible_path`: Story Bible 路径（可选）

#### is_enabled()

是否启用契约集成。

```python
def is_enabled(self) -> bool
```

#### get_contract()

获取指定章节的契约。

```python
def get_contract(self, chapter_number: int) -> Optional[ChapterContract]
```

#### initialize_state()

初始化故事状态。

```python
def initialize_state(self) -> StoryState
```

#### validate_chapter_entry()

验证章节入口条件。

```python
def validate_chapter_entry(
    self,
    chapter_number: int,
    previous_state: Optional[ProductionState] = None
) -> Tuple[bool, List[str]]
```

**返回**: (是否可以继续, 错误列表)

#### validate_chapter_draft()

验证章节草稿。

```python
def validate_chapter_draft(
    self,
    chapter_number: int,
    draft_text: str,
    extracted_data: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Dict[str, Any]]
```

**返回**: (是否通过, 验证结果详情)

#### update_state_from_draft()

从草稿更新故事状态。

```python
def update_state_from_draft(
    self,
    chapter_number: int,
    draft_text: str
) -> StoryState
```

---

### create_integration()

创建契约集成实例。

```python
def create_integration(
    project_path: Path,
    enable_contract_integration: bool = False
) -> Optional[ContractIntegration]
```

**示例**:
```python
from runtime.serialize.contract_integration import create_integration
from pathlib import Path

integration = create_integration(
    project_path=Path("my-project"),
    enable_contract_integration=True
)

if integration and integration.is_enabled():
    print("契约集成已启用")
```

---

### SerialHookAdapter

Serial 钩子适配器类。

#### 构造函数

```python
SerialHookAdapter(
    project_path: Path,
    enable_contract_integration: bool = False
)
```

#### can_generate_chapter()

检查是否可以生成指定章节。

```python
def can_generate_chapter(
    self,
    chapter_number: int,
    force: bool = False
) -> Tuple[bool, List[str]]
```

**参数**:
- `chapter_number`: 章节号
- `force`: 是否强制生成（忽略阻塞）

**返回**: (是否可以生成, 错误列表)

**示例**:
```python
from runtime.serialize.serial_hook_adapter import create_adapter

adapter = create_adapter(
    project_path=Path("my-project"),
    enable_contract_integration=True
)

# 检查第2章
can_proceed, errors = adapter.can_generate_chapter(2)
if not can_proceed:
    print(f"无法生成: {errors}")
```

#### validate_and_save_chapter()

验证章节并保存。

```python
def validate_and_save_chapter(
    self,
    chapter_number: int,
    draft_text: str,
    save_callback: Optional[Callable] = None
) -> Tuple[bool, ProductionState]
```

**参数**:
- `chapter_number`: 章节号
- `draft_text`: 草稿文本
- `save_callback`: 保存回调函数（可选）

**返回**: (验证是否通过, 生产状态)

**示例**:
```python
def save_callback(state: ProductionState):
    print(f"保存章节，状态: {state}")

passed, state = adapter.validate_and_save_chapter(
    chapter_number=1,
    draft_text=draft,
    save_callback=save_callback
)
```

#### get_statistics()

获取统计信息。

```python
def get_statistics(self) -> Dict
```

#### print_summary()

打印统计摘要。

```python
def print_summary(self)
```

---

## runtime.publishing

发布流程模块

### ContractValidator

发布验证器模块。

### validate_chapter_contracts_for_release()

发布前的章节契约验证。

```python
def validate_chapter_contracts_for_release(
    project_path: Path,
    chapter_list: List[int]
) -> Dict[str, Any]
```

**参数**:
- `project_path`: 项目路径
- `chapter_list`: 要发布的章节号列表

**返回**: 验证结果字典

**返回格式**:
```python
{
    'passed': bool,              # 总体是否通过
    'blocking_issues': List[str], # 阻塞问题列表
    'statistics': {
        'total_chapters': int,
        'validated_chapters': int,
        'approved_chapters': int,
        'blocked_chapters': int,
        'contract_passed': int,
        'contract_failed': int,
    },
    'chapter_validations': Dict,  # 每章验证结果
    'contract_validation_report': Dict  # 详细验证报告
}
```

**示例**:
```python
from runtime.publishing.contract_validator import validate_chapter_contracts_for_release

result = validate_chapter_contracts_for_release(
    project_path=Path("my-project"),
    chapter_list=[1, 2, 3, 4, 5]
)

if result['passed']:
    print("✓ 所有章节通过验证")
else:
    print(f"✗ 验证失败")
    for issue in result['blocking_issues']:
        print(f"  - {issue}")
```

### get_release_validation_summary()

生成人类可读的验证摘要。

```python
def get_release_validation_summary(
    validation_result: Dict[str, Any]
) -> str
```

**参数**:
- `validation_result`: 验证结果

**返回**: 格式化的摘要文本

**示例**:
```python
from runtime.publishing.contract_validator import (
    validate_chapter_contracts_for_release,
    get_release_validation_summary
)

result = validate_chapter_contracts_for_release(path, [1, 2, 3])
summary = get_release_validation_summary(result)
print(summary)
```

---

## 类型定义

### Character

人物类。

```python
@dataclass
class Character:
    id: str
    name: str
    role: str
    status: str
    first_appearance_chapter: int
```

### Relationship

人物关系类。

```python
@dataclass
class Relationship:
    from_character: str
    to_character: str
    type: RelationshipType
    description: str
```

### Thread

线索类。

```python
@dataclass
class Thread:
    id: str
    description: str
    opened_chapter: int
    status: str
```

---

## 常量

### RELEASE_PACKAGE_VERSION

发布包版本。

```python
RELEASE_PACKAGE_VERSION = "1.2"
```

### ReleaseStatus

发布状态枚举。

```python
class ReleaseStatus(Enum):
    NOT_READY = "not_ready"          # 未准备好
    CHECKS_FAILED = "checks_failed"   # 检查失败
    READY = "ready"                   # 准备就绪
    APPROVED = "approved"             # 已批准
```

---

**文档版本**: 1.0  
**最后更新**: 2026-09-09  
**反馈**: 欢迎提供反馈和改进建议
