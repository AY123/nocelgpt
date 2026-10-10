# V2-005 独立契约审核清单

审核日期：2026-10-03（Asia/Shanghai）  
声明审核基线：dev_cc @ `58d77d2673d07950d0a235d2b25bf7e1e17cb274`  
修订前基线：`323eaae71a94ff882569939fd70ee11b7e19597b`  
被审主契约版本：1.1.0  
审核结果：**NEEDS_REVISION，暂不具备契约冻结和进入实施的条件。**

本次结论来自上传文件的全文核验，不再是摘要预审。主要原因是修订未贯穿全部正文、示例和执行步骤；另有输入校验、归一化、存储表示和测试预期的具体矛盾。设计方向可以保留，需集中修订这些契约问题。

## 审核范围与证据边界

读取九份核心文档、三份治理文件，以及审核包额外包含的两份补充清单。核心九份文档实际共 **6,284 行**；其中 REVISION_EVIDENCE 实际为 **249 行**。文件名、行数、SHA-256 见附录。

审核对象是上传包内字节。包内没有 Git 对象数据库；远端未读取，本报告不独立证明这些字节与 Git 提交逐文件一致。修订前基线与审核提交是不同角色，文档保留旧基线本身不是缺陷。

审核包 SHA-256：
`732a967a5b52a2e68d69bc3795187a3199c51a288ad736e23f5ee99dcb6d90b6`

实测采用 Python 3.12.14，直接提取文档代码块执行；这些是文档示例复现，不是项目实现测试。没有执行 AT-V2-005、CI、生产数据库或 Provider 调用。当前环境没有 jsonschema，Schema 结论来自其原文约束的静态核对，未声称执行过完整 JSON Schema 验证器。

审核包没有提供 implementation-backlog.yaml、AI_EXECUTION_PROTOCOL.md、02_ARCHITECTURE_BASELINE.md、源代码或锁文件。因此，上游任务关闭、完整机器门禁、现有依赖和代码冲突等报告自述不升级为本次独立核验事实。已有文档矛盾足以形成当前审核结论。

## 八项检查结论

| 检查项 | 结论 | 依据 |
|---|---|---|
| 上位身份语义 | 设计方向符合，交付物尚未一致落实 | 03_DOMAIN §1 要求名字不作主键、作用域与显式歧义；当前选择符合方向 |
| 校验入口 | 需修订 | CR-003、CR-004 |
| 操作前后条件 | 需修订 | CR-006、CR-008、CR-009、CR-010、CR-011 |
| 项目隔离 | 查询设计已覆盖，注册示例存在反例 | CR-005 |
| 序列化 | 表示尚未冻结，确定性口径不一致 | CR-008、CR-012 |
| 测试映射 | 存在相反预期、无有效调用入口的用例和遗漏的执行步骤 | CR-006、CR-009、CR-013 |
| 文档一致性 | 未通过 | CR-001、CR-002 及其他交叉引用问题 |
| ADR 判断依据 | 引用不准确；本审核没有依据要求新建 ADR | CR-014 |

## 原五项待核实问题的最终判定

| 待核实项 | 原文已覆盖部分 | 真正需要修订的部分 |
|---|---|---|
| ProjectId 校验行为 | 主契约 §2.2 的代码已明确先 strip，再检查剩余字符；反序列化必须校验也已写出 | 跨文档代码不同、非字符串异常不符、调用方信任与“所有操作必须校验”矛盾，见 CR-003 |
| EntityId 规范 | §2.1 已明确小写、36 字符、带连字符、v4 和 variant；不必重新发明大写接受策略 | 实际验证函数可接受尾随换行，入口与 Schema 未落实，另有旧 ULID 决策，见 CR-002、CR-004 |
| candidates JSON 顺序 | §10.1、§10.3 已明确领域结果为无序集合、按值比较 | 当前 §9 只定义身份 JSON，并未定义结果 JSON；不能据此强制新增结果序列化功能。真正冲突是“字节一致”与集合相等混用，见 CR-012 |
| 注册表作用域 | §4.1 明确 ID 在同一 registry 内唯一；多项目索引和修订报告说明支持多项目容器 | 不必再预设单项目注册表或新增授权参数；应统一注册示例，并明确测试快照更新边界，见 CR-005、CR-011 |
| ADR 理由 | decision-register 中没有以 V2-005 为 related_task 或 due_task 的 ADR；治理 §5 允许授权范围内局部细化 | 文档引用了不存在的三条件规则和不存在的 V2-005 条目，见 CR-014 |

