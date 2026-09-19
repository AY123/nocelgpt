# ANovel V2 架构规划资料审核评估报告

审核日期：2026-09-18～2026-09-19（资料基线为 2026-09-18）  
审核对象：`/Users/angyang/Documents/AI/ANovelOS/gptdoc/`  
裁决基线：用户本轮明确冻结的 P0–P14 路线、双 Anchor Genre 与先生产内核后高级智能的实施策略。  
报告性质：独立架构与规格审核；不是新的总体架构规范，不替代现有宪章，也不代表 V2 已通过运行认证。

## 1. 审核裁决

**保留总体架构与实施路线；有条件进入 P0；现有材料尚不足以作为“交给任意 AI 后可逐项无歧义实施并自动验收”的冻结执行基线。**

这一判断包含三个不同层次：

| 层次 | 裁决 | 理由 |
|---|---|---|
| 产品与架构方向 | 通过 | 中文长篇、题材约束、独立 Canon、编译式 Contract/Context、持久工作流与质量分权，方向一致 |
| P0 启动 | 有条件通过 | 仓库、锁依赖、规范索引、门禁与 PostgreSQL 测试环境可以开始；规范冲突和 P0 验收条目应在 P0 中收敛 |
| 全部规范“实施就绪” | 暂不通过 | 存在可复现 Schema 缺陷、同名枚举语义冲突、阶段验收倒置与任务验收占位 |
| P0 已完成 / CI 已绿色 | 无证据，不作此认定 | 本次只审核规划资料，没有建立 V2 仓库流水线或运行 PostgreSQL/Provider 认证 |
| 双 Genre 已支持 | 无证据，不作此认定 | 当前提供的是设计和一个 DRAFT 都市示例，尚无双题材实际认证结果 |
| 能生产起点爆款 | 尚未验证 | 可靠性架构解决可控生产问题；读者吸引力与商业表现仍需文本、人工及真实市场证据 |

**建议冻结的是方向、边界和实施顺序，允许通过小型勘误与 ADR 修正规格缺陷。** 如果连已复现的 Schema 错误也不允许修订，“冻结”反而会把错误固化进实现。

不建议增加第 16 份总体研究文档。下一份仍应是用户指定的 `PHASE_0_REPOSITORY_BOOTSTRAP_EXECUTION.md`，将本报告中到期于 P0 的整改嵌入 V2-001～004，其余问题进入对应任务验收。

## 2. 审核范围、方法与证据边界

### 2.1 覆盖范围

纳入全部 15 个资料包，共 136 个文件，排除系统 `.DS_Store`：

| 类型 | 数量 | 本次检查 |
|---|---:|---|
| Markdown | 15 | 逐域核对职责、权威、状态、阶段、接口和验收要求；重点交叉检查核心生产链 |
| YAML | 37 | 全部解析；检查任务图、政策、测试矩阵、Genre 示例与研究来源登记 |
| JSON | 84 | 全部解析；其中 65 个 JSON Schema 做 Draft 2020-12 元模式校验 |
| MANIFEST | 15 | 验证全部 121 个登记文件的 SHA-256 |
| Schema `$ref` | 13 | 在离线 registry 中逐个解析，不依赖远程下载 |
| 首批任务 | 60 | 检查 ID、依赖存在性、环路、祖先依赖、Schema、规范/测试/产物引用 |

审核同时参考本工作区此前对 V1 指定提交的实际检查记录，作为失败模式补充；不把历史报告的完成声明当作当前 V2 的运行证据。本次没有再次执行 V1 全量测试，也没有执行 V2 生产测试。

此前“novel → 深度分析项目”任务的完整历史读取曾被验证页面阻断，本报告**不声称已完整读取该聊天**。本轮交付的本地资料与用户最新冻结说明构成本次主要依据。

### 2.2 实际执行结果

| 检查 | 结果 | 可以证明什么 |
|---|---|---|
| JSON/YAML 解析 | 0 错误 | 文件语法可读 |
| 65 个 Schema 元模式校验 | 65 通过 | Schema 自身语法符合相应元模式 |
| 13 个 `$ref` | 13 可离线解析 | 现有正式 Schema 引用可解析；不包括 `schema_ref` 等普通业务字符串 |
| 121 个 Manifest 哈希 | 121 一致 | 当前文件与各包登记内容一致 |
| 60 个任务 Schema | 60 通过 | 当前宽松任务结构可容纳现有清单 |
| 任务依赖 ID / 环路 | 无缺失 ID、无图论环路 | 依赖图形式合法；不等于阶段验收依赖完整 |
| 对照样例 | 3/3 符合预期 | 都市示例可验证，hard→ignore 被拒绝，基础实体可验证 |
| 定向契约探针 | 12/12 暴露契约缺口或正例拒绝 | 部分声明的业务条件没有落入当前 Schema，且存在类型组合错误 |

**12 个探针不是“发现 12 个运行时漏洞”，也不是随机样本失败率。** 它们是有意选择的反例与正例，用来识别规格边界。部分规则应由领域服务、数据库或政策验证器执行，而不是全部塞进 JSON Schema；问题在于必须明确执行者与验收证据。

审计脚本、每个探针的完整输入、错误路径、文件清单和哈希随报告交付。运行环境为 Python 3.9.6、PyYAML 6.0.1、jsonschema 4.25.1、referencing 0.36.2；这是审核工具环境，不是对 V2 的 Python 版本选型。

### 2.3 证据分类

本报告使用三类标记，避免把推断当成已发生故障：

- **已复现**：当前资料可通过脚本验证的问题。
- **已确认冲突**：两个规范或机器附件给出不一致要求。
- **实现风险 / 待细化**：原则已有，但尚无足够具体的契约、任务或验收；不等于实现已经错误。

问题编号采用 `AR-01`～`AR-20`。严重性以“阻塞哪个阶段的关闭”表达，避免与阶段 P0、缺陷优先级 P0 混淆。

## 3. 值得保留的架构决策

### 3.1 对 V1 根因的修正是成立的

资料不再将失败简单归因于 Prompt 或某个模型，而是重新确定谁拥有事实、谁可以提交、什么条件下必须停止。这直接对应 V1 的多决策中心、错误正文继续推进、状态写入口分散和恢复语义薄弱。

应长期保留以下决策：

1. **Draft → Delta → ChangeSet → Permit → Commit 的分层。** 每一步有不同权威，可以隔离“模型声称发生”与“项目正式接受”。
2. **Canon 与 WorkflowState 分离。** 重试、失败、暂停属于生产过程，不能改写故事历史。
3. **Genre 为基础能力。** 题材由现实模型、世界规则、机制、成长、叙事引擎与扩展共同决定。
4. **Contract 和 Context 编译。** 将当前任务需要的约束与事实固定成可追踪输入，减少临时拼接和隐性默认值。
5. **Q0–Q3 与语义偏好分权。** 高文笔评分不能覆盖确定性事实冲突。
6. **Repair 后重新抽取、重新验收。** 不复用旧 Permit，不让“修好了一个问题”掩盖新变化。
7. **真实 Provider 验证。** 避免只证明 Mock 能跑。
8. **按 1→10→30→100→300 章逐步建立证据。** 比一开始搭几十个 Agent 更适合收敛风险。
9. **Reference、Market 与 Learning 无直接 Canon 写权限。** 复杂智能可以后加，不必破坏基础内核。
10. **明确停止功能开发的条件。** 让 Canon、安全与硬门禁故障优先于功能数量。

### 3.2 双 Anchor Genre 选择合理

`urban.business.realistic` 与 `fantasy.eastern.progression` 的事实结构和世界法则差异明显，适合检验 Core 是否被某个题材污染。

