# AI-Novel 项目渐进式重构方案（C目标）

**制定日期**: 2026-09-09  
**目标**: 系统性解决叙事连续性问题，采用渐进式重构而非大爆炸重写  
**核心原则**: 重构控制面，保留基础设施

---

## 🎯 重构范围

### ✅ 保留（基础设施层）

**不需要重写的模块**:
- `registry/` - 事实存储
- `schema/` - 类型定义
- `provenance/` - 溯源链
- `execution/agent.py` - 哈希和重放
- `llm/` - 模型适配
- `validator.py` - Schema 验证（基础部分）

**原因**: 这些是稳定的、工作正常的基础设施

---

### 🔧 重构（控制面）

**需要重构的模块**:
1. **Canonical Story Bible** - 故事圣经（新建）
2. **Chapter Contract** - 章节契约（新建）
3. **Serial State Machine** - 串行状态机（重构）
4. **Semantic Continuity Gates** - 语义连续性门禁（新建）
5. **Unified Publish State** - 统一发布状态（重构）
6. **Allowed-final-only Export** - 受控导出（重构）

**原因**: 当前的控制面缺乏约束，导致章节独立生成

---

## 📋 分阶段实施计划

### C0: 立即止血（1-2天）

**目标**: 防止当前坏结果扩散

#### 行动清单

1. **冻结现有产物** ✅
   ```bash
   # 移动到隔离区
   mv novel-dushi/《重生之金融帝国》前30章.txt \
      novel-dushi/INVALIDATED-前30章-20260909.txt
   
   # 标记所有章节为 invalidated
   for ch in registry/derived/chapter-final/*.json; do
       jq '.production_state = "invalidated"' "$ch" > tmp && mv tmp "$ch"
   done
   ```

2. **标记 RUN 无效**
   ```bash
   # RUN-00030 标记为失败
   echo "INVALIDATED: 主角混乱、剧情断裂" > \
     registry/derived/run-manifests/RUN-00030.INVALID
   ```

3. **禁止对外交付**
   - 创建 `.DO_NOT_USE` 标记文件
   - 在导出器中添加检查

4. **暂停批量生成**
   - 停止所有正在运行的 Serial 任务
   - 在重构完成前不启动新生成

5. **指定 canonical run**
   ```bash
   # 创建 canonical run 标记（目前为空）
   echo "null" > registry/derived/.canonical-run
   ```

**验收标准**:
- ✅ 现有30章无法被导出
- ✅ 新生成被阻止
- ✅ 有明确的 canonical run 指向

---

### C1: 重建故事输入层（1周）

**目标**: 建立经过人工确认的 Canonical Story Bible

#### 新增：Story Bible 结构

**位置**: `registry/story-bible/BIBLE-00001.yaml`

```yaml
version: "1.0"
status: human_approved
locked_at: "2026-09-09"

# 核心设定（不可变）
protagonist:
  name: 陈默
  age_at_start: 25
  identity: 金融分析师
  rebirth_from: 2030
  rebirth_to: 2013
  memory_span: 17年完整记忆

# 时空设定（不可变）
timeline:
  start_date: "2013-01-15"
  end_date: "2023-12-31"
  current_chapter_date: "2013-01-15"  # 动态更新

world:
  primary_city: 江城
  primary_company: 恒远投资公司
  
# 核心人物（可扩展，需授权）
core_characters:
  - id: CHR-90001
    name: 陈默
    role: 主角
    
  - id: CHR-90002
    name: 张伟
    role: 导师/前辈
    relationship: 陈默的直属上司
    
  - id: CHR-90003
    name: 林雪
    role: 青梅竹马
    relationship: 陈默的暗恋对象

# 金手指规则（不可变）
golden_finger:
  type: 前世记忆
  scope: 17年完整记忆，知道所有商机和危机
  cost: 改变历史可能导致蝴蝶效应
  limits:
    - 不能直接预知具体股票涨跌细节
    - 只记得大趋势和关键事件
    - 人物关系可能因改变而偏移

# 前30章主线（具体事件）
chapter_events:
  - chapter: 1
    date: "2013-01-15"
    location: 恒远投资公司
    event: 陈默重生第一天，发现前世投资失败的项目即将启动
    antagonist: 赵经理（推动失败项目的人）
    objective: 阻止公司参与注定失败的江北地产项目
    hook: 陈默发现张伟也对项目有疑虑
    
  - chapter: 2
    date: "2013-01-16"
    location: 恒远投资公司会议室
    event: 陈默在项目评审会上提出反对意见
    antagonist: 赵经理 + 支持派
    objective: 说服管理层放弃项目
    previous_hook_resolution: 联合张伟收集证据
    hook: 赵经理威胁陈默的职位
    
  # ... 30章完整规划
```

