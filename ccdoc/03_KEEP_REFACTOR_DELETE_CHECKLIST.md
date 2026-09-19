# 保留-重构-删除清单

**版本**: v1.0  
**制定日期**: 2026-09-18  
**依据**: 项目深度分析 + 审计报告  

---

## 一、保留清单（40%）- 直接复用

### 1.1 AI-Novel-Standard（规范层）

**保留原因**: Schema-first 设计是正确的，IDL → JSON Schema 流程成熟

```
AI-Novel-Standard/
├── idl/                    ✅ 保留 - 实体定义
├── generated/              ✅ 保留 - 自动生成的 Schema
├── contracts/              ✅ 保留 - 任务合同
└── ADR/                    ✅ 保留 - 架构决策记录
```

**注意事项**:
- ADR 是经验总结，必须读
- Schema 不改，改 Runtime 的消费方式

---

### 1.2 编译管道

**保留原因**: Task Package 构建、验证、版本化机制成熟

```
AI-Novel-Runtime/runtime/
├── pipeline/
│   ├── compiler.py         ✅ 保留 - 任务编译
│   ├── validator.py        ✅ 保留 - 验证器（需重构注册机制）
│   └── manifest.py         ✅ 保留 - 构建清单
└── registry/
    ├── loader.py           ✅ 保留 - 事实加载
    ├── resolver.py         ✅ 保留 - 引用解析
    └── normalizer.py       ✅ 保留 - 归一化
```

**注意事项**:
- `validator.py` 需要重构为注册表模式（已在 V1 完成）
- 保持接口不变

---

### 1.3 事实系统

**保留原因**: State as Projection 是长篇小说的正确架构

```
AI-Novel-Runtime/runtime/
├── memory/
│   └── state.py            ✅ 保留 - StoryState 投影
├── mint/
│   ├── executor.py         ⚠️ 保留但需修复事务完整性
│   └── idmint.py           ✅ 保留 - ID 铸造账本
└── derived.py              ✅ 保留 - 衍生物管理
```

**注意事项**:
- `mint/executor.py` 必须修复原子提交问题（P0）
- StoryState 投影逻辑正确，保持不变

---

### 1.4 模型适配层

**保留原因**: 真实 LLM 适配器、Replay 机制、成本计算都可用

```
AI-Novel-Runtime/runtime/
└── llm/
    ├── gateway.py          ✅ 保留 - 模型网关
    ├── adapters/           ✅ 保留 - 各模型适配器
    │   ├── openai.py
    │   ├── deepseek.py
    │   └── anthropic.py
    ├── replay.py           ✅ 保留 - 回放机制
    └── cost.py             ✅ 保留 - 成本计算
```

**注意事项**:
- Replay key 已修复（不包含 timeout），保持当前实现
- 成本计算准确性未验证，但机制可用

---

### 1.5 测试框架

**保留原因**: 确定性测试覆盖基础功能

```
AI-Novel-Runtime/tests/
├── test_pipeline.py        ✅ 保留 - 编译管道测试
├── test_registry.py        ✅ 保留 - 事实加载测试
├── test_state.py           ✅ 保留 - 状态投影测试
├── test_llm.py             ✅ 保留 - 模型适配测试
└── test_fitness.py         ✅ 保留 - 架构健康测试
```

**注意事项**:
- 保留所有确定性测试
- 删除依赖未校准模块的测试

---

### 1.6 AI-Novel-Template

**保留原因**: 项目脚手架机制正确

```
AI-Novel-Template/
├── init_project.py         ✅ 保留
└── templates/              ✅ 保留
```

---

## 二、重构清单（30%）- 需要改造

### 2.1 Genre 系统（P0 核心优先级）

**重构原因**: 被当作字符串标签，导致都市写成奇幻

**当前实现**:
```
AI-Novel-Runtime/runtime/outline/
└── analyzer.py             🔄 重写 - 简单关键词匹配 → 领域模型
```

**目标实现**:
```
AI-Novel-Runtime/runtime/genre/    🆕 新建目录
├── __init__.py
├── core.py                         🆕 GenreConfig、GenreConstraints
├── registry.py                     🆕 GenreRegistry
├── progression.py                  🆕 ProgressionModel 抽象
├── progression/
│   ├── power.py                    🆕 PowerProgressionModel
│   ├── wealth.py                   🆕 WealthProgressionModel
│   └── tech.py                     🆕 TechProgressionModel
└── configs/
    ├── urban.py                    🆕 都市完整配置
    ├── xuanhuan.py                 🆕 玄幻完整配置
    └── ...
```

**工作量**: 2-3 周

**验收**:
- ✅ 题材检测准确率 > 90%
- ✅ 都市不生成修炼（5 个测试用例）
- ✅ 玄幻不生成商业（5 个测试用例）

---

### 2.2 Prompt 系统（P0）

**重构原因**: 通用模板无法约束题材

