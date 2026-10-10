# V2-005 H2 Delta Closure Review

**结论：NOT ACCEPTED。实施授权保持 BLOCKED。**

本次直接读取 GitLab 固定提交和比较结果，复核 H2-01～H2-06。两项通过，四项未闭环。H2 已修复部分实际缺陷，但“六项全部完成、跨文档已全部一致”的结论不成立。剩余工作属于既有整改范围内的文档收口。

## 1. 受审范围与来源

| 项目 | 已核实值 |
|---|---|
| 日期 | 2026-10-04，Asia/Shanghai |
| 仓库 | https://gitlab.com/ayitnovel/ainovelos |
| 审核条线 | dev_cc；受审分支 work/h2-convergence-closure |
| H1 baseline | c9345d18b69049cacbfd61690a781850a0e8ccf1 |
| H2 revision | e00b035c9789061983463a49b54e8fe87e26c011 |
| 远端分支 HEAD | 与 H2 revision 一致 |
| 比较方式 | straight/direct H1..H2；compare_timeout=false |
| 提交链 | c9345d18 → 6bad16fa → e00b035c |
| 变更 | 7 个路径：3 个新增、4 个修改；未涉及生产代码、测试或 CI 配置 |
| 本次动作 | 只读审核、隔离的代码样例复现、生成独立报告 |

原始来源：

