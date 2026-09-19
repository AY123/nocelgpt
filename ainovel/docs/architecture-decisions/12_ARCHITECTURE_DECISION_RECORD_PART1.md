# ANovel V2 架构决策记录：逐项评估与最终决策（第1部分）

**版本**: ADR v1.0  
**制定日期**: 2026-09-18  
**文档说明**: 由于篇幅限制，分为3部分
- 第1部分：Genre系统、State管理、Canon事实系统
- 第2部分：生产流程、质量系统、Prompt系统
- 第3部分：评分系统、工具系统、总结

---

## 📋 使用说明

### 评估维度

每个技术/模块按以下维度评估：

1. **✅ 可借鉴（ADOPT）**: 应该采纳或保持
2. **❌ 不应借鉴（REJECT）**: 应该避免或删除
3. **🔄 V2改良方案（IMPROVE）**: 具体改进设计
4. **⭐ 最终决策（DECISION）**: 明确的实施决定

### 决策来源

- **当前项目**: ainovel/AI-Novel-Runtime/
- **网络项目**: 30+项目调研
- **学术研究**: 15+篇论文
- **客观补充**: 架构师建议

---

## 第一部分：核心架构层

---

## 1. Genre 系统（题材/类型）

### 📊 现状

**V1问题**:
- ❌ Genre只是字符串标签
- ❌ 都市生成修炼内容
- ❌ Power System错误通用化

### ✅ 可借鉴

**从网络项目**:
- Genre-First架构（ANovel独创）
- GenreConfig + GenreConstraints
- ProgressionModel抽象

**客观补充**:
- Genre Hierarchy（层次分类）
- Genre Blending Rules（混合题材）

### ❌ 不应借鉴

**从V1拒绝**:
- 弱约束的Genre标签
- 通用Power System

**从网络拒绝**:
- "支持多题材"但无约束

### 🔄 V2改良方案

```python
@dataclass
class GenreConfig:
    genre_id: str
    constraints: GenreConstraints
    progression_model: Type[ProgressionModel]
    prompt_templates: Dict[str, str]
    detector: GenreDetector

class ProgressionModel(ABC):
    @abstractmethod
    def validate_transition(self, from_tier, to_tier, context) -> bool:
        pass

# 都市实现
class WealthProgressionModel(ProgressionModel):
    tiers = ["贫困线", "温饱", "小康", "中产", "富裕", "富豪"]
    
# 玄幻实现
class PowerProgressionModel(ProgressionModel):
    tiers = ["炼气期", "筑基期", "金丹期", "元婴期"]
```

### ⭐ 最终决策

**Decision 1.1**: ✅ **采纳** Genre-First作为V2核心

**理由**: 行业独创，解决V1最大问题

**实施**:
- M1 Week 1-4: GenreConfig、Registry、Detector
- M1 Week 5-6: Genesis集成

**验收**: 题材检测>90%，都市/玄幻隔离测试通过

---

**Decision 1.2**: ✅ **采纳** ProgressionModel抽象

**实施**: Power/Wealth/Tech/Status四种模型

---

**Decision 1.3**: ⚠️ **暂不采纳** Genre Hierarchy

**理由**: M3前只做都市/玄幻，暂不需要

---

**Decision 1.4**: ❌ **不采纳** Genre Blending

**理由**: 优先保证纯题材质量

---

## 2. State管理系统

### 📊 现状

**V1优点**:
- ✅ State as Projection正确
- ✅ 只读StoryState

**V1问题**:
- ❌ 缺少Validity Interval
- ❌ 无法区分合法变化vs非法矛盾

### ✅ 可借鉴

**从V1保持**:
- State as Projection模式
- 只读StoryState

**从网络项目**:
- Validity Interval（FactTrack论文）
- State Snapshot（Novel-OS项目）
- Temporal RAG（SCORE论文）

**客观补充**:
- State Diff机制
- Fact Lineage追踪

### ❌ 不应借鉴

**从V1拒绝**:
- 缺少有效性区间的Fact

**从网络拒绝**:
- 可变的State对象

### 🔄 V2改良方案

```python
@dataclass
class Fact:
    # V1字段（保留）
    fact_id: str
    fact_type: str
    content: dict
    
    # V2新增：有效性区间
    validity_start: int          # 从第几章开始有效
    validity_end: Optional[int]  # 到第几章结束
    superseded_by: Optional[str] # 被哪个事实替代
    supersede_reason: str        # character_growth/plot_twist/error_fix
    
    def is_valid_at_chapter(self, chapter_num: int) -> bool:
        if chapter_num < self.validity_start:
            return False
        if self.validity_end and chapter_num > self.validity_end:
            return False
        return True

class StoryState:
    current_chapter: int
    valid_facts: List[Fact]
    
    @staticmethod
    def project(facts: List[Fact], chapter_num: int) -> 'StoryState':
        # 只使用在指定章节有效的事实
        valid_facts = [f for f in facts if f.is_valid_at_chapter(chapter_num)]
        # ...

def detect_contradictions_v2(new_fact, chapter_num, story_state):
    """改良的矛盾检测"""
    for old_fact in story_state.get_entity_history(new_fact.entity_id):
        # 关键：检查有效期是否重叠
        if not old_fact.is_valid_at_chapter(chapter_num):
            continue  # 旧事实已失效，不是矛盾
        
        if new_fact.overlaps_with(old_fact):
            if _contents_contradict(old_fact.content, new_fact.content):
                yield Contradiction(...)
```

