# C3-1: Promise债务监控 - 实施计划

## 🎯 目标

建立跨章节Promise债务追踪系统，避免Promise累积过多导致读者失望。

---

## 📊 问题背景

### 当前状态
- Promise Ledger已存在
- Promise状态有pending/delivered
- 但缺少债务监控和提醒

### 问题
1. **债务累积** - Promise越积越多，无人关注
2. **兑现延迟** - 重要Promise长时间未兑现
3. **优先级不明** - 不知道该先兑现哪个
4. **无提醒机制** - 创作者不知道有多少债务

---

## 🏗️ 架构设计

### 核心组件

#### 1. PromiseDebtItem - 债务项
```python
@dataclass
class PromiseDebtItem:
    promise_id: str
    promise_type: str
    description: str
    
    created_chapter: int      # 创建章节
    current_chapter: int      # 当前章节  
    chapters_pending: int     # 已等待章节数
    
    urgency: PromiseUrgency   # 紧急程度
    importance: float         # 重要性 0-1
    reader_expectation: float # 读者期待度 0-1
```

#### 2. DebtReport - 债务报告
```python
@dataclass
class DebtReport:
    current_chapter: int
    total_pending_promises: int
    
    # 按紧急程度分类
    critical_debts: List[PromiseDebtItem]
    high_urgency_debts: List[PromiseDebtItem]
    medium_urgency_debts: List[PromiseDebtItem]
    low_urgency_debts: List[PromiseDebtItem]
    
    # 建议
    recommendations: List[str]
    next_chapter_suggestions: List[str]
```

#### 3. PromiseDebtTracker - 债务追踪器
```python
class PromiseDebtTracker:
    def analyze_debt(
        current_chapter: int,
        promise_ledger: Dict
    ) -> DebtReport
    
    def get_priority_promises(
        debt_report: DebtReport,
        top_n: int = 3
    ) -> List[PromiseDebtItem]
```

---

## 📐 紧急程度分级

### 5级紧急度

| 级别 | 等待章节数 | 说明 |
|------|-----------|------|
| CRITICAL | >20章 | 严重逾期，必须立即兑现 |
| HIGH | 15-20章 | 高度紧急，建议3章内兑现 |
| MEDIUM | 10-15章 | 中度紧急，建议5章内兑现 |
| LOW | 5-10章 | 低紧急，可适当关注 |
| NORMAL | <5章 | 正常，无需特别关注 |

---

## 🎯 功能特性

### 1. 债务分析
- 提取所有pending Promise
- 计算等待章节数
- 分配紧急程度

### 2. 优先级排序
```python
排序依据:
1. 紧急程度（高优先）
2. 重要性（高优先）
3. 读者期待度（高优先）
4. 等待时间（长优先）
```

### 3. 自动建议
- 检测债务累积
- 提醒兑现紧急Promise
- 建议下一章兑现目标

### 4. 可读报告
```
=== Promise债务报告 (第50章) ===
总待兑现Promise: 8个
平均等待: 12.5章
最长等待: 22章

紧急程度分布:
  🔴 严重: 1个
  🟠 高: 2个
  🟡 中: 3个
  🟢 低: 2个

建议:
  ⚠️ 严重：有1个Promise严重逾期（>20章），必须尽快兑现
  
下一章建议:
  💡 建议兑现：揭示主角真实身份 (已等待22章)
```

---

## 📦 数据流

```
Promise Ledger
    ↓
extract_pending_promises()
    ↓
calculate_urgency() for each
    ↓
categorize_by_urgency()
    ↓
generate_recommendations()
    ↓
DebtReport
```

---

## 🔗 集成点

### Production Card
```python
production_card.promise_debt_report = {
    "total_pending": int,
    "critical_count": int,
    "high_count": int,
    "recommendations": [...],
    "next_suggestions": [...]
}
```

### Decision Engine
```python
# 在决策中考虑Promise债务
if debt_report.critical_debts:
    priority += 5  # 提高优先级
    warnings.append("有严重逾期Promise")
```

---

## 📊 预期成果

### 功能
- ✅ 跨章节债务追踪
- ✅ 自动紧急程度计算
- ✅ 优先级排序
- ✅ 提醒和建议

### 成熟度提升
- 长期维护好: 70 → 75 (+5)
- 综合成熟度: 83 → 85 (+2)

---

## 🚀 实施步骤

### 阶段1: 核心实现（1-2天）
- PromiseDebtItem数据结构
- PromiseDebtTracker实现
- 紧急程度计算

### 阶段2: 测试（0.5天）
- 12-15个测试用例
- 覆盖各种场景

### 阶段3: 集成（0.5天）
- Production Card集成
- 文档编写

**总计**: 2-3天

---

需要我开始实现吗？
