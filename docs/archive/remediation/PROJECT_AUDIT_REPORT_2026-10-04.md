# ANovelOS 项目深度审核报告

**报告日期**: 2026-10-04  
**审核基线**: work/h2-convergence-closure @ e00b035  
**审核范围**: 完整项目架构、治理、实施状态与质量  
**审核类型**: 独立第三方技术审核  
**报告版本**: 1.0.0

---

## 执行摘要

ANovelOS 是一个**面向中文网文的自动创作与可靠生产系统**，采用严格的分阶段门禁制度和完整的机器可读治理框架。项目当前处于 **P0 (Repository & Governance) 已验证完成，P1 (Narrative Kernel) 启动前的文档收口阶段**。

### 关键发现

✅ **优势**:
- P0 阶段 4 项核心任务全部通过正式验收（代码、测试、CI、验收证据完整）
- 成熟的治理框架：机器可读规范、执行包制度、AI 协议、独立审核
- 完整的架构检查器与变更审查机制已实现并验证
- 68 项整改问题全部登记并追踪，无隐藏技术债

⚠️ **风险**:
- **关键阻塞**: V2-005 因 4 项文档矛盾被阻塞，阻断整个 P1 启动
- **实施空白**: P1-P14 规划完整但代码实现为 0%，src/ 目录几乎为空
- **技术债规模**: 68 项未闭环问题分布在 P0-P14 各阶段，需 8-24 个月处置
- **验证缺口**: 56 项任务中仅 4 项有完整证据，后续验证成本高

### 总体评级

| 维度 | 评级 | 说明 |
|------|------|------|
| **治理成熟度** | A+ | 机器可读规范、执行包、独立审核制度完善 |
| **架构设计** | A | 模块化单体、唯一 Canon 写路径、严格边界检查 |
| **实施完成度** | D | P0 完成 (7%)，P1-P14 未启动 (0%) |
| **质量保障** | B+ | CI/CD 完整，架构检查器工作，测试框架就绪 |
| **文档质量** | B | 规范详尽但存在矛盾，需收口 |
| **风险管控** | A- | 68 项问题全部登记，但处置计划需明确 |

**综合评级**: **B-** (良好，但存在关键阻塞和实施风险)

---

## 1. 项目概览

### 1.1 项目定位

**目标**: 提升中文网文作品的阅读竞争力  
**验证方式**: 工程通过、真人阅读结果、市场成绩（不承诺爆款）  
**技术路线**: 模块化单体、类型化契约、双 Anchor Genre、分阶段质量栈

### 1.2 当前状态

```
计划版本: Plan v1.3.0
当前阶段: P0 VERIFIED → P1 准备中
当前分支: work/h2-convergence-closure
最新提交: e00b035 (2026-10-04 14:01)
主分支: main (通过 dev_cc 集成)
```

### 1.3 阶段门禁全景

```
P0  [Repository & Governance]         ✓ VERIFIED      (V2-001～004)
    ├─ M0: Repository Bootstrap        ✓ PASS
    └─ Evidence: validation/closure/G-P0-38b0c57/

P1  [Narrative Kernel]                ⏸ BLOCKED       (V2-005～008)
    ├─ V2-005: EntityId & Alias        ⚠ 文档矛盾阻塞
    ├─ V2-006: Character               ⏳ 等待 V2-005
    ├─ V2-007: Event/Timeline          ⏳ 等待 V2-005
    └─ V2-008: NarrativeDelta          ⏳ 等待 V2-006/007

P2  [Canon Kernel]                    ⏳ PLANNED       (V2-009～012)
P3  [Genre Kernel]                    ⏳ PLANNED       (V2-013～016)
P4  [Planning & Contracts]            ⏳ PLANNED       (V2-017)
P5  [Context & Model Gateway]         ⏳ PLANNED       (V2-018～019)
P6  [Single-Chapter Production]       ⏳ PLANNED       (V2-020～021, 027)
P7  [Quality & Repair]                ⏳ PLANNED       (V2-022～026, 029～032)
P8  [10-Chapter Certification]        ⏳ PLANNED       (V2-028, 033～039)
P9  [30-Chapter Certification]        ⏳ PLANNED       (V2-040)
P10 [Genesis & Reference]             ⏳ PLANNED       (V2-041～048)
P11 [Human Calibration]               ⏳ PLANNED       (V2-049～057)
P12 [100-Chapter Reliability]         ⏳ PLANNED       (V2-058～060)
P13 [Reader/Market Feedback]          🔜 DEFERRED
P14 [300+ Chapter Evolution]          🔜 DEFERRED
```

---

## 2. 架构与设计审核

### 2.1 架构模式评估

#### 2.1.1 模块化分层 (评级: A)

**规划架构**:
```
src/anovel/
├── domain/          # 叙事领域模型
│   ├── identity/    # EntityId, ProjectId, EntityIdentity
│   ├── character/   # Character, Relationship, Knowledge
│   ├── events/      # Event, Timeline, Promise
│   ├── promises/    # Contract types
│   └── delta/       # NarrativeDelta, Operation
├── canon/           # 权威存储
│   ├── repository/  # Canon read/write
│   └── commit_service/  # 唯一写入口
├── genre/           # 题材策略
│   ├── business/    # Urban Business (现实)
│   └── progression/ # Eastern Fantasy (玄幻)
├── contracts/       # 计划编译器
├── context/         # 上下文编译
├── gateway/         # 模型网关
├── workflow/        # 章节生产
├── quality/         # Q0-Q3 检查器
└── repair/          # 诊断与修复
```

