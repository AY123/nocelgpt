# 阶段 B: Promise Ledger 重构计划

**日期**: 2026-08-17  
**状态**: 规划中  
**预计时间**: 4-6 小时

---

## 🎯 目标

重构承诺追踪系统（Promise Ledger），将当前分散在多个模块中的伏笔/承诺追踪功能统一到一个连贯的系统中。

## 📊 当前状态分析

### 现有的 Promise/Setup 相关模块

1. **`runtime/memory/state.py`** - StoryState 投影
   - 追踪 `open_setups` 和 `resolved_setups`
   - 通过事件的 `causes` 关系判断伏笔是否被回收
   - 纯函数式投影（ADR-008）

2. **`runtime/memory/threads.py`** - 跨章节连续性追踪（P13）
   - `track_threads()`: 扫描未回收的伏笔
   - `dangling_setups`: 标记为伏笔但无后续回收
   - Advisory only (ADR-003)

3. **`runtime/packaging/delivery.py`** - 包装承诺兑现检查（§3.3）
   - 检查包装层承诺是否在前3章兑现
   - 基于 `evidence_terms` 的确定性检查
   - 针对点击漏斗优化

4. **`runtime/narrative/state.py`** - 叙事状态投影
   - `setup_payoff` 字段汇总
   - `payoff_pressure` 计算（>3 个未回收伏笔 = 压力信号）

### 问题诊断

#### 问题 1: 概念碎片化
- **Setup** (memory/state.py) vs **Promise** (packaging/delivery.py) vs **Thread** (threads.py)
- 三个术语指向相同的核心概念：作者埋下的预期，需要在后续兑现
- 没有统一的数据模型和追踪机制

#### 问题 2: 追踪层次混乱
- **包装承诺**: 面向读者的营销承诺（前3章必兑）
- **叙事伏笔**: 故事内部的因果链（可能跨数百章）
- **开放线索**: 未结束的情节线
- 当前代码没有清晰区分这三个层次

#### 问题 3: 缺乏统一追踪
- `StoryState.open_setups` 只是快照，不是账本
- 没有"承诺创建→承诺兑现→承诺关闭"的完整生命周期
- 无法回答："这个伏笔是第几章埋的？应该第几章兑？实际第几章兑的？"

#### 问题 4: 缺少反馈到生成
- 检测器发现问题后，没有闭环到章节生成
- Director 看不到"还有哪些承诺需要兑现"
- 生成提示词缺少"本章应兑现的承诺"信息

## 🏗️ 重构设计

### 核心概念统一

```
Promise (承诺账本条目)
├── id: PROMISE-00001
├── type: packaging | narrative | thread
├── level: critical | important | optional
├── created_at: chapter_index
├── statement: "主角将获得特殊能力"
├── evidence_terms: ["梦晶", "精神力"]
├── must_deliver_by: chapter_index (可选)
├── delivered_at: chapter_index | null
├── status: open | delivered | missed | cancelled
└── lifecycle:
    ├── created_in: EVT-00005
    ├── mentioned_in: [EVT-00010, EVT-00015]
    └── delivered_in: EVT-00020 | null
```

### 三层架构

#### Layer 1: Promise Ledger (账本层)
- **位置**: `runtime/promise/ledger.py`
- **职责**: 
  - 唯一的承诺追踪账本
  - CRUD 承诺条目
  - 生命周期管理
  - 状态投影
- **存储**: `registry/derived/promise-ledger/` (ADR-006)
- **属性**: Pure fold, deterministic, never gates (ADR-003/008)

#### Layer 2: Promise Detectors (检测层)
- **位置**: `runtime/promise/detectors/`
- **职责**:
  - `packaging_detector.py`: 从 book-packaging.yaml 提取承诺
  - `narrative_detector.py`: 从 events 的标记提取伏笔
  - `thread_detector.py`: 检测未关闭的情节线
- **属性**: Read-only, advisory

#### Layer 3: Promise Feedback (反馈层)
- **位置**: `runtime/promise/feedback.py`
- **职责**:
  - 将未兑承诺注入到 chapter objective
  - 生成"本章应兑现"提示
  - 验证兑现是否成功
- **集成点**: Director brief, Chapter IR

### Schema 设计

```json
{
  "id": "promise-ledger.schema.json",
  "type": "object",
  "properties": {
    "ledger_id": {"type": "string"},
    "version": {"const": "1.0"},
    "promises": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"type": "string", "pattern": "^PROMISE-\\d{5}$"},
          "type": {"enum": ["packaging", "narrative", "thread"]},
          "level": {"enum": ["critical", "important", "optional"]},
          "created_at": {"type": "integer", "minimum": 1},
          "statement": {"type": "string"},
          "evidence_terms": {"type": "array", "items": {"type": "string"}},
          "must_deliver_by": {"type": "integer", "minimum": 1},
          "delivered_at": {"type": ["integer", "null"]},
          "status": {"enum": ["open", "delivered", "missed", "cancelled"]},
          "lifecycle": {
            "type": "object",
            "properties": {
              "created_in": {"type": "string"},
              "mentioned_in": {"type": "array"},
              "delivered_in": {"type": ["string", "null"]}
            }
          }
        },
        "required": ["id", "type", "level", "created_at", "statement", "status"]
      }
    },
    "gating": {"const": false},
    "authority": {"const": "human"}
  }
}
```