### ⭐ 最终决策

**Decision 2.1**: ✅ **保持** State as Projection

**理由**: V1设计正确，学术验证

---

**Decision 2.2**: ✅ **采纳** Validity Interval（P0）

**理由**: FactTrack论文验证，解决根本问题

**实施**:
- M1 Week 3: Fact增加字段
- M2 Week 9: 矛盾检测改良

**验收**: 角色成长不被判定为矛盾

---

**Decision 2.3**: ✅ **采纳** State Snapshot

**理由**: 支持A/B测试、人工标注

**实施**:
- M2 Week 10: SQLite存储
- 每次Mint自动保存快照

---

**Decision 2.4**: ⚠️ **暂不采纳** Temporal Knowledge Graph

**理由**: M3前优先基础功能，M4后考虑

---

**Decision 2.5**: ✅ **采纳简化版** State Diff

**实施**: M2 Week 12，只计算基础差异

---

## 3. Canon事实系统

### 📊 现状

**V1优点**:
- ✅ Canon Commit Boundary正确
- ✅ 唯一写入口（SSOT）
- ✅ Provenance完整

**V1问题**:
- ❌ 事务完整性Bug（Phase 6.1发现）
- ❌ 缺少Validity Interval支持

### ✅ 可借鉴

**从V1保持**:
- Canon Commit Boundary
- Validate-then-Write
- Provenance追踪

**从网络项目**:
- State Guards（novel-architect项目）

**客观补充**:
- Fact Lineage（事实血缘）
- Fact Confidence（置信度）

### ❌ 不应借鉴

**从V1拒绝**:
- 有Bug的事务实现

**从网络拒绝**:
- 多个写入口

### 🔄 V2改良方案

```python
class MintExecutor:
    """改良的Mint（原子事务）"""
    
    def execute(self, facts: List[Fact]) -> MintResult:
        # 1. 验证（增加State Guards）
        violations = self._validate(facts)
        if violations:
            raise MintValidationError(violations)
        
        # 2. 原子写入（修复Bug）
        try:
            self._begin_transaction()
            
            for fact in facts:
                self._write_fact(fact)
                self._write_provenance(fact)
            
            # 3. 生成快照（新增）
            snapshot_id = self.snapshot_manager.save_snapshot(...)
            
            self._commit_transaction()
            
        except Exception:
            self._rollback_transaction()
            raise
    
    def _validate(self, facts):
        violations = []
        
        # 基础验证
        violations.extend(self._validate_schema(facts))
        
        # State Guards（新增）
        current_state = StoryState.project(...)
        for guard in self.guards:
            violations.extend(guard.guard(current_state, facts))
        
        # Validity Interval检查（新增）
        violations.extend(self._check_validity_intervals(facts))
        
        return violations

class CharacterIdentityGuard(StateGuard):
    """守卫角色身份"""
    
    def guard(self, old_state, new_facts):
        violations = []
        for fact in new_facts:
            if "name" in fact.content:
                old_char = old_state.characters.get(fact.entity_id)
                if old_char and old_char.name != fact.content["name"]:
                    violations.append(GuardViolation(
                        type="character_name_change",
                        severity="critical"
                    ))
        return violations
```

### ⭐ 最终决策

**Decision 3.1**: ✅ **保持** Canon Commit Boundary

**理由**: SSOT最佳实践

---

**Decision 3.2**: ✅ **必须修复** 事务完整性Bug（P0）

**实施**:
- M1 Week 4: 设计原子事务
- M2 Week 9: 实现并测试

**验收**: 压力测试无数据损坏

---

**Decision 3.3**: ✅ **采纳** State Guards

**实施**: M2 Week 10实现4个核心Guards
- CharacterIdentityGuard
- TimelineGuard  
- WorldSettingGuard
- GenreConstraintsGuard

**验收**: 所有非法修改被阻断

---

**Decision 3.4**: ⚠️ **暂不采纳** Fact Lineage

**理由**: M3前优先基础功能

---

**Decision 3.5**: ✅ **采纳简化版** Fact Confidence

**实施**: M2 Week 10增加confidence字段
- 默认1.0（人工确认）
- AI推断0.7
- 冲突时高置信度优先

---

## 📄 文档状态

**当前**: 第1部分完成  
**下一步**: 生成第2部分（生产流程、质量系统、Prompt系统）

---

**制定人**: Claude Opus 4.8  
**文档版本**: ADR v1.0 Part 1/3
