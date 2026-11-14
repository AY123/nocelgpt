# ANovelOS 执行入口

日常项目目录：/Users/angyang/Documents/AI/ANovelOS
- 日常开发统一使用 `main`；旧 `dev_gpt` 保留历史，不再作为开发入口。开始和交接时核对实际 Git 分支及远程同步状态。
- 远程仓库：https://github.com/AY123/nocelgpt.git
- 开工前读取当前实际 Git 状态（分支、HEAD、工作区差异）

- 先读 `plan/README.md`、当前任务、对应现行规范和验收场景。历史档案与审核报告是输入，不能自行成为执行命令。
- AI 开发遵守 `plan/AI_EXECUTION_PROTOCOL.md`。正式开工通过任务的 `execution_packet_ref` 绑定非模板执行包；核对输入 hash、范围、验收、当前动作与未决事项。已有授权内的正常步骤自主推进，缺必要依据只阻断相关动作。
- PREPARE 可调查未决方案；IMPLEMENT、LIVE_CALL、CERTIFY 在各自动作前检查适用 ADR 和权限/预算。事实、假设、未知分开记录，不编造 API、成本或运行结果。
- 原 `.claude/convergence/` 已归档至 `plan/archive/convergence/`，根历史副本已按用户要求清除；历史内容不恢复为现行规范。工具配置单独保留，不因整理资料而停用或删除配置。
- 当前 V2-001～016 CLOSED，P0/P1/P2及M0/M1/M2 VERIFIED（单人Owner工程模式）；P1最新工程验收绑定f611ba3/run39128464248。V2-009已按3d12f20/run39256589017完成六门验收（1318项0skip）；V2-010已按16259d1/run42632232950完成工程验收；P2已按下方最新汇总完成工程验收。以 `plan/machine/` 的任务、阶段和证据状态为准。
- 用户请求修改规划时，完成必要的资料和验证器修改；不要据此自动创建业务内核、部署、调用付费 Provider 或关闭工程任务。
- 保留用户已有改动。任务身份、阶段、依赖及架构范围变更需符合用户授权，并留下明确变更理由与影响记录。
- 同步正文、机器源、任务/验收场景与生成视图。使用 `python3 -B plan/scripts/validate_plan.py --write-views`、`--check`、`--self-test` 和 `python3 -B plan/scripts/test_governance.py`。
- V2-002 提供 `scripts/check_governance.py` 聚合现行检查，`scripts/task_execution.py` 核对任务动作并支持恢复。V2-003 的本地架构、差异与防降标工具已实现并完成本地验证；差异检查使用固定 scope Git pin，处置另绑定 review Git pin。任务入口对 IMPLEMENT/LIVE_CALL/CERTIFY 强制从执行包 change_review 读取 scope/review 绑定，缺绑定或 CLI 覆盖均拒绝，并检查命令前后的实际差异；架构检查须明确运行。输出到 plan 外的新目录，不替代 V2-004 可信 CI/权限边界，也不自动授权后续任务。
- 测试既要证明错误被拒绝，也要证明合格证据可以通过。不得删减门禁、把模板当证据或用资料 PASS 代替真实 CI。
- 核对实际变更与任务范围；验收删减、测试删除/skip、阈值下降、扫描排除扩大和门禁修改需与可信基线比较并记录处置，正文/机器/测试一起改弱仍须审查。不得删除用户改动以制造干净工作区。
- 换会话或模型后先读交接并核对 checkout、工作区、输入 hash 和真实运行证据；不能仅凭摘要继承完成状态。记录已完成、失败/未知、下一动作及恢复条件。
- 实施与验证角色可由同一操作者承担，但须明确标注。没有独立复核就不声称独立审核；不预设必须增加团队人数。
- 本地结构校验不证明远端来源或权限保护；动作入口、实际差异门禁与可信 CI 由 P0 落地。全 AI 开发不允许用模拟读者替代真人/市场证据。
- Canon 损坏、密钥泄露、重复提交、跨项目泄漏、硬门禁绕过或第二 Canon 写路径按现行事故规则处理。

