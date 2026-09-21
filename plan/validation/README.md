# 校验结果的解释

`plan-validation.json`：当前资料结构、冻结身份、阶段/任务图、引用、来源哈希和生成视图检查。`validator-self-test.json`：通过故意破坏输入确认资料验证器能拒绝错误。

1.1 增加外部经验的来源/任务/场景引用、双向归属、无证据 VERIFIED、暂缓阶段和验收断言同步检查。`generated/EXTERNAL_PRACTICE_MAP.md` 由同一机器登记生成；不会联网验证来源真实性或运行上游项目。

两者都不是工程 P0 退出、业务测试、PostgreSQL、远端 CI、真实 Provider 或阅读/商业认证。正文与业务语义仍需实施者审核，程序没有声称证明全部自然语言没有歧义。

本目录属于可再生成输出，不纳入内容清单自身的哈希闭环；结果绑定 `FILE_MANIFEST.json` 的 SHA-256。后续任务证据可按任务归档在本目录下，但不得复用本资料 PASS 当运行 PASS。

## v1.2 结果范围

新增治理最低义务、类型化证据、双向关联与隔离正反测试。`governance-regression.json` 记录合格临时完成链及单点负例；`governance-probe-v1.2.json` 保留旧十个反例在当前规则下的复测。两者均不是实际工程任务完成。

`source_snapshot_baseline_commit` 仅指历史资料来源；`validated_repository_revision` 指校验时 checkout，`validated_worktree_dirty` 说明工作区是否有未提交变更。实际计划输入由 manifest SHA 标识，不能把有改动的工作区校验说成 HEAD 已提交内容的验证。导出包没有 Git 信息时保持 null，不猜提交号。
