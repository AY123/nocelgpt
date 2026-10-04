# V2-004 可信 CI 与权限落地候选

记录性质：PREPARE 方案，尚未变更平台、登记 runner 或获得验收。实施和验证仍由同一操作者承担；Owner 与 Developer 的有效凭证/操作区分不等于独立人员复核。任务继续 IN_PROGRESS，P0 NOT_VERIFIED。

## 已核实边界

项目 86656946 已要求成功 pipeline 才允许合并。实际 dev_gpt 未保护、main 允许 Maintainer push/merge；实际执行 runner54907241 是 GitLab.com instance shared、not_protected；ci_config_path 为空，六作业和检查器来自候选同仓库。Owner 无权以项目权限将该 instance runner 直接改成 protected。a6d66af 的真实流水线五项成功，安全硬失败；来源匹配不能替代可信执行。

## 最小平台配置候选

1. 保留普通 feature 分支用于 Developer 实施；最终验收 ref dev_gpt 冻结后保护为 push No one（access_level 0）、merge Maintainer（40）、allow_force_push false，逐项核对所有匹配 wildcard，防止宽规则覆盖。main 相同合并边界。保护动作改变现有直接推送流程，不能在当前普通代码交付前执行。
2. only_allow_merge_if_pipeline_succeeds 保持 true，allow_merge_on_skipped_pipeline 设 false；ci_pipeline_variables_minimum_override_role 设 no_one_allowed，防止高优先级变量改写固定门禁。平台 API 实际支持/有效值需读取后核验，不将示例当已生效。
3. 使用普通实施凭证不能改写的固定 CI 配置快照；ci_config_path 指向精确受保护配置项目/ref。该快照须包含固定门禁、可信检查器/基线/扫描政策和有审计的修订规则，不能仅远置 YAML 后继续信任候选中可改写的 driver。普通 Developer 只有读取权限；Owner 规则修改单独留痕，不使用 Free 可选 approval 冒充强制例外批准。新配置项目/ref 尚未创建，身份未知。
4. 使用已授权 Linux/Docker 主机上的 project runner，实际 project 绑定、access_level ref_protected、run_untagged false、专属 tag。记录真实 runner ID、版本、架构、命令和可信配置 hash 后才填 trusted_execution。没有已授权主机或 runner；不购买、不声称总成本零、不修改共享 instance runner。
5. MR 使用 protected resources 时，同项目 source 与 target 均须 protected，触发者具目标 push/merge 权限且开关有效；当前普通 Developer 不能作为 protected runner 正例。冻结后由 Owner 创建精确 SHA 的新流水线/新 MR 流水线，不能重试旧 job 并假定其保护资格改变。

## 实际正反例候选

- Developer 读取配置和在普通 feature 分支做无害提交应成功；对受保护配置写入、保护规则/ci_config_path/变量覆盖修改、直接 push 验收 ref 应明确被拒绝。使用合法 payload 与真实有权限身份对照，不能将404、无网络或无效参数视为越权403。
- 无害失败使六项门禁失败并阻断合并；删除 gate、后移 stage、增加 allow_failure、skip/排除验收须在可信配置下失败。经适用授权的正常修订应成功，旧反例和处置保留。
- 最终同一 SHA 全六项绿色、全部原始产物和来源合同匹配、真实 PostgreSQL连接、权限及反删除控制具证据后，才登记 CI/验收与 P0 退出。

## 尚缺的执行依据

需要针对上述冻结 ref/外部可信配置/项目 runner 的具体平台配置授权，以及可使用的 Linux/Docker runner 主机；有费用则另需明确上限。用户已有开始 V2-004 和正常代码推送授权仍支持当前修复、现有 Free CI、只读来源检查，局部缺口不阻断这些动作。历史三组疑似凭据还需提供脱敏撤销/轮换记录，不能试用密钥、删除文本或增加忽略来代替。

官方依据：

- [自定义 CI 配置](https://docs.gitlab.com/ci/pipelines/settings/#specify-a-custom-cicd-configuration-file)
- [受保护分支与匹配规则](https://docs.gitlab.com/user/project/repository/branches/protected/)
- [Runner 修改权限](https://docs.gitlab.com/api/runners/#update-runners-details)
- [MR 受保护资源条件](https://docs.gitlab.com/ci/pipelines/merge_request_pipelines/#control-access-to-protected-variables-and-runners)
- [GitLab Free 的可选审批边界](https://docs.gitlab.com/user/project/merge_requests/approvals/)
- [流水线变量权限](https://docs.gitlab.com/ci/variables/#restrict-pipeline-variables)
- [跳过流水线合并限制](https://docs.gitlab.com/user/project/merge_requests/auto_merge/#allow-merge-after-skipped-pipelines)
- [Runner 计算额度与主机成本范围](https://docs.gitlab.com/ci/pipelines/instance_runner_compute_minutes/#enforcement)
