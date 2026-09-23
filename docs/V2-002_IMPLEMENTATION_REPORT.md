# V2-002 Normative Documentation Index 实施报告

日期：2026-09-23。Plan：1.3.0。结论：**IMPLEMENTED，未 VERIFIED/CLOSED**。仅实施 P0 / V2-002；本地命令和测试已存在，真实 CI、提交绑定的最终验收尚未取得。

## 现场与开工

首次实际核对 branch=`main`、HEAD=`21849ed8919086982dd94d0a4c852db40eca5d40`、dirty=false；计划 manifest=`53ba2ae218132f28e6e55d91c68ad2719b7cde7094576e233d92590421351af9`，基线检查 PASS。实际复用 CPython 3.12.14 / uv 0.12.17；未新装依赖或访问 Provider。

V2-001 为 IMPLEMENTED、ADR-001 ACCEPTED、CI/验收为空；V2-002 为 OPEN，dependencies 和 required_decisions 均为空，P0_ENTRY_READY。按现行 P0 并行规则，V2-001 未关闭不阻断本任务。先绑定专属 PREPARE 包并取得 PASS，再转 IN_PROGRESS / IMPLEMENT 并取得开工 PASS。原始记录见[基线](../plan/validation/execution/V2-002/raw/preflight.json)、[PREPARE](../plan/validation/execution/V2-002/checks/prepare/plan-validation.json)、[IMPLEMENT](../plan/validation/execution/V2-002/checks/implementation-start/plan-validation.json)。

首次交付保留为未提交工作区记录，随后实现已提交为 `a3ea77304f0c68967f21532adf3852bec3ea0a4d`。审核后续修复提交为 `9c2fd253326e87e9e6c43920f29a95dc68680a64`；新的提交后 CODE / TEST_RESULT 已绑定该实际被测 revision，任务和套件均已引用。旧工作区日志与开工 `repository_revision` 原样保留；ci/acceptance 仍为空。后续证据和交接提交仅补充元数据，不冒充已测源码提交。用户审核报告原有修改未改动、未提交。

## 实际实现

- 复用现有 `validate_plan.py`、`governance_checks.py`、`execution_checks.py`、最低治理基线和证据 Schema。现行规范注册仍采用 backlog.normative_specs，新增解析后路径检查；历史 design_references 保留参考身份。
- `scripts/check_governance.py` 聚合 plan check、自测、治理/执行回归和旧探针，导出规范—任务索引、实际上下文配置清单和每条命令的 stdout/stderr/exit。独立输出不回写被测计划，不覆盖历史结果。
- `scripts/task_execution.py` / `plan/scripts/task_entry.py` 在子命令启动前复用完整现行检查，并核对实际仓库、开工 revision 祖先关系、任务和动作。check/run/resume 不自动推进任务状态。恢复比较 branch、HEAD、暂存区、已跟踪/未跟踪文件内容与执行包/输入/交接产物；子命令失败保留 FAIL，超时或运行后无法观察保留 UNKNOWN。
- 新增 `tests/contract/test_plan_governance.py` 和 `test_task_execution.py`，用真实子进程、临时 Git 仓库和标记文件证明合法命令执行、无效命令未执行。
- 仓库配置实查：根 README/AGENTS 指向 plan；`.claude/settings.local.json` 顶层只有 permissions，没有自动加载 archive 的配置。允许读取某路径不等于自动加载该路径。报告不认证宿主全局配置或插件行为。

该入口只约束经它启动的命令。共享写权限、直接工具旁路、任意子命令语义、远端权限均未被认证。LIVE_CALL/CERTIFY 保留既有声明级正反例，但真实付费/认证 dispatch 在可信授权适配器接入前拒绝。没有新建 Agent 平台、业务内核、架构差异扫描或 CI 配置。

## 验证结果与场景映射

首次工作区运行结果：契约测试 **39 passed / 0 skipped**；现有安装/打包回归 **5 passed**（离线缓存安装、wheel/sdist、归档保留与入口检查）；验证器自测 **32**、治理回归 **39**、执行包回归 **36**、旧探针 **13** 均通过；资料检查和显式 write-views 通过。见[最终本地结果及代码快照索引](../plan/validation/execution/V2-002/local-results.json)、[治理汇总与全部原始输出](../plan/validation/execution/V2-002/checks/final-governance/governance-summary.json)、[契约 JUnit](../plan/validation/execution/V2-002/checks/final/contract.xml)。本轮没有重复运行未修改的 PostgreSQL 测试，沿用 V2-001 的历史证据，不声称重新认证数据库。

| AT-V2-002 场景 | 本地验证与范围 |
|---|---|
| 01–04 | 现行源/生成视图、失效引用、CLOSED/阶段门禁、实际上下文配置、外部来源追踪；新契约测试及既有 self-test |
| 05–08 | 既有 39 项治理回归：必需 CI/里程碑、类型化证据、双向关系、合格完整链与单点负例 |
| 09–12 | PASS 见证与失败历史、plan 外输出不改源、模板路径别名/符号链接、同 revision 阶段聚合与合法历史证据 |
| 13 | 真实入口的有效/缺失/模板/错任务/过期/坏 hash 包及动作不匹配；标记命令证明先拦截再执行 |
| 14–15 | 未决 ADR 下合法 PREPARE、被拒 IMPLEMENT、接受 ADR 后实际执行、FACT 缺来源、阻断 UNKNOWN；未来动作预算结构正反例沿用原测试 |
| 16 | 合法恢复，HEAD/branch/dirty 内容/实际产物变更拒绝，缺交接、失败或 UNKNOWN 不继承为成功 |

