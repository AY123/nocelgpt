# P1 实现计划：完善出口状态可信度

**日期**: 2026-08-15  
**状态**: 设计阶段

---

## 🎯 目标

将当前的低置信度启发式提取器升级为：
1. 每个字段独立置信度
2. 实现 evidence_spans
3. 低置信度字段保留计划状态
4. 扩展地点、人物提取能力

---

## 📊 当前状态

### 当前实现
```python
def extract_actual_exit_state(self, chapter, final_text, final_text_hash):
    return {
        "location_id": "loc_xxx",
        "characters_present": [...],
        "emotional_state": "determined",
        "hook_promise": "...",
        "evidence_spans": [],  # 未实现
        "confidence": 0.6,     # 统一置信度
        "extraction_method": "heuristic"
    }
```

### 问题
- ❌ 所有字段使用统一的 0.6 置信度
- ❌ evidence_spans 为空
- ❌ 低置信度字段仍然会覆盖计划状态
- ❌ 地点依赖预配置关键词
- ❌ 人物依赖固定角色名列表

---

## 🔧 改进方案

### 1. 每个字段独立置信度

**新返回结构**:
```python
{
    "location_id": "loc_forest_ruins",
    "location_confidence": 1.0,  # 高置信度：匹配到关键词
    
    "characters_present": ["主角", "导师"],
    "characters_confidence": 0.8,  # 中高：找到角色名
    
    "emotional_state": "determined",
    "emotional_confidence": 0.9,  # 高：找到情绪关键词
    
    "hook_promise": "但是，远处传来了...",
    "hook_confidence": 0.7,  # 中：找到钩子指示词
    
    "overall_confidence": 0.85,  # 加权平均
}
```

**置信度分级**:
- `1.0`: 匹配到配置的关键词
- `0.7-0.9`: 找到强指示信号
- `0.5-0.6`: 使用计划值或弱信号
- `0.3-0.4`: 回退到默认值
- `< 0.3`: 完全未知

### 2. 实现 evidence_spans

**格式**:
```python
"evidence_spans": [
    {
        "field": "location_id",
        "text": "...走进了古老的遗迹深处...",
        "confidence": 1.0,
        "match": "遗迹"  # 匹配到的关键词
    },
    {
        "field": "characters_present",
        "text": "...主角和导师并肩而立...",
        "confidence": 0.8,
        "character": "主角"
    },
    {
        "field": "emotional_state",
        "text": "...他眼中闪烁着坚定的光芒...",
        "confidence": 0.9,
        "match": "坚定"
    }
]
```

**实现方法**:
- 使用 `str.find()` 定位关键词位置
- 提取前后各 20 个字符作为上下文
- 记录匹配到的关键词/模式

### 3. 低置信度字段处理

**策略**:
```python
CONFIDENCE_THRESHOLD = 0.5

if location_confidence < CONFIDENCE_THRESHOLD:
    # 保留计划值，标记为 "planned_fallback"
    actual_exit["location_id"] = planned_exit.get("location_id", "loc_unknown")
    actual_exit["location_source"] = "planned_fallback"
else:
    # 使用提取值
    actual_exit["location_id"] = extracted_location
    actual_exit["location_source"] = "extracted"
```

**在 loop.py 中使用**:
```python
# 优先使用高置信度的实际出口
if actual_exit.get("location_confidence", 0) > 0.5:
    location = actual_exit["location_id"]
else:
    # 低置信度：同时显示计划和实际（如果不同）
    location = f"{actual_exit['location_id']} (低置信度，计划: {planned_location})"
```

### 4. 扩展地点提取能力

**当前限制**:
- 依赖 `location_keywords` 配置
- 无法识别未配置的地点

**改进方向**:

**短期（P1）**:
- 增加常见地点关键词库
- 支持模式匹配（"XXX处", "XXX中", "XXX内"）
- 从事实库动态加载地点名称