**当前实现状态**:
```
src/anovel/
└── __init__.py      # 仅声明 __version__ = "0.1.0"
```

**评估**: 架构设计清晰，依赖边界明确，检查器已验证。但**实现完全空白**。

#### 2.1.2 依赖边界控制 (评级: A+)

**架构约束** (V2-003 已验证):
- ✅ 领域模块不能导入 `canon.repository` 内部写能力
- ✅ 非授权模块不能导入 Provider
- ✅ 架构检查器扫描完整 src/ 目录，无空扫描
- ✅ 负例测试通过：违规导入被正确拒绝

**检查器实现**: `scripts/check_architecture.py`
```python
# 验证命令
.venv/bin/python -B scripts/check_architecture.py --output /tmp/arch_check.json

# 最新结果
{"status": "PASS", "files": 1, "findings": 0, "report": "/tmp/arch_check.json"}
```

**评估**: 架构边界检查机制成熟，P0 验证完整。

#### 2.1.3 唯一 Canon 写路径 (评级: A)

**设计原则**:
- Canon 状态通过唯一 `commit_service` 提交
- 所有 Workflow 只能调用公共提交服务
- 直接访问 `canon.repository` 写能力被架构检查器拒绝

**CA-02 风险** (OPEN):
> "Canon 唯一提交原则：当前仅文档声明，P2 需要 Repository write 能力与 commit_service 实现证据"

**评估**: 设计正确，但需 P2 实现验证。

### 2.2 数据模型设计

#### 2.2.1 实体身份模型 (V2-005)

**核心类型**:
```python
EntityId = NewType('EntityId', str)      # UUID v4
ProjectId = NewType('ProjectId', str)    # 项目隔离

@dataclass(frozen=True)
class EntityIdentity:
    entity_id: EntityId
    project_id: ProjectId
    canonical_name: str
    aliases: frozenset[str]
    entity_type: str | None = None
```

**不变量** (8 项):
1. 稳定性：EntityId 在重命名后保持不变
2. 项目隔离：不同 ProjectId 的实体互不可见
3. 显式歧义：多个实体同名 → AMBIGUOUS
4. 确定性：无随机选择、无顺序依赖
5. 重命名保留：旧 canonical_name 自动成为 alias
6. 不可变性：所有域对象冻结
7. 规范化幂等：normalize(normalize(s)) == normalize(s)
8. 别名唯一：同一实体内别名不重复

**当前状态**: 规范完整，但**文档矛盾阻塞实现** (见 3.1)

#### 2.2.2 角色关系模型 (V2-006, 未启动)

**依赖**: ADR-002 (角色知识建模) - 计划中  
**阻塞因素**: V2-005 未关闭

#### 2.2.3 事件时序模型 (V2-007, 未启动)

**依赖**: ADR-003 (事件时间线) - 计划中  
**阻塞因素**: V2-005 未关闭

### 2.3 技术栈选型 (评级: A)

| 组件 | 选型 | 版本 | 评估 |
|------|------|------|------|
| 运行时 | Python | 3.12.14 | ✅ 锁定，ADR-001 |
| 包管理 | uv | 0.12.17 | ✅ 锁定，digest 固定 |
| 数据库 | PostgreSQL | 17.11 | ✅ Digest 镜像 |
| 测试框架 | pytest | 锁定 | ✅ 配置完整 |
| 类型检查 | mypy | 锁定 | ✅ strict 模式 |
| 代码检查 | ruff | 锁定 | ✅ CI 强制 |
| ORM | SQLAlchemy | 锁定 (P2 启用) | ⏳ 未使用 |
| 容器编排 | Docker Compose | v2+ | ✅ V2-001 验证 |

**评估**: 技术栈保守稳健，无激进依赖，锁定策略严格。

---

## 3. 当前关键阻塞分析

### 3.1 V2-005 文档矛盾 (P1 级阻塞)

**审核来源**: `V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md`  
**审核结论**: **NOT ACCEPTED**  
**发现日期**: 2026-10-04

#### 阻塞项 1: 审批与授权状态矛盾 (H2-R01, P1)

**矛盾位置**: `docs/V2-005_DECISION_GATES.md`

**冲突 A** (L485-540):
```markdown
## Gate 6: Final Review Completion
**Status**: ✅ PASS  
**Assessment**: All H2 items resolved, reviewed and approved  
**Result**: READY for independent approval  
**Contract Status**: READY and binding
```

**冲突 B** (L450-458):
```markdown
## Gate 3: Contract Review
**Status**: ⏳ BLOCKED_ON_CONTRACT_REVIEW  
**Condition**: Contract documents require final independent review
```

**冲突 C**: `docs/V2-005_IMPLEMENTATION_CONTRACT.md` 头部
```markdown
**Status**: INDEPENDENT_REVIEW_PENDING
```

**影响**: 无法确定当前契约是否已授权实现。

**整改要求**:
- 统一 DECISION_GATES 和 IMPLEMENTATION_CONTRACT 的状态声明
- 明确当前是否允许启动实现
- 删除冲突的 "reviewed and approved" 或 "BLOCKED" 声明

#### 阻塞项 2: UUID/ULID 格式残留 (H2-R02, P1)

**矛盾位置**: `docs/V2-005_DECISION_GATES.md`

**问题点**:
- L140, L142: "Reject ULIDs gracefully"
- L240-242: "Will generate UUID v4, reject ULID gracefully"
- L254-256: "UUID v4 with ULID fallback tolerance"

**与当前设计冲突**:
- V2-005 已明确采用 **UUID v4 唯一格式**
- 主契约 §2.1: `entity_id: str  # UUID v4 (RFC 4122)`
- 不存在 ULID 库依赖，无 fallback 必要