**当前实现**:
```
AI-Novel-Runtime/runtime/prompt/
├── templates/
│   └── universal.txt       🔄 删除 - 通用模板不可用
└── loader.py               🔄 保留框架，改加载逻辑
```

**目标实现**:
```
AI-Novel-Runtime/runtime/prompt/
├── templates/
│   ├── urban/              🆕 都市专用模板
│   │   ├── outline_v1.txt
│   │   ├── chapter_v1.txt
│   │   └── revision_v1.txt
│   ├── xuanhuan/           🆕 玄幻专用模板
│   │   ├── outline_v1.txt
│   │   ├── chapter_v1.txt
│   │   └── revision_v1.txt
│   └── shared/
│       └── constraints_injection.txt
├── loader.py               🔄 重构 - 题材感知加载
└── renderer.py             🔄 重构 - 约束自动注入
```

**工作量**: 1-2 周

**验收**:
- ✅ 都市/玄幻各有专用模板
- ✅ 约束自动注入到 prompt

---

### 2.3 生产编排（P1）

**重构原因**: `loop.py` 2907 行，高度耦合

**当前实现**:
```
AI-Novel-Runtime/runtime/serialize/
└── loop.py                 🔄 解耦 - 从 2907 行降到 < 500 行
```

**目标实现**:
```
AI-Novel-Runtime/runtime/production/   🆕 新建目录
├── __init__.py
├── pipeline.py             🆕 Pipeline 框架
├── context.py              🆕 ChapterContext
├── stages/                 🆕 Stage 插件
│   ├── __init__.py
│   ├── base.py             🆕 ProductionStage 抽象
│   ├── load.py             🆕 LoadContextStage
│   ├── generate.py         🆕 GenerateDraftStage
│   ├── genre_validate.py   🆕 GenreValidationStage
│   ├── quality_gate.py     🆕 QualityGateStage
│   ├── commercial.py       🆕 CommercialOptimizationStage
│   ├── decision.py         🆕 DecisionStage
│   └── persist.py          🆕 PersistStage
└── orchestrator.py         🔄 重写 - 使用 Pipeline
```

**保留**:
```
AI-Novel-Runtime/runtime/serialize/
├── plan.py                 ✅ 保留 - 章节规划
└── state.py                ✅ 保留 - 串行状态管理
```

**工作量**: 2-3 周

**验收**:
- ✅ 主流程 < 500 行
- ✅ BLOCKED 正确阻断后续章节
- ✅ 新增 Stage 不修改主流程

---

### 2.4 Genesis 流程（P1）

**重构原因**: 题材无关的通用生成

**当前实现**:
```
AI-Novel-Runtime/runtime/outline/
├── genesis.py              🔄 重构 - 题材感知
├── analyzer.py             🔄 删除 → 移到 genre/
└── llm_agents.py           🔄 重构 - 使用题材配置
```

**目标实现**:
```
AI-Novel-Runtime/runtime/genesis/      🆕 重命名 outline → genesis
├── __init__.py
├── genre_aware_genesis.py  🆕 题材感知的开书流程
├── analyzer.py             🔄 迁移自 outline/analyzer.py
└── llm_agents.py           🔄 重构 - 注入 GenreConfig
```

**工作量**: 1 周

**验收**:
- ✅ 都市参考 → 都市大纲
- ✅ 玄幻参考 → 玄幻大纲
- ✅ 约束违反阻断 Genesis

---

### 2.5 质量系统（P1）

**重构原因**: 确定性检查 vs 评分混在一起

**当前实现**:
```
AI-Novel-Runtime/runtime/qa/
├── quality_gate.py         🔄 保留 - 确定性检查
└── quality_judge.py        ⏸️ 暂时下线 - 未校准
```

**目标实现**:
```
AI-Novel-Runtime/runtime/qa/
├── deterministic/          🆕 确定性检查（可阻断）
│   ├── genre_validator.py  🆕 题材约束验证
│   ├── length_validator.py 🆕 长度验证
│   ├── format_validator.py 🆕 格式验证
│   └── ai_taste_detector.py 🆕 AI 味道检测
└── evaluative/             ⏸️ 评分系统（不阻断）
    ├── quality_judge.py    ⏸️ 暂时下线
    └── reader_sim.py       ⏸️ 暂时下线
```

**工作量**: 1-2 周

**验收**:
- ✅ 确定性检查可阻断
- ✅ 评分系统标记为"诊断级"

---

## 三、删除清单（30%）- 直接移除

### 3.1 未接线的模块

**删除原因**: Fitness 测试发现不可达

```
AI-Novel-Runtime/runtime/
├── duplicate_scheduler/    ❌ 删除 - 与主 scheduler 重复
├── old_contract_wrapper/   ❌ 删除 - 已被新合同系统替代
└── unused_orchestrator/    ❌ 删除 - 从未被调用
```

**如何确认**: 运行 Fitness 测试，检查不可达模块报告

---

### 3.2 未校准的评分系统（暂时下线）

