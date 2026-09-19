# Task 4.1 完成：Mint 流程分析

**日期**: 2026-09-09  
**任务**: 了解现有 Mint 流程  
**状态**: ✅ 完成

---

## 📋 现有 Mint 系统分析

### 核心文件

1. **`runtime/publishing/release_package.py`** - 主要发布包构建器
   - `build_release_package()` - 构建发布包
   - `ReleasePackage` dataclass - 发布包数据结构
   - `ReleaseStatus` enum - 发布状态（NOT_READY, CHECKS_FAILED, READY, APPROVED）

2. **`runtime/idmint/mint.py`** - ID Mint 系统

3. **`runtime/approval/publish.py`** - 发布审批

4. **`runtime/publishing/publish_queue.py`** - 发布队列

---

## 🔍 现有发布流程

```
1. build_release_package()
   ├─ 加载 outline
   ├─ 加载 first_30_chapters
   ├─ 【检查点】Redline check
   ├─ 【检查点】Originality check  
   ├─ 【检查点】Publish readiness
   ├─ 确定 status (NOT_READY/CHECKS_FAILED/READY)
   └─ 生成 ReleasePackage

2. 人工审批
   └─ status → APPROVED

3. 发布
   └─ 只有 APPROVED 可以发布
```

---

## 🎯 现有质量检查

### 1. Redline Check (敏感词检查)
```python
if not redline:
    blocking_issues.append("Redline check not executed")
elif not redline.get("passed", False):
    blocking_issues.append(f"Redline failed: {len(redline.get('hits', []))} hits")
```

### 2. Originality Check (原创性检查)
```python
if not orig:
    blocking_issues.append("Originality check not executed")
elif orig.get("risk_level") in ["L2", "L3"]:
    blocking_issues.append(f"Originality risk: {orig['risk_level']}")
```

### 3. Publish Readiness (发布准备度)
```python
if not pub:
    blocking_issues.append("Publish readiness not assessed")
elif pub.get("recommendation") == "block":
    blocking_issues.append("Publish readiness: blocked")
```

---

## 🔌 集成点识别

### 集成点1: 章节状态检查（新增）
**位置**: `build_release_package()` 开始处  
**功能**: 检查所有章节的 ProductionState  
**优先级**: 高

```python
# 在 build_release_package() 开始处添加
chapter_states_check = validate_chapter_states(project_path, first_30)
if not chapter_states_check['passed']:
    blocking_issues.append("Chapter states validation failed")
```

### 集成点2: 契约验证（新增）
**位置**: `build_release_package()` 中，与其他检查并列  
**功能**: 验证所有章节满足契约  
**优先级**: 高

```python
contract_check = validate_chapter_contracts(project_path, first_30)
if not contract_check['passed']:
    blocking_issues.append(f"Contract validation failed: {contract_check['errors']}")
```

### 集成点3: 连续性检查（新增）
**位置**: `build_release_package()` 中  
**功能**: 验证章节间连续性  
**优先级**: 中

```python
continuity_check = validate_story_continuity(project_path, first_30)
if not continuity_check['passed']:
    blocking_issues.append(f"Story continuity broken: {continuity_check['errors']}")
```

### 集成点4: 状态更新（新增）
**位置**: 发布成功后  
**功能**: 更新章节状态为 PUBLISHED  
**优先级**: 中

```python
# 发布成功后
for chapter_num in first_30:
    update_chapter_state(chapter_num, ProductionState.PUBLISHED)
```

### 集成点5: 验证报告（新增）
**位置**: 与其他报告并列  
**功能**: 生成契约验证详细报告  
**优先级**: 低

```python
contract_validation_report = generate_contract_report(project_path, first_30)
# 添加到 ReleasePackage
```

---

## 📐 现有架构特点

### 优点
1. **Fail-closed 设计** - 默认阻止发布，明确通过才放行
2. **模块化检查** - 每个检查独立，易于扩展
3. **详细的阻塞信息** - `blocking_issues` 列表
4. **人工审批** - 最终决策权在人

