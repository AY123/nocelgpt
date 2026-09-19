# ANovel V2 项目实施执行计划

**启动日期**: 2026-09-18  
**目标**: 按照架构决策记录完整实施，18周后通过M3验收  
**当前阶段**: M0（项目准备）  

---

## 🎯 执行总览

### 时间线

```
M0: 项目准备（1-2天）     ← 当前位置
  ↓
M1: Genre + 5个核心技术设计（6周）
  ↓
M2: 生产流程 + 5个核心技术实现（8周）
  ↓
M3: 30章基线验证（4周）
  ↓
Go/No-Go决策
```

### 核心目标

**M3成功标准**（18周后）:
- ✅ 都市/玄幻各30章完整生产
- ✅ 前3章盲评 > 7/10
- ✅ 30章 0 重大缺陷
- ✅ 成本 < $0.75/30章

---

## 📋 M0阶段：项目准备（1-2天）

### Day 1: Git分支管理 + 文档归档

#### Task 0.1: 冻结V1分支

```bash
# 当前main分支 = V1
cd /Users/angyang/Documents/AI/ANovelOS/ainovel

# 为V1打标签
git tag -a v1.0-frozen -m "V1 frozen before V2 refactor"

# 创建V1备份分支
git branch v1-backup
```

**验收**: 
- ✅ v1.0-frozen标签存在
- ✅ v1-backup分支存在

---

#### Task 0.2: 创建V2重构分支

```bash
# 从main创建v2-refactor分支
git checkout -b v2-refactor

# 推送到远程（如果有）
git push origin v2-refactor
```

**验收**:
- ✅ v2-refactor分支存在
- ✅ 当前工作在v2-refactor分支

---

#### Task 0.3: 归档架构文档

```bash
# 创建docs目录
mkdir -p docs/architecture-decisions

# 复制所有架构文档
cp /Users/angyang/Documents/AI/ANovelOS/ccdoc/*.md docs/architecture-decisions/

# 添加到Git
git add docs/
git commit -m "docs: add architecture decision records and planning documents

- 15 complete architecture documents (12,691 lines)
- 30+ project research analysis
- 15+ academic paper reviews
- 22 core architecture decisions
- Complete M1-M3 implementation roadmap

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**:
- ✅ docs/architecture-decisions/ 包含15份文档
- ✅ 已提交到Git

---

#### Task 0.4: 创建M1工作目录

```bash
# 创建M1阶段目录结构
mkdir -p work/m1/{design,prototype,tests}
mkdir -p work/m1/design/{genre,validity-interval,error-taxonomy,prompt}

# 创建M1跟踪文件
cat > work/m1/M1_PROGRESS.md << 'EOF'
# M1 阶段进度跟踪

**阶段**: M1 - Genre + 5个核心技术设计  
**时长**: 6周  
**状态**: 🟡 未开始  

## Week 1-2: Genre核心重构

- [ ] GenreConfig数据结构
- [ ] GenreConstraints数据结构
- [ ] ProgressionModel抽象基类
- [ ] WealthProgressionModel（都市）
- [ ] PowerProgressionModel（玄幻）

## Week 3: Genre + 核心技术设计

- [ ] Genesis流程题材感知改造
- [ ] Validity Interval机制设计
- [ ] 错误分类体系定义（19种）

## Week 4: 核心技术详细设计

- [ ] Draft A/B/C工作流设计
- [ ] Temporal RAG架构设计
- [ ] 情感一致性检查设计

## Week 5-6: 题材隔离测试 + 原型

- [ ] 题材隔离测试（10+用例）
- [ ] Validity Interval原型
- [ ] ConStory-Checker原型

## M1验收标准

- [ ] 题材检测准确率 > 90%
- [ ] 都市不生成修炼（5个测试用例）
- [ ] 玄幻不生成商业（5个测试用例）
- [ ] 5个核心技术设计文档完成
- [ ] Validity Interval原型可运行
- [ ] ConStory-Checker原型可运行
EOF

git add work/
git commit -m "chore: create M1 work directory structure

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**:
- ✅ work/m1/ 目录结构完整
- ✅ M1_PROGRESS.md 存在