**删除原因**: 未被真实数据校准，不能用于生产决策

```
AI-Novel-Runtime/runtime/
├── reader_sim/             ⏸️ 暂时下线（保留代码，不调用）
├── commercial/             ⏸️ 暂时下线
└── quality_judge/          ⏸️ 暂时下线（保留确定性部分）
```

**处理方式**:
- 不删除代码
- 从生产流程中移除
- 标记为"诊断级"（可记录数据，不参与决策）
- 等待金样集校准后再激活

---

### 3.3 复杂的修订系统（暂时下线）

**删除原因**: 未证明净收益为正

```
AI-Novel-Runtime/runtime/
└── revision/
    ├── auto_revise.py      ⏸️ 暂时下线
    └── revision_loop.py    ⏸️ 暂时下线
```

**处理方式**:
- 保留接口
- 从默认流程移除
- 等待 A/B 测试证明净收益后再启用

---

### 3.4 导演控制循环（暂时下线）

**删除原因**: 增加复杂度，收益未验证

```
AI-Novel-Runtime/runtime/
└── director/
    ├── objective.py        ⏸️ 暂时下线
    ├── brief.py            ⏸️ 暂时下线
    └── session.py          ⏸️ 暂时下线
```

**处理方式**:
- 保留接口
- 不作为默认流程
- 等待 30 章基线稳定后再考虑激活

---

### 3.5 未使用的 Schema（清理）

**删除原因**: 没有消费者

```
AI-Novel-Standard/idl/
├── unused_entity_v1.yaml   ❌ 删除 - 从未被使用
└── deprecated_*.yaml       ❌ 删除 - 已废弃
```

**如何确认**:
1. 检查 Runtime 是否导入
2. 检查是否有测试覆盖
3. 两者都没有 = 可删除

---

### 3.6 历史文档腐烂（归档）

**删除原因**: 多份重叠历史文档造成混淆

```
ainovel/docs/
├── archive/                ✅ 保留归档目录
│   └── 2026-08-history/    ✅ 明确标记为历史
└── DEPRECATED_*.md         ❌ 删除 - 移入 archive/
```

**处理方式**:
- 不直接删除
- 移入 `docs/archive/`
- 添加 README 说明这些是历史资料，不是当前状态

---

## 四、实施顺序

### Phase 1（Month 1）

**重构**:
- ✅ Genre 系统（P0）
- ✅ Prompt 系统（P0）
- ✅ Genesis 流程（P1）

**删除**:
- ❌ 未接线的模块
- ⏸️ 暂时下线未校准评分系统

### Phase 2（Month 2）

**重构**:
- ✅ 生产编排（P1）
- ✅ 质量系统（P1）

**删除**:
- ⏸️ 暂时下线修订系统
- ⏸️ 暂时下线导演循环

### Phase 3（Month 3）

**保持稳定**:
- 不再重构
- 冻结配置
- 跑满 30 章

---

## 五、决策规则

### 保留的标准

- ✅ 有真实消费者
- ✅ 测试覆盖充分
- ✅ 架构思想正确
- ✅ 可直接复用

### 重构的标准

- 🔄 思路正确但实现有问题
- 🔄 耦合度高需要解耦
- 🔄 缺少关键能力（如题材约束）
- 🔄 需要适配新架构（Genre-First）

### 删除的标准

- ❌ 没有消费者（No Consumer = Stub）
- ❌ 重复实现
- ❌ 未被校准且不能用于决策
- ❌ 增加复杂度但收益未证明

### 暂时下线的标准

- ⏸️ 代码本身没问题
- ⏸️ 但需要外部条件（金样集、A/B 测试）
- ⏸️ 保留接口，等待激活

---

## 六、风险提示

### 过度删除风险

**症状**: 删掉后发现还有用

**缓解**:
- 先移动到 `deprecated/` 目录
- 运行完整测试套件
- 确认无引用后再删除

### 过度保留风险

**症状**: 舍不得删，结果保留一堆死代码

**缓解**:
- 严格执行"No Consumer = Stub"
- 每周检查不可达代码
- Code Review 拒绝保留无用代码

### 误删核心模块风险

**症状**: 删掉后系统崩溃

**缓解**:
- 删除前运行测试套件
- 保持 Git 提交粒度小
- 随时可回滚

---

## 七、验收标准

### 保留部分（40%）

- ✅ 所有保留模块的测试仍然通过
- ✅ 接口保持不变
- ✅ 可直接在新架构中使用

### 重构部分（30%）

- ✅ M1: Genre 系统重构完成
- ✅ M2: 生产编排解耦完成
- ✅ 测试覆盖率不降低

### 删除部分（30%）

- ✅ 无引用报错
- ✅ Fitness 测试不报告不可达模块
- ✅ 代码量降低 > 20%

---

**制定人**: Claude Opus 4.8  
**审核状态**: 待项目负责人审核  
**下一步**: 生成题材专用 Prompt 模板示例
