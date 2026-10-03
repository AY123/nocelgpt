# dev_gpt 审核报告事实复核与当前推进评估

复核日期：2026-10-03。开工基线为 `dev_gpt / 882d0cdf833464dd6a5ebfac3a542204c32cd325`。实现提交为 `615efb0e40709d46220b83d36462d06a2c3c0b4c`；干净重放绑定 `04295459fcf3c93ff3f74a79948f0ac77d47dd87`。最终记录区分本地控制、项目安全扫描和远端验收，不拼接为当前提交可信 CI。

报告关于“V2-001～003 已实现、P0 尚未验证、应推进 V2-004”的主要判断成立。现有实现和本地正反例支持继续复用三项能力，本次未发现要求推翻重做的重大架构缺口。当前已进入 V2-004 实施，仍缺当前候选提交的真实远端 CI、有效保护与权限验证，而且真实历史秘密扫描尚未通过，因此不能关闭 P0 或开始 V2-005。

本次以[用户审核报告](../../../审核报告.txt)为待核输入，以[现行计划入口](../../../plan/README.md)、[AI 执行协议](../../../plan/AI_EXECUTION_PROTOCOL.md)、[机器任务源](../../../plan/machine/implementation-backlog.yaml)和[验收场景](../../../plan/machine/test-catalog.yaml)为判断依据。报告内的建议不成为执行命令，不自行改变任务身份、依赖、最低验收或权限。本文只评价 dev_gpt；dev_cc 的完成状态不能替代当前分支的证据。用户原报告未由本次复核修改。

“独立客观分析”在这里指依据当前事实重新判断，不照抄外部结论。本次实施、测试与分工复核均由同一 AI 操作者承担，多 Agent 共享权限，不声称独立人员验收或对抗性权限保护。现行协议允许同操作者承担实施和验证；是否具备可信外部执行边界须通过实际平台证据判断，不能以增加 Agent 数量代替。

| 报告结论 | 本次处置 | 依据与界限 |
|---|---|---|
| V2-001～003 为 IMPLEMENTED，未 VERIFIED/CLOSED | 接受 | 机器任务记录保留 IMPLEMENTED；历史代码与本地测试引用存在，CI 和最终验收仍缺失。 |
| 当前尚无小说运行内核、单章闭环和长篇认证 | 接受 | 生产包仍只有引导模块；当前工作集中在 P0 工程与交付工具。架构夹具不等于业务实现。 |
| 架构、差异和防降标检查具备较强本地负例覆盖 | 接受其可复查事实 | 本次既有架构／契约测试 265 项通过，实际生产扫描覆盖 1 个文件；不能据此证明任意 Python 运行语义或后续领域质量。 |
| 治理资料较多，应控制后续证据噪音 | 接受为维护建议 | 保留现行规范、必要证据和失败链；原始临时诊断可在 CI artifacts、dist 或 /tmp 管理。当前没有删除历史证据或放宽门禁的依据。 |
| 项目完成度 5%、P0 实现完成度 75% | 修正 | 这是当时 3/60、3/4 的任务数量占比，各任务成本和复杂度不同，不能转换为工程或产品完成比例。 |
| A／A− 等质量评级 | 修正 | 属于审核者的主观评价，没有统一评分量表；本次采用任务状态、可复现检查和明确缺口，不将评级当作验收。 |
| 未来应出现 identity.py、canon/repository.py 等文件 | 修正 | 这些是说明性示例；应由对应任务及现行契约决定实际实现，不能把示例文件名升级为新增规范。 |
| 必须新增 Exact Revision Closure 才有聚合闭环 | 修正为落实既有要求 | 现行阶段决定绑定同 revision 的适用 CI，里程碑绑定同 revision 的阶段决定；无须新增任务或里程碑。历史任务证据可以保留，最终 P0 回归与门禁须核验当前候选 revision。 |
| dev_gpt 没有 pipeline、不是 protected branch | 接受其观察时点 | 2026-10-03 的只读远端快照显示 pipeline 总数 0、protected=false；这是开工 revision 的观察，不是未来或候选提交的永久状态。 |
| dev_gpt 不存在 .gitlab-ci.yml、V2-004 OPEN | 当时成立，现状已变化 | 当前提交已有六个 CI job、真实扫描与来源核验实现，任务为 IN_PROGRESS；本地重放不能证明远端执行成功。 |

