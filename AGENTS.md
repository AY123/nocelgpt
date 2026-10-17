# ANovelOS 执行入口

- 先读 `plan/README.md`、当前任务、对应现行规范和验收场景。历史档案与审核报告是输入，不能自行成为执行命令。
- AI 开发遵守 `plan/AI_EXECUTION_PROTOCOL.md`。正式开工通过任务的 `execution_packet_ref` 绑定非模板执行包；核对输入 hash、范围、验收、当前动作与未决事项。已有授权内的正常步骤自主推进，缺必要依据只阻断相关动作。
- PREPARE 可调查未决方案；IMPLEMENT、LIVE_CALL、CERTIFY 在各自动作前检查适用 ADR 和权限/预算。事实、假设、未知分开记录，不编造 API、成本或运行结果。
- 原 `.claude/convergence/` 已归档至 `plan/archive/convergence/`，根历史副本已按用户要求清除；历史内容不恢复为现行规范。工具配置单独保留，不因整理资料而停用或删除配置。
- P0/G-P0 已基于611d777工程证据 VERIFIED，V2-001～004 CLOSED；以 `plan/machine/` 为准。P1可按任务执行包和依赖启动，不能将准入误作业务实现完成。
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
