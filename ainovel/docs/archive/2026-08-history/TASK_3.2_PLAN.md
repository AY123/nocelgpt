# Task 3.2详细实施方案 - 修改run_serial入口

**状态**: 📋 规划完成，待实施  
**预计**: 2小时  
**前置**: Task 3.1完成（v15 Prompt可用）

---

## 🎯 目标

将v15 Prompt集成到run_serial生成流程，使其能够：
1. 接受contracts_dir和schemas_dir参数
2. 在prompt_version="15.0.0"时使用v15
3. 支持enable_contract_gate开关
4. 处理Contract Gate的异常

---

## 📋 实施步骤

### Step 1: 添加参数到run_serial（30分钟）

**位置**: `runtime/serialize/loop.py::run_serial()`

**添加参数**:
```python
def run_serial(
    *,
    # ... 现有参数
    prompt_version: str = "1.0.0",
    
    # 新增参数 ↓
    contracts_dir: Optional[str | Path] = None,
    schemas_dir: Optional[str | Path] = None,
    enable_contract_gate: bool = False,
    contract_strict_mode: bool = False,
    # ... 其他参数
):
    """
    新增参数说明：
    - contracts_dir: 契约目录，v15必需
    - schemas_dir: Schema目录，v15必需
    - enable_contract_gate: 是否启用契约门禁
    - contract_strict_mode: 严格模式（precheck失败时抛异常）
    """
```

**验证参数**:
```python
# 在run_serial开始处添加
if enable_contract_gate or prompt_version.startswith("15."):
    if not contracts_dir or not schemas_dir:
        raise ValueError(
            "v15 prompt需要contracts_dir和schemas_dir参数"
        )
    
    contracts_dir = Path(contracts_dir)
    schemas_dir = Path(schemas_dir)
    
    if not contracts_dir.exists():
        raise ValueError(f"contracts_dir不存在: {contracts_dir}")
    
    if not schemas_dir.exists():
        raise ValueError(f"schemas_dir不存在: {schemas_dir}")
```

### Step 2: 集成v15到prompt生成（1小时）

**查找prompt生成位置**:

根据代码分析，prompt生成在章节执行时发生。需要找到：
- 哪里调用了prompt生成
- 如何传递prompt_version
- 如何注入v15逻辑

**集成方案A**: 在prompt_runtime中添加v15（推荐）

```python
# 在生成章节的位置（需要找到确切位置）
if prompt_version.startswith("15.") and enable_contract_gate:
    # 使用v15
    from runtime.prompts.v15.chapter import render_chapter_prompt_v15
    
    try:
        prompt = render_chapter_prompt_v15(
            chapter=chapter_no,
            contracts_dir=contracts_dir,
            schemas_dir=schemas_dir,
            base_context={
                'objective': objective,
                'ir': ir,
                # ... 其他上下文
            },
            strict_mode=contract_strict_mode
        )
    except ContractCheckError as e:
        log.error(f"Ch{chapter_no}契约检查失败: {e}")
        if contract_strict_mode:
            raise
        else:
            # 跳过此章
            continue
else:
    # 使用原有v1-v10逻辑
    prompt = render_original_prompt(...)
```

**集成方案B**: 修改prompt_runtime参数（备选）

可能需要在prompt_runtime字典中添加v15相关信息。

### Step 3: 处理Contract Gate异常（20分钟）

**异常类型**:
1. ContractCheckError - precheck失败
2. FileNotFoundError - 契约文件不存在
3. ValidationError - Schema验证失败

**处理策略**:

```python
from runtime_plugins.contract import ContractCheckError

try:
    # v15 prompt生成
    prompt = render_chapter_prompt_v15(...)
except ContractCheckError as e:
    log.error(f"Ch{chapter_no}契约检查失败: {e}")
    
    if contract_strict_mode:
        # 严格模式：抛出异常，停止serial
        raise
    else:
        # 非严格模式：记录并跳过
        log.warning(f"跳过Ch{chapter_no}（契约检查失败）")
        # 可选：记录到跳过列表
        skipped_chapters.append(chapter_no)
        continue
```

### Step 4: 传递contracts_dir参数（10分钟）

**向下传递**:

