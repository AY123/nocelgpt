# 写作中断后查看原请求的回执

模型调用中断，草稿检查点显示 `UNKNOWN` 时，可以用原工作库、冻结输入和对应的 Gateway 账本检查同一次尝试。

```sh
python -m anovel.workflow --db WORKFLOW_DB --project PROJECT --branch BRANCH --run-id RUN \
  recover --input CURRENT_INPUT --gateway-ledger GATEWAY_LEDGER --diagnose-only
```

如果中断发生在续场，指定原场景步骤和原账本。

```sh
python -m anovel.workflow --db WORKFLOW_DB --project PROJECT --branch BRANCH --run-id RUN \
  recover-scene --input CURRENT_INPUT --step-id SCENE_STEP \
  --gateway-ledger GATEWAY_LEDGER --diagnose-only
```

`state` 是草稿当前保存的状态。`stored_result` 和 `ledger_result` 分别显示检查点保存的结果和原尝试在账本中的结果，各自只返回状态和摘要。账本尚无结果时，`ledger_result` 为 `null`。同一逻辑请求的另一笔尝试即使已成功，也不会填入原尝试的结果。原回执晚到时，可以同时看到原检查点的 `UNKNOWN` 和账本的 `SUCCESS`。

首场改稿后，旧续场显示 `STALE_SOURCE`，`source_current` 为 `false`。此时即使原回执成功，续场仍需从新版首场重新制作交接。诊断只返回回执摘要，保留已保存的草稿状态与调用记录。项目任务接口使用 `INSPECT_RECOVERY`，续场时附上 `step_id`。

原检查点为 `UNKNOWN` 且来源仍有效时，用 `--save-late-success` 替换上述的 `--diagnose-only`，可把原尝试的成功正文保存为 DRAFT。重复运行会读回同一份已保存草稿。普通恢复继续返回已保存的检查点状态。任务接口使用 `SAVE_LATE_RECOVERY_SUCCESS`。

## 取消保存下一章

使用生成下一章时的冻结输入、前章修订和交接文件。沿用原命令使用的 `--brief`、`--source-chapter-id` 或全局 `--draft-handoff-step-id`。

```sh
python -m anovel.workflow --db WORKFLOW_DB --project PROJECT --branch BRANCH --run-id RUN \
  cancel-next-chapter-draft --input CURRENT_INPUT --expected-revision-hash SOURCE_REVISION_HASH \
  --handoff HANDOFF
```

返回 `CANCELLED` 时，该次写作输入无法再保存到工作库。已发出的模型请求仍可能返回，账本保留原回执。再次恢复或导入同一份结果会收到 `NEXT_CHAPTER_WRITE_CANCELLED`。继续创作时，可依据新版前章和交接重新生成。

返回 `DRAFT_SAVED` 时，草稿已经保存，`revision_hash` 指向该次写作最初保存的版本。再次取消同一输入会返回相同结果。应用任务接口使用 `CANCEL_NEXT_CHAPTER_DRAFT`。

## 从新版前章恢复后章的改写

用新版前章生成交接和简报。用 `inspect-written-draft-impact` 或 `inspect-written-draft --version N` 取得要替换的后章修订摘要。在 `prepare-next-chapter-model-request` 的原有参数上加 `--expected-target-revision-hash OLD_TARGET_REVISION`，将这版后章绑定到待生成的请求。

取得这份请求的成功回执后，用同样的交接、简报和待替换修订执行恢复。如果前章是另存的 Writer 草稿，准备和恢复时都带上同一个 `--source-chapter-id`。

```sh
python -m anovel.workflow --db WORKFLOW_DB --project PROJECT --branch BRANCH --run-id RUN \
  recover-next-chapter-openai --input CURRENT_INPUT --expected-revision-hash NEW_SOURCE_REVISION \
  --expected-target-revision-hash OLD_TARGET_REVISION --handoff NEW_HANDOFF \
  --brief NEW_BRIEF --request REWRITE_REQUEST --writer-ledger WRITER_LEDGER --output REVISED_DRAFT_JSON
```

恢复只读取原尝试的回执，核对两端修订后保存后章的新一版 DRAFT。旧交接、旧请求、晚于请求准备的后章修改和缺失回执都会使恢复停止。如果保存成功后导出中断，原参数配上新的输出文件名可重新导出同一版。用 `inspect-written-draft --version N --output FILE` 导出各版 TXT 对照。

