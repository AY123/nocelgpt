# Task 2: Candidate 失败触发修订 - 实施方案

**状态**: 设计完成，待实施  
**优先级**: P0-5  
**预计工作量**: 4-6 小时

---

## 📋 需求分析

根据用户检查报告 P0-5：

> 当前 Contract Validation 位于最终定稿后，即使契约严重失败，章节仍会标记为成功。
> 
> 建议拆成两级：
> 1. **Candidate Contract Check** - 最终定稿前，触发修订
> 2. **Final Contract Audit** - 最终持久化后，审计

---

## 🎯 设计目标

1. **不违反 ADR-003**: 永不杀死整个 serial
2. **有限修订**: 最多 N 次（如 2 次）
3. **降级策略**: 修订失败后仍继续
4. **清晰追踪**: 记录修订历史

---

## 🏗️ 架构设计

### 当前流程

```
Generation (draft)
    ↓
Commercial Loop (optional)
    ↓
Hygiene Rewrite (optional)
    ↓
Final Contract Validation (advisory) ← 当前位置
    ↓
W12 Extract (optional)
    ↓
Done (标记 ok=True)
```

### 新流程

```
Generation (draft) ← Candidate 0
    ↓
【Candidate Contract Check】← 新增
    ├─ Pass → Continue
    └─ Fail → Revision (max 2 rounds)
          ↓
        Regenerate ← Candidate 1
          ↓
        【Candidate Contract Check】
          ├─ Pass → Continue
          └─ Fail → Revision (1 more round)
                ↓
              Regenerate ← Candidate 2
                ↓
              【Candidate Contract Check】
                ├─ Pass → Continue
                └─ Fail → Log + Continue (降级)
                      ↓
Commercial Loop (optional)
    ↓
Hygiene Rewrite (optional)
    ↓
【Final Contract Audit】← 保留，改为只审计
    ↓
W12 Extract (optional)
    ↓
Done
```

---

## 🔧 实施细节

### 1. 新增参数

`run_serial()` 新增：

```python
def run_serial(
    ...
    enable_contract_gate: bool = False,
    contract_revision_enabled: bool = True,  # 新增
    max_contract_revisions: int = 2,         # 新增
    ...
):
```

### 2. ContractGate 新增方法

```python
def check_candidate(
    self,
    chapter: int,
    candidate_text: str,
    prev_text: str = ""
) -> dict:
    """
    Candidate 阶段契约检查
    
    Returns:
        {
            "pass": bool,
            "issues": [
                {
                    "category": "critical" | "major" | "minor",
                    "field": str,
                    "description": str
                }
            ],
            "requires_revision": bool,  # True if has critical issues
            "revision_suggestions": [str]
        }
    """
```

### 3. loop.py 集成点

**位置**: `loop.py:1162` (execute_package 之后)

```python
# After execute_package
if not ex.ok:
    ...
    continue

chapter_draft = ex.artifact

# --- Candidate Contract Check (Phase 3 Stage 2, Task 2) ---------
if enable_contract_gate and contract_revision_enabled and prompt_version == "15.0.0":
    revision_count = 0
    max_revisions = max_contract_revisions
    
    while revision_count <= max_revisions:
        # Check candidate against contract
        check_result = gate.check_candidate(
            chapter=spec.index,
            candidate_text=chapter_draft.get("body", ""),
            prev_text=bodies_by_chapter.get(spec.index - 1, "")
        )
        
        if check_result["pass"]:
            # Contract satisfied, continue
            break
        
        if not check_result["requires_revision"]:
            # Only minor issues, acceptable
            break
        
        if revision_count >= max_revisions:
            # Max revisions reached, log and continue (degrade gracefully)
            import logging
            logging.warning(
                f"Ch{spec.index} contract check failed after {revision_count} "
                f"revisions, continuing with degraded quality"
            )
            break
        
        # Trigger revision
        revision_count += 1
        logging.info(
            f"Ch{spec.index} contract check failed, triggering revision "
            f"{revision_count}/{max_revisions}"
        )
        
        # Regenerate with revision guidance
        revised_extra_vars = extra_vars.copy()
        revised_extra_vars["revision_guidance"] = {
            "revision_round": revision_count,
            "issues": check_result["issues"],
            "suggestions": check_result["revision_suggestions"]
        }
        
        # Re-execute with guidance
        revised_ex = execute_package(
            build.package,
            prompt_runtime,
            prompt_version=prompt_version,
            extra_vars=revised_extra_vars,
            ...
        )
        
        if revised_ex.ok:
            chapter_draft = revised_ex.artifact
        else:
            # Revision failed, keep original and break
            logging.warning(
                f"Ch{spec.index} revision {revision_count} failed, "
                f"keeping original draft"
            )
            break
    
    # Record revision history in ChapterRun
    if revision_count > 0:
        chapter_run_metadata["contract_revisions"] = revision_count

# Continue with commercial loop, hygiene, etc.
```