```python
def _extract_location_with_patterns(self, text: str):
    # 模式 1: "在XXX"、"到了XXX"
    patterns = [
        r'在([^，。！？]{2,6})',
        r'到了([^，。！？]{2,6})',
        r'走进([^，。！？]{2,6})',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            return matches[0], 0.6, {"text": ..., "pattern": pattern}
```

**长期（P2）**:
- 使用 LLM 提取地点（结构化输出）
- 命名实体识别（NER）
- 从事实库验证地点存在性

### 5. 扩展人物提取能力

**当前限制**:
- 依赖固定角色名列表 `['主角', '导师', ...]`

**改进方向**:

**短期（P1）**:
```python
def _extract_characters_from_facts(self, text: str, project_path: Path):
    # 从 registry/facts/characters/ 读取所有角色
    characters_dir = project_path / "registry" / "facts" / "characters"
    if not characters_dir.exists():
        return self._extract_characters_hardcoded(text)
    
    found_characters = []
    for char_file in characters_dir.glob("*.yaml"):
        char_data = yaml.safe_load(char_file.read_text())
        char_name = char_data.get("name")
        if char_name and char_name in text:
            found_characters.append(char_name)
    
    return found_characters, 0.8 if found_characters else 0.3, [...]
```

**长期（P2）**:
- 使用 LLM 提取角色
- 角色别名/称谓处理（"他"、"那人"）
- 从对话推断在场角色

---

## 📝 实现步骤

### 阶段 1: 基础增强（本次）

1. ✅ **设计文档** - 本文档
2. ✅ **设计原型** - `p1_enhanced_extraction_design.py`
3. ⏳ **实现独立置信度**
   - 修改每个 `_extract_*` 方法
   - 返回 `(value, confidence, evidence)`
4. ⏳ **实现 evidence_spans**
   - 使用 `str.find()` 定位
   - 提取上下文片段
5. ⏳ **聚合到主方法**
   - 修改 `extract_actual_exit_state`
   - 计算 overall_confidence
6. ⏳ **测试验证**
   - 单元测试每个提取方法
   - 集成测试完整流程

### 阶段 2: 回退策略（本次）

7. ⏳ **低置信度处理**
   - 添加 `_source` 字段标记来源
   - 阈值可配置
8. ⏳ **loop.py 集成**
   - 读取置信度
   - 低置信度时同时显示计划和实际
9. ⏳ **测试验证**

### 阶段 3: 扩展能力（P1+）

10. ⏳ **地点提取增强**
    - 模式匹配
    - 从事实库加载
11. ⏳ **人物提取增强**
    - 从事实库加载角色
12. ⏳ **测试验证**

### 阶段 4: 高级功能（P2）

13. 待定 **LLM 辅助提取**
14. 待定 **NER 集成**

---

## 🧪 测试计划

### 单元测试

```python
def test_extract_location_with_confidence():
    gate = ContractGate(...)
    
    # 高置信度：关键词匹配
    text1 = "他们走进了古老的遗迹深处"
    loc, conf, evidence = gate._extract_location_with_confidence(text1)
    assert conf >= 0.9
    assert "遗迹" in evidence["text"]
    
    # 中置信度：计划关键词
    text2 = "他们继续前行"
    loc, conf, evidence = gate._extract_location_with_confidence(
        text2, planned_location="loc_forest_path")
    assert 0.6 <= conf < 0.9
    
    # 低置信度：未知
    text3 = "他们停下了脚步"
    loc, conf, evidence = gate._extract_location_with_confidence(text3)
    assert conf < 0.5
```

### 集成测试