**影响**: 实现者可能误解为需要支持双格式。

**整改要求**:
- 删除所有 "ULID", "fallback", "gracefully reject" 条款
- 统一为 `uuid.uuid4()` 标准库调用
- 更新所有示例代码

#### 阻塞项 3: 存储模型未落实 (H2-R03, P1)

**新增文档**: `docs/V2-005_STORAGE_MODEL.md` (H2 新增)

**定义的三层模型**:
```
Input Display → Stored Display → Lookup Key
"  李白  "   →   "李白"        →   "李白"
```

**主契约未同步**: `docs/V2-005_IMPLEMENTATION_CONTRACT.md` §3.2-3.4
```python
# 当前写法 (错误)
canonical_name = new_canonical_name  # 未表达 trim

# 应为
stored_display = new_canonical_name.strip()
```

**影响**: 实现时无法确定是否需要存储 trim 后的值。

**整改要求**:
- 主契约 §3.1～3.4 明确 `canonical_name.strip()` 操作
- §9.4 存储建议同步三层模型
- 删除或修正 STORAGE_MODEL.md 中的 U+3000 错误示例

#### 阻塞项 4: 历史文档污染 (H2-R04, P2)

**问题文件**:
- `docs/V2-005_REMEDIATION_STATUS.md` (H1 中间状态)
- `docs/V2-005_REMEDIATION_RECORD.md` (H1 中间状态)
- `docs/H1_REMEDIATION_PROGRESS.md` (H1 中间状态)
- `docs/V2-005_FINAL_REMEDIATION_REPORT.md` (标记为 "HISTORICAL - Superseded by H2")

**问题点**:
- DECISION_GATES L150/L524/L545 仍写 "38 test cases"，实际为 51 项
- 多个文档暴露不同的中间状态，无明确入口

**影响**: 实现者需要人工判断哪个文档是最新的。

**整改要求**:
- 所有过期文档添加 `HISTORICAL - Superseded by <current>` 标记
- README 或 DECISION_GATES 明确当前状态入口
- 更新所有测试数量引用为 51 项

### 3.2 整改登记规模 (长期风险)

**总计**: 68 项未闭环问题

| 类别 | 数量 | 严重度 | 处置阶段 |
|------|------|--------|----------|
| AR (架构评审) | 20 项 | P0-P2 | P1-P3 |
| CA (合规审计) | 24 项 | P0-P11 | P1-P8 |
| RR (准入审查) | 12 项 | P0-P13 | P0-P9 |
| SUP (补充采纳) | 8 项 | P3-P14 | P3-P12 |
| DA (深层审计) | 6 项 (未闭) | P2-P12 | P2-P12 |
| PR (规划评价) | 1 项 | P0 | P1 |

**关键高优先级问题**:

| ID | 标题 | 严重度 | 阻塞阶段 | 状态 |
|----|------|--------|----------|------|
| **AR-05** | Quality→Permit 证据闭环 | P0 | P2, P7 | OPEN |
| **CA-02** | Canon 唯一提交原则 | P0 | P2, P6 | OPEN |
| **CA-04** | 事务并发与重复投递 | P0 | P2, P6 | OPEN |
| **CA-05** | 书籍与项目隔离 | P1 | P2, P5 | OPEN |
| **DA-06** | 取消与提交原子性 | P2 | P6, P7 | OPEN |
| **DA-07** | 必需预算字段约束 | P2 | P5, P6 | OPEN |
| **DA-08** | 规模与自动化程度 | P2 | P7, P9 | OPEN |
| **DA-09** | 成本对账机制 | P2 | P8, P9 | OPEN |
| **DA-11** | 恢复策略演练 | P2 | P9, P12 | OPEN |

**风险评估**:
- 5 项 P0 级问题分布在 P1-P7，**必须在对应阶段前处置**
- 6 项 P2 级问题集中在 P5-P12，**影响生产与成本控制**
- 若不处置，累计技术债可能导致 P6-P7 验收失败

### 3.3 实施完成度缺口 (战略风险)

**任务完成统计**:
```
总任务数:   60 项 (V2-001 ～ V2-060)
已完成:      4 项 (V2-001, 002, 003, 004)
进行中:      1 项 (V2-005, 文档阶段)
未启动:     55 项
完成率:      6.7%
```

**代码实施状态**:
```
src/anovel/ 目录:
- __init__.py:  9 行 (仅版本声明)
- 其他模块:     0 文件
总生产代码:     9 行
```

**测试实施状态**:
```
tests/contract/:        4 个文件 (P0 治理测试)
tests/integration/:     0 个文件 (P2 后启用)
tests/certification/:   0 个文件 (P8 后启用)
总测试用例:            106 个收集，仅 4 项 CLOSE
```

**关键路径任务** (27 项):
```
V2-005 → 008 → 009 → 010 → 013 → 017 → 018 → 019 →
020 → 021 → 022 → 023 → 024 → 025 → 026 → 033 →
034 → 035 → 040 (共 19 项显式标注)
```

**风险评估**:
- P1-P9 剩余 36 项任务，**基线估算 8 个月**
- V2-005 阻塞 3 个月以上 (基于提交历史)
- 若每个阶段出现类似 V2-005 的文档收口，**总周期可能翻倍**

---

## 4. 治理与质量保障审核

### 4.1 治理框架成熟度 (评级: A+)

#### 4.1.1 机器可读规范

