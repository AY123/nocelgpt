# N100-002 / N100-003 100 章实验协议与章级证据表

## 目标

- 冻结 100 章生产验证的实验边界，避免 run 内静默漂移。
- 为每一章建立同构证据记录，覆盖质量、成本、事实候选、审批、状态消费、事故与复盘。
- 让后续 100 章 run 能被独立复核、回放和比较。

## 实验协议

### 协议 ID

`N100-PROTOCOL-0001`

### 适用范围

- 适用于一部作品的 100 章生产验证。
- 适用于从黄金三章到 30 章、再到 100 章的连续推进。
- 适用于主线生产、候选抽取、审批、Mint、Recompute、评审与复盘。

### 冻结项

- 项目根目录与作品名
- 参考输入集合
- Prompt 版本
- Model provider / model id
- 预算上限
- 候选数与 reviewer policy
- W12 模式与是否启用事实回流
- Gate 顺序与人工授权条件
- 允许的配置漂移范围
- checkpoint 频率

### 禁止项

- 在同一 run 内无记录地更换模型
- 在 checkpoint 前改写历史事实
- 跳过人工授权直接 Mint
- 用未校准信号直接 gate 发布决策
- 将文档摘要替代原始证据

### 版本规则

- 协议变更必须生成新版本 ID。
- 变更必须记录变更原因、影响范围与 checkpoint 位置。
- 旧版本继续保留，禁止覆盖式改写。

### 验收标准

- run 内所有章节都能追溯到同一协议版本。
- 协议中的冻结项在 run manifest 中可见。
- 若发生漂移，必须能指出漂移点与审批记录。

## 章级产品证据表

### 记录粒度

- 一章一条记录。
- 黄金三章、checkpoint 章、事故章、人工修正章必须额外标记。

### 建议字段

| 字段 | 说明 |
|---|---|
| `run_id` | 例如 `RUN-00025` |
| `protocol_id` | 实验协议版本 |
| `chapter_id` | 章节 ID |
| `chapter_index` | 章序号 |
| `draft_hash` | 章节正文 hash |
| `state_hash` | 章节状态 hash |
| `final_hash` | 最终落盘 hash |
| `token_input` | 输入 token |
| `token_output` | 输出 token |
| `token_total` | token 总量 |
| `cost` | 本章成本 |
| `quality_verdict` | 质量 verdict |
| `commercial_verdict` | 商业 verdict |
| `fact_candidates` | 候选数与分类摘要 |
| `approval_status` | 审批状态 |
| `mint_status` | Mint 状态 |
| `recompute_status` | Recompute 状态 |
| `resume_status` | 是否经过恢复 |
| `incident_tags` | 事故标签 |
| `notes` | 章级人工备注 |
| `evidence_refs` | 对应 manifest / report / checkpoint 路径 |

### 记录规则

- 任何字段都必须可由原始产物回填，不允许手填想象值。
- 如果某项无法获得，应明确标 `unknown` 或 `null`，不能伪造。
- 证据表应优先引用已有产物，不复制大正文。
- 每 10 章至少有一次 checkpoint 汇总。

### 最低验收

- 100 章全部有记录。
- 每条记录都能回指到 run manifest 与对应章节产物。
- 质量、成本、候选、审批、Mint、Recompute 的字段不缺位。
- 可直接用于后续 300 章滚动扩展。

## 对应当前仓库产物

- `genesis-pilot/registry/derived/run-manifests/RUN-00025.json`
- `genesis-pilot/registry/derived/serial-checkpoints/cp-010.json`
- `genesis-pilot/registry/derived/serial-checkpoints/cp-020.json`
- `genesis-pilot/registry/derived/serial-checkpoints/cp-030.json`
- `genesis-pilot/analysis/v10-baseline-report.md`
- `genesis-pilot/analysis/checkpoint-reviews-run00025.md`
- `genesis-pilot/analysis/w12-run00025-report.md`
- `genesis-pilot/analysis/w12-mint-walkthrough-report.md`

## 备注

- 这份协议是当前版本的冻结版，不是最终商业协议。
- 后续若作品切换、模型切换或 reviewer policy 变化，必须新开协议版本。
