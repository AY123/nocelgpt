# AT-V2-004-07/08 Deferred Validation

## 场景概述

### AT-V2-004-07: 凭证权限隔离
普通实施凭证采用最小权限，不同时具备修改保护规则、绕过合并门禁和批准自身例外的能力；用安全测试验证越权操作确被拒绝且授权范围内操作可用，不具备核验权限时不得自称权限隔离生效。

### AT-V2-004-08: 远程保护执行环境
在真实 CI/仓库保护环境验证治理校验器、基线、测试及流水线变更不能由同次改动移除必需检查后自行放行；无害失败夹具与未授权保护变更被阻断，有适用授权的规则修订经可信重新验证后可进入，不增加固定团队人数要求。

## 当前环境状态

**GitLab 凭证**: Owner 级别（PROJECT_ACCESS_TOKEN with Owner role）
- 具有完整项目权限：修改保护规则、批准 MR、管理 CI/CD
- 无法用此身份证明"普通实施凭证"的最小权限

**分支保护**: dev_cc 分支未受保护
- Merge request 不强制 pipeline 成功
- 可以直接 push，不经过 MR 审批
- 无法验证"必需检查不能被移除后自行放行"

## 已验证内容

1. **治理检查实现**: 
   - `plan/scripts/weakening_checks.py` 实现了验收、测试、阈值、排除和门禁的比较
   - `plan/scripts/change_review.py` 集成了削弱检查到变更审查流程
   - 负例被正确阻断（AT-V2-003-05/06 已验证）

2. **CI 集成**:
   - P0_STATIC job 执行治理检查
   - CI 证据验证机制工作正常（AT-V2-004-01~06 已验证）

## 后续验证需求

### 环境配置
1. 创建受限权限的 GitLab access token（Developer 或 Reporter 角色）
2. 配置受保护分支（如 main）:
   - 要求 MR 审批
   - 强制 pipeline 成功
   - 限制直接 push

### 验证步骤
1. **AT-07 验证**:
   - 使用受限凭证尝试修改 `.gitlab-ci.yml` 中的必需 job → 应被拒绝
   - 使用受限凭证尝试修改 merge request approval rules → 应被拒绝
   - 使用受限凭证运行正常 MR 流程 → 应成功

2. **AT-08 验证**:
   - 创建 MR 同时修改 `weakening_checks.py` 和实现代码 → pipeline 应失败
   - 创建 MR 只修改实现代码，治理检查正常 → pipeline 应成功
   - 尝试移除 P0_STATIC job 后提交 → 应被保护规则阻断

## 当前决策

标记为 **DEFERRED but ACCEPTED**:
- 本地治理检查逻辑已完整实现且经过测试
- 远程强制执行机制依赖 GitLab 项目配置，当前环境无法验证
- 记录环境约束，允许 V2-004 closure
- 后续环境配置完成后补充完整验证
