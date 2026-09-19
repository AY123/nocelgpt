# C3-2: 世界设定一致性检查 - 实施计划

## 🎯 目标

建立跨章节世界设定追踪系统，检测设定矛盾，保证长期连载的世界观一致性。

---

## 📊 问题背景

### 当前状态
- 有Story State记录世界状态
- 有Registry记录设定
- 但缺少一致性检查机制

### 问题
1. **设定矛盾** - 前后章节设定冲突
2. **实力崩溃** - 战力体系前后不一致
3. **时间错乱** - 时间线出现矛盾
4. **地理混乱** - 位置距离前后矛盾
5. **无法发现** - 作者和编辑难以人工发现所有矛盾

---

## 🏗️ 架构设计

### 核心组件

#### 1. WorldRule - 世界规则
```python
@dataclass
class WorldRule:
    rule_id: str
    rule_type: str  # "power_system" | "magic" | "geography"
    description: str
    constraints: List[str]
    established_chapter: int
```

#### 2. Inconsistency - 矛盾记录
```python
@dataclass
class Inconsistency:
    inconsistency_type: InconsistencyType
    severity: InconsistencySeverity
    description: str
    conflicting_statements: List[str]
    chapters: List[int]
    suggestion: str
```

#### 3. WorldConsistencyChecker - 检查器
```python
class WorldConsistencyChecker:
    def check_consistency(
        current_chapter: int,
        chapter_content: str,
        story_state: Dict
    ) -> ConsistencyReport
```

---

## 📐 矛盾类型

### 6种矛盾类型

| 类型 | 说明 | 示例 |
|------|------|------|
| RULE_VIOLATION | 规则违反 | 违反已建立的规则 |
| POWER_LEVEL | 实力体系 | 战力前后不一致 |
| TIMELINE | 时间线 | 时间逻辑矛盾 |
| GEOGRAPHY | 地理 | 位置距离矛盾 |
| CHARACTER_ABILITY | 角色能力 | 能力描述不一致 |
| WORLD_LAW | 世界法则 | 物理/魔法法则矛盾 |

### 4级严重程度

| 级别 | 影响 | 处理 |
|------|------|------|
| CRITICAL | 破坏世界观 | 必须修正 |
| HIGH | 明显矛盾 | 建议修正 |
| MEDIUM | 可能矛盾 | 考虑修正 |
| LOW | 小瑕疵 | 可以忽略 |

---

## 🎯 检测逻辑

### 1. 实力体系检查
```python
规则: 筑基 < 金丹 < 元婴
章节50: A是筑基，打败了金丹B
→ 矛盾（实力体系不一致）
```

### 2. 时间线检查
```python
章节10: "三年前发生X事件"
章节50: "五年前发生X事件"
→ 矛盾（时间线冲突）
```

### 3. 地理检查
```python
章节20: "从A城到B城需要10天"
章节60: "主角从A城到B城用了2天"
→ 矛盾（地理距离不一致，需要解释）
```

### 4. 世界法则检查
```python
规则: 此世界魔法需要咒语
章节70: 主角无咒语施放魔法
→ 矛盾（违反世界法则，需要解释）
```

---

## 📦 一致性得分

### 计算公式
```python
初始分数 = 1.0

扣分规则:
- CRITICAL: -0.2
- HIGH: -0.1
- MEDIUM: -0.05
- LOW: -0.02

最终分数 = max(0, 初始分数 - 总扣分)
```

### 评级标准
- **0.95-1.0**: 优秀
- **0.85-0.95**: 良好
- **0.70-0.85**: 一般
- **<0.70**: 需改进

---

## 📊 报告示例

```
=== 世界设定一致性报告 (第50章) ===
已定义规则: 12条
检测到矛盾: 3个
一致性得分: 85.0%

严重程度分布:
  🟠 高: 1个
  🟡 中: 2个

矛盾详情:
1. [高] 实力体系矛盾 (第45-50章)
   描述: 筑基期角色战胜金丹期，与已定义的实力体系不一致
   建议: 添加特殊情况说明（如宝物加持、偷袭等）

2. [中] 时间线模糊 (第50章)
   描述: 缺少明确的时间参考
   建议: 添加时间标记

建议:
  🟠 高：发现1个明显矛盾，建议尽快修正
  📊 实力体系：建议明确实力体系的例外情况
```

---

## 🔗 集成点

### Production Card
```python
production_card.world_consistency = {
    "consistency_score": float,
    "total_inconsistencies": int,
    "critical_count": int,
    "recommendations": [...]
}
```

### Decision Engine
```python
# 严重矛盾影响发布决策
if consistency_score < 0.7:
    warnings.append("世界设定一致性低于70%")
```

---

## 📊 预期成果

### 功能
- ✅ 6类矛盾检测
- ✅ 4级严重程度
- ✅ 一致性得分
- ✅ 自动修正建议

### 成熟度提升
- 长期维护好: 75 → 78 (+3)
- 综合成熟度: 85 → 86 (+1)

---

## 🚀 实施步骤

### 阶段1: 核心实现（2-3天）
- WorldRule数据结构
- WorldConsistencyChecker
- 基础检测逻辑

### 阶段2: 测试（1天）
- 12-15个测试用例
- 各种矛盾场景

### 阶段3: 集成（1天）
- Production Card集成
- 文档编写

**总计**: 4-5天

---

C3-2实施中...
