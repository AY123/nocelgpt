# Phase 2简化实施方案

**现状**: AI-Novel-Runtime结构复杂，直接集成需要深入理解现有架构  
**问题**: 会话已600+分钟，完整集成需要更多时间  
**方案**: 创建独立的契约集成层，作为Runtime的插件

---

## 🎯 简化方案：Contract Plugin

### 设计理念
不修改Runtime核心代码，而是创建独立的契约插件层

### 架构
```
AI-Novel-Runtime (不修改)
    ↓
Contract Plugin (新增)
    ↓
    ├─ contract_loader.py (加载契约)
    ├─ contract_validator.py (验证)
    ├─ prompt_injector.py (注入prompt)
    └─ contract_gate.py (门禁)
```

---

## 📁 实施方案

### 文件结构
```
runtime/plugins/contract/
├── __init__.py
├── loader.py          # 加载契约
├── validator.py       # 验证契约
├── injector.py        # 注入到prompt
└── gate.py            # 生成前门禁
```

### 使用方式
```python
# 在Runtime中使用
from runtime.plugins.contract import ContractGate

# 生成前检查
gate = ContractGate(contracts_dir)
gate.precheck(chapter_num)  # 不通过则抛异常

# 加载契约并注入
contract = gate.load_contract(chapter_num)
prompt = gate.inject_contract(base_prompt, contract)

# 生成后验证
gate.validate(chapter_num, prev_text, curr_text)
```

---

## 🔧 核心代码

### 1. Contract Gate (门禁)

```python
# runtime/plugins/contract/gate.py

from pathlib import Path
import json
import jsonschema

class ContractGate:
    """契约门禁系统"""
    
    def __init__(self, contracts_dir: Path, schemas_dir: Path):
        self.contracts_dir = contracts_dir
        self.schema = self._load_schema(schemas_dir)
    
    def precheck(self, chapter: int) -> None:
        """
        生成前检查
        
        不通过则抛ContractCheckError
        """
        contract = self._load_contract(chapter)
        
        # 1. 契约存在
        if not contract:
            raise ContractCheckError(f"Ch{chapter}契约不存在")
        
        # 2. Schema合规
        try:
            jsonschema.validate(contract, self.schema)
        except jsonschema.ValidationError as e:
            raise ContractCheckError(f"Schema验证失败: {e.message}")
        
        # 3. 已批准
        if not contract.get("approved"):
            raise ContractCheckError(f"Ch{chapter}契约未批准")
    
    def load_contract(self, chapter: int) -> dict:
        """加载契约"""
        return self._load_contract(chapter)
    
    def inject_contract(self, base_prompt: str, contract: dict) -> str:
        """
        将契约注入prompt
        
        在base_prompt前添加契约要求
        """
        entry = contract.get("entry_state", {})
        intent = contract.get("chapter_intent", {})
        exit_target = contract.get("exit_target", {})
        
        contract_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 章节契约（必须严格遵守）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【入口要求】
• 地点：{entry.get('location_id', '')}
• 时间：{entry.get('time_relation', '')}
• 视角：{entry.get('pov', '')}
• 必须处理：{entry.get('must_address', '')}

【本章目标】
{intent.get('objective', '')}

【出口要求】
• 地点：{exit_target.get('location_id', '')}
• 钩子：{exit_target.get('hook_promise', '')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        return contract_section + "\n" + base_prompt
    
    def validate(self, chapter: int, prev_text: str, curr_text: str) -> dict:
        """
        生成后验证
        
        Returns:
            {
                "valid": bool,
                "errors": []
            }
        """
        from validate_contract import ContractValidator
        
        validator = ContractValidator(self.contracts_dir)
        return validator.validate_transition(
            chapter - 1, chapter, prev_text, curr_text
        )


class ContractCheckError(Exception):
    """契约检查失败异常"""
    pass
```

### 2. 集成到Runtime

```python
# runtime/chapter/writer.py (修改)

from runtime.plugins.contract import ContractGate, ContractCheckError

class ChapterWriter:
    def __init__(self, ...):
        # 新增：契约门禁
        self.contract_gate = ContractGate(
            contracts_dir=Path("contracts"),
            schemas_dir=Path("schemas")
        )
    
    def generate(self, chapter: int, base_prompt: str) -> str:
        # 新增：生成前检查
        try:
            self.contract_gate.precheck(chapter)
        except ContractCheckError as e:
            print(f"❌ 契约检查失败: {e}")
            raise
        
        # 新增：加载契约并注入
        contract = self.contract_gate.load_contract(chapter)
        prompt = self.contract_gate.inject_contract(base_prompt, contract)
        
        # 原有逻辑：生成
        text = self._generate_text(prompt)
        
        # 新增：生成后验证
        if chapter > 1:
            prev_text = self._load_prev_chapter(chapter - 1)
            validation = self.contract_gate.validate(
                chapter, prev_text, text
            )
            
            if not validation["valid"]:
                print(f"⚠️  Ch{chapter}验证失败:")
                for error in validation["errors"]:
                    print(f"  - {error}")
        
        return text
```

---

## ✅ 优点

1. **非侵入式**: 不修改Runtime核心
2. **独立可测**: 插件可单独测试
3. **易于集成**: 只需在writer中调用
4. **可选功能**: 可以开关

---

## 🧪 验证方式

### 单元测试
```python
# tests/test_contract_gate.py

def test_precheck_success():
    gate = ContractGate(contracts_dir, schemas_dir)
    gate.precheck(101)  # 应该通过

def test_precheck_no_contract():
    gate = ContractGate(contracts_dir, schemas_dir)
    with pytest.raises(ContractCheckError):
        gate.precheck(999)  # 应该失败

def test_inject_contract():
    gate = ContractGate(contracts_dir, schemas_dir)
    contract = gate.load_contract(101)
    prompt = gate.inject_contract("原始prompt", contract)
    assert "章节契约" in prompt
```

### 集成测试
```python
# 使用Contract Gate生成Ch102
writer = ChapterWriter(...)
text = writer.generate(102, base_prompt)
# 验证是否遵守契约
```

---

## ⏰ 实施时间

**创建插件**: 2小时
- gate.py实现（1h）
- 单元测试（1h）

**集成到Runtime**: 1小时
- 修改writer.py
- 集成测试

**总计**: 3小时（而非6小时）

---

## 🎯 最小验证

**目标**: 证明契约能阻止和指导生成

**步骤**:
1. 创建contract_gate.py
2. 写单元测试
3. 手动集成测试
4. 生成Ch102验证

**验收**: 
- precheck能阻止
- 契约能注入
- 验证能检测

---

**简化方案更实际，3小时可完成核心功能。** ✅