## 用现有 OpenAI Writer 执行改写

已获准运行的 OpenAI 写作任务可以在原授权记录中提供 `expected_target_revision_hash`，使用准备请求时选定的后章修订。原 Writer 入口会核对新版交接、待替换的草稿和冻结请求，再认领一次派发并读取凭据。生成完成后将结果保存为新一版 DRAFT，并保留旧稿。[OpenAI Writer 入口](../V2-020/revision-inspection-20261122/kimi-chapter-dispatch-20261124/run_openai_chapter.py)

如果模型已返回但保存或导出中断，用上一节的恢复命令处理原账本和原请求。恢复沿用原尝试，不会再次提交给模型。

## 前章重建期间导出后章旧稿

前章刚改、场景接续和整章还在重建时，可在原工作库里指定已保存的后章版本，将原文导出到新的 TXT 文件。

```sh
python -m anovel.workflow --db WORKFLOW_DB --project PROJECT --branch BRANCH --run-id RUN \
  inspect-written-draft --input CURRENT_INPUT --chapter-id TARGET_CHAPTER \
  --version 1 --output HISTORICAL_DRAFT_TXT
```

显式指定版本时，导出会沿该稿保存时的来源查找原前章。默认读取和生成新交接仍以当前版本为准，等新版前章重建后才能从它接续。

在《南桥试拍》留存工作库的副本中修改上游首场后，第 7 章两版均能导出，逐字节匹配原 TXT。原工作库和 Writer 账本的摘要在验证前后相同。

## 对照新旧稿里的未结约定

用 `inspect-written-draft --version N` 取得要审读的版本摘要。对每个版本准备一份包含本版原句和编辑判断的审读文件，沿用该版前章对应的章纲。

```sh
python -m anovel.workflow --db WORKFLOW_DB --project PROJECT --branch BRANCH --run-id RUN \
  review-written-draft-commitments --input CURRENT_INPUT --chapter-id CHAPTER \
  --version N --expected-revision-hash REVISION_HASH --brief CHAPTER_BRIEF \
  --review OBSERVATIONS --output VERSION_REPORT
```

报告从该版草稿实际使用的前章修订读取约定，并核对原句只在所选版正文中出现一次。`--version` 用于历史对照。要保存约定判断，省略 `--version`，带入当前稿摘要并使用 `--save-observations`。

## 提交应答中断时读取原结果

持有原执行票据和候选的调用方可以用 `CanonCommitService.inspect_chapter_submission(ticket, candidate)` 读回该次提交。`COMMITTED` 随附原收据，`CANCELLED` 表示数据库已确认取消，`UNKNOWN` 表示尚未观察到确定结果。读取在单个只读数据库快照内完成。

| 场景 | 本地验证 |
| --- | --- |
| AT-V2-027-01 中断恢复 | 首场、续场和后章 Writer 在中断后读回原尝试。已有成功回执可保存或重新导出同一版草稿。 |
| AT-V2-027-02 取消后迟到 | 先持久化取消，再让同一尝试返回成功。草稿重试和手工导入被拒绝，隔离库的旧执行及已发 TEST Permit 也无法提交。 |
| AT-V2-027-03 重复投递 | 重复启动和恢复原检查点保持 `UNKNOWN/PENDING` 以及原 Gateway 账本责任。另一尝试的成功无法替代原回执。 |
| AT-V2-027-04 输入变化 | 分别更改正文、合约、Pack 或 parent 后，恢复拒绝使用旧检查点。使用原输入的正例能够读回同一次成功。 |
| AT-V2-027-05 取消与提交竞态 | 两个真实 PostgreSQL 连接分别验证先取消和先提交。冷启动读取原结果，拒绝错 scope、操作者、父提交、执行版本或载荷。 |

草稿场景使用本地模拟响应。章节、场景和受控 Writer 回归共 148 项通过，提交和恢复的隔离 PostgreSQL 回归共 73 项通过，架构检查共 244 项通过，均无跳过。常规 PostgreSQL 检查已加入 V2-027 的竞态测试。

本候选承接已验收的 V2-020 和 P5 记录。正式结项依据本候选的常规 CI 和对应验收登记。