### 4. ChapterRun 扩展

```python
@dataclass
class ChapterRun:
    ...
    contract_validation: Optional[dict] = None
    contract_revisions: int = 0  # 新增：记录修订次数
```

### 5. CLI 参数

```bash
--enable-contract-revision    # 启用 Candidate 修订
--max-contract-revisions N    # 最多修订次数（默认 2）
```

---

## ⚠️ 注意事项

### 1. 与现有流程的关系

- **Commercial Loop**: Candidate Check 在 Commercial 之前
  - 确保契约遵守优先于商业优化
  - Commercial 可能会破坏契约遵守

- **Hygiene**: Candidate Check 在 Hygiene 之前
  - Hygiene 只是语言润色，不影响结构

- **Final Audit**: 保留在最后
  - 作为最终审计，不再触发修订
  - 记录最终版本与契约的偏差

### 2. 成本控制

每次修订 = 1 次完整的 chapter 生成调用

最多成本: `(1 + max_revisions) * base_cost`

建议：
- `max_revisions=2` (最多 3 次尝试)
- 与 `per_chapter_budget` 配合使用
- 超预算时跳过修订

### 3. 降级策略

修订全部失败后：
- ✅ 继续运行（不杀死 serial）
- ✅ 标记 `contract_revisions=N`
- ✅ Final Audit 会记录偏差
- ✅ 用户可事后人工修正

### 4. 幂等性

- Candidate Check 应该是确定性的
- 相同文本 → 相同结果
- 避免随机性导致的无限循环

---

## 🧪 测试计划

### 单元测试

1. `test_check_candidate_pass` - 契约满足
2. `test_check_candidate_fail_critical` - 严重失败
3. `test_check_candidate_fail_minor` - 轻微问题

### 集成测试

1. `test_candidate_revision_success` - 修订后通过
2. `test_candidate_revision_exhausted` - 修订耗尽，降级
3. `test_candidate_revision_disabled` - 修订禁用
4. `test_candidate_revision_cost_limit` - 预算限制

---

## 📊 预期效果

### Before (当前)

```
Generation → Final Audit (advisory)
   ↓              ↓
  ok=True      记录偏差 (但不处理)
```

**问题**: 契约失败的章节仍标记为成功

### After (修订后)

```
Generation → Candidate Check
   ↓              ↓
  Fail         Revision (max 2)
   ↓              ↓
Revised → Candidate Check
   ↓              ↓
  Pass         Continue
   ↓              ↓
Final Audit (只记录)
```

**改进**: 
- 大部分契约问题在 Candidate 阶段修正
- Final 版本契约遵守率显著提高
- 仍然不杀死 serial (ADR-003)

---

## 🚀 实施步骤

1. **ContractGate.check_candidate()** (1h)
   - 实现 Candidate 检查逻辑
   - 返回结构化结果
   - 单元测试

2. **loop.py 集成** (2h)
   - 在 execute_package 后插入检查
   - 实现修订循环
   - 记录修订历史

3. **CLI 参数** (0.5h)
   - 添加 `--enable-contract-revision`
   - 添加 `--max-contract-revisions`

4. **集成测试** (1.5h)
   - 测试修订成功
   - 测试修订耗尽
   - 测试禁用情况

5. **文档更新** (0.5h)
   - 更新使用说明
   - 更新架构文档

**总计**: ~5.5 小时

---

## 💡 替代方案

### 方案 A: 简化版（当前推荐）

只检查 Critical 问题，触发修订：
- 地点不匹配
- 钩子未消费
- 必需人物缺失

### 方案 B: 完整版

检查所有契约字段，分级处理：
- Critical → 必须修订
- Major → 建议修订
- Minor → 记录但不修订

### 方案 C: LLM 引导修订

不是完全重新生成，而是：
1. 识别具体问题
2. 生成修订指导
3. 局部修改（而非重新生成）

**推荐**: 方案 A (简化版)
- 成本可控
- 实施简单
- 覆盖核心问题

---

## 📝 后续工作

完成 Task 2 后，还需要：

1. **Task 3**: 验证 Final hash 对应
2. **Task 4**: Schema 严格化
3. **Stage 3**: Validator 去硬编码
4. **Stage 3**: 真实章节金样评估

---

**文档创建时间**: 2026-08-15  
**状态**: 设计完成，待实施  
**预计完成后完成度**: ~85%
