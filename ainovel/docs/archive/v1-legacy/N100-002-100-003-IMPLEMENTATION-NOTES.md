# N100-002 / N100-003 落地说明

这份说明对应代码与文档的同步落地：

- `AI-Novel-Runtime/runtime/serialize/chapter_evidence.py`
- `docs/N100-002-100-003-EXPERIMENT-AND-EVIDENCE-PACK.md`
- `docs/ANOVEL_EXECUTION_TASKS.md`

## 已完成的落地内容

- 新增章级证据表构建器，用 RUN manifest + serial checkpoints 生成同构 ledger。
- 给 100 章实验协议定义了冻结字段与变更规则。
- 将 N100-002 / N100-003 从抽象目标改成可执行协议草案。

## 还需要的后续工作

- 如果要正式启用 100 章协议，需要把协议配置写成可加载的 JSON/YAML，并接到 run 启动入口。
- 如果要正式启用证据表，需要给 `run_manifest` 或 `run_serial` 增加调用入口，把每次 run 自动导出 ledger。
- 这一步目前是“协议与能力就位”，不是完整的生产接线。
