# M1 阶段进度跟踪

**阶段**: M1 - Genre + 5个核心技术设计  
**时长**: 6周（2026-09-22 至 2026-11-02）  
**当前周**: Week 0（准备周）  
**状态**: 🟡 准备中  

---

## 📅 Week 1-2: Genre核心重构（9月22日-10月5日）

### Week 1: Genre数据结构设计

**目标**: 完成GenreConfig、GenreConstraints、ProgressionModel的完整设计

#### Day 1-2: GenreConfig + GenreConstraints
- [ ] GenreConfig数据结构设计
- [ ] GenreConstraints数据结构设计
- [ ] 示例配置（都市/玄幻）定义
- [ ] 约束验证逻辑设计

**交付物**: `work/m1/design/genre/01_genre_config_design.md`

#### Day 3-4: ProgressionModel抽象
- [ ] ProgressionModel抽象基类设计
- [ ] WealthProgressionModel（都市）设计
- [ ] PowerProgressionModel（玄幻）设计
- [ ] 晋级验证逻辑设计

**交付物**: `work/m1/design/genre/02_progression_model_design.md`

#### Day 5: GenreRegistry + GenreDetector
- [ ] GenreRegistry设计
- [ ] GenreDetector抽象设计
- [ ] UrbanGenreDetector设计
- [ ] XuanhuanGenreDetector设计

**交付物**: `work/m1/design/genre/03_registry_detector_design.md`

---

### Week 2: Genre实现 + 原型

#### Day 1-3: 核心实现
- [ ] GenreConfig实现（runtime/genre/config.py）
- [ ] ProgressionModel实现（runtime/genre/progression.py）
- [ ] GenreRegistry实现（runtime/genre/registry.py）
- [ ] GenreDetector实现（runtime/genre/detector.py）

#### Day 4-5: 单元测试 + 集成测试
- [ ] GenreConfig测试
- [ ] ProgressionModel测试（都市/玄幻）
- [ ] GenreDetector测试（准确率>90%）
- [ ] 题材隔离测试（10个用例）

**交付物**: `AI-Novel-Runtime/runtime/genre/` 完整模块

---

## 📅 Week 3: Genre + 核心技术设计（10月6日-10月12日）

### Genesis流程改造

#### Day 1-2: Genesis题材感知
- [ ] Genesis流程分析
- [ ] 题材检测集成点设计
- [ ] 约束注入机制设计
- [ ] 题材专用分析器设计

**交付物**: `work/m1/design/genre/04_genesis_integration_design.md`

---

### Validity Interval机制设计

#### Day 3-4: Validity Interval设计
- [ ] Fact数据结构扩展设计
  - validity_start: int
  - validity_end: Optional[int]
  - superseded_by: Optional[str]
  - supersede_reason: str
- [ ] 有效性检查逻辑设计
- [ ] 矛盾检测改良设计
- [ ] 合法变化vs非法矛盾判定

**交付物**: `work/m1/design/validity-interval/01_validity_interval_design.md`

---

### 错误分类体系定义

#### Day 5: 19种错误类型定义
- [ ] Factual错误（3种）
- [ ] Temporal错误（4种）
- [ ] Character错误（5种）
- [ ] World错误（4种）
- [ ] Plot错误（5种）
- [ ] 错误严重程度定义
- [ ] 检测器接口设计

**交付物**: `work/m1/design/error-taxonomy/01_error_taxonomy_definition.md`

---

## 📅 Week 4: 核心技术详细设计（10月13日-10月19日）

### Draft A/B/C工作流设计

#### Day 1-2: 三稿制工作流
- [ ] Draft A（快速初稿）设计
- [ ] Draft B（改进版）设计
- [ ] Draft C（精修版）设计
- [ ] 质量判断标准设计
- [ ] 成本控制策略设计

**交付物**: `work/m1/design/pipeline/01_draft_abc_workflow_design.md`

---

### Temporal RAG架构设计

#### Day 3-4: Temporal RAG设计
- [ ] RAG检索架构设计
- [ ] 时间对齐机制设计
- [ ] 事实向量化方案
- [ ] 时间衰减权重设计
- [ ] 上下文注入方案