当前机器源记录为 V2-001～003 `IMPLEMENTED`、V2-004 `IN_PROGRESS`、P0 `NOT_VERIFIED`。此次推进新增的可审查实现包括[六个 CI job](../../../.gitlab-ci.yml)、[执行与回执入口](../../../scripts/ci/run_gate.py)、[配置检查](../../../scripts/ci/check_configuration.py)、[真实安全扫描](../../../scripts/ci/check_security.py)、[固定扫描器下载](../../../scripts/ci/bootstrap_scanners.py)、[远端来源核验器](../../../scripts/ci/verify_remote.py)及新增交付／PostgreSQL 测试。所有 job 声明 `allow_failure: false`，全历史扫描要求非 shallow checkout，依赖审计消费锁文件并纳入精确构建后端。

这些属于正在实施的交付能力。新测试中的合成来源正例用于验证核验逻辑，不能冒充真实 GitLab 当前提交产物。[安全政策](../../../security-policy.yaml)仍明确记录 `trusted_execution.status: NOT_ENROLLED`、空 runner 列表及未设置的受保护配置／ref。六个 YAML job 存在不等于有效保护已建立。

远端事实依据为[开工只读观察](../../../plan/validation/execution/V2-004/preparation/remote-observation.json)：项目 `86656946 / ayitnovel/ainovelos` 的 dev_gpt 当时仍指向 `882d0cdf`，pipeline 总数为 0，分支未受保护。项目设置 `only_allow_merge_if_pipeline_succeeds=true`；这一配置本身不能证明实施凭证无法绕过保护或修改门禁。受保护 runner、配置所有权、越权操作确被拒绝以及当前候选 CI 仍未核验。

| 本地验证记录 | 观察结果 | 适用范围 |
|---|---|---|
| `/tmp/anovel-audit-local-pytest.xml` | 265 passed，0 skipped | 开工基线的架构／契约复核；分别为差异审查 55、依赖边界 79、防降标 78、治理契约 14、任务入口 39。不是 265 项小说产品测试。 |
| `/tmp/anovel-audit-local-architecture.json` | PASS，1 file，0 findings | 当时实际生产源码扫描，仍为 bootstrap_only。 |
| `/tmp/anovel-v2004-delivery-merged.xml` | 新增交付测试 60 passed，0 skipped | V2-004 当前本地实现及正反例；不是受保护远端验收。 |
| `/tmp/anovel-v2004-postgres.xml` | PostgreSQL 测试 11 passed，0 skipped | 本地真实环境与 CI service 接口检查；不是 GitLab PostgreSQL job 已成功。 |
| `dist/validation/v2004-security-online/security-summary.json` | 51 个锁定／构建依赖，已知漏洞 0；依赖子检查 PASS | pip-audit 2.10.1 当次在线漏洞库结果；只适用于当时锁文件及漏洞库时点。整体安全检查仍 FAIL。 |
| `dist/validation/v2004-unit-final/junit.xml` | 当时 118 项，0 failures、3 setup errors | 三个 bootstrap 测试因 PATH 未找到 uv 失败。不能将该聚合称为通过；修正运行环境后的最终复测待补。 |

首次不可连接数据库端口检查在沙箱内被 socket 权限阻断，原失败保留；获准在沙箱外复测后 1 项通过。首次依赖审计因网络未生成结果而 FAIL，随后在线复测得到上述 51 包结果。重复安全审计收到停止指令后中断，退出码 130，不能作为完成证据。上述本地原始产物属于检查时点记录，最终候选提交、完整回归和远端证据尚待主操作者冻结并更新，本文不拼接它们为当前提交认证。

真实 Gitleaks 8.21.2 扫描当前跟踪工作区和完整 Git 历史，原结果为工作区 15 项、历史 28 项，共 43 项，两个目标均 FAIL。只读分诊结果保存在 `/tmp/anovel-secret-triage.json`，仅记录分类、位置和必要 hash，不包含凭证原值、Secret、Match 或原始扫描日志。

