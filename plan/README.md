# ANovelOS 正式架构建设实施资料

本目录的产品目标是中文长篇网文的可靠生产与真实阅读竞争力，详见[产品目标](01_PRODUCT_SCOPE_AND_SUCCESS.md)。工程验收不等于小说生产、真人阅读或市场验证。

**阶段摘要（2026-10-18）：V2-001～007 CLOSED，P0/G-P0、M0 VERIFIED，P1 尚未完成，V2-008 IMPLEMENTED，其余52个任务OPEN。** 日常开发使用 `main`。V2-007已按 `a0ea8df` / run39119023861完成六门工程验收（1071项测试、0skip），见[验收记录](validation/execution/V2-007/closure-20261018/ACCEPTANCE_SUMMARY.md)。当前 **V2-008 NarrativeDelta 已本地实现**，ADR-004已接受、专属执行包已绑定；待远程CI与正式验收，P1尚未完成。V2-006已按 `e210078` / run39106725089完成六门验收（990项测试、0skip），见[验收记录](validation/execution/V2-006/closure-20261018/ACCEPTANCE_SUMMARY.md)。实际状态读取[任务表](machine/implementation-backlog.yaml)、[阶段门禁](machine/phase-gates.yaml)和[决策登记](machine/decision-register.yaml)，本文不是平行状态源。

V2-005 工程验收绑定 `72219b4` / run39088653270，六门通过、889项测试0skip；见[验收记录](validation/execution/V2-005/closure-20261018/ACCEPTANCE_SUMMARY.md)。P0验收仍绑定历史 `611d777`，见[P0汇总验收](validation/execution/P0/closure-20261017/ACCEPTANCE_SUMMARY.md)。后续资料维护不冒称新提交已运行CI。

Plan Version：1.3.0；该版本发布于2026-09-22；历史资料来源基线：`5cffff8`。本目录是正式实施入口。审核报告的版本不替代本计划版本。

v1.3.0 将全 AI 推进的六项措施落实为[执行协议](AI_EXECUTION_PROTOCOL.md)、执行包 Schema、交接模板、本地检查及 P0 验收要求。见 [v1.3.0 变更与验证说明](changes/2026-09-22_AI_EXECUTION_GOVERNANCE.md)。P0—P14、双 Anchor、60 个任务身份/阶段/依赖不变；246 个验收场景按机器源分别记录实施和验证状态。本地回归不是业务运行或可信 CI 认证。

保留 [v1.2.2](changes/2026-09-21_REVIEW_ROUND3_ADOPTION.md)、[v1.2.1](changes/2026-09-21_REVIEW_REFRESH_ADOPTION.md)、[v1.2](changes/2026-09-21_REVIEW_ADOPTION.md)和 [v1.1](changes/2026-09-20_EXTERNAL_PRACTICES_ADOPTION.md)的历史变更记录；旧版本数字与结论只适用于其声明时点。

文档校验通过只说明资料包内部检查通过；真实CI、数据库、模型与作品质量分别核验。V2-005已交付内存实体能力，不代表完整叙事内核或题材认证已完成。

开工前清理已按用户授权完成：根目录旧资料的重复副本已删除，独有文件补充归档；旧根 ZIP 的 Git 恢复依据和逐文件去向保存在项目根下 `docs/repository-layout-migration.md` / `.json`。来源登记中的 `origin` 是历史位置，不要求根副本继续存在。2026-09-23 V2-001 已 IMPLEMENTED：具备最小 Python 骨架、锁定安装和本地真实 PostgreSQL 测试；当时远端CI尚缺，现已纳入P0汇总验收。见[执行包](validation/execution/V2-001/execution-packet.yaml)及 [ADR-001](decisions/ADR-001_RUNTIME_AND_LOCKING.md)。

## 阅读与执行顺序

