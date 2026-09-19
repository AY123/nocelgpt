# W9 校准 backfill→定级 闭环走通报告（官方 CLI）

- **目的**: 证明「真值一旦落到 human_scores.json，官方 W9 管道自动产出 12 维定级」。
- **日期**: 2026-07-22
- **命令**（官方 CLI，非自定义脚本）:
  - `reviewer-calibration backfill-all --project <sandbox>`
  - `reviewer-calibration summary --project <sandbox> --write`

## 硬红线（已守住）

- **只在隔离沙箱** `/tmp/w9-cal-sandbox`（golden-set 副本）操作。沙箱里把 AI consensus 落到 human_scores.json 位置，**live 的 43 个真值文件与真实校准产物一个未碰**（git 已确认，live QGS-00001 仍是 `consensus: borderline`）。

## 结果

官方 backfill-all → summary 全链路跑通，43 样本、12 维全部产出 correlation / MAE / CI95 / 定级：

| status | sample_count | real | skeleton | boundary |
|---|---|---|---|---|
| complete_with_skeleton_seeds | 43 | 43 | 7 | 5 |

12 维 trusted（n≥5, corr≥0.6）：全部 12 维。相关性 0.94–0.99。

## 诚实结论：闭环成立，但相关性是"自比"假象，不是校准质量

- **闭环成立**：这证明了 §15.6 判据要的机制 —— **真值落盘后，官方 CLI（backfill-all→summary）自动产出每维定级，无需任何手工步骤**。管道是通的。
- **相关性 0.94–0.99 高得反常，必须打折看**：官方 backfill 的 reviewer 侧取 `editor_a`、真值侧取 consensus(=editor_a/b 均值)。而 AI 两个"编辑"是同一个 temp=0 模型、95% 自我一致 —— 于是 reviewer ≈ 真值，相关性接近完美。**这是同一份 AI 数据自己跟自己比，不是 reviewer 校准得好。**
- 对照上一轮 `w8-w9-ai-flow-report.md`（AI consensus 作 reviewer vs 真实 human_mean）得到的 0.53–0.92 才更接近真实 reviewer 能力；本次的近完美相关只说明管道闭合，不说明质量。

## 对 §15.6 判据的影响

- 「人工真值闭环」**判据本身仍需真人评分**（🟡 不变）—— 本次是 AI 替身，相关性自比虚高。
- **增量**：官方 backfill→summary→定级闭环已用真数据端到端验证。真人双评一旦落到 human_scores.json，`reviewer-calibration backfill-all` + `summary --write` 即可直接产出真实定级，**无需任何额外工程**。