#### 实施步骤

1. **人工编写 Story Bible**（2天）
   - 基于最初的题材卡和 Outline
   - 明确主角、时间、地点、核心人物
   - 规划30章的具体事件（不是抽象目标）

2. **锁定 Story Bible**（1天）
   - 人工审核确认
   - 设置 `status: human_approved`
   - 生成 `locked_hash`

3. **修改 Event 生成**（2天）
   - 从 Story Bible 生成 30个具体 Event
   - 每个 Event 包含：
     - 明确的日期、地点、人物
     - 具体的事件描述（不是"摸清敌人底细"）
     - 上一章的钩子解决
     - 本章的新钩子

4. **验证 Event 链**（1天）
   - 检查30个 Event 的因果关系
   - 确保时间线连续
   - 确保人物关系一致

**验收标准**:
- ✅ Story Bible 完整且人工确认
- ✅ 30个 Event 具体且相互连接
- ✅ 主角、时间、地点固定不变

---

### C2: 重建章节契约和状态机（1-2周）

**目标**: 每章必须符合明确的契约，状态统一管理

#### 新增：Chapter Contract

**位置**: `runtime/contract/chapter_contract.py`

```python
@dataclass
class ChapterContract:
    """章节契约：每章生成必须满足的约束"""
    
    # 输入约束
    entry_state: StoryState
    objective: str  # 具体目标，不是抽象框架
    antagonist: str  # 明确的对手
    beats: List[str]  # 必须经过的情节点
    
    # 输出约束
    irreversible_change: str  # 本章改变了什么
    exit_state: StoryState
    next_hook: str  # 下一章的起点
    
    # 溯源
    previous_artifact_hash: str  # 上一章的哈希
    story_bible_hash: str  # Story Bible 的哈希
    
    # 连续性约束
    protagonist_name: str  # 必须出现的主角名字
    date_range: Tuple[str, str]  # 允许的日期范围
    allowed_locations: List[str]  # 允许的地点
    required_characters: List[str]  # 必须出现的人物

@dataclass
class StoryState:
    """故事状态：跨章节共享的世界状态"""
    
    protagonist: Character  # 主角信息
    current_date: str  # 当前日期
    current_location: str  # 当前地点
    
    # 人物关系图
    characters: Dict[str, Character]
    relationships: Dict[Tuple[str, str], Relationship]
    
    # 未完成的线索
    open_threads: List[Thread]
    # 已解决的线索
    resolved_threads: List[Thread]
    
    # 世界事实
    world_facts: Dict[str, Any]
    
    def validate_continuity(self, prev_state: 'StoryState') -> List[str]:
        """验证与上一个状态的连续性"""
        errors = []
        
        # 主角名字不能变
        if self.protagonist.name != prev_state.protagonist.name:
            errors.append(f"主角名字改变: {prev_state.protagonist.name} → {self.protagonist.name}")
        
        # 时间只能前进
        if self.current_date < prev_state.current_date:
            errors.append(f"时间倒流: {prev_state.current_date} → {self.current_date}")
        
        # 人物不能凭空消失
        for char_id in prev_state.characters:
            if char_id not in self.characters:
                errors.append(f"人物消失: {char_id}")
        
        return errors
```

#### 统一状态枚举

**位置**: `runtime/contract/production_state.py`

```python
class ProductionState(Enum):
    """统一的生产状态"""
    
    GENERATED = "generated"  # 已生成，未验证
    NEEDS_REVISION = "needs_revision"  # 需要修改
    BLOCKED = "blocked"  # 被阻塞（依赖未满足）
    HUMAN_APPROVED = "human_approved"  # 人工审核通过
    PUBLISHED = "published"  # 已发布
    INVALIDATED = "invalidated"  # 已作废
    
    def can_export(self) -> bool:
        """是否可以导出"""
        return self in [
            ProductionState.HUMAN_APPROVED,
            ProductionState.PUBLISHED
        ]
    
    def can_proceed_next(self) -> bool:
        """是否可以继续下一章"""
        return self in [
            ProductionState.HUMAN_APPROVED,
            ProductionState.PUBLISHED
        ]
```

#### 删除旧的独立决策字段