1. 完整仓库先读根目录 `AGENTS.md` → 本页 → [产品目标](01_PRODUCT_SCOPE_AND_SUCCESS.md)与[架构边界](02_ARCHITECTURE_BASELINE.md)。单独导出的 `plan/` 不附带根目录文件，不据此执行仓库动作。
2. 从[机器任务表](machine/implementation-backlog.yaml)选择本次任务，核对依赖、阶段、[验收场景](machine/test-catalog.yaml)、[ADR](machine/decision-register.yaml)和已有实现。生成的[阶段任务视图](generated/PHASE_TASK_REGISTRY.md)仅供阅读。
3. 按该任务的 `normative_specs` 阅读现行规范，遵守[AI执行协议](AI_EXECUTION_PROTOCOL.md)和[任务执行规则](09_TASK_EXECUTION_GUIDE.md)。V2-008已接受ADR-004并绑定自己的执行包，本地结果见[实现说明](validation/execution/V2-008/LOCAL_IMPLEMENTATION.md)；V2-007的[工程验收](validation/execution/V2-007/closure-20261018/ACCEPTANCE_SUMMARY.md)保留原SHA，不复用其IMPLEMENT入口；每次受限动作仍核验实际输入与差异，不能把已关闭任务的执行包或模板当作开工凭证。
4. 需要追溯时再读[资料权威](00_GOVERNANCE_AND_SOURCE_AUTHORITY.md)、对应任务验收、[P0历史执行方案](PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md)与 archive。无需每次重新证明已验收的P0，也不从历史报告继承新的执行指令。

## 现行规范

| 文件 | 职责 |
|---|---|
| [00](00_GOVERNANCE_AND_SOURCE_AUTHORITY.md) | 权威、替代关系、术语和证据语义 |
| [01](01_PRODUCT_SCOPE_AND_SUCCESS.md) | 中文网文目标、范围、自动化和成本口径 |
| [02](02_ARCHITECTURE_BASELINE.md) | 模块化单体、边界、依赖、技术选择策略 |
| [03](03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md) | Narrative、Canon、Artifact、权限、幂等与历史证据 |
| [04](04_GENRE_AND_STORY_FIXTURES.md) | 双 Anchor、合法边界、标准测试书与叙事持续性 |
| [05](05_PRODUCTION_CONTEXT_QUALITY_REPAIR.md) | Contract、Context、Gateway、Workflow、Q0–Q3、Repair |
| [06](06_CERTIFICATION_AND_PRODUCT_EVALUATION.md) | 连续章节、真人阅读、版本绑定和认证证据 |
| [07](07_PLATFORM_SECURITY_AND_DELIVERY.md) | 工程、隔离、CI、安全、恢复与阶段启用 |
| [08](08_ROADMAP_AND_GATES.md) | 阶段准入/退出与里程碑完成条件 |
| [09](09_TASK_EXECUTION_GUIDE.md) | OPEN→CLOSED、执行/证据规则与复现命令 |
| [10](10_DECISIONS_AND_REMEDIATION.md) | 已采纳决定、未决 ADR、审核整改归属 |
| [AI 执行协议](AI_EXECUTION_PROTOCOL.md) | 全程 AI 开发的任务边界、动作前提、证据与交接；不新增业务架构 |

## 机器资料

- [最低治理义务](machine/governance-baseline.yaml)、[类型化执行证据](schemas/evidence-record.schema.json)、[基础来源历史索引](machine/foundational-reference-register.yaml)。
- [AI 执行约束登记](machine/ai-execution-policy.yaml)：六项措施的责任、场景与实际实现边界；[执行包 Schema](schemas/execution-packet.schema.json)、[执行包模板](templates/EXECUTION_PACKET.yaml)、[交接模板](templates/AI_HANDOFF_RECORD.yaml)。
- [任务清单](machine/implementation-backlog.yaml)：60 个任务的唯一身份、阶段、依赖和验收映射。
- [阶段门禁](machine/phase-gates.yaml)、[里程碑](machine/milestones.yaml)、[CI 门禁](machine/ci-gates.yaml)。
- [验收场景目录](machine/test-catalog.yaml)：逐套件记录状态与实际执行证据，未实施场景仍为计划。
- [决策登记](machine/decision-register.yaml)、[整改登记](machine/remediation-register.yaml)。
- [权限与证据政策](machine/authority-policy.yaml)、[来源登记](machine/source-register.yaml)。
- [外部经验采纳登记](machine/external-practice-register.yaml)：公开来源、证据局限、本地改造、关联任务/验收场景及暂缓范围。
- [机器结构约束](schemas/implementation-task.schema.json)、[校验程序](scripts/validate_plan.py)、[校验结果](validation/plan-validation.json)。

