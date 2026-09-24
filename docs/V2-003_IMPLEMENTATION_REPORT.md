# V2-003 实施与交接

## 2026-09-24 外部深审整改（当前）

用户要求“评估报告，如果确实存在问题修正”。本轮实际开工为 main / `a11693ee5ac08fd3aa102e03de0125bd8b800dd9`、Plan v1.3.0；没有把报告自述的 GitLab 审核当成本次已核验的远端结果。四项问题均在本地旧代码真实复现，见 `plan/validation/execution/V2-003/followup/assessment/`。新 PREPARE 已通过，以 `fb87e60b6c2f9f7d62ad1ed039f0082403cd21c6` 固定专属范围后实施。修正期间 V2-003 重新置为 IN_PROGRESS，最终状态待本轮证据绑定。

| 报告问题 | 核实结果与修正 |
|---|---|
| 不传 scope 可跳过差异门禁 | 属实。IMPLEMENT/LIVE_CALL/CERTIFY 的 check/run/resume 必须有执行包 change_review；入口自动读取固定 scope/review，CLI 只能重述同值。省略参数仍检查命令前后差异。PREPARE 可调查未冻结范围；直接工具和同写权限者仍不受操作系统级约束。 |
| 通用技术复核可放行生产功能 | 属实。PRODUCTION_SCOPE_REVIEW 改为 AUTHORIZATION_REQUIRED；需要固定 scope 中事先精确的 task/path/code/old_sha/new_sha 范围授权，且固定提交仍含授权前字节。普通 REVIEWED_NO_WEAKENING 不能解除；本轮没有生产授权或生产改动。 |
| 新增 conftest 可改变收集而漏报 | 属实。新增/变更 conftest、pytest hooks、collect_ignore、pytest_plugins 与 pytest.ini/setup.cfg/tox.ini 进入复核；合法 fixture 有精确技术复核通过例。 |
| 常见 builtin-loader 下标漏报 | 属实。覆盖 __builtins__ 下标、builtins.__dict__、vars(builtins/importlib) 及别名；字面量目标适用原依赖规则，未知键产生 ARCH_DYNAMIC_UNKNOWN；合法 json 导入通过。 |

没有重建治理体系，也没有执行 V2-004/P1+、CI、付费 Provider 或业务功能。执行包 schema 仅增加字段，旧约束保持；历史 V2-001/002 包仍可作为历史记录读取，新受限动作必须先准备并绑定适用范围。六条 AC、60 个任务身份/依赖、246 个场景和最低门禁均保留。用户两份审核材料与本地配置按开工 hash 保留。

同一操作者实施和复核，不能称为独立审核。当前结果与恢复入口以 `followup/execution-packet.yaml`、`followup/handoff.json` 为准；下面原交付内容仅描述对应历史提交。

## 原交付记录（历史，adc537d8 至 d1d25494）

当前为 **IMPLEMENTED**。本地代码和测试证据已绑定真实实现提交 `adc537d88d2228ef2690d4e7bc04d2def8e1b1af`。任务仍缺可信 CI 和最终验收，不能 VERIFIED/CLOSED；V2-004 及 P1+ 未启动。最终机器记录与原始运行结果位于 `plan/validation/execution/V2-003/`，交接元数据提交不冒充另一次代码/CI验证。

## 提示词评估与开工

用户已授权评估、直接修正 `V2-003任务prompt.txt` 后启动。原提示词保存在 `preparation/original-prompt.txt`；修正依据在 `preparation/prompt-review.md`，保留六条 AC，不把报告当新命令、不添加任务依赖、不凭空要求逐文件批准。实际开工 main / `c6f26c6188f0b6ad82ce73bf04024d1eab96e1cf`、Plan v1.3.0；V2-001/002 IMPLEMENTED，P0 尚未 VERIFIED。专属 PREPARE 已通过并先提交冻结范围，再通过 IMPLEMENT。

