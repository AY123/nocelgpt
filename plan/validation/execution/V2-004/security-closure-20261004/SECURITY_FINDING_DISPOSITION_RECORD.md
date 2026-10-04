# V2-004 Security Finding Disposition Record

最新已核验扫描来源：`e927dbfb05f4b917e9f825cb9aae91c6caf64f9a`，Pipeline `2910441607`，Job `16919376075`。本记录处于 OPEN，不是安全验收或例外批准。被测 SHA 是扫描来源，不能解释为后续包含本记录的提交已经通过 CI。

45 项与 CI artifact 一一对应：PUBLIC_IDENTIFIER 26 项（原公开文件 SHA256 24 项及新增公开测试变量名 2 项），TEST_FIXTURE 3 项，FALSE_POSITIVE 9 项；另有 6 项完整凭据形态和 1 项截断引用等待 owner 确认。三组完整形态只按值一致性分组，未判断有效性。

根据实际分类形成 38 项精确例外申请，未批准、未应用；45 项关闭数均为 0。原 43 项的身份、来源及处置内容保留，新 SF-044/045 单独加入。JSON 的 current_ci_binding 将全部 45 个 ID 绑定本次真实 scan、job、路径/行、历史 commit、source blob 和当次 fingerprint；原 tracked 15 项指纹因临时路径不同而全部重新绑定，未继承旧 hash。

| Finding | 分类 | 目标 | 路径:行 | 凭据组 | 当前处置 |
|---|---|---|---|---|---|
| V2-004-SF-001 | FALSE_POSITIVE | tracked_worktree | `plan/archive/ccdoc/19_API_SPECIFICATION.md:164` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-002 | FALSE_POSITIVE | tracked_worktree | `plan/archive/ccdoc/19_API_SPECIFICATION.md:165` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-003 | FALSE_POSITIVE | tracked_worktree | `plan/archive/ccdoc/19_API_SPECIFICATION.md:192` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-004 | PUBLIC_IDENTIFIER | tracked_worktree | `plan/archive/plan-review-2026-09-21/governance-probe-results.json:48` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-005 | TEST_FIXTURE | tracked_worktree | `plan/archive/root_matrices/V1_REGRESSION_ASSET_REGISTER.md:54` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-006 | PUBLIC_IDENTIFIER | tracked_worktree | `plan/validation/ai-governance-1.3.0/legacy-governance-probes.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-007 | PUBLIC_IDENTIFIER | tracked_worktree | `plan/validation/execution/V2-002/checks/final-governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-008 | PUBLIC_IDENTIFIER | tracked_worktree | `plan/validation/execution/V2-002/checks/first-governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-009 | PUBLIC_IDENTIFIER | tracked_worktree | `plan/validation/execution/V2-002/followup/bound-governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-010 | PUBLIC_IDENTIFIER | tracked_worktree | `plan/validation/execution/V2-002/followup/postcommit/governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-011 | PUBLIC_IDENTIFIER | tracked_worktree | `plan/validation/execution/V2-003/final/governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-012 | PUBLIC_IDENTIFIER | tracked_worktree | `plan/validation/execution/V2-003/followup/final/governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-013 | PUBLIC_IDENTIFIER | tracked_worktree | `plan/validation/execution/V2-003/followup/postcommit/checks/governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-014 | PUBLIC_IDENTIFIER | tracked_worktree | `plan/validation/execution/V2-003/postcommit/checks/governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-015 | PUBLIC_IDENTIFIER | tracked_worktree | `plan/validation/governance-probe-v1.2.json:48` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-016 | PUBLIC_IDENTIFIER | git_history | `plan/validation/execution/V2-002/revalidation-fd7667ec/local/legacy-governance.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-017 | PUBLIC_IDENTIFIER | git_history | `plan/validation/execution/V2-003/followup/final/governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-018 | PUBLIC_IDENTIFIER | git_history | `plan/validation/execution/V2-003/followup/postcommit/checks/governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-019 | PUBLIC_IDENTIFIER | git_history | `plan/validation/execution/V2-003/final/governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-020 | PUBLIC_IDENTIFIER | git_history | `plan/validation/execution/V2-003/postcommit/checks/governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-021 | PUBLIC_IDENTIFIER | git_history | `plan/validation/execution/V2-002/followup/bound-governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-022 | PUBLIC_IDENTIFIER | git_history | `plan/validation/execution/V2-002/followup/postcommit/governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-023 | PUBLIC_IDENTIFIER | git_history | `plan/validation/execution/V2-002/checks/final-governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-024 | PUBLIC_IDENTIFIER | git_history | `plan/validation/execution/V2-002/checks/first-governance/legacy.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-025 | PUBLIC_IDENTIFIER | git_history | `plan/validation/ai-governance-1.3.0/legacy-governance-probes.json:49` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-026 | PUBLIC_IDENTIFIER | git_history | `plan/archive/plan-review-2026-09-21/governance-probe-results.json:48` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-027 | PUBLIC_IDENTIFIER | git_history | `plan-review-2026-09-21/governance-probe-results.json:48` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-028 | PUBLIC_IDENTIFIER | git_history | `plan/validation/governance-probe-v1.2.json:48` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-029 | FALSE_POSITIVE | git_history | `plan/archive/ccdoc/19_API_SPECIFICATION.md:164` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-030 | FALSE_POSITIVE | git_history | `plan/archive/ccdoc/19_API_SPECIFICATION.md:165` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-031 | FALSE_POSITIVE | git_history | `plan/archive/ccdoc/19_API_SPECIFICATION.md:192` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-032 | TEST_FIXTURE | git_history | `plan/archive/root_matrices/V1_REGRESSION_ASSET_REGISTER.md:54` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-033 | TEST_FIXTURE | git_history | `V1_REGRESSION_ASSET_REGISTER.md:54` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-034 | POSSIBLE_EXPOSURE | git_history | `ainovel/AI-Novel-Runtime/PHASE1-INTEGRATION-SESSION-SUMMARY.md:188` | CRED-001 | OPEN / NOT_PERFORMED |
| V2-004-SF-035 | POSSIBLE_EXPOSURE | git_history | `ainovel/AI-Novel-Runtime/PHASE1-INTEGRATION-SESSION-SUMMARY.md:189` | CRED-001 | OPEN / NOT_PERFORMED |
| V2-004-SF-036 | POSSIBLE_EXPOSURE | git_history | `ainovel/docs/archive/2026-08-history/BALANCE_ISSUE_REPORT.md:17` | CRED-002 | OPEN / NOT_PERFORMED |
| V2-004-SF-037 | TRUNCATED_REFERENCE_UNRESOLVED | git_history | `ainovel/docs/archive/2026-08-history/CC_VIBE_SUCCESS.md:9` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-038 | POSSIBLE_EXPOSURE | git_history | `ainovel/docs/archive/2026-08-history/RETRY_CC_VIBE.md:9` | CRED-002 | OPEN / NOT_PERFORMED |
| V2-004-SF-039 | POSSIBLE_EXPOSURE | git_history | `ainovel/docs/archive/2026-08-history/SWITCH_TO_CC_VIBE.md:12` | CRED-002 | OPEN / NOT_PERFORMED |
| V2-004-SF-040 | POSSIBLE_EXPOSURE | git_history | `ainovel/docs/archive/2026-09-genre-work/P0关键问题最终修复报告.md:118` | CRED-003 | OPEN / NOT_PERFORMED |
| V2-004-SF-041 | FALSE_POSITIVE | git_history | `ccdoc/19_API_SPECIFICATION.md:164` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-042 | FALSE_POSITIVE | git_history | `ccdoc/19_API_SPECIFICATION.md:165` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-043 | FALSE_POSITIVE | git_history | `ccdoc/19_API_SPECIFICATION.md:192` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-044 | PUBLIC_IDENTIFIER | tracked_worktree | `plan/validation/execution/V2-004/authority-controls-20261004/actual-pipeline-variable-controls.json:23` | — | OPEN / NOT_PERFORMED |
| V2-004-SF-045 | PUBLIC_IDENTIFIER | git_history @ e927dbf | `plan/validation/execution/V2-004/authority-controls-20261004/actual-pipeline-variable-controls.json:23` | — | OPEN / NOT_PERFORMED |