```python
def test_enhanced_extraction_with_evidence():
    gate = ContractGate(...)
    
    final_text = """
    ...(前面 80% 内容)...
    
    他们终于走进了古老的遗迹深处。主角和导师并肩而立，
    眼中闪烁着坚定的光芒。但是，远处传来了诡异的声音...
    """
    
    result = gate.extract_actual_exit_state(1, final_text, "hash-xxx")
    
    # 检查独立置信度
    assert result["location_confidence"] >= 0.9
    assert result["characters_confidence"] >= 0.8
    assert result["emotional_confidence"] >= 0.9
    assert result["hook_confidence"] >= 0.7
    
    # 检查 evidence_spans
    assert len(result["evidence_spans"]) >= 4
    location_evidence = [e for e in result["evidence_spans"] 
                         if e["field"] == "location_id"][0]
    assert "遗迹" in location_evidence["text"]
    
    # 检查总体置信度
    assert result["overall_confidence"] >= 0.8
```

---

## 🎯 成功标准

### 功能完整性
- ✅ 每个字段有独立置信度
- ✅ evidence_spans 不为空
- ✅ 低置信度字段有回退机制
- ✅ 地点提取能力扩展

### 测试覆盖
- ✅ 单元测试覆盖所有提取方法
- ✅ 集成测试验证完整流程
- ✅ 边界情况测试

### 文档
- ✅ API 文档更新
- ✅ 使用指南
- ✅ 示例代码

---

## 📊 预期改进

### 提取质量

| 字段 | 当前置信度 | 改进后置信度 | 说明 |
|-----|-----------|-------------|------|
| location_id | 0.6 (统一) | 0.9 (高) | 关键词匹配 |
| characters | 0.6 (统一) | 0.8 (中高) | 事实库加载 |
| emotional_state | 0.6 (统一) | 0.9 (高) | 关键词匹配 |
| hook_promise | 0.6 (统一) | 0.7 (中高) | 模式匹配 |

### 可审计性

- ❌ 当前：无法知道提取依据
- ✅ 改进：每个字段都有证据片段
- ✅ 改进：可以追溯到原文位置

### 可靠性

- ❌ 当前：低置信度字段仍然覆盖计划
- ✅ 改进：低置信度字段保留计划或标记
- ✅ 改进：用户可以根据置信度决策

---

## 🔄 向后兼容

### API 兼容性

**选项 1: 扩展现有 API（推荐）**
```python
# 老代码仍然工作
result = gate.extract_actual_exit_state(1, text, hash)
location = result["location_id"]  # 仍然可用

# 新代码可以使用置信度
if result.get("location_confidence", 0) > 0.5:
    location = result["location_id"]
```

**选项 2: 新增 API**
```python
# 老 API 保持不变
result = gate.extract_actual_exit_state(1, text, hash)

# 新 API 返回增强信息
result = gate.extract_actual_exit_state_enhanced(1, text, hash)
```

### 数据兼容性

- ✅ 旧的出口文件仍然可读（已有字段不变）
- ✅ 新字段是可选的（`*_confidence`, `evidence_spans`）
- ✅ loop.py 优雅降级（检查字段是否存在）

---

## 📅 时间估算

| 任务 | 工作量 | 说明 |
|-----|--------|------|
| 独立置信度实现 | 2-3 小时 | 修改 7 个提取方法 |
| evidence_spans 实现 | 1-2 小时 | 添加上下文提取 |
| 主方法聚合 | 1 小时 | 修改主方法 |
| 回退策略 | 1 小时 | 低置信度处理 |
| loop.py 集成 | 1 小时 | 读取和使用置信度 |
| 地点扩展 | 2 小时 | 模式匹配 + 事实库 |
| 人物扩展 | 2 小时 | 事实库加载 |
| 测试编写 | 2-3 小时 | 单元 + 集成测试 |
| 文档更新 | 1 小时 | API 文档 |
| **总计** | **13-16 小时** | 约 2 个工作日 |

---

## 🚀 下一步

1. ✅ 完成设计文档（本文档）
2. ✅ 完成设计原型（已完成）
3. ⏳ 实现独立置信度和 evidence_spans
4. ⏳ 编写测试验证
5. ⏳ 集成到 loop.py
6. ⏳ 文档更新

---

**状态**: 设计完成，准备开始实现 ✅

*设计人: Claude Opus 4.8*  
*日期: 2026-08-15*
