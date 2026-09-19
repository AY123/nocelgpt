# 📅 每日行动清单

**当前阶段**: M0完成，准备进入M1  
**当前日期**: 2026-09-18（周三）  
**下一里程碑**: M1 Week 1（2026-09-22 周一）  

---

## 本周剩余任务（9月18-21日）

### ✅ 今天（周三，9月18日）- 已完成

- [x] M0阶段所有任务
- [x] Git分支管理（v1.0-frozen, v2-refactor）
- [x] 15份架构文档归档
- [x] M1工作目录创建
- [x] 论文和项目研究模板创建
- [x] 所有文件提交到Git

**成果**: 6个Git commits，20份文档，M0圆满完成 ✅

---

### 📖 明天（周四，9月19日）

#### 上午（2小时）: 阅读FactTrack论文

**任务**:
- [ ] 阅读论文: https://arxiv.org/html/2407.16347v1
- [ ] 重点: Section 3（Validity Interval定义）
- [ ] 填写`docs/papers/READING_NOTES.md`的FactTrack部分
- [ ] 记录关键概念和对ANovel的启示

**产出**: FactTrack阅读笔记完成

---

#### 下午（2小时）: 阅读SCORE论文

**任务**:
- [ ] 阅读论文: https://arxiv.org/html/2503.23512v1
- [ ] 重点: Section 4-5（Temporal RAG + 量化结果）
- [ ] 填写`docs/papers/READING_NOTES.md`的SCORE部分
- [ ] 特别关注量化数据（+23.6%连贯性，-41.8%幻觉）

**产出**: SCORE阅读笔记完成

---

### 📖 周五（9月20日）

#### 上午（2小时）: 阅读ConStory-Bench论文

**任务**:
- [ ] 阅读论文: http://acl.ldc.upenn.edu/2026.findings-acl.410/
- [ ] 重点: Section 3-4（19种错误分类体系）
- [ ] 填写`docs/papers/READING_NOTES.md`的ConStory-Bench部分
- [ ] 记录5大类19种错误的详细定义

**产出**: ConStory-Bench阅读笔记完成

---

#### 下午（1.5小时）: 阅读DHO论文

**任务**:
- [ ] 阅读论文: https://arxiv.org/html/2412.13575v1
- [ ] 重点: Section 3（动态大纲调整机制）
- [ ] 填写`docs/papers/READING_NOTES.md`的DHO部分
- [ ] 理解动态调整触发条件和策略

**产出**: DHO阅读笔记完成

---

#### 晚上（30分钟）: 论文总结

**任务**:
- [ ] 回顾4篇论文的核心贡献
- [ ] 整理对ANovel的3个最重要启示
- [ ] 准备周六的项目研究

**产出**: 论文阅读周总结

---

### 💻 周六（9月21日）

#### 上午（1.5小时）: 克隆和浏览项目

**任务**:
```bash
# 创建研究目录
mkdir -p /tmp/ainovel-research
cd /tmp/ainovel-research

# 克隆HZ-KMNO项目
git clone https://github.com/HZ-KMNO/web-novel-writing-guidance-skill.git

# 克隆Novel-OS项目
git clone https://github.com/mrigankad/Novel-OS.git

# 浏览结构
cd web-novel-writing-guidance-skill
ls -la
cat README.md

cd ../Novel-OS
ls -la
cat README.md
```

**产出**: 两个项目克隆完成，目录结构理解

---

#### 下午（1.5小时）: 深度研究HZ-KMNO

**任务**:
- [ ] 研究Draft A/B/C工作流实现
- [ ] 研究章节蓝图（Chapter Blueprint）
- [ ] 查找优秀案例库相关代码
- [ ] 填写`docs/papers/PROJECT_RESEARCH_NOTES.md`的HZ-KMNO部分
- [ ] 摘录关键代码片段

**产出**: HZ-KMNO研究笔记完成

---

### 💻 周日（9月22日）

#### 上午（2小时）: 深度研究Novel-OS

**任务**:
- [ ] 研究SQLite持久化实现
- [ ] 研究Snapshot机制
- [ ] 查看表结构设计
- [ ] 填写`docs/papers/PROJECT_RESEARCH_NOTES.md`的Novel-OS部分
- [ ] 摘录关键代码片段

**产出**: Novel-OS研究笔记完成

---

#### 下午（1小时）: 项目研究总结 + M1准备

**任务**:
- [ ] 整理2个项目的可借鉴设计
- [ ] 回顾M1 Week 1的目标和任务
- [ ] 准备Genre核心设计的参考资料
- [ ] Git提交论文和项目研究笔记