**不以新增 15 个测试或达到 66 个为审核门槛。** 先修订行为，再复用、扩展或参数化现有用例。51 个编号代表测试规格，不代表 51 个测试已实现或已通过。

## 正式问题清单

共 **15 项：HIGH 8 项、MEDIUM 6 项、LOW 1 项**。严重性表示对契约实施的影响，不是对尚未编写的生产代码定级。

### CR-001 — 冻结、审批与实施授权声明仍相互矛盾

- **问题_ID**：CR-001
- **描述**：标题和部分新增段落为待审核，正文仍声称契约冻结、审批完成、可以立即实施。
- **位置**：DECISION_GATES：Gate 3 第77行、第104行；Gate 4 第112行、第148行；Final Certification 第420行、第446行；Approval Checklist 第483行；Authorization 第500行。REFINEMENT_SUMMARY 第28行、第146行、第373行。IMPLEMENTATION_CONTRACT 第1553行。
- **证据**：同一决策门文件同时出现 `Contract Frozen: YES`、`BLOCKED_ON_CONTRACT_REVIEW`、`Implementation Authorization: READY`；审批清单把主契约和测试矩阵“reviewed and approved”勾为完成。主契约页尾仍写 `CONTRACT FROZEN`。这些正文没有被标成历史快照。
- **影响**：**HIGH**。下一个执行者可以从不同段落得到相反开工条件；修订证据的“状态已全部修正”不能成立。
- **最小修改要求**：统一所有现行状态、门禁、结论和审批清单。待审核事项取消完成勾选；旧状态只放在明确标注的历史区。保留 CURRENT_STATE_AUDIT 历史身份，不为同步状态而改写原始审计。
- **复核标准**：任意现行入口均得到 REVIEW_PENDING / BLOCKED；历史引文中的 FROZEN 可以保留，不能使用全局删词代替语义核查。

### CR-002 — UUID v4 决策未同步至细化、计划和示例

- **问题_ID**：CR-002
- **描述**：主契约改成 UUID v4 only，其他实施输入仍明确采用 ULID 或运行时回退。
- **位置**：IMPLEMENTATION_CONTRACT §2.1 第37行、§3.1 第294行、§9.1 第846行、§13.1 第1218行；TASK_REFINEMENT §13 R-5 第951行、§15 D-4 第1055行；IMPLEMENTATION_PLAN Step 3 第149行、第198行、R1 第670行；DECISION_GATES 第99行、第128行；REFINEMENT_SUMMARY D-4 第172行。
- **证据**：计划的动作要求 `Try ULID first`、`Fallback to UUID`；同一 Step 3 的代码又是 uuid4。JSON 示例仍使用 `01HQ...` 样式 ID，Schema 描述仍写 `ULID format`。
- **影响**：**HIGH**。按不同实施输入可得到不同 ID 格式，违背已选定的修订方向。
- **最小修改要求**：将所有现行选择、生成动作、风险措施、示例和 Schema 描述统一为 UUID v4；删除可选 ULID 依赖与双路径测试要求。历史“修订前 ULID”引文保留。
- **复核标准**：生成步骤唯一指向 uuid4；所有有效样本符合主契约格式；用现有创建/ID 用例验证格式，而不是只看 1000 次生成无碰撞。

### CR-003 — ProjectId 校验职责冲突，修订报告代码不可运行

- **问题_ID**：CR-003
- **描述**：主契约已有清理语义，但校验职责与公共前置条件相冲突；修订报告给出了不同且会抛 TypeError 的函数。
- **位置**：IMPLEMENTATION_CONTRACT §2.2 第85行、第105行、第111行、第118行、第120行；§3.1 第277行、第291行；§5.1 第662行。CONTRACT_REVISION_REPORT 修订3 第148行。IMPLEMENTATION_PLAN Step 5 第311行。
- **证据**：§2.2 让调用者校验、registry 不再校验；§5.1 又要求“所有操作 MUST validate IDs”。计划 create_identity 示例只校验名字，直接保存 project_id。主契约函数对 `123` 实测抛 AttributeError；报告的 `any(c in s for c in range(0x00, 0x20))` 对正常 `proj_a` 实测抛 TypeError，因为 c 为整数。
- **影响**：**HIGH**。按现有计划可以构造带空项目 ID 的实体；“新增函数”尚不能证明 runtime 安全已建立。
- **最小修改要求**：只保留一份可执行校验定义；明确首尾空白和控制字符的处理对象。统一字符串类型错误语义、清理后的项目键和实际调用入口。可采用构造校验或受控工厂边界，内部信任已验证对象；不能同时保留“所有操作校验”和“NewType 输入无需校验”两个口径。明确解析传入非法 project_id 的结果或异常，与 §5/§8 一致。
- **复核标准**：合法 ID、首尾空白、内部控制字符、空白 ID、非字符串输入及绕过 NewType 路径都有可达入口和明确断言。无需按这些输入机械新增五个独立函数。