```python
# 删除或标记为 advisory：
# - publish_readiness.overall_status
# - commercial_verdict
# - m7_final.decision

# 这些仍然生成，但不再决定最终状态
# 最终状态由 ProductionState 统一决定
```

#### 实施步骤

1. **实现 ChapterContract**（3天）
   - 定义契约结构
   - 生成时注入契约
   - 验证时检查契约

2. **实现 StoryState**（3天）
   - 提取上一章的状态
   - 传递给下一章
   - 验证连续性

3. **统一 ProductionState**（2天）
   - 替换所有旧状态字段
   - 实现状态转换逻辑
   - 更新 Serial 使用新状态

4. **重构 Serial**（3天）
   - 检查上一章状态
   - 只有 `can_proceed_next()` 才继续
   - 记录契约和状态

**验收标准**:
- ✅ 每章有明确的契约
- ✅ StoryState 正确传递
- ✅ 状态统一为 ProductionState
- ✅ 无法跳过阻塞章节

---

### C3: 重建连续性门禁（1-2周）

**目标**: 确定性检查 + 语义审查

#### 新增：Semantic Continuity Gate

**位置**: `runtime/gates/semantic_continuity.py`

```python
class SemanticContinuityGate:
    """语义连续性门禁"""
    
    def validate(self, 
                 prev_chapter: ChapterFinal,
                 curr_chapter: ChapterFinal,
                 contract: ChapterContract) -> GateResult:
        """验证语义连续性"""
        
        errors = []
        warnings = []
        
        # 1. 确定性检查（硬约束）
        errors.extend(self._check_deterministic(prev_chapter, curr_chapter, contract))
        
        # 2. 语义审查（软约束）
        warnings.extend(self._check_semantic(prev_chapter, curr_chapter))
        
        if errors:
            return GateResult(passed=False, errors=errors, warnings=warnings)
        else:
            return GateResult(passed=True, errors=[], warnings=warnings)
    
    def _check_deterministic(self, prev_ch, curr_ch, contract) -> List[str]:
        """确定性检查"""
        errors = []
        
        curr_text = curr_ch.final_text
        
        # 1. 主角名字
        if contract.protagonist_name not in curr_text[:1000]:
            errors.append(f"主角名字缺失: {contract.protagonist_name}")
        
        # 检查是否出现其他主角名字
        wrong_names = self._extract_protagonist_candidates(curr_text)
        if wrong_names and contract.protagonist_name not in wrong_names:
            errors.append(f"主角名字错误: 出现 {wrong_names}，应为 {contract.protagonist_name}")
        
        # 2. 日期范围
        dates = self._extract_dates(curr_text)
        for date in dates:
            if not (contract.date_range[0] <= date <= contract.date_range[1]):
                errors.append(f"日期越界: {date} 不在 {contract.date_range}")
        
        # 3. 地点
        locations = self._extract_locations(curr_text)
        for loc in locations:
            if loc not in contract.allowed_locations:
                errors.append(f"地点未授权: {loc} 不在允许列表")
        
        # 4. 上一章出口消费
        if prev_ch and prev_ch.exit_state:
            if not self._hook_consumed(prev_ch.exit_state.next_hook, curr_text[:500]):
                errors.append(f"上一章钩子未消费: {prev_ch.exit_state.next_hook[:50]}...")
        
        # 5. 未完成任务
        if prev_ch and prev_ch.exit_state:
            for thread in prev_ch.exit_state.open_threads:
                if not self._thread_addressed(thread, curr_text):
                    warnings.append(f"未解决的线索: {thread.description}")
        
        # 6. 新事实授权
        new_characters = self._extract_new_characters(curr_text, contract.required_characters)
        if new_characters:
            # 检查是否在 Story Bible 中授权
            for char in new_characters:
                if not self._is_authorized(char, contract.story_bible_hash):
                    errors.append(f"未授权的新人物: {char}")
        
        # 7. 上一章哈希
        if prev_ch and contract.previous_artifact_hash:
            if prev_ch.content_hash != contract.previous_artifact_hash:
                errors.append(f"上一章哈希不匹配")
        
        return errors
    
    def _check_semantic(self, prev_ch, curr_ch) -> List[str]:
        """语义审查（使用 LLM）"""
        warnings = []
        
        # 调用 LLM 检查：
        # - 动机是否合理
        # - 因果是否连贯
        # - 承诺是否兑现
        # - 伏笔是否回收
        
        prompt = f"""
        检查章节连续性：
        
        上一章结尾：{prev_ch.final_text[-500:]}
        本章开头：{curr_ch.final_text[:500]}
        
        问题：
        1. 主角动机是否延续？
        2. 因果是否合理？
        3. 上一章的钩子是否被处理？
        4. 是否有明显的剧情断裂？
        
        返回问题列表。
        """
        
        # ... LLM 调用
        
        return warnings
```