### 缺点
1. **章节级别检查缺失** - 只检查整体，不检查每章
2. **状态管理分散** - 没有统一的 ProductionState
3. **契约概念缺失** - 没有章节契约验证

---

## 💡 集成策略

### 策略1: 最小侵入（推荐）

**方式**: 创建新的检查函数，作为现有检查的补充

```python
def build_release_package(...):
    # ... 现有代码 ...
    
    # 【新增】章节契约验证
    contract_check = validate_chapter_contracts_for_release(
        project_path=project,
        chapter_list=first_30
    )
    if not contract_check['passed']:
        blocking_issues.extend(contract_check['blocking_issues'])
        contract_status = "failed"
    else:
        contract_status = "passed"
    
    # 添加到状态判断
    if blocking_issues:
        if any("not executed" in issue for issue in blocking_issues):
            status = ReleaseStatus.NOT_READY.value
        else:
            status = ReleaseStatus.CHECKS_FAILED.value
    else:
        status = ReleaseStatus.READY.value
    
    # ... 现有代码 ...
```

**优点**:
- ✅ 不破坏现有逻辑
- ✅ 与现有检查风格一致
- ✅ 易于测试
- ✅ 向后兼容

### 策略2: 独立验证器

**方式**: 创建独立的 `ReleaseValidator` 类

```python
class ReleaseValidator:
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.integration = create_integration(project_path, True)
    
    def validate_for_release(self, chapter_list: list) -> dict:
        results = {
            'passed': True,
            'blocking_issues': [],
            'chapter_states': {},
            'contract_validation': {},
            'continuity_check': {}
        }
        
        # 检查章节状态
        # 检查契约
        # 检查连续性
        
        return results

# 在 build_release_package 中使用
validator = ReleaseValidator(project)
validation = validator.validate_for_release(first_30)
if not validation['passed']:
    blocking_issues.extend(validation['blocking_issues'])
```

**优点**:
- ✅ 封装良好
- ✅ 易于单元测试
- ✅ 可重用

---

## 🎯 推荐方案

**采用策略1（最小侵入）**

**原因**:
1. 与现有代码风格一致
2. 改动最小，风险最低
3. 易于理解和维护
4. 保持向后兼容

**实现步骤**:
1. 创建 `runtime/publishing/contract_validator.py`
2. 实现 `validate_chapter_contracts_for_release()`
3. 在 `build_release_package()` 中调用
4. 添加单元测试
5. 更新 `ReleasePackage` 添加契约验证报告

---

## 📊 数据流图

```
Story Bible
    ↓
30 ChapterContracts
    ↓
Generated Chapters
    ├─ chapter-final-TASK-00001.json (production_state)
    ├─ chapter-final-TASK-00002.json
    └─ ...
    ↓
build_release_package()
    ├─ 【现有】Redline check
    ├─ 【现有】Originality check
    ├─ 【现有】Publish readiness
    ├─ 【新增】Chapter states check ← ProductionState
    ├─ 【新增】Contract validation ← ChapterContract
    └─ 【新增】Continuity check ← StoryState
    ↓
ReleasePackage
    ├─ status: NOT_READY/CHECKS_FAILED/READY
    ├─ blocking_issues: [...]
    └─ contract_validation_report: {...}
    ↓
Human Approval
    ↓
status → APPROVED
    ↓
Release & Publish
    ↓
Update chapter states → PUBLISHED
```

---

## 🚀 下一步

### Task 4.2: 实现发布验证器

创建 `runtime/publishing/contract_validator.py`:

```python
def validate_chapter_contracts_for_release(
    project_path: Path,
    chapter_list: list
) -> dict:
    """
    发布前的章节契约验证
    
    检查：
    1. 所有章节状态为 HUMAN_APPROVED 或 PUBLISHED
    2. 所有章节通过契约验证
    3. 章节间连续性正确
    
    Returns:
        {
            'passed': bool,
            'blocking_issues': list[str],
            'chapter_validations': dict,
            'statistics': dict
        }
    """
```

---

**完成日期**: 2026-09-09  
**下一任务**: Task 4.2 - 实现发布验证器