**交付物**: `work/m1/design/pipeline/02_temporal_rag_design.md`

---

### 情感一致性检查设计

#### Day 5: 情感一致性设计
- [ ] 情感状态定义
- [ ] 情感转换规则设计
- [ ] 合法转换判定逻辑
- [ ] 重大事件识别

**交付物**: `work/m1/design/pipeline/03_emotional_consistency_design.md`

---

## 📅 Week 5-6: 题材隔离测试 + 原型（10月20日-11月2日）

### Week 5: 题材隔离测试（10+用例）

#### 都市题材测试用例（5个）
- [ ] 测试用例1: 都市重生创业（不生成修炼）
- [ ] 测试用例2: 都市商战（不生成境界）
- [ ] 测试用例3: 都市职场（不生成法宝）
- [ ] 测试用例4: 都市投资（不生成灵气）
- [ ] 测试用例5: 都市豪门（不生成宗门）

#### 玄幻题材测试用例（5个）
- [ ] 测试用例6: 玄幻废材流（不生成公司）
- [ ] 测试用例7: 玄幻宗门（不生成股票）
- [ ] 测试用例8: 玄幻修炼（不生成商战）
- [ ] 测试用例9: 玄幻异界（不生成职场）
- [ ] 测试用例10: 玄幻炼丹（不生成投资）

**交付物**: `work/m1/tests/genre_isolation_tests.py`

---

### Week 6: 核心技术原型

#### Day 1-2: Validity Interval原型
- [ ] Fact扩展实现
- [ ] 有效性检查实现
- [ ] 矛盾检测改良实现
- [ ] 原型测试

**交付物**: `work/m1/prototype/validity_interval_prototype.py`

#### Day 3-4: ConStory-Checker原型
- [ ] 错误检测器接口实现
- [ ] 实现3-5个核心Checker
  - EntityAttributeChecker
  - TimelineChecker
  - PersonalityChecker
- [ ] 原型测试

**交付物**: `work/m1/prototype/constory_checker_prototype.py`

#### Day 5: M1集成验证
- [ ] Genre系统集成测试
- [ ] 题材隔离测试通过
- [ ] 原型功能验证
- [ ] M1验收报告

**交付物**: `work/m1/M1_ACCEPTANCE_REPORT.md`

---

## ✅ M1验收标准

### 功能验收
- [ ] 题材检测准确率 > 90%
- [ ] 都市不生成修炼（5个测试用例全部通过）
- [ ] 玄幻不生成商业（5个测试用例全部通过）
- [ ] GenreConfig、GenreConstraints、ProgressionModel完整实现
- [ ] GenreRegistry、GenreDetector可用

### 设计验收
- [ ] 5个核心技术设计文档完成
  1. Validity Interval设计
  2. 19种错误类型定义
  3. Draft A/B/C工作流设计
  4. Temporal RAG设计
  5. 情感一致性设计

### 原型验收
- [ ] Validity Interval原型可运行
- [ ] ConStory-Checker原型可运行
- [ ] 原型演示通过

### 质量验收
- [ ] 所有设计文档经过Review
- [ ] 所有代码有单元测试
- [ ] 测试覆盖率 > 80%
- [ ] 无Critical Bug

---

## 📊 进度监控

### 当前状态
- **完成度**: 0%
- **当前任务**: 准备阶段
- **风险**: 无
- **阻塞**: 无

### 下周计划
- Week 1 开始（2026-09-22）
- Genre核心数据结构设计

---

## 📝 每周总结

### Week 0（准备周，2026-09-15至9-21）
- [x] V1分支冻结
- [x] V2分支创建
- [x] 架构文档归档
- [x] M1工作目录创建
- [ ] 核心论文阅读（进行中）
- [ ] 核心项目研究（进行中）

### Week 1（待更新）
### Week 2（待更新）
### Week 3（待更新）
### Week 4（待更新）
### Week 5（待更新）
### Week 6（待更新）

---

**最后更新**: 2026-09-18  
**更新人**: Claude Opus 4.8  
**下次更新**: Week 1 Day 1（2026-09-22）