## 🔄 迁移路径

### Phase B.1: 账本核心 (1.5 小时)
- [ ] 创建 `promise-ledger.schema.json`
- [ ] 实现 `runtime/promise/ledger.py`
  - `PromiseLedger` 类
  - `project_ledger()` 投影函数
  - `ledger_artifact()` 序列化
- [ ] 测试: `test_promise_ledger.py`

### Phase B.2: 检测器统一 (1.5 小时)
- [ ] 创建 `runtime/promise/detectors/`
- [ ] 实现 `packaging_detector.py`
  - 重构 `packaging/delivery.py` 的逻辑
  - 输出标准 Promise 对象
- [ ] 实现 `narrative_detector.py`
  - 重构 `memory/threads.py` 的逻辑
  - 从 events 标记提取
- [ ] 测试: `test_promise_detectors.py`

### Phase B.3: 反馈闭环 (1.5 小时)
- [ ] 实现 `runtime/promise/feedback.py`
  - `pending_promises_for_chapter()`: 查询待兑承诺
  - `render_promise_brief()`: 生成提示文本
  - `verify_delivery()`: 验证兑现
- [ ] 集成到 Director objective
- [ ] 集成到 Chapter IR
- [ ] 测试: `test_promise_feedback.py`

### Phase B.4: 旧模块适配 (1 小时)
- [ ] 保留 `memory/state.py` 的 `open_setups`（向后兼容）
- [ ] 将其实现为 Ledger 的薄包装
- [ ] 保留 `packaging/delivery.py` 的检查逻辑
- [ ] 更新调用方指向新 API

### Phase B.5: CLI 集成 (0.5 小时)
- [ ] 添加 `promise` 命令组
  - `promise ledger --project PATH`: 显示账本
  - `promise check --project PATH --chapter N`: 检查某章承诺
  - `promise export --project PATH`: 导出账本
- [ ] 文档和示例

## ✅ 验收标准

### 功能验收
1. [ ] Promise Ledger 可以追踪所有三类承诺
2. [ ] 可以查询"第 N 章应兑现的承诺"
3. [ ] 可以验证承诺是否已兑现
4. [ ] Director 能看到待兑承诺列表
5. [ ] 生成提示包含待兑承诺信息

### 架构验收
1. [ ] 所有承诺追踪代码统一到 `promise/` 子域
2. [ ] 符合 ADR-003/006/008
3. [ ] Schema 验证通过
4. [ ] 向后兼容（旧代码仍工作）

### 测试验收
1. [ ] 单元测试覆盖 > 90%
2. [ ] 集成测试验证端到端流程
3. [ ] 性能测试（100章账本 < 100ms）
4. [ ] Schema conformance 测试通过

## 📈 预期收益

### 短期收益（立即）
1. **概念清晰**: 统一术语，降低认知负担
2. **追踪完整**: 承诺的完整生命周期可见
3. **调试友好**: 一个地方查看所有承诺状态

### 中期收益（1-2周）
1. **生成质量**: Director 能主动兑现承诺
2. **一致性**: 承诺与兑现自动对齐
3. **读者体验**: 减少"挖坑不填"问题

### 长期收益（1-3月）
1. **数据积累**: 承诺模式可被挖掘
2. **智能推荐**: 基于历史数据推荐承诺策略
3. **质量保证**: 承诺兑现率成为质量指标

## ⚠️ 风险与缓解

### 风险 1: 破坏现有功能
**缓解**: 保留旧 API，新系统作为增强层

### 风险 2: 性能影响
**缓解**: 延迟计算，缓存投影结果

### 风险 3: 复杂度上升
**缓解**: 清晰的层次划分，每层职责单一

## 🎯 成功指标

- [ ] 统一的 Promise 数据模型
- [ ] 100% 测试覆盖关键路径
- [ ] 向后兼容，零回归
- [ ] 文档完整，示例清晰
- [ ] CLI 工具可用
- [ ] 集成到 serial run

## 📝 后续任务

完成阶段 B 后，可以：
1. **C. 真实验证**: 30章基线测试验证 Promise Ledger 效果
2. **D. Promise Analytics**: 挖掘承诺模式，优化策略
3. **E. Auto-Promise**: 自动建议应该埋下的伏笔

---

**准备开始？** 输入 "start B.1" 开始账本核心实现。