原 scope pin 为 `518c8a6646acbd236a38436388d05da06ac19abd`。真实扫描发现全局忽略的既有 `.claude/settings.local.json` 漏入初始清单；保留原失败和基线，通过 `1e9327792b622420ae1414bc8c10e9a57e4babdb` 固定 v2 清单。仅增补该文件当前精确保护身份，不扩大 allowed_paths、protected_paths 或编辑授权，不伪称开工时已经核验其字节。见 `preparation/opening-inventory-correction.md`。完整回归另发现旧治理测试把缺 CI/验收误期待为版本混用诊断；已先用 `b1013cc17b76a237db64503062daf24340efb5c7` 固定 v3，仅增加该测试文件修正路径，再保留原拒绝要求并增加分别检查 CI 与验收缺失的断言。原失败与理由见 `preparation/legacy-contract-correction.md`；当前 scope pin 以 `preparation/pinned-baseline.json` 为准。

## 实现及六场景映射

| 场景 | 实现和真实回归 |
|---|---|
| AT-V2-003-01 | `architecture_checks.py` 静态 AST 依赖图：绝对/相对导入、别名、包初始化、重导出、传递依赖及字面量动态加载；合法领域接口通过，领域到 Provider/DB/Web/Workflow 和未知第三方依赖被拒绝/要求复核。对应 `test_dependency_boundaries.py`。 |
| AT-V2-003-02 | Canon 内部 repository 限 Canon 内部；Workflow 可调用公开 commit_service，但不能经别名、重导出或动态 fromlist 访问内部写能力。Gateway/Quality/Repair/Context/Intelligence 违规夹具失败。这是静态包职责检查，不实现 Canon 运行权限。 |
| AT-V2-003-03 | 递归发现整个 `src/anovel`，新增嵌套模块参与扫描；零文件、语法错、源链接、动态加载未知、缩窄扫描根、禁用/后移 P0 门禁失败。真实源树目前仅 1 个引导模块，报告明确 bootstrap_only；隔离夹具不是生产业务实现。 |
| AT-V2-003-04 | `change_review.py` 从固定 Git opening/scope 对比 index 与工作树，检查增删改名、未跟踪、路径/链接、原有用户改动、漏扫和扫描期间变化；不消费候选 ignore 来隐去文件。真实 Git 正反例在 `test_change_review.py`。 |
| AT-V2-003-05 | `weakening_checks.py` 对固定旧版联动比较验收/场景、测试 AST、skip、阈值、排除、硬失败、门禁和保护代码。同步修改正文/机器/测试也保留 finding，未处置即失败。对应 `test_weakening_checks.py`。 |
| AT-V2-003-06 | 合法增改删重命名、测试增加、语法等价、固定技术复核和明确事先授权的真实规则修订均有通过例；自写理由、过期内容、缺授权、跨任务或降低验收被拒绝。授权修订仅在合成隔离仓库演示，本任务没有降标授权或实际删测。 |

`scripts/check_architecture.py` 输出真实发现数与硬门禁适用性；`scripts/check_changes.py` 保留原 finding、精确 hash、层和处置。`scripts/task_execution.py` 显式提供 scope/review pin 时，在子命令前和结束后检查差异。没提供 pin 的旧调用维持 V2-002 行为，不冒称所有工具动作都已经受保护。

## 保护变化与复核

现有入口增加前后差异检查、参数成对约束和输入竞态阻断；原 ADR、执行包、预算、恢复检查均保留。机器任务仅记录当前实现产物、状态和证据，AI-EXEC-02 记录本地实现，AI-EXEC-03 因整体含可信受保护复验仍 NOT_IMPLEMENTED。

旧契约测试 seed 原本从生产当前任务表复制 OPEN 的 V2-003。项目启动 V2-003 后，原负例会先遇到 action 不匹配而非缺包。只将隔离 fixture 的后续任务恢复为原测试前提，现有 test 函数和断言逐 AST 保持一致；修复前真实失败与修复后正负例保存在 raw/001、002。不是修改生产状态来通过测试。另修正 `test_plan_governance.py` 关闭负例的过时诊断前缀，并增加 CI、acceptance 两项具体拒绝断言；没有减少负例或断言，也未改 validator 为错误诊断让步。

