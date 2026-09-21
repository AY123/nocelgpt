# ANovelOS 规划 v1.1 审核交付包

日期：2026-09-21。结论：**可以开始 P0；先补强规划验收机制，取得真实 P0 证据后再进入 P1。**

## 阅读顺序

1. [完整审核报告](PLAN_V1_1_DEEP_AUDIT_REPORT.md)：结论、架构评估、11 项问题、反例证据、最小整改顺序与最终目标映射。
2. [机器可读问题登记](audit-findings.json)：5 类已复现治理缺陷与 6 项契约/认证/产品细化要求；全部为本次审核建议，没有修改正式任务状态。
3. [探针结果](governance-probe-results.json)：13 项实际检查结果及被审源目录 251 文件哈希。
4. [复现脚本](probe_plan_governance.py)：在临时副本运行原验证器，原规划只读。
5. [交付完整性检查](delivery-integrity.json)：源文件未变化、引用与包内检查结果。

压缩包内的 `plan/` 是此次审核的原样快照。`plan-review-2026-09-21/` 是新增审核资料。原工作区此前已有的改动均予保留，本次未直接修改或关闭正式规划任务。

## 复现

在解压目录中运行（环境需具备原验证器所用的 PyYAML 和 jsonschema）：

```bash
python3 -B plan-review-2026-09-21/probe_plan_governance.py \
  --plan plan \
  --output plan-review-2026-09-21/governance-probe-rerun.json
```

脚本不联网，不调用模型，不启动数据库，不修改原 `plan/`。它会在临时目录构造不合格完成材料并执行验证流程。进程成功退出只表示探针执行完成；应查看 `unexpected_acceptances` 与每项 `expected`/`actual`，不能把脚本退出码 0 误当为治理合格。

此次原始结果为：基线校验通过、原有自测 32/32 通过；三个对照符合预期，十个违规元数据反例被接受。整改后应保留原始结果，在新结果文件记录复测，避免覆盖审核证据。深层反例需要合格前置测试夹具，不能因为更早一层拒绝就认定深层缺口已修复。

## 边界

被审源版本是当前工作区 v1.1.0，源 `FILE_MANIFEST.json` 的 SHA-256：

```text
4340e256fc32e329c8cf291af9ae59b80dd93360e0db4e77bce642d06b5114bd
```

完整报告中的行号指向此快照，后续修订可能改变行号。原脚本运行环境版本记录于 `delivery-integrity.json`。本包没有认证业务代码、PostgreSQL、远程 CI、真实模型、小说质量或市场成功；也没有把历史归档内容当现行实现规范。