#### 实施步骤

1. **实现确定性检查**（5天）
   - 主角名字提取和验证
   - 日期、地点提取和验证
   - 钩子消费检查
   - 新事实授权检查

2. **实现语义审查**（3天）
   - 设计 LLM prompt
   - 调用 LLM 检查连续性
   - 解析结果

3. **集成到 Serial**（2天）
   - 在生成后立即验证
   - 失败则标记为 BLOCKED
   - 记录详细错误

**验收标准**:
- ✅ 主角名字错误必被检出
- ✅ 时间倒流必被检出
- ✅ 未授权人物必被检出
- ✅ 钩子未消费被警告

---

### C4: 新旧链路并行验证（1-2周）

**目标**: 渐进式验证，不一次性生成30章

#### 验证策略

```
第1-3章: 逐章人工审核
  - 生成第1章 → 人工审核 → 通过才继续
  - 生成第2章 → 人工审核 → 通过才继续
  - 生成第3章 → 人工审核 → 通过才继续

第4-10章: 自动门禁 + 定期人工检查
  - 每章自动门禁必须通过
  - 每5章人工抽查
  - 发现问题立即停止

第11-30章: 每10章 checkpoint
  - 第10章后人工全面审核
  - 第20章后人工全面审核
  - 第30章后最终验收
```

#### 实施步骤

1. **实现人工审核接口**（2天）
   ```bash
   # 生成章节后暂停
   python -m runtime.cli serial run --pause-after-each
   
   # 人工审核
   python -m runtime.cli review chapter TASK-00001
   
   # 批准或拒绝
   python -m runtime.cli approve TASK-00001
   python -m runtime.cli reject TASK-00001 --reason "主角名字错误"
   ```

2. **实现 checkpoint 机制**（3天）
   - 每N章自动创建 checkpoint
   - checkpoint 包含：
     - 当前 StoryState
     - 所有已完成章节的哈希
     - 连续性验证报告
   - 失败时可以回滚到 checkpoint

3. **渐进式生成**（5天）
   - 生成1-3章，逐章审核
   - 审核通过后生成4-10章
   - 继续直到30章

4. **记录问题和改进**（持续）
   - 每次失败记录原因
   - 改进门禁规则
   - 改进 Story Bible

**验收标准**:
- ✅ 1-3章逐章通过人工审核
- ✅ 4-30章自动门禁通过率 > 90%
- ✅ 人工抽查发现问题 < 10%
- ✅ 最终30章连贯可读

---

### C5: 切换并淘汰旧路径（1周）

**目标**: 新链路稳定后，删除/限制旧的不受控导出

#### 新增：Controlled Export

**位置**: `runtime/export/controlled_export.py`

```python
class ControlledExport:
    """受控导出：只导出经过审核的章节"""
    
    def export_book(self, 
                    project_dir: Path,
                    canonical_run_id: str,
                    output_path: Path) -> ExportResult:
        """导出书籍"""
        
        # 1. 验证 canonical run
        if not self._is_canonical(canonical_run_id):
            raise ValueError(f"非 canonical run: {canonical_run_id}")
        
        # 2. 只读取 chapter-final
        chapter_dir = project_dir / "registry/derived/chapter-final"
        
        # 3. 过滤章节
        chapters = []
        for ch_file in sorted(chapter_dir.glob("*.json")):
            with open(ch_file) as f:
                ch = json.load(f)
            
            # 检查状态
            state = ProductionState(ch.get('production_state'))
            if not state.can_export():
                continue
            
            # 检查 run_id
            if ch.get('run_id') != canonical_run_id:
                continue
            
            # 检查连续性
            if not self._check_continuity_passed(ch):
                continue
            
            chapters.append(ch)
        
        # 4. 验证完整性
        if not self._is_complete_sequence(chapters):
            raise ValueError("章节序列不完整")
        
        # 5. 导出
        return self._write_book(chapters, output_path)
    
    def _is_complete_sequence(self, chapters: List[dict]) -> bool:
        """检查章节序列是否完整"""
        indices = [ch.get('index') for ch in chapters]
        indices.sort()
        
        # 必须从1开始
        if indices[0] != 1:
            return False
        
        # 必须连续
        for i, idx in enumerate(indices, 1):
            if idx != i:
                return False
        
        return True
```

