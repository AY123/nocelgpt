# Phase 3实施计划 - Runtime集成

**目标**: 将Contract Gate集成到AI-Novel-Runtime  
**预计**: 8小时  
**前置**: Contract Gate已开发并测试完成

---

## 📋 当前状态分析

### Runtime架构理解

**核心入口**: `runtime/serialize/loop.py::run_serial()`

**生成流程**:
```
run_serial()
  ↓
plan_chapters() - 规划章节列表
  ↓
for each chapter:
  ↓
  build task package - 构建任务包
  ↓
  execute chapter - 生成章节
  ↓
  review & finalize - 评审和定稿
  ↓
  write output - 输出结果
```

**关键特性**:
- 使用prompt_version选择模板（v1-v5）
- 状态在章节间传递（fold cursor）
- 从不gate serial（ADR-003）
- 支持approval_queue参数

---

## 🎯 集成方案

### 方案A: 添加v15模板（推荐）

**思路**: 将Contract Gate作为v15 prompt版本

**优点**:
- 非侵入式（遵循现有架构）
- 向后兼容（v1-v5不受影响）
- 选择性使用（通过prompt_version）

**实施步骤**:

#### Step 1: 创建v15 Prompt模板（2小时）

**位置**: `runtime/prompts/v15/`

**文件**:
```
runtime/prompts/v15/
├── __init__.py
├── chapter.py           # 章节prompt生成
└── contract_loader.py   # 契约加载逻辑
```

**chapter.py核心逻辑**:
```python
def render_chapter_prompt_v15(
    chapter: int,
    contracts_dir: Path,
    schemas_dir: Path,
    base_context: dict
) -> str:
    """
    生成v15版本的章节prompt
    
    v15特性: 契约注入
    """
    from runtime_plugins.contract import ContractGate
    
    gate = ContractGate(contracts_dir, schemas_dir)
    
    # 1. Precheck
    gate.precheck(chapter)
    
    # 2. 加载契约
    contract = gate.load_contract(chapter)
    
    # 3. 生成基础prompt（继承v5）
    base_prompt = render_v5_base(base_context)
    
    # 4. 注入契约
    full_prompt = gate.inject_contract(base_prompt, contract)
    
    return full_prompt
```

#### Step 2: 集成到run_serial（2小时）

**修改**: `runtime/serialize/loop.py`

**在run_serial中添加**:
```python
def run_serial(
    *,
    # ... 现有参数
    prompt_version: str = "1.0.0",
    contracts_dir: Optional[Path] = None,  # 新增
    schemas_dir: Optional[Path] = None,    # 新增
    enable_contract_gate: bool = False,    # 新增
    # ...
):
    # ... 现有逻辑
    
    # 在生成每章前
    if enable_contract_gate and prompt_version == "15.0.0":
        from runtime_plugins.contract import ContractGate, ContractCheckError
        
        gate = ContractGate(contracts_dir, schemas_dir)
        
        try:
            gate.precheck(chapter_no)
        except ContractCheckError as e:
            log.error(f"Ch{chapter_no}契约检查失败: {e}")
            # 根据配置决定：跳过或抛出
            if strict_mode:
                raise
            else:
                continue  # 跳过此章
```

#### Step 3: 生成后验证（2小时）

**添加验证钩子**:
```python
def run_serial(...):
    # ... 生成逻辑
    
    # 生成后
    if enable_contract_gate:
        # 验证
        if chapter_no > 1:
            prev_text = load_chapter_text(chapter_no - 1)
            result = gate.validate(chapter_no, prev_text, curr_text)
            
            # 保存验证报告
            save_validation_report(chapter_no, result)
            
            # 如果失败，标记下一章
            if not result['valid']:
                log.warning(f"Ch{chapter_no}验证失败")
                # 可选：阻止下一章
```

#### Step 4: CLI集成（1小时）

**修改**: `runtime/cli.py`

**添加命令参数**:
```bash
python runtime/cli.py serial \
    --project-path . \
    --prompt-version 15.0.0 \
    --enable-contract-gate \
    --contracts-dir contracts \
    --schemas-dir schemas
```