需要确保contracts_dir和schemas_dir能传递到实际生成prompt的位置。

可能需要：
1. 添加到章节任务包（task package）
2. 添加到执行上下文
3. 通过闭包捕获

---

## 🔍 代码分析要点

### 关键位置

**已确认**:
- `run_serial()` 在 line 417
- `prompt_version` 参数在 line 429
- 有多处检查prompt_version（line 585, 650）

**待确认**:
- prompt实际生成在哪里
- 如何传递context到prompt
- execute_package的调用位置

### 查找方法

```bash
# 查找execute相关
grep -n "execute" runtime/serialize/loop.py | grep -i "chapter\|package"

# 查找prompt生成
grep -n "render\|build.*prompt" runtime/serialize/loop.py

# 查找章节循环
grep -n "for.*chapter\|while.*chapter" runtime/serialize/loop.py
```

---

## 🧪 测试计划

### 单元测试

**测试用例**:
1. v15 + enable_contract_gate=True → 使用v15
2. v15 + enable_contract_gate=False → 使用v15但降级
3. v1-v10 + enable_contract_gate=True → 忽略契约
4. 无contracts_dir → ValueError
5. precheck失败 + strict=True → 抛异常
6. precheck失败 + strict=False → 跳过章节

### 集成测试

**端到端测试**:
```bash
# 测试1: 正常生成（有契约）
python runtime/cli.py serial \
    --project-path . \
    --prompt-version 15.0.0 \
    --enable-contract-gate \
    --contracts-dir ../contracts \
    --schemas-dir ../schemas \
    --start-chapter 101 \
    --max-chapters 1

# 测试2: 无契约章节（应跳过）
python runtime/cli.py serial \
    ... \
    --start-chapter 999

# 测试3: 严格模式（应失败）
python runtime/cli.py serial \
    ... \
    --contract-strict-mode \
    --start-chapter 999
```

---

## 📝 实施检查清单

### 代码修改

- [ ] 添加参数到run_serial签名
- [ ] 添加参数验证逻辑
- [ ] 找到prompt生成位置
- [ ] 集成v15调用
- [ ] 添加异常处理
- [ ] 传递contracts_dir

### 测试

- [ ] 参数验证测试
- [ ] v15调用测试
- [ ] 异常处理测试
- [ ] 端到端测试

### 文档

- [ ] 更新函数docstring
- [ ] 添加参数说明
- [ ] 更新使用示例

---

## 💡 实施注意事项

### 1. 保持向后兼容

**原则**:
- v1-v10不受影响
- enable_contract_gate默认False
- 优雅降级

### 2. 最小侵入

**原则**:
- 只在必要处修改
- 复用现有逻辑
- 添加而非替换

### 3. 错误处理

**原则**:
- 明确的错误信息
- 区分用户错误vs系统错误
- 提供解决建议

### 4. 遵循ADR-003

**原则**:
- Never gate the serial
- 记录问题但继续
- 只在strict_mode才停止

---

## 🚀 快速开始（下次会话）

### 第一步：代码探索

```bash
cd AI-Novel-Runtime

# 1. 找到prompt生成位置
grep -n "render" runtime/serialize/loop.py | less

# 2. 找到章节执行循环
grep -n "for.*in.*chapters" runtime/serialize/loop.py

# 3. 查看execute_package
grep -A20 "def execute_package" runtime/serialize/*.py
```

### 第二步：最小修改

1. 添加4个参数到run_serial
2. 找到1个prompt生成位置
3. 添加v15分支逻辑
4. 测试

### 第三步：完整测试

1. 单元测试
2. 端到端测试
3. 边界测试

---

## 📊 预期成果

### Task 3.2完成标志

- [x] run_serial接受v15参数
- [x] v15能正确调用
- [x] 异常处理正确
- [x] 测试通过

### 验收标准

| 标准 | 验证方式 |
|------|----------|
| 参数可用 | 调用不报错 |
| v15生成 | 生成包含契约的prompt |
| 异常处理 | precheck失败时正确处理 |
| 向后兼容 | v1-v10不受影响 |

---

**Task 3.2方案完成！下次可直接实施。** ✅

**预计**: 2小时  
**关键**: 找到prompt生成位置