### CR-004 — EntityId 验证入口与 Schema 未落实，正则接受尾随换行

- **问题_ID**：CR-004
- **描述**：格式已明确，但实际验证谓词不足，且未规定其在重建身份时的强制执行位置。
- **位置**：IMPLEMENTATION_CONTRACT §2.1 第42行、第53行、第57行；§2.3 第139行；§5.1 第665行；§9.2 第867行；§13.1 第1217行。CLARIFICATION_CHECKLIST 第164行。
- **证据**：`ENTITY_ID_PATTERN.match(valid_uuid + "\n")` 实测返回 True，虽然字符串长度为37、末尾不是 UUID 字符。EntityId 为 NewType，`EntityId("bad")` 实际仍得到 `"bad"`。Schema 的 ID 只有 string/minLength 1，没有版本和规范形式约束；主契约没有描述反序列化如何强制调用验证。补充清单建议仍使用相同 match 写法，不能直接采纳为最终方案。
- **影响**：**HIGH**。无效身份可被当成有效对象，或以非规范字符串参与唯一性比较。
- **最小修改要求**：使用完整字符串匹配或等价严格验证；明确生成、构造/重建、注册之间的验证边界。同步 Schema 的 UUID 约束，或清楚界定结构校验与强制语义校验两个层次。现有小写带连字符策略可以直接保留并拒绝大写，无须为了修复而引入多格式规范化。唯一性比较只能消费规范 ID。
- **复核标准**：有效 v4 通过；尾随换行、非 v4、非法 variant、非 UUID 与非规范形式按同一策略处理。TC-005-031 应含非法数据拒绝断言，不能只有正例。
- **附带修正**：§3.1 的“never previously issued”应说明是 UUID v4 的概率性生成加 registry 查重，而不是未实现的跨进程全局历史去重保证。TC-005-033 的1000次抽样不能证明绝对永不碰撞。

### CR-005 — 注册表示例会静默覆盖并导致跨项目结果

- **问题_ID**：CR-005
- **描述**：§4.1 已有正确的幂等/冲突规则，但 §14.2 和计划 Step 4 仍直接覆盖字典，项目索引因此失配。
- **位置**：IMPLEMENTATION_CONTRACT §4.1 第604行、第608行、第617行；§14.2 第1283行、第1284行、第1291行。IMPLEMENTATION_PLAN Step 4 第239行、第240行、第249行。
- **证据**：§4.1 要求同 ID 不同内容抛 ValueError；建议代码却执行 `self._entities[entity.entity_id] = entity`。直接提取该代码，先注册 `(id=X, project=proj_a, name=甲)`，再注册 `(id=X, project=proj_b, name=乙)`，随后 `get_entities("proj_a")` 返回 project_id 为 proj_b 的实体。结合计划 Step 7 的原始解析代码，`resolve_alias("proj_a", "乙", registry)` 实测得到 RESOLVED，所指实体属于 proj_b。
- **影响**：**HIGH**。文档建议实现违反自身隔离保证；这是可复现的示例缺陷，不是已发生的生产泄漏。
- **最小修改要求**：保留 §4.1 的查重规则，同步所有建议代码和实施动作；冲突失败时不能修改任一索引。写明唯一性保证覆盖同一 registry 实例，不声称对多个无共享存储实例执行了全局查重。
- **复核标准**：TC-005-046 验证相同值重放不变；TC-005-047 可参数化同项目/跨项目的同 ID 不同内容，并断言失败后全部可观察查询结果不变。

### CR-006 — 别名冲突的负向场景与主契约相反

- **问题_ID**：CR-006
- **描述**：主契约允许跨实体同别名；细化和测试却要求添加同别名时报错或警告。
- **位置**：IMPLEMENTATION_CONTRACT §3.3 第382行、§3.5 第473行、§4.1 第613行；TASK_REFINEMENT §3.2 第102行、NS-5 第731行；TEST_CONTRACT_MATRIX TC-005-038 第53行、NS-5 映射第159行。
- **证据**：细化写 add_alias 前提是“alias not ambiguous in project”，NS-5 要求 `raise ConflictError`；TC-005-038 预期 `Error or warning`。主契约明确不在操作层检查跨实体冲突，解析时统一返回 AMBIGUOUS。
- **影响**：**HIGH**。执行者无法同时满足规范性操作和测试预期，可能为通过测试偷偷加入另一套别名唯一性规则。
- **最小修改要求**：采用已选定的允许同别名策略；将 NS-5/TC-005-038 改成“两个实体的别名都保留、添加不覆盖、查询返回包含两者的 AMBIGUOUS”。删除未定义的 ConflictError 和警告要求。
- **复核标准**：既有同别名歧义用例与防覆盖用例得到一致结果；不依赖执行顺序，不删除或转移原实体的别名。

