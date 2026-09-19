# ccdoc 架构审核交付包

审核日期：2026-09-19。对象为 ANovelOS 的 `ccdoc/` 全部 25 份规划文件。

先读 `CCDOC_ARCHITECTURE_AUDIT_REPORT.md`；任务化整改使用 `REMEDIATION_REGISTER.json`；产品目标、真实读者验证和研究来源的展开说明见 `product-review.md`。

## 结论

当前资料可保留为设计候选库，但不适合作为统一的最终实施基线直接开发。应沿用户已经冻结的 P0—P14 路线，先关闭规范、Canon、Genre、门禁和认证口径中的阻断问题。主报告有 24 项发现：8 项阻断、15 项高优先级、1 项一般。这里的级别是阶段准入级别，不是线上漏洞等级。

## 验证范围

- 原文快照：25 文件，22,403 行，620,468 字节；逐文件 SHA-256 在 `audit-results.json`。
- 四份脚本均已在本机 Python 3.9.6 执行成功，仅依赖标准库。
- Genre/模板 12 探针、核心领域/存储 9 项检查、交付 12 项检查及产品侧例算。不同脚本存在 A/B 测试等重叠，不能简单相加当作独立缺陷总数。
- 代码提取只运行预先审阅的命名定义；未运行文档里的部署、推送、删除或 Provider 命令。
- PostgreSQL DDL 是静态审阅；跨小说关系只在 SQLite 上验证等价的单列外键逻辑。没有宣称 PostgreSQL、CI、V2 或真实模型认证已通过。
- 文档内模型价格只做内部算术复算，不作为当前价格；小样本统计例算不作为起点市场实测。

## 复现

将原始 `ccdoc/` 与本文件所在的 `ccdoc-review-2026-09-19/` 放在同一个父目录，保持源文件内容与记录的哈希一致，从父目录运行：

```sh
python3 ccdoc-review-2026-09-19/audit_ccdoc.py
python3 ccdoc-review-2026-09-19/core-probes.py
python3 ccdoc-review-2026-09-19/delivery-probes.py
python3 ccdoc-review-2026-09-19/product-probes.py
python3 ccdoc-review-2026-09-19/build_delivery.py
```

脚本会更新本审核目录内的结果 JSON；不修改 ccdoc。本包不含原始规划文件，因此脱离源目录仍可阅读报告和结果，但运行探针需要同一份源资料。文档引用使用文件名/行号；桌面内的绝对路径链接定位的是此次审核机器上的原文。

`build_delivery.py` 生成整改台账、文件校验清单和 ZIP，检查源快照未变、发现数量/等级、文件引用及 ZIP 解压字节一致性。该打包验证不等于业务系统测试。

## 文件说明

| 文件 | 用途 |
|---|---|
| CCDOC_ARCHITECTURE_AUDIT_REPORT.md | 主审核、24 项发现、整改和阶段准入 |
| product-review.md | 产品、中文网文、读者及外部研究专项 |
| REMEDIATION_REGISTER.json | 每项发现的级别、证据位置、建议、关闭条件和阶段 |
| audit_ccdoc.py / audit-results.json | 清单与 Genre/模板复现 |
| core-probes.py / core-probe-results.json | 模型往返、时间区间、关系 scope 和 DDL 静态检查 |
| delivery-probes.py / delivery-probe-results.json | 工作流、评估、缓存、备份与预算检查 |
| product-probes.py / product-probe-results.json | A/B、小样本与成本/权重/工期例算 |
| build_delivery.py | 可重复打包与基本交付校验 |
| FILE_MANIFEST.json | 审核文件 SHA-256 与字节数，清单自身除外 |

所有整改状态初始为 OPEN。审核完成不代表被审核项目的问题已经修复或对应工程任务已 CLOSED。