- [H1→H2 比较](https://gitlab.com/ayitnovel/ainovelos/-/compare/c9345d18b69049cacbfd61690a781850a0e8ccf1...e00b035c9789061983463a49b54e8fe87e26c011?straight=true)。
- [H2 提交](https://gitlab.com/ayitnovel/ainovelos/-/commit/e00b035c9789061983463a49b54e8fe87e26c011)。
- 固定 H2 ref 的 AGENTS.md、plan/README.md、AI_EXECUTION_PROTOCOL.md、领域规范、相关机器记录和 V2-005 文档原文。

读取固定 ref 的文件后进行逐项检查；未以提交说明或实施者的 COMPLETE 声明代替验证。审阅者未修改仓库、提交、审批 MR、合并或签发实施授权。本报告判断契约收口，不对尚未存在的 V2-005 生产实现作验收。

## 2. 六项裁决

| 项目 | 裁决 | 实际结果 |
|---|---|---|
| H2-01 状态收敛 | FAIL | SUMMARY 已修正；DECISION_GATES 仍有已审批勾选、READY、完整冻结与 binding 声明 |
| H2-02 UUID v4 收敛 | FAIL | SUMMARY 与 PLAN 已修正；DECISION_GATES 当前风险条款仍采用 ULID/fallback |
| H2-03 §13.1 schema pattern | PASS（文档范围） | entity_id 已加入 UUID v4 pattern，与 §9.2 一致；ECMAScript pattern 正反例通过 |
| H2-04 PLAN normalize 同步 | PASS | 已加入内部 U+3000 删除；与 H1 可执行检查的函数执行体一致，5 个样例通过 |
| H2-05 三层存储语义 | FAIL | 新文档已建立三层定义，但主契约矛盾未同步消除；新文档自身另有错误示例 |
| H2-06 历史报告标记 | FAIL | FINAL_REMEDIATION_REPORT 已标记；其他明显过时的进度/状态报告仍未标记或建立替代关系 |

H2-03 的 PASS 仅证明本轮要求的 pattern 已落实到文档、规则样例得到验证。未在本环境执行完整 JSON Schema Draft 2020-12 验证器，也不等于生产 schema 或 V2-005 测试已实现。

## 3. 尚未闭环的发现

### H2-R01 — 当前审批与授权仍互相矛盾

**对应：H2-01；级别 P1；CONFIRMED / E2；建议 ADOPT_NOW；阻塞本次 closure。**

固定 H2 的 `docs/V2-005_DECISION_GATES.md`：

- L485～489：多份文档仍被 `[x] reviewed and approved` 标记，包括 Implementation Contract。
- L504：`Implementation Authorization: READY`。
- L506：`Recommended Action: AUTHORIZE IMPLEMENTATION`。
- L530：`All documents complete and frozen.`
- L540：`Contract: Complete and binding`。

同一文件 L450～458 却将实施状态声明为 `BLOCKED_ON_CONTRACT_REVIEW`，主契约头部也是 `INDEPENDENT_REVIEW_PENDING`。DECISION_GATES 在 H1→H2 中未变更，因此以上缺口仍在。

**最小修正：**撤回未经验收支持的批准勾选，将授权段统一为 `PENDING_REVIEW / BLOCKED_ON_APPROVAL`，将冻结/binding 声明改为“文档已修订，待独立复核通过”。已完成的文档准备工作可以继续记录 COMPLETE；不得据此标记批准或实施就绪。

**复核通过条件：**当前文档头部、Gate 3/4、Final Certification、Approval Checklist、Authorization 和 Summary 使用同一审批口径。历史叙述与“通过审核后才可冻结”的条件语句可以保留。

### H2-R02 — 当前 Gate 文档仍采用 ULID/fallback

**对应：H2-02；级别 P1；CONFIRMED / E2；建议 ADOPT_NOW；阻塞本次 closure。**

固定 H2 的 `docs/V2-005_DECISION_GATES.md`：

- L140：`ULID unavailable → UUID fallback`。
- L142：`ID format debate → Simple ULID choice`。
- L240～242：当前 R-1 仍是 ULID 库不可用，缓解方式写成 UUID v4 fallback implemented。
- L254～256：当前 R-4 仍采用 ULID。

这些属于当前资源/风险判断，并非“修订前”的引用，与 UUID v4 唯一格式冲突。

**最小修正：**上述当前条款统一为 Python 标准库 `uuid.uuid4()`、UUID v4 唯一格式、无环境回退。原始历史引用、负例中的 ULID 和“No ULID fallback”的禁止性表述不要求删除。

**复核通过条件：**所有当前设计/风险/实现指令均指向 UUID v4，不再出现实际采用 ULID 或双路径回退的条款。

### H2-R03 — 三层存储模型未落实到主契约，且新示例错误

**对应：H2-05；级别 P1；CONFIRMED / E2；示例另有实际执行证据；建议 ADOPT_NOW；阻塞本次 closure。**

新增 `docs/V2-005_STORAGE_MODEL.md` 定义：input 为原输入；stored display value 只执行 `.strip()`；lookup key 查询时生成、不持久化。这个方向可采用，但主契约尚未同步：

- `IMPLEMENTATION_CONTRACT.md` L322 / §3.2：仍写 `canonical_name = new_canonical_name`，未表达 stored display 的 trim；PLAN 的 rename 示例实际执行 `.strip()`。
- L377 / §3.3：别名入集合仍写 `after normalization`。
- L407 / §3.4：别名移除仍写 `after normalization`。
- L911 / §9.4：`Store original (raw) form only.`
- L929：仍以 `Raw storage` 描述 V2-005 范围。

H1→H2 对主契约仅修改了 §13.1 的 entity_id 字段，因此上述存储条款没有被新文档替换。

新存储文档 L76～77 的 add_alias 示例本身也有确定错误：

```python
input_alias = "  老张　  "
input_alias.strip() == "老张"       # 实际结果
input_alias.strip() != "老张　"     # 文档目前的错误预期
```

尾部 U+3000 是外侧空白，`.strip()` 会连同尾部 ASCII 空格一起删除。内部 U+3000 才会在 stored display 中保留，例如：`"  李　明  " → "李　明"`，lookup 再变为 `"李明"`。

**最小修正：**同步主契约 §3.1～3.4、§9.4 和直接实现示例；明确存储/集合操作使用 trim 后的 display value，查询使用 normalize_for_lookup。将“after normalization”改成精确的“after outer whitespace trim”，并写清 remove_alias 使用何种比较键。修正 add_alias 示例，保留查询时生成 lookup key 的既定设计。

**复核通过条件：**一个输入在契约、PLAN、STORAGE_MODEL 中得到一致的 stored display 和 lookup key；首尾 U+3000 与内部 U+3000 的样例均能实际复现。

### H2-R04 — 历史状态隔离不完整，测试数量口径仍有残留

**对应：H2-06；级别 P2；CONFIRMED / E2；建议 ADOPT_NOW；阻塞本次文档收口。**

本次已在 `V2-005_FINAL_REMEDIATION_REPORT.md` 第一行添加 `HISTORICAL - Superseded by H2`，此部分成立。

以下其他旧状态文档仍无历史/替代标记：

| 文档 | 仍暴露的旧状态 |
|---|---|
| V2-005_REMEDIATION_STATUS.md | 头部 PARTIAL_REMEDIATION_COMPLETE (6/15 items) |
| V2-005_REMEDIATION_RECORD.md | 头部 Partial implementation in progress，多项 NOT STARTED |
| H1_REMEDIATION_PROGRESS.md | H1-01 PARTIAL COMPLETE，并建议提交部分工作再继续 |
| H1_CHANGE_SUMMARY.md | 新增到 H2，但叙述旧 H1；H1-08 PENDING，并声称全部冻结/ULID等残留已清除 |

这些文件会把旧进度或未经独立确认的完成结论继续传给后续 AI。不能以“没有改这些文件”视为完成 stale 报告隔离。

另有与本轮“计数已澄清”提交说明相关的残留：DECISION_GATES L150/L524 仍写完整矩阵 38 个测试，L545 和 SUMMARY L237 仍写 38+；当前 TEST_CONTRACT_MATRIX 明确为 TC-005-001～051，共 51 项。主契约的 `Minimum 25` 可以作为最低核心要求保留，但应明确它与完整 51 项矩阵的关系，避免执行者按 25 或旧 38 项停止。

**最小修正：**对上述确已被替代的进度/状态文档添加历史标记、适用基线、superseded_by 和“不构成当前审批/实施依据”的说明，保留原文证据。建立一个当前 H2 状态入口，并同步其引用的完整测试矩阵为 51 项；25 的最低口径若保留，应注明完整矩阵仍须全部覆盖。

**复核通过条件：**读者能从文档头部区分历史状态与当前状态；当前完整测试集统一为 51，未把计划测试写成已执行结果。

## 4. 已确认通过的部分

### H2-03

§13.1 的 entity_id 不再仅靠 `minLength: 1`，已采用与 §9.2 一致的 UUID v4 pattern。以该文档实际 pattern 在 ECMAScript Unicode 正则引擎执行：合法 UUID v4 通过；`abc`、`123`、ULID、全大写、错误版本和末尾换行被拒绝。共 7 个样例，预期一致。

边界说明：在 Python `re.search` 中，同一个 `$` pattern 会接受末尾单个换行，而 `fullmatch` 会拒绝。这里未执行 Python jsonschema 库，所以不将这一引擎差异直接写成完整 schema validator 的实测缺陷，也不新增本轮 closure 阻塞。实施时宜用实际选定 validator 验证该负例；如需固定 36 字符边界，可结合 minLength/maxLength 36。JSON Schema 官方说明 [pattern 使用 ECMAScript 语法](https://json-schema.org/understanding-json-schema/reference/string)。

### H2-04 与 H1 已通过项的保留

- 实际执行 H1_03_EXECUTABLE_CHECK 第一段 Python：11/11 预期一致，包括末尾换行拒绝。
- 实际执行 H1_05_EXECUTABLE_CHECK：5/5 样例通过。
- 抽取 PLAN 的 normalize_for_lookup：除 docstring 外，执行体与 H1_05 helper 的 AST 一致。
- 再执行 PLAN 的 5 个样例：全部通过，包含 `李　明 → 李明`、`John　Doe → johndoe`。

这些是文档代码样例的复现结果，不能称为尚未实现的 V2-005 领域契约测试 51/51 PASS。

## 5. 精确提交 CI

[Pipeline 2910274247 / IID 109](https://gitlab.com/ayitnovel/ainovelos/-/pipelines/2910274247)：远端状态 SUCCESS，source=push，绑定 SHA=e00b035c9789061983463a49b54e8fe87e26c011。

| Job | ID | 状态 | allow_failure |
|---|---|---|---|
| static | 16918547997 | success | false |
| schema_contract | 16918547998 | success | false |
| unit | 16918547999 | success | false |
| arch_fitness | 16918548000 | success | false |
| postgres_env | 16918548001 | success | false |
| secret_dependency | 16918548002 | success | false |

已直接核对 pipeline 和六个 job 的远端返回，另抽查 schema_contract 日志中现行治理测试的运行记录。六项成功成立；本次未完整重验所有 job 原始产物与 hash。CI 成功没有消除本报告列出的跨文档语义冲突。

## 6. 当前状态与下一动作

```yaml
H2_DELTA_CLOSURE_REVIEW: NOT_ACCEPTED
H2_01: FAIL
H2_02: FAIL
H2_03: PASS_DOCUMENT_SCOPE
H2_04: PASS
H2_05: FAIL
H2_06: FAIL
CONTRACT_STATUS: REVISED / INDEPENDENT_REVIEW_PENDING
IMPLEMENTATION_AUTHORIZATION: BLOCKED
EXACT_REVISION_PUSH_CI: SUCCESS_6_OF_6
NEXT_ACTION: FOCUSED_DOCUMENT_CONVERGENCE_AND_DELTA_REVIEW
```

固定 H2 的机器源中 V2-005 仍为 OPEN / PLANNED，execution_packet_ref=null，AT-V2-005 为 PLANNED；这符合当前仍处于准备审核阶段。本次未更改这些记录，也未审定 P0 后续阶段准入。

下一步仅处理 H2-R01～R04，保留通过项和原始历史证据。后续复核绑定新提交，对 e00b035→新提交做直接差异比较，运行受影响的样例，并核对该提交 CI。契约收口通过后，进入实施仍需满足既有阶段门禁与正式执行包条件；本报告不自动授权 IMPLEMENT。

不需要架构重构、新 Provider、数据库实现或增加未来阶段能力。旧 H1 包本次只作为历史来源：其内 manifest 自述来源 6b35aa1，不能作为 H2 完整快照或 H2 closure 证据。无需为本轮审核改写历史包内容。