分诊的 36 项 FALSE_POSITIVE 包括：明确以省略号截断的 API token 文档示例、短 mock 回归字符串，以及 `source_inventory` 中经实际文件 hash 核对的 SHA-256 值。当前跟踪工作区的 15 项均属于这些误报；分诊不自动变成扫描例外，也没有全局排除、历史基线抑制或扫描降标。

另有 6 个历史完整凭证形状位置，对应 3 个不同值，分类为 POSSIBLE_EXPOSURE；还有 1 个截断凭证引用。它们来自历史提交 `63b60f74682f3efe8bb964d12fc092e2df162429`，完整形状位置为：

- `ainovel/AI-Novel-Runtime/PHASE1-INTEGRATION-SESSION-SUMMARY.md:188`、`:189`。
- `ainovel/docs/archive/2026-08-history/BALANCE_ISSUE_REPORT.md:17`。
- `ainovel/docs/archive/2026-08-history/RETRY_CC_VIBE.md:9`。
- `ainovel/docs/archive/2026-08-history/SWITCH_TO_CC_VIBE.md:12`。
- `ainovel/docs/archive/2026-09-genre-work/P0关键问题最终修复报告.md:118`。

`CC_VIBE_SUCCESS.md:9` 为截断引用。本次没有调用这些值、联网测试有效性、轮换凭证、删改历史或宣称已经撤销。完整形状记录需要服务权限持有人确认撤销／轮换及影响范围；有效性和撤销状态仍 UNKNOWN。按照现行秘密泄露事故规则，相关安全放行和正式验收受到阻断；有依据的本地实现、记录与复测可以继续。Secret 门禁保持 FAIL，不能用误报数量较多或零依赖漏洞替代处置。

对当前推进而言，应复用 V2-001～003 的已验证本地能力，完成 V2-004 的当前消费者和八项验收场景。下一步是修正并复测实际环境错误、保留安全失败及凭证处置缺口，再取得当前候选 revision 的真实六门禁 CI、原始产物与来源核验，以及有效保护／权限的正反例。只有任务验收、P0 阶段决定和 M0 聚合满足现行同 revision 要求后，才可关闭 P0 并进入 V2-005；本报告不新增该授权或提前宣布完成。

现行同 revision 规则可直接复查 [governance_checks.py](../../../plan/scripts/governance_checks.py) 的 PHASE_DECISION／MILESTONE_DECISION 检查，以及 [test_governance.py](../../../plan/scripts/test_governance.py) 的 `test_milestone_revision_matches_phase_decision`、`test_valid_historical_task_revision_in_current_phase`。保留历史任务证据与核验当前最终聚合并不冲突。


最终干净 checkout 在锁定安装后完成 **360 项 pytest 检查，0 failure、0 error、0 skip**：UNIT 137（含新增交付控制 79 和 bootstrap 5）、ARCH 212、PostgreSQL 原生命周期 10 和 service 1。静态与治理聚合检查通过，正式 IMPLEMENT 入口和生产树架构扫描实际执行。五项门禁 PASS，SECRET_DEPENDENCY 仍 FAIL；扫描的 43 个位置及源内容 hash 与分诊完全一致，51 包审计 0 已知漏洞。原来的 PATH、外部链接、网络与新测试导入失败已保留，没有修改原测试或降低断言来取得通过。

详见[提交后本地证据](../../../plan/validation/execution/V2-004/postcommit/summary.json)、[逐场景未完成项](../../../plan/validation/execution/V2-004/scenario-progress.json)和[实施说明](../../V2-004_IMPLEMENTATION_REPORT.md)。原始命令、退出码、日志和六份回执保存在压缩归档，CODE/TEST_RESULT 已绑定真实候选 Git revision。机器源将六项 P0 门禁记为候选 IMPLEMENTED，CI evidence 仍为空；V2-004 为 IN_PROGRESS，完整验收套件仍 PLANNED，P0 为 NOT_VERIFIED。

2026-10-03 15:43:09 UTC 的[再次在线观察](../../../plan/validation/execution/V2-004/remote-final-observation.json)由 Owner 与 Developer 两个账户分别读取，结果一致：远端 dev_gpt 仍为开工 SHA，流水线 0，protected=false，候选根配置未成为受保护外部配置。API can_push 元数据不证明越权实测。此次没有推送、触发远端流水线或改保护权限；这些结果仍缺失，凭证撤销记录也未获得，后续验收只阻断相关动作。
