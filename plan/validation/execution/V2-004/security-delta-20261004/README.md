# V2-004 45 项安全发现 Delta 对账

本次只补齐最新已核验扫描 `e927dbfb05f4b917e9f825cb9aae91c6caf64f9a` / Pipeline `2910441607` / security job `16919376075` 与 canonical 的对应关系，不把审核建议变成批准或任务状态。

[Canonical disposition](../security-closure-20261004/SECURITY_FINDING_DISPOSITION_RECORD.json)是当前处置主记录：45 项 = tracked 16 + history 29；PUBLIC_IDENTIFIER 26、TEST_FIXTURE 3、FALSE_POSITIVE 9、POSSIBLE_EXPOSURE 6、TRUNCATED_REFERENCE_UNRESOLVED 1。38 项申请由实际分类计算；approved/applied/closed 都为 0，owner-required 仍 7。

仅新增 SF-044 / SF-045，分别为相同公开测试变量名的当前文件与 e927 历史命中，保持 OPEN / NOT_PERFORMED / authority=PENDING / expires_at=null。原 43 项的完整对象原样保留；current_ci_binding 单独重绑全部 45 个 ID 的真实本次 source、fingerprint 和 artifact，原工作区 15 项指纹不沿用旧临时路径 hash。原 36 项申请不授权新增两项。

可复核来源：

- [实际安全 artifact 与 predecessor 绑定](CI_ARTIFACT_BINDING.json)、[原字节 scan](ci-artifacts/secret-scan.json)、[原字节 receipt](ci-artifacts/receipt.json)。
- [原43与当前45实际差异](finding-delta-vs-c0ba3a7.json)、[e927dbf 全套真实 CI 摘要](actual-ci-summary-e927dbf.json)。
- [命中值 hash 固定 scanner 复现](value-extraction-proof.json)：两项同一 23 字节公开标识，value SHA256 与整行 SHA256 不同；Darwin / Linux 官方发行变体不宣称 binary 字节相同。
- [原3ce6c32处置完整原文 gzip](predecessor-disposition-3ce6c32.json.gz)，解压 SHA 与压缩 SHA 分开绑定，原文也可从 e927 的 Git 对象恢复。

原 CI 报告脱敏省略 Secret / Match；新增两项的 value_sha256 来自精确源 blob 的 JSON 标量并核对同一固定 scanner 的单文件复现，不能声称 CI 报告包含命中原文，也不能把整行 hash 当命中值 hash。只记录 hash、长度及匹配结论，不保存原始命中值。

实施和验证仍是同一操作者，agent 只读复核不称独立人员验收。旧 local packet、handoff 和 audit 是历史快照，不声称在文件更新后仍是有效当前输入。当前执行包引用新的 canonical hash，原数据有完整恢复依据。

本轮主工作区的 [local packet](local-execution-packet.yaml) 和 [实际入口结果 gzip](local-entry.json.gz) 单独存档；压缩与解压 hash 由 [execution-context](../execution-context.json) 绑定。活动包的 clean scope 供后续真实干净提交检出使用，不能用于假称主工作区干净，也不能授权删除用户文件。

被测 e927 是产物来源，后续包含本记录的提交有自己的 SHA；后者必须运行并读取它自己的真实 CI，不能在提交前伪填未发生的结果。源 blob 和稳定 finding ID 用于对账；临时路径指纹绑定各次实际扫描，不以旧指纹代替新提交产物。安全门禁仍 FAIL，V2-004 IN_PROGRESS，P0 NOT_VERIFIED。

后续依次取得 owner 脱敏处置、精确有期批准、可信执行及完整权限控制；未修改 scanner/CI、未应用例外、未部署 runner、未改写历史。