**Git提交**:
```bash
git add docs/papers/
git commit -m "docs: complete paper reading and project research notes

Papers:
- FactTrack: Validity Interval mechanism
- SCORE: Temporal RAG + quantified improvements
- ConStory-Bench: 19 error types taxonomy
- DHO: Dynamic outline adjustment

Projects:
- HZ-KMNO: Draft A/B/C workflow, Chapter Blueprint
- Novel-OS: SQLite persistence, Snapshot mechanism

Key insights for ANovel V2 implementation documented.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**产出**: 准备周完成，准备进入M1

---

## M1 Week 1开始（9月23日-27日，下周）

### 周一（9月23日）

#### 全天: GenreConfig数据结构设计

**任务**:
- [ ] 创建`work/m1/design/genre/01_genre_config_design.md`
- [ ] 定义GenreConfig数据结构
- [ ] 定义GenreConstraints数据结构
- [ ] 设计都市题材示例配置
- [ ] 设计玄幻题材示例配置

**交付物**: GenreConfig设计文档完成

---

### 周二（9月24日）

#### 全天: GenreConstraints详细设计

**任务**:
- [ ] 完善GenreConstraints的约束验证逻辑
- [ ] 设计违规严重程度分级
- [ ] 设计例外规则机制
- [ ] 编写约束验证伪代码

**交付物**: GenreConstraints设计完成

---

### 周三（9月25日）

#### 全天: ProgressionModel抽象设计

**任务**:
- [ ] 创建`work/m1/design/genre/02_progression_model_design.md`
- [ ] 设计ProgressionModel抽象基类
- [ ] 设计WealthProgressionModel（都市）
- [ ] 设计PowerProgressionModel（玄幻）

**交付物**: ProgressionModel设计文档完成

---

### 周四（9月26日）

#### 全天: ProgressionModel验证逻辑

**任务**:
- [ ] 设计晋级验证逻辑（validate_transition）
- [ ] 设计合理性检查规则
- [ ] 编写验证伪代码
- [ ] 设计测试用例

**交付物**: ProgressionModel验证逻辑完成

---

### 周五（9月27日）

#### 全天: GenreRegistry + GenreDetector设计

**任务**:
- [ ] 创建`work/m1/design/genre/03_registry_detector_design.md`
- [ ] 设计GenreRegistry注册表
- [ ] 设计GenreDetector抽象接口
- [ ] 设计UrbanGenreDetector
- [ ] 设计XuanhuanGenreDetector

**交付物**: Registry和Detector设计完成

---

#### 晚上: Week 1总结

**任务**:
- [ ] 更新`work/m1/M1_PROGRESS.md`
- [ ] 标记Week 1所有任务为完成
- [ ] Git提交Week 1所有设计文档
- [ ] 准备Week 2的实现工作

**Git提交**:
```bash
git add work/m1/design/genre/
git commit -m "feat(m1): Genre core data structure design (Week 1)

Week 1 deliverables:
- GenreConfig and GenreConstraints design
- ProgressionModel abstract class design
- WealthProgressionModel and PowerProgressionModel design
- GenreRegistry and GenreDetector design

Design documents:
- 01_genre_config_design.md
- 02_progression_model_design.md
- 03_registry_detector_design.md

Next: Week 2 implementation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## 进度跟踪

### 本周（准备周）完成情况

**计划任务**: 6个
- [x] 周三: M0阶段完成
- [ ] 周四: FactTrack + SCORE论文
- [ ] 周五: ConStory-Bench + DHO论文
- [ ] 周六: HZ-KMNO项目研究
- [ ] 周日: Novel-OS项目研究
- [ ] 周日: Git提交研究笔记

**完成率**: 1/6（16%）

---

### M1 Week 1（下周）任务预览

**计划任务**: 5个设计文档
- [ ] GenreConfig设计
- [ ] GenreConstraints设计
- [ ] ProgressionModel设计
- [ ] 验证逻辑设计
- [ ] Registry + Detector设计

**目标**: 100%完成

---

## 📊 关键提醒

### 每日习惯

1. **早上**: 查看今日任务清单
2. **工作中**: 专注当前任务，避免跳跃
3. **晚上**: 更新进度，准备明日任务
4. **Git提交**: 每完成一个交付物就提交

### 质量标准

1. **论文阅读**: 不求快，求理解核心机制
2. **项目研究**: 重点关注可借鉴的设计
3. **设计文档**: 清晰、完整、可执行
4. **Git提交**: 清晰的commit message

### 时间管理

1. **专注时间**: 每个任务2小时连续工作
2. **休息时间**: 每2小时休息15分钟
3. **每日工作**: 4-6小时（不过度疲劳）
4. **周末工作**: 适度研究，保持精力

---

## 🎯 验收标准

### 准备周验收（本周日晚）

- [ ] 4篇论文阅读笔记完成
- [ ] 2个项目研究笔记完成
- [ ] 所有笔记已提交Git
- [ ] 准备好进入M1

### M1 Week 1验收（下周五晚）

- [ ] 3份设计文档完成
- [ ] 所有设计文档已提交Git
- [ ] M1_PROGRESS.md已更新
- [ ] 准备好进入Week 2实现

---

## 📞 帮助资源

### 遇到问题时

1. **查阅文档**: `docs/architecture-decisions/`
2. **查阅论文**: `docs/papers/READING_NOTES.md`
3. **查阅项目**: `docs/papers/PROJECT_RESEARCH_NOTES.md`
4. **查阅ADR**: `12_ARCHITECTURE_DECISION_RECORD_PART1-3.md`

### 需要clarification时

- 回顾架构决策记录
- 查看可执行指南
- 参考论文原文

---

**制定人**: Claude Opus 4.8  
**制定日期**: 2026-09-18  
**下次更新**: 每日更新（标记完成任务）  
**状态**: ✅ 准备就绪，按计划推进！
