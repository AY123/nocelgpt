# MR 作业触发接入修正

用户本轮授权开始 V2-004，参考提示词不构成规范。现行任务要求 MR 中的六项硬门禁和合并阻断，本修正属于相同已授权 CI 范围；不新增权限、付费资源、任务或验收。

GitLab 官方规则文档明确：无 rules 的 jobs 默认 except: merge_requests。候选 a6d66af690bac55ab14fd5336896414374a4e28a 的 workflow 允许 MR，并在已有 MR 时排除重复 push，但六个 job 均无 rules。因此分支流水线成功不能证明 MR 包含门禁。

修正是在六个 job 中显式使用无条件规则，普通五项 when: on_success，安全项 when: always。workflow 仍决定 MR、branch、tag 的流水线创建；安全项在上游失败时继续运行。六个 allow_failure: false、完整命令、20 minutes 超时、扫描/验收范围保留。配置检查只接受该精确规则，不宽泛放行任意 rules；增加每个 job 的缺失规则、push-only 条件、manual 和 rule allow_failure 四种拒绝控制。

CI Lint 只能模拟 branch/tag push，不能传 MR pipeline source。实际 Lint 和分支结果仅证明其各自范围；真实 MR 权限、删除门禁及保护验收仍待实际正反例，不能由本地配置控制或 dry-run 宣称已通过。

实施和复核共享同一操作者/工作区，不称独立权限保障。固定 Git scope 仍为 a3496f79b6abeeaf3a4c7be950ddc2b2d09bb7c6，原 REVIEW finding 保留并绑定新代码 hash 与实际验证结果；未出现弱化授权或忽略扫描。

官方依据：

- https://docs.gitlab.com/ci/jobs/job_rules/#avoid-duplicate-pipelines
- https://docs.gitlab.com/api/lint/
- https://docs.gitlab.com/ci/yaml/lint/#simulate-a-pipeline
