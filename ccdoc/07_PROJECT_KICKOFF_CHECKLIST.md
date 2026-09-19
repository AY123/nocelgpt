# ANovel V2 项目启动清单

**版本**: v1.0  
**制定日期**: 2026-09-18  
**适用阶段**: M0 准备阶段 → M1 开始前  

---

## 一、立即行动（今天完成）

### 1.1 Git 仓库准备

```bash
# 进入项目目录
cd /Users/angyang/Documents/AI/ANovelOS/ainovel

# 1. 冻结当前主分支
git tag v1.0-genre-broken-baseline
git push origin v1.0-genre-broken-baseline

# 2. 创建重构分支
git checkout -b refactor/v2-genre-first
git push -u origin refactor/v2-genre-first

# 3. 确认分支状态
git branch  # 应该显示 * refactor/v2-genre-first
git log --oneline -5
```

### 1.2 文档整理

```bash
# 1. 确认 ccdoc 文档已生成
ls -lh /Users/angyang/Documents/AI/ANovelOS/ccdoc/

# 应该看到以下文件：
# 00_PROJECT_REFACTOR_ASSESSMENT.md
# 01_GENRE_SYSTEM_ARCHITECTURE_DESIGN.md
# 02_STRATEGIC_REFACTOR_ROADMAP.md
# 03_KEEP_REFACTOR_DELETE_CHECKLIST.md
# 04_GENRE_SPECIFIC_PROMPT_TEMPLATES.md
# 05_V1_LESSONS_LEARNED.md
# 06_MILESTONE_DEFINITIONS.md
# 07_PROJECT_KICKOFF_CHECKLIST.md (本文件)

# 2. 创建 README 索引
cat > /Users/angyang/Documents/AI/ANovelOS/ccdoc/README.md << 'EOF'
# ANovel V2 架构设计文档

本目录包含 ANovel V2 重构的完整架构设计文档。

## 文档列表

1. **00_PROJECT_REFACTOR_ASSESSMENT.md** - 项目重构评估报告
   - 评估现有项目状态
   - 战略重构 vs 完全重建对比
   - ROI 分析

2. **01_GENRE_SYSTEM_ARCHITECTURE_DESIGN.md** - Genre 系统架构设计
   - GenreConfig、GenreConstraints 数据模型
   - ProgressionModel 抽象（Power/Wealth/Tech）
   - GenreRegistry 注册表

3. **02_STRATEGIC_REFACTOR_ROADMAP.md** - 战略重构路线图
   - 3 个月实施计划
   - M1/M2/M3 里程碑定义
   - Go/No-Go 决策点

4. **03_KEEP_REFACTOR_DELETE_CHECKLIST.md** - 保留-重构-删除清单
   - 40% 保留（直接复用）
   - 30% 重构（改造）
   - 30% 删除（移除）

5. **04_GENRE_SPECIFIC_PROMPT_TEMPLATES.md** - 题材专用 Prompt 模板
   - 都市 Outline/Chapter 模板
   - 玄幻 Outline/Chapter 模板
   - 约束注入机制

6. **05_V1_LESSONS_LEARNED.md** - V1 经验教训总结
   - 必须继承的成功经验
   - 不得重演的失败教训
   - 20 条核心原则

7. **06_MILESTONE_DEFINITIONS.md** - 实施里程碑定义
   - M1/M2/M3 详细验收标准
   - Go/No-Go 决策规则
   - 里程碑跟踪机制

8. **07_PROJECT_KICKOFF_CHECKLIST.md** - 项目启动清单
   - 立即行动项
   - 准备工作
   - 团队对齐

## 阅读顺序

**项目负责人**:
1. 00_PROJECT_REFACTOR_ASSESSMENT.md（了解评估结论）
2. 02_STRATEGIC_REFACTOR_ROADMAP.md（了解实施路线）
3. 06_MILESTONE_DEFINITIONS.md（了解验收标准）

**架构师/开发者**:
1. 01_GENRE_SYSTEM_ARCHITECTURE_DESIGN.md（核心架构）
2. 03_KEEP_REFACTOR_DELETE_CHECKLIST.md（具体改动）
3. 04_GENRE_SPECIFIC_PROMPT_TEMPLATES.md（模板设计）
4. 05_V1_LESSONS_LEARNED.md（避免重蹈覆辙）

**新加入成员**:
1. 05_V1_LESSONS_LEARNED.md（理解历史背景）
2. 00_PROJECT_REFACTOR_ASSESSMENT.md（理解当前状态）
3. 02_STRATEGIC_REFACTOR_ROADMAP.md（理解实施计划）

## 版本历史

- v1.0 (2026-09-18): 初始版本，完整架构设计
EOF
```