#### Step 5: 测试验证（1小时）

**测试用例**:
1. 无契约章节被阻止
2. 未批准契约被阻止
3. 有效契约正常生成
4. 验证失败记录日志

---

### 方案B: 独立Contract Gate服务（备选）

**思路**: Contract Gate作为外部服务，Runtime通过API调用

**优点**:
- 完全独立
- 可以服务多个Runtime实例

**缺点**:
- 增加复杂度
- 需要维护服务

**不推荐理由**: 过度设计，当前规模不需要

---

## 📊 集成后的完整流程

### 使用Contract Gate的生成流程

```
用户调用：serial --prompt-version 15.0.0 --enable-contract-gate

run_serial() 开始
  ↓
plan_chapters() - 规划Ch101-110
  ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
开始生成Ch101
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ↓
[1. Contract Precheck] ✅ 新增
  - 检查contracts/chapter_101_contract.json存在
  - 验证Schema合规
  - 检查approved=true
  - 失败则跳过/抛出
  ↓
[2. Load Contract] ✅ 新增
  - 加载契约内容
  ↓
[3. Build Task Package]
  - 使用v15 prompt
  - inject_contract()注入契约 ✅ 新增
  ↓
[4. Execute Chapter]
  - 使用LLM生成正文
  ↓
[5. Review & Finalize]
  - 现有的评审流程
  ↓
[6. Contract Validate] ✅ 新增
  - 验证契约遵守
  - 保存validation报告
  - 失败则记录警告
  ↓
[7. Write Output]
  - 输出到registry/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

继续Ch102...
```

---

## 🎯 验收标准

### 集成完成的标志

| 标准 | 验证方式 |
|------|----------|
| v15 prompt可用 | `--prompt-version 15.0.0`生成成功 |
| Precheck阻止 | 无契约时停止生成 |
| 契约注入 | 生成的prompt包含契约 |
| 验证报告 | 生成后有validation报告 |
| CLI参数 | `--enable-contract-gate`有效 |

---

## 📝 实施检查清单

### Phase 3 Task List

- [ ] Task 3.1: 创建v15 prompt模板（2h）
  - [ ] 创建目录结构
  - [ ] 实现chapter.py
  - [ ] 实现contract_loader.py
  - [ ] 单元测试

- [ ] Task 3.2: 修改run_serial（2h）
  - [ ] 添加参数
  - [ ] 集成precheck
  - [ ] 处理ContractCheckError
  - [ ] 测试

- [ ] Task 3.3: 生成后验证（2h）
  - [ ] 添加验证钩子
  - [ ] 保存报告
  - [ ] 失败处理
  - [ ] 测试

- [ ] Task 3.4: CLI集成（1h）
  - [ ] 添加参数
  - [ ] 文档
  - [ ] 测试

- [ ] Task 3.5: 集成测试（1h）
  - [ ] 端到端测试
  - [ ] 边界测试
  - [ ] 文档

---

## 🚀 下次启动

### 继续Phase 3实施

```bash
cd /Users/angyang/Documents/xiaoshuo/AINovel

# 查看计划
cat PHASE3_IMPLEMENTATION_PLAN.md

# 开始Task 3.1
mkdir -p AI-Novel-Runtime/runtime/prompts/v15

# 创建v15 prompt模板
# ...
```

---

## 💡 关键设计决策

### 1. 为什么选择v15而不是修改v5？

**原因**:
- 向后兼容（v1-v5不受影响）
- 清晰分离（契约是新功能）
- 可选使用（用户选择）
- 遵循现有架构（prompt版本演进）

### 2. 为什么Precheck不gate serial？

**原因**:
- 遵循ADR-003（never gate serial）
- 只记录问题，继续运行
- 或在strict_mode下才gate

### 3. 为什么验证不阻止？

**原因**:
- 生成后验证主要用于报告
- 阻止应该在precheck阶段
- 保持serial的连续性

---

**Phase 3计划完成！准备下次实施。** ✅

**预计时间**: 8小时  
**当前状态**: 规划完成，待实施