隔离夹具与真实远端 CI 分别记录。上述局部验证不能关闭 G-P0 或作为真人/市场证据。

## 夹具修正与保护比较

V2-002 激活后，旧 AI 测试复制全任务状态但只准备 V2-001 文件，导致 36 个用例在进入目标断言前被无关 packet 缺失挡住。修正只把隔离环境中未受测任务恢复 OPEN/null，隔离政策实施状态；全部原测试函数体/断言保持不变。

旧 probe 会在临时副本重序列化 YAML 并再生成 manifest，使有效对照因执行包输入过期被误拒。修正仅在临时副本重绑对应输入/manifest，保留被注入的任务、动作、ADR 和证据缺陷。两项旧代码均从开工 Git revision 取回并在临时副本真实复现 exit=1，见[旧夹具复现](../plan/validation/execution/V2-002/raw/fixture-baseline-reproduction.json)。失败未改标为工程 PASS。

与可信开工提交比较：全部 246 条验收断言、60 个任务身份/阶段/依赖、最低基线、阶段/CI/ADR 规则、证据 Schema、原 39+36 个测试函数体保持不变。新增路径解析规则加强现行约束。一次性范围核对全部修改在 packet.allowed_paths 内，见[范围复核](../plan/validation/execution/V2-002/raw/scope-review.json)；它不是提前实现 V2-003 的自动审查 harness。

V2-001 仍为活动 IMPLEMENTED 包，共享规范/backlog/manifest 变化会使其上下文过期；本次仅刷新其输入快照/hash，并在 V2-002 目录保留每次旧 packet。原始实现、ADR、CODE/TEST_RESULT 和缺 CI 状态均未改写，也未声称重新验收 V2-001。

## 审核后修复与提交绑定

两份报告复核后，用户要求继续。以 `a3ea7730` 为本次比较基线，实际通过 IMPLEMENT 入口后完成两项 P2 修复：合法 detached HEAD 记录 branch=null 和完整 HEAD；无效 JSON、数组、null、标量及缺字段 checkpoint 保存 BLOCKED 结果且不执行子命令。新增 12 个正反例，原有测试函数与验收断言均保留。

AI-EXEC-01 保留 IMPLEMENTED_LOCAL、原 owner/scenario 映射和全部 p0_required；由于该整体义务还包含尚未接入的可信 CI，p0_enforcement_status 校正为 NOT_IMPLEMENTED。AI-EXEC-04/06 不变，未新增 PARTIAL 枚举或放宽检查器。依据见[变更说明](../plan/validation/execution/V2-002/followup/rationale.md)与[基线比较](../plan/validation/execution/V2-002/followup/precommit-scope.json)。

在修复提交 `9c2fd253326e87e9e6c43920f29a95dc68680a64` 上重新运行：契约 **51 passed / 0 skipped**、安装打包 **5 passed**、验证器自测 **32**、治理 **39**、执行包 **36**、旧探针 **13** 全部 PASS。契约测试经真实 task_execution run 入口执行。原始命令、stdout/stderr/exit、JUnit、规范索引与上下文清单均已保存；19 个源码路径逐一比对该提交的 Git blob，相同快照复用，变更快照另存。详见[代码证据](../plan/validation/execution/V2-002/code-evidence.yaml)、[测试证据](../plan/validation/execution/V2-002/test-result.yaml)、[治理证据](../plan/validation/execution/V2-002/governance-result.yaml)和[绑定汇总](../plan/validation/execution/V2-002/followup/postcommit/binding-summary.json)。这些是本地同操作者结果，不是可信远端 CI；未重新执行 PostgreSQL，也不声称测试覆盖率 100%。

V2-001 仅刷新共享输入；其状态、源码与历史证据不重新认证。V2-002 仍缺 CI_RUN、最终 ACCEPTANCE_RECORD 和 finding 正式处置，保持 IMPLEMENTED。

## 责任与剩余事项

操作者与验证者均为 Codex/本地同一权限边界。子代理进行了有限资料核对和三处初始修改，随后因账户限额失败；主代理接手完成实现/测试。没有独立审核结论。

AR-01/02/06/07/19、CA-01/20/21/22、RR-01～06、DA-01～05 的本任务局部责任已有命令与测试依据，所有 finding 仍 OPEN_TRACKED。P0 关闭所需可信 CI、最终 ACCEPTANCE_RECORD 和逐项正式 finding 处置仍未取得；跨阶段业务责任继续属于登记中的后续任务。EXT-009 采用已有登记和本地独立追踪校验，没有复制上游代码/提示词，也未虚构上游 commit 或本项目收益；保持 PLANNED，未 VERIFIED。

V2-003、V2-004 及 P1+ 均未开始；G-P0/M0 保持 NOT_VERIFIED。本任务停止在 IMPLEMENTED。恢复先读[专属执行包](../plan/validation/execution/V2-002/execution-packet.yaml)及本报告，核对真实 checkout、工作区和证据，再按已有授权处理具体剩余事项；不要从这份报告自行开始下一任务。