#### 删除/限制旧导出器

```python
# runtime/export/book.py:59

# 旧代码（删除）：
# chapters = glob("chapter-final/*.json")

# 改为：
# raise DeprecationWarning("请使用 ControlledExport")
```

#### 实施步骤

1. **实现 ControlledExport**（3天）
   - 只读取 canonical run
   - 只导出 can_export() 状态
   - 验证完整性

2. **更新 CLI**（2天）
   ```bash
   # 新命令
   python -m runtime.cli export \
     --project ../novel-dushi \
     --canonical-run RUN-00031 \
     --output 《重生之金融帝国》.txt
   
   # 旧命令报错
   python -m runtime.export.book  # DeprecationWarning
   ```

3. **删除旧路径**（1天）
   - 标记 `runtime/export/book.py` 为 deprecated
   - 或删除不受控的导出逻辑

**验收标准**:
- ✅ 只能导出 canonical run
- ✅ 只能导出 approved/published 状态
- ✅ 章节序列必须完整
- ✅ 旧导出器无法使用

---

## 📊 总体时间表

| 阶段 | 时间 | 累计 | 验收标准 |
|------|------|------|----------|
| C0 止血 | 1-2天 | 2天 | 坏结果被隔离 |
| C1 Story Bible | 1周 | 9天 | 故事设定固定 |
| C2 契约+状态 | 1-2周 | 23天 | 状态统一，契约生效 |
| C3 连续性门禁 | 1-2周 | 37天 | 错误必被检出 |
| C4 渐进验证 | 1-2周 | 51天 | 30章连贯可读 |
| C5 切换导出 | 1周 | 58天 | 只导出审核通过 |

**总计**: 约 **2个月**（58天）

---

## 🎯 验收标准（最终）

### 不是承诺生成质量绝对完美

**正确的验收标准**:

1. **错误章节必须被阻断** ✅
   - 主角名字错误 → BLOCKED
   - 时间倒流 → BLOCKED
   - 剧情断裂 → NEEDS_REVISION

2. **坏稿不能进入成书** ✅
   - 只有 HUMAN_APPROVED 才能导出
   - 章节序列必须完整
   - canonical run 明确

3. **连续性和状态可验证** ✅
   - 每章有契约
   - StoryState 可追溯
   - 门禁结果可查

4. **系统可控可审计** ✅
   - 人工可介入审核
   - checkpoint 可回滚
   - 问题可追溯

### 不保证的

- ❌ LLM 永远写出精彩情节
- ❌ 零人工干预
- ❌ 100%自动化生成

### 保证的

- ✅ 坏章节不会混入成书
- ✅ 主角、时间、地点不会乱
- ✅ 问题可以被检测和修复

---

## 💡 风险和应对

### 风险1: 门禁过严，无章节能通过

**应对**: 
- 渐进式调整阈值
- 人工可以覆盖（override）
- 记录每次失败原因，改进规则

### 风险2: Story Bible 设计不合理

**应对**:
- C1 阶段人工充分审核
- 允许小幅修改（版本控制）
- 记录修改原因

### 风险3: LLM 仍然生成质量差

**应对**:
- 门禁只保证连续性，不保证质量
- 质量问题交给人工审核
- 或增加质量门禁（M7等）

### 风险4: 重构周期长，影响交付

**应对**:
- 分阶段交付（1-3章先验证）
- C0-C2 完成后即可小规模生产
- C3-C5 是增强，不阻塞基本功能

---

## 📝 总结

### 核心决策

**采用 C 方案重构生产控制架构，保留基础设施，渐进式迁移**

### 关键原则

1. **重构控制面，不重写全部**
   - 保留：registry、schema、hash、模型层
   - 重构：Story Bible、契约、状态、门禁、导出

2. **渐进式验证，不大爆炸生成**
   - 1-3章逐章审核
   - 4-30章分批验证
   - checkpoint 可回滚

3. **合理验收，不过度承诺**
   - 保证：错误被阻断、坏稿不混入
   - 不保证：LLM 完美生成

### 预期效果

**2个月后**:
- ✅ 系统能稳定生成连贯的30章
- ✅ 错误章节被可靠阻断
- ✅ 导出只包含审核通过的内容
- ⚠️  仍需人工介入审核质量

**不是银弹，但能系统性解决当前的失败模式**

---

**制定日期**: 2026-09-09  
**预期完成**: 2026-11-09（2个月）
