# 核心项目研究笔记

**研究计划**: 本周完成2个核心项目代码研究  
**总时间**: ~5小时  
**状态**: 🟡 待开始  

---

## 📂 项目列表

| # | 项目 | 时间 | 重点内容 | 状态 |
|---|------|------|---------|------|
| 1 | HZ-KMNO | 3h | Draft A/B/C、章节蓝图 | 🟡 待研究 |
| 2 | Novel-OS | 2h | SQLite持久化、Snapshot | 🟡 待研究 |

---

## 1. HZ-KMNO - 中文网文写作指导 Skill

**项目链接**: https://github.com/HZ-KMNO/web-novel-writing-guidance-skill  
**最新更新**: （克隆后查看）  
**研究日期**: ________  
**研究时长**: ____小时  
**状态**: 🟡 待研究  

### 项目概况

**类型**: Claude Code Skill系统  
**定位**: 中文网文写作指导  
**特点**: 专门针对中文连载网文

### 核心特点

1. **Draft A/B/C工作流**
   - Draft A: 快速初稿
   - Draft B: 改进版本（修复问题）
   - Draft C: 精修版本（优化细节）

2. **章节蓝图（Chapter Blueprint）**
   - 比Task Package更详细
   - 包含场景、角色弧光、钩子、伏笔

3. **优秀案例方法（Excellent-case Methods）**
   - 参考起点爆款案例
   - 提取成功模式
   - 应用到生成中

### 关键代码位置

（克隆项目后填写）

**Draft A/B/C实现**:
- 文件: 
- 行数: 
- 关键逻辑: 

**章节蓝图实现**:
- 文件: 
- 行数: 
- 关键逻辑: 

**优秀案例库**:
- 文件: 
- 行数: 
- 数据结构: 

### 可借鉴设计

#### 设计1: Draft A/B/C工作流

**原始实现**:
```python
# （研究后填写代码片段）
```

**ANovel应用**:
- 位置: `runtime/production/stages/generate_draft_stage.py`
- 改良点: 
  - 与Pipeline集成
  - 增加成本追踪
  - 增加质量判断标准
- 预期收益: 单章质量提升15-25%

#### 设计2: 章节蓝图

**原始实现**:
```python
# （研究后填写代码片段）
```

**ANovel应用**:
- 位置: `runtime/outline/chapter_blueprint.py`
- 改良点:
  - 从TaskPackage扩展
  - 增加题材专用字段
- 预期收益: 章节规划更详细

#### 设计3: 优秀案例库

**原始实现**:
```python
# （研究后填写代码片段）
```

**ANovel应用**:
- 位置: `runtime/knowledge/excellent_cases.py`
- 改良点:
  - 按题材分类
  - Few-shot Prompt集成
- 预期收益: 参考优秀模式

### 技术细节记录

（研究代码时详细记录）

### 疑问与讨论

（研究过程中的疑问）

---

## 2. Novel-OS

**项目链接**: https://github.com/mrigankad/Novel-OS  
**最新更新**: 2026年6月11日  
**研究日期**: ________  
**研究时长**: ____小时  
**状态**: 🟡 待研究  

### 项目概况

**类型**: Multi-agent novel writing framework  
**特点**: 
- Persistent story state
- Deterministic continuity engine
- Five-role editorial pipeline
- SQLite persistence layer

### 核心特点

1. **SQLite持久化层**
   - 轻量级，可嵌入
   - 支持事务
   - 适合单机部署

2. **Snapshot机制**
   - 保存完整状态快照
   - 支持时间回溯
   - 支持A/B测试

3. **Comments（评论）机制**
   - 支持人工标注
   - 用于金样集构建

### 关键代码位置

（克隆项目后填写）

**SQLite持久化实现**:
- 文件: 
- 表结构: 
- 关键SQL: 

**Snapshot实现**:
- 文件: 
- 数据结构: 
- 保存时机: 

**Comments实现**:
- 文件: 
- 数据结构: 
- 用途: 

### 可借鉴设计

#### 设计1: SQLite持久化

**原始实现**:
```python
# （研究后填写代码片段）
```

**表结构**:
```sql
-- （研究后填写表结构）
CREATE TABLE snapshots (
    snapshot_id TEXT PRIMARY KEY,
    ...
);
```

**ANovel应用**:
- 位置: `runtime/persistence/sqlite_backend.py`
- 改良点:
  - 集成到MintExecutor
  - 自动在Mint时保存快照
- 预期收益: 
  - 支持时间回溯
  - 支持A/B测试
  - 人工标注基础

#### 设计2: Snapshot机制

**原始实现**:
```python
# （研究后填写代码片段）
```

**ANovel应用**:
- 位置: `runtime/mint/snapshot_manager.py`
- 改良点:
  - 与Validity Interval结合
  - 快照差异计算
- 预期收益:
  - 状态可追溯
  - 支持版本对比

#### 设计3: 五角色编辑管道

**原始实现**:
（研究后填写）

**ANovel应用**:
- ⚠️ M3前不采纳多智能体争论
- 但可参考角色分工理念

### 技术细节记录

（研究代码时详细记录）

### 疑问与讨论

（研究过程中的疑问）

---

## 📊 研究计划

### 本周计划

**周六**: HZ-KMNO项目
- 上午：克隆项目，浏览结构
- 下午：深度研究Draft A/B/C实现

**周日**: Novel-OS项目
- 上午：克隆项目，浏览结构
- 下午：深度研究SQLite持久化实现

### 研究方法

1. **克隆项目**: 本地完整克隆
2. **浏览结构**: 理解整体架构
3. **精读代码**: 关键模块详细阅读
4. **运行测试**: 本地运行（如果可能）
5. **提取设计**: 记录可借鉴设计

### 输出物

- [ ] 2个项目研究笔记完成
- [ ] 关键代码片段摘录
- [ ] ANovel应用设计草案

---

## 🔗 辅助资源

### 克隆命令

```bash
# 创建研究目录
mkdir -p /tmp/ainovel-research
cd /tmp/ainovel-research

# 克隆HZ-KMNO项目
git clone https://github.com/HZ-KMNO/web-novel-writing-guidance-skill.git

# 克隆Novel-OS项目
git clone https://github.com/mrigankad/Novel-OS.git
```

### 相关文档

- **架构决策**: 12_ARCHITECTURE_DECISION_RECORD_PART2.md
- **可执行指南**: 11_FINAL_EXECUTABLE_GUIDE.md
- **竞品分析**: 09, 10

---

**最后更新**: 2026-09-18  
**下次更新**: 研究第一个项目后