---

### Day 2: 核心论文阅读 + 项目研究

#### Task 0.5: 下载核心论文

**必读论文（4篇）**:

1. **FactTrack** - Time-Aware World State Tracking
   - URL: https://arxiv.org/html/2407.16347v1
   - 重点: Section 3（Validity Interval定义）
   - 时间: 2小时

2. **SCORE** - Story Coherence and Retrieval Enhancement
   - URL: https://arxiv.org/html/2503.23512v1
   - 重点: Section 4（Temporal RAG）、Section 5（结果）
   - 时间: 2小时

3. **ConStory-Bench** - Consistency Bugs in Long Story
   - URL: http://acl.ldc.upenn.edu/2026.findings-acl.410/
   - 重点: Section 3（错误分类体系）、Section 4（检测器）
   - 时间: 2小时

4. **DHO** - Dynamic Hierarchical Outlining
   - URL: https://arxiv.org/html/2412.13575v1
   - 重点: Section 3（动态调整机制）
   - 时间: 1.5小时

**行动**:
```bash
# 创建论文目录
mkdir -p docs/papers

# 创建论文笔记模板
cat > docs/papers/READING_NOTES.md << 'EOF'
# 核心论文阅读笔记

## FactTrack - Time-Aware World State Tracking

**阅读日期**: 
**状态**: 🟡 待读

### 核心贡献
- Validity Interval（有效性区间）机制

### 关键发现
（阅读后填写）

### 对ANovel的启示
（阅读后填写）

---

## SCORE - Story Coherence and Retrieval Enhancement

**阅读日期**: 
**状态**: 🟡 待读

### 核心贡献
- Temporal RAG
- 量化指标：连贯性+23.6%，幻觉-41.8%，情感一致性89.7%

### 关键发现
（阅读后填写）

### 对ANovel的启示
（阅读后填写）

---

## ConStory-Bench - Consistency Bugs

**阅读日期**: 
**状态**: 🟡 待读

### 核心贡献
- 5大类19种错误类型体系
- ConStory-Checker自动检测

### 关键发现
（阅读后填写）

### 对ANovel的启示
（阅读后填写）

---

## DHO - Dynamic Hierarchical Outlining

**阅读日期**: 
**状态**: 🟡 待读

### 核心贡献
- 动态大纲调整机制
- 时间知识图谱

### 关键发现
（阅读后填写）

### 对ANovel的启示
（阅读后填写）
EOF

git add docs/papers/
git commit -m "docs: add paper reading notes template

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**:
- ✅ READING_NOTES.md存在
- ✅ 4篇论文链接可访问

---

#### Task 0.6: 研究核心项目

**必研究项目（2个）**:

1. **HZ-KMNO/web-novel-writing-guidance-skill**
   - URL: https://github.com/HZ-KMNO/web-novel-writing-guidance-skill
   - 重点: Draft A/B/C工作流、章节蓝图
   - 时间: 3小时

2. **Novel-OS**
   - URL: https://github.com/mrigankad/Novel-OS
   - 重点: SQLite持久化、Snapshot机制
   - 时间: 2小时

**行动**:
```bash
# 克隆到临时目录研究
mkdir -p /tmp/ainovel-research
cd /tmp/ainovel-research

# 克隆HZ-KMNO项目
git clone https://github.com/HZ-KMNO/web-novel-writing-guidance-skill.git

# 克隆Novel-OS项目
git clone https://github.com/mrigankad/Novel-OS.git

# 创建研究笔记
cat > /Users/angyang/Documents/AI/ANovelOS/ainovel/docs/papers/PROJECT_RESEARCH_NOTES.md << 'EOF'
# 核心项目研究笔记

## HZ-KMNO - 中文网文写作指导

**研究日期**: 
**状态**: 🟡 待研究

### 核心特点
- Draft A/B/C工作流
- 章节蓝图（Chapter Blueprint）
- 优秀案例方法

### 关键代码位置
（研究后填写）

### 可借鉴设计
（研究后填写）

---