但两者通过，只能支持“这两个 Pack 在指定版本与认证条件下通过”的结论。它不能自动证明悬疑、历史、言情、无限流或家族多代叙事已经被支持。

“玄幻不被商业 Schema 污染”应指：没有被无条件要求公司、股权等字段，没有加载错误约束，没有共享错误状态。它不应被解释成玄幻不能存在商会、交易、资本或经营冲突。

### 3.3 复杂性控制基本正确

当前资料推荐以模块化单体、PostgreSQL、类型化模型、少量可恢复工作流构建初版，并把微服务、Kafka、Kubernetes、图数据库和 Agent Swarm 延后。这个策略与当前风险匹配。

仍需注意：大量目录、65 个 Schema 和众多“Domain”名称本身也可能造成复杂性。它们是逻辑职责和长期规格目录，不应全部变成首批运行模块、独立服务或独立持久化表。

## 4. 主要问题登记

| 编号 | 主要问题 | 证据性质 | 最晚关闭点 |
|---|---|---|---|
| AR-01 | 宪章与实施计划的里程碑编号、机器附件不一致 | 已确认冲突 | P0 规范索引关闭 |
| AR-02 | E1/E3/E4 证据含义发生变化 | 已确认冲突 | P0 术语基线；P7 必须统一执行 |
| AR-03 | Character 扩展字段被基础 Schema 拒绝 | 已复现 | V2-006 |
| AR-04 | 操作、事实与转移语言类型约束不足 | 已复现 + 待细化 | V2-008～010、V2-017 |
| AR-05 | QualityDecision→Permit 的放行证据契约不闭合 | 已复现 + 待细化 | P2 基础防线、V2-026 集成 |
| AR-06 | 60 个任务缺少具体规范、测试和验收证据映射 | 已复现 | P0 首批任务；逐任务实施前 |
| AR-07 | 任务图不能表达 M0、M4 和恢复认证门槛 | 已确认冲突 | P0 图规则；P6/P8 关闭前 |
| AR-08 | P10 前初始 Canon/Genesis 输入如何建立未闭合 | 已确认依赖缺口 | P2 初始化、P4 规划输入 |
| AR-09 | 逻辑叙事事务与数据库事务容易混淆 | 规范歧义 | V2-009～011 |
| AR-10 | 哈希、正文持久化、绑定与失效协议不够精确 | 已复现 + 待细化 | P2/P4/P5 各相关任务 |
| AR-11 | Scene 内推进与 Chapter 级提交之间缺少候选状态协议 | 实现风险 | P4～P6 |
| AR-12 | “抽取结果合法”与“正文没有违规”之间仍有盲区 | 实现风险 | V2-021～025、P8 |
| AR-13 | 项目/分支隔离没有贯穿全部键与契约 | 已复现 + 待细化 | P2/P5 |
| AR-14 | Provider 结果未知、费用与恢复状态不足 | 已复现 + 待细化 | V2-019/027 |
| AR-15 | 双 Genre 仍缺可执行扩展与边界正例 | 已确认资料缺口 | V2-015/016、P8 |
| AR-16 | 认证状态、准入、报告和度量协议不完整 | 已复现 + 待细化 | P8 前冻结、P9 验收 |
| AR-17 | CI 缺阶段启用规则及真实 Provider 的强制放行条件 | 已确认附件缺口 | P0 规则、P5/P8 证据 |
| AR-18 | 平台横切要求缺少早期任务归属 | 执行风险 | P0 分配；随数据/调用引入 |
| AR-19 | 研究来源可追踪性不足以支持全部强结论 | 资料质量问题 | 进入对应 ADR / P10 / P13 前 |
| AR-20 | 工程认证与中文网文可读性、商业验证缺少明确交付分层 | 产品验收风险 | P8/P9 文本验收；P11/P13 校准 |

以下展开每个问题的影响、最小修订与验证方法。

## 5. 规范、Schema 与任务执行审核

### AR-01：同一里程碑编号已经表示不同能力

**证据：**[宪章里程碑][constitution-milestones]中 M5=30 章、M7=100 章、M8=多源 Genesis；[实施计划里程碑][milestones]中 M5=Repair、M7=30 章、M8=Genesis。外部架构研究仍写“M5 前不优先复杂能力”。宪章正文的 INV-009“可由 Event Log + reducer 重建”未出现在 YAML 的 hard_invariants 中。

用户最新冻结说明已经明确采用新实施路线，所以实际执行意图不模糊；**问题是仓库材料尚未记录这次覆盖关系**。一个只读上位宪章的 AI 可能按旧 M5 解锁范围，另一个读取实施计划后按新 M7 执行。

最小修订：P0 建立唯一的里程碑注册表，记录新编号、旧编号映射与 supersedes；同步宪章附件或明确其过期字段。规范索引区分已批准决策、候选 ADR、研究输入、示例与实现契约。对 INV-009 标注 SHOULD/required 的真实规范强度，避免机器附件无声漏项。

验收：任何任务对 `M7` 的解析结果唯一；旧编号不会触发阶段放行；正文和机器附件的 invariant ID 差异必须有解释。

### AR-02：证据等级不是同一套语义

**证据：**[宪章证据表][constitution-evidence]与[质量规范 §12][quality-evidence]定义如下：

| 级别 | 宪章 | Quality Spec |
|---|---|---|
| E0 | 确定性证据 | 确定性证据 |
| E1 | 结构化抽取 | 已验证结构证据、平台事实、人工批准事实 |
| E2 | LLM / 多模型评价 | 模型评价 |
| E3 | 人工 Gold / 盲评 | 模拟读者 / 商业预测 |
| E4 | 真实读者 / 市场 | 人工与真实市场合并 |

E3 的冲突尤其严重：同一个值可能表示真实人工评价，也可能表示模拟读者。`evidence-record.schema.json` 只限定 E0–E4 枚举，无法识别这类语义漂移。

最小修订：在 P0 统一枚举语义，按当前宪章或一份显式批准的修订确定唯一版本。将 `source_kind`、`verification_status`、`authority_scope`、`calibration_ref` 与 E 编码分开，避免一个数字同时承担来源、可靠性和权限。

验收：模拟读者不可能被序列化成人工 Gold；LLM 抽取不会因为输出了合法 JSON 就升级成已验证事实；历史记录有明确映射版本。

### AR-03：Character 的正常字段无法通过 Schema

**证据：**[Character Schema][character-schema]通过 `allOf` 引用 NarrativeEntity；[基础 Schema][entity-schema]设置 `additionalProperties: false`。基础 Schema 不认识 `identity`、`personality`、`current_location` 等 Character 新字段。

`PROBE-01` 给合法基础实体加上 `identity: {species: human}`，即被拒绝。反过来，`PROBE-02` 使用 `entity_type: Location`、`lifecycle: 受伤`，却能通过 Character Schema。