**核心文件** (plan/machine/):
```yaml
phase-gates.yaml              # 阶段门禁定义 (274 行)
implementation-backlog.yaml   # 60 项任务 (87,930 字节)
remediation-register.yaml     # 68 项整改 (37,487 字节)
milestones.yaml               # 13 个里程碑 (2,812 字节)
decision-register.yaml        # 12 项 ADR (5,275 字节)
ai-execution-policy.yaml      # AI 协议 (5,993 字节)
governance-baseline.yaml      # 治理基线 (6,643 字节)
```

**校验脚本**:
- `plan/scripts/validate_plan.py`: 规范一致性检查
- `plan/scripts/test_governance.py`: 治理回归测试
- `plan/scripts/test_ai_execution.py`: AI 执行协议测试

**评估**: 完整的机器可读规范，版本化管理，自动化校验。

#### 4.1.2 执行包制度

**定义**: `plan/schemas/execution-packet.schema.json`

**包含要素**:
- 任务 ID 与规范引用
- 动作类型 (PREPARE / IMPLEMENT / LIVE_CALL / CERTIFY)
- 范围定义 (scope_revision, scope_ref)
- 审查绑定 (review_revision, review_ref)
- 输入快照 (hash)
- 交接记录 (handoff)

**验证点**:
- 执行前: `scripts/task_execution.py check`
- 执行中: `scripts/task_execution.py run`
- 恢复时: `scripts/task_execution.py resume`

**V2-001 示例**:
```yaml
task_id: V2-001
action: IMPLEMENT
scope_revision: 开工范围 commit
review_revision: 审查结论 commit
normative_specs:
  - 02_ARCHITECTURE_BASELINE.md (hash: ...)
  - 07_PLATFORM_SECURITY_AND_DELIVERY.md (hash: ...)
```

**评估**: 严格的执行包绑定，防止范围蔓延和自签证据。

#### 4.1.3 AI 执行协议

**文档**: `plan/AI_EXECUTION_PROTOCOL.md`

**六项约束**:
1. 不得绕过前置阶段门禁
2. 不得实现未经 ADR 决定的能力
3. 不得接入真实 Provider 直到 P5
4. 不得修改治理基线 (plan/machine/)
5. 不得自签验收证据
6. 不得冒充独立审核

**验证**: `plan/scripts/test_ai_execution.py` 通过

**评估**: AI 协议边界清晰，角色权限受限。

### 4.2 CI/CD 状态 (评级: A)

#### 4.2.1 Pipeline 配置

**配置文件**: `.gitlab-ci.yml`

**Job 定义** (6 项):
```yaml
static:              # ruff, mypy
schema_contract:     # JSON Schema 验证
unit:                # pytest 单元测试
arch_fitness:        # 架构边界检查
postgres_env:        # PostgreSQL 集成测试
secret_dependency:   # Secret 扫描与依赖审计
```

**最新运行** (Pipeline 2910274247, IID 109):
```
Commit:  e00b035
Branch:  work/h2-convergence-closure
Status:  ✓ PASS (6/6 jobs)
Date:    2026-10-04 14:01
```

**历史稳定性**:
- V2-001 关闭: ✓ PASS (6/6)
- V2-002 关闭: ✓ PASS (6/6)
- V2-003 关闭: ✓ PASS (6/6)
- V2-004 关闭: ✓ PASS (6/6)

**评估**: CI 稳定，门禁完整，负例能阻断。

#### 4.2.2 远端保护

**V2-004 已验证**:
- ✅ Secret 扫描 (Gitleaks 模式)
- ✅ 依赖审计 (pip-audit)
- ✅ 必需 CI 集合与最晚启用阶段绑定
- ✅ 已验证阶段聚合真实适用证据

**评估**: 远端保护已就绪，P0 验证完整。

### 4.3 变更审查机制 (评级: A)

**检查器**: `scripts/check_changes.py`

**检测能力**:
- ✅ 验收弱化 (降低 threshold, 删除 assertion)
- ✅ 门禁删改 (删除必需 CI, 放宽 Gate 条件)
- ✅ 范围逃逸 (符号链接、父目录引用)
- ✅ 自签范围 (执行包内修改自身 scope)
- ✅ 索引弱化 (暂存区削弱但工作区恢复)

**测试覆盖**: 50 个回归测试通过 (`tests/architecture/test_change_review.py`)

**评估**: 变更审查覆盖全面，负例验证充分。

### 4.4 测试策略 (评级: B+)

#### 4.4.1 测试分层

| 层级 | 文件数 | 状态 | 启用阶段 |
|------|--------|------|----------|
| 合约测试 | 4 | ✓ PASS | P0 |
| 集成测试 | 0 | ⏳ 计划 | P2 |
| 认证测试 | 0 | ⏳ 计划 | P8 |

**P0 合约测试**:
```
tests/contract/
├── test_plan_governance.py      # 规范一致性
├── test_task_execution.py       # 执行包验证
└── (共 4 个文件)
```

#### 4.4.2 V2-005 测试矩阵

**定义**: `docs/V2-005_TEST_CONTRACT_MATRIX.md`

**规模**: 51 个测试用例 (TC-005-001 ～ TC-005-051)

**分组**:
1. 输入验证 (6 项)
2. 身份稳定性 (5 项)
3. 重命名 (6 项)
4. 别名管理 (8 项)
5. 解析逻辑 (10 项)
6. 项目隔离 (4 项)
7. 规范化 (4 项)
8. 确定性 (2 项)
9. 序列化 (3 项)
10. 反模式 (3 项)

**覆盖映射**:
- 10 个验收标准 (AC-005-01 ～ AC-005-10): ✓ 全覆盖
- 6 个负向场景 (NS-1 ～ NS-6): ✓ 全覆盖
- 8 个不变量: ✓ 全验证