历史证据与工作区：
- dist/validation/ 包含历史验证产物、检查点和嵌套 Git checkout
- 不作为日常开发目录，不修改其中内容
- dist/validation/v2004-github-migration-20261016/repository 是 GitHub 迁移交付副本（1fa558d），已用于统一主工作区

工具注意事项：
- scripts/ci/verify_remote.py 仅支持 GitLab API，用于历史 GitLab 运行验证
- 当前 CI 运行在 GitHub Actions (.github/workflows/v2-004.yml)
- GitHub Actions 验证使用 GitHub API 或直接查看 https://github.com/AY123/nocelgpt/actions

V2-009：ADR-005/006及root-only持久化已完成[工程验收](plan/validation/execution/V2-009/closure-20261019/ACCEPTANCE_SUMMARY.md)，绑定3d12f20/run39256589017；P2最新工程汇总见下文，V2-010已按16259d1/run42632232950完成工程验收。

V2-010本地交付：[授权章节提交协议](plan/validation/execution/V2-010/LOCAL_IMPLEMENTATION.md)。隔离测试Permit与正式生产放行分离；未据此关闭V2-011/012或P2。

V2-010已完成[工程验收](plan/validation/execution/V2-010/closure-20261109/ACCEPTANCE_SUMMARY.md)，绑定16259d1/run42632232950，1460项0skip；V2-012及P2结项见下方最新验收。

V2-011已完成[工程验收](plan/validation/execution/V2-011/closure-20261110/ACCEPTANCE_SUMMARY.md)，绑定b716e7c/run42734728628，1474项0skip；现有提交服务复用不变，新增14项真实PG竞争/恢复控制。V2-012/P2结项见下方最新验收；小说生成产品闭环仍未完成。

V2-012已完成[工程验收](plan/validation/execution/V2-012/closure-20261110/ACCEPTANCE_SUMMARY.md)，绑定416c451/run42774996789，1525项0skip；[P2/M2汇总](plan/validation/execution/P2/closure-20261110/ACCEPTANCE_SUMMARY.md)VERIFIED。当前仅有限事实Canon和隔离TEST Permit，不代表生产备份或小说生成/阅读质量已完成。V2-013验收见下方最新记录，P3仍未完成。

V2-013已完成[工程验收](plan/validation/execution/V2-013/closure-20261113/ACCEPTANCE_SUMMARY.md)，绑定b9cb604/run43424270308，1588项0skip（新63项题材契约属于UNIT子集）。ADR007已接受，两Anchor精确加载/项目快照/无匹配不改题材已验证；V2-014验收见下方最新记录，P3及自动写作/阅读质量/外部备份仍未完成。

V2-014已完成[工程验收](plan/validation/execution/V2-014/closure-20261113/ACCEPTANCE_SUMMARY.md)，绑定e688ca0/run43435762543，1699项0skip（新111项属于UNIT子集）。显式语义证据的世界规则冲突、梦境/引用区分、UNKNOWN和策略冲突已验证；不等于全文语义Q2。V2-015验收见下方最新记录，P3及自动写作/阅读质量/外部备份仍未完成。

V2-015已完成[工程验收](plan/validation/execution/V2-015/closure-20261114/ACCEPTANCE_SUMMARY.md)，绑定e9a19d0/run43539261866，1815项0skip（新88契约+28PG为子集）。都市商业严格类型/守恒及唯一Canon提交和冷重放已验证；旧Pack/政策保留。V2-016验收见下方最新记录，P3、自动写作/阅读质量/外部备份及人工标准测试书仍未完成。

V2-016已完成[工程验收](plan/validation/execution/V2-016/closure-20261114/ACCEPTANCE_SUMMARY.md)，绑定160a7e2/run43564108955，1960项0skip（新114契约+31PG为子集）。境界/能力/资源精确代价与正式Canon提交/重放已验证，旧Pack/政策保留。P3尚待汇总验收，之后V2-017；自动写作、阅读质量及外部备份仍未完成。