### CR-007 — 全角空格的规则、示例、代码和测试不一致

- **问题_ID**：CR-007
- **描述**：正文要求空白折叠，示例和测试要求删除内部全角空格，而建议代码实际折叠成 ASCII 空格。
- **位置**：IMPLEMENTATION_CONTRACT §3.6 第540行、第551行；TASK_REFINEMENT §8.2 第525行、§8.3 第555行；IMPLEMENTATION_PLAN Step 3 第183行、第189行；TEST_CONTRACT_MATRIX TC-005-026 第41行。
- **证据**：文档要求 `normalize_for_lookup("李　明") == "李明"`；实际提取计划函数执行，结果为 `"李 明"`。计划 docstring 的 `"张　三" -> "张三"` 同样与函数执行结果 `"张 三"` 不符。
- **影响**：**HIGH**。名称是否相等直接影响解析、去重和歧义，当前无法唯一决定结果。
- **最小修改要求**：明确 U+0020、U+3000 及其他被处理空白在首尾/内部的变换；选择折叠或删除的单一规则，同步示例、代码与 TC-005-026。不要为纠正这个局部冲突引入 NFKC 或拼音处理。
- **复核标准**：测试同时覆盖内部单个全角空格、连续空白、首尾空白和归一化空值。中文与 ASCII 混合串的处理应明确；当前 `isascii()` 分支本身已经定义为整串条件，不能未经决定就改为逐字符 lowercase。

### CR-008 — 身份存储表示仍交给实现选择，与闭合 Schema 冲突

- **问题_ID**：CR-008
- **描述**：契约尚未冻结保存原文、归一化文本或二者的具体表示；建议的双字段编码不符合其自己的 Schema 和数据类型。
- **位置**：IMPLEMENTATION_CONTRACT §2.3 第141行、第142行；§3.1 第285行；§3.3 第374行；§9.1 第849行；§9.4 第888行、第893行、第895行、第903行；§13.1 第1233行、第1245行。TASK_REFINEMENT §8.3 第545行；IMPLEMENTATION_PLAN Step 5 第317行、Step 6 第417行。
- **证据**：§9.4 说推荐 BOTH，并展示 `canonical_name_normalized` 与对象数组 aliases；但 §13.1 的 aliases item 必须是字符串、additionalProperties 为 false，因此这些编码按原文约束应被拒绝。§9.4 最后又写“implementation chooses”。操作条款要求 normalized storage，计划却仅 strip，保留 ASCII 大小写及内部空白；细化还要求 raw_alias 和 lookup_key 两份值。
- **影响**：**HIGH**。两个实现可使用不同字段、不同展示名和不同去重含义，却都认为遵循契约。单纯往返成功不能证明它们兼容。
- **最小修改要求**：冻结一个 EntityIdentity 内存表示和一个 JSON 表示，明确名称保存规则与 lookup key 的计算位置。最小方案可以保持 string/frozenset[str] 并在解析时计算 key，不强制新增字段或 Alias 类型。只保留被采纳的 JSON 示例；明确 aliases/entity_type 缺省值和重建规则。
- **复核标准**：具体有效实体可以按唯一格式往返，符合被采纳 Schema；名称大小写、空白和 Unicode 的保存/比较断言一致。

### CR-009 — 不可变性输入测试没有绑定真实构造入口

- **问题_ID**：CR-009
- **描述**：TC-005-050 要求接受输入 list 并隔离修改，但公共操作没有 aliases 集合参数，公共 dataclass 也没有转换或拒绝规则。
- **位置**：IMPLEMENTATION_CONTRACT §2.3 第135行、第142行、第174行；§3.1 第268行；§3.3 第360行；CONTRACT_REVISION_REPORT 修订8 第375行；TEST_CONTRACT_MATRIX TC-005-050 第72行、第292行。
- **证据**：create_identity 只接 project_id/name/type，add_alias 接单个 str；报告却说两者接受可变集合。按公开 dataclass 示例传入 list，再在外部 append，实体 aliases 实际同步改变。这个调用违反类型提示，但类型提示和 frozen=True 不会在运行时自动拒绝或复制它。
- **影响**：**MEDIUM**。在正确的 frozenset[str] 输入下设计安全，但“所有公开构造都隔离可变输入”的保证和测试尚不可执行。
- **最小修改要求**：明确可变集合进入系统的真实位置：直接构造、重建或内部转换。选择转为 frozenset，或明确拒绝不符合字段类型的输入。将 TC-005-050 改为真实入口与明确预期，不增加一个与用途无关的批量别名 API。已是 frozenset[str] 时允许安全复用。
- **复核标准**：变更外部有效输入不会变更实体；非法输入按契约拒绝；不能只断言 dataclass_params.frozen 就声称验证了集合隔离。