分工复核发现并修复：用户脏文件恢复为旧 Git 内容漏报；index 篡改/删除 scope 或 packet；测试移出发现路径；保护文件重命名；缓存目录隐藏 Python 源；父路径符号链接；验证到子命令之间竞态；新增嵌套 ignore；明确删除授权 null 身份；新增测试注解副作用和反射 skip。所有对应回归均保留。多 Agent 共享写权限，属于协作复核，不是独立权限审核。

`tools/check_preservation.py` 真实比较开工 Git，检查60任务身份/依赖/验收、246场景断言、最低基线/门禁/权限/锁文件、原有契约测试定义、用户报告 hash 和生产源未变。初版辅助脚本错误假设 `.gitlab-ci.yml` 已存在，raw/006 真实失败保留；修正后明确验证该 V2-004 文件仍不存在，不伪造 CI。

## 整改责任和未决项

AR-06、RR-04 的本任务范围/测试/实际差异义务已本地落实，整体 Closure 与 P0 放行仍缺可信 CI/验收。AR-17、CA-17、RR-09 的架构违规阻断已本地落实，远端运行/安全/依赖及权限保护仍属 V2-004；真实 Provider 证据仍在适用后续阶段。RR-03 提供实际提交/hash/源计数及失败记录；RR-10 提供可运行边界夹具，不把历史目录数当测试数；其它 Canon/Repair 回归仍属 V2-010/020。七项保持 OPEN_TRACKED，不代全项目关闭。

本地 Git pin 只能固定比较输入，不能证明操作者授权真实或抵抗同写者绕过/修改校验器。AST 检查不证明任意 Python 语义等价，也不实现数据库唯一写路径、真实 Provider 或远端保护。下一阶段必须由明确授权后单独启动，不能把本任务 PASS 当自动准入。

## 实际提交后验证与恢复

所有以下成功运行的 checkout 均为 `adc537d88d2228ef2690d4e7bc04d2def8e1b1af`；CODE 快照逐文件与该 Git 内容相等。用户原报告脏文件、新增运行记录和任务辅助证据整理不冒充已提交产品源码。

- raw/014：`pytest -q tests/architecture tests/contract`，**236 passed**（185 架构/差异/弱化 + 51 契约），退出0，0 skip。
- raw/015：治理聚合 PASS：现行资料 check、自测32、治理39、AI执行36、历史探针13，均退出0。
- raw/016：锁定环境离线安装/打包回归 **5 passed**，退出0。没有把它称为当前 PostgreSQL 或 CI 运行。
- raw/017：实际开工 Git 保留比较17项全部PASS，任务/依赖/验收/基线未弱化；未新增业务源码。
- raw/019：固定 scope v3 + 实现提交中的12条精确技术处置，任务入口命令前/后差异检查及真实架构子命令全部PASS。真实生产树仍为1文件、1模块、bootstrap_only=true。

失败、竞态阻断、错误pin和修复说明在 `review/execution-attempts.md`；原始结果不覆盖。成功类型化证据见 `code-evidence.yaml`、`test-result.yaml`；压缩 entry 原始JSON可用 gzip 解码，内容与原始运行对应。所有 `ci`、`acceptance` 仍为空，G-P0/M0 未 VERIFIED，七项整改仍 OPEN_TRACKED。

恢复时先读 `handoff.json` 与执行包，实际核对 branch/HEAD、用户报告 hash、输入manifest及Code证据适用性。用 `preparation/pinned-baseline.json` 取得最新 scope pin；用 handoff 中已实际固定的 review pin/ref，输出到新的 dist 目录。若代码或被审字段变更导致处置不匹配，重新审查受影响部分，不能复用旧PASS或自动开始 V2-004/P1。

更新 IMPLEMENTED/类型化证据/活动输入后，raw/020 的全套治理聚合再次PASS；现行源记录为3项IMPLEMENTED、57项OPEN。代码、测试和锁文件相对实现提交没有再变。最终技术处置与当前交接检查保存在 `final/` 和 `handoff.json`。

最终 metadata/review pin 为 `f599dd821b61c2b7e347efc6834d63d54e7f0028`，raw/021 的真实当前上下文入口检查PASS；压缩完整报告见 `final/metadata-entry.json.gz`。封存提交只记录以上结果，不把源码证据改绑到封存HEAD。
