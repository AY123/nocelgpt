# V2-004 实际 Developer 写入权限控制

本次依据当前任务 AT-V2-004-07 执行有界真实实验。新审核报告仅作输入，其 ACCEPTED、90 天期限及 acceptance/v2-004 分支建议均未自动成为批准或规范。

| 控制 | 实际身份 | 实际结果 | 可核验来源 |
|---|---|---|---|
| 在允许的隔离开发分支创建无害文件 | Developer2897322 / role30 | WRITE_SUCCEEDED | commit8e751d401f03a463ff8fd6e6d97d9f81f694ae0c，父c0ba3a7；文件及hash回读匹配 |
| 相同filecreate请求写入已保护main | 同一Developer | HTTP403 / WRITE_DENIED | 实际create_commit接口返回“not allowed to push into this branch”；main前后SHA882d0cdf833464dd6a5ebfac3a542204c32cd325一致 |
| 在同一测试分支创建不带变量的流水线 | 同一 Developer | PIPELINE_CREATION_SUCCEEDED | pipeline 2910430587，source=api，SHA 8e751d4，创建及 GET 回读匹配 |
| 同一请求携带无害测试变量 | 同一 Developer | HTTP 400 / VARIABLE_USAGE_DENIED | 明确返回 Insufficient permissions to set pipeline variables；HTTP 400 未改写为 403 |

[完整实际写入记录](actual-developer-write-controls.json)保留有效payload、工具、Actor来源、保护分支前后状态、实际403错误和提交/文件回读。测试分支为 `codex/v2-004-permission-probe-c0ba3a7-20261004`，只新增2行无害文本；未修改保护规则、runner或安全例外。developer成功写入的同一凭证排除了“只有无效token”的伪拒绝；预先确认目标分支存在及新增路径不存在，不将404或无效参数算权限拒绝。

[Actor来源](owner-developer-observations.json)来自6次真实project-scoped安全GET。purpose connector提供结构化结果和明确HTTP错误，未提供原始HTTP bytes；不编造原始响应hash。

[流水线变量使用记录](actual-pipeline-variable-controls.json)保存上述另一组正反例。GitLab [官方变量文档](https://docs.gitlab.com/ci/variables/#restrict-pipeline-variables)将此明确错误用于变量使用权限不足；结合相同身份、项目、接口和 ref 的无变量创建成功，可判为真实使用权限拒绝。该结果没有证明 Developer 无权修改项目设置，也没有证明测试分支的六门禁通过。

[写入回读复核](write-control-audit.json)的 22 项检查通过，[九次只读回读](write-control-readback-observations.json)保留实际提交、文件及分支来源。复核没有重新发起被拒绝的写请求，403 来源仍是原操作返回；不同 agent 只读复核不构成独立人员验收。

[变量使用复核](pipeline-variable-control-audit.json)的 15 项检查通过，[流水线只读回读](pipeline-variable-readback-observation.json)确认同一 Developer、项目、ref、SHA 及 source=api。没有新增流水线触发，读取时 running 的状态原样保留。

[审核意见评估](review-assessment.json)区分现行事实与建议。实施和验证仍由同一操作者承担；不同权限账号不等于独立人员审核。以上只证明允许的开发写入及现有main写入保护，不替代最终acceptance ref、保护规则/可信CI/变量修改、自批例外或真实防删除门禁控制。AT-V2-004-07仍NOT_VERIFIED，权限整体UNKNOWN，V2-004 IN_PROGRESS，P0 NOT_VERIFIED。

下一动作仍需真实 owner 依据、36 项有期精确例外批准和持续 runner 主机授权。实际 Developer 仓库写入请求两次、流水线创建请求两次，正反例各一；保护配置、runner、审批均未改动。最终同一候选 SHA 六门禁全 PASS、受保护执行及完整权限正反例后再验收。

[主机可行性只读记录](host-feasibility.json)：现有Mac/Docker可作为待授权候选，LinuxARM64扫描工具pin已有实现；未登记runner或部署。独立验收branch不必冻结dev_gpt，但仍需不可由普通Developer改写的固定CI及driver/基线/政策和真实保护控制。