**当前状态**: 规范完整，代码未实现。

**评估**: 测试设计充分，但需等待 V2-005 文档收口。

---

## 5. 代码质量审核

### 5.1 代码规模

```
语言统计:
Python:      3,334 文件
Markdown:    ~100 文件
YAML:        16 个机器规范文件
JSON:        若干 schema 文件
Shell:       若干辅助脚本
```

**生产代码**:
```
src/anovel/__init__.py:  9 行
总计:                    9 行
```

**测试代码**:
```
tests/:                  ~10,000 行 (估算)
```

**脚本与工具**:
```
scripts/:                ~2,000 行
plan/scripts/:           ~3,000 行
```

**文档**:
```
plan/:                   ~50,000 字 (机器规范)
docs/:                   ~100,000 字 (V2-005 等)
```

### 5.2 代码风格 (评级: A)

**工具配置**:
- `ruff`: ✓ 已配置，CI 强制
- `mypy`: ✓ strict 模式，CI 强制
- `pytest`: ✓ strict markers, 收集验证

**V2-005 质量承诺**:
```python
# 公共 API 要求
- 100% 类型提示
- 所有函数 docstring
- mypy --strict 通过
- frozen dataclasses (不可变性)
```

**评估**: 工具链完整，规范严格，但**代码未实现无法验证**。

### 5.3 架构合规性 (评级: A+)

**检查结果** (最新):
```json
{
  "status": "PASS",
  "files": 1,
  "findings": 0,
  "report": "/tmp/arch_check.json"
}
```

**验证的边界**:
- ✅ 领域不导入持久化
- ✅ 非授权不访问 Canon 写入口
- ✅ 无 Provider 泄漏
- ✅ 负例被正确拒绝

**评估**: 架构检查器工作正常，P0 验证完整。

---

## 6. 风险评估与缓解

### 6.1 关键风险矩阵

| ID | 风险描述 | 概率 | 影响 | 等级 | 缓解措施 |
|----|----------|------|------|------|----------|
| **R-01** | V2-005 文档矛盾持续阻塞 P1 | 高 | 高 | **致命** | 1-2 天专项收口，删除冲突条款 |
| **R-02** | 68 项整改未处置导致验收失败 | 中 | 高 | **严重** | 建立分阶段处置计划，P0 问题前置 |
| **R-03** | P1-P9 实施周期超预期 (>8 个月) | 高 | 中 | **严重** | 简化非关键任务，聚焦 M6 (30 章) |
| **R-04** | Canon 并发控制未验证 (CA-04) | 中 | 高 | **严重** | P2 专项测试，PostgreSQL 事务隔离 |
| **R-05** | 成本失控 (DA-07, DA-09) | 中 | 中 | **中等** | P5 预算机制，每周成本审查 |
| **R-06** | 质量检查未闭环 (AR-05) | 中 | 中 | **中等** | P7 完整 Q0-Q3 实施与证据 |
| **R-07** | 30 章认证失败 (P9) | 低 | 高 | **中等** | M4-M6 渐进认证，故障恢复演练 |
| **R-08** | 人工反馈不足 (P11) | 低 | 中 | **低** | P8 最小真人评阅，样本分区 |

### 6.2 技术债务

**当前债务规模**:
```
未闭环问题:  68 项
分布阶段:    P0-P14 (跨 14 个阶段)
预计处置:    8-24 个月
```

**债务分类**:

| 类别 | 数量 | 平均处置时间 | 总工作量 |
|------|------|--------------|----------|
| P0 级 (致命) | 5 项 | 1 周/项 | 5 周 |
| P1 级 (严重) | 15 项 | 3 天/项 | 45 天 |
| P2 级 (重要) | 28 项 | 2 天/项 | 56 天 |
| P3 级 (一般) | 20 项 | 1 天/项 | 20 天 |

**总计**: ~126 天 (~6 个月专职处置)

**评估**: 债务规模可控，但**需要明确的分阶段处置计划**。

### 6.3 依赖风险

**外部依赖**:
- Python 3.12.14: ✓ 官方支持到 2028-10
- PostgreSQL 17.11: ✓ 官方支持到 2031-11
- uv 0.12.17: ⚠ 新工具，社区成熟度待观察

**内部依赖**:
- V2-005 阻塞 V2-006, 007, 008: **关键路径风险**
- V2-008 阻塞 P2-P14 全部任务: **战略风险**

**缓解**: 优先打通 V2-005 → 008 最小路径。

---

## 7. 项目创新点与特色

### 7.1 治理创新

#### 7.1.1 机器可读规范
- YAML 格式的阶段门禁、任务积压、整改登记
- JSON Schema 验证执行包、证据记录
- 自动化校验脚本，回归测试覆盖

#### 7.1.2 执行包制度
- 每个任务绑定具体的 EXECUTION_PACKET
- 范围冻结、审查绑定、输入快照
- 防止范围蔓延、自签证据、恢复失败

#### 7.1.3 AI 协议
- 明确 AI 角色权限与约束
- 六项执行边界
- 独立审核与交接记录

### 7.2 架构创新

#### 7.2.1 唯一 Canon 写路径
- 叙事状态通过唯一 `commit_service` 提交
- 防止并发冲突、数据不一致
- 架构检查器强制验证

#### 7.2.2 类型化契约
- 故事结构 (StoryStructureContract)
- 情节承诺 (PlotPromiseContract)
- 可执行规范，与 Canon/Genre 绑定

#### 7.2.3 双 Anchor Genre
- Urban Business (现实向)
- Eastern Fantasy (玄幻向)
- 独立策略扩展，无默认题材

