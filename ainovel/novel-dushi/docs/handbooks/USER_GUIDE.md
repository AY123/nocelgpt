# AI-Novel 契约系统使用指南

**版本**: 1.0  
**日期**: 2026-09-09  
**适用于**: AI-Novel Runtime v2.0+

---

## 📖 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [完整流程](#完整流程)
4. [最佳实践](#最佳实践)
5. [常见问题](#常见问题)
6. [故障排除](#故障排除)

---

## 🚀 快速开始

### 5分钟上手

**前置条件**:
- Python 3.9+
- AI-Novel Runtime 已安装

**第一步：创建 Story Bible**

```bash
# 使用现有的 Story Bible
cp registry/story-bible/BIBLE-00001.yaml my-story-bible.yaml

# 或创建新的
nano my-story-bible.yaml
```

**第二步：验证 Story Bible**

```bash
python3 -m runtime.tools.validate_story_bible my-story-bible.yaml
```

**第三步：生成章节**

```python
from pathlib import Path
from runtime.serialize.serial_hook_adapter import create_adapter

# 创建适配器
adapter = create_adapter(
    project_path=Path("my-project"),
    enable_contract_integration=True
)

# 生成第1章
can_proceed, errors = adapter.can_generate_chapter(1)
if can_proceed:
    draft = generate_chapter(1)
    passed, state = adapter.validate_and_save_chapter(1, draft)
    print(f"章节状态: {state}")
```

**完成！** 你已经成功使用了契约系统。

---

## 💡 核心概念

### 1. Story Bible - 单一真相源

**什么是 Story Bible？**

Story Bible 是整个故事的权威定义，包含：
- 主角信息
- 世界设定
- 30章事件规划

**为什么需要它？**
- ✅ 避免不一致
- ✅ 自动生成契约
- ✅ 自动验证章节

**示例**:
```yaml
version: "1.2"
status: human_approved
locked_at: "2026-09-09"

protagonist:
  name: 陈默
  age: 25
  background: 金融分析师，重生者

chapter_events:
  - chapter: 1
    date: "2013-01-15"
    title: 身份落差暴露
    objective: 避免重蹈前世覆辙
    antagonist: 赵鹏程
    irreversible_change: 改变历史轨迹
    next_hook: 明天见周子铭
```

### 2. ChapterContract - 章节契约

**什么是章节契约？**

每章的输入/输出约束，定义章节必须满足的条件。

**约束类型**:
- **硬约束** (必须满足)：主角名字、日期
- **软约束** (建议满足)：地点、人物

**自动生成**:
```python
from runtime.contract import load_story_bible_contracts

# 从 Story Bible 生成30个契约
contracts = load_story_bible_contracts("story-bible.yaml")
# [Contract(chapter=1, ...), Contract(chapter=2, ...), ...]
```

**验证**:
```python
contract = contracts[0]  # 第1章契约
result = contract.validate(draft_text, extracted_data)

if result.passed:
    print("✓ 契约验证通过")
else:
    print(f"✗ 错误: {result.errors}")
```

### 3. StoryState - 故事状态

**什么是故事状态？**

跨章节传递的世界状态，包含：
- 当前时间和地点
- 主角状态
- 人物关系
- 未完成线索

**状态传递**:
```python
# 第0章（初始）
state0 = StoryState.create_initial_state(story_bible)

# 第1章
state1 = StoryState.extract_from_draft(
    draft_text=chapter1_draft,
    chapter_number=1,
    previous_state=state0
)

# 第2章
state2 = StoryState.extract_from_draft(
    draft_text=chapter2_draft,
    chapter_number=2,
    previous_state=state1
)
```

**连续性验证**:
```python
# 验证第2章与第1章的连续性
errors = state2.validate_continuity(state1)

if errors:
    print("连续性错误:")
    for err in errors:
        print(f"  - {err}")
```

### 4. ProductionState - 生产状态

**什么是生产状态？**

统一的章节状态枚举，决定章节是否可以发布。

**6种状态**:
```python
from runtime.contract import ProductionState

ProductionState.GENERATED          # 📝 已生成，待审核
ProductionState.NEEDS_REVISION     # ✏️ 需要修改
ProductionState.BLOCKED            # 🚫 被阻塞
ProductionState.HUMAN_APPROVED     # ✅ 人工审核通过
ProductionState.PUBLISHED          # 🎉 已发布
ProductionState.INVALIDATED        # ❌ 已作废
```

**状态判断**:
```python
state = ProductionState(chapter_data['production_state'])

# 是否可以导出（发布）
if state.can_export():
    export_chapter()

# 是否可以继续下一章
if state.can_proceed_next():
    generate_next_chapter()
```

**状态转换**:
```python
# 合法转换
GENERATED → HUMAN_APPROVED → PUBLISHED

# 非法转换（会被阻止）
GENERATED → PUBLISHED  # ✗ 必须先 HUMAN_APPROVED
```

---

## 📋 完整流程

### 端到端：从 Story Bible 到发布

#### 第1步：创建 Story Bible

```yaml
# my-story.yaml
version: "1.0"
status: draft

protagonist:
  name: 张三
  age: 30

chapter_events:
  - chapter: 1
    date: "2024-01-01"
    title: 第一章标题
    objective: 主角目标
```

#### 第2步：验证 Story Bible

```bash
python3 -m runtime.tools.validate_story_bible my-story.yaml
```

输出:
```
✓ 章节数量正确：1章
✓ 章节编号连续：1-1
✓ 时间线连续
✓ 主角名字一致：张三
✓ 所有检查通过
```

#### 第3步：生成章节（使用 Serial）

```python
from pathlib import Path
from runtime.serialize.production_hook import create_production_hook

# 创建钩子
hook = create_production_hook(
    project_path=Path("my-project"),
    enable_contract_integration=True
)

# 生成第1章
ctx = ChapterProductionContext(
    chapter_number=1,
    project_path=Path("my-project")
)

# 验证入口条件
can_proceed, errors = hook.before_generate(ctx)
if not can_proceed:
    print(f"无法生成: {errors}")
    exit(1)

# 生成章节（调用 LLM）
draft = llm_generate_chapter(1)
ctx.draft_text = draft

# 验证契约
passed, result = hook.after_generate(ctx)
if not passed:
    print(f"验证失败: {result}")

# 设置状态
state = hook.before_save(ctx, passed)
print(f"章节状态: {state}")

# 保存
save_chapter(1, draft, state)
```

#### 第4步：人工审核

```python
from runtime.contract import ProductionState

# 审核通过
chapter_data['production_state'] = ProductionState.HUMAN_APPROVED.value
save_chapter(1, chapter_data)
```

#### 第5步：发布（使用 Mint）

```python
from runtime.publishing.release_package import build_release_package

# 构建发布包
package = build_release_package(
    project_path="my-project",
    project_id="my-story"
)

# 检查契约验证
if package.contract_status == "passed":
    print("✓ 所有章节通过验证")
    if package.can_release:
        release(package)
else:
    print(f"✗ 验证失败: {package.blocking_issues}")
```

---

## ⭐ 最佳实践

### 1. 如何写好 Story Bible

**原则**:
- **一致性** - 主角名字、日期格式保持一致
- **连续性** - 时间线连续，事件逻辑连贯
- **完整性** - 所有必填字段都填写

**示例**:

✅ **好的 Story Bible**:
```yaml
chapter_events:
  - chapter: 1
    date: "2013-01-15"  # 统一格式
    title: 明确的标题
    objective: 清晰的目标
    antagonist: 具体的对手
    irreversible_change: 明确的改变
    next_hook: 引向下一章的钩子
```

❌ **不好的 Story Bible**:
```yaml
chapter_events:
  - chapter: 1
    date: "2013/1/15"  # 格式不一致
    title: 标题  # 太笼统
    objective: 做事情  # 不明确
```

### 2. 如何定义契约

**原则**:
- **明确** - 约束条件清晰明确
- **可验证** - 可以自动检查
- **合理** - 不过度约束

**硬约束** (必须满足):
- 主角名字
- 日期
- 章节号

**软约束** (建议满足):
- 地点
- 人物出现
- 线索提及

### 3. 如何处理验证失败

**步骤**:

1. **查看错误信息**
```python
result = contract.validate(draft_text)
if not result.passed:
    for error in result.errors:
        print(f"错误: {error}")
    for warning in result.warnings:
        print(f"警告: {warning}")
```

2. **修正草稿**
   - 错误（errors）必须修正
   - 警告（warnings）建议修正

3. **重新验证**
```python
result = contract.validate(fixed_draft_text)
```

4. **设置状态**
```python
if result.passed:
    state = ProductionState.HUMAN_APPROVED
else:
    state = ProductionState.NEEDS_REVISION
```

### 4. 如何管理状态

**状态流转图**:
```
GENERATED ──────────┐
    │               │
    │ 验证通过      │ 验证失败
    ↓               ↓
HUMAN_APPROVED   BLOCKED
    │
    │ 发布
    ↓
PUBLISHED
```

**最佳实践**:
- ✅ 使用 `can_export()` 而不是直接判断状态值
- ✅ 使用 `validate_state_transition()` 验证转换
- ✅ 记录状态变更日志
- ❌ 不要跳过状态（如 GENERATED 直接到 PUBLISHED）

---

## ❓ 常见问题

### Q1: Story Bible 可以修改吗？

**A**: 可以，但建议：
- 锁定前（`status: draft`）可以随意修改
- 锁定后（`status: human_approved`）需要更新版本号
- 已生成章节的契约不受影响（使用当时的版本）

### Q2: 契约验证失败章节还能继续吗？

**A**: 不能。验证失败的章节会被设置为 BLOCKED 状态，无法继续下一章。必须：
1. 修正当前章节
2. 重新验证通过
3. 设置为 HUMAN_APPROVED
4. 才能继续下一章

### Q3: 如何跳过某章？

**A**: 不建议跳过，但如果必须：
```python
# 使用 force 模式
adapter.can_generate_chapter(2, force=True)
```

⚠️ 警告：跳过会破坏连续性

### Q4: 旧章节没有 production_state 怎么办？

**A**: 系统会自动兼容：
```python
# 读取时提供默认值
state = ProductionState(
    chapter_data.get('production_state', 'generated')
)
```

### Q5: 性能会受影响吗？

**A**: 影响很小：
- 契约加载: ~100ms（一次性）
- 单章验证: ~10ms
- 相对于 LLM 生成（几秒），几乎可忽略

### Q6: 如何禁用契约验证？

**A**: 
```python
# Serial 中
adapter = create_adapter(
    project_path=path,
    enable_contract_integration=False  # 禁用
)

# Mint 中
# 契约验证错误不会阻止发布（只添加 blocking_issues）
```

---

## 🔧 故障排除

### 问题1: 契约加载失败

**症状**: `RuntimeError: Failed to load contracts`

**原因**: Story Bible 文件不存在或格式错误

**解决**:
```bash
# 验证 Story Bible
python3 -m runtime.tools.validate_story_bible story-bible.yaml

# 检查路径
ls registry/story-bible/BIBLE-00001.yaml
```

### 问题2: 契约验证总是失败

**症状**: 所有章节都验证失败

**原因**: 提取的数据不正确

**解决**:
```python
# 手动提供提取数据
extracted_data = {
    'protagonist_name': '陈默',
    'date': '2013-01-15',
    'locations': ['恒远投资公司'],
    'characters': ['陈默', '周子铭']
}

result = contract.validate(draft_text, extracted_data)
```

### 问题3: 状态转换被拒绝

**症状**: `ValueError: 非法状态转换`

**原因**: 违反状态转换规则

**解决**:
```python
# 检查当前状态
current = ProductionState(chapter_data['production_state'])

# 检查可能的下一个状态
next_states = current.next_states()
print(f"可能的状态: {[s.display_name() for s in next_states]}")

# 使用合法的转换
if new_state in next_states:
    chapter_data['production_state'] = new_state.value
```

### 问题4: 测试全部失败

**症状**: 运行测试时全部失败

**原因**: 依赖未安装或路径错误

**解决**:
```bash
# 安装依赖
pip install -r requirements.txt

# 从正确的目录运行
cd AI-Novel-Runtime
python3 -m pytest tests/ -v
```

---

## 📚 参考资料

### 核心文档
- [API 参考](API_REFERENCE.md) - 完整的 API 文档
- [迁移指南](ProductionState-迁移指南.md) - 从旧系统迁移
- [架构文档](AI-Novel渐进式重构方案(C目标).md) - 系统架构

### 代码示例
- `demo_production_hook.py` - 钩子使用示例
- `demo_serial_integration.py` - Serial 集成示例
- `test_*.py` - 测试代码作为示例

### 相关项目
- [AI-Novel-Runtime](../AI-Novel-Runtime/) - 运行时系统
- [AI-Novel-Standard](../AI-Novel-Standard/) - 标准和 Schema

---

## 🆘 获取帮助

### 社区支持
- GitHub Issues: 报告 bug 和功能请求
- 文档: 查看完整文档
- 示例: 参考示例代码

### 常用命令
```bash
# 运行所有测试
python3 -m pytest tests/ -v

# 验证 Story Bible
python3 -m runtime.tools.validate_story_bible <file>

# 生成契约
python3 -m runtime.tools.generate_contracts <story-bible>

# 查看帮助
python3 -m runtime --help
```

---

**文档版本**: 1.0  
**最后更新**: 2026-09-09  
**反馈**: 欢迎提供反馈和改进建议
