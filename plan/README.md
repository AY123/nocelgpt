# ANovelOS 正式架构建设实施资料

版本：1.0.0；整理日期：2026-09-20；来源基线：`5cffff8`。本目录是本次用户要求统一整理后的实施入口。

**当前状态：资料基线已整理，可启动 P0；V2 工程、P0 退出、业务内核及题材认证尚未完成。** 文档校验通过只说明本资料包内部检查通过，不代表 CI、数据库或真实模型已经通过。

## 阅读与执行顺序

1. [治理与资料权威](00_GOVERNANCE_AND_SOURCE_AUTHORITY.md)：确定什么是现行规范，如何处理旧资料。
2. [目标、首期范围与成功口径](01_PRODUCT_SCOPE_AND_SUCCESS.md)、[架构基线](02_ARCHITECTURE_BASELINE.md)：掌握产品边界及模块职责。
3. [路线与门禁](08_ROADMAP_AND_GATES.md)、[阶段任务表](generated/PHASE_TASK_REGISTRY.md)：按被冻结的 P0—P14 路线工作。
4. [P0 执行方案](PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md)：现在只实施 V2-001～004。
5. 开始具体业务任务前，阅读相应规范、[任务执行规则](09_TASK_EXECUTION_GUIDE.md)与[决策和整改说明](10_DECISIONS_AND_REMEDIATION.md)。

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

## 机器资料

- [任务清单](machine/implementation-backlog.yaml)：60 个任务的唯一身份、阶段、依赖和验收映射。
- [阶段门禁](machine/phase-gates.yaml)、[里程碑](machine/milestones.yaml)、[CI 门禁](machine/ci-gates.yaml)。
- [验收场景目录](machine/test-catalog.yaml)：当前均为计划场景，不冒充已实现测试。
- [决策登记](machine/decision-register.yaml)、[整改登记](machine/remediation-register.yaml)。
- [权限与证据政策](machine/authority-policy.yaml)、[来源登记](machine/source-register.yaml)。
- [机器结构约束](schemas/implementation-task.schema.json)、[校验程序](scripts/validate_plan.py)、[校验结果](validation/plan-validation.json)。

`machine/` 保存事实，`generated/` 是其只读视图。运行 `python3 plan/scripts/validate_plan.py --write-views` 更新视图；运行 `python3 plan/scripts/validate_plan.py --check` 检查一致性。需要 PyYAML、jsonschema；P0 时纳入正式依赖锁定。

## 历史资料与实施状态

[archive/](archive/) 保留来源快照；内部的 NORMATIVE、FINAL、READY、PASS 等标签都是历史内容，不构成当前授权。旧 Schema 不进入生产验证器的自动扫描路径，需经任务修正、正反例测试后进入未来的 `specs/`。

60 个任务初始状态全部为 OPEN。本次完成的是实施资料整理，不因此关闭 V2-001～004，不创建生产服务，不调用真实模型，也不发布作品。未来任务关闭的证据须写入任务记录并通过检查。