## Novel-OS

**研究日期**: 
**状态**: 🟡 待研究

### 核心特点
- SQLite持久化层
- Snapshot机制
- 5层架构

### 关键代码位置
（研究后填写）

### 可借鉴设计
（研究后填写）
EOF

cd /Users/angyang/Documents/AI/ANovelOS/ainovel
git add docs/papers/PROJECT_RESEARCH_NOTES.md
git commit -m "docs: add project research notes template

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

**验收**:
- ✅ 项目克隆成功
- ✅ PROJECT_RESEARCH_NOTES.md存在

---

### M0验收清单

- [ ] V1分支已冻结（v1.0-frozen标签）
- [ ] V2重构分支已创建（v2-refactor）
- [ ] 15份架构文档已归档到docs/
- [ ] M1工作目录已创建
- [ ] 4篇核心论文链接已确认
- [ ] 2个核心项目已克隆
- [ ] 阅读笔记模板已创建

---

## 📅 M1阶段：Genre + 5个核心技术设计（6周）

### Week 1: Genre核心数据结构（2026-09-22开始）

#### Day 1-2: GenreConfig设计

**文件**: `work/m1/design/genre/01_genre_config_design.md`

**任务**:
1. 定义GenreConfig数据结构
2. 定义GenreConstraints数据结构
3. 设计GenreRegistry
4. 设计GenreDetector抽象

**交付物**:
```python
# AI-Novel-Runtime/runtime/genre/config.py
@dataclass
class GenreConfig:
    genre_id: str
    genre_name: str
    constraints: GenreConstraints
    progression_model: Type[ProgressionModel]
    prompt_templates: Dict[str, str]
    detector: GenreDetector
    
@dataclass
class GenreConstraints:
    allowed_elements: List[str]
    forbidden_elements: List[str]
    allowed_scenes: List[str]
    forbidden_scenes: List[str]
    violation_severity: Dict[str, str]
```

**验收**:
- [ ] 数据结构设计文档完成
- [ ] 示例配置（都市/玄幻）定义
- [ ] 单元测试计划

---

#### Day 3-4: ProgressionModel抽象

**文件**: `work/m1/design/genre/02_progression_model_design.md`

**任务**:
1. 设计ProgressionModel抽象基类
2. 设计WealthProgressionModel（都市）
3. 设计PowerProgressionModel（玄幻）
4. 设计晋级合理性验证

**交付物**:
```python
# AI-Novel-Runtime/runtime/genre/progression.py
class ProgressionModel(ABC):
    @abstractmethod
    def get_tiers(self) -> List[str]:
        pass
    
    @abstractmethod
    def validate_transition(self, from_tier, to_tier, context) -> bool:
        pass

class WealthProgressionModel(ProgressionModel):
    def get_tiers(self):
        return ["贫困线", "温饱", "小康", "中产", "富裕", "富豪"]
```

**验收**:
- [ ] 抽象基类设计完成
- [ ] 都市/玄幻实现设计完成
- [ ] 验证逻辑设计完成

---

#### Day 5: GenreRegistry + GenreDetector

**文件**: `work/m1/design/genre/03_registry_detector_design.md`

**任务**:
1. 设计GenreRegistry（注册表）
2. 设计GenreDetector（题材检测）
3. 设计约束验证流程

**验收**:
- [ ] Registry设计完成
- [ ] Detector设计完成
- [ ] 集成流程设计完成

---

### Week 2: Genre实现 + 测试

**详细计划**: （周一开始时展开）

---

### Week 3-6: 5个核心技术设计

**详细计划**: （根据Week 1-2进度展开）

---

## 🚀 立即开始：M0 Day 1执行

让我现在就帮你执行M0 Day 1的任务：

1. ✅ 冻结V1分支
2. ✅ 创建V2重构分支
3. ✅ 归档架构文档
4. ✅ 创建M1工作目录

**准备好了吗？我将立即执行这些Git操作！**

---

**制定人**: Claude Opus 4.8  
**文档版本**: Execution Plan v1.0  
**下一步**: 执行M0 Day 1任务