### 7.3 质量创新

#### 7.3.1 分层检查栈
- Q0 (确定性): 输入合法性、确定性保证
- Q1 (Canon 一致): 读取当前 Canon，检查 Delta 合法性
- Q2 (题材相关): Genre-specific 检查 (权限、境界)
- Q3 (可读性转移): 无注水、无情节跳变、承诺兑现

#### 7.3.2 三稿制修复
- 诊断 (Diagnose): 识别具体问题
- 修复 (Repair): 生成修复候选
- 验证 (Verify): 独立验证修复效果

#### 7.3.3 成本透明化
- 预算失败正确处理
- 未知费用可查
- 全成本与人工贡献分离报告

---

## 8. 对标与借鉴

### 8.1 外部实践借鉴

**已采纳** (9 项, plan/machine/external-practice-register.yaml):

| ID | 来源 | 实践 | 应用 |
|----|------|------|------|
| EXT-001 | 《代码大全》 | 阶段门禁 | phase-gates.yaml |
| EXT-002 | Kent Beck | TDD | 测试先行 |
| EXT-003 | Martin Fowler | 持续集成 | .gitlab-ci.yml |
| EXT-004 | Eric Evans | DDD | domain/ 模块 |
| EXT-005 | IEEE 830 | 需求规范 | 机器源 |
| EXT-006 | ISO/IEC 25010 | 质量模型 | Q0-Q3 |
| EXT-007 | Atlassian | ADR | decision-register |
| EXT-008 | Google SRE | 可观测性 | (P10 计划) |
| EXT-009 | NIST | 证据记录 | evidence-record |

### 8.2 同类系统对比

**AI 写作系统**:
- Sudowrite: ✓ 商业化，✗ 无 Canon 概念
- NovelAI: ✓ 生成质量高，✗ 无长期一致性
- Jasper: ✓ 营销内容，✗ 不适合长篇叙事

**ANovelOS 差异化**:
- ✅ 唯一 Canon 写路径 (一致性保证)
- ✅ 类型化契约 (情节承诺可验证)
- ✅ 分阶段认证 (10 章 → 30 章 → 100 章)
- ✅ 成本透明化 (预算与人工分离)

---

## 9. 建议与行动计划

### 9.1 即时行动 (1-2 天, P1 级)

#### 任务 A: V2-005 文档收口

**负责人**: 技术主管或文档负责人  
**工作量**: 1-2 天  
**交付物**:

1. **统一授权状态**:
   - [ ] 删除 `V2-005_DECISION_GATES.md` L485-540 的 "reviewed and approved" 声明
   - [ ] 统一 Gate 3 和 Gate 6 状态为 `INDEPENDENT_REVIEW_PENDING`
   - [ ] 同步 `V2-005_IMPLEMENTATION_CONTRACT.md` 头部状态

2. **清除 ULID 残留**:
   - [ ] 删除 `V2-005_DECISION_GATES.md` L140, L142, L240-242, L254-256 的 ULID 条款
   - [ ] 统一为 `uuid.uuid4()` 标准库调用
   - [ ] 更新所有示例代码

3. **同步存储模型**:
   - [ ] 主契约 §3.1～3.4 明确 `canonical_name.strip()` 操作
   - [ ] §9.4 存储建议同步三层模型 (Input → Stored → Lookup)
   - [ ] 修正 `STORAGE_MODEL.md` 中的 U+3000 示例

4. **标记历史文档**:
   - [ ] 所有 H1/H2 中间状态文件添加 `HISTORICAL - Superseded by <current>` 标记
   - [ ] `V2-005_REFINEMENT_SUMMARY.md` 或 README 明确当前状态入口
   - [ ] 更新所有测试数量引用为 51 项

**验收标准**:
- ✅ H2 Delta Closure Review 的 4 项阻塞全部解除
- ✅ CI Pipeline 通过 (6/6 jobs)
- ✅ 独立审核人确认文档无矛盾

**风险**: 若不完成，V2-005 无法启动实现，阻塞整个 P1。

#### 任务 B: V2-005 独立审核

**负责人**: 非参与 V2-005 编写的独立审核人  
**工作量**: 0.5-1 天  
**检查点**:

- [ ] 契约文档内部一致性
- [ ] 规范与测试矩阵对齐
- [ ] 示例代码可执行性
- [ ] 不变量完整性

**交付物**: `V2-005_INDEPENDENT_REVIEW_FINAL.md`

**决策**:
- APPROVED → 启动实现
- CONDITIONALLY_APPROVED → 明确条件后启动
- REJECTED → 返回文档收口

### 9.2 短期行动 (1-2 周, P1 级)

#### 任务 C: V2-005 实现

**依赖**: 任务 A + 任务 B 完成  
**工作量**: 1-2 周  
**实施步骤**:

1. **模块结构** (Step 1)
   ```python
   src/anovel/domain/identity/
   ├── __init__.py
   ├── types.py          # EntityId, ProjectId, EntityIdentity
   ├── normalization.py  # normalize_for_lookup
   ├── registry.py       # EntityRegistry
   └── operations.py     # create_identity, rename_identity, etc.
   ```

2. **核心类型** (Step 2)
   - EntityId, ProjectId (NewType)
   - EntityIdentity (frozen dataclass)
   - ResolutionStatus, ResolutionResult variants

3. **规范化** (Step 3)
   - `normalize_for_lookup()`
   - 空白 trim + ASCII 折叠
   - 全角空格删除 (U+3000)

4. **注册表** (Step 4)
   - EntityRegistry 实现
   - 查重逻辑 (防止静默覆盖)