### 1.3 阅读必读文档

```bash
# 1. 阅读 Project Constitution（V2 指导原则）
open /Users/angyang/Documents/AI/ANovelOS/ANovel_V2_Project_Constitution_v1.0/PROJECT_CONSTITUTION.md

# 或使用文本编辑器
# 重点关注：
# - Section 5: Core Principles (P-001 到 P-020)
# - Section 6: V1 Lessons (LESSON-V1-001 到 LESSON-V1-012)
# - Section 11: Core Invariants (INV-001 到 INV-015)
# - Section 12: Architecture Prohibitions (PROHIBIT-001 到 PROHIBIT-014)

# 2. 阅读本次生成的核心文档
open /Users/angyang/Documents/AI/ANovelOS/ccdoc/00_PROJECT_REFACTOR_ASSESSMENT.md
open /Users/angyang/Documents/AI/ANovelOS/ccdoc/02_STRATEGIC_REFACTOR_ROADMAP.md
open /Users/angyang/Documents/AI/ANovelOS/ccdoc/05_V1_LESSONS_LEARNED.md
```

---

## 二、准备工作（本周完成）

### 2.1 环境准备

```bash
# 1. 确认 Python 版本
python3 --version  # 建议 Python 3.9+

# 2. 确认依赖
cd /Users/angyang/Documents/AI/ANovelOS/ainovel/AI-Novel-Runtime
pip install -r requirements.txt

# 3. 运行现有测试（了解基线）
pytest tests/ --ignore=tests/test_llm_with_env.py -q

# 记录测试结果（作为对比基准）
# 预期：405+ passed, 一些 failed（这是 V1 的状态）
```

### 2.2 代码审查准备

```bash
# 1. 统计当前代码规模
cd /Users/angyang/Documents/AI/ANovelOS/ainovel/AI-Novel-Runtime

# Python 文件统计
find . -name "*.py" | wc -l

# 代码行数统计
find . -name "*.py" -exec wc -l {} + | tail -1

# 2. 识别待删除模块（根据 Fitness 测试）
python -m pytest tests/test_fitness.py -v

# 记录不可达模块列表
```

### 2.3 保留-重构-删除标记

```bash
# 创建工作目录
mkdir -p /Users/angyang/Documents/AI/ANovelOS/ainovel/AI-Novel-Runtime/docs/refactor

# 生成模块清单
cat > docs/refactor/module_inventory.md << 'EOF'
# 模块清单

## ✅ 保留（40%）

- [ ] AI-Novel-Standard/
- [ ] runtime/pipeline/
- [ ] runtime/registry/
- [ ] runtime/memory/state.py
- [ ] runtime/mint/
- [ ] runtime/derived.py
- [ ] runtime/llm/

## 🔄 重构（30%）

- [ ] runtime/outline/ → runtime/genre/ + runtime/genesis/
- [ ] runtime/serialize/loop.py → runtime/production/
- [ ] runtime/prompt/
- [ ] runtime/qa/

## ❌ 删除（30%）

- [ ] （待 Fitness 测试识别）
- [ ] （未接线模块）
- [ ] （未校准评分系统 - 暂时下线）

## ⏸️ 暂时下线

- [ ] runtime/reader_sim/
- [ ] runtime/commercial/
- [ ] runtime/director/
EOF
```

---

## 三、团队对齐（本周完成）

### 3.1 召开启动会议

**会议议程**:

1. **项目背景**（10 分钟）
   - V1 的成功与失败
   - 为什么需要重构
   - 为什么不推倒重来

2. **核心问题**（10 分钟）
   - Genre 系统架构缺陷
   - 都市写成奇幻的根本原因
   - Power System 错误通用化

3. **战略方向**（15 分钟）
   - 战略重构 vs 完全重建
   - 保留-重构-删除（40%-30%-30%）
   - 3 个月实施计划