### CR-010 — canonical_name 是否可出现在 aliases 中有相反规定

- **问题_ID**：CR-010
- **描述**：同一类型的字段语义禁止 aliases 包含 canonical_name，不变量却允许，改名实现也可能生成这种对象。
- **位置**：IMPLEMENTATION_CONTRACT §2.3 第155行、第169行；§3.2 第319行、第320行；§3.4 第404行、第410行；§14.3 第1313行。IMPLEMENTATION_PLAN Step 6 第443行、第444行。TEST_CONTRACT_MATRIX TC-005-039 第61行。
- **证据**：原文同时写 `Does NOT include canonical_name` 与 `canonical_name MAY exist as alias`。按改名示例 A→B→A，最终 aliases 包含 A；同名改名也会把当前名字加入 aliases。此外 remove_alias 的“归一化后移除”与计划仅 strip 后按原字符串移除，需要与 CR-008 的存储选择统一。
- **影响**：**MEDIUM**。实体有效性、同名改名、返回原名和删除别名可能出现不同实现。
- **最小修改要求**：统一是否允许 canonical_name 与 aliases 重叠，定义同名改名及 A→B→A 的结果；明确 remove_alias 按保存文本还是 lookup key 定位，以及 canonical-name 保护的比较规则。不要改变身份 ID。
- **复核标准**：扩展既有改名/移除用例即可；检查 project_id、entity_id 不变，并检查同名改名和循环改名的完整 aliases 集合。

### CR-011 — 注册表“测试快照”与改名后的解析流程未衔接

- **问题_ID**：CR-011
- **描述**：registry 不提供 update/remove；add_entity 又拒绝同 ID 不同内容。改名后的当前状态如何进入解析测试仍要求操作私有字段或采用未提供的删除操作。
- **位置**：IMPLEMENTATION_CONTRACT §4.1 第609行、§4.2 第639行、第644行、第645行、第649行；TASK_REFINEMENT AC-005-03 第379行；TEST_CONTRACT_MATRIX TC-005-037 第52行、TC-005-041 第63行；CONTRACT_REVISION_REPORT 第432行。
- **证据**：§4.2 建议 `_entities[id] = new_entity` 或 remove+add，但没有公开 remove；直接覆盖还可能破坏项目索引。细化的验收示例则像是 rename 后解析会自动读取新状态，没有显式快照装载。
- **影响**：**MEDIUM**。测试和下游可能误以为纯函数已经写入 registry，或依赖未受契约保护的私有修改。
- **最小修改要求**：将 registry 明确为多项目测试容器/快照，注明同一实例内 ID 唯一。最小可行做法是用改名后的实体集合重建新 registry，并让验收样例使用该快照；无需引入生产更新、事务或授权。若保留测试辅助更新，需规定项目归属不变及索引一致性，但不能把它描述为正式 Canon 写入。
- **复核标准**：改名前后的解析使用清楚的状态；改名失败原对象、原快照不变。纯函数传入对象没有 caller project 参数，因此不能无依据要求新增“调用者跨项目修改拒绝”授权功能；它必须保留输入对象的 project_id，既有稳定性断言可扩展验证。

### CR-012 — 领域值相等与字节一致混用，结果 JSON 范围需声明

