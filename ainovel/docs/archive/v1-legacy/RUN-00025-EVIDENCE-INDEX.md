# RUN-00025 证据索引 (CLOSE-01~03)

本文件让 fresh clone 可定位并独立复核 W5–W7 的 30 章产品基线证据。

## 背景

`genesis-pilot/` 整目录被 `.gitignore:7` 忽略(内含 50MB+ 快照,不宜全量入库)。
经二次核实,RUN-00025 及配套报告**真实存在且充实**;首轮审计判「无法定位/可能丢失」是搜索路径错误(只搜了仓库根 `analysis/`)。
本轮通过 `git add -f` 白名单方式,将关键证据(约 1.0MB)纳入版本控制;50MB 快照仍留在 gitignored 的本地目录。

## 运行事实(来自 manifest)

| 字段 | 值 |
|---|---|
| run | RUN-00025 · genesis-pilot · 2026-07-18 |
| 冻结配置 | LAUNCH-30CH-V10-0001 (hash 37ae1c4f) — prompt v10 全栈 `--long-arc` + `--hygiene`, deepseek-chat |
| 章数 | 33/33 done,0 skip |
| final_state_hash | `sha256:147514d4d961d1e4d3808199be5d55b356a4c0ef01804ccd7229c3a0526c52d2` |
| token | in 131249 / out 104868 / total 236117 |
| gating | false (ADR-003) |

## 已纳入版本控制的证据(git add -f 白名单)

| 文件 | sha256(前16) | 说明 |
|---|---|---|
| `genesis-pilot/registry/derived/run-manifests/RUN-00025.json` | `8b2716aebac2b65a` | run manifest,33 章、totals、gating |
| `genesis-pilot/registry/derived/serial-checkpoints/cp-010.json` | `98f7569b06c6dc0e` | 第 10 章 checkpoint |
| `genesis-pilot/registry/derived/serial-checkpoints/cp-020.json` | `10008c503f539731` | 第 20 章 checkpoint |
| `genesis-pilot/registry/derived/serial-checkpoints/cp-030.json` | `9fc6b665f720d587` | 第 30 章 checkpoint |
| `genesis-pilot/analysis/v10-baseline-report.md` | — | 30 章基线报告 |
| `genesis-pilot/analysis/checkpoint-reviews-run00025.md` | — | 10/20/30 章复盘 |
| `genesis-pilot/analysis/w12-run00025-report.md` | — | W12 全 33 章双模式汇总 |
| `genesis-pilot/analysis/w12-mint-walkthrough-report.md` | — | W12 候选审批 mint walkthrough(沙箱) |

## 未入库(留在本地 gitignored 目录)

- `genesis-pilot/analysis/run-00025-snapshot/`(26MB,1235 文件)—— 逐章 provenance 快照
- `genesis-pilot/analysis/v10-baseline-snapshot/`(24MB,1514 文件)—— 旧产物归档快照

如需在其它机器复核逐章快照,须从原始运行环境同步这两个目录(不通过 git)。

## 复核方法

```
python3 -c "import json;m=json.load(open('genesis-pilot/registry/derived/run-manifests/RUN-00025.json'));print(m['totals']['final_state_hash'], len(m['chapters']), m['totals']['token_usage']['total'])"
# 应输出:sha256:147514d4... 33 236117
```