`machine/` 保存事实，`generated/` 是其只读视图。运行 `python3 plan/scripts/validate_plan.py --write-views` 更新视图；运行 `python3 plan/scripts/validate_plan.py --check` 检查一致性。PyYAML、jsonschema 已随 V2-001 纳入根 `uv.lock`；使用锁定环境。活动执行包必须在计划变动后核对来源并更新快照/hash。

## 历史资料与实施状态

[archive/](archive/) 保留来源快照；内部的 NORMATIVE、FINAL、READY、PASS 等标签都是历史内容，不构成当前授权。旧 Schema 不进入生产验证器的自动扫描路径，需经任务修正、正反例测试后进入未来的 `specs/`。

P0按用户确认的单人Owner模式验收，保护未启用是明确接受的限制，不声称具备对抗性权限隔离；见[范围修订](changes/2026-10-16_V2-004_SINGLE_OPERATOR_CLOSURE.md)。54项finding仍OPEN，精确批准有期限，未被资料整理关闭。

V2-001～003的早期实施报告与执行包记录的是各自时点；当时缺少的CI/最终验收由[P0汇总证据](validation/execution/P0/closure-20261017/ACCEPTANCE_SUMMARY.md)补齐。V2-004的旧GitLab失败、权限实验及完整仓库中的 `docs/V2-004_IMPLEMENTATION_REPORT.md` 继续保留，不是恢复旧runner或重新索取凭据补证的任务。最终证据见其[GitHub验收](validation/execution/V2-004/closure-20261016/acceptance-evidence.yaml)。V2-005的实现与边界见顶部验收入口；完整仓库另有根目录 `V2-005_HANDOFF.md`。这些记录均不证明章节生产、真实模型或作品发布已经实现。

规划验证还需运行 `python3 -B plan/scripts/test_governance.py` 与 `python3 -B plan/scripts/test_ai_execution.py`。最低义务基线不可由 `--write-views` 自动放宽；原始审核和新复测结果分开保留。V2-003 的 `scripts/check_architecture.py` 扫描完整生产包并区分 Canon 公共提交服务与内部写能力；`scripts/check_changes.py` 使用固定 scope/review Git pin 审查实际变化，`task_execution.py` 对受限动作按执行包绑定强制运行命令前后差异检查。用法见[任务执行指南](09_TASK_EXECUTION_GUIDE.md)。这些本地工具不能抵抗共享写权限者修改检查器，可信 CI 和有效权限保护仍须 V2-004 实施。V2-017 的[设计执行包](task-packets/V2-017_PLANNING_CONTRACT_PACKET.md)在 P4 消费，不替代任务开工时的正式记录。

2026-10-17精确处置补记：Owner已批准报告公开哈希的两个精确例外及52→54账本重绑定，仍到期于2027-01-06T06:07:49Z；当前54项OPEN（45精确例外、9历史风险接纳），本地完整扫描54/54消费、0未匹配、0未使用批准。工作区来源基线推进至9d71f91且原16项内容逐一不变，历史身份不变；旧52项GitHub扫描结果仍仅属于611d777。原暂停记录保留在CURRENT_HEAD_BLOCKER.json，由CURRENT_HEAD_RESOLUTION.json及authority-54/OWNER_DECISION_RECEIPT.json补充解除，不改写历史。

结项兼容修正：ARCH_FITNESS对VERIFIED/CLOSED任务执行固定scope/review的实际差异审计；进行中任务仍走原IMPLEMENT动作入口，架构检查及全部架构测试保留。原动作入口继续拒绝对完成任务重新实施。227项本地回归通过；后续完整本地结果保存在dist。六门配置与手动触发方式不变，本维护提交未触发远程CI。