- **问题_ID**：CR-012
- **描述**：修订后的确定性定义正确使用集合值相等，但其他现行条款仍要求 bitwise/byte-identical。
- **位置**：IMPLEMENTATION_CONTRACT §3.5 第517行、§9.3 第881行、§10.1 第930行、第934行、§10.3 第967行；TASK_REFINEMENT AC-005-10 第502行；TEST_CONTRACT_MATRIX TC-005-027 第42行、INV-005-05 第172行。
- **证据**：§10.1 明确不要求对象身份，并用 frozenset equality；细化却说 `Must be byte-identical`。`identity == restored` 是值比较，不是字节比较。§9 只有 EntityIdentity 编码，没有 ResolutionResult 编码或 candidates 数组协议。
- **影响**：**MEDIUM**。实现者可能为领域集合强加顺序，或把未定义的字节输出当作已完成保证。
- **最小修改要求**：将领域确定性统一为相同输入与实体集合产生相同结果值。明确 V2-005 是否序列化 ResolutionResult：若不需要，直接标为不承诺结果 JSON；若纳入本轮，定义各变体编码及候选数组稳定顺序/集合恢复语义。排序仅用于输出，不用于选择第一个候选。不要因此提前实现 P2 的结构化哈希规范。
- **复核标准**：TC-005-043/028 验证集合值相等；只有实际采纳结果序列化功能时才增加该路径的断言。无序 frozenset 本身不是缺陷，也无需改成领域列表。

### CR-013 — 公共接口、验收编号和实施步骤未绑定同一契约

- **问题_ID**：CR-013
- **描述**：细化样例使用不同调用模型，计划遗漏新增校验及身份编解码步骤，测试完成口径不一致。
- **位置**：TASK_REFINEMENT §3.2 第90行、第108行；§3.3 AC-005-03 第138行与 §7 AC-005-03 第369行；§7 第362行、第387行、第348行；§11.2 第785行、§11.3 第802行。IMPLEMENTATION_CONTRACT §3.2 第305行、§3.5 第427行、§11.1 第1082行、§17 第1457行。IMPLEMENTATION_PLAN Step 8 第588行、第615行。TEST_CONTRACT_MATRIX 第189行、第196行、第206行、第365行。
- **证据**：主契约 rename/add/remove 接 EntityIdentity，resolve 显式接 registry；细化传 entity_id、忽略返回的新对象、解析不传 registry。细化要求 Alias 类和 entity.schema.json，主契约没有 Alias 公共类且使用 entity-identity.schema.json。同一 AC-005-03 在两节分别表示“歧义”与“旧名别名”。矩阵退出要求51例，计划明确只确保001–038，主契约完成清单仍为25+。身份 serialize_to_json/deserialize_from_json 只出现在示例，没有签名/负责位置及实施动作。pytest node ID 的 `::test_*` 写法不能作为可靠筛选方式。
- **影响**：**MEDIUM**。执行者可能实现额外类型、遗漏后13例、把纯函数当成更新命令，或缺少有效的序列化入口。
- **最小修改要求**：以主契约最终接口为唯一执行输入，其他文档引用或给出同签名样例；明确 Alias 是 string 概念还是实际类型；统一 Schema 路径。区分上游验收条目与本地扩展 AC 编号，保持稳定映射。计划覆盖最终全部有效 TC ID，并加入校验和身份编解码的实现/验证动作；不预设测试数量。将筛选命令改为可执行的 `pytest <文件> -k '<表达式>'` 或完整 node ID。
- **复核标准**：每个 TC 有明确输入入口、确定预期和相应步骤；001–051 中有效用例都在执行表内。修订 TC-038/050 等现有用例后再计算最终数量。新增/修订规格仍不能写成已执行 PASS。

### CR-014 — ADR 分析引用了治理原文不存在的规则和条目

- **问题_ID**：CR-014
- **描述**：文档将通用判断框架写成治理强制条款，且引述了 decision-register 内不存在的 V2-005 required_decisions 条目。
- **位置**：CONTRACT_REVISION_REPORT ADR 必要性判断第495行、第497行、第529行；DECISION_GATES Gate 5 第160行、第166行、第182行；REVISION_EVIDENCE 第112行、第127行；TASK_REFINEMENT §5.2 第226行；CLARIFICATION_CHECKLIST 第351行、第359行。治理 00_GOVERNANCE §5 第58行、第60行；decision-register 全文。
- **证据**：治理 §5 没有“跨阶段影响/难逆转/重大权衡，任一满足就必须 ADR”这三项规则，也没有“标准技术选择即可豁免”的条款。decision-register 是 ADR 条目列表，没有被引用的 V2-005 task_id/required_decisions 结构。现有 ADR 的 related_tasks 与 due_task 中没有 V2-005；这与“存在一条显式豁免”是不同事实。下游依赖也使“没有跨阶段影响”不准确。
- **影响**：**MEDIUM**。ADR 结论可能合理，但当前论证使用了未提供的权威，无法作为冻结证据。
- **最小修改要求**：准确引用 §5 允许授权范围内局部细化的规则，以及当前 ADR 列表未登记 V2-005 依赖的事实。承认身份会被后续阶段消费，记录局部选择及其影响。如果 required_decisions 实际在 backlog 中，改为引用那个真实文件，不继续归到 decision-register。不要创造“触发后豁免”规则。
- **复核标准**：每个治理引用都能在实际原文定位。本审核没有依据要求新增 ADR；如另有真实规则约束则按该规则核对。此前摘要审查对 ADR 可能性的通用推测不能替代这次原文结论。