4. **里程碑与验收**（15 分钟）
   - M1: Genre 系统重构（Month 1）
   - M2: 生产流程优化（Month 2）
   - M3: 30 章基线建立（Month 3）- Go/No-Go 决策点
   - M3 不通过 = 不继续投入

5. **角色分工**（10 分钟）
   - 架构师：Genre 核心设计
   - 开发者：实现与测试
   - 产品：人工评审标准
   - 项目管理：进度跟踪

6. **Q&A**（10 分钟）

**会议产出**:
- [ ] 团队理解重构战略
- [ ] 角色分工明确
- [ ] M1 任务分配完成

### 3.2 文档共享

```bash
# 1. 将 ccdoc 文档发送给团队
# 建议使用 Google Docs / Notion / 内部 Wiki

# 2. 必读文档清单（团队成员）
# - 00_PROJECT_REFACTOR_ASSESSMENT.md
# - 02_STRATEGIC_REFACTOR_ROADMAP.md
# - 05_V1_LESSONS_LEARNED.md

# 3. 可选文档清单（深入了解）
# - 01_GENRE_SYSTEM_ARCHITECTURE_DESIGN.md
# - 03_KEEP_REFACTOR_DELETE_CHECKLIST.md
# - 04_GENRE_SPECIFIC_PROMPT_TEMPLATES.md
# - 06_MILESTONE_DEFINITIONS.md
```

### 3.3 工具准备

**进度跟踪**:
- [ ] 创建看板（Trello / Jira / GitHub Projects）
- [ ] 列出 M1 所有任务
- [ ] 分配任务到具体人员
- [ ] 设定 M1 验收日期（4 周后）

**文档协作**:
- [ ] 设置文档仓库（Google Docs / Notion）
- [ ] 共享 ccdoc 文档
- [ ] 建立变更记录机制

**沟通渠道**:
- [ ] 建立项目群（微信/Slack/Discord）
- [ ] 设定每周五检查点时间
- [ ] 设定 M1 验收会议时间

---

## 四、M1 任务分解（准备进入实施）

### Week 1: Genre 核心数据结构

**任务**:
- [ ] 创建 `runtime/genre/` 目录
- [ ] 实现 `core.py`（GenreConfig、GenreConstraints）
- [ ] 实现 `progression.py`（ProgressionModel 抽象）
- [ ] 实现 `registry.py`（GenreRegistry）
- [ ] 单元测试

**负责人**: [架构师/核心开发者]  
**截止日期**: Week 1 结束

### Week 2: 进阶模型实现

**任务**:
- [ ] 创建 `runtime/genre/progression/` 目录
- [ ] 实现 `power.py`（PowerProgressionModel）
- [ ] 实现 `wealth.py`（WealthProgressionModel）
- [ ] 实现 `tech.py`（TechProgressionModel）
- [ ] 单元测试

**负责人**: [开发者]  
**截止日期**: Week 2 结束

### Week 3: 题材配置与 Genesis 集成

**任务**:
- [ ] 创建 `runtime/genre/configs/` 目录
- [ ] 实现 `urban.py`（都市完整配置）
- [ ] 实现 `xuanhuan.py`（玄幻完整配置）
- [ ] 实现题材检测器
- [ ] 改造 Genesis 流程（题材感知）
- [ ] 集成测试

**负责人**: [架构师 + 开发者]  
**截止日期**: Week 3 结束

### Week 4: 题材隔离测试与验收

**任务**:
- [ ] 编写 10+ 题材检测测试用例
- [ ] 编写 5+ 都市题材隔离测试
- [ ] 编写 5+ 玄幻题材隔离测试
- [ ] 端到端集成测试
- [ ] 准备 M1 验收报告

**负责人**: [QA + 开发者]  
**截止日期**: Week 4 结束

---

## 五、M1 验收准备

### 验收前自查清单

```bash
# 1. 运行完整测试套件
cd /Users/angyang/Documents/AI/ANovelOS/ainovel/AI-Novel-Runtime
pytest tests/ -v

# 2. 运行题材隔离测试
pytest tests/test_genre_isolation.py -v

# 3. 检查题材检测准确率
python -m tests.test_genre_detection

# 4. 生成测试报告
pytest tests/ --html=report.html --self-contained-html

# 5. 代码覆盖率检查
pytest tests/ --cov=runtime/genre --cov-report=html
```

