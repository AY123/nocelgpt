# 整章草稿抽取和接续

作者可检查已保存的整章草稿。命令默认核对当前版本和最新前章来源，报告对应的原句、证据位置、抽取遗漏和待复核线索。用 `--version N` 可对照留存版本。

```sh
python -B -m anovel.workflow --db WORKFLOW_DB --project PROJECT --branch BRANCH \
  --run-id RUN inspect-written-draft-extraction --input CURRENT_INPUT \
  --chapter-id CHAPTER --expected-revision-hash REVISION_HASH --output PRIVATE_REPORT
```

标准输出只有该版本的摘要。完整报告含私有正文摘录，按 `0600` 创建，已存在的文件会被拒绝。任务入口 `INSPECT_WRITTEN_DRAFT_EXTRACTION` 使用同一服务。写作准备复用同一核对结果，只有在提议和独立原文清单对应时，规则支持的实际事实才进入下一章写作输入。人物误信、传闻、意图和自然正文线索保留原文，供作者复核。超出规则范围的正文标记为 `UNKNOWN`。

## 离线回放

用 ANovelOS 的真实 Writer 留存稿回放《南桥试拍》第 7 章。首稿和改稿分别定位到接听、延后回电的线索，两版均保留后半章的人物误信。第 8 章冻结输入继续携带改稿里的未结约定。旧版修订摘要无法用于新版审读，旧交接也无法用于准备新版下一章。

```sh
python -B plan/validation/execution/V2-021/written-draft/verify_retained_drafts.py \
  RETAINED_WRITER_JOB_DIRECTORY
```

回放脚本只在私有临时目录读回已保存版本和请求，原库、模型账本及正文的文件哈希保持一致。留存的场景账本位置曾发生变化，历史版本走既有的只读历史入口。当前版本核对、改稿后的交接失效和重新准备另由工作流回归验证。[脱敏回放结果](RETAINED_READBACK.json)

| 原验收场景 | 本地核对 |
| --- | --- |
| AT-V2-021-01 正文和 Delta 同源 | 整章装配的 `NarrativeDelta` 使用原装配身份及正文哈希。Writer 报告绑定来源修订、正文哈希和原文区间，旧版无法配新版。 |
| AT-V2-021-02 区分叙述情境 | 有限规则正反例覆盖实际状态、传闻、误信和计划，只有实际事实进入下一章。真实稿的人物误信作为待复核线索。 |
| AT-V2-021-03 诊断后段遗漏 | 在提议读入前封存独立的完整原文清单。故意删除已知尾段变化时，报告给出原文位置，写作准备拒绝失配的抽取结果。 |
| AT-V2-021-04 避免误放行 | 缺失、冲突、错位置的证据产生 `FAIL` 或 `ERROR`。自然语义证据不足保持 `UNKNOWN`，仅形成 DRAFT 证据。 |
