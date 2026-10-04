# V2-004 恢复实施记录

本轮用户明确开始 V2-004；提示词只作参考。现行六门禁、八个验收场景、任务身份和 P0 退出条件不变。实施及验证由同一操作者承担，协作 Agent 不构成独立权限保障。

恢复时 `dev_gpt` 与 `origin/dev_gpt` 同为 `6ed09939bdc7715fd582338675cd0443777aac50`。规范输入结构检查通过。前轮 `04295459` 的本地 360 个测试及 Secret 失败仍是历史证据，不自动升格为当前远端证据。

真实 [GitLab pipeline 2909931436](https://gitlab.com/ayitnovel/ainovelos/-/pipelines/2909931436) 绑定恢复提交，四项成功、UNIT 失败、SECRET_DEPENDENCY 跳过。已实读五个执行 job 的 trace，并比对固定提交 driver hash。具体 job artifact 在取得、核对 hash 后另行登记；来源、受信执行、权限与最终验收分开记录。

| 现行场景 | 已核实事实 | 剩余工作 |
|---|---|---|
| AT-01 硬失败 | UNIT 非零使真实 pipeline failed | 修复真实故障后核对新候选，保留失败原始记录 |
| AT-02 无害 Secret/依赖负例 | 前轮真实本地扫描负例通过，历史疑似凭据未处置 | 本轮真实 CI 负例及脱敏凭据处置依据 |
| AT-03 PostgreSQL | 当前远端 postgres_env success，实际 trace 可读 | 获取精确 job artifact 并核对连接原始结果；最终候选重跑 |
| AT-04 合并保护 | 项目要求成功 pipeline，dev_gpt 不受保护；main 保护标记为真 | 核对完整规则、有效保护与删除/后移/失败阻断 |
| AT-05 当前真实产物 | 当前真实 pipeline/job/trace 已取得，整体 failed | 全部精确 job artifact/hash 与最终候选身份 |
| AT-06 受信执行 | 实际 instance/shared runner 元数据；未登记受保护 runner | 补强命令/产物合同，核对有效受保护执行与真实正例 |
| AT-07 最小权限 | 两账户只读结果一致，Developer 对 main can_push=false | 真实越权拒绝与合法操作正反例，不能用 metadata 代替 |
| AT-08 防删除 | 已有本地差异/弱化控制 | 真实受保护配置上的反删除、无害失败及有授权修订正反例 |

正常代码修复、测试和提交推送在用户已授权任务范围内继续；新增付费、平台权限扩张以及验收关闭不由参考提示词授权。未知项只阻断相关步骤。任务继续 IN_PROGRESS，P0 NOT_VERIFIED，不能进入 P1。

本轮准备记录包含原 packet/context、实际用户文件身份和固定授权来源。开工检查曾拒绝 `review_revision: null` 的结构错误以及 worktree 身份多出的 oid；纠正格式后 `dist/v2004-20261004-implement-entry-v3.json` PASS。保留原失败记录，未放宽检查器或修改用户文件。

## 最终 MR 接入修正与已核验远端结果

a6d66af 的真实 pipeline2910062335 已终态失败：五门禁成功，UNIT178、ARCH212、PG1 无失败/错误/skip；安全扫描15当前发现与28历史发现硬失败，51依赖0漏洞。六个job原始产物/hash匹配，五个成功job完整在线源合同PASS，整体来源FAIL、权限UNKNOWN、验收false。对应remote-a6-*记录保留，不移用至新候选。

发现无rules job默认排除MR后，补齐六job精确无条件rules（普通on_success、安全always）；24新增拒绝控制保留全部原测试。完整本地UNIT202 PASS、STATIC和五治理PASS；沙箱202/2fail的原运行与正常权限重放均保留。GitLab实际Lint静态/push模拟均valid且六hardjobs，不宣称真实MR认证。

主工作区local入口PASS与源码/review由mr-code-index、final-mr-local-entry及local-execution-packet绑定；活动包切回干净CI作用域，用户文件身份核对未变，不清理用户工作区。最后候选待正常push并读取精确真实CI。trusted-ci-proposal.md给出可审阅的平台/runner与权限正反例方案，未修改平台或增加资源。
