# 任务执行与关闭证据

## 1. 开始任务

读取 backlog 中 task、对应现行规范、验收场景和必需 ADR。确认前置 Phase Gate 与依赖任务已 VERIFIED/CLOSED。若该任务仍需细化（PLANNED），先把输入、测试场景、产物路径、范围、负责人和待决项补齐，才转 IN_PROGRESS。

AI 执行同时遵守 [AI 开发执行协议](AI_EXECUTION_PROTOCOL.md)。正式开工由任务的 `execution_packet_ref` 绑定非模板执行包；准备、实现、付费调用和认证分别检查前置条件。已有授权内的正常实施和修复自主推进，缺少必要依据则阻断对应动作，不靠模型猜测补齐，也不要求用户逐项重复批准。

前四任务已提供执行级要求，可以开始；并不意味着它们已实现。后续任务具备明确目标和验收映射，具体接口设计在最晚决策点前细化。

`normative_specs` 指向本包现行规则；`design_references` 指向对应领域的原始详细设计快照，便于查阅候选字段和研究背景。参考快照中的旧阶段、证据语义、缺陷 Schema 和完成状态不恢复为现行规则。任务产物与目标测试路径相对项目根目录；规范、参考和验收记录引用相对 plan 目录。

## 2. 状态机

```text
OPEN → IN_PROGRESS → IMPLEMENTED → VERIFIED → CLOSED
```

IMPLEMENTED 表示代码/配置已存在；VERIFIED 需对应测试与 CI；CLOSED 还需验收记录与未关闭缺陷的明确处置。发现回归可以重开，历史证据不删除。

`evidence.code`、`tests`、`ci`、`acceptance` 在 VERIFIED/CLOSED 时都必须有可定位引用，绑定同一变更/提交。生产测试失败不能仅修改状态字段。填写 [验收模板](templates/TASK_ACCEPTANCE_RECORD.yaml)。

## 3. 计划测试与已执行测试

[test-catalog.yaml](machine/test-catalog.yaml) 记录每个任务的计划场景、断言和未来测试路径。当前状态 PLANNED，所有未来代码路径都明确是 expected outputs，不要求本资料包中已经存在。

文件存在校验只应用于现行规范、来源与已提交证据；不能为了路径校验通过创建空测试文件。业务实现完成后，需把测试状态和运行证据更新为真实结果。

## 4. 常用命令

在项目根目录运行：

```bash
python3 plan/scripts/validate_plan.py --check
python3 plan/scripts/validate_plan.py --write-views
python3 plan/scripts/validate_plan.py --self-test
```

`--check` 不修正不一致；检查后输出范围明确的 JSON。`--write-views` 仅从机器源重新生成只读表；不能自动关闭任何任务。`--self-test` 在内存/临时环境注入任务错位、循环、空 CLOSED、缺失证据等反例，确认验证器确实拒绝。

本脚本只验证实施资料，不替代后续 pytest、PostgreSQL、CI 或真实 Provider 测试。源版本变化后重新检查；包内结果不适用于未记录的新版本。

## 5. 工作纪律

优先完成当前关键链及必要防线，不新增没有消费者的模块或 Schema。不从 archive 直接抄入已知缺陷实现。不把外部研究结论当本系统收益证明。用户新决策进入机器源/正文及影响登记，避免依靠聊天隐式维护版本。

## 6. 外部机制的任务接入

任务可通过 `external_practices` 引用[外部经验登记](machine/external-practice-register.yaml)。登记项的关联任务和场景必须双向匹配；修改验收要求时同步任务清单与 test-catalog，验证器拒绝只改一边。

开始相关任务时核对来源局限，在既有 ADR 中细化本地接口，不新增同职责框架。验收记录中的 `external_practice_results` 写明采纳 ID、独立实现/复用方式、适用版本或来源说明、本地测试引用、收益结论与局限。复用上游代码/提示词时补齐不可变 revision、文件路径及许可处理；没有上游代码复用则明确标注，不伪造 commit。

## 7. v1.2 类型化完成证据

`evidence.*[].ref` 指向包内正式证据 JSON/YAML，不直接指向 README、模板或远程 URL。记录服从 [evidence-record.schema.json](schemas/evidence-record.schema.json)，包含身份、种类、subject、实现 revision、生产者、时间、环境、原始产物引用/hash 与上游证据引用。原始代码/运行输出可归档到 `validation/`，远端 CI 另记录 pipeline/job ID 和 URL。Git SHA 格式与哈希匹配只能证明结构和绑定，不能认证操作者或远端来源真实性。

| 引用位置 | 必需种类/约束 |
|---|---|
| task code / tests / ci / acceptance | CODE / TEST_RESULT / CI_RUN / ACCEPTANCE_RECORD，所属 task 与 revision 匹配 |
| suite execution_evidence | TEST_RESULT，覆盖本套件全部 scenario ID |
| ADR decision_record | ADR_DECISION，decision=ACCEPTED，并引用正式决定原文；模板不作决定 |
| phase evidence_refs | PHASE_DECISION，绑定本阶段任务验收及本次适用 CI |
| milestone evidence_refs | MILESTONE_DECISION，绑定对应已验证阶段与必要任务验收 |
| finding closure_refs | FINDING_CLOSURE，绑定已履行责任任务的验收 |

