# 校验结果的解释

`plan-validation.json`：当前资料结构、冻结身份、阶段/任务图、引用、来源哈希和生成视图检查。`validator-self-test.json`：通过故意破坏输入确认资料验证器能拒绝错误。

1.1 增加外部经验的来源/任务/场景引用、双向归属、无证据 VERIFIED、暂缓阶段和验收断言同步检查。`generated/EXTERNAL_PRACTICE_MAP.md` 由同一机器登记生成；不会联网验证来源真实性或运行上游项目。

两者都不是工程 P0 退出、业务测试、PostgreSQL、远端 CI、真实 Provider 或阅读/商业认证。正文与业务语义仍需实施者审核，程序没有声称证明全部自然语言没有歧义。

本目录属于可再生成输出，不纳入内容清单自身的哈希闭环；结果绑定 `FILE_MANIFEST.json` 的 SHA-256。后续任务证据可按任务归档在本目录下，但不得复用本资料 PASS 当运行 PASS。

## v1.2 结果范围

新增治理最低义务、类型化证据、双向关联与隔离正反测试。`governance-regression.json` 记录合格临时完成链及单点负例；`governance-probe-v1.2.json` 保留旧十个反例在当前规则下的复测。两者均不是实际工程任务完成。

`source_snapshot_baseline_commit` 仅指历史资料来源；`validated_repository_revision` 指校验时 checkout，`validated_worktree_dirty` 说明工作区是否有未提交变更。实际计划输入由 manifest SHA 标识，不能把有改动的工作区校验说成 HEAD 已提交内容的验证。导出包没有 Git 信息时保持 null，不猜提交号。

## v1.2.1 结果与输出目录

本轮采纳和边界见[更新报告复核记录](../changes/2026-09-21_REVIEW_REFRESH_ADOPTION.md)。`review-round2-baseline-probes.json` 是修复前的两个隔离探针，不是当前 PASS 结果；保留其错误接受记录用于解释修复。当前治理回归含 39 个测试方法，新增模板路径别名、版本错配以及合法输入的对照测试。

原有、已修改的两份本地验证 JSON 已先快照保留在 `archive/review-inputs-2026-09-21-round2/`，再运行新校验。`governance-probe-v1.2.json` 的版本以内容中的 `source_plan_version` 为准。

CI 可生成到 `plan/` 外的项目内目录，不改写被测规划：

```bash
python3 -B plan/scripts/validate_plan.py --check --output-dir dist/validation/plan
python3 -B plan/scripts/validate_plan.py --self-test --output-dir dist/validation/plan
python3 -B plan/scripts/test_governance.py --output-dir dist/validation/plan
```

目录位置不是可信来源证明。正式 CI 的项目、commit、pipeline/job、状态和产物由 V2-004 核验；已提交的 JSON 不能认证包含它的下一次提交。PASS-only 关闭见证不能替代失败、错误、未知、阻断等原始运行历史。