可核验附件：

- [完整逐项记录](SECURITY_FINDING_DISPOSITION_RECORD.json)
- [24 项公开文件标识静态证明](public-identifier-proof.json)
- [e927dbf 实际安全 artifact 绑定](../security-delta-20261004/CI_ARTIFACT_BINDING.json)
- [e927dbf 实际 CI 脱敏扫描](../security-delta-20261004/ci-artifacts/secret-scan.json)
- [当前45与原43的实际差异](../security-delta-20261004/finding-delta-vs-c0ba3a7.json)
- [原3ce6c32处置原文快照](../security-delta-20261004/predecessor-disposition-3ce6c32.json.gz)
- [历史3ce6c32六门禁 artifact 索引](ci-evidence-index.json)
- [Runner / 保护分支实际查询](trust-boundary-metadata.json)
- [首次网络失败保留](trust-boundary-first-attempt.json)

接续条件：owner 提供三组凭据的脱敏撤销/轮换或非凭据依据，确认 SF-037 引用；例外须由授权角色给出理由、精确范围和有效期。历史发现即使当前文件不存在仍会被全历史扫描检出，任何历史改写须另行明确授权并重绑定受影响证据。

最终候选必须在同一个新 SHA 上重新取得六门禁 PASS，以及真实受保护执行和 Developer 权限正反例；不得合并不同 SHA 的通过结果。当前 V2-004 IN_PROGRESS，P0 NOT_VERIFIED。
