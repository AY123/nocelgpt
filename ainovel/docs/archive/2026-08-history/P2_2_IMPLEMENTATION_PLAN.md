# P2-2: Paywall Optimizer 重构计划

## 📋 背景与问题

### 当前状态（推测）
- 固定章号付费墙（如第30章）
- 不考虑实际内容价值
- 无法适应不同故事节奏

### 问题
1. **机械化**: 无论质量如何，固定章节付费
2. **错失机会**: 高价值内容可能在免费区
3. **用户体验差**: 可能在低潮期遇到付费墙
4. **不可配置**: 无法基于Constitution调整

---

## 🎯 目标

### 从固定章号到事件驱动

**旧方式**:
```
章节30 → 付费墙（无论内容）
```

**新方式**:
```
核心能力首次兑现 → 付费点
阶段胜利完成 → 付费点
重要关系建立 → 付费点
身份真相揭示 → 付费点
```

---

## 🏗️ 架构设计

### 1. PaywallEvent - 付费点事件

```python
class PaywallEventType(Enum):
    ABILITY_FIRST_DELIVERY = "ability_first_delivery"   # 核心能力首次兑现
    STAGE_VICTORY = "stage_victory"                      # 阶段胜利
    RELATIONSHIP_MILESTONE = "relationship_milestone"    # 关系里程碑
    IDENTITY_REVEAL = "identity_reveal"                  # 身份揭示
    POWER_BREAKTHROUGH = "power_breakthrough"            # 重大突破
    PAYOFF_CLUSTER = "payoff_cluster"                   # 爽点集群
```

### 2. PaywallDetector - 付费点检测器

```python
class PaywallDetector:
    def detect_events(
        chapter_content: str,
        chapter_metadata: Dict,
        story_state: Dict
    ) -> List[PaywallEvent]
```

### 3. PaywallOptimizer - 付费点优化器

```python
class PaywallOptimizer:
    def recommend_paywall(
        chapter_number: int,
        detected_events: List[PaywallEvent],
        constitution: Constitution,
        paywall_history: List[int]
    ) -> PaywallRecommendation
```

---

## 📊 实施阶段

### 阶段1: 数据结构与检测器（2-3天）
- PaywallEvent定义
- PaywallDetector实现
- 6种事件检测逻辑
- 测试用例（15个）

### 阶段2: 优化器与策略（2-3天）
- PaywallOptimizer实现
- 决策策略（基于Constitution）
- 最优时机计算
- 测试用例（12个）

### 阶段3: 集成Production Card（1-2天）
- Production Card扩展
- 决策引擎集成
- 完整流程测试

---

## 🎯 检测逻辑设计

### 1. 核心能力首次兑现
**检测**:
- 检查Promise状态（首次delivered）
- 验证是否为核心能力类Promise
- 确认兑现质量（payoff分数）

**示例**:
```
Promise: "主角获得火焰操控能力"
检测: delivered=true, is_core=true, payoff≥80
→ 付费点候选
```

### 2. 阶段胜利
**检测**:
- 主要冲突解决
- Reward density高峰
- Character growth阶段推进

**示例**:
```
打败大反派 + reward_density≥85 + growth: challenged→transformed
→ 付费点候选
```

### 3. 关系里程碑
**检测**:
- CharacterGrowth中关系状态转变
- Relationship类型的Promise兑现
- 情感高峰（emotion分数）

### 4. 身份揭示
**检测**:
- IDENTITY_REVEAL类型的Promise
- 信息差填补
- 读者"恍然大悟"的时机

### 5. 重大突破
**检测**:
- CharacterGrowth的能力解锁
- Growth stage推进
- 实力质变

### 6. 爽点集群
**检测**:
- 连续3章reward_density≥80
- 多个payoff同时兑现
- Hook强度持续高位

---

## 💡 优化策略

### 1. 基于Constitution
```python
# 从Constitution读取付费策略
constitution.constraints.paywall_earliest_chapter  # 最早付费章节
constitution.core_selling_points  # 核心卖点必须兑现

# 确保核心卖点都体现后再设置付费墙
```

### 2. 最优时机
```python
# 计算付费点质量分数
paywall_score = (
    event_importance * 0.4 +      # 事件重要性
    reader_engagement * 0.3 +      # 读者投入度
    content_quality * 0.2 +        # 内容质量
    timing_appropriateness * 0.1   # 时机合适度
)

# 选择分数最高的章节
```

### 3. 间隔控制
```python
# 避免付费墙过密
min_chapters_between_paywalls = 50

# 避免付费墙过疏
max_chapters_between_paywalls = 100
```

---

## 📦 数据结构草案

```python
@dataclass
class PaywallEvent:
    event_type: PaywallEventType
    chapter_number: int
    importance: float  # 0-1
    description: str
    evidence: Dict[str, Any]

@dataclass
class PaywallRecommendation:
    should_place_paywall: bool
    chapter_number: int
    confidence: float  # 0-1
    primary_event: PaywallEvent
    supporting_events: List[PaywallEvent]
    reasoning: str
```

---

## 🎯 集成点

### Production Card
```python
@dataclass
class ProductionCard:
    # ... 现有字段 ...
    
    # P2-2新增
    paywall_events: List[Dict] = field(default_factory=list)
    paywall_recommendation: Optional[Dict] = None
```

### Decision Engine
```python
# 在决策引擎中考虑付费点
if paywall_recommendation and paywall_recommendation["should_place"]:
    # 影响发布优先级
    # 确保付费点章节质量
```

---

## 🚀 下一步

开始阶段1：
1. 创建paywall_optimizer.py
2. 定义PaywallEvent数据结构
3. 实现PaywallDetector
4. 编写测试用例

**预估时间**: 2-3天

需要我开始实现吗？
