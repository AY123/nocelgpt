# 草稿接续回放工具（V2-020 PREPARE）

把《灯下机床》的三章窗口试写保存为可重复运行的准备样本：核对正文和审阅映射，逐章预演有限事实变化，导出下一章 Writer 安全输入。无需 API、数据库或远程 CI。

在项目根目录运行（输出目录每次用新名称）：

```bash
.venv/bin/python -B plan/validation/execution/V2-020/prepare/replay.py \
  --output dist/experiments/urban-replay-local-01
.venv/bin/pytest -q plan/validation/execution/V2-020/prepare/test_replay.py
```

输出 `replay-report.json` 和 `next-writer-input.json`。后者含候选数值状态、已审阅的接续注记和第三章真实末段，可供下一次窗口试写使用；它是 `WINDOW_DRAFT_CONTEXT`，不是正式 ContextArtifact 或 accepted 前章证据。样本的第一章保留原“第一场”标题，不为统一标题改动原稿。

## 回放什么

| 步骤 | 有限事实预演 | 接续重点 |
|---|---|---|
| 第一章 | 同笔定金配对：工厂18000000→17700000分，机构0→300000分 | 调包仍是猜想；缺页不证明责任人；公开承诺不等于报告已公开 |
| 第二章 | 原候选完整继承，无新 Delta | 有限求证已发，没有已收/已读依据；Writer未获赵川私有信息不能清空既有知情 |
| 第三章 | 报告公开 false→true | 实际证据后揭示真因；报告面向本批相关客户/厂内人员开放；收到不等于验收；30件实物不等于合格放行；授信待审不计现金 |

现金、股权、库存数量、期限等有限事实使用现有 `FactBaseline` / `NarrativeDelta` / `preview_delta` 和已登记题材扩展。每章 `before_sha256` 必须等于上章实际返回的**完整候选**哈希（含 revision、扩展、project/branch/parent），不能只核对几个数值。第二章以 `delta: null` 明确继承，不伪造空 Delta 或提交收据。组件 parent 是试验用固定身份，不冒称真实 Canon HEAD。

## 最小输入契约

`samples/urban/replay.json` 的版本为 `DRAFT_REPLAY_SAMPLE / 1.0`：

- `story`：已有故事 fixture 的仓库路径和字节 SHA256，派生初始事实与扩展，不复制整套作者隐藏输入。
- `branch`、`parent_ref`：隔离预演范围；`initial_notes` 是 Writer 安全的显式候选注记。
- `steps[]`：连续章节号、`body` 路径/hash、`previous_body_sha256`、完整 `before_sha256/after_sha256`、已有有限 `delta` 或明确继承。
- `operation_evidence`：每个 Delta 操作恰好一个当前正文引文；操作本身的 source/chapter 也须一致。
- `notes_after`：同一组注记键完整继承；变更的键与 `notes_evidence` 必须一一对应，不支持静默清空或新增字段。
- `revealed_facts`：实际揭示的隐藏事实及引文；既要满足既有读者边界，也要显式提供实际证据，不能仅因章纲到了第三章就输出真因。
- `ending`：当前正文真实后缀。全部 span 为 **0-based Unicode codepoint / 半开区间**，不按UTF8字节计数、不trim或规范化，末尾换行也参与核对。

单独的 `review.json` 是 `PREPARE_MAPPING_REVIEW / 1.0`，精确绑定整个 sample 的原始字节 SHA256，并登记审阅者、AI技术审阅性质、适用决定及限制。正文改动使 body hash 过期；Delta、注记、span或映射改动使旧 review 失效。工具没有自动重签、自动审批或“改hash就当审阅完成”的命令。修改样本后须实际审阅新正文及映射，再记录新绑定。

这份 review 是实施/验证同一操作者的有界AI技术核对，不是身份认证或安全批准。`provenance.json` 保留原试写审阅链的路径/hash及修正说明，已由本次操作者人工核对；运行时不读取旧 dist 产物，**不会自动认证整条历史审阅链**。第三章沿用 V1 全文审阅＋唯一段落修订＋V2窄差异核对，第二章采用已修正的 Notes。

## 验证与局限

本地专项54项、0skip，结果见[本地记录](../PREPARE_RESULTS.json)。用例包括合法三章/两章前缀、确定性导出、单边扣款与1分不守恒、重复付款旧前置条件、完整状态重置、错项目/parent/source/chapter、缺少或错误引文、提前揭示、非真实末段、正文或注记改动后旧审阅失效、重复JSON字段/非有限数值/非法UTF8和输出覆盖拒绝。

其中数值守恒、前置条件和揭示边界是实际组件/规则检查；“未提供→UNKNOWN”“发出→已收/接受”“数量→合格”的错误注记用例证明**不能复用旧审阅绑定**，不证明工具能理解这些任意自然语言断言。引文相符也不证明注记语义真实。工具不会抽取正文、生成下一章、验证文学质量或调用模型。

V2-020仍为 **OPEN / PREPARE**。真实Provider验收、P5门禁、正式单章 Workflow、Q0–Q3集成、真实读者评价和生产恢复仍待后续任务完成。本次没有 Canon/Permit/accepted/published 状态写入；现有六门配置不变，未触发CI。