### CR-015 — 审核清单、行数和修订完成证据未与实际包绑定

- **问题_ID**：CR-015
- **描述**：打包清单和“Final Evidence”仍有近似或过期统计，报告中的完成宣称与正文核验结果不符。
- **位置**：AUDIT_MATERIALS_CHECKLIST 第25行、第27行、第45行；REVISION_EVIDENCE 第15行、第24行、第41行、第228行；CONTRACT_REVISION_REPORT 第575行、第591行、第597行。
- **证据**：清单写证据180行、核心6215行；实际为249行、6284行。包有14个正文文件，比所列12个多两份补充清单。Final Evidence 写8份/约5878行，与九份核心文件不一致。修订报告末尾仍是更新进行中，Final Evidence 却声明10/10完成，其中状态与 UUID 同步已被本审核反证。包没有逐文件 Git blob 绑定；仅凭清单所写 SHA 不能证明来源一致。
- **影响**：**LOW**（统计与来源绑定）；相关冻结/完整修订的错误宣称按 CR-001/002 处理，不能因这里为 LOW 就忽略。
- **最小修改要求**：最后重新生成文件清单、精确行数和每文件 hash；区分审核提交、修订前基线和后续补充材料。修订证据按“已完成且核验/部分完成/待处理”记录实际结果；原报告若保留为阶段历史需标清身份。可记录源路径及导出提交，不为修正文案改写 Git 历史。
- **复核标准**：新包目录、manifest 和报告统计一致；每个完成项可追踪到修订条款、测试规格或实际执行证据。

## 已覆盖、无需重做的内容

- 主契约 §3.5 的统一候选集、规范名无优先级、按 entity_id 去重已经明确。TC-005-022、044 支持这些要求。
- §4.1 已明确相同 ID/相同内容幂等，不同内容拒绝；问题在其他示例没有同步，不需要另选重复注册策略。
- §3.2 明确 rename 的 entity_id 与 project_id 不变及失败不改变原对象；这些条款可保留，补充有明确状态装载的验证。
- §10.1 与 §10.4 已将解析值确定性和 UUID 生成随机性分开；保留这份定义并清理其他现行段落。
- frozen dataclass 与 frozenset[str] 对有效不可变输入是合适设计；安全复用 frozenset 不需要强制重复复制。
- 持久化、授权、复杂 NLP、Genre 字段均可以继续留在后续任务。当前问题不要求扩大范围。

## 集中修订与复核顺序

1. **先修主契约**：明确 ID 验证边界、存储表示、归一化、别名规则、registry 快照职责、错误与确定性口径。保留已选定的 UUID v4/同名允许/无优先级。
2. **同步执行材料**：细化、计划、Schema 示例、决策门和摘要引用同一接口与行为；撤回全部现行冻结/通过声明，历史引用保持可识别。
3. **修正矩阵**：优先修 TC-005-038、026、050；扩展046/047的状态与项目断言，补齐实际缺少的 ID/项目拒绝场景及序列化断言。无需按清单数量机械加测试。
4. **纠正治理论证**：使用真实的 §5 和 ADR 注册事实；不为凑放行条件创建多余 ADR。
5. **生成新审核包**：每项 CR 标记处理位置和处理方式；导出完整文件并记录来源。未执行的测试仍是规格，不写 PASS。
6. **复核**：对15项给出 CLOSED、保留风险或不适用的可核查理由，再核对全文没有新的矛盾。仅完整复核通过后讨论冻结与实施授权。

这是现有范围内的文档收敛，不要求增加生产实现、数据库、项目授权系统或额外公共 API。建议复核时集中提交完整修订版，避免继续只提交“全部已修复”的摘要。

## 当前门禁结论

本报告是审核意见，不直接修改仓库机器状态，也不构成实施授权。

```yaml
V2_005_REFINEMENT_STATUS: REVISED
V2_005_CONTRACT_STATUS: INDEPENDENT_REVIEW_PENDING
V2_005_IMPLEMENTATION_AUTH: BLOCKED_ON_CONTRACT_REVIEW
```

本次独立审核已执行，结果为 **需要集中修订并复核**；不应再将阻塞原因写成“审核材料尚未收到”。冻结前首先解决全部 HIGH 与影响契约明确性的 MEDIUM 项；LOW 项随证据刷新处理。