### M1 验收会议准备

**准备材料**:
1. [ ] M1 验收报告（根据模板填写）
2. [ ] 测试结果报告（HTML）
3. [ ] 题材隔离测试演示
4. [ ] 代码 Review 总结
5. [ ] 遗留问题列表

**参会人员**:
- 项目负责人
- 架构师
- 开发者
- QA

**决策结果**:
- [ ] ✅ Go - 进入 M2
- [ ] ❌ No-Go - 延长 M1，修复问题

---

## 六、风险提示与应对

### 风险 1: 范围蔓延

**症状**: Week 2 就开始讨论"顺便把科幻题材也做了"

**应对**:
- M1 只做都市/玄幻
- 科幻留到 M1 之后
- 严格控制范围

### 风险 2: 完美主义

**症状**: Week 3 了还在优化 Week 1 的代码

**应对**:
- 通过单元测试就行
- 不追求完美代码
- 先完成 M1，后续再优化

### 风险 3: 沟通不足

**症状**: 团队成员理解不一致

**应对**:
- 每周五检查点（强制）
- 文档更新及时同步
- 遇到疑问立即沟通

### 风险 4: 测试回归

**症状**: 新代码破坏现有测试

**应对**:
- 每次提交前运行测试
- CI/CD 自动检查
- 红色测试当天修复

---

## 七、成功标准

### M0 阶段成功标志

- [x] V1 主分支已冻结（`v1.0-genre-broken-baseline`）
- [x] 重构分支已创建（`refactor/v2-genre-first`）
- [x] 架构文档已生成（8 份）
- [ ] 团队已对齐战略方向
- [ ] M1 任务已分配
- [ ] 验收会议已安排

### 准备进入 M1 的标志

- [ ] 所有团队成员理解重构战略
- [ ] 所有团队成员读过必读文档
- [ ] M1 任务分解完成
- [ ] 工具与环境准备就绪
- [ ] 沟通渠道建立完成

---

## 八、检查清单总结

### 今天完成（Day 1）

- [ ] Git 仓库冻结与分支创建
- [ ] 文档确认与 README 生成
- [ ] 阅读 Project Constitution
- [ ] 阅读核心架构文档

### 本周完成（Week 1）

- [ ] 环境准备与依赖安装
- [ ] 现有测试基线确认
- [ ] 模块清单标记（保留/重构/删除）
- [ ] 召开启动会议
- [ ] 团队文档共享
- [ ] 工具与看板准备
- [ ] M1 任务分解与分配

### 下周开始（Week 2）

- [ ] 正式进入 M1 实施
- [ ] Genre 核心数据结构开发
- [ ] 每周五检查点会议

---

## 九、联系方式

如有疑问，请联系：

**项目负责人**: [姓名] - [联系方式]  
**架构师**: [姓名] - [联系方式]  
**文档负责人**: Claude Opus 4.8（通过项目负责人联系）

---

## 十、最后的话

**你现在站在一个关键的决策点**：

- ✅ 你已经深度分析了现有项目
- ✅ 你识别了核心问题（Genre 系统架构缺陷）
- ✅ 你制定了正确的战略（战略重构，而非推倒重来）
- ✅ 你有完整的实施路线图（3 个月 M1/M2/M3）
- ✅ 你有明确的验收标准（M3 Go/No-Go 决策点）

**接下来需要的是执行纪律**：

1. **不范围蔓延** - M1 只做 Genre，不添加其他功能
2. **不降低标准** - M3 前 3 章 < 7 分 = 不通过
3. **不完美主义** - 通过测试就行，不追求完美
4. **不跳过验证** - 人工盲评不能省

**记住 Project Constitution 的最终测试**：

> 它是否让系统更稳定地生产一部长篇、类型正确、事实一致、人物可信、剧情持续推进、可恢复、可验证，并最终让真实读者愿意继续阅读和付费的原创商业小说？

**如果答案是"是"，你就在正确的道路上。**

**祝项目成功！**

---

**制定人**: Claude Opus 4.8  
**状态**: 项目启动清单完成  
**下一步**: 执行 M0 检查清单，准备进入 M1
