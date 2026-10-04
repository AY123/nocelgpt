# V2-004 安全处置当前记录与历史证据

当前 canonical [逐项处置记录](SECURITY_FINDING_DISPOSITION_RECORD.json)已对齐实际 `e927dbf` / Pipeline `2910441607` 的 45 项扫描：原 43 项保留，新增 SF-044/045 为公开测试变量名命中；按现有分类生成 38 项精确申请，批准、应用、关闭均为 0，owner-required 仍 7。当前扫描绑定与旧来源分开记录，说明见 [极小 Delta 对账](../security-delta-20261004/README.md)。旧处置原文已保存可恢复 gzip 快照。

以下 CI 索引、权限观察、local packet 和 handoff 是 3ce6c32 时点的历史证据，不声明为本次当前输入或当前权限验收。

本目录记录 2026-10-04 对实际 SHA `3ce6c32e5666ee8fc2381dcf40f71dd7f8802bc0`、Pipeline `2910092880` 的复核。五项门禁 PASS，`secret_dependency` 硬失败；202 + 212 + 1 = 415 项测试无失败/错误/跳过。V2-004 仍 IN_PROGRESS，P0 NOT_VERIFIED。

- [逐项处置记录及完整列表](SECURITY_FINDING_DISPOSITION_RECORD.md)：当前 45 项 OPEN / 38 项申请；原 43 项和 36 项申请保留在原文快照，另外 7 项仍需 owner 依据。
- [实际 CI artifact 索引](ci-evidence-index.json)：项目、revision、pipeline、job、原始 ZIP hash、下载地址和仓库内 receipt/log/JUnit/安全报告选集。选集保持原始字节，原 CI 路径由索引映射；不把共享 runner 的产物称为受保护执行。
- [可信权限边界](TRUSTED_PERMISSION_BOUNDARY_RECORD.json)：136 个可用 runner 都是 instance；实际 runner `54907241` 为 not_protected；保护规则仅覆盖 main，dev_gpt 未保护。变量覆盖限制已是 no_one_allowed，skip 合并字段为 null/未知。Owner 和 Developer 存在，真实权限正反例尚未执行。
- [恢复交接](handoff.json)：已完成、失败/未知、下一动作和恢复条件。

旧 `dist/validation/v2004-final-3ce6c32/DELIVERY_HANDOFF.md` 是本地补充材料，不属于该远程 revision，也不作为仓库可核验来源。本目录提交后能从仓库核验上述事实；这些事实仍只绑定被测 3ce6c32，不证明记录提交本身通过 CI。

下一步需要三组历史凭据的脱敏撤销/轮换或非凭据依据、SF-037 引用归属，以及可用 Linux/Docker 主机和安全接入方式。具备依据后推进实际处置、精确有期例外审批和可信边界实施。最终同一候选 SHA 上六项 mandatory gates 全 PASS，并完成受保护执行与真实权限正反例，再进入验收。没有批准或事实依据的动作继续保持未执行。

[本地记录核验](local-verification.json)：五项治理检查、正式 IMPLEMENT 入口、43项内容/41项附件逐项核验通过；新脱敏记录默认规则扫描0发现。这些结果仅证明记录质量，不替代真实 CI 或权限验收。
