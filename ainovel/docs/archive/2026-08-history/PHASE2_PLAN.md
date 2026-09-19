# Phase 2实施计划 - Runtime集成与完整闭环

**目标**: 将契约系统集成到生产链，建立完整闭环  
**预计**: 6-8小时  
**状态**: 规划中

---

## 🎯 Phase 2最小可行方案

### 核心目标
将Phase 1验证成功的原型集成到实际生产链，实现：
1. 写前契约加载
2. 生成后验证
3. 不通过则阻止

### 不包含（留给Phase 3）
- 自动改写
- 活动窗口管理
- ApprovalQueue
- 20章视野

---

## 📋 任务拆解

### Task 1: Prompt v15注册（1小时）

**目标**: 让Runtime能识别和使用v15

**步骤**:
1. 将prompt v15转为标准格式
2. 注册到PromptLoader
3. 添加版本选择逻辑

**产物**:
- AI-Novel-Runtime/prompts/v15/chapter.yaml
- PromptLoader支持v15

### Task 2: Serial precheck集成（2小时）

**目标**: 生成前检查契约是否存在且已批准

**步骤**:
1. 修改serial run入口
2. 添加contract_precheck()
3. 不通过则停止生成

**检查项**:
```python
def contract_precheck(chapter: int):
    # 1. 契约文件存在
    # 2. Schema合规
    # 3. approved=true
    # 4. 来源未过期（可选）
```

**产物**:
- AI-Novel-Runtime/runtime/contract_precheck.py
- Serial run集成点

### Task 3: 生成后验证（2小时）

**目标**: 生成完成后自动验证契约

**步骤**:
1. 在chapter finalizer中添加验证
2. 调用validate_contract
3. 生成transition_assessment报告

**验证流程**:
```
生成Ch101 → 提取actual_exit
          → 生成Ch102 → 提取actual_entry
                      → 对比contract
                      → 生成报告
```

**产物**:
- transition_assessment报告
- 验证失败时的警告

### Task 4: 阻断机制（1小时）

**目标**: 验证失败时阻止下一章

**步骤**:
1. 验证失败时设置标志
2. Precheck检查标志
3. 人工审核后才能继续

**流程**:
```
Ch101验证失败 → 标记blocked
             → Ch102 precheck检测到blocked
             → 停止生成
             → 等待人工审核
```

**产物**:
- blocked状态管理
- 人工审核接口

---

## 🔧 技术实施细节

### 1. Prompt v15格式

```yaml
# AI-Novel-Runtime/prompts/v15/chapter.yaml
version: "v15"
description: "Chapter prompt with contract integration"

template: |
  你正在创作第{{chapter}}章。
  
  📍 章节契约（必须严格遵守）
  
  【入口要求】
  • 地点：{{contract.entry_state.location_id}}
  • 时间：{{contract.entry_state.time_relation}}
  • 视角：{{contract.entry_state.pov}}
  • 上章钩子：{{contract.entry_state.must_address}}
  
  【本章目标】
  {{contract.chapter_intent.objective}}
  
  【出口要求】
  • 地点：{{contract.exit_target.location_id}}
  • 钩子：{{contract.exit_target.hook_promise}}
  
  现在开始创作。

required_context:
  - contract
  - objective (optional)
  - ir (optional)
```

### 2. Contract Precheck

```python
# AI-Novel-Runtime/runtime/contract_precheck.py

from pathlib import Path
import json
import jsonschema

def contract_precheck(chapter: int, contracts_dir: Path) -> dict:
    """
    契约前置检查
    
    Returns:
        {
            "passed": bool,
            "errors": []
        }
    """
    errors = []
    
    # 1. 契约文件存在
    contract_file = contracts_dir / f"chapter_{chapter:03d}_contract.json"
    if not contract_file.exists():
        errors.append(f"契约文件不存在: {contract_file}")
        return {"passed": False, "errors": errors}
    
    # 2. 加载契约
    with open(contract_file, 'r') as f:
        contract = json.load(f)
    
    # 3. Schema验证
    schema = load_schema()
    try:
        jsonschema.validate(contract, schema)
    except jsonschema.ValidationError as e:
        errors.append(f"Schema验证失败: {e.message}")
    
    # 4. 批准检查
    if not contract.get("approved"):
        errors.append("契约未批准")
    
    # 5. 来源过期检查（可选）
    # TODO: 检查content_hash
    
    return {
        "passed": len(errors) == 0,
        "errors": errors
    }
```

### 3. Serial Run集成点

```python
# AI-Novel-Runtime/runtime/serialize/loop.py

def generate_chapter(chapter: int):
    # 新增：契约前置检查
    precheck = contract_precheck(chapter, contracts_dir)
    if not precheck["passed"]:
        log.error(f"Ch{chapter} 契约检查失败")
        for error in precheck["errors"]:
            log.error(f"  - {error}")
        raise ContractCheckError(precheck["errors"])
    
    # 加载契约
    contract = load_contract(chapter)
    
    # 生成prompt（使用v15）
    prompt = generate_prompt_v15(chapter, contract)
    
    # 生成正文
    text = generate_text(prompt)
    
    # 新增：生成后验证
    if chapter > 1:
        prev_text = load_chapter_text(chapter - 1)
        validation = validate_transition(chapter - 1, chapter, 
                                        prev_text, text)
        
        # 保存验证报告
        save_transition_assessment(chapter, validation)
        
        # 如果失败，标记阻断
        if not validation["valid"]:
            mark_blocked(chapter + 1)
            log.warning(f"Ch{chapter} 验证失败，Ch{chapter+1} 已阻断")
    
    return text
```

---

## 🧪 测试计划

### 测试场景1: 正常流程
```
1. 准备Ch102契约（已批准）
2. 运行serial generate Ch102
3. 验证：
   - precheck通过
   - 生成成功
   - 验证通过
   - 无阻断
```

### 测试场景2: 无契约阻断
```
1. 删除Ch102契约
2. 运行serial generate Ch102
3. 验证：
   - precheck失败
   - 生成被阻止
   - 报错清晰
```

### 测试场景3: 未批准阻断
```
1. Ch102契约approved=false
2. 运行serial generate Ch102
3. 验证：
   - precheck失败
   - 报错"契约未批准"
```

### 测试场景4: 验证失败阻断
```
1. Ch102契约要求immediate
2. 生成的正文有时间跳跃
3. 验证：
   - 生成成功
   - 验证失败
   - Ch103被阻断
```

---

## 📊 验收标准

| 指标 | 目标 | 验证方式 |
|------|------|----------|
| Precheck集成 | 100% | 无契约时阻止生成 |
| Prompt v15可用 | 100% | 生成时使用契约 |
| 验证集成 | 100% | 生成后自动验证 |
| 阻断机制 | 100% | 失败时阻止下一章 |

---

## ⏳ 实施时间表

**Task 1: Prompt注册**（1小时）
- 创建v15 YAML
- 注册到PromptLoader
- 测试加载

**Task 2: Precheck集成**（2小时）
- 实现contract_precheck
- 集成到serial run
- 测试阻断

**Task 3: 验证集成**（2小时）
- 实现生成后验证
- 保存assessment报告
- 测试检测

**Task 4: 阻断机制**（1小时）
- 实现blocked标志
- 集成到precheck
- 测试流程

**总计**: 6小时

---

## 🚀 立即开始

**从Task 1开始**: Prompt v15注册

**下一步**:
```bash
cd AI-Novel-Runtime/prompts
mkdir -p v15
# 创建chapter.yaml
```

---

**Phase 2规划完成！准备实施。** ✅