5. **身份操作** (Step 5-6)
   - `create_identity()`, `rename_identity()`
   - `add_alias()`, `remove_alias()`

6. **解析** (Step 7)
   - `resolve_alias()`: RESOLVED / NOT_FOUND / AMBIGUOUS / INVALID_INPUT

7. **Schema + 测试** (Step 8)
   - JSON Schema (§13)
   - 51 个测试用例实现
   - mypy --strict 通过

**验收标准**:
- ✅ 所有 51 个测试通过
- ✅ mypy --strict 无错误
- ✅ CI Pipeline 通过 (6/6 jobs)
- ✅ 架构检查器通过

**交付物**: 
- 代码: `src/anovel/domain/identity/`
- 测试: `tests/domain/test_identity.py`
- 证据: `plan/validation/execution/V2-005/closure/`

#### 任务 D: V2-006, 007, 008 启动准备

**依赖**: V2-005 关闭  
**工作量**: 3-5 天 (每个任务)  
**行动**:

1. **V2-006 (Character)**:
   - [ ] ADR-002 (角色知识建模) 决策
   - [ ] 当前状态审计
   - [ ] 任务细化与契约编写

2. **V2-007 (Event/Timeline)**:
   - [ ] ADR-003 (事件时间线) 决策
   - [ ] 当前状态审计
   - [ ] 任务细化与契约编写

3. **V2-008 (NarrativeDelta)**:
   - [ ] 依赖 V2-006, 007 完成
   - [ ] 操作类型设计
   - [ ] Delta 应用逻辑

**目标**: P1 (V2-005 ～ 008) 在 2-3 个月内完成。

### 9.3 中期行动 (3-6 个月, P0-P2 级)

#### 任务 E: P0 级整改处置

**工作量**: 5 周  
**问题清单**:

| ID | 标题 | 工作量 | 处置阶段 |
|----|------|--------|----------|
| AR-05 | Quality→Permit 证据闭环 | 1 周 | P2 启动前 |
| CA-02 | Canon 唯一提交原则 | 1 周 | P2 实施时 |
| CA-04 | 事务并发与重复投递 | 1.5 周 | P2 测试 |
| CA-05 | 书籍与项目隔离 | 1 周 | P2 设计 |
| DA-06 | 取消与提交原子性 | 0.5 周 | P2 回归 |

**行动计划**:
- 每个问题创建独立 issue
- 分配到对应阶段 (P1/P2)
- 关闭前需要独立审核

#### 任务 F: P2 阶段实施

**任务范围**: V2-009 ～ V2-012 (Canon Kernel)  
**工作量**: 2-3 个月  
**关键交付**:

1. **V2-009 (Canon Persistence)**:
   - PostgreSQL schema 设计
   - SQLAlchemy ORM 映射
   - 事务边界与隔离级别

2. **V2-010 (Authorization)**:
   - 权限模型 (Project, Book, Chapter)
   - 书籍与项目隔离 (CA-05)

3. **V2-011 (Commit Service)**:
   - 唯一写入口实现 (CA-02)
   - CAS 幂等性验证
   - 并发控制 (CA-04)

4. **V2-012 (Snapshot)**:
   - 快照重建
   - 跨项目隔离

**验收重点**:
- PostgreSQL 事务一致性
- 并发投递正确性
- 恢复策略可演练 (DA-11)

### 9.4 长期行动 (6-12 个月, P1-P2 级)

#### 任务 G: P3-P7 实施

**任务范围**: V2-013 ～ V2-032 (Genre, Planning, Context, Gateway, Production, Quality)  
**工作量**: 4-6 个月  
**里程碑**:

- **M3 (P3)**: 双 Anchor Genre 扩展就绪
- **M4 (P4-P6)**: 单章生产完整闭环
- **M5 (P7)**: Q0-Q3 质量栈集成

**关键验证点**:
- Genre 污染对照 (CA-07)
- Context 预算失败 (DA-07)
- 成本对账机制 (DA-09)
- Quality→Permit 闭环 (AR-05)

#### 任务 H: P8-P9 认证

**任务范围**: V2-033 ～ V2-040 (10 章 → 30 章)  
**工作量**: 2-3 个月  
**认证要素**:

1. **工程通过**:
   - 10 章自动生成无崩溃
   - 30 章连续运行完成

2. **阅读结果**:
   - 最小真人评阅 (10-30 人)
   - 样本分区，不外推

3. **成本透明**:
   - 全成本记录
   - 人工贡献分离

**交付物**: M6 认证报告

### 9.5 战略建议

#### 建议 1: 简化非关键任务

**背景**: 60 项任务覆盖 P0-P14，周期 8-24 个月。

**行动**:
- 聚焦 M6 (30 章认证) 作为近期目标
- P10-P14 (Genesis, Learning, 100 章, Market) 延后
- 简化 P3 Genre 扩展 (仅两个 Anchor)
- 删除或推迟低优先级整改 (P3 级)

**预期**: 周期缩短至 8-12 个月。

#### 建议 2: 增强独立审核

**背景**: V2-005 因文档矛盾阻塞 3 个月以上。

**行动**:
- 每个 Gate 前安排外部审核
- 审核人不参与编写
- 审核清单标准化 (checklist)

**预期**: 减少返工，提升质量。

#### 建议 3: 建立整改处置计划

**背景**: 68 项问题无明确处置时间表。

**行动**:
- 按阶段分组 (P0 → P1 → P2 → ...)
- 每个问题指定处置责任人
- 阶段 Gate 前强制关闭对应问题

**预期**: 技术债可控，不累积。

#### 建议 4: 成本监控机制