测试/CI 记录还需命令、退出码及检查 ID；任务验收需覆盖验收场景并逐项记录 finding_dispositions。处置包括已解决、部分解决、转交或有理由的不适用；部分解决/转交需剩余工作、接手任务、责任角色和 gate。证据来自当前任务的实际责任范围，不强迫一个早期任务关闭整个跨阶段 finding。

阶段关闭聚合已启用的 every_change CI；真实 Provider 在首个 P5、P8/P9 认证及模型/Provider 影响发布时取得适用证据，仍不要求每次普通提交调用 Provider。先验证任务和 CI，再验证阶段，再汇总里程碑；阶段不等待里程碑字段回写，避免互相依赖。

本次里程碑决定必须与它消费的阶段决定绑定同一被核验 revision，阶段适用 CI 也绑定该 revision；较早任务已经通过的历史证据可保留原 revision，由当前集成检查确认仍适用，不强迫整个历史证据图同 SHA。Artifact 是否来自模板目录按解析后的真实包内路径判断，`..`、`./` 或符号链接不能改变模板身份。

离线校验无法抵抗仓库写入者同时伪造记录、原始输出和校验代码。V2-004 仍负责真实 CI 接入与保护策略；有权限的核验者核对远端 run/revision/artifact。结构通过不授权自动关闭任务，也不证明业务正确。

另运行 `python3 -B plan/scripts/test_governance.py`，验证合格完成链与单点反例。旧审核探针保留在 archive 和原审核包，新运行结果不得覆盖旧证据。

## 8. 开工记录与变更记录

实施时使用[执行包模板](templates/EXECUTION_PACKET.yaml)明确本任务操作者、验证者、输入输出、估算区间及假设、付费上限与停止条件。一个人可以承担多个角色，但不能称其为独立审核。没有实测吞吐时允许估算未定，不把报告中的固定团队人数或日历工期设为准入条件；付费调用没有批准的上限则不能开始。

执行包同时记录 `plan_version`、`repository_revision`、工作区是否有改动、`plan_manifest_sha256` 和实际环境，并绑定适用规范/输入 hash、允许变更范围、验收、动作、事实/假设/未知、待决项与恢复记录。它是执行上下文，不是代码/测试/CI 的完成证据；模板中的 null 不能当作已核验值。P0 四任务复用这一模板与既有执行顺序，环境信息随 V2-001 的实际决定填写，不新增一份平行 P0 规范。停止条件区分预算/环境阻断、验收失败后的修复和是否继续投入；单次失败不自动等于永久放弃项目。

规划修改记录来源、采纳/调整/延后/不采纳理由、影响任务/ADR/场景和验证结果。既有用户授权范围内的完善无需额外逐项审批。修改冻结路线、任务身份或最低门禁属于显式基线变更，需说明用户授权依据和影响，不能用 `--write-views` 悄悄生成更弱基线。

## 9. CI 产物与运行记录边界

`plan_execution_evidence` 只接收具备关闭资格的 PASS 见证，失败和未知执行使用所属任务的原始记录。负例测试成功拒绝错误时，测试自身可 PASS；这不把被注入的失败调用改记为成功，也不删除其原始输出。

正式证据按“提交 → 实际 CI 运行 → 产物 → 核对 → 验收引用”生成。仓库内已经提交的 `validation/*.json` 是可追溯快照，不能自己证明包含它的下一提交已通过。V2-004 核对可信 CI 服务中的项目、commit、pipeline/job、结果和产物 hash；仅有看似合理的 URL 或本地 JSON 不构成远端真实性。

校验和自测支持 `--output-dir`；治理回归同样支持该参数。CI 选择 `plan/` 外的独立生成目录运行 `--check` / `--self-test`，不使用 `--write-views` 自动修正被测源。GitLab 可使用项目内已忽略的 `dist/validation/`，由 job 上传；其 `artifacts:paths` 相对项目目录，不能直接引用项目目录外的文件。输出到外部临时目录时，先复制到项目内的 artifact 目录再上传。参见 [GitLab 官方 artifact 路径约束](https://docs.gitlab.com/ci/yaml/#artifactspaths)。

旧探针可用 `--output` 指定结果文件。输出目录只改变报告位置，不使任何命令自动成为真实 CI，也不改变冻结基线。V2-004 配置适当的产物保留与失败上传规则，保留可获得的失败原始记录；任务取消、超时或执行器丢失导致产物不完整时明确记录缺失，不能声称取得了不存在的日志。

## 10. AI 推进中的差异与恢复

P0 将任务范围与实际代码差异关联，并对验收删减、测试 skip、阈值下降、排除扩大和门禁修改做基线比较。正文、任务验收和测试同时修改仍需评估要求是否被放宽，不能仅凭三者一致放行。受信任比较基线及有效权限由真实交付环境提供，本地结构检查不能自证可信。

在 `PREPARE` 中允许调查未决 ADR；转 `IMPLEMENT`、`LIVE_CALL`、`CERTIFY` 时，按 ADR 最晚时点核对正式决定。任务写成 IN_PROGRESS 不表示所有后续动作都获准。交接记录保存真实结果与下一动作；恢复先与工作区和输入 hash 核对，版本变化后重验受影响证据。详细规则及 V2-002～004 分工见 [AI 开发执行协议](AI_EXECUTION_PROTOCOL.md)，不以本轮文件新增关闭这些工程任务。