这是具体类型契约缺陷，不是尚待实现的业务规则。[JSON Schema 官方文档](https://json-schema.org/understanding-json-schema/reference/object#extending-closed-schemas)说明了封闭基础 Schema 与 `allOf` 组合时的限制。

最小修订：选择开放的公共定义 + 叶子层封闭，或展开共享属性等一种一致策略；在适用层使用 `unevaluatedProperties: false`，不能只在派生层加它而保留基础层原有阻断。为 Character 固定实体类型，并按实体类型约束 lifecycle。

验收：每个特有字段都有正例；非 Character、受伤充当 lifecycle、未注册字段有负例；由 Pydantic/领域类型生成或手工维护的 Schema 必须与同一批实例一致。

### AR-04：NarrativeDelta、ChangeSet 与 Contract 还不是足够精确的执行语言

**证据：**[Delta Schema][delta-schema]中操作只要求 `op` 与 `subject`；`value` 无类型；[ChangeSet Schema][changeset-schema]的 `op` 是任意字符串，`validation_summary` 可以为空。Chapter/Scene Contract 的转移、protected facts、knowledge boundary 大多只是对象数组。

`PROBE-03` 中没有 path、value、evidence 的 `SET_FACT` 被接受；`PROBE-04` 中未注册操作被接受。正文又允许扩展注册新操作，而 Delta 的 op 枚举是封闭列表；需要明确扩展采用通用宿主操作还是注册后编译 Schema。

这样直接实施，容易得到“外壳很规范、里面全是自由字典”的系统。都市金额、股权和玄幻境界的合法性又会落回 Prompt 或分散 if 判断。

最小修订：P1/P2 先定义首批所需的有限操作代数；每种操作声明输入类型、前置条件、幂等/重复含义、证据要求与 reducer。P4 的 RequiredTransition 复用同一语义，不重新发明另一套字段解释。

这里不要求现在补完所有未来实体 Schema，但 P1 声明要实现的 FactClaim、时间、资源与未知值语义必须有正式类型或明确替代表示。禁止用 null 同时代表 unknown、无变化和删除。

验收：每种操作至少有正例、缺字段负例、错误实体类型、过期前值、重复应用和跨 Genre 负例；未注册 extension 必须在提交前被拒绝。

### AR-05：放行凭据的“存在”尚不能证明完整验证已完成

**证据：**[Permit Schema][permit-schema]允许 `decision: ALLOW` 配合空 `validation_refs`，且 issuer、issued_at 并非强制完整凭据；[QualityReport Schema][quality-report-schema]允许所有层为空后写 `PASS`，也允许确认的 Q0 HARD_FAIL 与 PASS 同时出现。对应 `PROBE-05/06/07` 均通过。

需要明确：允许 DENY 出现在一个决策记录里未必错误；错误在于不能把“任何符合 CommitPermit Schema 的对象”视为有效通行证。当前正文已经要求 permit_allow，后续必须落实为受保护的服务校验。

最小修订：定义检查执行记录与 Findings 的区别。每个必跑 check 有 `check_id/version/status/input_hash/result_ref`；没有 Findings 不等于检查跑过。缺失、ERROR、UNKNOWN、未授权 SKIP 都不能发 Permit。

还需处理首期范围：当前 QualityReport Schema 强制要求 Q0～Q7 全部数组，而冻结首期只实现 Q0～Q3。正文的完整质量 Gate 又包含 Q4/Q5/Q7 条件。应把完整愿景与当前版本所支持的检查集合分开，显式记录未实现/不适用层；不能为了满足 Schema 填空数组后将其解释为“Q4～Q7 全部通过”，也不必因此提前实现所有语义评估。

PermitIssuer 必须验证所需 check 集合、候选/父提交/政策一致性、授权者、适用模式和有效期。CanonCommitService 重新核验 Permit 来源与绑定，拒绝模型提交的伪造对象。实现可使用受保护 DB 记录，不必提前引入复杂签名基础设施。

验收：空证据 ALLOW、缺 Q2、Q0 HARD_FAIL+PASS、旧候选证据、新 Policy 搭旧报告、旧 Permit 配修复后正文、非授权 issuer 全部不能 Commit。JSON Schema 能表达的结构约束进入 Schema；跨对象与授权约束进入领域服务和数据库测试。

### AR-06：任务清单目前更接近目录，不是完整实施包

**机械检查结果：**60/60 任务只引用 `PROJECT_CONSTITUTION.md`；60/60 的 `artifacts` 与 `out_of_scope` 为空；tests 为 `TEST-V2-NNN`；这些引用未映射到本次发现的 114 个 test-matrix ID。所有任务均为 OPEN，没有虚假 CLOSED 的实际记录。

任务的三条验收普遍是“按规范实现、所需测试通过、CI 硬门禁通过”。这与[实施计划任务模板和映射示例][implementation-task-template]要求的具体输入、相关规范、实现边界和产物不等价。

`PROBE-09` 还证明：当前 Task Schema 允许没有测试、验收条目和证据的任务标记为 CLOSED。

最小修订：不必现在把 60 个任务扩写成 60 篇文档，但任务进入 IN_PROGRESS 前必须形成完整 Task Packet。首批 V2-001～004 在 P0 执行文档中一次补齐；其余按阶段滚动细化。至少包含版本固定的规范段落、真实测试 ID、预期失败行为、产物路径、排除范围和闭环证据。

CLOSED 应由验收工具检查证据而非手改枚举决定；纯文档任务、基础设施任务与业务任务可有不同证据类型，但不得省略证明。

验收：给另一位实现者只提供单个 Task Packet，能确定要改什么、什么不做、如何证明失败路径正确；未生成真实测试结果或 CI 不属于当前提交时不能关闭。

### AR-07：任务图形式无环，阶段语义仍不闭合

**证据：**[Backlog][backlog]中 V2-005 只依赖 V2-001，不依赖 V2-002/003/004 或 M0 Gate。仅按 dependencies 调度，会绕过“P0 真正绿色后才进入 P1”的冻结要求。

另外：

- P6 文本要求真实 Q0–Q3→Permit→Commit，并连续 3 章；Q0–Q3/Permit 集成在 P7 的 V2-022～026，3 章 smoke 是 P8 的 V2-033。
- V2-028 Kill/restart Harness 不是 V2-034/035/036/040 的祖先依赖，认证链可在任务图上绕过它。
- V2-050 GoldenSet、V2-051 RegressionSet 不在 V2-056/057/060 的必要依赖路径上；若 Calibration 实际需要它们，应明确数据就绪门槛，而不是依赖任务顺序习惯。
- `architecture-dependency-graph.yaml` 只有线性 critical_path 列表，未表达 Q0–Q3 与双 Genre 的并行汇合；它与真实 dependencies 不是同一 DAG。

最小修订：区分 **实现依赖**、**阶段开始门槛**、**认证关闭门槛**。P6 可以交付工作流执行骨架与阶段接口，但不能在 P7 门禁实现前宣称真实生产闭环已认证。M4 在所需集成通过后关闭，不必为此重排用户冻结的主路线。

关键链应作为核心依赖链表述；缺少工期与资源约束时，不能视为已经计算出的项目管理关键路径。

验收：模拟调度器在 M0 未 VERIFIED 时不得启用 V2-005；M4 不得在 V2-026 前关闭；10/30 章认证需要恢复测试证据；后续任务不能仅因编号较大便被当作具备前置能力。

## 6. Canon、上下文与生产执行审核

### AR-08：初始 Canon 的最小引导协议缺位

**证据：**[Canon 初始状态][canon-genesis]要求通过 GenesisCommit 建立初始设定；Planning 的 SeriesVision 必须引用 GenesisSpec。[任务 V2-048][backlog-genesis]却到 P10 才实现 GenesisCommit，前面的 P2、P4、P8 已需要它们。

这不意味着应把 Reference Intelligence 或 Genesis Tournament 提前。真正缺少的是：**手工编写/受控 fixture 的最小 GenesisSpec 如何通过唯一 Canon 通路进入系统。**

还需统一 root：CanonCommit 允许 `parent_commit_id: null`，ChangeSet/Transaction 要求父 ID 字符串，Permit 要求父哈希字符串，Genesis 文本称 `parent = genesis root`。当前没有唯一的空分支/根提交协议。

最小修订：P2 定义一次性 Branch Initialization 和受控 Seed 输入，仍由 CanonCommitService 执行；固定 sequence 起点、root hash、唯一初始化约束。P4 使用人工准备的版本化最小 Genesis/Plan 输入；P10 才自动生成这些输入。

验收：两个并发初始化只有一个成功；重试返回同一根提交；两套初始状态不能静默覆盖；fixture 与生产提交走同一写入口；不得通过手工插表或读取任意 Bible 绕过历史。

### AR-09：需要明确短数据库事务边界与幂等冲突协议

**证据：**[Canon §8][canon-transaction]在 BEGIN/COMMIT 之间列出了编译、生成、抽取、验证及投影，失败均 ROLLBACK；[§19/20][canon-atomicity]又允许提交后投影失败并保留成功 Commit。

把 §8 理解为逻辑叙事事务可以成立；若照字面实现为包含 LLM 调用的 DB transaction，将产生长事务、锁与恢复问题。必须在规范中明确这两个“事务”不是同一个边界。PostgreSQL 事务只覆盖其自身数据库操作，不会替系统撤销外部模型调用。[PostgreSQL 官方事务说明](https://www.postgresql.org/docs/current/tutorial-transactions.html)

最小协议应是：生成和验证固定父提交的候选；随后开启短 DB transaction，检查授权/Permit/幂等键/CAS，追加 Commit+Events+推进 Head；成功后投影和 Workflow checkpoint 可分别补偿恢复。

幂等还需区分：同 key 同 payload 返回原结果；同 key 不同 payload 是冲突；同一章接受槽位不得通过换 idempotency_key 绕过重复提交保护。有效的第二次修订需要显式 revision/retcon 语义。

验收：真实 PostgreSQL 两连接竞争、提交响应丢失、CAS 0 行、重复 key 不同内容、相同 source 换 key、投影异常；已成功的提交不能因过期 Permit 或当前 Head 已变化而被错误当成新提交重做，应按身份/作用域返回可验证的既有 receipt。

### AR-10：哈希与 Artifact 协议还需要跨层统一

**证据：**平台规范提出 canonical serialization；不同规范给出若干建议哈希公式，但没有共同序列化协议和测试向量。[SceneContract Schema][scene-schema]没有 `genre_pack_hash`/`plan_hash`/作用域字段，而正文要求每个 Chapter/Scene Contract 绑定 Canon 和 Genre；`PROBE-10` 加入 genre_pack_hash 会被 additionalProperties 拒绝。通过父 Chapter 间接绑定可以设计，但必须正式定义并验证链路。

建议在 P2 前冻结最小 Artifact Envelope：schema ID/version、project/branch/scope、producer、input refs/hashes、content identity。分别明确：

- 正文 hash 基于哪一份精确字节、UTF-8 编码、换行和导出转换；不能在评价后规范化正文却仍沿用旧 hash。
- 结构化 hash 的 key 排序、数字/Decimal、null/缺失、集合顺序、时间格式、Unicode 策略，以及不参与 hash 的非语义字段。
- 不使用未分隔的字符串拼接表达复合身份；应使用版本化结构化编码。
- 若正文在对象存储而 metadata 在 DB：先保证不可变正文可持久读取，再引用提交；上传失败不得形成悬空 Commit，孤儿候选可按政策清理。
- “Artifact immutable”与状态由 ACTIVE→STALE 的关系：状态记录与不可变内容分离，或写新版本，不原地改变已参与签名/哈希的载荷。

验收：排序变化与合法序列化产生预期 hash；正文换行/修复变化必须被识别；缺失对象、错误 hash、失效祖先 Contract、不同 Genre 的 Context 均阻塞；重建使用的 schema/projector 版本可定位。

### AR-11：章内候选状态需要显式建模

**证据：**Planning 以 Scene 为生成/契约单位、Chapter 为 Commit 单位，并要求章内 Repair 后重验下游 Scene；Canon 规范要求 SceneDelta 按序聚合。但两者之间没有完整的章内候选状态生命周期。

例如第一场景拿到钥匙，第二场景用钥匙开门。如果每个 Scene 都只看章开始 Canon，第二场景前置条件不成立；如果第一场景直接写 Canon，又突破 Chapter 提交边界。

最小修订：定义基于固定 Canon Parent 的 `ChapterWorkingState` 或等价候选投影，绑定 run/candidate revision。经过章内验证的 SceneDelta 可影响本章后续 Scene；它仍是候选，不是全局事实。

同样需要定义 SceneContract 是逐场景编译，还是绑定可重建的预期 entry state；章内重排、Scene 1 修复导致后继 state hash 变化时，相关 Contract、Context、正文与证据全部按依赖失效。

验收：第一场景新增知识供第二场景合法使用；第一场景修复撤销知识后第二场景被重验；整章失败时无候选状态进入下一章 Canon Context。

### AR-12：必须检验抽取遗漏，不能只检验已抽取字段

**证据：**Narrative Spec 明确 unknown≠no change；V1 regression seed 也要求 extractor unknown 不能放过身份错误。这一原则是正确的。但当前 Delta 的 uncertain_claims/conflicts 可为空，没有强制的检查覆盖证明或“未能判定”协议。

最危险的例子是：正文写“主角凭空御剑”，Extractor 漏掉能力变化，输出空 delta；规则引擎只能看到“没有新增修炼字段”，于是符号层合法。**规则引擎对不完整输入的正确判断，不等于正文正确。**

最小修订：为合同关键义务、身份、世界法则、能力、资源和知识边界生成明确待检查集合；每项输出 supported/refuted/unknown/error 与正文证据位置。UNKNOWN 不必把整本书所有未知事实都阻塞，但当前提交依赖的关键命题必须完成判定或进入受控复核。

保留独立的正文→约束核对路径，用于发现 Extractor 未声明的变化；它输出证据，不成为第二 Canon，也不靠堆更多 Reviewer 替代覆盖率验证。记录判定是确定性计算还是依赖模型解释，不能把 E1/E2 输入经过一个 if 后包装成绝对 E0 真值。

验收语料必须包括：隐喻、梦境、戏中戏、角色误信、否定句、转述、回忆、无显式“灵气”词的超自然行为、正文与 delta 不一致、别名和称谓歧义。分别报告漏检和误杀。

### AR-13：作用域隔离必须落到数据库、缓存与载荷解析

**证据：**Canon 正文要求所有 Canon key 包含 project_id，但建议 UNIQUE 中出现 `UNIQUE(branch_id, sequence)`。若 branch_id 是全局 UUID，此约束可能成立；若是每项目常用的 `main`，则不同项目会碰撞。当前必须二选一明确。[ContextItem Schema][context-item-schema]又把 project_id/branch_id 设为可选，`PROBE-11` 接受无项目绑定对象。

GenrePack/全局政策等共享资料确实不该强行伪装成项目私有事实，因此修订不应简单把所有 item 的 project_id 都变成必填字符串。应定义 GLOBAL/PROJECT/BRANCH 等 scope 与继承关系。

最小修订：统一 ID 全局性、复合键/FK、查询 scope、缓存 scope、Artifact 解析和授权作用域；Context Compiler 从可信注册表确定 scope，不能信任模型提供的 authority/project 字段。

验收：两个项目使用同一人物显示名、相同章号、相同 `main` 分支和相似文本，交错执行与缓存复用仍不串；错误 project 的 Permit/Artifact/Context/回放请求全部被拒绝。仅 import 检查不能代替这些测试。

### AR-14：模型结果未知时不能承诺绝对不重复计费

**证据：**Workflow 已正确包含 `SIDE_EFFECT_UNKNOWN`、semantic request fingerprint、缓存复用和“可缓存条件下不重复计费”的限定。但未给出 Provider 成功后、本地保存前断线/崩溃的完整对账协议；timeout 被归入可重试 TRANSIENT。[ModelRun Schema][model-run-schema]只有 SUCCEEDED/FAILED/CACHED，且总要求 response_hash；`PROBE-12` 无响应的合法失败无法表示。

最小修订：区分请求未发送、已发送结果未知、已收到并持久化、明确失败、缓存复用；记录 provider request ID、attempt、费用已确认/待对账。若 Provider 支持可查询 receipt 或 idempotency，使用其能力；否则不可证明远端没有执行。

对未知结果自动重发须受 attempt/预算限制并标记可能重复费用；不能把本地缓存当成跨网络的 exactly-once 保证。Canon Commit 的本地事务幂等可以做强保证，两种边界要分开。

还要区分“同一逻辑请求恢复”与“主动采样多个候选”。后者即使 Prompt/Context/Model 相同也需要 sample identity，避免缓存把 Tournament 全部候选变成同一份正文。fallback 是新的 ModelRun/attempt，是否新建 WorkflowRun 必须明确，避免 Context 与 Workflow 文档中“new Run”含义不一致。

验收：成功后断线、响应后落盘前崩溃、UNKNOWN 对账、未返回 usage、预算冻结、fallback、显式新采样与恢复复用；错误分类不靠捕获全部异常后盲重试。

## 7. Genre 与认证审核

### AR-15：双 Genre 设计方向清楚，可执行业务边界尚未建立

**证据：**资料有[一个 DRAFT 都市 Pack][urban-example]，只有禁止 cultivation/magic 两条结构化 hard rules；company/equity/cash 的 schema_ref 指向当前包内尚不存在的业务 Schema；引擎 config 为空；没有东方玄幻的对应完整示例。这与当前仍处规划阶段相符，但不能据此宣称已支持双 Genre。

都市示例还开启 rebirth，同时 reality_model=realistic。此组合未必错误：可以是只发生一次的开局设定、梦境叙事或限定机制，但需声明边界，避免实现者一边禁止全部超自然、一边默认允许能力不断扩张。

V2-015/016 至少应具体到：

| 维度 | 现实都市商战 | 东方玄幻成长 |
|---|---|---|
| 状态 | 主体、现金/负债、权益、产品、人员与业务关系 | 境界、能力、功法、资源、器物与组织关系 |
| 转移 | 资金来源和用途、融资/稀释、所有权变化的类型与前提 | 突破前提、消耗、能力授权、代价、失败或回退 |
| 数值 | 单位/币种/精度明确；现金、利润、估值、收入不混同 | 资源单位、等级与实际能力区分；不同体系不可无条件比较 |
| 时间 | 工作/产品/机构变化需要合理时间；年代设定有具体来源 | 修炼时间、寿命与世界日历一致 |
| 合法例外 | 借款、亏损、赠与等应有显式事件，而非简单禁止负数 | 隐藏实力、特殊传承或合法越阶需在规则内表示 |
| 污染判定 | 区分真实超自然、比喻、广告、梦境、作品内引用 | 区分错误商业必填字段与合法商会/资源经营情节 |

验收：同核切换、交错双项目、正例、反例、边界例、未注册 extension 和规则不相容，均通过明确规则与正文证据验证。

### AR-16：认证需要一个可执行协议，不能只有章数与 PASS

**证据：**[Genre 认证定义][genre-certification]包含 C0～C8，其中 C4 Reference Mode 在 C5/C6 长篇测试之前；本轮路线却明确把 Reference Intelligence 排在 P10。实施计划正确区分 CERTIFIED_30 与 PRODUCTION_READY，但未给出两者各模式的完整准入矩阵。

[认证 Schema][cert-schema]可接受 `level: C6, status: PASS, metrics: {}, cases: []`，即 `PROBE-08`。没有强制的 run fingerprint、正文/提交清单、实际章数和证据附件。单一 level 字段也不足以自然表达“C5/C6 已过、C4 尚未实现”的能力矩阵。

需要解决三点：

1. **引导认证。** IMPLEMENTED Pack 在隔离 CERTIFICATION 模式可以运行；它不能因尚未 PRODUCTION_READY 而永远无法产生首轮认证。该模式仍执行 Canon/Genre 硬门禁，绝不是 unsafe bypass。
2. **阶段能力。** P8/P9 认证核心双 Genre 生产；P10 再增加 Reference 模式证据。未实现项显式 NOT_APPLICABLE/NOT_YET_SUPPORTED，不能伪造 PASS，也不能强迫把 Reference 前移。
3. **行为版本与认证状态。** Pack 内容 hash 固定；认证记录引用被测 hash。若把生命周期 status 从 IMPLEMENTED 改 CERTIFIED_30 后连内容 hash 都变化，必须避免“认证完即不再是被测版本”的自失效。

建议认证报告至少固定：被测代码/锁文件/Schema/政策/Pack/模型、初始种子、完整章节与 Commit 序列、失败尝试、修复次数、故障注入位置、恢复结果、费用、人工审查及明确拒绝条件。

“0 violation”必须区分候选违规、被门禁挡住的违规、进入 Canon 的违规、后验人工发现漏检。故障注入本来就应制造违规候选；如果把它们全计为认证失败，会反过来鼓励隐藏检测结果。

10/30 章是工程认证窗口，不是可靠率或商业效果的统计证明。单项目连续 30 章存在高度相关性；不能把章节当成 30 个独立实验，更不能用一次成功推广到全部书与题材。

### 建议采用的认证检查表

下面是本报告建议，尚不是已有冻结数值。具体抽样规模、语义阈值和预算上限应在每轮认证前登记，运行后不得调整标准追求 PASS。

| 认证 | 必须可证明 | 不得据此宣称 |
|---|---|---|
| 1 章闭环 | 合同→上下文→正文→Delta→Q0–Q3→Permit→Commit 全链，拒绝路径不推进 Canon | 长篇能力 |
| 3 章 smoke | 连续提交无缺口，前章事实真正进入后章，修复版本与最终接受一致 | 双题材认证 |
| 双 Genre 10 章 | 同核不同 Pack；错误跨域约束被挡；随机 kill/restart；合法边界不被无故误杀 | 30/100 章可靠性 |
| 双 Genre 30 章 | 明确 Arc 的推进与收束；多故障恢复；不靠隐性手修状态完成；人工检查漂移、人物、Promise | 商业 Production Ready 或稳定爆款 |
| 100 章 | 状态增长、Context 检索、成本、恢复、Schema/版本长期兼容；明确所认证的 Genre | 全部 Genre 都具备 100 章能力 |
| 300+ / 百万字 | 多卷、后期疲劳、Retcon、Promise 更新；实际总字数与长期读者证据 | 章数天然等于百万字 |

## 8. CI、平台与研究证据审核

### AR-17：CI 顺序正确，但阶段启用与阻断规则不足

**证据：**[ci-gates.yaml][ci-gates]把 deterministic E2E 与 Genre smoke 标记为 hard，但没有 enabled_from/适用阶段；P0 尚未有业务实现。live_provider 为 `hard: false, mode: scheduled_or_release`，不足以保证发布时真正阻断失败或缺失结果。

本报告不建议每个 commit 都付费跑模型。应明确三类运行：每提交的确定性测试；夜间/受保护手动的真实调用；进入模型支持/Genre 认证或发布时必须满足的真实证据。

真实证据应关联受影响的模型路由、Adapter、输出 Schema 与政策版本，并定义可接受的时效。一次任意模型成功调用不能永久替所有角色、所有 fallback 路由和后续代码版本担保；同样不要求每个角色都绑定不同 Provider。

建议把每个 gate 定义为：ID、适用阶段、触发条件、实际命令、失败与 skip 语义、证据路径、版本适用范围和责任任务。早期未到阶段的 E2E 显示不适用，不得以空测试或永远 return True 表示通过。

P0 的 Architecture Fitness 至少验证“能抓到违规”：在临时 fixture 中注入 Writer→Canon write import，CI 应失败；Secret Scan 使用明确合成标记检验扫描器配置；0 tests collected、所需测试全部 skip、扫描工具异常、依赖扫描未执行，均不能当绿色。

Fitness 还要区分静态依赖约束与运行时权限：禁止 import 可以防止常规误用，但共享 DB 凭证、原始 SQL、脚本入口仍需服务权限、数据库约束和集成测试覆盖。迁移身份应与普通运行身份区分。

### AR-18：平台基础必须分阶段落入任务，而非等最后统一补

**证据：**Platform Spec 要求授权、审计、Artifact 完整性、隔离、秘密清理、成本和恢复；前 60 个任务专门平台任务主要是安全门禁，以及 P12 的 V2-058 Backup/Restore、V2-059 Release Manifest。正文说“Day 1”，Backlog 尚未说明这些能力由哪些早期任务交付。

建议保留后期完整平台能力任务，但补上最小内核归属：

| 引入时点 | 同时具备的最小横切能力 | 建议归属 |
|---|---|---|
| P0 仓库 | 锁依赖、Secret Scan、日志脱敏基础、扫描范围、规范/Schema 注册 | V2-001～004 |
| P2 第一笔持久 Canon | scoped actor、受控写入口、关键提交审计、不可变 Artifact 引用、最小导出恢复样例 | V2-009～012 |
| P5 第一次真实模型调用 | 数据类别/允许 Provider、脱敏、调用与费用记录、预算上限、错误语义 | V2-018/019 |
| P6 恢复执行 | durable checkpoints、side-effect receipts、结构化失败、lineage | V2-020/027/028 |
| P8/P9 昂贵长跑 | 保留完整证据，至少能恢复本轮实验数据，事故冻结与恢复流程 | V2-033～040 |
| P12 长期运维 | 完整备份、灾难恢复演练、发布配置重建与运行手册 | V2-058/059/060 |

当前没有生产数据时，不必提前搭完整备份平台；但不能等到大量真实生成与人工标注已积累后才第一次验证恢复。恢复 snapshot 不等于恢复正文，数据库与对象内容必须共同验证。

### AR-19：研究资料可作为设计输入，不能直接作为能力或市场证明

本次抽查的 [DOME 原始论文页](https://aclanthology.org/2025.naacl-long.63/)、[ConWriter 原始论文页](https://arxiv.org/abs/2608.05169)、[MAGNET/ATLAS 原始论文页](https://arxiv.org/abs/2607.00918)与资料中的主要研究主题匹配：层级规划/记忆、状态转移约束/局部修复、角色目标/共享世界与图验证。这支持“借鉴这些设计思路”。本次没有复现它们的实验，不能据此给 V2 的百万字或商业效果背书。

[外部 source registry][reference-sources]存在只引用产品首页、基础设施文档入口或整卷论文目录的项目，缺少固定版本、具体段落、访问快照和 claim→source 绑定。ConStory-Bench 登记的是会议卷目录，本次访问也未成功获取，不能算该具体论文已独立验证。

市场资料引用的[《2025 中国网络文学蓝皮书》](https://wyb.chinawriter.com.cn/content/202608/10/content84876.html)可访问，能支持行业规模和若干创作趋势的背景讨论。但市场 snapshot 中信号多数仅列 M0/M1/M2 等来源等级，没有逐条 source ID/证据片段映射。本文不认定所有订阅徽章、推荐规则与趋势置信度已逐项复核。

最小修订：研究结论进入 ADR、Genesis 或 Market 输入前，补准确来源、版本/日期、抽样范围、观测与推断区分。把“没有找到完整覆盖系统”保留为检索范围内结论，不升级成“全球没有竞品”。平台推荐机制、榜单与热度作为可过期 evidence，不写死进生产内核。

P0 不需要重做全部外部研究；只需正确归档其权威等级，避免研究句子被 AI 当成已批准实现要求。

## 9. 中文网文产品适配与商业目标审核

### AR-20：需要把工程正确、文学可读、商业结果分开验收

现有规格已经正确承认 Q6 是 Proxy、人工也有偏好、市场受到曝光和流量影响。这些原则应保留。当前执行计划最强的是防损坏和防越权；对于“正文让人愿意追读”，仍主要停留在维度名称，缺少早期可观察的样本文本与人工判定标准。

本报告不建议把复杂 Reader Simulation、Corpus Learning 或自动市场系统前移。但需要区分：**P11 才建设正式 Human Calibration 系统，不等于 P8/P9 之前无人认真读正文。** 实施计划已有 human sample review，Genre 规范已有 C8；应把这些现成要求具体到评审角色、抽样、表单和判定记录。

中文网文第一批文本验收至少应检查：

- **人物主体性**：主角是否做出有代价的选择；配角与对手是否有独立动机，是否只为爽点配合。
- **类型兑现**：商战依靠具体决策、产品、组织与竞争，玄幻依靠世界法则、能力、资源与代价；不能只更换名词。
- **场景表现**：是否有可读对话、动作与信息差，避免每章变成状态变化说明书。
- **中文表达**：称谓、视角、时间指代、段落与对话习惯一致；“AI 味”由可定位样本和人工反馈讨论，不能当未经校准的确定性分类。
- **追读动机**：前几章兑现了什么、下一章为什么值得看；Hook 不必每章悬崖，也不应只靠假紧急。
- **长线变化**：第 20～30 章是否仍只是第一章套路换人重演；人物关系、选择空间和世界认识是否在变化。
- **创作自由**：合同约束高风险结果与禁止变化，不要把每句台词、情绪和所有小细节变成强制字段。

建议让双 Genre 10/30 章同时交付可连续阅读的正文、简短的作者意图、结构化工程证据和独立人工阅读记录。工程 PASS、阅读评估未通过时，允许承认“内核可运行、作品仍需改进”，不把两者合成一个高分。

到 P11 再建立系统化盲评、holdout、评审者差异与模型校准；到 P13 才用真实读者/市场结果验证 Commercial Proxy。论文、榜单案例和 LLM 共识都不能替代这一步。

## 10. 15 份资料逐份结论

| 资料 | 主要价值 | 审核意见 |
|---|---|---|
| 01 Constitution | 事实、权限、失败关闭与长期目标的上位原则 | 保留；修正里程碑覆盖关系、证据枚举同步与附件遗漏 |
| 02 V1 Forensics | 从真实旧问题提炼迁移边界和回归种子 | 保留为证据；任务必须映射种子，不能只归档复盘 |
| 03 External Architecture | 对规划、状态、上下文、恢复、观测的组合借鉴 | 保留；补版本与 claim 引用；研究结果不能成为 V2 已具能力的证据 |
| 04 Market/Genre Research | 多轴类型、读者承诺、长期叙事引擎 | 保留为时间受限研究；分类与趋势不能直接变永久 hard rule |
| 05 Genre Intelligence | Pack、世界法则、扩展、Fusion 与认证 | 主干合理；双 Pack 实体规则、合法边界与认证准入待落地 |
| 06 Narrative Domain | ID、关系、知识、事件、Promise 与未知语义 | 最优先修 Schema 组合；收敛第一批操作和实体类型，不一次做全本体 |
| 07 Canon | 唯一提交、CAS、幂等、重建、Retcon 分离 | 核心价值最高；补根提交、短事务、完整键、Artifact 持久化与 Permit 验证 |
| 08 Genesis | 四入口汇合、参考隔离、原创与用户意图 | 继续 P10；仅最小手工种子/初始 Canon 协议需要前置 |
| 09 Planning/Contract | 远粗近细、滚动重规划、转移而非措辞约束 | 补 typed transition、Scene 输入状态及 hash 绑定，避免类型只有 object |
| 10 Context | 显式编译、mandatory coverage、角色可见性 | 方向成熟；补统一 scope、稳定序列化、实际 Adapter 请求与 Context 的对应证据 |
| 11 Workflow | durable state、恢复、费用、唯一执行链 | 补 UNKNOWN provider result、状态转换与章内 revision；明确 P6/P7 验收分工 |
| 12 Quality/Repair | 多层证据、硬门禁、局部修复、人工校准 | 修证据枚举；补 check 执行覆盖与 Delta 漏检；明确早期 Q0–Q3 模式 |
| 13 Corpus/Learning | 数据权属、实验冻结、holdout、提升与回滚 | 继续延后；早期 regression fixture 与人工抽检不依赖整个系统建成 |
| 14 Platform | Secrets、授权、审计、隔离、恢复与供应链 | 按首次使用时点嵌入任务，不独立演化成另一个庞大平台 |
| 15 Implementation | 主路径、范围控制、60 任务、CI 与 Closure | 战略可执行；机器清单仍是骨架，P0 Gate 与闭环证据须变成实际约束 |

## 11. 首批 60 任务的实施就绪评估

下面保持现有任务 ID 与阶段，不新增并行的大功能。

| 任务 | 当前评价 | 实施前需要补齐 |
|---|---|---|
| V2-001～004 | 可开始细化与执行 | 四份具体 Task Packet、P0 CI 阶段表、规范冲突登记、工具故障不得假绿 |
| V2-005～008 | 概念清楚、类型尚不完整 | Character Schema 修正、ID/alias scope、Unknown 类型、类型化操作与真实实例测试 |
| V2-009～012 | 高优先级、必须先做强一致性 | root 初始化、短事务、DB constraints、幂等冲突、可重建版本和提交证据 |
| V2-013～016 | 可按双 Anchor 收敛 | 两套 executable extension、Pack 行为 hash、注册规则、双向隔离与正例 |
| V2-017 | 不应一次实现完整长期规划平台 | 第一批计划输入、typed transition、Scene working state、依赖失效与合同绑定 |
| V2-018～019 | 边界合理 | role/source/scope 校验、语义与实际请求绑定、Provider UNKNOWN、预算与真实调用证据 |
| V2-020～021 | 需要阶段式集成定义 | P6 引擎/端口与 P7 真门禁区分；Extractor 覆盖、证据位置、未知失败 |
| V2-022～026 | 第一阶段核心风险点 | check 集合、PASS/UNKNOWN/ERROR 语义、证据层级、PermitIssuer 与提交二次校验 |
| V2-027～028 | 不能成为认证可跳过的支线 | kill 矩阵、恢复幂等、版本变更、费用对账；必须进入 M6/M7 关闭证据 |
| V2-029～032 | 与前链一致 | Repair 的影响范围、重新抽取、必跑检查、候选版本、回退与循环预算 |
| V2-033～036 | 应从“runner”变成受控认证执行 | 真实章序列、相同内核版本、故障注入、失败计数口径、人工正文检查 |
| V2-037～039 | 保持小范围 | CLI/简单 inspection 即可；读取权威 Artifact，不维护第二状态 |
| V2-040 | P9 的主要交付，不只是脚本 | 双 Genre 30 章的证据协议、连续性、恢复、人工抽检和失败归档 |
| V2-041～048 | 继续 P10 | 四模式准入、Reference/Originality 检查、数据权属与安全；最小 seed 入口与自动开书分开 |
| V2-049～051 | 正式治理系统可延后 | 明确早期已有回归样例如何升级登记；不要把永久 regression 的首次执行拖到这里 |
| V2-052～057 | 实验设计方向良好 | 真实可用数据依赖、冻结指标、blind 协议、holdout、证据到 Promotion 的权限 |
| V2-058～060 | 长期运维与规模认证必要 | 早期最小备份与后期完整 DR 区分；100 章的 Genre 范围、可靠性和成本条件 |

补充：60 个任务只排到 P12，不是遗漏了 P13/P14 的架构。它们是首批 backlog；后两阶段可以在证据足够时细化。不能用“总共有 60 个编号”估算工期或完成百分比，V2-017、020、040 的实际工作量显著不同。

## 12. P0 的最小整改与退出标准

### 12.1 不需要等待所有未来规格完善才能开始

本报告建议 P0 同步完成两件事：建立工程仓库；把执行入口变得无歧义。未来的市场系统、学习系统、完整 GenrePack 都不属于 P0 的实现范围。

| P0 任务 | 必须交付的具体内容 | 可审核证据 |
|---|---|---|
| V2-001 | 明确 Python/依赖管理工具与测试 PostgreSQL 版本；新仓库包骨架；锁文件；基础 migration 与真实 DB fixture | 从干净 checkout 的安装/测试记录、lock hash、DB 集成任务结果 |
| V2-002 | Normative Index、资料权威类型、稳定 ID/版本、里程碑映射、证据枚举勘误、Manifest/Schema registry、Task→Spec/Test 映射规则 | 无未知引用；所有矛盾有唯一裁决或明确阻塞任务；现有 Schema 缺陷登记并安排修复 |
| V2-003 | 首批 architecture rules 的可执行检查、扫描范围、运行入口约束、必须失败的违规 fixture | 正常样例通过；注入违规样例确实失败；所需检查未运行时失败 |
| V2-004 | Secret/依赖扫描、脱敏基础、归档扫描、受控抑制流程、CI 证据和真实 Provider 后续触发规则 | 合成 secret 被拦、干净树通过、工具失败不是 pass、对应 CI 不可 allow_failure |

P0 至少应满足：

1. V2-001～004 各自有任务相关规范、明确验收和实际产物；不是只填写 OPEN→CLOSED。
2. 锁定依赖可从干净环境安装；具体版本由实施时的兼容性验证决定，不在本报告中虚构锁版本。
3. 全部资料归档并区分规范、研究、示例；里程碑与证据等级没有相互矛盾的有效定义。
4. Schema 元模式校验与实例校验分开；Character 等已知正例拒绝问题有修复或明确阻塞下一任务，不能宣称“全部契约已正确”。
5. Architecture Fitness 与 Secret Scan 至少通过一次“故意违规应失败”的验证。
6. PostgreSQL 集成环境真实启动、连通、执行基础 migration 并验证清理隔离；不得以 SQLite 或永久 skip 代替。
7. 当前阶段要求的 CI jobs 全部实际运行通过；未来阶段 jobs 明确尚未启用，不伪装成能力已验证。
8. M0 Gate 有版本绑定的证据，V2-005 开始条件依赖该 Gate。
9. 本报告所列后续问题有责任任务与最晚关闭点，不因为 P0 CI 绿色被自动视为关闭。

P0 绿色意味着“当前仓库治理与执行防线成立”。它不意味着 Canon 正确、Provider 已支持、Genre 已认证或商业生产已就绪。

### 12.2 后续几个关键阶段的关闭底线

| 关闭点 | 最小硬条件 |
|---|---|
| M1 / Narrative | 核心正例可表示；类型错误被拒绝；Unknown 不等于无变化；双 Genre 无须改 Core 语义 |
| M2 / Canon | 单一提交入口；初始化、事务、CAS、幂等、作用域、重建、wrong hash/permit 拒绝均有真实 PostgreSQL 证据 |
| M3 / Genre | 两套已实现 Pack 与 registry；相同核心运行；非法扩展阻断；合法域内行为通过 |
| M4 / 单章 E2E | P7 所需门禁集成后才能宣告关闭；真实 Provider 正文绑定完整评审与提交；失败不推进 Canon |
| M5 / Repair | 新候选版本、重抽取、重新验收、旧 Permit 失效、回归检测与有限循环 |
| M6 / 10 章 | 双 Genre、恢复测试、真实证据链、人工阅读、错误检测的误杀/漏检记录 |
| M7 / 30 章 | 双 Genre 连续运行、故障注入、版本固定、正文和状态共同验证；如靠人工介入，次数与内容完全记录 |

## 13. 应避免的整改误区

1. **不要用更多总体文档代替修订。** 把冲突直接勘误到原规范、执行文档和任务映射中。
2. **不要为“规范完整”提前实现所有实体与扩展。** 当前任务需要的最小可执行类型优先，长期愿景保留注册位置即可。
3. **不要用 Schema 承担全部业务真值。** Schema、领域验证、数据库约束、语义审查各司其职，但每条 invariant 必须有明确执行点。
4. **不要用更多 Reviewer 解决所有问题。** 先验证输入覆盖、身份、作用域、状态转移和权限；模型共识仍可能共同漏检。
5. **不要让认证模式关闭硬约束。** 允许尚未认证的 Pack 参与认证，与允许绕过 Canon/Genre 安全规则完全是两回事。
6. **不要把故障被正确拦截算成系统失败。** 同时记录被拦错误与漏入已接受正文的错误，保留所有尝试。
7. **不要因 P11 才做 Learning 就延后阅读正文。** 早期人工抽检是验收，完整校准与学习系统仍按既定路线实施。
8. **不要因 30 章零事故承诺百万字可靠或商业成功。** 认证结论绑定实际运行条件与适用范围。

## 14. 最终审核意见

这套资料已经完成了重要的方向选择：用统一、受约束、可恢复的生产内核承载中文网文创作，再让复杂智能在其上增长。相比 V1，最值得保留的改进是明确 Canon 权威、题材执行边界、不可绕过的提交条件与阶段性认证。

当前最需要补的不是领域数量，而是四类工程事实：**同一术语只表达一种含义；合法对象可以被表示；非法放行能被阻止；任务完成有可核验证据。**

因此建议：

> 按用户冻结路线进入 P0，把本报告列出的近期问题写入 V2-001～004 的执行与验收；P0 真正绿色后进入 V2-005。各阶段只在其到期问题关闭、相应测试和实际证据齐备后晋级。

本报告未修改任何原始规范，未提前实施 V2 业务内核，也未替任何任务或 Genre 颁发完成/认证状态。

## 附录 A：探针结果速查

| 探针 | 场景 | 当前 Schema | 应有契约行为 |
|---|---|---|---|
| CONTROL-01 | 随包都市 DRAFT 示例 | 接受 | 接受其结构，不代表认证通过 |
| CONTROL-02 | hard rule 的 on_violation=ignore | 拒绝 | 拒绝 |
| CONTROL-03 | 仅基础字段的 Character | 接受 | 接受最小实体 |
| PROBE-01 | Character 增加已声明 identity | 拒绝 | 应可表示 |
| PROBE-02 | Character 使用 Location 类型和“受伤”lifecycle | 接受 | 应被类型/领域拒绝 |
| PROBE-03 | SET_FACT 缺 path/value/evidence | 接受 | 应被操作契约拒绝 |
| PROBE-04 | ChangeSet 含未注册 op 与空 validation_summary | 接受 | 应被 registry/验证拒绝 |
| PROBE-05 | ALLOW 无验证引用与完整签发信息 | 接受 | 不可作为有效 Permit 使用 |
| PROBE-06 | 所有质量层为空但 PASS | 接受 | 未完成 required checks 时不可放行 |
| PROBE-07 | 已确认 Q0 HARD_FAIL 与 PASS 同时出现 | 接受 | 聚合/提交政策必须拒绝 |
| PROBE-08 | C6 PASS 无指标、无 case | 接受 | 不可视为有效认证 |
| PROBE-09 | CLOSED 无测试与验收证据 | 接受 | Closure 工具必须拒绝 |
| PROBE-10 | SceneContract 增加 genre_pack_hash | 拒绝 | 直接字段或正式间接绑定必须可表示 |
| PROBE-11 | ContextItem 无 project/branch | 接受 | 项目私有 item 必须有可信作用域；全局 item 显式区分 |
| PROBE-12 | Provider FAILED 无 response_hash | 拒绝 | 应能表示未获得响应的失败 |

## 附录 B：复核与交付物

在项目根目录运行：

```bash
python3 architecture-review-2026-09-18/audit_specs.py
```

该脚本只读取 `gptdoc/`，将审计结果写入报告目录，不调用 Provider，不写原始规范。脚本退出成功表示审计执行完成，不表示规划没有问题；具体缺口见 `probe_contract_mismatches` 与探针明细。

- [完整机械检查结果][audit-results]
- [可复现审计脚本][audit-script]
- [整改登记表][findings]


[constitution-milestones]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Project_Constitution_v1.0/PROJECT_CONSTITUTION.md:748
[constitution-evidence]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Project_Constitution_v1.0/PROJECT_CONSTITUTION.md:619
[milestones]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Implementation_Plan_v1.0/milestone-plan.yaml:1
[quality-evidence]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Quality_Evaluation_Repair_Spec_v1.0/QUALITY_EVALUATION_REPAIR_SPEC.md:371
[character-schema]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Narrative_Domain_Spec_v1.0/character.schema.json:5
[entity-schema]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Narrative_Domain_Spec_v1.0/narrative-entity.schema.json:68
[delta-schema]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Narrative_Domain_Spec_v1.0/narrative-delta.schema.json:1
[changeset-schema]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Canonical_State_Spec_v1.0/change-set.schema.json:1
[permit-schema]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Canonical_State_Spec_v1.0/commit-permit.schema.json:1
[quality-report-schema]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Quality_Evaluation_Repair_Spec_v1.0/quality-report.schema.json:1
[implementation-task-template]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Implementation_Plan_v1.0/IMPLEMENTATION_PLAN.md:1057
[backlog]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Implementation_Plan_v1.0/implementation-backlog.yaml:1
[canon-genesis]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Canonical_State_Spec_v1.0/CANONICAL_STATE_SPEC.md:964
[backlog-genesis]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Implementation_Plan_v1.0/implementation-backlog.yaml:864
[canon-transaction]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Canonical_State_Spec_v1.0/CANONICAL_STATE_SPEC.md:240
[canon-atomicity]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Canonical_State_Spec_v1.0/CANONICAL_STATE_SPEC.md:547
[scene-schema]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Planning_Contract_Spec_v1.0/scene-contract.schema.json:1
[context-item-schema]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Context_Intelligence_Spec_v1.0/context-item.schema.json:1
[model-run-schema]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Production_Workflow_Spec_v1.0/model-run.schema.json:1
[urban-example]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Genre_Intelligence_Spec_v1.0/example-urban-business-realistic.genre-pack.yaml:1
[genre-certification]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Genre_Intelligence_Spec_v1.0/GENRE_INTELLIGENCE_SPEC.md:1075
[cert-schema]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Genre_Intelligence_Spec_v1.0/genre-certification.schema.json:1
[ci-gates]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Implementation_Plan_v1.0/ci-gates.yaml:1
[reference-sources]: /Users/angyang/Documents/AI/ANovelOS/gptdoc/ANovel_V2_Reference_Architecture_Study_v1.0/source-registry.yaml:1
[audit-results]: /Users/angyang/Documents/AI/ANovelOS/architecture-review-2026-09-18/audit-results.json
[audit-script]: /Users/angyang/Documents/AI/ANovelOS/architecture-review-2026-09-18/audit_specs.py
[findings]: /Users/angyang/Documents/AI/ANovelOS/architecture-review-2026-09-18/REMEDIATION_REGISTER.yaml