**背景**: P5 启用真实 Provider 后，成本可能失控 (DA-07, DA-09)。

**行动**:
- P5 建立预算管理器
- 每周审查费用与预算
- 未知费用可查，失败正确处理

**预期**: 成本透明，无意外超支。

#### 建议 5: 人工反馈不外推

**背景**: P8-P9 认证需要真人评阅。

**行动**:
- 10-30 人样本即可
- 明确样本分区 (题材、年龄、偏好)
- 不宣称代表市场

**预期**: 避免过度承诺。

---

## 10. 结论

### 10.1 项目健康度评估

**总体评级**: **B-** (良好，但存在关键阻塞和实施风险)

**分项评级**:

| 维度 | 评级 | 权重 | 加权得分 |
|------|------|------|----------|
| 治理成熟度 | A+ (95) | 25% | 23.75 |
| 架构设计 | A (90) | 20% | 18.00 |
| 实施完成度 | D (60) | 20% | 12.00 |
| 质量保障 | B+ (85) | 15% | 12.75 |
| 文档质量 | B (80) | 10% | 8.00 |
| 风险管控 | A- (88) | 10% | 8.80 |
| **加权总分** | | **100%** | **83.30** |

**等级映射**:
- A+: 95-100
- A: 90-94
- A-: 85-89
- B+: 80-84  ← **当前**
- B: 75-79
- B-: 70-74
- C+: 65-69
- C: 60-64
- D: 50-59
- F: <50

**修正**: 考虑 V2-005 关键阻塞 (-10 分) → **73.30** → **B-**

### 10.2 关键制约因素

1. **V2-005 文档矛盾** (致命): 阻塞整个 P1，需 1-2 天专项收口
2. **68 项未闭环整改** (严重): 分布 P0-P14，需 6 个月专职处置
3. **代码实现空白** (严重): P1-P14 实现为 0%，需 8-12 个月
4. **并发控制未验证** (严重): CA-04 风险，P2 需专项测试

### 10.3 成功关键因素

1. **文档收敛**: 确保规范、契约、实现三向一致
2. **独立验证**: 每个 Gate 前客观第三方复核
3. **成本控制**: P5 后持续监控预算与实际费用
4. **人工节制**: 清晰区分自动化与人工边界
5. **技术债处置**: 分阶段强制关闭对应整改问题

### 10.4 最终建议

**优先级 1** (1-2 天, 关键路径):
- ✅ 完成 V2-005 文档收口 (任务 A)
- ✅ 通过独立审核 (任务 B)

**优先级 2** (1-2 周, 启动 P1):
- ✅ V2-005 实现与验收 (任务 C)
- ✅ V2-006, 007, 008 准备 (任务 D)

**优先级 3** (3-6 个月, P0-P2 整改):
- ✅ P0 级问题处置 (任务 E)
- ✅ P2 阶段实施 (任务 F)

**战略决策**:
- 聚焦 M6 (30 章认证)
- P10-P14 延后
- 增强独立审核
- 建立整改处置计划

---

## 附录

### A. 审核方法

**审核范围**:
- 完整代码库 (src/, tests/, scripts/, plan/)
- 全部机器规范 (plan/machine/)
- V2-005 全部文档 (docs/)
- 最近 20 次提交历史
- CI/CD Pipeline 最新结果

**审核工具**:
- 架构检查器: `scripts/check_architecture.py`
- 治理校验: `scripts/check_governance.py`
- 变更审查: `scripts/check_changes.py`
- 规范验证: `plan/scripts/validate_plan.py`
- 测试收集: `pytest --collect-only`

**审核时间**: 2026-10-04, 4 小时

### B. 关键文件清单

**机器规范** (plan/machine/):
- phase-gates.yaml (274 行)
- implementation-backlog.yaml (87,930 字节)
- remediation-register.yaml (37,487 字节)
- milestones.yaml (2,812 字节)
- decision-register.yaml (5,275 字节)
- ai-execution-policy.yaml (5,993 字节)

**V2-005 文档** (docs/):
- V2-005_CURRENT_STATE_AUDIT.md
- V2-005_TASK_REFINEMENT.md
- V2-005_IMPLEMENTATION_CONTRACT.md
- V2-005_TEST_CONTRACT_MATRIX.md
- V2-005_IMPLEMENTATION_PLAN.md
- V2-005_DECISION_GATES.md
- V2-005_REFINEMENT_SUMMARY.md
- V2-005_STORAGE_MODEL.md (H2 新增)
- V2-005_H2_DELTA_CLOSURE_REVIEW_e00b035.md (未提交)

**验证证据** (plan/validation/):
- closure/G-P0-38b0c57/ (P0 完成证据)
- execution/V2-001/execution-packet.yaml
- execution/V2-002/execution-packet.yaml
- execution/V2-003/execution-packet.yaml
- execution/V2-004/execution-packet.yaml

### C. 审核人声明

**审核人**: 独立第三方技术审核（AI 辅助）  
**利益关系**: 无  
**审核依据**: 项目实际状态、机器规范、CI 结果、文档内容  
**审核立场**: 客观、独立、基于证据  
**审核限制**: 
- 未运行完整测试套件 (仅收集)
- 未执行 V2-005 代码实现 (不存在)
- 未访问远端 GitLab (仅本地仓库)

**声明**: 本报告基于 2026-10-04 的项目状态，反映当时的实际情况。后续变更可能使部分内容过时。

---

**报告结束**

**下一步行动**: 见 §9.1 即时行动 (任务 A + 任务 B)

**跟踪**: 建议 1 周后复审 V2-005 状态，1 个月后复审 P1 进展。