## 附录 A：关键最小复现

| 文档代码/约束 | 输入或步骤 | 实际结果 | 结论 |
|---|---|---|---|
| 主契约 §2.2 | `validate_project_id("\tproj_a\n")` | `"proj_a"` | 当前代码清理首尾空白；需与其余声明一致 |
| 主契约 §2.2 | `validate_project_id(123)` | AttributeError | 与统一校验失败语义不一致 |
| 修订报告“修订3” | `validate_project_id("proj_a")` | TypeError | 示例用整数执行字符串成员检查 |
| 主契约 §2.1 | `is_valid_entity_id(valid_uuid + "\n")` | True | 不符合36字符完整格式 |
| 计划 Step 3 | `normalize_for_lookup("李　明")` | `"李 明"` | 不符合示例及TC-026要求的“李明” |
| 主契约 §14.2 + 计划 Step 7 | 相同ID依次注册到A、B，随后在A查B名字 | RESOLVED，实体project_id为B | 建议注册实现造成索引失配与越项目结果 |
| 主契约公开 EntityIdentity | 将list作为aliases构造，外部再append | 对象的aliases同步改变 | frozen不自动保证不符合类型的输入隔离 |
| 主契约 §13.1，静态核对 | ID为`"bad"`，项目/名字为单空格 | 满足所列string/minLength条件 | 需要明确强制语义验证层 |
| 主契约 §9.4 对照 §13.1，静态核对 | normalized字段、对象型aliases | 新字段违反additionalProperties，别名对象违反string类型 | 推荐编码与Schema相冲突 |

复现没有应用生产补丁，未修改上传材料；没有推送或更改 dev_cc。

## 附录 B：审核输入指纹

以下是正文文件的实测指纹。额外两份清单作为补充材料，不自动视为已证明属于声明提交的原始核心文件。

| 文件 | 行数 | SHA-256 |
|---|---:|---|
| V2-005_IMPLEMENTATION_CONTRACT.md | 1559 | cd0ab7464a6f0414dd0243c1db6d66a16234c73a8a2388ee00dd463bcbb359a2 |
| V2-005_TASK_REFINEMENT.md | 1197 | 8421735348150a49ec44fbeb3ad92232855b3f431271289b018b0a1f9343e743 |
| V2-005_TEST_CONTRACT_MATRIX.md | 396 | cb26650a90e23df90a85c39a95291e8bc2a537db18583485dd0b8073794927c3 |
| V2-005_IMPLEMENTATION_PLAN.md | 744 | 6172ab25a3dc5137a0d17e32fe4862d2efd305a938df0dc1a1f029fbe31e785f |
| V2-005_CONTRACT_REVISION_REPORT.md | 601 | 8fe17721d3a57782733992a9ad4960a8f9592fea10916891954244285c777f3c |
| V2-005_DECISION_GATES.md | 547 | 0657b4b78dcf465d04229d870c99dfcfd610a6e2ea22902620f2f716a4652408 |
| V2-005_REFINEMENT_SUMMARY.md | 466 | dc0cf349bffe82fb5e1db2071d17a0d2e54070dca2b5e1c9dd9ae65ee259ed51 |
| V2-005_CURRENT_STATE_AUDIT.md | 525 | 86286123a330f0cde29e5fa395d36561c942545b4d189c6ad2fd521f3efe9559 |
| V2-005_REVISION_EVIDENCE.md | 249 | 34505a5e2ce71698700fb0c348b4074ab993425ed34c316c65581e344a5d99ea |
| decision-register.yaml | 205 | f7f80f8f20cd3701c87450749db60ded8553c095127fd332cbf172a883c932d1 |
| 00_GOVERNANCE_AND_SOURCE_AUTHORITY.md | 82 | 558fc835e0128f7c2d0af463c869f0569cfa96ed6819a86a97e126c643b14fd2 |
| 03_DOMAIN_CANON_AND_ARTIFACT_CONTRACTS.md | 80 | 5e7dcb3c3cc6a8220171a7b48b9fed718c075611f79ec81e2ef58899ea4e2f75 |
| V2-005_AUDIT_MATERIALS_CHECKLIST.md | 172 | 74d479f41e5cd3ae8d1d2f82581c2c64720961ddd2b1ebab618d03f07d4707ad |
| V2-005_CLARIFICATION_CHECKLIST.md | 435 | 3d4edbb0da5742f951d61956dccb12f2fbb47dfb30d42dfba9241bf428e8a903 |

审核记录结束。
